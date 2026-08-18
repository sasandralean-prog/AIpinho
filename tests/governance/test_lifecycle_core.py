from aipinho.schemas.governance.lifecycle import CanonicalPermission, GovernanceLifecycleState, PreviewKind
from aipinho.schemas.runtime.runtime_truth import RuntimeTruth
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.governance.approval.canonical_approval_service import CanonicalApprovalService
from aipinho.services.governance.completion.completion_resolver import CanonicalCompletionResolver
from aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService
from aipinho.services.governance.policy.canonical_policy_service import CanonicalPolicyService
from aipinho.services.governance.speaker_truth.speaker_truth_service import CanonicalSpeakerTruthService


def _assert_readonly_planning(snapshot):
    assert snapshot.intent.intent_type != "approval_command"
    assert snapshot.intent.readonly is True
    assert snapshot.intent.side_effect_requested is False
    assert snapshot.intent.negative_constraints["write_forbidden"] is True
    assert snapshot.operation_contract.requested_actions == []
    assert snapshot.approval_gate.approval_id is None
    assert snapshot.task_run_id is None


def test_g6_readonly_planning_is_plan_only_not_approval():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Somente planejamento textual. Nao escrever arquivos. Classifique como product_planning_readonly.",
        source_channel="unit",
    )
    assert snapshot.intent.intent_type == "product_planning_readonly"
    assert snapshot.state == GovernanceLifecycleState.PLAN_ONLY_PREVIEW
    assert snapshot.policy.permission == CanonicalPermission.ALLOWED
    assert snapshot.approval_gate.required is False
    assert snapshot.execution_plan.preview_kind == PreviewKind.PLAN_ONLY
    assert not snapshot.operation_contract.requested_actions


def test_g8_policy_normalizes_needs_approval_to_ask():
    service = CanonicalPolicyService()
    assert service.normalize("needs_approval") == CanonicalPermission.ASK
    assert service.normalize("approval_required") == CanonicalPermission.ASK
    assert service.normalize("waiting_input") == CanonicalPermission.ASK
    assert service.normalize("blocked") == CanonicalPermission.DENIED


def test_g9_ask_without_executable_plan_does_not_create_approval():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Crie um projeto novo",
        source_channel="unit",
        requested_actions=["write_files"],
        operation_type="project_generation",
        explicit_policy_decisions=["ask"],
    )
    assert snapshot.policy.permission == CanonicalPermission.ASK
    assert snapshot.approval_gate.required is True
    assert snapshot.approval_gate.can_create_approval is False
    assert snapshot.approval_gate.status == "APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN"
    assert snapshot.state == GovernanceLifecycleState.PLAN_ONLY_PREVIEW


def test_g9_ask_with_executable_plan_creates_pending_approval_gate():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Crie um projeto novo",
        source_channel="unit",
        requested_actions=["write_files"],
        operation_type="project_generation",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="draft_1:project_generation_plan",
        expected_outputs=["project_generation_result", "validation_result"],
        workspace_path=r"C:\Users\rafae\Documents\AIpinhoTestes",
        target_paths=[r"C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo"],
        context_ref="context_unit",
        validation_plan={"checks": ["target_paths_match_preview"]},
        rollback_plan={"strategy": "revert_preview_targets"},
        plan_payload={"project_generation_plan": {"files_to_create": [{"path": r"C:\Users\rafae\Documents\AIpinhoTestes\ProjetoNovo"}]}},
    )
    assert snapshot.execution_plan.executable is True
    assert snapshot.execution_plan.preview_kind == PreviewKind.EXECUTABLE
    assert snapshot.approval_gate.required is True
    assert snapshot.approval_gate.can_create_approval is True
    assert snapshot.approval_gate.status == "pending_approval"
    assert snapshot.state == GovernanceLifecycleState.PENDING_APPROVAL


def test_g10_completion_fails_when_expected_outputs_missing():
    verdict = CanonicalCompletionResolver().resolve(
        ["patch_result", "validation_result"],
        {"patch_result": {"ok": True}},
        proposed_status="completed",
    )
    assert verdict.status == "incomplete"
    assert verdict.safe_to_report_success is False
    assert verdict.missing_outputs == ["validation_result"]


def test_g10_speaker_truth_blocks_success_without_completion_outputs():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Aplique um patch",
        source_channel="unit",
        requested_actions=["apply_patch"],
        operation_type="patch_request",
        explicit_policy_decisions=["allowed"],
        executable_plan_ref="draft_1:patch_plan",
        expected_outputs=["patch_result", "validation_result"],
        outputs={"patch_result": {"ok": True}},
        proposed_completion_status="completed",
    )
    assert snapshot.completion.status == "incomplete"
    assert snapshot.speaker_truth.can_claim_success is False
    assert "validated" in snapshot.speaker_truth.forbidden_claims


