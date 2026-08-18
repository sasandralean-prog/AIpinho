from __future__ import annotations

from aipinho.schemas.prompts.prompt_assembly import PromptAssemblyRequest, PromptPreview
from aipinho.schemas.roles.effective_role_policy import EffectiveRolePolicy
from aipinho.schemas.roles.role_pass_input import RolePassInput
from aipinho.services.prompts.prompt_assembly_service import PromptAssemblyService


class RolePromptService:
    PURPOSE_MAP = {
        "planning": "task_preview",
        "explanation": "chat",
        "policy_explanation": "chat",
        "final_response": "chat",
        "validation": "task_preview",
        "supervision": "task_preview",
        "debug_trace": "chat",
        "artifact_preview": "task_preview",
    }

    def __init__(self, prompt_service: PromptAssemblyService | None = None) -> None:
        self.prompt_service = prompt_service or PromptAssemblyService()

    def preview(self, role_input: RolePassInput, effective_policy: EffectiveRolePolicy) -> PromptPreview:
        purpose = self.PURPOSE_MAP.get(role_input.purpose, role_input.purpose)
        if purpose not in {"chat", "project_report", "code_analysis", "self_analysis", "capability_explanation", "task_preview"}:
            purpose = "chat"
        return self.prompt_service.preview(
            PromptAssemblyRequest(
                purpose=purpose,  # type: ignore[arg-type]
                role_id=role_input.role_id,
                user_message=role_input.user_message,
                intent_map=role_input.intent_map,
                policy_decision=role_input.policy_decision,
                session_context={"session_id": role_input.session_id, "role_pass_id": role_input.pass_id},
                file_context_bundle=role_input.file_context_bundle,
                project_report=role_input.project_report,
                context_injection_plan_id=role_input.context_injection_plan_id,
                context_injection_plan=role_input.context_injection_plan,
                evidence=role_input.evidence,
                output_contract_type=effective_policy.output_contract,
                model_id=role_input.requested_model_id or "stub.default",
                include_trace=role_input.include_trace,
            )
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_prompt", "prompt_assembly": self.prompt_service.status()}
