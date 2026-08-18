from aipinho.services.context.context_core import ContextSourceAdmissionService
from tests.unit.context_test_helpers import candidate
from aipinho.schemas.context.contracts import ContextCandidate

def test_source_ref_required_and_blocked_source():
    svc=ContextSourceAdmissionService(); missing=ContextCandidate(layer='governed_rag',source_type='rag_chunk',summary='x')
    assert 'missing_source_ref' in svc.validate_source('user_response', missing)
    raw=candidate(source_type='raw_prompt'); raw.layer='chat_session'
    assert 'raw_context_blocked' in svc.validate_source('user_response', raw)
