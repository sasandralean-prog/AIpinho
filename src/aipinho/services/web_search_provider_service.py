from __future__ import annotations

import base64
import json
import re
import unicodedata
from html import unescape
from html.parser import HTMLParser
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from aipinho.core.paths import PATHS
from aipinho.schemas.web_search import WebSearchResult, WebSearchSource
from aipinho.utils.yaml_loader import load_yaml_file


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self, *, max_results: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_results = max_results
        self.results: list[dict[str, str]] = []
        self._active: dict[str, str] | None = None
        self._capture_title = False
        self._capture_snippet_index: int | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        css = attr.get("class", "")
        if tag == "a" and "result__a" in css and len(self.results) < self.max_results:
            self._active = {"title": "", "url": _decode_search_url(attr.get("href", "")), "snippet": ""}
            self._capture_title = True
            return
        if "result__snippet" in css and self.results:
            self._capture_snippet_index = len(self.results) - 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title and self._active is not None:
            title = _clean_text(self._active.get("title", ""))
            url = self._active.get("url", "")
            if title and url and _is_public_http_url(url):
                self.results.append({"title": title, "url": url, "snippet": ""})
            self._active = None
            self._capture_title = False
        if self._capture_snippet_index is not None and tag in {"a", "div", "span"}:
            self._capture_snippet_index = None

    def handle_data(self, data: str) -> None:
        if self._capture_title and self._active is not None:
            self._active["title"] = (self._active.get("title", "") + " " + data).strip()
        elif self._capture_snippet_index is not None and self._capture_snippet_index < len(self.results):
            current = self.results[self._capture_snippet_index].get("snippet", "")
            self.results[self._capture_snippet_index]["snippet"] = _clean_text(f"{current} {data}")


