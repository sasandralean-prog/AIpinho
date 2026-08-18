from __future__ import annotations

import re

from aipinho.schemas.patching.canonical_diagnosis_artifact import (
    CanonicalDiagnosisArtifact,
    DiagnosisEvidenceRef,
    DiagnosisMetadata,
    RepairHint,
    TechnicalLocalization,
)
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_evidence import PatchEvidence


class PatchCandidateBuilder:
    """Deterministically translates canonical diagnoses into patch candidates."""

    REPAIR_INTENT_STRATEGY_TEMPLATES = {
        "REPAIR_INTENT_BOUNDS_RESOLVED": (
            "Edit {target} to validate bounds before indexed or offset-based reads and route insufficient input through the existing failure contract."
        ),
        "REPAIR_INTENT_EOF_RESOLVED": (
            "Edit {target} to detect incomplete input before consuming bytes past the available range and reuse the existing short-input or error path."
        ),
        "REPAIR_INTENT_NULL_RESOLVED": (
            "Edit {target} to guard missing values before dereference and return through the existing no-value or error contract."
        ),
        "REPAIR_INTENT_TIMEOUT_RESOLVED": (
            "Edit {target} to stop work through the configured timeout path instead of allowing execution to continue past the allowed budget."
        ),
        "REPAIR_INTENT_CACHE_RESOLVED": (
            "Edit {target} so invalidation removes stale state before the next read and keep the current access contract unchanged."
        ),
        "REPAIR_INTENT_PARSE_RESOLVED": (
            "Edit {target} to reject malformed input through the existing parse error path while preserving valid parse behavior."
        ),
        "REPAIR_INTENT_MEDIA_FORMAT_RESOLVED": (
            "Edit {target} so media handling is selected from detected container and codec metadata instead of extension-based assumptions."
        ),
        "REPAIR_INTENT_PERMISSION_RESOLVED": (
            "Edit {target} to enforce the effective policy decision before the guarded side effect occurs."
        ),
        "REPAIR_INTENT_VALIDATION_RESOLVED": (
            "Edit {target} to surface missing or invalid required outputs through the existing validation contract."
        ),
        "REPAIR_INTENT_EXCEPTION_RESOLVED": (
            "Edit {target} to convert the observed failure into the existing governed error result instead of allowing an uncaught exception."
        ),
    }
    REPAIR_STRATEGY_TERM_PATTERNS = (
        ("REPAIR_INTENT_BOUNDS_RESOLVED", ("indexoutofbounds", "out of bounds", "bounds", "boundary", "indice", "limite", "array index")),
        ("REPAIR_INTENT_EOF_RESOLVED", ("eof", "end of file", "truncated", "incomplete", "partial stream", "stream incompleto", "arquivo incompleto")),
        ("REPAIR_INTENT_NULL_RESOLVED", ("nullpointer", "none", "null", "nulo", "missing value", "valor ausente")),
        ("REPAIR_INTENT_TIMEOUT_RESOLVED", ("timeout", "timed out", "latency", "hung", "travou", "bloqueado por tempo")),
        ("REPAIR_INTENT_CACHE_RESOLVED", ("cache", "stale", "stale value", "valor antigo", "invalidation", "invalidacao", "inconsistente")),
        ("REPAIR_INTENT_PARSE_RESOLVED", ("parse", "parser", "json", "yaml", "decode", "deserialize", "serializar", "desserializar")),
        ("REPAIR_INTENT_MEDIA_FORMAT_RESOLVED", ("codec", "container", "format", "decoder", "media", "aac", "m4a", "mp4", "sample rate", "bitrate")),
        ("REPAIR_INTENT_PERMISSION_RESOLVED", ("permission", "approval", "deny", "forbidden", "unauthorized", "permissao", "aprovacao")),
        ("REPAIR_INTENT_VALIDATION_RESOLVED", ("validation", "validacao", "invalid", "required output", "missing artifact", "artifact missing")),
        ("REPAIR_INTENT_EXCEPTION_RESOLVED", ("exception", "erro", "error", "crash", "falha", "stacktrace", "uncaught")),
    )

    OPERATIONAL_EXPECTED_BEHAVIOR_MARKERS = (
        "artifact",
        "artifacts",
        "approval",
        "completion",
        "contract",
        "csv",
        "diff",
        "fase",
        "generate",
        "gerar",
        "markdown",
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
        "zip",
    )

    def from_diagnosis(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        *,
        current_content_by_path: dict[str, str] | None = None,
    ) -> list[PatchCandidateArtifact]:
        current_content_by_path = current_content_by_path or {}
        candidates: list[PatchCandidateArtifact] = []
        evidence_refs = [item.evidence_id for item in diagnosis.evidence if item.evidence_id]
        constraints = [
            constraint
            for hint in diagnosis.repair_hints
            for constraint in hint.constraints
            if constraint
        ]
        if diagnosis.repair_intent:
            constraints.extend(diagnosis.repair_intent.repair_boundary)
        for localization in diagnosis.technical_localization:
            if not localization.target_file or not localization.target_symbol:
                continue
            repair_intent = self._matching_repair_intent(diagnosis, localization)
            expected_behavior = self._expected_behavior(diagnosis, repair_intent)
            semantic_goal = self._semantic_goal(diagnosis, repair_intent)
            strategy = self._replacement_strategy(diagnosis, localization, repair_intent=repair_intent)
            current = current_content_by_path.get(localization.target_file) or current_content_by_path.get(localization.target_file.replace("\\", "/"))
            excerpt = self._current_excerpt(current, localization)
            candidates.append(
                PatchCandidateArtifact(
                    diagnosis_id=diagnosis.diagnosis_id,
                    workspace=diagnosis.workspace or localization.workspace,
                    task_run_id=diagnosis.metadata.task_run_id,
                    execution_plan_id=diagnosis.metadata.execution_plan_id,
                    semantic_goal=semantic_goal,
                    target_file=localization.target_file,
                    target_symbol=localization.target_symbol,
                    symbol_kind=localization.symbol_kind,
                    observed_behavior=diagnosis.observed_behavior,
                    expected_behavior=expected_behavior,
                    evidence_refs=evidence_refs,
                    risk_level="medium",
                    confidence=min(1.0, max(diagnosis.confidence, localization.confidence)),
                    optional_constraints=list(dict.fromkeys(constraints)),
                    replacement_strategy=strategy,
                    current_content_excerpt=excerpt,
                    technical_context={
                        "region_hint": localization.region_hint,
                        "diagnosis_type": diagnosis.diagnosis_type,
                        "reason_codes": list(diagnosis.reason_codes),
                        "localized_excerpt": bool(excerpt and current and excerpt != current[:1200]),
                        "repair_intent": repair_intent.model_dump(mode="json") if repair_intent else None,
                    },
                )
            )
        return candidates

    def from_diagnoses(
        self,
        diagnoses: list[CanonicalDiagnosisArtifact],
        *,
        current_content_by_path: dict[str, str] | None = None,
    ) -> list[PatchCandidateArtifact]:
        candidates: list[PatchCandidateArtifact] = []
        for diagnosis in diagnoses:
            candidates.extend(self.from_diagnosis(diagnosis, current_content_by_path=current_content_by_path))
        return candidates

    def diagnosis_from_candidate(
        self,
        candidate: PatchCandidateArtifact,
        *,
        evidence: list[PatchEvidence] | None = None,
        objective: str = "",
        source_type: str = "compat_patch_candidate",
        source_id: str | None = None,
    ) -> CanonicalDiagnosisArtifact:
        evidence_refs = self._evidence_refs(candidate.evidence_refs, evidence or [])
        repair_hints = []
        if candidate.replacement_strategy or candidate.optional_constraints:
            repair_hints.append(
                RepairHint(
                    strategy=candidate.replacement_strategy or objective or "Compile a governed replacement from the selected target.",
                    constraints=list(candidate.optional_constraints),
                )
            )
        payload = {
            "metadata": DiagnosisMetadata(
                source_type=source_type,
                source_id=source_id,
                task_run_id=candidate.task_run_id,
                execution_plan_id=candidate.execution_plan_id,
            ),
            "workspace": candidate.workspace,
            "semantic_goal": candidate.semantic_goal or objective,
            "observed_behavior": candidate.observed_behavior,
            "expected_behavior": candidate.expected_behavior,
            "technical_localization": [
                TechnicalLocalization(
                    workspace=candidate.workspace,
                    target_file=candidate.target_file,
                    target_symbol=candidate.target_symbol,
                    symbol_kind=candidate.symbol_kind,
                    confidence=candidate.confidence,
                )
            ],
            "evidence": evidence_refs,
            "confidence": candidate.confidence,
            "repair_hints": repair_hints,
            "reason_codes": ["compat_candidate_promoted_to_canonical_diagnosis"],
        }
        if candidate.diagnosis_id:
            payload["diagnosis_id"] = candidate.diagnosis_id
        return CanonicalDiagnosisArtifact(**payload)

    def diagnoses_from_request(
        self,
        *,
        workspace: str,
        objective: str,
        source_type: str,
        source_id: str | None,
        paths: list[str],
        evidence: list[PatchEvidence],
        candidates: list[PatchCandidateArtifact] | None = None,
    ) -> list[CanonicalDiagnosisArtifact]:
        if candidates:
            return [
                self.diagnosis_from_candidate(
                    candidate,
                    evidence=evidence,
                    objective=objective,
                    source_type="compat_patch_candidate",
                    source_id=source_id,
                )
                for candidate in candidates
            ]
        if not paths:
            return []
        evidence_refs = self._evidence_refs([], evidence)
        observed = next((item.excerpt for item in evidence if item.excerpt), objective)
        confidence = max([item.confidence for item in evidence] or [0.5])
        return [
            CanonicalDiagnosisArtifact(
                metadata=DiagnosisMetadata(
                    source_type=source_type,
                    source_id=source_id,
                    task_run_id=source_id if source_type == "task_run" else None,
                ),
                workspace=workspace,
                semantic_goal=objective,
                observed_behavior=observed or objective or "Patch evidence was provided.",
                expected_behavior=objective or "Apply the requested governed correction.",
                technical_localization=[
                    TechnicalLocalization(
                        workspace=workspace,
                        target_file=path,
                        target_symbol=path,
                        symbol_kind="file",
                        confidence=confidence,
                    )
                ],
                evidence=evidence_refs,
                confidence=confidence,
                repair_hints=[
                    RepairHint(
                        strategy=objective or "Compile a governed replacement from the selected target.",
                    )
                ],
                reason_codes=["diagnosis_derived_from_governed_patch_evidence"],
            )
            for path in paths
        ]

    def _matching_repair_intent(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        localization: TechnicalLocalization,
    ):
        intent = diagnosis.repair_intent
        if intent is None:
            return None
        if self._same_path(intent.target_file, localization.target_file) and self._target_terms_overlap(
            intent.target_symbol,
            localization.target_symbol,
        ):
            return intent
        return None

    def _expected_behavior(self, diagnosis: CanonicalDiagnosisArtifact, repair_intent) -> str:
        if repair_intent is not None and repair_intent.expected_behavior.strip():
            return repair_intent.expected_behavior
        return diagnosis.expected_behavior

    def _semantic_goal(self, diagnosis: CanonicalDiagnosisArtifact, repair_intent) -> str:
        if repair_intent is not None:
            return repair_intent.success_condition or repair_intent.expected_behavior
        return diagnosis.semantic_goal

    def _replacement_strategy(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        localization: TechnicalLocalization,
        *,
        repair_intent,
    ) -> str | None:
        for hint in diagnosis.repair_hints:
            strategy = str(hint.strategy or "").strip()
            if not strategy:
                continue
            if repair_intent is not None:
                if self._looks_operational(strategy):
                    continue
                if not self._mentions_target(strategy, localization.target_file, localization.target_symbol):
                    continue
            return strategy
        if repair_intent is not None:
            synthesized = self._synthesized_strategy(diagnosis, localization, repair_intent)
            if synthesized:
                return synthesized
        return None

    def _current_excerpt(self, current: str | None, localization: TechnicalLocalization) -> str | None:
        content = str(current or "")
        if not content.strip():
            return None
        if localization.symbol_kind == "file":
            return content[:1200]
        symbol_excerpt = self._symbol_excerpt(content, localization.target_symbol)
        if symbol_excerpt:
            return symbol_excerpt[:1600]
        if localization.region_hint:
            hinted = self._region_excerpt(content, localization.region_hint)
            if hinted:
                return hinted[:1600]
        return content[:1200]

    def _symbol_excerpt(self, content: str, symbol: str) -> str:
        symbol = str(symbol or "").strip()
        if not symbol:
            return ""
        lines = content.splitlines(keepends=True)
        start = None
        for index, line in enumerate(lines):
            stripped = line.strip()
            if (
                stripped.startswith(f"def {symbol}(")
                or stripped.startswith(f"async def {symbol}(")
                or stripped.startswith(f"class {symbol}(")
                or stripped.startswith(f"class {symbol}:")
                or stripped.startswith(f"class {symbol} ")
                or stripped.startswith(f"fun {symbol}(")
                or stripped.startswith(f"private fun {symbol}(")
                or stripped.startswith(f"internal fun {symbol}(")
                or stripped.startswith(f"public fun {symbol}(")
                or stripped.startswith(f"override fun {symbol}(")
                or stripped.startswith(f"suspend fun {symbol}(")
                or stripped.startswith(f"function {symbol}(")
            ):
                start = index
                break
        if start is None:
            return ""
        base_indent = len(lines[start]) - len(lines[start].lstrip())
        end = len(lines)
        for index in range(start + 1, len(lines)):
            stripped = lines[index].strip()
            if not stripped:
                continue
            indent = len(lines[index]) - len(lines[index].lstrip())
            if indent <= base_indent and not stripped.startswith((")", "}", "else", "catch", "finally")):
                end = index
                break
        return "".join(lines[start:end]).strip()

    def _region_excerpt(self, content: str, region_hint: str) -> str:
        hint = str(region_hint or "").strip().casefold()
        if not hint:
            return ""
        lowered = content.casefold()
        index = lowered.find(hint)
        if index < 0:
            return ""
        start = max(0, index - 400)
        end = min(len(content), index + 1200)
        return content[start:end].strip()

    def _synthesized_strategy(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        localization: TechnicalLocalization,
        repair_intent,
    ) -> str | None:
        target = self._target_label(localization.target_file, localization.target_symbol)
        if not target:
            return None
        for reason_code in list(getattr(repair_intent, "reason_codes", []) or []):
            template = self.REPAIR_INTENT_STRATEGY_TEMPLATES.get(str(reason_code))
            if template:
                return template.format(target=target)
        diagnosis_text = self._diagnosis_text(diagnosis)
        for reason_code, terms in self.REPAIR_STRATEGY_TERM_PATTERNS:
            if any(term in diagnosis_text for term in terms):
                template = self.REPAIR_INTENT_STRATEGY_TEMPLATES.get(reason_code)
                if template:
                    return template.format(target=target)
        expected = str(getattr(repair_intent, "expected_behavior", "") or "").strip()
        if expected:
            return f"Edit {target} so that {self._as_lower_action(expected)}"
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

    def _target_label(self, target_file: str, target_symbol: str) -> str:
        symbol = str(target_symbol or "").strip()
        file = str(target_file or "").strip()
        if symbol and self._normalize(symbol) != self._normalize(file):
            return symbol
        if file:
            return file.replace("\\", "/").rsplit("/", 1)[-1]
        return symbol

    def _as_lower_action(self, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        normalized = text[0].lower() + text[1:]
        return normalized if normalized.endswith(".") else f"{normalized}."

    def _normalize(self, value: str) -> str:
        return str(value or "").replace("\\", "/").strip().casefold()

    def _looks_operational(self, value: str) -> bool:
        text = str(value or "").replace("\\", "/").casefold()
        if not text:
            return False
        marker_count = sum(1 for marker in self.OPERATIONAL_EXPECTED_BEHAVIOR_MARKERS if marker in text)
        artifact_shape = bool(re.search(r"(^|[/\s])[^/\s]+\.(md|csv|json|zip)\b", text))
        return marker_count >= 2 or (artifact_shape and marker_count >= 1)

    def _mentions_target(self, value: str, target_file: str, target_symbol: str) -> bool:
        text = str(value or "").replace("\\", "/").casefold()
        return any(term in text for term in self._target_terms(target_file, target_symbol))

    def _target_terms_overlap(self, left: str, right: str) -> bool:
        return bool(self._target_terms("", left) & self._target_terms("", right))

    def _same_path(self, left: str, right: str) -> bool:
        return str(left or "").replace("\\", "/").strip().casefold() == str(right or "").replace("\\", "/").strip().casefold()

    def _target_terms(self, target_file: str, target_symbol: str) -> set[str]:
        terms: set[str] = set()
        for value in (target_file, target_symbol):
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

    def _evidence_refs(self, candidate_refs: list[str], evidence: list[PatchEvidence]) -> list[DiagnosisEvidenceRef]:
        by_id: dict[str, DiagnosisEvidenceRef] = {}
        for item in evidence:
            if not item.evidence_id:
                continue
            by_id[item.evidence_id] = DiagnosisEvidenceRef(
                evidence_id=item.evidence_id,
                source_type=item.source_type,
                source_path=item.source_path,
                summary=item.excerpt,
                confidence=item.confidence,
            )
        for ref in candidate_refs:
            if ref and ref not in by_id:
                by_id[ref] = DiagnosisEvidenceRef(evidence_id=ref)
        return list(by_id.values())
