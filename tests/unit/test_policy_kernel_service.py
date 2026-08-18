from aipinho.schemas.intent.intent_map import IntentSummary
from aipinho.schemas.policy.policy_decision import PolicyResolveRequest, RoleInput, UserConstraints, WorkspaceInput
from aipinho.schemas.tasks.task_contract import TaskContractInput
from aipinho.services.policy_kernel.policy_kernel_service import PolicyKernelService


def make_request(intent_type="conversation", task_type="conversation", actions=None, read_only=True, workspace=None, role="planner", requires_task=False, requires_workspace=False, constraints=None):
    return PolicyResolveRequest(
        intent=IntentSummary(intent_type=intent_type, requires_task=requires_task, requires_workspace=requires_workspace, risk_level="low", confidence=1.0),
        task=TaskContractInput(task_type=task_type, requested_actions=actions or [], read_only=read_only),
        workspace=WorkspaceInput(path=workspace, declared=workspace is not None),
        role=RoleInput(role_id=role),
        user_constraints=constraints or UserConstraints(),
    )


def test_conversation_allowed_without_task_or_tools():
    decision = PolicyKernelService().resolve(make_request())

    assert decision.status == "allowed"
    assert decision.contract_type == "conversation"
    assert decision.allowed_actions == []
    assert decision.approval_required_for == []
    assert decision.safe_to_execute is False


def test_readonly_analysis_allows_read_and_denies_writes_by_contract():
    request = make_request(
        intent_type="readonly_analysis",
        task_type="readonly_analysis",
        actions=["read_file"],
        workspace="C:\\Dev\\AIpinho",
        role="executor",
        requires_task=True,
        requires_workspace=True,
        read_only=True,
    )

    decision = PolicyKernelService().resolve(request)

    assert decision.status == "allowed"
    assert "read_files" in decision.allowed_actions
    assert "write_files" in decision.denied_actions
    assert "apply_patch" in decision.denied_actions
    assert decision.approval_required_for == []
    assert decision.safe_to_execute is True


def test_artifact_generation_needs_write_approval():
    request = make_request(
        intent_type="artifact_generation",
        task_type="artifact_generation",
        actions=["write_files"],
        workspace="C:\\Dev\\AIpinho",
        role="artifact_writer",
        requires_task=True,
        requires_workspace=True,
        read_only=False,
    )

    decision = PolicyKernelService().resolve(request)

    assert decision.status == "needs_approval"
    assert "write_files" in decision.approval_required_for
    assert "apply_patch" in decision.denied_actions
    assert decision.safe_to_preview is True
    assert decision.safe_to_execute is False


def test_patch_request_splits_preview_and_apply():
    request = make_request(
        intent_type="patch_request",
        task_type="patch_request",
        actions=["patch_preview", "apply_patch"],
        workspace="C:\\Dev\\AIpinho",
        role="executor",
        requires_task=True,
        requires_workspace=True,
        read_only=False,
    )

    decision = PolicyKernelService().resolve(request)

    assert decision.status == "needs_approval"
    assert "patch_preview" in decision.allowed_actions
    assert "apply_patch" in decision.approval_required_for
    assert decision.safe_to_execute is False
    assert any(item.stage == "approval_policy" for item in decision.trace)


def test_unknown_action_is_denied():
    request = make_request(actions=["teleport_files"], workspace="C:\\Dev\\AIpinho", role="executor")

    decision = PolicyKernelService().resolve(request)

    assert decision.status == "denied"
    assert "teleport_files" in decision.denied_actions
    assert any(violation.code == "unknown_action" for violation in decision.violations)