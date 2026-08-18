from aipinho.schemas.roles.role_model_gate import RoleModelGateRequest
from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.schemas.roles.role_policy import RolePolicyRequest
from aipinho.services.roles.effective_role_policy_service import EffectiveRolePolicyService
from aipinho.services.roles.role_model_gate_service import RoleModelGateService
from aipinho.services.roles.role_pass_runner import RolePassRunner
from aipinho.services.roles.role_pipeline_service import RolePipelineService


def test_e2e_20_required_role_pipeline_cases():
    roles = RolePipelineService().status()
    assert roles["enabled"] is True
    assert roles["real_inference_auto_use"] is True
    assert roles["tools_enabled"] is False
    assert roles["write_enabled"] is False

    analyst = EffectiveRolePolicyService().resolve(RolePolicyRequest(role_id="analyst", policy_decision={"status": "allowed", "allowed_actions": ["read_files"], "denied_actions": ["write_files"]}))
    assert analyst.allowed is True and analyst.can_call_tools is False and analyst.output_contract == "json_findings"

    denied = EffectiveRolePolicyService().resolve(RolePolicyRequest(role_id="analyst", policy_decision={"status": "denied"}))
    assert denied.allowed is False and "policy_denied" in denied.blocked_reasons

    speaker = EffectiveRolePolicyService().resolve(RolePolicyRequest(role_id="speaker", policy_decision={"status": "allowed", "denied_actions": ["write_files"]}, task_contract={"requested_actions": ["write_files"]}))
    assert speaker.can_write is False and "write_files" in speaker.denied_actions

    stub_gate = RoleModelGateService().decide(RoleModelGateRequest(role_id="analyst", model_policy="stub_only", requested_model_id="stub.default", output_contract={"contract_type": "json_findings"}, safety_envelope={"rules": ["no_tools"]}))
    assert stub_gate.allowed is True and stub_gate.real_inference is False

    real_gate = RoleModelGateService().decide(RoleModelGateRequest(role_id="analyst", model_policy="stub_only", requested_model_id="llama.local.placeholder", output_contract={"contract_type": "json_findings"}, safety_envelope={"rules": ["no_tools"]}, allow_real_inference=True, operator_confirmed=True))
    assert real_gate.allowed is False and "real_inference_not_allowed_by_role_policy" in real_gate.blocked_reasons

    supervisor = RolePassRunner().run(RolePassInput(role_id="supervisor", purpose="validation", policy_decision={"status": "allowed"}))
    assert supervisor.model_gate.status == "deterministic_only" and supervisor.output.source == "deterministic"

    speaker_pass = RolePassRunner().run(RolePassInput(role_id="speaker", user_message="Ola", policy_decision={"status": "allowed"}))
    assert speaker_pass.status == "completed" and speaker_pass.output.source == "stub"

    analyst_no_evidence = RolePassRunner().run(RolePassInput(role_id="analyst", purpose="code_analysis", policy_decision={"status": "allowed"}))
    assert analyst_no_evidence.status == "rejected"

    preview = RolePipelineService().preview_pipeline(RolePipelineRunRequest(pipeline_id="chat_basic", intent_map={"intent_type": "conversation"}, policy_decision={"status": "allowed"}))
    assert preview.status == "preview" and preview.final_output["model_invoked"] is False

    chat_run = RolePipelineService().run_pipeline(RolePipelineRunRequest(pipeline_id="chat_basic", user_message="Ola", intent_map={"intent_type": "conversation"}, policy_decision={"status": "allowed"}, model_mode="deterministic"))
    assert chat_run.status == "completed" and chat_run.final_output["real_inference"] is False

    missing = RolePipelineService().preview_pipeline(RolePipelineRunRequest(pipeline_id="readonly_project_report", intent_map={"intent_type": "readonly_analysis"}, policy_decision={"status": "allowed"}))
    assert missing.status == "needs_input"

    report = {"evidence": [{"evidence_id": "ev1", "path": "README.md"}]}
    readonly = RolePipelineService().run_pipeline(RolePipelineRunRequest(pipeline_id="readonly_project_report", intent_map={"intent_type": "readonly_analysis"}, policy_decision={"status": "allowed"}, project_report=report, evidence=[{"evidence_id": "ev1", "path": "README.md"}]))
    assert readonly.status in {"completed", "partial", "rejected"}
    assert readonly.final_output.get("write") is False

    manual_real_preview = RolePipelineService().preview_pipeline(RolePipelineRunRequest(pipeline_id="chat_basic", intent_map={"intent_type": "conversation"}, policy_decision={"status": "allowed"}, model_mode="manual_real", allow_real_inference=True, operator_confirmed=True))
    assert manual_real_preview.status == "preview"
    assert any(pass_item.model_gate and pass_item.model_gate.real_inference for pass_item in manual_real_preview.passes)

    assert all(p.model_gate is None or p.model_gate.real_inference is False for p in chat_run.passes)
    assert all(p.effective_policy is None or p.effective_policy.can_call_tools is False for p in chat_run.passes)
    assert all(p.effective_policy is None or p.effective_policy.can_write is False for p in chat_run.passes)
    assert all(p.effective_policy is None or p.effective_policy.can_patch is False for p in chat_run.passes)
    assert chat_run.trace
