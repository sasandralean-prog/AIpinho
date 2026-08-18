from __future__ import annotations

import re
from dataclasses import dataclass

from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact, RepairIntent


@dataclass(frozen=True)
class _RepairPattern:
    reason_code: str
    terms: tuple[str, ...]
    expected_template: str
    success_template: str


_PATTERNS: tuple[_RepairPattern, ...] = (
    _RepairPattern(
        reason_code="REPAIR_INTENT_BOUNDS_RESOLVED",
        terms=("indexoutofbounds", "out of bounds", "bounds", "boundary", "indice", "limite", "array index"),
        expected_template="{target} must validate boundaries before indexed access and use the existing failure contract when input is shorter than required.",
        success_template="{target} no longer performs indexed access without a preceding boundary check.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_EOF_RESOLVED",
        terms=("eof", "end of file", "truncated", "incomplete", "partial stream", "stream incompleto", "arquivo incompleto"),
        expected_template="{target} must detect incomplete input before reading past available data and return through the existing error path.",
        success_template="{target} handles incomplete input without uncaught exceptions or invalid reads.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_NULL_RESOLVED",
        terms=("nullpointer", "none", "null", "nulo", "missing value", "valor ausente"),
        expected_template="{target} must handle missing values through the existing no-value or error contract instead of dereferencing them.",
        success_template="{target} does not dereference missing values for valid guarded inputs.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_TIMEOUT_RESOLVED",
        terms=("timeout", "timed out", "latency", "hung", "travou", "bloqueado por tempo"),
        expected_template="{target} must stop the operation through the configured timeout path when execution exceeds the allowed budget.",
        success_template="{target} exits through the timeout contract when the configured budget is exceeded.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_CACHE_RESOLVED",
        terms=("cache", "stale", "stale value", "valor antigo", "invalidation", "invalidacao", "inconsistente"),
        expected_template="{target} must prevent stale reads after invalidation and expose only the current value through the existing access contract.",
        success_template="{target} no longer returns stale data after invalidation.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_PARSE_RESOLVED",
        terms=("parse", "parser", "json", "yaml", "decode", "deserialize", "serializar", "desserializar"),
        expected_template="{target} must reject malformed input through the existing parse error contract and preserve valid input behavior.",
        success_template="{target} reports malformed input consistently while preserving valid parse results.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_MEDIA_FORMAT_RESOLVED",
        terms=("codec", "container", "format", "decoder", "media", "aac", "m4a", "mp4", "sample rate", "bitrate"),
        expected_template="{target} must derive media handling from detected container and codec metadata instead of relying on extension or format assumptions.",
        success_template="{target} selects the media handling path from detected metadata and preserves supported formats.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_PERMISSION_RESOLVED",
        terms=("permission", "approval", "deny", "forbidden", "unauthorized", "permissao", "aprovacao"),
        expected_template="{target} must enforce the existing policy decision before performing the guarded operation.",
        success_template="{target} blocks or requests approval according to the effective policy decision before side effects occur.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_VALIDATION_RESOLVED",
        terms=("validation", "validacao", "invalid", "required output", "missing artifact", "artifact missing"),
        expected_template="{target} must report missing or invalid required outputs through the existing validation contract.",
        success_template="{target} produces validation state that matches the required output contract.",
    ),
    _RepairPattern(
        reason_code="REPAIR_INTENT_EXCEPTION_RESOLVED",
        terms=("exception", "erro", "error", "crash", "falha", "stacktrace", "uncaught"),
        expected_template="{target} must route the observed failure through the existing error contract instead of allowing an uncaught exception.",
        success_template="{target} converts the observed failure into the existing governed error result.",
    ),
)

_GENERIC_EXPECTED_TERMS = {
    "apply",
    "aplicar",
    "artefato",
    "artifact",
    "artifacts",
    "candidate",
    "candidato",
    "concrete",
    "correcao",
    "correction",
    "diff",
    "evidence",
    "evidencia",
    "file",
    "fix",
    "function",
    "generate",
    "gerar",
    "patch",
    "plan",
    "planning",
    "preview",
    "replacement",
    "risco",
    "rollback",
    "safe",
    "strategy",
    "target",
}

_OPERATIONAL_EXPECTED_BEHAVIOR_MARKERS = {
    "artifact",
    "artifacts",
    "approval",
    "completion",
    "contract",
    "diff",
    "fase",
    "generate",
    "gerar",
    "patch plan",
    "patch planning",
    "patch preview",
    "phase",
    "report",
    "reports/",
    "responder",
    "rollback",
    "speaker truth",
    "success contract",
    "task run",
    "taskrun",
    "validation",
}


