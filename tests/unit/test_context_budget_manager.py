from aipinho.services.context.context_core import ContextBudgetManager
from tests.unit.context_test_helpers import candidate

def test_budget_preserves_priority_and_truncates_low():
    hi=candidate(source_id='hi',content='h'*90,priority=10); lo=candidate(source_id='lo',content='l'*90,priority=1)
    results,trunc=ContextBudgetManager().apply([hi,lo],'user_response',100)
    assert results[hi.candidate_id].admitted_chars==90; assert lo.candidate_id in trunc
