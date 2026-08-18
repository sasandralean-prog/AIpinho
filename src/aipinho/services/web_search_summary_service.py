from __future__ import annotations

import re
from dataclasses import dataclass, field

from aipinho.schemas.web_search import WebSearchSource


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class WebSearchSummary:
    text: str
    warnings: list[str] = field(default_factory=list)


class WebSearchSummaryService:
    """Builds a grounded chat summary from web provider sources.

    This service does not browse, infer hidden facts, or call a model. It only
    turns provider-returned titles/snippets into a readable synthesis.
    """

    def summarize(self, *, query: str, sources: list[WebSearchSource]) -> WebSearchSummary:
        cleaned = [self._source_text(source) for source in sources]
        cleaned = [text for text in cleaned if text]
        if not cleaned:
            return WebSearchSummary(
                text=(
                    "A pesquisa retornou fontes, mas elas nao trouxeram trechos suficientes "
                    "para uma sintese confiavel. Consulte as fontes listadas para validar a resposta."
                ),
                warnings=["web_summary_insufficient_snippets"],
            )

        sentences = self._dedupe_sentences(cleaned)
        if not sentences:
            return WebSearchSummary(
                text=(
                    "A pesquisa encontrou fontes relacionadas, mas o conteudo retornado pelo provider "
                    "foi curto demais para resumir sem risco de inventar informacao."
                ),
                warnings=["web_summary_insufficient_snippets"],
            )

        selected = sentences[:4]
        summary = " ".join(selected)
        warnings: list[str] = []
        if len(sentences) <= 1 or len(summary) < 120:
            warnings.append("web_summary_limited_to_provider_snippets")
            summary = (
                "Com base nos trechos curtos retornados pelo provider: "
                f"{summary}"
            )
        return WebSearchSummary(text=summary, warnings=warnings)

    def _source_text(self, source: WebSearchSource) -> str:
        parts = [source.title, source.snippet]
        text = ". ".join(part.strip(" .") for part in parts if part and part.strip())
        return _SPACE_RE.sub(" ", text).strip()

    def _dedupe_sentences(self, source_texts: list[str]) -> list[str]:
        seen: set[str] = set()
        sentences: list[str] = []
        for text in source_texts:
            for sentence in _SENTENCE_SPLIT_RE.split(text):
                normalized = _SPACE_RE.sub(" ", sentence).strip(" -")
                if not normalized:
                    continue
                key = normalized.casefold()
                if key in seen:
                    continue
                seen.add(key)
                sentences.append(normalized if normalized.endswith((".", "!", "?")) else f"{normalized}.")
        return sentences
