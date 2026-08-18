from __future__ import annotations

import re
from typing import Any

from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_observability import ActionabilityAnalysis, RepairTaskArtifact


DEFAULT_GENERIC_TERMS = {
    "apply",
    "aplicar",
    "artifact",
    "artifacts",
    "candidate",
    "candidato",
    "causa",
    "codigo",
    "code",
    "concrete",
    "correcao",
    "correction",
    "diff",
    "evidence",
    "evidencia",
    "file",
    "files",
    "funcao",
    "funcoes",
    "function",
    "functions",
    "gerar",
    "hunk",
    "hunks",
    "patch",
    "plan",
    "planning",
    "preview",
    "produce",
    "replacement",
    "return",
    "risco",
    "riscos",
    "risk",
    "rollback",
    "safe",
    "selected",
    "strategy",
    "target",
}

DEFAULT_OPERATIONAL_EXPECTED_BEHAVIOR_MARKERS = {
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


class PatchCandidateActionabilityAnalyzer:
    """Deterministically decides whether a candidate is an editable repair task."""

    def analyze(
        self,
        candidate: PatchCandidateArtifact,
        *,
        policy: dict[str, Any] | None = None,
    ) -> ActionabilityAnalysis:
        policy = dict(policy or {})
        min_score = self._positive_int(policy.get("min_score"), 75)
        max_file_edit_chars = self._positive_int(policy.get("max_file_edit_chars"), 3400)
        min_objective_terms = self._positive_int(policy.get("min_objective_terms"), 2)
        generic_terms = {
            str(item).strip().casefold()
            for item in policy.get("generic_behavior_terms", DEFAULT_GENERIC_TERMS)
            if str(item).strip()
        }
        operational_markers = {
            str(item).strip().casefold()
            for item in policy.get("operational_expected_behavior_markers", DEFAULT_OPERATIONAL_EXPECTED_BEHAVIOR_MARKERS)
            if str(item).strip()
        }

        context = dict(candidate.technical_context)
        present: list[str] = []
        missing: list[str] = []
        reason_codes: list[str] = []
        diagnostics: list[str] = []

        def mark(condition: bool, field: str, reason: str | None = None, diagnostic: str | None = None) -> int:
            if condition:
                present.append(field)
                return 1
            missing.append(field)
            if reason:
                reason_codes.append(reason)
            if diagnostic:
                diagnostics.append(diagnostic)
            return 0

        target_file = candidate.target_file.strip()
        target_symbol = candidate.target_symbol.strip()
        symbol_kind = candidate.symbol_kind
        file_level = symbol_kind == "file" or self._normalize(target_file) == self._normalize(target_symbol)
        current_excerpt = candidate.current_content_excerpt or ""
        current_chars = self._positive_int(context.get("current_content_chars"), len(current_excerpt))
        source_chars = self._positive_int(context.get("source_content_chars"), current_chars)
        current_complete = context.get("current_content_complete")
        repair_intent = context.get("repair_intent") if isinstance(context.get("repair_intent"), dict) else {}
        if current_complete is None:
            current_complete = bool(current_excerpt) and (not file_level or source_chars <= len(current_excerpt))
        expected_operational = self._has_operational_expected_behavior(candidate.expected_behavior, operational_markers)

        score = 0
        score += 14 * mark(bool(target_file), "target_file", "REPAIR_TASK_TARGET_MISSING", "missing:target_file")
        score += 12 * mark(bool(target_symbol), "target_symbol", "REPAIR_TASK_SYMBOL_UNRESOLVED", "missing:target_symbol")
        score += 12 * mark(
            not file_level or source_chars <= max_file_edit_chars,
            "bounded_edit_unit",
            "REPAIR_TASK_TARGET_TOO_BROAD",
            f"target_too_broad:source_chars={source_chars}:limit={max_file_edit_chars}",
        )
        score += 10 * mark(
            bool(current_excerpt or current_chars > 0),
            "code_snippet",
            "REPAIR_TASK_SNIPPET_MISSING",
            "missing:code_snippet",
        )
        score += 10 * mark(
            bool(current_complete) or not file_level,
            "complete_context",
            "REPAIR_TASK_SNIPPET_INSUFFICIENT",
            f"incomplete_context:current_chars={current_chars}:source_chars={source_chars}",
        )
        score += 12 * mark(
            self._has_specific_objective(candidate.expected_behavior, generic_terms, min_objective_terms)
            and self._mentions_target(candidate.expected_behavior, target_file, target_symbol)
            and not expected_operational,
            "expected_behavior",
            "REPAIR_TASK_EXPECTED_BEHAVIOR_OPERATIONAL" if expected_operational else "REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING",
            "operational_noise:expected_behavior" if expected_operational else "missing:target_specific_expected_behavior",
        )
        score += 10 * mark(
            self._has_specific_objective(candidate.observed_behavior, generic_terms, min_objective_terms),
            "observed_behavior",
            "REPAIR_TASK_OBSERVED_BEHAVIOR_MISSING",
            "missing:specific_observed_behavior",
        )
        score += 8 * mark(bool(candidate.evidence_refs), "evidence_refs", "REPAIR_TASK_EVIDENCE_MISSING", "missing:evidence_refs")
        score += 6 * mark(bool(candidate.replacement_strategy), "repair_strategy", "REPAIR_TASK_STRATEGY_MISSING", "missing:repair_strategy")
        score += 6 * mark(candidate.confidence > 0, "confidence", "REPAIR_TASK_CONFIDENCE_MISSING", "missing:confidence")

        if file_level and bool(target_file) and bool(target_symbol):
            diagnostics.append("edit_unit:file")
        elif bool(target_symbol):
            diagnostics.append(f"edit_unit:{symbol_kind}")

        score = max(0, min(100, score))
        editable = score >= min_score and not any(
            reason
            in {
                "REPAIR_TASK_TARGET_MISSING",
                "REPAIR_TASK_SYMBOL_UNRESOLVED",
                "REPAIR_TASK_SNIPPET_MISSING",
                "REPAIR_TASK_SNIPPET_INSUFFICIENT",
                "REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING",
                "REPAIR_TASK_EXPECTED_BEHAVIOR_OPERATIONAL",
            }
            for reason in reason_codes
        )
        if not editable:
            reason_codes.insert(0, "REPAIR_TASK_NOT_ACTIONABLE")
        repair_boundary = [
            str(item).strip()
            for item in [*list(repair_intent.get("repair_boundary") or []), *list(candidate.optional_constraints)]
            if str(item).strip()
        ]
        success_condition = str(repair_intent.get("success_condition") or candidate.semantic_goal or candidate.expected_behavior).strip()
        gaps = self._gap_labels(missing)
        repair_task = RepairTaskArtifact(
            repair_task_id=f"repair_task:{candidate.candidate_id}",
            diagnosis_id=candidate.diagnosis_id,
            candidate_id=candidate.candidate_id,
            workspace=candidate.workspace,
            target_file=target_file,
            target_symbol=target_symbol,
            symbol_kind=symbol_kind,
            edit_unit="file" if file_level else symbol_kind,
            semantic_goal=candidate.semantic_goal,
            why_change=candidate.observed_behavior,
            behavior_to_create=candidate.expected_behavior,
            preconditions=[candidate.observed_behavior] if candidate.observed_behavior.strip() else [],
            postconditions=[candidate.expected_behavior] if candidate.expected_behavior.strip() else [],
            invariants=list(dict.fromkeys(repair_boundary)),
            success_condition=success_condition,
            repair_boundary=list(dict.fromkeys(repair_boundary)),
            evidence_refs=list(candidate.evidence_refs),
            current_content_chars=current_chars,
            source_content_chars=source_chars,
            current_content_complete=bool(current_complete),
            actionability_score=score,
            actionable=editable,
            missing=list(dict.fromkeys(missing)),
            gaps=gaps,
            reason_codes=list(dict.fromkeys(reason_codes)),
        )
        return ActionabilityAnalysis(
            score=score,
            confidence=self._confidence(score),
            editable=editable,
            edit_unit="file" if file_level else symbol_kind,
            present=list(dict.fromkeys(present)),
            missing=list(dict.fromkeys(missing)),
            reason_codes=list(dict.fromkeys(reason_codes)),
            diagnostics=list(dict.fromkeys(diagnostics)),
            repair_task=repair_task,
        )

    def _gap_labels(self, missing: list[str]) -> list[str]:
        mapping = {
            "target_file": "target file real",
            "target_symbol": "símbolo",
            "bounded_edit_unit": "unidade editável",
            "code_snippet": "contexto técnico",
            "complete_context": "contexto técnico",
            "expected_behavior": "expected behavior específico",
            "observed_behavior": "observed behavior específico",
            "evidence_refs": "evidência",
            "repair_strategy": "estratégia sugerida",
            "confidence": "confiança",
        }
        return list(dict.fromkeys(mapping[field] for field in missing if field in mapping))

    def _has_specific_objective(self, value: str, generic_terms: set[str], min_terms: int) -> bool:
        tokens = [
            token.casefold()
            for token in re.findall(r"[A-Za-zÀ-ÿ0-9_]{4,}", str(value or ""))
        ]
        specific = [token for token in tokens if token not in generic_terms]
        return len(set(specific)) >= min_terms

    def _mentions_target(self, value: str, target_file: str, target_symbol: str) -> bool:
        text = str(value or "").replace("\\", "/").casefold()
        if not text:
            return False
        target_terms = self._target_terms(target_file, target_symbol)
        return any(term in text for term in target_terms)

    def _has_operational_expected_behavior(self, value: str, markers: set[str]) -> bool:
        text = str(value or "").replace("\\", "/").casefold()
        if not text:
            return False
        marker_count = sum(1 for marker in markers if marker in text)
        artifact_shape = bool(re.search(r"(^|[/\s])[^/\s]+\.(md|csv|json|zip)\b", text))
        return marker_count >= 2 or (artifact_shape and marker_count >= 1)

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

    def _positive_int(self, value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return max(1, default)
        return max(1, parsed)

    def _normalize(self, value: str) -> str:
        return str(value or "").replace("\\", "/").strip().casefold()

    def _confidence(self, score: int) -> str:
        if score >= 80:
            return "alta"
        if score >= 55:
            return "media"
        return "baixa"
