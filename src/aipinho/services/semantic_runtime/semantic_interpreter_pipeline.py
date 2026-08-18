from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.semantic_runtime.isr import ISRMetadata
from aipinho.schemas.semantic_runtime.semantic_interpreter import (
    SemanticEntity,
    SemanticInterpreterContract,
    SemanticInterpreterOutput,
    SemanticInterpreterPipelineResult,
)
from aipinho.services.semantic_runtime.capability_resolver import CapabilityResolver
from aipinho.utils.yaml_loader import load_yaml_file


class SemanticInterpreterRole:
    def __init__(self, capability_resolver: CapabilityResolver | None = None, config_path: Path | None = None) -> None:
        self.capability_resolver = capability_resolver or CapabilityResolver()
        self.config_path = config_path or PATHS.config_root / "semantic_runtime" / "semantic_interpreter.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def interpret(self, contract: SemanticInterpreterContract) -> SemanticInterpreterOutput:
        if not self.enabled:
            return SemanticInterpreterOutput(
                status="disabled",
                intent="unknown",
                scope="unknown",
                confidence=0.0,
                ambiguity={"score": 1.0, "reasons": ["semantic_runtime_disabled"]},
                metadata=ISRMetadata(contract_id=contract.contract_id, session_id=contract.session_id),
                reasoning_summary="Semantic runtime feature flag is disabled.",
                blocked_reasons=["semantic_runtime_disabled"],
                semantic_trace=[self._trace("feature_flag", "disabled")],
            )
        selection = self.capability_resolver.resolve_for_role("semantic_interpreter")
        if not selection.allowed:
            return SemanticInterpreterOutput(
                status="blocked",
                intent="unknown",
                scope="unknown",
                confidence=0.0,
                ambiguity={"score": 1.0, "reasons": ["semantic_understanding_unavailable"]},
                metadata=ISRMetadata(contract_id=contract.contract_id, session_id=contract.session_id, model_selection=selection.model_dump()),
                reasoning_summary="SemanticUnderstanding capability is unavailable.",
                blocked_reasons=selection.blocked_reasons or ["semantic_understanding_unavailable"],
                semantic_trace=[self._trace("capability_resolution", "blocked", selection.model_dump())],
            )
        isr = self._deterministic_isr(contract)
        isr.metadata.model_selection = selection.model_dump()
        isr.semantic_trace.append(self._trace("capability_resolution", "ready", selection.model_dump()))
        isr.semantic_trace.append(self._trace("semantic_interpretation", "ready", {"strategy": "deterministic_parallel_isr"}))
        return isr

    @property
    def enabled(self) -> bool:
        semantic_runtime = self.config.get("semantic_runtime", {}) if isinstance(self.config.get("semantic_runtime", {}), dict) else {}
        return bool(semantic_runtime.get("semantic_runtime_enabled", False))

    def _deterministic_isr(self, contract: SemanticInterpreterContract) -> SemanticInterpreterOutput:
        prompt = contract.prompt.strip()
        lower = prompt.lower()
        constraints = self._constraints(lower)
        entities = self._entities(prompt)
        requested_outputs = self._requested_outputs(lower)
        intent = self._intent(lower, constraints)
        scope = self._scope(lower, entities)
        confidence = self._confidence(intent, entities, constraints, requested_outputs)
        ambiguity_score = round(max(0.0, 1.0 - confidence), 3)
        return SemanticInterpreterOutput(
            version="1.0",
            status="ready",
            intent=intent,
            scope=scope,
            entities=entities,
            permissions_requested=self._permissions_requested(lower),
            constraints=constraints,
            expected_outputs=requested_outputs,
            confidence=confidence,
            ambiguity={"score": ambiguity_score, "reasons": self._ambiguity_reasons(intent, entities, requested_outputs)},
            metadata=ISRMetadata(contract_id=contract.contract_id, session_id=contract.session_id),
            reasoning_summary=f"ISR preliminar gerada em modo paralelo sem contratos, ferramentas ou runtime. Intent={intent}; scope={scope}.",
        )

    def _constraints(self, lower: str) -> dict[str, Any]:
        return {
            "read_only": any(token in lower for token in ["read-only", "somente leitura", "apenas leitura", "nao modificar", "não modificar"]),
            "no_write": any(token in lower for token in ["nao escrever", "não escrever", "nao criar arquivo", "não criar arquivo", "nao modificar", "não modificar"]),
            "no_patch": any(token in lower for token in ["nao aplicar patch", "não aplicar patch", "nao rodar patch", "não rodar patch"]),
            "no_shell": any(token in lower for token in ["nao executar shell", "não executar shell", "nao rodar build", "não rodar build", "sem shell"]),
            "no_runtime": any(token in lower for token in ["nao executar runtime", "não executar runtime", "nao execute", "não execute", "sem side effects"]),
            "approval_forbidden": any(token in lower for token in ["nao criar approval", "não criar approval", "nao abrir approvalrequest", "não abrir approvalrequest"]),
        }

    def _entities(self, prompt: str) -> list[SemanticEntity]:
        entities: list[SemanticEntity] = []
        for match in re.finditer(r"[A-Za-z]:\\[^\n\r\"']+", prompt):
            entities.append(SemanticEntity(entity_type="path", value=match.group(0).strip(), confidence=0.95))
        for quoted in re.finditer(r'"([^"]+)"', prompt):
            value = quoted.group(1).strip()
            if value and not any(entity.value == value for entity in entities):
                entities.append(SemanticEntity(entity_type="quoted_text", value=value, confidence=0.75))
        return entities

    def _requested_outputs(self, lower: str) -> list[str]:
        outputs: list[str] = []
        output_terms = {
            "relatorio": "report",
            "relatório": "report",
            "resumo": "summary",
            "plano": "plan",
            "diagnostico": "diagnostic",
            "diagnóstico": "diagnostic",
            "preview": "preview",
            "arquivo": "file",
            "apk": "apk",
            "artifact": "artifact",
            "artefato": "artifact",
        }
        for token, output in output_terms.items():
            if token in lower and output not in outputs:
                outputs.append(output)
        return outputs

    def _permissions_requested(self, lower: str) -> list[str]:
        permissions: list[str] = []
        permission_terms = {
            "escrever": "write_files",
            "criar arquivo": "write_files",
            "alterar": "write_files",
            "modificar": "write_files",
            "patch": "apply_patch",
            "shell": "run_command",
            "build": "run_command",
            "instalar": "run_command",
            "deletar": "delete_file",
        }
        for token, permission in permission_terms.items():
            if token in lower and permission not in permissions:
                permissions.append(permission)
        return permissions

    def _ambiguity_reasons(self, intent: str, entities: list[SemanticEntity], requested_outputs: list[str]) -> list[str]:
        reasons: list[str] = []
        if intent == "unknown":
            reasons.append("intent_unknown")
        if not entities:
            reasons.append("no_explicit_entities")
        if not requested_outputs:
            reasons.append("no_requested_outputs_detected")
        return reasons

    def _intent(self, lower: str, constraints: dict[str, Any]) -> str:
        if constraints.get("read_only") or "diagnostico" in lower or "diagnóstico" in lower or "analise" in lower or "análise" in lower:
            return "readonly_analysis"
        if any(token in lower for token in ["crie", "criar", "implemente", "implementar", "modifique", "alterar", "corrija"]):
            return "implementation_request"
        if any(token in lower for token in ["pesquise", "internet", "web", "noticias", "notícias"]):
            return "public_fact_query"
        if any(token in lower for token in ["explique", "o que", "como funciona"]):
            return "conversation"
        return "unknown"

    def _scope(self, lower: str, entities: list[SemanticEntity]) -> str:
        if any(entity.entity_type == "path" for entity in entities):
            return "workspace_or_filesystem"
        if any(token in lower for token in ["projeto", "workspace", "repositorio", "repositório"]):
            return "project"
        if any(token in lower for token in ["internet", "web", "noticias", "notícias"]):
            return "public_knowledge"
        return "chat"

    def _confidence(self, intent: str, entities: list[SemanticEntity], constraints: dict[str, Any], requested_outputs: list[str]) -> float:
        score = 0.35
        if intent != "unknown":
            score += 0.25
        if entities:
            score += 0.15
        if any(bool(value) for value in constraints.values()):
            score += 0.15
        if requested_outputs:
            score += 0.10
        return round(min(score, 0.95), 3)

    def _trace(self, stage: str, status: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"stage": stage, "status": status, "data": data or {}}


class SemanticInterpreterPipeline:
    def __init__(self, role: SemanticInterpreterRole | None = None) -> None:
        self.role = role or SemanticInterpreterRole()

    def run(self, prompt: str, *, session_id: str | None = None, context: dict[str, Any] | None = None) -> SemanticInterpreterPipelineResult:
        contract = SemanticInterpreterContract(prompt=prompt, session_id=session_id, context=context or {})
        output = self.role.interpret(contract)
        return SemanticInterpreterPipelineResult(status=output.status, contract=contract, output=output, warnings=list(output.warnings))

    def status(self) -> dict[str, object]:
        return {
            "status": "ok" if self.role.enabled else "disabled",
            "service": "semantic_interpreter_pipeline",
            "semantic_runtime_enabled": self.role.enabled,
        }
