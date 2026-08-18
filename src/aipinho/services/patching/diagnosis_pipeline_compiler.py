from __future__ import annotations

import re

from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact
from aipinho.schemas.patching.diagnosis_pipeline_artifact import (
    BehaviorJustificationArtifact,
    BehaviorLocalizationArtifact,
    CandidateTransformationArtifact,
    SemanticEvidenceArtifact,
    SemanticEvidenceEntry,
)
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_observability import RepairTaskArtifact


class DiagnosisPipelineCompiler:
    """Compiles diagnosis evidence into intermediate, verifiable repair artifacts."""

    _GENERIC_TOKENS = {
        "artifact",
        "artifacts",
        "behavior",
        "candidate",
        "change",
        "code",
        "contract",
        "diagnosis",
        "evidence",
        "expected",
        "file",
        "files",
        "function",
        "logic",
        "patch",
        "plan",
        "preview",
        "proposal",
        "repair",
        "runtime",
        "strategy",
        "symbol",
        "target",
    }

    def enrich_diagnosis(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        *,
        current_content_by_path: dict[str, str] | None = None,
    ) -> CanonicalDiagnosisArtifact:
        current_content_by_path = current_content_by_path or {}
        semantic_evidence = self._semantic_evidence(
            diagnosis,
            current_content_by_path=current_content_by_path,
        )
        behavior_localization = self._behavior_localization(
            diagnosis,
            current_content_by_path=current_content_by_path,
            semantic_evidence=semantic_evidence,
        )
        behavior_justification = self._behavior_justification(
            diagnosis,
            semantic_evidence=semantic_evidence,
            behavior_localization=behavior_localization,
        )
        reason_codes = list(diagnosis.reason_codes)
        if semantic_evidence.status == "missing":
            reason_codes.append("SEMANTIC_EVIDENCE_MISSING")
        if behavior_localization.status == "missing":
            reason_codes.append("BEHAVIOR_LOCALIZATION_MISSING")
        if behavior_justification.status == "missing":
            reason_codes.append("BEHAVIOR_JUSTIFICATION_MISSING")
        return diagnosis.model_copy(
            update={
                "semantic_evidence": semantic_evidence,
                "behavior_localization": behavior_localization,
                "behavior_justification": behavior_justification,
                "reason_codes": self._dedupe(reason_codes),
            }
        )

    def candidate_transformation(
        self,
        candidate: PatchCandidateArtifact,
        *,
        repair_task: RepairTaskArtifact | None = None,
    ) -> CandidateTransformationArtifact:
        context = dict(candidate.technical_context)
        repair_task_payload = repair_task.model_dump(mode="json") if repair_task else {}
        if not repair_task_payload and isinstance(context.get("repair_task"), dict):
            repair_task_payload = dict(context["repair_task"])
        repair_intent = dict(context.get("repair_intent") or {}) if isinstance(context.get("repair_intent"), dict) else {}
        justification = dict(context.get("behavior_justification") or {}) if isinstance(context.get("behavior_justification"), dict) else {}
        localized = dict(context.get("behavior_localization") or {}) if isinstance(context.get("behavior_localization"), dict) else {}

        current_logic = str(candidate.current_content_excerpt or localized.get("localized_excerpt") or "").strip()
        desired_logic = str(
            repair_task_payload.get("behavior_to_create")
            or repair_intent.get("expected_behavior")
            or candidate.expected_behavior
            or ""
        ).strip()
        strategy = str(candidate.replacement_strategy or "").strip()
        constraints = [str(item).strip() for item in list(candidate.optional_constraints) if str(item).strip()]
        invariants = [
            str(item).strip()
            for item in list(repair_task_payload.get("repair_boundary") or repair_task_payload.get("invariants") or [])
            if str(item).strip()
        ]
        success_criteria = [
            str(item).strip()
            for item in list(repair_task_payload.get("postconditions") or [])
            if str(item).strip()
        ]
        success_condition = str(repair_task_payload.get("success_condition") or repair_intent.get("success_condition") or "").strip()
        if success_condition:
            success_criteria.append(success_condition)
        supporting_evidence_ids = [
            str(item).strip()
            for item in list((justification.get("supporting_evidence_ids") or candidate.evidence_refs))
            if str(item).strip()
        ]
        behavior_summary = str(
            justification.get("reasoning_chain", [""])[-1]
            if isinstance(justification.get("reasoning_chain"), list) and justification.get("reasoning_chain")
            else desired_logic or candidate.semantic_goal
        ).strip()

        present = 0
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        for field_name, value in (
            ("current_logic", current_logic),
            ("desired_logic", desired_logic),
            ("transformation_strategy", strategy),
            ("success_criteria", success_criteria),
        ):
            if self._has_value(value):
                present += 1
            else:
                diagnostics.append(f"{field_name}:missing")
        if not current_logic:
            reason_codes.append("TRANSFORMATION_MISSING")
        if not desired_logic:
            reason_codes.append("TRANSFORMATION_MISSING")
        if not strategy:
            reason_codes.append("TRANSFORMATION_MISSING")
        if not success_criteria:
            reason_codes.append("TRANSFORMATION_MISSING")
        coverage = int(round((present / 4) * 100)) if present else 0
        status = "complete" if coverage >= 100 else "partial" if coverage > 0 else "missing"
        if status == "missing":
            diagnostics.append("candidate_transformation:missing")
        return CandidateTransformationArtifact(
            diagnosis_id=candidate.diagnosis_id,
            candidate_id=candidate.candidate_id,
            status=status,
            target_file=candidate.target_file,
            target_symbol=candidate.target_symbol,
            current_logic=current_logic,
            desired_logic=desired_logic,
            transformation_strategy=strategy,
            constraints=self._dedupe(constraints),
            invariants=self._dedupe(invariants),
            success_criteria=self._dedupe(success_criteria),
            supporting_evidence_ids=self._dedupe(supporting_evidence_ids),
            affected_symbols=[candidate.target_symbol] if candidate.target_symbol else [],
            behavior_summary=behavior_summary,
            coverage_score=coverage,
            confidence=candidate.confidence,
            reason_codes=self._dedupe(reason_codes),
            diagnostics=self._dedupe(diagnostics),
        )

    def _semantic_evidence(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        *,
        current_content_by_path: dict[str, str],
    ) -> SemanticEvidenceArtifact:
        localization = diagnosis.technical_localization[0] if diagnosis.technical_localization else None
        target_file = localization.target_file if localization else ""
        target_symbol = localization.target_symbol if localization else ""
        target_terms = self._target_terms(target_file, target_symbol)
        behavior_terms = self._behavior_terms(diagnosis.observed_behavior, diagnosis.expected_behavior, diagnosis.semantic_goal)
        evidence_entries: list[SemanticEvidenceEntry] = []
        for item in diagnosis.evidence:
            summary = str(item.summary or "").strip()
            relation: list[str] = []
            summary_tokens = self._tokens(summary)
            overlap_target = len(target_terms & summary_tokens)
            overlap_behavior = len(behavior_terms & summary_tokens)
            if overlap_target:
                relation.append("target_localization")
            if overlap_behavior:
                relation.append("behavior_support")
            if not relation and item.source_path:
                if any(term in str(item.source_path).replace("\\", "/").casefold() for term in target_terms):
                    relation.append("target_path")
            if relation or summary or item.source_path:
                evidence_entries.append(
                    SemanticEvidenceEntry(
                        evidence_id=item.evidence_id,
                        source_type=item.source_type,
                        source_path=item.source_path,
                        target_file=target_file,
                        target_symbol=target_symbol,
                        excerpt=summary,
                        relation=", ".join(relation) if relation else "unclassified",
                        confidence=max(item.confidence, diagnosis.confidence if relation else 0.0),
                        reason_codes=[] if relation else ["SEMANTIC_EVIDENCE_RELATION_WEAK"],
                    )
                )
        current = str(
            current_content_by_path.get(target_file)
            or current_content_by_path.get(target_file.replace("\\", "/"))
            or ""
        )
        localized_excerpt = self._localized_excerpt(current, target_symbol, localization.region_hint if localization else None)
        if localized_excerpt:
            evidence_entries.append(
                SemanticEvidenceEntry(
                    evidence_id=f"semantic_code:{diagnosis.diagnosis_id}",
                    source_type="runtime_observation",
                    source_path=target_file,
                    target_file=target_file,
                    target_symbol=target_symbol,
                    excerpt=localized_excerpt,
                    relation="code_support, target_localization",
                    confidence=max(diagnosis.confidence, localization.confidence if localization else 0.0),
                    reason_codes=[],
                )
            )
        matched = [item for item in evidence_entries if item.relation != "unclassified"]
        coverage_score = 0
        if evidence_entries:
            coverage_score += 35
        if matched:
            coverage_score += 35
        if any("behavior_support" in item.relation for item in matched):
            coverage_score += 15
        if any("target_localization" in item.relation or "target_path" in item.relation for item in matched):
            coverage_score += 15
        coverage_score = min(100, coverage_score)
        status = "complete" if coverage_score >= 75 else "partial" if coverage_score > 0 else "missing"
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        if not evidence_entries:
            reason_codes.append("SEMANTIC_EVIDENCE_MISSING")
            diagnostics.append("semantic_evidence:none")
        elif not matched:
            reason_codes.append("SEMANTIC_EVIDENCE_RELATION_WEAK")
            diagnostics.append("semantic_evidence:unclassified_only")
        return SemanticEvidenceArtifact(
            diagnosis_id=diagnosis.diagnosis_id,
            status=status,
            coverage_score=coverage_score,
            confidence=max((item.confidence for item in evidence_entries), default=diagnosis.confidence),
            evidence=evidence_entries,
            reason_codes=self._dedupe(reason_codes),
            diagnostics=self._dedupe(diagnostics),
        )

    def _behavior_localization(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        *,
        current_content_by_path: dict[str, str],
        semantic_evidence: SemanticEvidenceArtifact,
    ) -> BehaviorLocalizationArtifact:
        localization = diagnosis.technical_localization[0] if diagnosis.technical_localization else None
        if localization is None:
            return BehaviorLocalizationArtifact(
                diagnosis_id=diagnosis.diagnosis_id,
                status="missing",
                reason_codes=["BEHAVIOR_LOCALIZATION_MISSING"],
                diagnostics=["behavior_localization:none"],
            )
        current = str(
            current_content_by_path.get(localization.target_file)
            or current_content_by_path.get(localization.target_file.replace("\\", "/"))
            or ""
        )
        excerpt = self._localized_excerpt(current, localization.target_symbol, localization.region_hint)
        coverage = 0
        if localization.target_file:
            coverage += 25
        if localization.target_symbol and localization.target_symbol != localization.target_file:
            coverage += 25
        if localization.symbol_kind != "file":
            coverage += 25
        if excerpt.strip():
            coverage += 25
        if localization.symbol_kind == "file" and localization.target_file and excerpt.strip():
            coverage = max(coverage, 75)
        status = "complete" if coverage >= 75 else "partial" if coverage > 0 else "missing"
        diagnostics: list[str] = []
        if not excerpt.strip():
            diagnostics.append("behavior_localization:excerpt_missing")
        if localization.symbol_kind == "file":
            diagnostics.append("behavior_localization:file_level")
        return BehaviorLocalizationArtifact(
            diagnosis_id=diagnosis.diagnosis_id,
            status=status,
            target_file=localization.target_file,
            target_symbol=localization.target_symbol,
            symbol_kind=localization.symbol_kind,
            anchor_kind=localization.symbol_kind,
            anchor_name=localization.target_symbol,
            anchor_signature=localization.region_hint or localization.target_symbol,
            localized_behavior=diagnosis.observed_behavior,
            localized_excerpt=excerpt,
            supporting_evidence_ids=self._dedupe([item.evidence_id for item in semantic_evidence.evidence if item.relation != "unclassified"]),
            coverage_score=coverage,
            confidence=localization.confidence,
            reason_codes=["BEHAVIOR_LOCALIZATION_MISSING"] if status == "missing" else [],
            diagnostics=self._dedupe(diagnostics),
        )

    def _behavior_justification(
        self,
        diagnosis: CanonicalDiagnosisArtifact,
        *,
        semantic_evidence: SemanticEvidenceArtifact,
        behavior_localization: BehaviorLocalizationArtifact,
    ) -> BehaviorJustificationArtifact:
        evidence_excerpt = " ".join(item.excerpt for item in semantic_evidence.evidence if item.excerpt)
        overlap = len(
            self._behavior_terms(diagnosis.observed_behavior, diagnosis.expected_behavior, diagnosis.semantic_goal)
            & self._tokens(f"{evidence_excerpt}\n{behavior_localization.localized_excerpt}")
        )
        reasoning_chain: list[str] = []
        if diagnosis.observed_behavior.strip():
            reasoning_chain.append(f"Observed behavior: {diagnosis.observed_behavior.strip()}")
        if behavior_localization.target_symbol:
            reasoning_chain.append(
                f"Localized behavior anchor: {behavior_localization.target_symbol} ({behavior_localization.anchor_kind})."
            )
        if semantic_evidence.evidence:
            reasoning_chain.append(
                f"Supporting evidence count: {len([item for item in semantic_evidence.evidence if item.relation != 'unclassified']) or len(semantic_evidence.evidence)}."
            )
        if diagnosis.expected_behavior.strip():
            reasoning_chain.append(f"Expected behavior: {diagnosis.expected_behavior.strip()}")
        if overlap > 0:
            reasoning_chain.append("Evidence and localized snippet share behavior terms with the diagnosis.")

        coverage = 0
        if diagnosis.observed_behavior.strip():
            coverage += 25
        if diagnosis.expected_behavior.strip():
            coverage += 25
        if semantic_evidence.status in {"complete", "partial"}:
            coverage += 25
        if behavior_localization.status in {"complete", "partial"}:
            coverage += 15
        if overlap > 0:
            coverage += 10
        coverage = min(100, coverage)
        status = "complete" if coverage >= 75 else "partial" if coverage > 0 else "missing"
        reason_codes: list[str] = []
        diagnostics = [f"behavior_overlap={overlap}"]
        if not diagnosis.observed_behavior.strip() or not diagnosis.expected_behavior.strip():
            reason_codes.append("BEHAVIOR_JUSTIFICATION_MISSING")
        if semantic_evidence.status == "missing":
            reason_codes.append("SEMANTIC_EVIDENCE_MISSING")
        if status == "missing":
            reason_codes.append("BEHAVIOR_JUSTIFICATION_MISSING")
        return BehaviorJustificationArtifact(
            diagnosis_id=diagnosis.diagnosis_id,
            status=status,
            observed_behavior=diagnosis.observed_behavior,
            expected_behavior=diagnosis.expected_behavior,
            supporting_evidence_ids=self._dedupe([item.evidence_id for item in semantic_evidence.evidence]),
            reasoning_chain=reasoning_chain,
            coverage_score=coverage,
            confidence=max(diagnosis.confidence, behavior_localization.confidence, semantic_evidence.confidence),
            reason_codes=self._dedupe(reason_codes),
            diagnostics=self._dedupe(diagnostics),
        )

    def _localized_excerpt(self, content: str, target_symbol: str, region_hint: str | None) -> str:
        text = str(content or "")
        if not text.strip():
            return ""
        symbol = str(target_symbol or "").strip()
        region = str(region_hint or "").strip()
        if symbol:
            lines = text.splitlines()
            for index, line in enumerate(lines):
                if symbol in line:
                    return "\n".join(lines[index : min(len(lines), index + 20)]).strip()
        if region:
            lowered = text.casefold()
            idx = lowered.find(region.casefold())
            if idx >= 0:
                start = max(0, idx - 300)
                end = min(len(text), idx + 900)
                return text[start:end].strip()
        return text[:1200]

    def _target_terms(self, target_file: str, target_symbol: str) -> set[str]:
        values = [target_file, target_symbol]
        tokens: set[str] = set()
        for value in values:
            normalized = str(value or "").replace("\\", "/").casefold()
            if not normalized:
                continue
            tokens.add(normalized)
            tokens.update(part for part in re.split(r"[/._\-\s]+", normalized) if len(part) >= 3)
        return {token for token in tokens if len(token) >= 3}

    def _behavior_terms(self, *values: str) -> set[str]:
        return {
            token
            for token in self._tokens(" ".join(str(value or "") for value in values))
            if token not in self._GENERIC_TOKENS
        }

    def _tokens(self, value: str) -> set[str]:
        return {
            token.casefold()
            for token in re.findall(r"[A-Za-zÀ-ÿ0-9_]{4,}", str(value or ""))
            if len(token) >= 4
        }

    def _has_value(self, value: object) -> bool:
        if isinstance(value, bool):
            return True
        if isinstance(value, (int, float)):
            return value > 0
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return value is not None

    def _dedupe(self, values: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
        return ordered
