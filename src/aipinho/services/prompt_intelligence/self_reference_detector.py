from __future__ import annotations

from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatch, ConceptMatcher


class SelfReferenceDetector:
    def __init__(self, concept_matcher: ConceptMatcher | None = None) -> None:
        self.concept_matcher = concept_matcher or ConceptMatcher().load()

    def is_self_reference(self, matches: list[ConceptMatch], *, workspace_declared: bool) -> bool:
        if workspace_declared:
            return False
        has_self_actor = self.concept_matcher.has_type(matches, "actor") and any(match.concept_id == "self_actor" for match in matches)
        has_project_actor = any(match.concept_id in {"workspace_actor", "project_object"} for match in matches)
        return has_self_actor and not has_project_actor