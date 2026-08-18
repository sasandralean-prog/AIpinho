from __future__ import annotations

import re

from aipinho.schemas.governance.lifecycle import CanonicalIntentDecision
from aipinho.services.governance.intent.intent_normalizer import has_any, normalize_text
from aipinho.services.semantic_runtime.semantic_proposition_normalization_service import SemanticPropositionNormalizationService


class CanonicalIntentRouter:
    """Canonical intent signal collector driven by intended state effect."""

    READONLY_TERMS = (
        "read-only",
        "read only",
        "readonly",
        "somente leitura",
        "apenas leitura",
        "modo somente leitura",
        "modo read-only",
        "product_planning_readonly",
        "somente planejamento textual",
        "nao escrever arquivos",
        "nÃ£o escrever arquivos",
        "nao criar approvalrequest",
        "nÃ£o criar approvalrequest",
        "nao criar grant",
        "nÃ£o criar grant",
        "nao implementar nada agora",
        "nÃ£o implementar nada agora",
        "somente analise",
        "somente anÃ¡lise",
        "somente planejamento",
        "apenas planejamento",
        "analysis_only",
        "read_only_plan",
    )
    NEGATIVE_SIDE_EFFECT_TERMS = (
        "nao modificar",
        "nao pode modificar",
        "nao pode alterar",
        "nao pode escrever",
        "nao altere",
        "nao alterar",
        "nao criar",
        "nao editar",
        "nao mover",
        "nao deletar",
        "nao apagar",
        "nao formatar",
        "nao instalar",
        "nao executar build",
        "nao rodar build",
        "nao executar shell",
        "nao executar comando",
        "nao rodar comando",
        "nao executar patch",
        "nao rodar patch",
        "nao aplicar patch",
        "nao criar artifact",
        "nao criar artefato",
        "nao abrir approvalrequest",
        "nao criar approvalrequest",
        "nao criar taskrun",
        "sem side effects",
        "sem efeitos colaterais",
        "sem modificar",
        "sem alterar",
        "sem escrever",
        "patch futuro",
        "plano futuro",
        "preview textual",
        "mas nao execute",
        "apenas diagnostico",
        "somente diagnostico",
        "diagnostico read-only",
        "diagnostico readonly",
    )
    ANALYSIS_READONLY_TERMS = (
        "analise os arquivos",
        "analise arquivos",
        "crie um plano",
        "criar plano",
        "plano de acao",
        "plano de aÃ§Ã£o",
        "relatorio do que mudar",
        "relatÃ³rio do que mudar",
        "responda com relatorio",
        "responda com relatÃ³rio",
        "relatorio e plano",
        "relatÃ³rio e plano",
        "diagnostique problemas",
        "diagnosticar problemas",
        "explique como corrigir",
        "liste arquivos provaveis",
        "liste arquivos provÃ¡veis",
        "faca uma auditoria",
        "faÃ§a uma auditoria",
        "diga o que precisa mudar",
        "auditoria",
        "somente relatorio",
        "somente relatÃ³rio",
    )
    FIX_REQUEST_TERMS = (
        "analise e corrija",
        "analise e corrigir",
        "diagnostique e corrija",
        "diagnostique e corrigir",
        "corrija os problemas",
        "corrigir os problemas",
        "conserte os problemas",
        "analise, diagnostique e corrija",
        "analise diagnostique e corrija",
    )
    CAPABILITY_TERMS = (
        "voce consegue executar tarefas",
        "vocÃª consegue executar tarefas",
        "voce consegue ler arquivos",
        "vocÃª consegue ler arquivos",
        "voce pode criar projeto",
        "vocÃª pode criar projeto",
        "voce pode editar arquivos",
        "vocÃª pode editar arquivos",
        "voce pode rodar build",
        "vocÃª pode rodar build",
        "voce tem acesso ao workspace",
        "vocÃª tem acesso ao workspace",
        "voce consegue aplicar patch",
        "vocÃª consegue aplicar patch",
        "voce consegue aprovar",
        "vocÃª consegue aprovar",
        "voce consegue executar shell",
        "vocÃª consegue executar shell",
    )
    WORKSPACE_QUERY_TERMS = (
        "listar workspaces",
        "workspaces aprovados",
        "quais diretorios posso escrever",
        "workspace registry",
        "permissoes de workspace",
    )
    APPROVAL_COMMAND_PATTERNS = (
        re.compile(r"^APROVAR approval_[A-Za-z0-9_-]+$", re.IGNORECASE),
        re.compile(r"^NEGAR approval_[A-Za-z0-9_-]+$", re.IGNORECASE),
        re.compile(r"^LISTAR APPROVALS PENDENTES$", re.IGNORECASE),
    )
    SESSION_DIAGNOSTIC_TERMS = (
        "diagnostique esta sessao",
        "diagnostico da conversa",
        "debug da sessao",
        "session diagnostic",
    )
    PROJECT_TERMS = (
        "iniciar projeto",
        "criar projeto",
        "inicie projeto",
        "inicie o projeto",
        "crie projeto",
        "implementar mvp",
        "implemente",
        "implementar",
        "corrija",
        "corrigir",
        "conserte",
        "rebuild",
        "sprint",
        "crie uma pasta",
        "criar pasta",
        "crie pasta",
        "crie um diretorio",
        "crie um diretÃ³rio",
        "criar diretorio",
        "criar diretÃ³rio",
        "project_generation",
        "project_bootstrap",
    )
    CONTROLLED_PREVIEW_TERMS = (
        "crie taskpreview",
        "criar taskpreview",
        "crie um taskpreview",
        "crie agora um taskpreview",
        "taskpreview executavel",
        "taskpreview executÃƒÂ¡vel",
        "task preview executavel",
        "task preview executÃƒÂ¡vel",
        "crie approvalrequest",
        "criar approvalrequest",
        "crie um approvalrequest",
        "crie agora um approvalrequest",
        "approvalrequest para",
        "approval request para",
    )

    def __init__(self, semantic_normalizer: SemanticPropositionNormalizationService | None = None) -> None:
        self.semantic_normalizer = semantic_normalizer or SemanticPropositionNormalizationService()

    def decide(self, text: str, *, source_channel: str = "unknown") -> CanonicalIntentDecision:
        normalized = normalize_text(text)
        concept_matches = self.semantic_normalizer.concept_matcher.match(text)
        semantic_graph = self.semantic_normalizer.normalize(text)

        if self._is_formal_approval_command(text):
            return CanonicalIntentDecision(
                intent_type="approval_command",
                operation_type="approval_command",
                requires_task=False,
                readonly=False,
                source_channel=source_channel,
                evidence=["approval_command_precedence"],
                semantic_intent_graph=semantic_graph,
            )
        if has_any(normalized, self.WORKSPACE_QUERY_TERMS):
            return CanonicalIntentDecision(
                intent_type="workspace_permission_list",
                operation_type="workspace_permission_list",
                requires_task=False,
                readonly=True,
                source_channel=source_channel,
                evidence=["workspace_registry_query"],
                semantic_intent_graph=semantic_graph,
            )
        if has_any(normalized, self.CAPABILITY_TERMS):
            return CanonicalIntentDecision(
                intent_type="capability_truth",
                operation_type="capability_truth",
                requires_task=False,
                readonly=True,
                source_channel=source_channel,
                evidence=["capability_truth_question"],
                semantic_intent_graph=semantic_graph,
            )
        readonly_negative = self._merge_graph_constraints(
            self._readonly_negative_constraints(normalized),
            semantic_graph,
        )
        if self._is_meta_conversation_request(concept_matches, semantic_graph):
            return CanonicalIntentDecision(
                intent_type="conversation_self_diagnosis",
                operation_type="conversation",
                requires_task=False,
                side_effect_requested=False,
                readonly=False,
                source_channel=source_channel,
                negative_constraints=readonly_negative,
                evidence=["meta_conversation_about_chat_runtime", *semantic_graph.evidence],
                semantic_intent_graph=semantic_graph,
            )
        if (
            semantic_graph.approval_intent
            and self._is_controlled_preview_request(normalized)
            and not semantic_graph.readonly_contract
            and not readonly_negative.get("approval_forbidden", False)
        ):
            if semantic_graph.state_effect in {"build_execution", "runtime_execution"}:
                return CanonicalIntentDecision(
                    intent_type="governed_shell_request",
                    operation_type="run_command",
                    requires_task=True,
                    side_effect_requested=True,
                    readonly=False,
                    source_channel=source_channel,
                    negative_constraints=readonly_negative,
                    evidence=["controlled_preview_shell_precedence", *semantic_graph.evidence],
                    semantic_intent_graph=semantic_graph,
                )
            return CanonicalIntentDecision(
                intent_type="project_bootstrap",
                operation_type="project_generation",
                requires_task=True,
                side_effect_requested=True,
                readonly=False,
                source_channel=source_channel,
                evidence=["controlled_preview_approval_request_precedence"],
                semantic_intent_graph=semantic_graph,
            )
        if self._is_readonly_artifact_analysis_request(text, normalized, semantic_graph=semantic_graph):
            return CanonicalIntentDecision(
                intent_type="workspace_analysis_readonly",
                operation_type="workspace_analysis_readonly",
                requires_task=True,
                side_effect_requested=False,
                readonly=True,
                source_channel=source_channel,
                negative_constraints=readonly_negative,
                evidence=["readonly_analysis_with_artifact_output", *semantic_graph.evidence],
                semantic_intent_graph=semantic_graph,
            )
        if semantic_graph.readonly_contract:
            readonly_intent = (
                "workspace_analysis_readonly"
                if self._has_workspace_analysis_scope(concept_matches, normalized)
                or self._is_readonly_analysis_request(normalized)
                else "product_planning_readonly"
            )
            return CanonicalIntentDecision(
                intent_type=readonly_intent,
                operation_type=readonly_intent,
                requires_task=False,
                side_effect_requested=False,
                readonly=True,
                source_channel=source_channel,
                negative_constraints=readonly_negative,
                evidence=["state_effect_readonly_contract", *semantic_graph.evidence],
                semantic_intent_graph=semantic_graph,
            )
        if has_any(normalized, self.SESSION_DIAGNOSTIC_TERMS):
            return CanonicalIntentDecision(
                intent_type="session_diagnostic",
                operation_type="session_diagnostic",
                requires_task=False,
                readonly=True,
                source_channel=source_channel,
                evidence=["explicit_session_diagnostic"],
                semantic_intent_graph=semantic_graph,
            )
        if has_any(normalized, self.FIX_REQUEST_TERMS):
            return CanonicalIntentDecision(
                intent_type="workspace_fix_request",
                operation_type="workspace_fix_request",
                requires_task=True,
                readonly=True,
                source_channel=source_channel,
                evidence=["fix_request_requires_discovery_first"],
                semantic_intent_graph=semantic_graph,
            )
        if semantic_graph.execution_intent and semantic_graph.state_effect in {"build_execution", "runtime_execution"}:
            evidence = ["state_effect_execution", *semantic_graph.evidence]
            if readonly_negative:
                evidence.append("negative_constraints_preserved")
            return CanonicalIntentDecision(
                intent_type="governed_shell_request",
                operation_type="run_command",
                requires_task=True,
                side_effect_requested=True,
                readonly=False,
                source_channel=source_channel,
                negative_constraints=readonly_negative,
                evidence=evidence,
                semantic_intent_graph=semantic_graph,
            )
        if has_any(normalized, self.PROJECT_TERMS) and semantic_graph.state_effect == "workspace_mutation":
            return CanonicalIntentDecision(
                intent_type="project_bootstrap",
                operation_type="project_bootstrap",
                requires_task=True,
                side_effect_requested=True,
                readonly=False,
                source_channel=source_channel,
                evidence=["project_bootstrap_signal", *semantic_graph.evidence],
                semantic_intent_graph=semantic_graph,
            )
        if semantic_graph.mutation_intent and semantic_graph.state_effect == "workspace_mutation":
            evidence = ["state_effect_mutation", *semantic_graph.evidence]
            if readonly_negative:
                evidence.append("negative_constraints_preserved")
            return CanonicalIntentDecision(
                intent_type="patch_or_write_request",
                operation_type="patch_request",
                requires_task=True,
                side_effect_requested=True,
                readonly=False,
                source_channel=source_channel,
                negative_constraints=readonly_negative,
                evidence=evidence,
                semantic_intent_graph=semantic_graph,
            )
        if (
            (semantic_graph.observational_intent or semantic_graph.knowledge_output)
            and (
                self._has_workspace_analysis_scope(concept_matches, normalized)
                or self._is_readonly_analysis_request(normalized)
                or semantic_graph.artifact_output
            )
        ):
            return CanonicalIntentDecision(
                intent_type="workspace_analysis_readonly",
                operation_type="workspace_analysis_readonly",
                requires_task=False,
                side_effect_requested=False,
                readonly=True,
                source_channel=source_channel,
                negative_constraints=readonly_negative,
                evidence=["state_effect_observation", *semantic_graph.evidence],
                semantic_intent_graph=semantic_graph,
            )
        return CanonicalIntentDecision(source_channel=source_channel, semantic_intent_graph=semantic_graph)

    def _is_formal_approval_command(self, text: str) -> bool:
        normalized = " ".join(str(text or "").strip().split())
        if not normalized:
            return False
        return any(pattern.fullmatch(normalized) for pattern in self.APPROVAL_COMMAND_PATTERNS)

    def _readonly_negative_constraints(self, normalized: str) -> dict[str, bool]:
        has_readonly = has_any(normalized, self.READONLY_TERMS)
        has_negative_side_effect = has_any(normalized, self.NEGATIVE_SIDE_EFFECT_TERMS)
        if not (has_readonly or has_negative_side_effect):
            return {}
        constraints: dict[str, bool] = {}
        if any(term in normalized for term in ("nao modificar", "nao pode modificar", "nao pode alterar", "nao pode escrever", "nao alter", "nao editar", "nao criar", "sem modificar", "sem alterar", "sem escrever", "sem side effects", "sem efeitos colaterais")):
            constraints["write_forbidden"] = True
        if any(term in normalized for term in ("nao executar shell", "nao executar comando", "nao rodar comando", "nao executar build", "nao rodar build")):
            constraints["shell_forbidden"] = True
        if any(term in normalized for term in ("nao executar patch", "nao rodar patch", "nao aplicar patch")):
            constraints["patch_forbidden"] = True
        if any(term in normalized for term in ("nao criar artifact", "nao criar artefato")):
            constraints["artifact_forbidden"] = True
        if any(term in normalized for term in ("nao abrir approvalrequest", "nao criar approvalrequest")):
            constraints["approval_forbidden"] = True
        if "nao criar taskrun" in normalized:
            constraints["taskrun_forbidden"] = True
        if any(term in normalized for term in ("patch futuro", "plano futuro", "preview textual", "mas nao execute")):
            constraints["execution_forbidden"] = True
            constraints.setdefault("write_forbidden", True)
        return constraints

    def _is_readonly_analysis_request(self, normalized: str) -> bool:
        if has_any(normalized, self.ANALYSIS_READONLY_TERMS):
            return True
        return bool(
            ("diagnostico" in normalized or "diagnosticar" in normalized or "discovery" in normalized)
            and ("workspace" in normalized or "projeto" in normalized or "arquivos" in normalized or "workload" in normalized)
        )

    def _is_meta_conversation_request(self, concept_matches, semantic_graph) -> bool:
        concept_types = {match.concept_type for match in concept_matches}
        about_conversation = "object_conversation_state" in concept_types
        about_runtime_failure = "object_runtime_failure" in concept_types
        asks_for_explanation = bool(
            semantic_graph.knowledge_output
            or semantic_graph.observational_intent
            or (about_conversation and about_runtime_failure)
        )
        about_workspace = any(
            match.concept_id in {"workspace_actor", "project_object", "directory_object", "executable_artifact_object"}
            for match in concept_matches
        )
        return asks_for_explanation and (about_conversation or about_runtime_failure) and not about_workspace

    def _has_workspace_analysis_scope(self, concept_matches, normalized: str) -> bool:
        scoped_concepts = {
            "workspace_actor",
            "project_object",
            "directory_object",
            "executable_artifact_object",
            "artifact_report_object",
        }
        if any(match.concept_id in scoped_concepts for match in concept_matches):
            return True
        return bool(
            "workspace" in normalized
            or "projeto" in normalized
            or "repositorio" in normalized
        )

    def _is_readonly_artifact_analysis_request(self, text: str, normalized: str, *, semantic_graph) -> bool:
        if any(term in normalized for term in ("nao criar artifact", "nÃ£o criar artifact", "nao gerar artifact", "nÃ£o gerar artifact")):
            return False
        if semantic_graph.state_effect in {"workspace_mutation", "build_execution", "runtime_execution"}:
            return False
        if not semantic_graph.readonly_contract or not semantic_graph.knowledge_output:
            return False
        if not any(term in normalized for term in ("artifact", "artifacts", "artefato", "artefatos", "entregavel", "entregÃ¡vel", "reports/")):
            return False
        if not re.search(
            r"(?<![A-Za-z]:)(?:[A-Za-z0-9_.-]+[\\/])+[A-Za-z0-9_. -]+\.(?:md|json|txt|csv|html|yaml|yml|zip)",
            text or "",
            re.IGNORECASE,
        ):
            return False
        return semantic_graph.observational_intent or self._has_analysis_output_intent(normalized)

    def _has_analysis_output_intent(self, normalized: str) -> bool:
        return any(
            term in normalized
            for term in (
                "analise",
                "anÃ¡lise",
                "analysis",
                "diagnost",
                "diagnosis",
                "descoberta",
                "discovery",
                "inventario",
                "inventory",
                "mapear",
                "auditoria",
                "auditar",
                "relatorio",
                "relatÃ³rio",
                "report",
                "comparar",
                "compare",
                "comparison",
                "use os artifacts",
                "use artifacts",
                "utilizar os artifacts",
                "utilize os artifacts",
            )
        )

    def _is_controlled_preview_request(self, normalized: str) -> bool:
        return has_any(normalized, self.CONTROLLED_PREVIEW_TERMS)

    def _merge_graph_constraints(self, constraints: dict[str, bool], semantic_graph) -> dict[str, bool]:
        merged = dict(constraints)
        prohibited = set(getattr(semantic_graph, "prohibited_effects", []) or [])
        if getattr(semantic_graph, "readonly_contract", False):
            merged.setdefault("write_forbidden", True)
            merged.setdefault("approval_forbidden", True)
        if prohibited.intersection({"workspace_mutation", "proposal_only"}):
            merged.setdefault("write_forbidden", True)
        if "proposal_only" in prohibited:
            merged.setdefault("patch_forbidden", True)
        if prohibited.intersection({"build_execution", "runtime_execution"}):
            merged.setdefault("shell_forbidden", True)
        return merged
