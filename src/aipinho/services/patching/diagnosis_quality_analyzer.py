from __future__ import annotations

from typing import Any

from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact
from aipinho.schemas.patching.patch_observability import QualityAnalysis


class DiagnosisQualityAnalyzer:
    REQUIRED = {
        "symbol": "DIAGNOSIS_SYMBOL_MISSING",
        "target_file": "DIAGNOSIS_TARGET_FILE_MISSING",
        "observed_behavior": "PROMPT_OBSERVED_BEHAVIOR_MISSING",
        "expected_behavior": "PROMPT_EXPECTED_BEHAVIOR_MISSING",
        "hypothesis": "DIAGNOSIS_HYPOTHESIS_MISSING",
        "confidence": "DIAGNOSIS_CONFIDENCE_MISSING",
        "evidence": "DIAGNOSIS_EVIDENCE_MISSING",
    }

    def analyze(self, diagnosis: CanonicalDiagnosisArtifact) -> QualityAnalysis:
        localization = diagnosis.technical_localization[0] if diagnosis.technical_localization else None
        values: dict[str, Any] = {
            "symbol": localization.target_symbol if localization else "",
            "target_file": localization.target_file if localization else "",
            "observed_behavior": diagnosis.observed_behavior,
            "expected_behavior": diagnosis.expected_behavior,
            "hypothesis": diagnosis.semantic_goal or diagnosis.reason_codes,
            "confidence": diagnosis.confidence > 0,
            "evidence": diagnosis.evidence,
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
            reason_codes.insert(0, "DIAGNOSIS_TOO_GENERIC")
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
