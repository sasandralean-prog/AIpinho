from aipinho.services.context.context_core import ContextAdmissionServiceV2
from tests.unit.context_test_helpers import request, candidate

def test_admission_admitted_rejected_degraded_truncated_deduplicated():
    good=candidate(source_id='good',content='good cited'); no_cite=candidate(source_id='nocite',content='missing citation',cited=False); cand=candidate(source_id='cand',content='candidate trust',trust='candidate'); long=candidate(source_id='long',content='x'*500,priority=1)
    dup=candidate(source_id='good')
    decisions=ContextAdmissionServiceV2().admit(request(candidates=[good,no_cite,cand,long,dup],budget=100), [good,no_cite,cand,long,dup])
    statuses={d.status for d in decisions}
    assert 'admitted' in statuses and 'rejected' in statuses and 'degraded' in statuses and 'truncated' in statuses and 'deduplicated' in statuses
