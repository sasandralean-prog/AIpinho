from __future__ import annotations

from aipinho.services.web_search_provider_service import WebSearchProviderService


def test_browser_search_provider_parses_sources_without_network(monkeypatch):
    provider = WebSearchProviderService(
        config={
            "enabled": True,
            "provider_id": "browser_test",
            "provider_type": "browser_search",
            "max_results": 2,
        }
    )

    def fake_fetch(url: str, *, timeout: float) -> str:
        assert "duckduckgo.com/html/" in url
        assert timeout == 10
        return """
        <html>
          <body>
            <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.org%2Fgovernadores">
              Governadores do Rio de Janeiro
            </a>
            <a class="result__snippet">Lista historica de governadores.</a>
            <a class="result__a" href="https://example.org/rj-atual">
              Governador atual do RJ
            </a>
            <a class="result__snippet">Fonte publica sobre cargo atual.</a>
          </body>
        </html>
        """

    monkeypatch.setattr(provider, "_fetch_text", fake_fetch)

    result = provider.search("Quem e o atual governador do Rio de Janeiro?", max_results=2)

    assert result.status == "ready"
    assert result.provider_id == "browser_test"
    assert result.source_count == 2
    assert result.results[0].url == "https://example.org/governadores"
    assert result.results[0].title == "Governadores do Rio de Janeiro"
    assert result.results[0].snippet == "Lista historica de governadores."
    assert result.results[1].url == "https://example.org/rj-atual"


def test_browser_search_provider_failure_is_structured(monkeypatch):
    provider = WebSearchProviderService(
        config={
            "enabled": True,
            "provider_id": "browser_test",
            "provider_type": "browser_search",
        }
    )

    def fake_fetch(url: str, *, timeout: float) -> str:
        raise OSError("network down")

    monkeypatch.setattr(provider, "_fetch_text", fake_fetch)

    result = provider.search("Qual a versao atual do Kotlin?", max_results=2)

    assert result.status == "failed"
    assert result.reason_code == "web_search_provider_failed"
    assert result.errors == ["browser_test:network down"]


def test_browser_search_provider_no_sources_is_structured(monkeypatch):
    provider = WebSearchProviderService(
        config={
            "enabled": True,
            "provider_id": "browser_test",
            "provider_type": "browser_search",
        }
    )
    monkeypatch.setattr(provider, "_fetch_text", lambda url, *, timeout: "<html><body>sem resultados</body></html>")

    result = provider.search("noticias recentes sobre Android Studio", max_results=2)

    assert result.status == "failed"
    assert result.reason_code == "web_search_no_sources"


def test_browser_search_provider_uses_configured_fallback_backend(monkeypatch):
    provider = WebSearchProviderService(
        config={
            "enabled": True,
            "provider_id": "browser_test",
            "provider_type": "browser_search",
            "browser_backends": [
                {
                    "provider_id": "duckduckgo_test",
                    "search_endpoint": "https://duckduckgo.com/html/",
                    "parser": "duckduckgo",
                },
                {
                    "provider_id": "bing_test",
                    "search_endpoint": "https://www.bing.com/search",
                    "parser": "bing",
                },
            ],
        }
    )

    def fake_fetch(url: str, *, timeout: float) -> str:
        if "duckduckgo.com" in url:
            return "<html><body>anomaly page without public results</body></html>"
        return """
        <html>
          <body>
            <li class="b_algo">
              <h2><a href="https://example.org/kotlin">Versao atual do Kotlin</a></h2>
              <p>Fonte publica sobre versoes do Kotlin.</p>
            </li>
          </body>
        </html>
        """

    monkeypatch.setattr(provider, "_fetch_text", fake_fetch)

    result = provider.search("Qual a versao atual do Kotlin?", max_results=2)

    assert result.status == "ready"
    assert result.source_count == 1
    assert result.results[0].source_name == "bing_test"
    assert result.results[0].title == "Versao atual do Kotlin"
    assert "duckduckgo_test:no_sources" in result.warnings


def test_browser_search_provider_normalizes_query_from_config(monkeypatch):
    provider = WebSearchProviderService(
        config={
            "enabled": True,
            "provider_id": "browser_test",
            "provider_type": "browser_search",
            "search_endpoint": "https://example.org/search",
            "parser": "bing",
            "query_normalization": {
                "enabled": True,
                "min_terms": 2,
                "stopwords": ["qual", "e", "o", "atual", "do"],
            },
        }
    )

    def fake_fetch(url: str, *, timeout: float) -> str:
        assert "qual" not in url.casefold()
        assert "atual" not in url.casefold()
        assert "status" in url.casefold()
        assert "framework" in url.casefold()
        return """
        <html>
          <body>
            <li class="b_algo">
              <h2><a href="https://example.org/framework">Status do framework</a></h2>
              <p>Fonte publica sobre o framework.</p>
            </li>
          </body>
        </html>
        """

    monkeypatch.setattr(provider, "_fetch_text", fake_fetch)

    result = provider.search("Qual e o status atual do framework?", max_results=1)

    assert result.status == "ready"
    assert "web_search_query_normalized" in result.warnings


def test_browser_search_provider_ranks_sources_by_query_overlap(monkeypatch):
    provider = WebSearchProviderService(
        config={
            "enabled": True,
            "provider_id": "browser_test",
            "provider_type": "browser_search",
            "search_endpoint": "https://example.org/search",
            "parser": "bing",
        }
    )
    monkeypatch.setattr(
        provider,
        "_fetch_text",
        lambda url, *, timeout: """
        <html>
          <body>
            <li class="b_algo">
              <h2><a href="https://example.org/random">Resultado amplo</a></h2>
              <p>Texto generico.</p>
            </li>
            <li class="b_algo">
              <h2><a href="https://example.org/framework-status">Status do framework</a></h2>
              <p>Fonte publica sobre status e framework.</p>
            </li>
          </body>
        </html>
        """,
    )

    result = provider.search("status framework", max_results=1)

    assert result.status == "ready"
    assert result.results[0].url == "https://example.org/framework-status"
