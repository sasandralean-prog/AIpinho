from aipinho.services.context.context_core import ContextEvidenceValidator
from tests.unit.context_test_helpers import candidate

def test_evidence_present_missing_invalid_ocr():
    svc=ContextEvidenceValidator(); assert svc.validate('user_response',candidate())[0]
    assert not svc.validate('user_response',candidate(cited=False))[0]
    assert not svc.validate('ocr_analysis',candidate(layer='vision_ocr_context',source_type='ocr_text_block',metadata={'confidence':0.1},cited=False))[0]