class RepairIntentResolver:
    """Deterministically enriches canonical diagnoses with repair intent."""

    def enrich(self, diagnosis: CanonicalDiagnosisArtifact) -> CanonicalDiagnosisArtifact:
        localization = diagnosis.technical_localization[0] if diagnosis.technical_localization else None
        target_file = localization.target_file if localization else ""
        target_symbol = localization.target_symbol if localization else ""
        target = self._target_label(target_file, target_symbol)
        evidence_refs = [item.evidence_id for item in diagnosis.evidence if item.evidence_id]
        reason_codes = list(diagnosis.reason_codes)

        existing = diagnosis.repair_intent
        if existing and self._is_usable_target_specific(existing.expected_behavior, target_file, target_symbol):
            return diagnosis.model_copy(
                update={
                    "expected_behavior": existing.expected_behavior,
                    "reason_codes": self._append_unique(reason_codes, existing.reason_codes),
                }
            )

        if self._is_usable_target_specific(diagnosis.expected_behavior, target_file, target_symbol):
            intent = RepairIntent(
                target_file=target_file,
                target_symbol=target_symbol,
                expected_behavior=diagnosis.expected_behavior.strip(),
                repair_boundary=self._repair_boundary(target),
                success_condition=diagnosis.expected_behavior.strip(),
                evidence_refs=evidence_refs,
                confidence=max(diagnosis.confidence, localization.confidence if localization else 0.0),
                reason_codes=["REPAIR_INTENT_RESOLVED_FROM_DIAGNOSIS"],
            )
            return diagnosis.model_copy(
                update={
                    "repair_intent": intent,
                    "reason_codes": self._append_unique(reason_codes, intent.reason_codes),
                }
            )

        pattern = self._match_pattern(diagnosis)
        if pattern and target:
            expected = pattern.expected_template.format(target=target)
            success = pattern.success_template.format(target=target)
            intent = RepairIntent(
                target_file=target_file,
                target_symbol=target_symbol,
                expected_behavior=expected,
                repair_boundary=self._repair_boundary(target),
                success_condition=success,
                evidence_refs=evidence_refs,
                confidence=max(diagnosis.confidence, localization.confidence if localization else 0.0),
                reason_codes=[pattern.reason_code],
            )
            return diagnosis.model_copy(
                update={
                    "expected_behavior": expected,
                    "repair_intent": intent,
                    "reason_codes": self._append_unique(reason_codes, intent.reason_codes),
                }
            )

        missing = ["REPAIR_INTENT_MISSING"]
        if not target:
            missing.append("REPAIR_INTENT_TARGET_MISSING")
        if self._looks_operational(diagnosis.expected_behavior):
            missing.append("REPAIR_INTENT_EXPECTED_BEHAVIOR_OPERATIONAL")
        if not self._is_usable_target_specific(diagnosis.expected_behavior, target_file, target_symbol):
            missing.append("TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING")
        return diagnosis.model_copy(update={"reason_codes": self._append_unique(reason_codes, missing)})

    def _match_pattern(self, diagnosis: CanonicalDiagnosisArtifact) -> _RepairPattern | None:
        text = self._diagnosis_text(diagnosis)
        for pattern in _PATTERNS:
            if any(term in text for term in pattern.terms):
                return pattern
        return None

    def _diagnosis_text(self, diagnosis: CanonicalDiagnosisArtifact) -> str:
        values = [
            diagnosis.diagnosis_type,
            diagnosis.semantic_goal,
            diagnosis.observed_behavior,
            diagnosis.expected_behavior,
            " ".join(diagnosis.reason_codes),
            " ".join(item.summary for item in diagnosis.evidence),
            " ".join(hint.strategy for hint in diagnosis.repair_hints),
            " ".join(constraint for hint in diagnosis.repair_hints for constraint in hint.constraints),
        ]
        return " ".join(str(value or "") for value in values).casefold()

    def _repair_boundary(self, target: str) -> list[str]:
        return [
            f"Limit changes to {target} unless the canonical patch plan requires another bound target.",
            "Preserve public APIs and external contracts.",
            "Preserve existing return formats.",
            "Do not introduce side effects outside the selected technical target.",
        ]

    def _is_usable_target_specific(self, value: str, target_file: str, target_symbol: str) -> bool:
        return self._is_target_specific(value, target_file, target_symbol) and not self._looks_operational(value)

    def _is_target_specific(self, value: str, target_file: str, target_symbol: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        target_terms = self._target_terms(target_file, target_symbol)
        if not target_terms or not any(term in text.replace("\\", "/").casefold() for term in target_terms):
            return False
        specific_terms = [
            token.casefold()
            for token in re.findall(r"[A-Za-z0-9_]{4,}", text)
            if token.casefold() not in _GENERIC_EXPECTED_TERMS
        ]
        return len(set(specific_terms)) >= 2

    def _looks_operational(self, value: str) -> bool:
        text = str(value or "").replace("\\", "/").casefold()
        if not text:
            return False
        marker_count = sum(1 for marker in _OPERATIONAL_EXPECTED_BEHAVIOR_MARKERS if marker in text)
        artifact_shape = bool(re.search(r"(^|[/\s])[^/\s]+\.(md|csv|json|zip)\b", text))
        return marker_count >= 2 or (artifact_shape and marker_count >= 1)

    def _target_label(self, target_file: str, target_symbol: str) -> str:
        symbol = str(target_symbol or "").strip()
        file = str(target_file or "").strip()
        if symbol and self._normalize(symbol) != self._normalize(file):
            return symbol
        if file:
            return file.replace("\\", "/").rsplit("/", 1)[-1]
        return symbol

    def _target_terms(self, target_file: str, target_symbol: str) -> set[str]:
        terms: set[str] = set()
        for value in (target_file, target_symbol, self._target_label(target_file, target_symbol)):
            normalized = str(value or "").replace("\\", "/").casefold()
            if not normalized:
                continue
            terms.add(normalized)
            filename = normalized.rsplit("/", 1)[-1]
            if filename:
                terms.add(filename)
                stem = filename.rsplit(".", 1)[0]
                if stem:
                    terms.add(stem)
            for part in re.split(r"[/._\-]+", normalized):
                if len(part) >= 3:
                    terms.add(part)
        return {term for term in terms if len(term) >= 3}

    def _normalize(self, value: str) -> str:
        return str(value or "").replace("\\", "/").strip().casefold()

    def _append_unique(self, base: list[str], extra: list[str]) -> list[str]:
        return list(dict.fromkeys([*base, *extra]))
