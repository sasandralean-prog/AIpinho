from aipinho.services.context.context_core import ContextKernelService
from tests.unit.context_test_helpers import request, candidate

def test_kernel_preview_build_and_trace():
    service=ContextKernelService(); req=request(candidates=[candidate()])
    preview=service.preview(req); assert preview['status']=='ok'; assert preview['bundle']['items']
    built=service.build(req); assert built.status=='ok'; assert built.bundle.trace_id

def test_kernel_unknown_purpose_blocked():
    result=ContextKernelService().preview(request(purpose='ghost'))
    assert result['status']=='blocked'
