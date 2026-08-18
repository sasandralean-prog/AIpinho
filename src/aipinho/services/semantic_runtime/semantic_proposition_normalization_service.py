from __future__ import annotations

import re

from aipinho.schemas.intent.intent_map import OutputIntent
from aipinho.schemas.intent.semantic_intent_graph import SemanticIntentGraph
from aipinho.services.governance.intent.intent_normalizer import normalize_text
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatch, ConceptMatcher
from aipinho.services.prompt_intelligence.output_intent_detector import OutputIntentDetector


class SemanticPropositionNormalizationService:
    _CLAUSE_SPLIT_RE = re.compile(r"[\n\r.;:]+")
    _NEGATIVE_RE = re.compile(r"\b(?:nao|nunca|sem)\b")
    _NON_WORD_RE = re.compile(r"[^0-9a-zA-Z]+")

    _OBSERVATION_TERMS = (
        "analise",
        "analisar",
        "diagnost",
        "discovery",
        "identificar",
        "inventari",
        "localizar",
        "listar",
        "mapear",
        "compreender",
        "conhecer",
        "explicar",
        "descrever",
        "auditoria",
        "auditar",
    )
    _PLANNING_TERMS = (
        "planej",
        "plano",
        "proposta",
        "propor",
        "preview",
        "roadmap",
        "estrateg",
        "estrategia",
        "como corrigir",
        "como consertar",
    )
    _KNOWLEDGE_OBJECT_TERMS = (
        "relatorio",
        "report",
        "tabela",
        "lista",
        "inventario",
        "inventory",
        "mapa",
        "markdown",
        "csv",
        "json",
        "documentacao",
        "documentacao",
        "resumo",
        "evidencia",
        "artefato",
        "artifacts",
    )
    _PATCH_OBJECT_TERMS = ("patch", "diff", "hunk")
    _PATCH_EXECUTION_VERBS = ("aplicar", "aplique", "execute", "executar", "rode", "rodar", "corrija", "conserte", "modifique", "altere", "edite", "implemente")
    _PATCH_PROPOSAL_VERBS = ("gerar", "gere", "preparar", "prepare", "propor", "proponha", "preview")
    _FILE_OBJECT_TERMS = ("arquivo", "arquivos", "file", "files", "pasta", "folder", "diretorio", "diretorio")
    _FILE_WRITE_VERBS = ("criar", "crie", "escrever", "escreva", "salvar", "salve", "gravar", "grave", "alterar", "altere", "modificar", "modifique", "editar", "edite", "mover", "delete", "apagar")
    _MUTATION_VERBS = ("alterar", "altere", "modificar", "modifique", "editar", "edite", "corrigir", "corrija", "consertar", "conserte", "implementar", "implemente", "refatorar", "refatore", "aplicar", "aplique")
    _BUILD_OBJECT_TERMS = ("build", "apk", "package", "pacote", "installer")
    _COMMAND_OBJECT_TERMS = ("comando", "shell", "pytest", "npm test", "gradlew", "gradle")
    _COMMAND_ACTION_TERMS = ("executar", "execute", "rodar", "rode", "run", "comando")
    _READONLY_TERMS = (
        "somente leitura",
        "apenas leitura",
        "read-only",
        "readonly",
        "sem alterar",
        "sem modificar",
        "sem escrever",
    )
    _APPROVAL_TERMS = (
        "approvalrequest",
        "approval request",
        "taskpreview",
        "task preview",
    )
    _EXPLANATORY_REPAIR_TERMS = (
        "como corrigir",
        "como consertar",
        "explique como corrigir",
        "explique como consertar",
    )

    def __init__(
        self,
        *,
        concept_matcher: ConceptMatcher | None = None,
        output_detector: OutputIntentDetector | None = None,
    ) -> None:
        self.concept_matcher = concept_matcher or ConceptMatcher().load()
        self.output_detector = output_detector or OutputIntentDetector(self.concept_matcher)

    def normalize(
        self,
        prompt: str,
        *,
        matches: list[ConceptMatch] | None = None,
        output_intent: OutputIntent | None = None,
    ) -> SemanticIntentGraph:
        normalized = normalize_text(prompt)
        matches = matches if matches is not None else self.concept_matcher.match(prompt)
        output_intent = output_intent or self.output_detector.detect(prompt, matches)

        requested_effects: set[str] = set()
        prohibited_effects: set[str] = set()
        evidence: list[str] = []
        approval_intent = False

        clauses = [clause.strip() for clause in self._CLAUSE_SPLIT_RE.split(normalized) if clause.strip()]
        for clause in clauses:
            if self._contains_exact(clause, self._APPROVAL_TERMS) and not self._NEGATIVE_RE.search(clause):
                approval_intent = True
            clause_effects = self._effects_for_clause(clause)
            if not clause_effects:
                continue
            if self._NEGATIVE_RE.search(clause):
                prohibited_effects.update(clause_effects)
                evidence.extend(f"negative:{effect}" for effect in clause_effects)
            else:
                requested_effects.update(clause_effects)
                evidence.extend(f"positive:{effect}" for effect in clause_effects)

        has_analysis = self.concept_matcher.has_type(matches, "operation_analysis") or self._contains_any(normalized, self._OBSERVATION_TERMS)
        has_info = self.concept_matcher.has_type(matches, "operation_information")
        has_mutation = self.concept_matcher.has_type(matches, "operation_mutation")
        has_execution = self.concept_matcher.has_type(matches, "operation_execution")
        has_no_write_constraint = any(match.concept_id == "no_write_constraint" for match in matches) or self._contains_any(normalized, self._READONLY_TERMS)
        has_approval_gated_write = any(match.concept_id == "approval_gated_write_constraint" for match in matches)
        has_preview_only = any(match.concept_id == "preview_only_constraint" for match in matches)
        has_artifact_output = bool(output_intent.should_save_file or output_intent.channel == "artifact")

        knowledge_output = (
            "knowledge_only" in requested_effects
            or (
                has_artifact_output
                and not requested_effects.intersection({"workspace_mutation", "build_execution", "runtime_execution"})
            )
        )
        planning_intent = has_preview_only or self._contains_any(normalized, self._PLANNING_TERMS)
        observational_intent = has_analysis or has_info or knowledge_output

        positive_mutation_effects = requested_effects.intersection({"workspace_mutation"})
        positive_proposal_effects = requested_effects.intersection({"proposal_only"})
        positive_execution_effects = requested_effects.intersection({"build_execution", "runtime_execution"})

        execution_intent = bool(positive_execution_effects)
        if not execution_intent and has_execution and not prohibited_effects.intersection({"build_execution", "runtime_execution"}):
            execution_intent = True

        mutation_intent = bool(positive_mutation_effects)
        if (
            not mutation_intent
            and has_mutation
            and not execution_intent
            and not (has_no_write_constraint and not positive_mutation_effects)
            and not (requested_effects and requested_effects.issubset({"knowledge_only", "planning_only"}))
            and not prohibited_effects.intersection({"workspace_mutation"})
        ):
            mutation_intent = True

        readonly_contract = (
            (has_no_write_constraint or bool(prohibited_effects))
            and not has_approval_gated_write
            and not approval_intent
            and not positive_mutation_effects
            and not positive_execution_effects
        )
        if readonly_contract:
            evidence.append("readonly_contract")

        state_effect = "none"
        if positive_mutation_effects or (mutation_intent and not positive_execution_effects):
            state_effect = "workspace_mutation"
        elif execution_intent:
            state_effect = "build_execution" if "build_execution" in requested_effects else "runtime_execution"
        elif positive_proposal_effects:
            state_effect = "proposal_only"
        elif planning_intent:
            state_effect = "planning_only"
        elif knowledge_output or observational_intent:
            state_effect = "knowledge_only"

        workspace_effect = "none"
        if readonly_contract:
            workspace_effect = "immutable"
        elif state_effect == "workspace_mutation":
            workspace_effect = "mutable"
        elif state_effect == "proposal_only":
            workspace_effect = "proposal_only"
        elif state_effect == "planning_only":
            workspace_effect = "planning_only"
        elif state_effect == "knowledge_only":
            workspace_effect = "knowledge_only"

        filesystem_effect = "none"
        if readonly_contract or prohibited_effects.intersection({"workspace_mutation", "proposal_only"}):
            filesystem_effect = "prohibited"
        elif state_effect == "workspace_mutation":
            filesystem_effect = "mutable"
        elif state_effect == "proposal_only":
            filesystem_effect = "proposal_only"
        elif state_effect in {"knowledge_only", "planning_only"} and has_artifact_output:
            filesystem_effect = "knowledge_only"

        runtime_effect = "none"
        if prohibited_effects.intersection({"build_execution", "runtime_execution"}):
            runtime_effect = "prohibited"
        elif state_effect == "build_execution":
            runtime_effect = "build_execution"
        elif state_effect == "runtime_execution":
            runtime_effect = "command_execution"

        if has_artifact_output:
            evidence.append("artifact_output")
        if planning_intent:
            evidence.append("planning_intent")
        if observational_intent:
            evidence.append("observational_intent")
        if mutation_intent:
            evidence.append("mutation_intent")
        if execution_intent:
            evidence.append("execution_intent")

        return SemanticIntentGraph(
            observational_intent=observational_intent,
            planning_intent=planning_intent,
            mutation_intent=mutation_intent,
            execution_intent=execution_intent,
            approval_intent=approval_intent,
            knowledge_output=knowledge_output,
            artifact_output=has_artifact_output,
            readonly_contract=readonly_contract,
            state_effect=state_effect,
            workspace_effect=workspace_effect,
            filesystem_effect=filesystem_effect,
            runtime_effect=runtime_effect,
            prohibited_effects=sorted(prohibited_effects),
            requested_effects=sorted(requested_effects),
            evidence=list(dict.fromkeys(evidence)),
        )

    def _effects_for_clause(self, clause: str) -> set[str]:
        effects: set[str] = set()
        if not clause:
            return effects
        explanatory_repair = self._contains_any(clause, self._EXPLANATORY_REPAIR_TERMS)
        if self._contains_exact(clause, self._PATCH_OBJECT_TERMS):
            if self._contains_exact(clause, self._PATCH_EXECUTION_VERBS):
                effects.add("workspace_mutation")
            elif self._contains_exact(clause, self._PATCH_PROPOSAL_VERBS):
                effects.add("proposal_only")
        if self._contains_exact(clause, self._BUILD_OBJECT_TERMS):
            effects.add("build_execution")
        if self._contains_exact(clause, self._COMMAND_OBJECT_TERMS) and self._contains_exact(clause, self._COMMAND_ACTION_TERMS):
            effects.add("runtime_execution")
        if self._contains_exact(clause, self._FILE_OBJECT_TERMS) and self._contains_exact(clause, self._FILE_WRITE_VERBS):
            effects.add("workspace_mutation")
        elif not explanatory_repair and self._contains_exact(clause, self._MUTATION_VERBS):
            effects.add("workspace_mutation")
        if self._contains_any(clause, self._KNOWLEDGE_OBJECT_TERMS):
            effects.add("knowledge_only")
        if self._contains_any(clause, self._PLANNING_TERMS):
            effects.add("planning_only")
        if self._contains_any(clause, self._OBSERVATION_TERMS):
            effects.add("knowledge_only")
        return effects

    @staticmethod
    def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)

    @classmethod
    def _contains_exact(cls, text: str, terms: tuple[str, ...]) -> bool:
        return any(cls._contains_term(text, term) for term in terms)

    @classmethod
    def _contains_term(cls, text: str, term: str) -> bool:
        normalized_term = term.strip().casefold()
        if not normalized_term:
            return False
        if " " in normalized_term or "/" in normalized_term or "\\" in normalized_term or "-" in normalized_term:
            pattern = re.compile(rf"(?<![0-9A-Za-z]){re.escape(normalized_term)}(?![0-9A-Za-z])")
            return bool(pattern.search(text))
        pattern = re.compile(rf"(?<![0-9A-Za-z]){re.escape(normalized_term)}(?![0-9A-Za-z])")
        return bool(pattern.search(text))
