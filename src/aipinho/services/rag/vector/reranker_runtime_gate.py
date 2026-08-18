from __future__ import annotations

from aipinho.services.models.model_doctor_service import ModelDoctorService
from aipinho.services.models.model_health_service import ModelHealthService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.rag.vector.config import rag_config


class RerankerRuntimeGate:
    def __init__(self) -> None:
        self.config = rag_config("reranker_policy.yaml")
        self.registry = ModelRegistryService()
        self.health = ModelHealthService(registry=self.registry)
        self.doctor = ModelDoctorService(registry=self.registry)

    def decide(self, model_id: str | None = None) -> dict[str, object]:
        policy = self.config.get("reranker", {}) if isinstance(self.config.get("reranker", {}), dict) else {}
        selected = model_id or str(policy.get("model_id", "qwen3_reranker_4b_q5_k_m"))
        blocked: list[str] = []
        warnings: list[str] = []
        model = self.registry.get_runtime_model(selected)
        if model is None:
            blocked.append("reranker_model_not_registered")
        elif model.provider_id != "llama_cpp_reranker" or "rerank" not in model.capabilities:
            blocked.append("model_not_reranker_capable")
        if model is not None:
            health = self.health.health(model.model_id)
            if health is None or health.status == "unknown":
                self.doctor.run_for_model(model.model_id)
                health = self.health.health(model.model_id)
            if health and health.status == "blocked":
                blocked.extend(health.blocked_reasons or ["reranker_model_health_blocked"])
            if health and health.status == "degraded":
                warnings.extend(health.warnings)
        return {"allowed": not blocked, "status": "ok" if not blocked else "blocked", "model_id": selected, "warnings": list(dict.fromkeys(warnings)), "blocked_reasons": list(dict.fromkeys(blocked))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "reranker_runtime_gate", **self.decide()}
