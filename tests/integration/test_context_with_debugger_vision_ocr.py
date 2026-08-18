from aipinho.services.context.context_core import ContextKernelService, DebuggerContextAdapter, VisionOCRContextAdapter
from tests.unit.context_test_helpers import request

def test_debugger_vision_ocr_purpose_restrictions():
    dbg=DebuggerContextAdapter().candidate('t','trace')
    assert 'admitted' in {d['status'] for d in ContextKernelService().admit(request(purpose='diagnosis',candidates=[dbg]))['decisions']}
    assert 'rejected' in {d['status'] for d in ContextKernelService().admit(request(purpose='user_response',candidates=[dbg]))['decisions']}
    assert 'admitted' in {d['status'] for d in ContextKernelService().admit(request(purpose='vision_analysis',candidates=[VisionOCRContextAdapter().visual('v','img')]))['decisions']}
    assert 'rejected' in {d['status'] for d in ContextKernelService().admit(request(purpose='ocr_analysis',candidates=[VisionOCRContextAdapter().ocr('o','txt',0.1)]))['decisions']}
