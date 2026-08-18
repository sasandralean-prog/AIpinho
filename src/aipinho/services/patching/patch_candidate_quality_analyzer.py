from __future__ import annotations

from typing import Any

from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_observability import QualityAnalysis


class PatchCandidateQualityAnalyzer:
    REQUIRED = {
        "target_file": "PATCH_CANDIDATE_TARGET_FILE_MISSING",
        "target_symbol": "PATCH_CANDIDATE_SYMBOL_MISSING",
        "observed_behavior": "PROMPT_OBSERVED_BEHAVIOR_MISSING",
        "expected_behavior": "PROMPT_EXPECTED_BEHAVIOR_MISSING",
        "evidence_refs": "PATCH_CANDIDATE_EVIDENCE_MISSING",
        "confidence": "PATCH_CANDIDATE_CONFIDENCE_MISSING",
        "diagnosis_id": "PATCH_CANDIDATE_WITHOUT_DIAGNOSIS",
        "current_content_excerpt": "PROMPT_CODE_SNIPPET_MISSING",
    }

    def analyze(self, candidate: PatchCandidateArtifact) -> QualityAnalysis:
        values: dict[str, Any] = {
            "target_file": candidate.target_file,
            "target_symbol": candidate.target_symbol,
            "observed_behavior": candidate.observed_behavior,
            "expected_behavior": candidate.expected_behavior,
            "evidence_refs": candidate.evidence_refs,
            "confidence": candidate.confidence > 0,
            "diagnosis_id": candidate.diagnosis_id,
            "current_content_excerpt": candidate.current_content_excerpt,
        }
        present: list[str] = []
        missing: list[str] = []
        reason_codes: list[str] = []
        for field, reason in self.REQUIRED.items():
            if self._has_value(values.get(field)):
                present.append(field)
            else:
                missing.append(field)
                reason_codes.append(reason)
        score = int(round((len(present) / max(1, len(self.REQUIRED))) * 100))
        if missing:
            reason_codes.insert(0, "PATCH_CANDIDATE_TOO_WEAK")
        return QualityAnalysis(
            score=score,
            confidence="alta" if score >= 80 else "media" if score >= 50 else "baixa",
            present=present,
            missing=missing,
            reason_codes=list(dict.fromkeys(reason_codes)),
            diagnostics=[f"missing:{item}" for item in missing],
        )

    def _has_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return bool(value)
