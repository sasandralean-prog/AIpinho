from aipinho.services.rag.citation_builder import CitationBuilder


def test_citation_builder_supports_all_governed_source_types():
    builder = CitationBuilder()
    types = ["file_line_range", "report_section", "task_result_field", "validation_finding", "patch_apply_field", "memory_id"]
    for citation_type in types:
        citation = builder.build(citation_type=citation_type, source_id="source", source_type="test", ref="ref", location="loc", excerpt="evidence")
        assert citation.source_ref.content_hash
        assert citation.citation_type == citation_type
