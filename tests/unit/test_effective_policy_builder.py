from aipinho.schemas.intent.intent_map import IntentSummary
from aipinho.schemas.policy.policy_decision import PolicyResolveRequest, RoleInput, WorkspaceInput
from aipinho.schemas.tasks.task_contract import TaskContractInput
from aipinho.services.policy_kernel.policy_kernel_service import PolicyKernelService


def request_for(actions, *, workspace="C:\\Dev\\AIpinho", role="executor", read_only=False, task_type="readonly_analysis"):
    return PolicyResolveRequest(
        intent=IntentSummary(intent_type=task_type if task_type != "validation" else "readonly_analysis", requires_task=True, requires_workspace=True, confidence=1.0),
        task=TaskContractInput(task_type=task_type, requested_actions=actions, read_only=read_only),
        workspace=WorkspaceInput(path=workspace, declared=True),
        role=RoleInput(role_id=role),
    )


def test_denied_wins_for_forbidden_root():
    decision = PolicyKernelService().resolve(request_for(["read_files"], workspace="C:\\Windows\\System32"))

    assert decision.status == "denied"
    assert "read_files" in decision.denied_actions
    assert "forbidden_root" in [violation.code for violation in decision.violations]


def test_role_cannot_expand_read_only_contract():
    decision = PolicyKernelService().resolve(request_for(["write_files"], read_only=True))

    assert decision.status == "denied"
    assert "write_files" in decision.denied_actions
    assert decision.effective_policy.reasons["write_files"] == "read_only_or_no_write_constraint"


def test_approval_required_is_not_execution_allowed():
    decision = PolicyKernelService().resolve(request_for(["write_files"], role="artifact_writer", task_type="artifact_generation"))

    assert decision.status == "needs_approval"
    assert "write_files" in decision.approval_required_for
    assert decision.safe_to_execute is False


def test_default_deny_for_unknown_action():
    decision = PolicyKernelService().resolve(request_for(["unknown_future_action"]))

    assert decision.status == "denied"
    assert "unknown_future_action" in decision.denied_actions
