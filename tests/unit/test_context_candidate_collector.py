from aipinho.services.context.context_core import ContextCandidateCollector
from tests.unit.context_test_helpers import request, candidate

def test_candidate_collector_adds_current_message_and_candidates():
    items=ContextCandidateCollector().collect(request(candidates=[candidate()]))
    assert items[0].source_type=='current_request'; assert len(items)==2
