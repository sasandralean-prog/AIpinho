from aipinho.schemas.governance.lifecycle import CanonicalPermission
from aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService


def test_approval_not_created_when_prompt_context_missing():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="",
        source_channel="unit",
        requested_actions=["write_files"],
        operation_type="project_generation",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_1",
        workspace_path=r"C:\Users\rafae\Documents\AIpinhoTestes",
        target_paths=[r"C:\Users\rafae\Documents\AIpinhoTestes\App"],
        context_ref="context_1",
        expected_outputs=["project_generation_result", "validation_result"],
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "revert"},
        plan_payload={"project_generation_plan": {"files_to_create": [{"path": r"C:\Users\rafae\Documents\AIpinhoTestes\App"}]}},
    )

    assert snapshot.policy.permission == CanonicalPermission.ASK
    assert snapshot.approval_gate.can_create_approval is False
    assert snapshot.approval_gate.reason_code.value == "APPROVAL_NOT_CREATED_PROMPT_CONTEXT_MISSING"


def test_write_approval_requires_context_target_outputs_and_validation():
    service = GovernanceLifecycleService()
    base = dict(
        user_text="Crie arquivos do projeto.",
        source_channel="unit",
        requested_actions=["write_files"],
        operation_type="project_generation",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_1",
        workspace_path=r"C:\Users\rafae\Documents\AIpinhoTestes",
        target_paths=[r"C:\Users\rafae\Documents\AIpinhoTestes\App"],
        expected_outputs=["project_generation_result", "validation_result"],
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "revert"},
        plan_payload={"project_generation_plan": {"files_to_create": [{"path": r"C:\Users\rafae\Documents\AIpinhoTestes\App"}]}},
    )

    assert service.evaluate(**base).approval_gate.reason_code.value == "PREVIEW_REJECTED_NO_CONTEXT_REF"
    assert service.evaluate(**{**base, "context_ref": "ctx", "target_paths": []}).approval_gate.reason_code.value == "APPROVAL_NOT_CREATED_NO_TARGET_FILES"
    assert service.evaluate(**{**base, "context_ref": "ctx", "expected_outputs": []}).approval_gate.reason_code.value == "APPROVAL_NOT_CREATED_NO_EXPECTED_OUTPUTS"
    assert service.evaluate(**{**base, "context_ref": "ctx", "validation_plan": None}).approval_gate.reason_code.value == "APPROVAL_NOT_CREATED_NO_VALIDATION_PLAN"


def test_task_run_never_blocks_prompt_context_missing_after_approval():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Crie arquivos do projeto.",
        source_channel="unit",
        requested_actions=["write_files"],
        operation_type="project_generation",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="plan_1",
        workspace_path=r"C:\Users\rafae\Documents\AIpinhoTestes",
        target_paths=[r"C:\Users\rafae\Documents\AIpinhoTestes\App"],
        context_ref="ctx",
        expected_outputs=["project_generation_result", "validation_result"],
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "revert"},
        plan_payload={"project_generation_plan": {"files_to_create": [{"path": r"C:\Users\rafae\Documents\AIpinhoTestes\App"}]}},
    )

    assert snapshot.approval_gate.can_create_approval is True
    assert snapshot.approval_gate.status == "pending_approval"
    assert snapshot.context_gate.reason_code.value == "none"