class _BingHTMLParser(HTMLParser):
    def __init__(self, *, max_results: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_results = max_results
        self.results: list[dict[str, str]] = []
        self._active: dict[str, str] | None = None
        self._inside_h2 = False
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        css = attr.get("class", "")
        if tag == "li" and "b_algo" in css and len(self.results) < self.max_results:
            self._active = {"title": "", "url": "", "snippet": ""}
            return
        if self._active is not None and tag == "h2":
            self._inside_h2 = True
            return
        if self._active is not None and self._inside_h2 and tag == "a" and not self._active.get("url"):
            url = _decode_search_url(attr.get("href", ""))
            if _is_public_http_url(url):
                self._active["url"] = url
                self._capture_title = True
            return
        if self._active is not None and tag == "p":
            self._capture_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._capture_title = False
        if tag == "h2":
            self._inside_h2 = False
            self._capture_title = False
        if tag == "p":
            self._capture_snippet = False
        if tag == "li" and self._active is not None:
            title = _clean_text(self._active.get("title", ""))
            url = self._active.get("url", "")
            snippet = _clean_text(self._active.get("snippet", ""))
            if title and url and _is_public_http_url(url):
                self.results.append({"title": title, "url": url, "snippet": snippet})
            self._active = None
            self._inside_h2 = False
            self._capture_title = False
            self._capture_snippet = False

    def handle_data(self, data: str) -> None:
        if self._active is None:
            return
        if self._capture_title:
            self._active["title"] = _clean_text(f"{self._active.get('title', '')} {data}")
        elif self._capture_snippet:
            self._active["snippet"] = _clean_text(f"{self._active.get('snippet', '')} {data}")


def _clean_text(value: str) -> str:
    return " ".join(unescape(value).split())


def _decode_search_url(value: str) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return unquote(query["uddg"][0])
    if parsed.netloc.endswith("bing.com") and "u" in query and query["u"]:
        decoded = _decode_bing_redirect(query["u"][0])
        if decoded:
            return decoded
    if parsed.scheme in {"http", "https"}:
        return value
    return ""


def _decode_bing_redirect(value: str) -> str:
    token = value[2:] if value.startswith("a1") else value
    padding = "=" * (-len(token) % 4)
    try:
        return base64.urlsafe_b64decode(f"{token}{padding}").decode("utf-8", errors="replace")
    except Exception:
        return ""


def _is_public_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _infer_parser_type(endpoint: str) -> str:
    host = urlparse(endpoint).netloc.casefold()
    if "bing." in host:
        return "bing"
    return "duckduckgo"


def _build_search_url(endpoint: str, query: str) -> str:
    encoded = quote_plus(query)
    if "{query}" in endpoint:
        return endpoint.replace("{query}", encoded)
    separator = "&" if "?" in endpoint else "?"
    return f"{endpoint}{separator}q={encoded}"


class WebSearchProviderService:
    """Configurable public web-search provider facade.

    Unit tests should use the deterministic fake provider. Real web mechanisms can be
    added behind the same interface without changing ChatService.
    """

    def __init__(self, config: dict[str, object] | None = None) -> None:
        self.config = config or load_yaml_file(
            PATHS.config_root / "providers" / "web_search.yaml",
            critical=False,
            root=PATHS.config_root / "providers",
        )

    def search(self, query: str, max_results: int | None = None, freshness: str | None = None) -> WebSearchResult:
        searched_at = _now_iso()
        if not bool(self.config.get("enabled", False)):
            return WebSearchResult(
                status="capability_missing",
                query=query,
                provider_id=str(self.config.get("provider_id", "web_search")),
                reason_code="web_search_provider_disabled",
                warnings=["WEB_SEARCH_DISABLED", "web_search_provider_disabled"],
                searched_at=searched_at,
            )

        provider_type = str(self.config.get("provider_type", "disabled"))
        provider_id = str(self.config.get("provider_id", provider_type))
        limit = max_results or int(self.config.get("max_results", 3) or 3)
        if provider_type in {"fake", "local_stub"}:
            source = WebSearchSource(
                title=f"Resultado publico para: {query[:80]}",
                url=f"https://example.com/search?q={quote_plus(query)}",
                snippet=(
                    "Fonte deterministica de teste para validar o fluxo Web/Search. "
                    "Configure um provider HTTP/browser real para respostas factuais de producao."
                ),
                source_name=provider_id,
                retrieved_at=searched_at,
                reliability_hint="test_provider_not_public_fact_authority",
            )
            return WebSearchResult(
                status="ready",
                query=query,
                provider_id=provider_id,
                results=[source][:limit],
                warnings=["web_search_fake_provider"],
                source_count=1,
                searched_at=searched_at,
            )
        if provider_type == "browser_search":
            return self._browser_search(query, provider_id=provider_id, max_results=limit, searched_at=searched_at)

        return WebSearchResult(
            status="capability_missing",
            query=query,
            provider_id=provider_id,
            reason_code="web_search_provider_type_not_implemented",
            warnings=["WEB_SEARCH_DISABLED", "web_search_provider_type_not_implemented"],
            searched_at=searched_at,
        )

    def _browser_search(self, query: str, *, provider_id: str, max_results: int, searched_at: str) -> WebSearchResult:
        timeout = float(self.config.get("timeout_seconds", 10) or 10)
        search_query = self._normalize_query(query)
        normalization_warnings = ["web_search_query_normalized"] if search_query != query else []
        backend_results: list[str] = []
        backend_errors: list[str] = []
        for backend in self._browser_backends():
            backend_id = str(backend.get("provider_id") or backend.get("name") or provider_id)
            endpoint = str(backend.get("search_endpoint") or backend.get("endpoint") or "")
            if not endpoint:
                backend_results.append(f"{backend_id}:missing_endpoint")
                continue
            try:
                html = self._fetch_text(_build_search_url(endpoint, search_query), timeout=timeout)
            except TimeoutError:
                backend_results.append(f"{backend_id}:timeout")
                continue
            except (HTTPError, URLError, OSError) as exc:
                backend_results.append(f"{backend_id}:failed")
                backend_errors.append(f"{backend_id}:{self._sanitize_error(exc)}")
                continue

            sources = self._parse_browser_sources(
                html,
                parser_type=str(backend.get("parser") or backend.get("type") or _infer_parser_type(endpoint)),
                source_name=backend_id,
                query=search_query,
                max_results=max_results,
                searched_at=searched_at,
            )
            if sources:
                return WebSearchResult(
                    status="ready",
                    query=query,
                    provider_id=provider_id,
                    results=sources,
                    warnings=[*normalization_warnings, *backend_results],
                    source_count=len(sources),
                    searched_at=searched_at,
                )
            backend_results.append(f"{backend_id}:no_sources")
        wiki_sources = self._wikipedia_fallback_sources(search_query, max_results=max_results, searched_at=searched_at)
        if wiki_sources:
            return WebSearchResult(
                status="ready",
                query=query,
                provider_id=provider_id,
                results=wiki_sources,
                warnings=[*normalization_warnings, *backend_results, "wikipedia_fallback_used"],
                source_count=len(wiki_sources),
                searched_at=searched_at,
            )
        if any(item.endswith(":timeout") for item in backend_results) and not backend_errors:
            return WebSearchResult(
                status="timeout",
                query=query,
                provider_id=provider_id,
                reason_code="web_search_provider_timeout",
                warnings=[*normalization_warnings, "web_search_provider_timeout", *backend_results],
                searched_at=searched_at,
            )
        return WebSearchResult(
            status="failed",
            query=query,
            provider_id=provider_id,
            reason_code="web_search_no_sources" if not backend_errors else "web_search_provider_failed",
            warnings=[*normalization_warnings, "web_search_no_sources", *backend_results],
            errors=backend_errors,
            searched_at=searched_at,
        )

    def _normalize_query(self, query: str) -> str:
        policy = self.config.get("query_normalization")
        if not isinstance(policy, dict) or not bool(policy.get("enabled", False)):
            return query
        stopwords = {self._fold(str(item)) for item in policy.get("stopwords", []) if str(item).strip()}
        tokens = self._word_tokens(query)
        kept = [token for token in tokens if self._fold(token) not in stopwords and not self._fold(token).isdigit()]
        min_terms = int(policy.get("min_terms", 2) or 2)
        if len(kept) < min_terms:
            return query
        return " ".join(kept)

    def _browser_backends(self) -> list[dict[str, object]]:
        backends = self.config.get("browser_backends")
        if isinstance(backends, list):
            return [backend for backend in backends if isinstance(backend, dict)]
        return [
            {
                "provider_id": self.config.get("provider_id", "browser_web_search"),
                "search_endpoint": self.config.get("search_endpoint", "https://duckduckgo.com/html/"),
                "parser": self.config.get("parser"),
            }
        ]

    def _parse_browser_sources(
        self,
        html: str,
        *,
        parser_type: str,
        source_name: str,
        query: str,
        max_results: int,
        searched_at: str,
    ) -> list[WebSearchSource]:
        parser: _DuckDuckGoHTMLParser | _BingHTMLParser
        parse_limit = max(max_results, max_results * 4)
        if parser_type == "bing":
            parser = _BingHTMLParser(max_results=parse_limit)
        else:
            parser = _DuckDuckGoHTMLParser(max_results=parse_limit)
        parser.feed(html)
        sources = [
            WebSearchSource(
                title=item["title"],
                url=item["url"],
                snippet=item.get("snippet") or "Resultado encontrado por busca publica.",
                source_name=source_name,
                retrieved_at=searched_at,
                reliability_hint="public_web_search_result",
            )
            for item in parser.results[:parse_limit]
        ]
        return self._relevant_sources(query, sources)[:max_results]

    def _rank_sources(self, query: str, sources: list[WebSearchSource]) -> list[WebSearchSource]:
        query_terms = {self._fold(token) for token in self._word_tokens(query)}
        if not query_terms:
            return sources

        def score(source: WebSearchSource) -> int:
            haystack = self._fold(f"{source.title} {source.snippet} {source.url}")
            return sum(1 for term in query_terms if term in haystack)

        return sorted(sources, key=score, reverse=True)

    def _relevant_sources(self, query: str, sources: list[WebSearchSource]) -> list[WebSearchSource]:
        query_terms = self._informative_terms(query)
        if not query_terms:
            return sources
        minimum = min(len(query_terms), max(1, int(self.config.get("semantic_min_overlap", 2) or 2)))
        return [
            source
            for source in self._rank_sources(query, sources)
            if self._source_overlap_score(source, query_terms) >= minimum
        ]

    def _informative_terms(self, query: str) -> set[str]:
        policy = self.config.get("query_normalization")
        stopwords: set[str] = set()
        if isinstance(policy, dict):
            stopwords = {self._fold(str(item)) for item in policy.get("stopwords", []) if str(item).strip()}
        terms: set[str] = set()
        for token in self._word_tokens(query):
            folded = self._fold(token)
            if folded and folded not in stopwords and not folded.isdigit():
                terms.add(folded)
        return terms

    def _source_overlap_score(self, source: WebSearchSource, query_terms: set[str]) -> int:
        haystack = self._fold(f"{source.title} {source.snippet} {source.url}")
        return sum(1 for term in query_terms if term in haystack)

    def _fold(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.casefold())
        return "".join(char for char in normalized if not unicodedata.combining(char))

    def _word_tokens(self, value: str) -> list[str]:
        return [match.group(0) for match in re.finditer(r"\w+", value, flags=re.UNICODE)]

    def _wikipedia_fallback_sources(self, query: str, *, max_results: int, searched_at: str) -> list[WebSearchSource]:
        if not bool(self.config.get("wikipedia_fallback_enabled", False)):
            return []
        endpoint = "https://pt.wikipedia.org/w/api.php?action=opensearch&limit={limit}&namespace=0&format=json&search={{query}}".format(limit=max(max_results, 1))
        try:
            payload = json.loads(self._fetch_text(_build_search_url(endpoint, query), timeout=float(self.config.get("timeout_seconds", 10) or 10)))
        except Exception:
            return []
        if not isinstance(payload, list) or len(payload) < 4:
            return []
        titles = payload[1] if isinstance(payload[1], list) else []
        descriptions = payload[2] if isinstance(payload[2], list) else []
        urls = payload[3] if isinstance(payload[3], list) else []
        sources: list[WebSearchSource] = []
        for index, title in enumerate(titles[:max_results]):
            url_value = str(urls[index]) if index < len(urls) else ""
            if not _is_public_http_url(url_value):
                continue
            description = str(descriptions[index]) if index < len(descriptions) and descriptions[index] else "Fonte enciclopedica publica encontrada para a consulta."
            sources.append(
                WebSearchSource(
                    title=str(title),
                    url=url_value,
                    snippet=description,
                    source_name="wikipedia_opensearch",
                    retrieved_at=searched_at,
                    reliability_hint="public_encyclopedia_fallback",
                )
            )
        return self._relevant_sources(query, sources)

    def _fetch_text(self, url: str, *, timeout: float) -> str:
        request = Request(
            url,
            headers={
                "User-Agent": str(self.config.get("user_agent", "AIpinhoWebSearch/1.0 (+local-governed-agent)")),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def _sanitize_error(self, exc: BaseException) -> str:
        message = str(exc)
        if len(message) > 300:
            message = message[:300] + "..."
        return message

    def status(self) -> dict[str, object]:
        return {
            "status": "ok" if bool(self.config.get("enabled", False)) else "disabled",
            "provider_id": self.config.get("provider_id", "web_search"),
            "provider_type": self.config.get("provider_type", "disabled"),
            "require_sources": bool(self.config.get("require_sources", True)),
        }
