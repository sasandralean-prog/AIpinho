from aipinho.services.context.context_core import ContextLayerResolver

def test_layer_resolver_l0_l8_and_purpose_mismatch():
    svc=ContextLayerResolver(); layers=svc.layers(); assert 'current_message' in layers and 'vision_ocr_context' in layers
    assert 'debugger_eval_traces' not in svc.resolve('user_response')
