from aipinho.services.context.context_core import ContextPurposePolicyService

def test_purpose_known_unknown_budget_layers():
    svc=ContextPurposePolicyService(); assert svc.known('user_response'); assert not svc.known('ghost')
    assert 'governed_rag' in svc.allowed_layers('user_response'); assert svc.max_budget('user_response')>0
