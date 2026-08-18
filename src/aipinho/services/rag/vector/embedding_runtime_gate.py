from __future__ import annotations

from aipinho.services.models.model_doctor_service import ModelDoctorService
from aipinho.services.models.model_health_service import ModelHealthService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.rag.vector.config import rag_config


class EmbeddingRuntimeGate:
    def __init__(self) -> None:
        self.config = rag_config("embedding_policy.yaml")
        self.registry = ModelRegistryService()
        self.health = ModelHealthService(registry=self.registry)
        self.doctor = ModelDoctorService(registry=self.registry)

    def decide(self, model_id: str | None = None) -> dict[str, object]:
        policy = self.config.get("embedding", {}) if isinstance(self.config.get("embedding", {}), dict) else {}
        selected = model_id or str(policy.get("model_id", "qwen3_embedding_4b_q5_k_m"))
        blocked: list[str] = []
        warnings: list[str] = []
        model = self.registry.get_runtime_model(selected)
        if model is None:
            blocked.append("embedding_model_not_registered")
        elif model.provider_id != "llama_cpp_embedding" or "embedding" not in model.capabilities:
            blocked.append("model_not_embedding_capable")
        if model is not None:
            health = self.health.health(model.model_id)
            if health is None or health.status == "unknown":
                self.doctor.run_for_model(model.model_id)
                health = self.health.health(model.model_id)
            if health and health.status == "blocked":
                blocked.extend(health.blocked_reasons or ["embedding_model_health_blocked"])
            if health and health.status == "degraded":
                warnings.extend(health.warnings)
        return {"allowed": not blocked, "status": "ok" if not blocked else "blocked", "model_id": selected, "warnings": list(dict.fromkeys(warnings)), "blocked_reasons": list(dict.fromkeys(blocked))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "embedding_runtime_gate", **self.decide()}
