from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.intent.prompt_segment import PromptSegment
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatcher
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService


class PromptSegmenter:
    def __init__(
        self,
        concept_matcher: ConceptMatcher | None = None,
        path_extractor: PathExtractionService | None = None,
    ) -> None:
        self.concept_matcher = concept_matcher or ConceptMatcher().load()
        self.path_extractor = path_extractor or PathExtractionService()

    def segment(self, prompt: str) -> list[PromptSegment]:
        segments: list[PromptSegment] = []
        normalized = self.concept_matcher.normalize(prompt)
        for path in self.path_extractor.extract(prompt):
            segments.append(PromptSegment(
                segment_id=f"seg_{uuid4().hex}",
                kind="path",
                text=path.value,
                start=path.start,
                end=path.end,
                confidence=1.0,
            ))
        matches = self.concept_matcher.match(prompt)
        if self.concept_matcher.has_type(matches, "constraint"):
            segments.append(PromptSegment(segment_id=f"seg_{uuid4().hex}", kind="constraint", text="no_write", confidence=0.9))
        if self.concept_matcher.has_type(matches, "output_artifact") or self.concept_matcher.has_type(matches, "output_chat_summary"):
            segments.append(PromptSegment(segment_id=f"seg_{uuid4().hex}", kind="output_request", text=prompt, confidence=0.8))
        if prompt.strip().endswith("?") or normalized.startswith(("como ", "o que ", "quais ", "qual ")):
            segments.append(PromptSegment(segment_id=f"seg_{uuid4().hex}", kind="question", text=prompt, confidence=0.8))
        if any(match.concept_type.startswith("operation_") for match in matches):
            segments.append(PromptSegment(segment_id=f"seg_{uuid4().hex}", kind="command", text=prompt, confidence=0.7))
        if not segments:
            segments.append(PromptSegment(segment_id=f"seg_{uuid4().hex}", kind="main_request", text=prompt, start=0, end=len(prompt), confidence=0.5))
        return segments
