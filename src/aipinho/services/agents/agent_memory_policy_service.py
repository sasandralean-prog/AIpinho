from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.memory import MemoryNamespaceInfo, MemoryPolicyEvaluation, MemoryRecord, MemorySearchRequest, MemoryWriteRequest
from aipinho.services.events.event_core import contains_secret
from aipinho.utils.yaml_loader import load_yaml_file


PRIVATE_NAMESPACE_BY_AGENT = {
    "aipinho": "memory:aipinho",
    "lucio": "memory:lucio",
    "codex": "memory:codex",
    "gemini": "memory:gemini",
}
PRIVATE_NAMESPACES = set(PRIVATE_NAMESPACE_BY_AGENT.values())


class AgentMemoryPolicyService:
    def __init__(self, path: Path | None = None, *, root: Path | None = None) -> None:
        self.root = root or PATHS.config_root
        self.path = path or self.root / "agents" / "memory_gateway_policy.yaml"

    def config(self) -> dict[str, Any]:
        return load_yaml_file(self.path, root=self.root)

    def namespaces(self) -> list[MemoryNamespaceInfo]:
        rows = self.config().get("namespaces", [])
        return [MemoryNamespaceInfo(**item) for item in rows]

    def evaluate_write(self, request: MemoryWriteRequest) -> MemoryPolicyEvaluation:
        if self._contains_blocked_sensitive(request.content_sanitized) or contains_secret(request.metadata_sanitized):
            return self._deny("memory_secret_blocked", "Memoria bloqueada: conteudo sensivel nao pode ser gravado.")
        if self._contains_chain_of_thought_marker(request.content_sanitized):
            return self._deny("memory_chain_of_thought_blocked", "Memoria bloqueada: raciocinio interno nao deve ser persistido.")
        if request.namespace in PRIVATE_NAMESPACES:
            owner = self.owner_for_namespace(request.namespace)
            if owner != request.agent_id:
                return self._deny("private_memory_cross_agent_denied", "Agente nao pode escrever na memoria privada de outro agente.")
            return MemoryPolicyEvaluation(decision="allow", reason_code="private_memory_write_allowed", human_reason="Escrita na memoria privada do proprio agente permitida.")
        if request.namespace == "memory:shared":
            if not request.evidence_refs and bool(self.config().get("require_evidence_for_shared", True)):
                return MemoryPolicyEvaluation(decision="candidate_only", reason_code="shared_memory_requires_evidence", human_reason="Shared memory sem evidencia vira candidate, nao memoria validada.")
            if request.validation_status == "validated" and request.metadata_sanitized.get("memory_review_accepted") is True:
                return MemoryPolicyEvaluation(decision="allow", reason_code="shared_memory_review_accepted", human_reason="Shared memory aceita por revisao explicita.")
            if request.validation_status == "validated" and self._auto_accept_shared():
                return MemoryPolicyEvaluation(decision="allow", reason_code="shared_memory_validated_allowed", human_reason="Shared memory validada com evidencia permitida.")
            return MemoryPolicyEvaluation(decision="candidate_only", reason_code="shared_memory_candidate_required", human_reason="Shared memory exige fluxo de candidate/validacao.")
        if request.namespace == "memory:security":
            return MemoryPolicyEvaluation(decision="require_validation", reason_code="security_memory_restricted", human_reason="Security memory exige validacao/policy.")
        if request.namespace in {"memory:project", "memory:regression", "memory:user_preferences"}:
            if request.namespace == "memory:project" and not (request.workspace_id or request.project_id):
                return MemoryPolicyEvaluation(decision="candidate_only", reason_code="project_memory_scope_required", human_reason="Project memory exige workspace_id ou project_id; salvo como candidate.")
            if request.namespace == "memory:regression" and not request.evidence_refs:
                return MemoryPolicyEvaluation(decision="candidate_only", reason_code="regression_memory_evidence_required", human_reason="Regression memory exige evidencia; salvo como candidate.")
            return MemoryPolicyEvaluation(decision="allow", reason_code="scoped_memory_write_allowed", human_reason="Memoria escopada permitida com metadados sanitizados.")
        return self._deny("memory_namespace_unknown", "Namespace de memoria desconhecido.")

    def can_read_record(self, agent_id: str, record: MemoryRecord) -> tuple[bool, list[str]]:
        warnings: list[str] = []
        if record.namespace in PRIVATE_NAMESPACES and self.owner_for_namespace(record.namespace) != agent_id:
            return False, ["private_memory_cross_agent_denied"]
        if record.namespace == "memory:security":
            return False, ["security_memory_restricted"]
        if record.validation_status == "contradicted":
            warnings.append("contradicted_memory_detected")
        if record.validation_status == "stale" or record.freshness == "stale":
            warnings.append("stale_memory_used")
        if record.confidence == "low":
            warnings.append("low_confidence_memory")
        if not record.evidence_refs and record.namespace in {"memory:shared", "memory:regression"}:
            warnings.append("missing_evidence_ref")
        return True, warnings

    def allowed_namespaces_for_search(self, request: MemorySearchRequest) -> list[str]:
        requested = [str(item) for item in request.namespaces] if request.namespaces else [item.namespace for item in self.namespaces()]
        allowed: list[str] = []
        for namespace in requested:
            if namespace in PRIVATE_NAMESPACES and self.owner_for_namespace(namespace) != request.agent_id:
                continue
            if namespace == "memory:security":
                continue
            allowed.append(namespace)
        return allowed

    def owner_for_namespace(self, namespace: str) -> str | None:
        for agent_id, private_namespace in PRIVATE_NAMESPACE_BY_AGENT.items():
            if namespace == private_namespace:
                return agent_id
        return None

    def _auto_accept_shared(self) -> bool:
        return bool(self.config().get("auto_accept_shared_with_strong_evidence", False))

    def _contains_blocked_sensitive(self, value: str) -> bool:
        if contains_secret(value):
            return True
        lowered = value.lower()
        blocked_markers = self.config().get("blocked_sensitive_markers", [])
        return any(str(marker).lower() in lowered for marker in blocked_markers)

    def _contains_chain_of_thought_marker(self, value: str) -> bool:
        lowered = value.lower()
        markers = self.config().get("chain_of_thought_markers", ["chain-of-thought", "raciocinio interno", "raciocínio interno"])
        return any(str(marker).lower() in lowered for marker in markers)

    def _deny(self, reason_code: str, human_reason: str) -> MemoryPolicyEvaluation:
        return MemoryPolicyEvaluation(decision="deny", reason_code=reason_code, human_reason=human_reason)
