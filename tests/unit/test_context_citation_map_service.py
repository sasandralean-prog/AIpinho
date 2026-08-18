from aipinho.services.rag.integration.context_citation_map_service import ContextCitationMapService
from tests.unit.rag_memory_test_helpers import admitted_retrieval


def test_every_context_item_is_mapped():
    admission = admitted_retrieval()
    citation_map = ContextCitationMapService().build(admission.admitted_items)
    assert citation_map.valid is True
    assert set(citation_map.item_to_citations) == {item.context_item_id for item in admission.admitted_items}


def test_missing_citation_blocks_item():
    admission = admitted_retrieval()
    admission.admitted_items[0].citation_ids = []
    citation_map = ContextCitationMapService().build(admission.admitted_items)
    assert citation_map.valid is False
    assert "citation_missing" in ",".join(citation_map.blocked_reasons)


def test_validation_rejects_incomplete_map():
    admission = admitted_retrieval()
    citation_map = ContextCitationMapService().build(admission.admitted_items)
    citation_map.item_to_citations = {}
    checked = ContextCitationMapService().validate(citation_map, admission.admitted_items)
    assert checked.valid is False
    assert "citation_map_incomplete" in checked.blocked_reasons

