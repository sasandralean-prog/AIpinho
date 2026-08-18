from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.integration.contracts import RAGMemoryStatus
from aipinho.utils.yaml_loader import inspect_yaml_file


class RAGMemoryStatusService:
    CONFIGS = (
        "rag_memory_policy.yaml",
        "context_admission_policy.yaml",
        "context_injection_policy.yaml",
        "context_budget_policy.yaml",
        "context_provenance_policy.yaml",
        "context_citation_map_policy.yaml",
        "context_conflict_policy.yaml",
        "context_freshness_policy.yaml",
        "memory_context_policy.yaml",
        "retrieval_context_policy.yaml",
        "context_usage_validation_policy.yaml",
        "context_usage_audit_policy.yaml",
    )

    def status(self) -> dict[str, object]:
        root = PATHS.config_root / "rag" / "integration"
        configs = {name: inspect_yaml_file(root / name, root=PATHS.project_root).__dict__ for name in self.CONFIGS}
        warnings = [f"{name}:{value.get('status')}" for name, value in configs.items() if value.get("status") != "ok"]
        return RAGMemoryStatus(status="degraded" if warnings else "ok", configs=configs, warnings=warnings).model_dump()