def test_g10_completion_success_allows_speaker_success():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Aplique um patch",
        source_channel="unit",
        requested_actions=["apply_patch"],
        operation_type="patch_request",
        explicit_policy_decisions=["allowed"],
        executable_plan_ref="draft_1:patch_plan",
        expected_outputs=["patch_result", "validation_result"],
        outputs={"patch_result": {"ok": True}, "validation_result": {"status": "passed"}},
        proposed_completion_status="completed",
    )
    assert snapshot.completion.safe_to_report_success is True
    assert snapshot.speaker_truth.can_claim_success is True
    assert snapshot.state == GovernanceLifecycleState.COMPLETED


def test_speaker_truth_maps_runtime_truth_missing_evidence_to_blocked_claims():
    truth = RuntimeTruth(
        truth_id="runtime_truth_unit",
        task_id="task_unit",
        task_run_id="run_unit",
        status="blocked",
        reason_code="completed_missing_required_evidence",
        safe_to_report_success=False,
        ui_status="blocked",
        speaker_truth_status="evidence_required",
        missing_evidence=["timeline", "validation_evidence"],
    )

    speaker_truth = CanonicalSpeakerTruthService().from_runtime_truth(truth)

    assert speaker_truth.can_claim_success is False
    assert "completed" in speaker_truth.forbidden_claims
    assert "missing_evidence:timeline" in speaker_truth.required_disclosures


def test_readonly_sapoandando_prompt_overrides_legacy_patch_signal():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            r'Diagnostico read-only do workspace "C:\Users\rafae\Documents\TestesIALocal\SapoAndando". '
            "Operar somente em modo read-only. Nao modificar arquivos. Nao criar artifact. "
            "Nao rodar patch. Nao executar build. Gere apenas diagnostico e preview textual futuro."
        ),
        source_channel="unit",
        requested_actions=["apply_patch"],
        operation_type="patch_request",
        explicit_policy_decisions=["allowed"],
    )

    assert snapshot.intent.readonly is True
    assert snapshot.intent.side_effect_requested is False
    assert snapshot.intent.negative_constraints["write_forbidden"] is True
    assert snapshot.operation_contract.operation_type == "workspace_analysis_readonly"
    assert snapshot.operation_contract.requested_actions == []
    assert snapshot.policy.allowed_actions == []
    assert snapshot.approval_gate.required is False
    assert snapshot.task_run_id is None


def test_readonly_governance_diagnostic_does_not_become_project_bootstrap():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "Diagnostico read-only da governanca. Analise os termos patch_or_write_request, "
            "project_bootstrap, filesystem_create_directory, create_directory e negative_constraints. "
            "Nao criar arquivos. Nao abrir ApprovalRequest. Nao executar nada."
        ),
        source_channel="unit",
        requested_actions=["create_directory"],
        operation_type="filesystem_create_directory",
        explicit_policy_decisions=["allowed"],
    )

    assert snapshot.intent.readonly is True
    assert snapshot.operation_contract.operation_type == "workspace_analysis_readonly"
    assert snapshot.operation_contract.requested_actions == []
    assert snapshot.policy.allowed_actions == []
    assert snapshot.approval_gate.approval_id is None
    assert snapshot.policy.permission == CanonicalPermission.ALLOWED


def test_planning_readonly_existing_good_case_stays_readonly():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "AIpinho - Fase 0A: somente planejamento textual. "
            "Isto NAO e pedido para criar grant, NAO e escrita, NAO e shell, "
            "NAO e ConfigChangeRequest. Classifique este pedido como product_planning_readonly."
        ),
        source_channel="unit",
    )

    assert snapshot.intent.intent_type == "product_planning_readonly"
    assert snapshot.intent.readonly is True
    assert snapshot.intent.negative_constraints["write_forbidden"] is True
    assert snapshot.intent.negative_constraints["approval_forbidden"] is True
    assert snapshot.operation_contract.requested_actions == []
    assert snapshot.approval_gate.approval_id is None


def test_formal_approval_command_routes_and_parse_target():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="APROVAR approval_123abc",
        source_channel="unit",
    )
    command = ChatApprovalCommandService().parse("APROVAR approval_123abc")

    assert snapshot.intent.intent_type == "approval_command"
    assert snapshot.operation_contract.operation_type == "approval_command"
    assert command is not None
    assert command.action == "approve"
    assert command.target_id == "approval_123abc"


def test_formal_deny_command_routes_and_parse_target():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="NEGAR approval_123abc",
        source_channel="unit",
    )
    command = ChatApprovalCommandService().parse("NEGAR approval_123abc")

    assert snapshot.intent.intent_type == "approval_command"
    assert snapshot.operation_contract.operation_type == "approval_command"
    assert command is not None
    assert command.action == "deny"
    assert command.target_id == "approval_123abc"


