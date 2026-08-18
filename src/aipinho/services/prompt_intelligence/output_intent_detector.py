from __future__ import annotations

from aipinho.schemas.intent.intent_map import OutputIntent
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatch, ConceptMatcher


class OutputIntentDetector:
    def __init__(self, concept_matcher: ConceptMatcher | None = None) -> None:
        self.concept_matcher = concept_matcher or ConceptMatcher().load()

    def detect(self, prompt: str, matches: list[ConceptMatch]) -> OutputIntent:
        normalized = self.concept_matcher.normalize(prompt)
        has_artifact = self.concept_matcher.has_type(matches, "output_artifact") or self.concept_matcher.has_type(matches, "operation_artifact")
        has_chat_report = self.concept_matcher.has_type(matches, "output_chat_summary")
        if has_artifact:
            fmt = "markdown" if ".md" in normalized or "markdown" in normalized else "file"
            return OutputIntent(channel="artifact", format=fmt, should_save_file=True)
        if has_chat_report:
            return OutputIntent(channel="chat", format="text", should_save_file=False)
        return OutputIntent(channel="chat", format="text", should_save_file=False)