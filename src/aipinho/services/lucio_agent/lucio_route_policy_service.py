from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.lucio_agent import LucioAgentRequest, LucioRouteDecision
from aipinho.utils.yaml_loader import load_yaml_file


class LucioRoutePolicyService:
    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = policy_path or PATHS.config_root / "agents" / "lucio_agent_policy.yaml"

    def policy(self) -> dict[str, Any]:
        return load_yaml_file(self.policy_path, root=PATHS.project_root)

    def decide(self, request: LucioAgentRequest) -> LucioRouteDecision:
        config = self.policy()
        routes = dict(config.get("routing") or {})
        capabilities = set(request.requested_capabilities)
        prompt_concepts = self._concepts(request.prompt, config)
        modalities = self._modalities(request)

        codex = dict(routes.get("codex") or {})
        aipinho = dict(routes.get("aipinho") or {})
        direct = dict(routes.get("direct") or {})

        if request.artifacts and self._ambiguous_visual_request(request.prompt, prompt_concepts):
            return LucioRouteDecision(
                route="request_better_image",
                route_type="request_better_image",
                confidence="medium",
                reasons=["visual_input_ambiguous", *sorted(prompt_concepts)],
                reason_sanitized="Artifact visual anexado, mas o pedido ainda esta ambiguo.",
                requested_capabilities=request.requested_capabilities,
                required_capabilities=["multimodal_review"],
                expected_outputs=["clarification_question"],
                detected_intent="visual_clarification",
                input_modalities=modalities,
                risk_level="low",
                clarification_question="Voce quer uma avaliacao de UX, diagnostico de erro, revisao de arquitetura ou delegacao tecnica?",
                evidence_refs=[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts],
                evidence_source_count=len(request.artifacts),
                requires_local_execution=False,
            )

        if self._prefer_aipinho_for_local_execution(request, capabilities, prompt_concepts, aipinho, codex):
            operation = self._delegated_operation(request, aipinho)
            return LucioRouteDecision(
                route="delegate_aipinho",
                route_type="delegate_to_aipinho",
                target_agent_id="aipinho",
                delegated_operation=operation,
                confidence="high",
                reasons=["local_workspace_execution_requires_aipinho", "local_execution_priority", *sorted(prompt_concepts & set(aipinho.get("concepts") or []))],
                reason_sanitized="O pedido exige contexto ou execucao local governada.",
                requested_capabilities=request.requested_capabilities,
                required_capabilities=request.requested_capabilities,
                expected_outputs=["human_summary", "event_trace", "validation_evidence"],
                detected_intent=operation,
                input_modalities=modalities,
                risk_level=self._risk_level(capabilities),
                evidence_refs=[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts],
                evidence_source_count=len(request.artifacts),
                requires_local_execution=True,
            )

        if self._matches_route(request, capabilities, prompt_concepts, codex):
            operation = self._delegated_operation(request, codex)
            return LucioRouteDecision(
                route="delegate_codex",
                route_type="delegate_to_codex",
                target_agent_id="codex",
                delegated_operation=operation,
                confidence="high",
                reasons=["technical_execution_requires_codex", *sorted(prompt_concepts & set(codex.get("concepts") or []))],
                reason_sanitized="O pedido exige trabalho tecnico governado.",
                requested_capabilities=request.requested_capabilities,
                required_capabilities=request.requested_capabilities,
                expected_outputs=["technical_plan", "event_trace", "validation_evidence"],
                detected_intent=operation,
                input_modalities=modalities,
                risk_level=self._risk_level(capabilities),
                evidence_refs=[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts],
                evidence_source_count=len(request.artifacts),
                requires_local_execution=True,
            )

        if self._matches_route(request, capabilities, prompt_concepts, aipinho):
            operation = self._delegated_operation(request, aipinho)
            return LucioRouteDecision(
                route="delegate_aipinho",
                route_type="delegate_to_aipinho",
                target_agent_id="aipinho",
                delegated_operation=operation,
                confidence="high",
                reasons=["local_workspace_execution_requires_aipinho", *sorted(prompt_concepts & set(aipinho.get("concepts") or []))],
                reason_sanitized="O pedido exige contexto ou execucao local governada.",
                requested_capabilities=request.requested_capabilities,
                required_capabilities=request.requested_capabilities,
                expected_outputs=["human_summary", "event_trace", "validation_evidence"],
                detected_intent=operation,
                input_modalities=modalities,
                risk_level=self._risk_level(capabilities),
                evidence_refs=[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts],
                evidence_source_count=len(request.artifacts),
                requires_local_execution=True,
            )

        return LucioRouteDecision(
            route="direct_response",
            route_type="answer_directly",
            confidence="high" if request.operation_type in set(direct.get("operations") or []) else "medium",
            reasons=["strategic_or_conversational_response", *sorted(prompt_concepts & set(direct.get("concepts") or []))],
            reason_sanitized="O pedido pode ser respondido por analise estrategica sem side effect local.",
            requested_capabilities=request.requested_capabilities,
            required_capabilities=["multimodal_review"] if request.artifacts else [],
            expected_outputs=["structured_human_answer", "evidence_refs"],
            detected_intent=request.operation_type,
            input_modalities=modalities,
            risk_level=self._risk_level(capabilities),
            evidence_refs=[f"artifact:{artifact.artifact_id}" for artifact in request.artifacts],
            evidence_source_count=len(request.artifacts),
            requires_local_execution=False,
        )

    def _matches_route(
        self,
        request: LucioAgentRequest,
        capabilities: set[str],
        concepts: set[str],
        route: dict[str, Any],
    ) -> bool:
        if request.operation_type in set(route.get("operations") or []):
            return True
        if capabilities & set(route.get("capabilities") or []):
            return True
        if concepts & set(route.get("concepts") or []):
            return True
        if route.get("workspace_context_routes_here") and (request.workspace_id or request.target_paths):
            return True
        return False

    def _prefer_aipinho_for_local_execution(
        self,
        request: LucioAgentRequest,
        capabilities: set[str],
        concepts: set[str],
        aipinho: dict[str, Any],
        codex: dict[str, Any],
    ) -> bool:
        if not self._matches_route(request, capabilities, concepts, aipinho):
            return False
        code_specific = set(codex.get("capabilities") or []) - {"workspace_write", "read_workspace", "report_generate", "validation"}
        code_concepts = set(codex.get("concepts") or [])
        code_operations = set(codex.get("operations") or [])
        if request.operation_type in code_operations and request.operation_type not in set(aipinho.get("operations") or []):
            return False
        if capabilities & code_specific:
            return False
        if concepts & code_concepts:
            return False
        return bool(request.workspace_id or request.target_paths or capabilities & set(aipinho.get("capabilities") or []))

    def _delegated_operation(self, request: LucioAgentRequest, route: dict[str, Any]) -> str:
        operation_map = dict(route.get("operation_map") or {})
        return str(operation_map.get(request.operation_type) or route.get("default_operation") or request.operation_type)

    def _concepts(self, prompt: str, config: dict[str, Any]) -> set[str]:
        text = prompt.casefold()
        concepts: set[str] = set()
        for concept, markers in dict(config.get("concept_registry") or {}).items():
            if any(str(marker).casefold() in text for marker in markers or []):
                concepts.add(str(concept))
        return concepts

    def _modalities(self, request: LucioAgentRequest) -> list[str]:
        modalities = ["text"]
        if any(str(artifact.content_type or "").lower().startswith("image/") for artifact in request.artifacts):
            modalities.append("image")
        if any(str(artifact.content_type or "").lower() in {"application/pdf", "text/plain", "text/markdown", "application/json"} for artifact in request.artifacts):
            modalities.append("file")
        return list(dict.fromkeys(modalities))

    def _ambiguous_visual_request(self, prompt: str, concepts: set[str]) -> bool:
        if not prompt.strip():
            return True
        if concepts:
            return False
        text = prompt.casefold()
        explicit = ["analise", "diagnostique", "explique", "delegue", "corrija", "revise", "plano", "erro", "ux", "interface"]
        return not any(marker in text for marker in explicit)

    def _risk_level(self, capabilities: set[str]) -> str:
        high = {"shell", "workspace_write", "patch_apply", "git_write", "network_shell"}
        return "medium" if capabilities & high else "low"
