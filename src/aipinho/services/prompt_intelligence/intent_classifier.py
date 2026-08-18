from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.intent.intent_map import ActorType, IntentType, ObjectType, OperationType, TaskType
from aipinho.schemas.intent.semantic_intent_graph import SemanticIntentGraph
from aipinho.schemas.intent.workspace_resolution import WorkspaceResolution
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatch, ConceptMatcher
from aipinho.schemas.intent.intent_map import OutputIntent
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class IntentClassification:
    intent_type: IntentType
    task_type: TaskType
    actor: ActorType
    operation: OperationType
    object: ObjectType
    requires_task: bool
    requires_workspace: bool
    requires_approval: bool
    requested_actions: list[str]
    confidence: float
    semantic_graph: SemanticIntentGraph


class IntentClassifier:
    def __init__(self, config_path: Path | None = None, concept_matcher: ConceptMatcher | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "intent_taxonomy.yaml"
        self.concept_matcher = concept_matcher or ConceptMatcher().load()
        self._config: dict[str, object] | None = None

    def load(self) -> "IntentClassifier":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def taxonomy(self) -> dict[str, object]:
        if self._config is None:
            self.load()
        intents = (self._config or {}).get("intents", {})
        return intents if isinstance(intents, dict) else {}

    def _intent_defaults(self, intent_type: str) -> dict[str, object]:
        raw = self.taxonomy.get(intent_type, {})
        return raw if isinstance(raw, dict) else {}

    def _classification_overrides(self) -> dict[str, object]:
        if self._config is None:
            self.load()
        raw = (self._config or {}).get("classification_overrides", {})
        return raw if isinstance(raw, dict) else {}

    def classify(
        self,
        prompt: str,
        matches: list[ConceptMatch],
        *,
        self_reference: bool,
        workspace: WorkspaceResolution,
        output_intent: OutputIntent,
        semantic_graph: SemanticIntentGraph,
    ) -> IntentClassification:
        has_capability = any(match.concept_id == "capability_object" for match in matches)
        has_architecture = any(match.concept_id == "architecture_object" for match in matches)
        has_project = any(match.concept_id in {"project_object", "workspace_actor"} for match in matches) or workspace.declared
        has_info = self.concept_matcher.has_type(matches, "operation_information")
        has_analysis = self.concept_matcher.has_type(matches, "operation_analysis")
        has_mutation = semantic_graph.mutation_intent or self.concept_matcher.has_type(matches, "operation_mutation")
        has_validation = self.concept_matcher.has_type(matches, "operation_validation")
        has_memory = self.concept_matcher.has_type(matches, "operation_memory")
        has_retrieval = self.concept_matcher.has_type(matches, "operation_retrieval")
        has_web_search = self.concept_matcher.has_type(matches, "operation_web_search")
        has_public_fact = self.concept_matcher.has_type(matches, "object_public_fact")
        has_execution = semantic_graph.execution_intent or self.concept_matcher.has_type(matches, "operation_execution")
        has_executable_artifact = any(match.concept_id == "executable_artifact_object" for match in matches)
        has_directory = any(match.concept_id == "directory_object" for match in matches)
        has_approval_gated_write = any(match.concept_id == "approval_gated_write_constraint" for match in matches)
        has_no_write_constraint = semantic_graph.readonly_contract and not has_approval_gated_write

        actor: ActorType = "self" if self_reference else ("workspace" if has_project else "user")
        obj: ObjectType = "architecture" if has_architecture else ("capabilities" if has_capability else ("artifact" if has_executable_artifact else ("project" if has_project or has_directory else "unknown")))
        operation: OperationType = "unknown"
        intent_type: IntentType = "unknown"
        confidence = 0.35
        lowered_prompt = prompt.casefold()
        has_project_repair = has_project and has_mutation and self._has_override_term(
            lowered_prompt,
            "project_repair_request",
            "repair_terms",
        )
        has_strong_executable_artifact = self._has_override_term(
            lowered_prompt,
            "executable_artifact_request",
            "strong_terms",
        )

        if self._matches_deferred_creation_conversation(lowered_prompt):
            operation = "explain"
            intent_type = "conversation"
            confidence = 0.78
        elif has_no_write_constraint and has_project and (semantic_graph.observational_intent or semantic_graph.knowledge_output or has_analysis or has_info):
            operation = "analyze" if has_analysis else "explain"
            intent_type = "readonly_analysis"
            confidence = 0.9
        elif semantic_graph.mutation_intent and not has_project and not has_directory and not has_executable_artifact and output_intent.channel == "chat":
            if has_info or has_analysis or "?" in prompt or any(term in lowered_prompt for term in {"como ", "em teoria", "conceitual", "abstrat"}):
                operation = "explain"
                intent_type = "conversation"
                confidence = 0.74
            else:
                operation = "unknown"
                intent_type = "unknown"
                confidence = 0.4
        elif semantic_graph.state_effect in {"build_execution", "runtime_execution"}:
            operation = "create"
            if has_strong_executable_artifact or semantic_graph.state_effect == "build_execution":
                intent_type = "artifact_build_request"
                confidence = 0.86
            else:
                intent_type = "validation_request"
                confidence = 0.8
        elif has_mutation or has_execution:
            operation = "create" if has_execution or has_directory or has_executable_artifact else "fix"
            if has_project_repair:
                operation = "fix"
                intent_type = "patch_request"
                confidence = 0.86
            elif has_directory or any(term in lowered_prompt for term in {"arquivo", "ficheiro", "file"}):
                intent_type = "filesystem_write_request"
                confidence = 0.84
            elif has_strong_executable_artifact:
                intent_type = "artifact_build_request"
                confidence = 0.84
            elif "android" in lowered_prompt and has_project:
                intent_type = "android_project_generation"
                confidence = 0.84
            elif has_project and operation == "create":
                intent_type = "project_generation_request"
                confidence = 0.82
            elif semantic_graph.state_effect == "proposal_only":
                intent_type = "patch_request"
                confidence = 0.82
            else:
                intent_type = "patch_request"
                confidence = 0.8
        elif output_intent.channel == "artifact" and not semantic_graph.readonly_contract:
            operation = "create"
            intent_type = "artifact_generation"
            obj = "report" if obj == "unknown" else obj
            confidence = 0.8
        elif self_reference and has_capability:
            operation = "list"
            intent_type = "capability_explanation"
            confidence = 0.9
        elif self_reference and (has_architecture or has_info):
            operation = "explain"
            intent_type = "self_analysis"
            confidence = 0.88
        elif has_web_search or (not self_reference and has_public_fact and (has_info or prompt.strip().endswith("?"))):
            operation = "search"
            intent_type = "public_fact_query"
            confidence = 0.84
        elif self.concept_matcher.has_type(matches, "output_chat_summary"):
            operation = "summarize"
            intent_type = "in_chat_final_report"
            obj = "report"
            confidence = 0.85
        elif has_validation:
            operation = "validate"
            intent_type = "validation_request"
            confidence = 0.8
        elif has_memory:
            operation = "remember"
            intent_type = "memory_write"
            obj = "memory"
            confidence = 0.75
        elif has_retrieval:
            operation = "search"
            intent_type = "rag_query"
            confidence = 0.7
        elif (semantic_graph.observational_intent or semantic_graph.knowledge_output or has_analysis or has_info) and has_project:
            operation = "analyze" if has_analysis else "explain"
            intent_type = "readonly_analysis"
            confidence = 0.82
        elif has_info or prompt.strip().endswith("?"):
            operation = "explain"
            intent_type = "conversation"
            confidence = 0.72
        elif prompt.strip():
            intent_type = "conversation"
            operation = "unknown"
            confidence = 0.55

        defaults = self._intent_defaults(intent_type)
        task_type: TaskType = "none"
        if intent_type == "readonly_analysis":
            task_type = "readonly_analysis"
        elif intent_type == "artifact_generation":
            task_type = "artifact_generation"
        elif intent_type == "filesystem_write_request":
            task_type = "filesystem_write"
        elif intent_type == "file_modification_request":
            task_type = "file_modification"
        elif intent_type in {"project_generation_request", "android_project_generation"}:
            task_type = "project_generation"
        elif intent_type == "artifact_build_request":
            task_type = "artifact_build"
        elif intent_type == "patch_request":
            task_type = "patch_request"
        elif intent_type == "validation_request":
            task_type = "validation"
        elif intent_type == "memory_write":
            task_type = "memory_curation"
        requested_actions = self._actions_for_intent(intent_type, defaults, output_intent, semantic_graph=semantic_graph)
        requested_actions = self._apply_action_constraints(requested_actions, matches)
        return IntentClassification(
            intent_type=intent_type,
            task_type=task_type,
            actor=actor,
            operation=operation,
            object=obj,
            requires_task=bool(defaults.get("requires_task", False)),
            requires_workspace=bool(defaults.get("requires_workspace", False)),
            requires_approval=bool(defaults.get("requires_approval", False)),
            requested_actions=requested_actions,
            confidence=confidence,
            semantic_graph=semantic_graph,
        )

    def _matches_deferred_creation_conversation(self, lowered_prompt: str) -> bool:
        config = self._classification_overrides().get("deferred_creation_conversation", {})
        if not isinstance(config, dict):
            return False
        signal_terms = [str(item).casefold() for item in config.get("signal_terms", []) or []]
        defer_terms = [str(item).casefold() for item in config.get("defer_terms", []) or []]
        return any(term and term in lowered_prompt for term in signal_terms) and any(term and term in lowered_prompt for term in defer_terms)

    def _has_override_term(self, lowered_prompt: str, override_name: str, terms_key: str) -> bool:
        config = self._classification_overrides().get(override_name, {})
        if not isinstance(config, dict):
            return False
        terms = [str(item).casefold() for item in config.get(terms_key, []) or []]
        return any(term and term in lowered_prompt for term in terms)

    def _actions_for_intent(
        self,
        intent_type: str,
        defaults: dict[str, object],
        output_intent: OutputIntent,
        *,
        semantic_graph: SemanticIntentGraph,
    ) -> list[str]:
        actions = [str(action) for action in defaults.get("default_actions", []) or []]
        if (
            intent_type not in {"conversation", "self_analysis", "capability_explanation", "in_chat_final_report", "public_fact_query", "rag_query", "memory_request"}
            and (output_intent.should_save_file or output_intent.channel in {"artifact", "task_report"})
            and not semantic_graph.readonly_contract
            and semantic_graph.state_effect not in {"knowledge_only", "planning_only"}
        ):
            actions.append("write_files")
        return list(dict.fromkeys(action for action in actions if action.strip()))

    def _apply_action_constraints(self, actions: list[str], matches: list[ConceptMatch]) -> list[str]:
        if self._config is None:
            self.load()
        configured = (self._config or {}).get("action_constraints", {})
        if not isinstance(configured, dict):
            return actions
        matched_concepts = {match.concept_id for match in matches}
        constrained = list(actions)
        for raw_rule in configured.values():
            if not isinstance(raw_rule, dict):
                continue
            concept_ids = {str(item) for item in raw_rule.get("concept_ids", []) or []}
            if not concept_ids.intersection(matched_concepts):
                continue
            allowed = {str(item) for item in raw_rule.get("allowed_actions", []) or []}
            denied = {str(item) for item in raw_rule.get("denied_actions", []) or []}
            if allowed:
                constrained = [action for action in constrained if action in allowed]
            if denied:
                constrained = [action for action in constrained if action not in denied]
        return list(dict.fromkeys(constrained))

    def status(self) -> dict[str, object]:
        try:
            return {"status": "ok", "intents": len(self.taxonomy)}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}
