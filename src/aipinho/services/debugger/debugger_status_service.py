from __future__ import annotations

from aipinho.schemas.debugger.contracts import DebuggerStatus
from aipinho.services.debugger.debugger_policy_service import DebuggerPolicyService


class DebuggerStatusService:
    INSPECTORS = ["model_run", "role_run", "rag_run", "rag_ingestion", "context_plan", "memory_usage", "vision_run", "ocr_run", "patch_apply", "validation", "output_evaluation"]

    def __init__(self, policy: DebuggerPolicyService | None = None) -> None:
        self.policy = policy or DebuggerPolicyService()

    def status_model(self) -> DebuggerStatus:
        status = self.policy.status()
        return DebuggerStatus(inspectors=self.INSPECTORS, **{key: value for key, value in status.items() if key in DebuggerStatus.model_fields})

    def status(self) -> dict[str, object]:
        model = self.status_model()
        return {"status": "ok", **model.model_dump(), "context_kernel_enabled": True, "context_admission_owner": "context_kernel", "debugger_builds_final_context": False}
