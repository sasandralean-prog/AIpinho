from aipinho.schemas.intent.intent_map import IntentSummary
from aipinho.schemas.policy.effective_policy import EffectivePolicy
from aipinho.schemas.policy.policy_decision import PolicyDecision, PolicyResolveRequest
from aipinho.schemas.policy.policy_trace import PolicyTraceItem
from aipinho.schemas.tasks.task_contract import TaskContractPreview


def test_policy_resolve_request_schema_defaults():
    request = PolicyResolveRequest()

    assert request.intent.intent_type == "unknown"
    assert request.task.read_only is True
    assert request.role.role_id == "planner"


def test_policy_decision_schema_accepts_required_shape():
    decision = PolicyDecision(
        decision_id="policy_test",
        status="allowed",
        contract_type="conversation",
        effective_policy=EffectivePolicy(),
    )

    assert decision.status == "allowed"
    assert decision.safe_to_execute is False


def test_task_contract_preview_schema():
    preview = TaskContractPreview(
        contract_type="readonly_analysis",
        policy_decision_id="policy_test",
        requires_task=True,
        requires_workspace=True,
    )

    assert preview.safe_to_preview is False


def test_trace_schema():
    trace = PolicyTraceItem(
        stage="workspace_policy",
        rule="forbidden_root",
        decision="denied",
        reason="workspace_path_matches_protected_root",
        severity="critical",
        source="config/workspaces/protected_workspaces.yaml",
    )

    assert trace.severity == "critical"


def test_intent_schema_is_minimal_and_structured():
    intent = IntentSummary(intent_type="conversation", confidence=0.9)

    assert intent.intent_type == "conversation"
    assert intent.confidence == 0.9