from aipinho.schemas.web_search import WebSearchSource
from aipinho.services.web_search_summary_service import WebSearchSummaryService


def _source(title: str, snippet: str) -> WebSearchSource:
    return WebSearchSource(
        title=title,
        url="https://example.com/source",
        snippet=snippet,
        source_name="test",
        retrieved_at="2026-06-18T00:00:00+00:00",
    )


def test_web_search_summary_synthesizes_provider_snippets():
    summary = WebSearchSummaryService().summarize(
        query="noticias recentes sobre Android Studio",
        sources=[
            _source(
                "Android Studio release notes",
                "As notas oficiais descrevem correcoes no editor, melhorias no build e atualizacoes de compatibilidade.",
            ),
            _source(
                "Android Developers Blog",
                "O blog destaca mudancas de produtividade e ajustes para fluxos de desenvolvimento Android.",
            ),
        ],
    )

    assert "correcoes no editor" in summary.text
    assert "produtividade" in summary.text
    assert "https://example.com" not in summary.text


def test_web_search_summary_is_honest_when_snippets_are_missing():
    summary = WebSearchSummaryService().summarize(
        query="pergunta publica",
        sources=[_source("Fonte sem trecho", "   ")],
    )

    assert "trechos curtos" in summary.text
    assert "web_summary_limited_to_provider_snippets" in summary.warnings
