from aipinho.services.context.context_core import ContextConflictDetector
from tests.unit.context_test_helpers import candidate

def test_conflict_stale_memory_vs_event():
    mem=candidate(layer='curated_memory',source_type='curated_memory',freshness='stale'); ev=candidate(layer='active_task',source_type='event_summary',source_id='message_received',cited=False)
    assert ContextConflictDetector().detect([mem,ev])
