from __future__ import annotations

import json
from difflib import SequenceMatcher
from typing import Any

from aipinho.schemas.models.inference_observability import (
    CanonicalInferenceInputArtifact,
    CanonicalInferenceOutputArtifact,
    CompletenessAnalysis,
    ContextBudgetArtifact,
    InferenceInputDoctorReport,
    PromptDiffArtifact,
)


class CompletenessAnalyzer:
    REQUIRED_FIELDS = {
        "observed_behavior": "PROMPT_OBSERVED_BEHAVIOR_MISSING",
        "expected_behavior": "PROMPT_EXPECTED_BEHAVIOR_MISSING",
        "symbol_targets": "PROMPT_SYMBOL_MISSING",
        "file_targets": "PROMPT_TARGET_FILE_MISSING",
        "code_snippets": "PROMPT_CODE_SNIPPET_MISSING",
        "output_schema": "PROMPT_OUTPUT_SCHEMA_MISSING",
        "evidence_used": "PROMPT_EVIDENCE_MISSING",
        "diagnosis_ids": "PROMPT_DIAGNOSIS_MISSING",
        "patch_candidate_id": "PROMPT_PATCH_CANDIDATE_MISSING",
    }

    def analyze(self, artifact: CanonicalInferenceInputArtifact) -> CompletenessAnalysis:
        present: list[str] = []
        missing: list[str] = []
        reason_codes: list[str] = []
        values = {
            "observed_behavior": artifact.metadata.get("observed_behavior"),
            "expected_behavior": artifact.metadata.get("expected_behavior"),
            "symbol_targets": artifact.symbol_targets,
            "file_targets": artifact.file_targets,
            "code_snippets": artifact.code_snippets,
            "output_schema": artifact.output_schema,
            "evidence_used": artifact.evidence_used,
            "diagnosis_ids": artifact.diagnosis_ids,
            "patch_candidate_id": artifact.patch_candidate_id,
        }
        for field, reason in self.REQUIRED_FIELDS.items():
            value = values.get(field)
            if self._has_value(value):
                present.append(field)
            else:
                missing.append(field)
                reason_codes.append(reason)
        score = int(round((len(present) / max(1, len(self.REQUIRED_FIELDS))) * 100))
        confidence = "alta" if score >= 80 else "media" if score >= 50 else "baixa"
        if missing:
            reason_codes.insert(0, "INFERENCE_INPUT_INCOMPLETE")
        return CompletenessAnalysis(score=score, confidence=confidence, missing=missing, present=present, reason_codes=list(dict.fromkeys(reason_codes)))

    def _has_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True


class PromptDiffAnalyzer:
    def analyze(self, artifact: CanonicalInferenceInputArtifact) -> PromptDiffArtifact:
        matcher = SequenceMatcher(a=artifact.prompt_original, b=artifact.prompt_final)
        removed: list[str] = []
        for tag, start_a, end_a, _start_b, _end_b in matcher.get_opcodes():
            if tag in {"delete", "replace"}:
                fragment = artifact.prompt_original[start_a:end_a].strip()
                if fragment:
                    removed.append(fragment[:240])
        return PromptDiffArtifact(
            original_chars=len(artifact.prompt_original),
            final_chars=len(artifact.prompt_final),
            removed_items=list(dict.fromkeys(removed[:20])),
            truncated_items=list(artifact.truncated_items),
            omitted_artifacts=list(artifact.metadata.get("omitted_artifacts") or []),
            omitted_snippets=list(artifact.metadata.get("omitted_snippets") or []),
            omitted_symbols=list(artifact.metadata.get("omitted_symbols") or []),
        )


class ContextBudgetAnalyzer:
    def analyze(self, artifact: CanonicalInferenceInputArtifact) -> ContextBudgetArtifact:
        budget = artifact.context_budget
        actual = len(artifact.prompt_final)
        role_limit = budget.role_limit_chars
        provider_limit = budget.provider_limit_chars
        discarded = 0
        if role_limit is not None and actual > role_limit:
            discarded = actual - role_limit
        if provider_limit is not None and actual > provider_limit:
            discarded = max(discarded, actual - provider_limit)
        return budget.model_copy(
            update={
                "actual_chars": actual,
                "estimated_tokens": max(1, actual // 4) if actual else 0,
                "discarded_chars": max(0, int(budget.discarded_chars or 0), discarded),
                "truncated_items": list(dict.fromkeys([*budget.truncated_items, *artifact.truncated_items])),
            }
        )


class InferenceInputDoctorService:
    def __init__(
        self,
        completeness: CompletenessAnalyzer | None = None,
        prompt_diff: PromptDiffAnalyzer | None = None,
        context_budget: ContextBudgetAnalyzer | None = None,
    ) -> None:
        self.completeness = completeness or CompletenessAnalyzer()
        self.prompt_diff = prompt_diff or PromptDiffAnalyzer()
        self.context_budget = context_budget or ContextBudgetAnalyzer()

    def analyze(
        self,
        input_artifact: CanonicalInferenceInputArtifact,
        output_artifact: CanonicalInferenceOutputArtifact | None = None,
    ) -> InferenceInputDoctorReport:
        completeness = self.completeness.analyze(input_artifact)
        prompt_diff = self.prompt_diff.analyze(input_artifact)
        context_budget = self.context_budget.analyze(input_artifact)
        reason_codes = [*completeness.reason_codes]
        diagnostics: list[str] = []
        if prompt_diff.truncated_items:
            reason_codes.append("PROMPT_CONTEXT_TRUNCATED")
            diagnostics.append("Prompt/context truncation recorded with item-level details.")
        if output_artifact is not None and output_artifact.empty_output:
            reason_codes.append("INFERENCE_EMPTY_OUTPUT")
            diagnostics.extend(output_artifact.diagnostics)
            if not output_artifact.replacement_detected:
                reason_codes.append("PATCH_MODEL_EMPTY_OUTPUT")
        status = "PASS" if not reason_codes else "WARN"
        return InferenceInputDoctorReport(
            status=status,
            completeness=completeness,
            prompt_diff=prompt_diff,
            context_budget=context_budget,
            reason_codes=list(dict.fromkeys(reason_codes)),
            diagnostics=list(dict.fromkeys(diagnostics)),
        )

    def parse_output(self, raw_output: str) -> tuple[Any, bool, list[str]]:
        diagnostics: list[str] = []
        if not raw_output.strip():
            return None, False, ["raw_output_empty"]
        try:
            parsed = json.loads(raw_output)
            return parsed, True, diagnostics
        except (TypeError, ValueError):
            diagnostics.append("json_parse_failed")
            return None, False, diagnostics
