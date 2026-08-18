from __future__ import annotations

from aipinho.schemas.roles.role_model_binding import RoleModelStatus
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.services.roles.role_inference_policy_service import RoleInferencePolicyService
from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_model_run_store import RoleModelRunStore


class RoleModelStatusService:
    def __init__(self, bindings: RoleModelBindingService | None = None, policy: RoleInferencePolicyService | None = None, store: RoleModelRunStore | None = None) -> None:
        self.bindings = bindings or RoleModelBindingService()
        self.policy = policy or RoleInferencePolicyService()
        self.store = store or RoleModelRunStore()

    def status_model(self) -> RoleModelStatus:
        roles = [binding.model_dump() for binding in self.bindings.list_bindings()]
        policy_status = self.policy.status()
        return RoleModelStatus(
            enabled=True,
            mode="controlled_real_inference_per_role",
            chat_auto_role_inference=bool(policy_status.get("chat_auto_role_inference", False)),
            tool_calling_enabled=False,
            workspace_write_enabled=False,
            vision_runtime_enabled=bool(policy_status.get("vision_runtime_enabled", False)),
            ocr_runtime_enabled=bool(policy_status.get("ocr_runtime_enabled", False)),
            embedding_runtime_enabled=bool(policy_status.get("embedding_runtime_enabled", False)),
            reranker_runtime_enabled=bool(policy_status.get("reranker_runtime_enabled", False)),
            default_coding_role="coder",
            default_coding_model="qwen2_5_coder_7b_q4_k_m",
            large_models_manual_only=True,
            roles=roles,
        )

    def status(self) -> dict[str, object]:
        model = self.status_model()
        vector = VectorRAGStatusService().status()
        return {
            "status": "ok",
            "service": "role_model_status",
            **model.model_dump(),
            "runs": self.store.status().get("runs", 0),
            "embedding_runtime_enabled": bool(vector.get("embedding_runtime_enabled", False)),
            "reranker_runtime_enabled": bool(vector.get("reranker_runtime_enabled", False)),
            "embedding_model_role_binding_enabled": False,
            "reranker_model_role_binding_enabled": False,
        }
