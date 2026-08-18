from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.intent.ambiguity import AmbiguityResult
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatch, ConceptMatcher
from aipinho.utils.yaml_loader import load_yaml_file


class AmbiguityDetector:
    def __init__(self, config_path: Path | None = None, concept_matcher: ConceptMatcher | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "ambiguity_policy.yaml"
        self.concept_matcher = concept_matcher or ConceptMatcher().load()
        self._config: dict[str, object] | None = None

    def load(self) -> "AmbiguityDetector":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, object]:
        if self._config is None:
            self.load()
        return self._config or {}

    def detect(
        self,
        prompt: str,
        matches: list[ConceptMatch],
        *,
        workspace_requires_clarification: bool,
        workspace_resolved: bool = False,
        confidence: float,
        is_operational: bool,
    ) -> AmbiguityResult:
        reasons: list[str] = []
        ambiguity_config = self.config.get("ambiguity", {}) if isinstance(self.config.get("ambiguity", {}), dict) else {}
        has_light_marker = self.concept_matcher.has_type(matches, "ambiguity_marker")
        has_mutation = self.concept_matcher.has_type(matches, "operation_mutation")
        operational_required = bool(ambiguity_config.get("operational_markers_required_for_light_ambiguity", True))
        light_marker_applies = is_operational if operational_required else (is_operational or has_mutation)
        if has_light_marker and light_marker_applies:
            reasons.append("contextual_ambiguity_marker")
        mutation_target_check = bool(ambiguity_config.get("mutation_without_target_requires_clarification", True))
        if mutation_target_check and is_operational and has_mutation and not workspace_resolved and not any(match.concept_type in {"object", "actor"} for match in matches):
            reasons.append("mutation_without_clear_target")
        if workspace_requires_clarification:
            reasons.append("workspace_reference_requires_clarification")
        threshold = float(ambiguity_config.get("low_confidence_threshold", 0.45))
        if confidence < threshold:
            reasons.append("low_confidence")
        is_ambiguous = bool(reasons)
        question = None
        if is_ambiguous:
            questions = ambiguity_config.get("clarifying_questions", {}) if isinstance(ambiguity_config.get("clarifying_questions", {}), dict) else {}
            question = str(questions.get("workspace" if workspace_requires_clarification else "default", "Você pode esclarecer o objetivo?"))
        return AmbiguityResult(is_ambiguous=is_ambiguous, requires_clarification=is_ambiguous, reasons=reasons, clarifying_question=question)