def test_formal_list_pending_approvals_routes_and_parses_list():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="LISTAR APPROVALS PENDENTES",
        source_channel="unit",
    )
    command = ChatApprovalCommandService().parse("LISTAR APPROVALS PENDENTES")

    assert snapshot.intent.intent_type == "approval_command"
    assert snapshot.operation_contract.operation_type == "approval_command"
    assert command is not None
    assert command.action == "list"
    assert command.scope == "pending"


def test_technical_prompt_with_approval_terms_is_not_approval_command():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "Objetivo: Analisar e preparar a correcao minima do projeto SapoAndando\n"
            "ApprovalRequest deve ser citado como conceito, nao como comando.\n"
            "approval_id deve permanecer None durante discovery.\n"
            "Nao criar approval. Comecar em read-only.\n"
            r"Workspace alvo: C:\Users\rafae\Documents\TestesIALocal\SapoAndando"
        ),
        source_channel="unit",
    )

    _assert_readonly_planning(snapshot)


def test_sentence_mentioning_approval_is_readonly_not_approval_command():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Nao crie ApprovalRequest ainda, apenas faca diagnostico read-only.",
        source_channel="unit",
    )

    _assert_readonly_planning(snapshot)


def test_aprovar_inside_instruction_is_not_approval_command():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Explique quando devo usar APROVAR approval_xxx, mas nao aprove nada agora.",
        source_channel="unit",
    )

    assert snapshot.intent.intent_type != "approval_command"
    assert snapshot.approval_gate.approval_id is None


def test_multiline_prompt_with_approval_mentions_is_not_approval_command():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=(
            "Objetivo: diagnosticar fluxo de approval\n"
            "Fase 1: read-only\n"
            "Regras: nao criar ApprovalRequest, nao aprovar approval_123abc\n"
            "Workspace: C:\\Dev\\AIpinho"
        ),
        source_channel="unit",
    )

    _assert_readonly_planning(snapshot)


def test_dangerous_request_without_plan_is_not_allowed():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="crie taskpreviee, aprovalrequest, grant shell e escrita em arquivos",
        source_channel="unit",
        requested_actions=["run_command"],
        operation_type="run_command",
        runtime_profile="shell_build_test",
        explicit_policy_decisions=["allowed"],
        expected_outputs=["command_result", "validation_result"],
    )

    assert snapshot.intent.side_effect_requested is True
    assert snapshot.policy.permission == CanonicalPermission.DENIED
    assert snapshot.policy.allowed_actions == []
    assert snapshot.policy.denied_actions == ["run_command"]
    assert snapshot.reason_code.value == "missing_executable_plan"
    assert snapshot.approval_gate.approval_id is None
    assert snapshot.state == GovernanceLifecycleState.BLOCKED
    assert snapshot.speaker_truth.can_claim_success is False


def test_shell_with_executable_plan_requires_approval_before_execution():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text=r'Execute "npm test" em "C:\Work\App".',
        source_channel="unit",
        requested_actions=["run_command"],
        operation_type="run_command",
        runtime_profile="shell_build_test",
        explicit_policy_decisions=["ask"],
        executable_plan_ref="draft_shell:command_plan",
        expected_outputs=["command_result", "validation_result"],
        workspace_path=r"C:\Work\App",
        target_paths=[r"C:\Work\App"],
        context_ref="context_shell",
        validation_plan={"checks": ["exit_code_zero"]},
        rollback_plan={"strategy": "no_write_shell"},
        plan_payload={"command_plan": {"argv": ["npm", "test"], "cwd": r"C:\Work\App"}},
    )

    assert snapshot.policy.permission == CanonicalPermission.ASK
    assert snapshot.policy.allowed_actions == []
    assert snapshot.policy.ask_actions == ["run_command"]
    assert snapshot.approval_gate.required is True
    assert snapshot.approval_gate.status == "pending_approval"
    assert snapshot.state == GovernanceLifecycleState.PENDING_APPROVAL


def test_blocked_task_completion_outputs_do_not_pass_validation_aggregate():
    snapshot = GovernanceLifecycleService().evaluate(
        user_text="Aplique um patch",
        source_channel="unit",
        requested_actions=["apply_patch"],
        operation_type="patch_request",
        explicit_policy_decisions=["allowed"],
        executable_plan_ref="draft_1:patch_plan",
        expected_outputs=["patch_result", "validation_result"],
        outputs={"patch_result": {"ok": True}},
        proposed_completion_status="blocked",
    )

    assert snapshot.completion.status == "blocked"
    assert snapshot.completion.safe_to_report_success is False
    assert "validation_result" in snapshot.completion.missing_outputs
    assert snapshot.speaker_truth.can_claim_success is False
