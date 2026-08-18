from aipinho.services.context.context_core import ContextKernelService, EventContextAdapter, ArtifactContextAdapter
from tests.unit.context_test_helpers import request

def test_context_with_known_unknown_events_and_artifacts():
    known=EventContextAdapter().candidate('message_received','known')
    unknown=EventContextAdapter().candidate('ghost_event','unknown')
    artifact=ArtifactContextAdapter().candidate('a1','artifact')
    result=ContextKernelService().admit(request(purpose='diagnosis',candidates=[known,unknown,artifact]))
    reasons=[r for d in result['decisions'] for r in d.get('reason_codes',[])]
    assert 'unknown_event_contract' in reasons
