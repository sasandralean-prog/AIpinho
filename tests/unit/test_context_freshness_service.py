from aipinho.services.context.context_core import ContextFreshnessService
from tests.unit.context_test_helpers import candidate

def test_fresh_stale_expired_superseded():
    svc=ContextFreshnessService(); assert svc.evaluate(candidate(freshness='fresh'))[0]=='fresh'
    assert svc.evaluate(candidate(freshness='stale'))[0]=='degraded'
    assert svc.evaluate(candidate(freshness='expired'))[0]=='rejected'
    assert svc.evaluate(candidate(freshness='superseded'))[0]=='rejected'
