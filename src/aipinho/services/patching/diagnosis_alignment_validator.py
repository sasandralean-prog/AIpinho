from __future__ import annotations

import re

from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_observability import AlignmentAnalysis


_GENERIC_TERMS = {
    "adjust",
    "alter",
    "apply",
    "artifact",
    "artifacts",
    "candidate",
    "change",
    "code",
    "concrete",
    "correction",
    "diff",
    "edit",
    "evidence",
    "file",
    "fix",
    "function",
    "generate",
    "hunk",
    "patch",
    "plan",
    "planning",
    "preview",
    "replacement",
    "return",
    "risk",
    "rollback",
    "strategy",
    "target",
    "update",
}

_DOMAIN_PATTERNS = (
    ("bounds", {"indexoutofbounds", "bounds", "boundary", "limit", "offset", "index", "header", "buffer"}),
    ("eof", {"eof", "truncated", "incomplete", "partial", "stream", "input", "bytes", "read"}),
    ("null", {"null", "missing", "none"}),
    ("timeout", {"timeout", "latency", "budget", "timed", "deadline"}),
    ("cache", {"cache", "invalidate", "invalidation"}),
    ("parse", {"parse", "parser", "json", "yaml", "decode", "deserialize"}),
    ("media", {"codec", "container", "format", "sample", "bitrate"}),
)


class DiagnosisAlignmentValidator:
    """Validates whether diagnosis evidence can justify a concrete editable change."""

    def analyze(self, candidate: PatchCandidateArtifact) -> AlignmentAnalysis:
        context = dict(candidate.technical_context)
        repair_intent = context.get("repair_intent") if isinstance(context.get("repair_intent"), dict) else {}
        repair_task = context.get("repair_task") if isinstance(context.get("repair_task"), dict) else {}
        semantic_evidence = context.get("semantic_evidence") if isinstance(context.get("semantic_evidence"), dict) else {}
        behavior_localization = context.get("behavior_localization") if isinstance(context.get("behavior_localization"), dict) else {}
        behavior_justification = context.get("behavior_justification") if isinstance(context.get("behavior_justification"), dict) else {}
        candidate_transformation = context.get("candidate_transformation") if isinstance(context.get("candidate_transformation"), dict) else {}
        proposal_scaffold = context.get("repair_proposal_scaffold") if isinstance(context.get("repair_proposal_scaffold"), dict) else {}
        snippet = str(candidate.current_content_excerpt or "")
        target_terms = self._target_terms(candidate.target_file, candidate.target_symbol)
        expected_terms = self._specific_terms(candidate.expected_behavior, excluded=target_terms)
        observed_terms = self._specific_terms(candidate.observed_behavior, excluded=target_terms)
        success_terms = self._specific_terms(
            str(repair_intent.get("success_condition") or repair_task.get("success_condition") or ""),
            excluded=target_terms,
        )
        proposal_terms = self._proposal_terms(proposal_scaffold, excluded=target_terms)
        snippet_terms = self._snippet_terms(snippet)
        required_domain_terms = self._required_domain_terms(candidate, repair_intent)
        present: list[str] = []
        missing: list[str] = []
        gaps: list[str] = []
        reason_codes: list[str] = []
        diagnostics: list[str] = []

        def mark(condition: bool, field: str, reason: str | None = None, gap: str | None = None, diagnostic: str | None = None) -> int:
            if condition:
                present.append(field)
                return 1
            missing.append(field)
            if reason:
                reason_codes.append(reason)
            if gap:
                gaps.append(gap)
            if diagnostic:
                diagnostics.append(diagnostic)
            return 0

        evidence_coverage = self._coverage_score(semantic_evidence)
        localization_coverage = self._coverage_score(behavior_localization)
        justification_coverage = self._coverage_score(behavior_justification)
        transformation_coverage = self._coverage_score(candidate_transformation)
        constraint_coverage = 100 if list(repair_intent.get("repair_boundary") or repair_task.get("repair_boundary") or repair_task.get("invariants") or []) else 0
        proposal_completeness = self._proposal_completeness(proposal_scaffold)

        score = 0
        score += 10 * mark(bool(snippet.strip()), "technical_context", "REPAIR_TASK_TECHNICAL_CONTEXT_MISSING", "technical_context", "missing:technical_context")
        score += 8 * mark(bool(candidate.target_symbol.strip()), "symbol", "REPAIR_TASK_SYMBOL_UNRESOLVED", "symbol", "missing:symbol")
        score += 8 * mark(bool(expected_terms), "expected_behavior", "TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING", "expected behavior especifico", "missing:target_specific_expected_behavior")
        score += 6 * mark(bool(observed_terms), "observed_behavior", "REPAIR_TASK_OBSERVED_BEHAVIOR_MISSING", "observed behavior especifico", "missing:specific_observed_behavior")
        score += 8 * mark(
            bool(str(repair_intent.get("success_condition") or repair_task.get("success_condition") or "").strip()),
            "success_condition",
            "SUCCESS_CONDITION_MISSING",
            "success criteria",
            "missing:success_condition",
        )
        score += 8 * mark(constraint_coverage >= 100, "repair_boundary", "REPAIR_BOUNDARY_MISSING", "invariant", "missing:repair_boundary")

        symbol_aligned = self._symbol_aligned(candidate, snippet)
        score += 8 * mark(
            symbol_aligned,
            "edit_unit",
            "REPAIR_TASK_EDIT_UNIT_UNRESOLVED",
            "unidade editavel",
            f"target_symbol_not_anchored:{candidate.target_symbol}",
        )
        score += 12 * mark(
            evidence_coverage >= 60,
            "semantic_evidence",
            "SEMANTIC_EVIDENCE_MISSING",
            "semantic evidence",
            f"semantic_evidence_score={evidence_coverage}",
        )
        score += 12 * mark(
            localization_coverage >= 60,
            "behavior_localization",
            "BEHAVIOR_LOCALIZATION_MISSING",
            "behavior localization",
            f"behavior_localization_score={localization_coverage}",
        )
        score += 12 * mark(
            justification_coverage >= 60,
            "behavior_justification",
            "BEHAVIOR_JUSTIFICATION_MISSING",
            "behavior justification",
            f"behavior_justification_score={justification_coverage}",
        )
        score += 12 * mark(
            transformation_coverage >= 60,
            "candidate_transformation",
            "TRANSFORMATION_MISSING",
            "candidate transformation",
            f"candidate_transformation_score={transformation_coverage}",
        )
        if proposal_scaffold:
            score += 10 * mark(
                proposal_completeness > 0,
                "repair_proposal",
                "PROPOSAL_ASSEMBLY_FAILED",
                "repair proposal scaffold",
                f"proposal_completeness={proposal_completeness}",
            )
        else:
            present.append("repair_proposal")

        overlap_terms = required_domain_terms or (expected_terms | observed_terms | success_terms | proposal_terms)
        overlap = len(overlap_terms & snippet_terms)
        behavior_coverage = min(
            100,
            max(
                justification_coverage,
                len((expected_terms | observed_terms | success_terms | proposal_terms) & snippet_terms) * 20,
            ),
        )
        semantic_alignment = (
            evidence_coverage >= 60
            and localization_coverage >= 60
            and behavior_coverage >= 60
            and transformation_coverage >= 60
            and (proposal_completeness > 0 if proposal_scaffold else True)
            and constraint_coverage >= 100
        ) or (
            (candidate.symbol_kind == "file" and bool(snippet.strip()))
            or (not required_domain_terms and bool(snippet.strip()) and (symbol_aligned or candidate.symbol_kind == "file"))
            or overlap >= 2
            or (overlap >= 1 and candidate.symbol_kind != "file")
        )
        score += 14 * mark(
            semantic_alignment,
            "semantic_alignment",
            "DIAGNOSIS_ALIGNMENT_MISSING",
            "semantic alignment",
            (
                f"behavior_coverage={behavior_coverage};"
                f"evidence_coverage={evidence_coverage};"
                f"localization_coverage={localization_coverage};"
                f"constraint_coverage={constraint_coverage};"
                f"transformation_coverage={transformation_coverage};"
                f"semantic_overlap={overlap}"
            ),
        )

        score = max(0, min(100, score))
        aligned = score >= 70 and not any(
            reason in {
                "REPAIR_TASK_TECHNICAL_CONTEXT_MISSING",
                "REPAIR_TASK_SYMBOL_UNRESOLVED",
                "TARGET_SPECIFIC_EXPECTED_BEHAVIOR_MISSING",
                "REPAIR_TASK_EDIT_UNIT_UNRESOLVED",
                "SEMANTIC_EVIDENCE_MISSING",
                "BEHAVIOR_LOCALIZATION_MISSING",
                "BEHAVIOR_JUSTIFICATION_MISSING",
                "TRANSFORMATION_MISSING",
                "PROPOSAL_ASSEMBLY_FAILED",
                "DIAGNOSIS_ALIGNMENT_MISSING",
            }
            for reason in reason_codes
        )
        if not aligned:
            reason_codes.insert(0, "REPAIR_TASK_ALIGNMENT_FAILED")
        return AlignmentAnalysis(
            score=score,
            confidence=self._confidence(score),
            aligned=aligned,
            present=list(dict.fromkeys(present)),
            missing=list(dict.fromkeys(missing)),
            gaps=list(dict.fromkeys(gaps)),
            reason_codes=list(dict.fromkeys(reason_codes)),
            diagnostics=list(dict.fromkeys(diagnostics)),
        )

    def _symbol_aligned(self, candidate: PatchCandidateArtifact, snippet: str) -> bool:
        text = snippet.casefold()
        symbol = str(candidate.target_symbol or "").strip()
        if not symbol:
            return False
        if candidate.symbol_kind == "file":
            return bool(snippet.strip())
        symbol_terms = self._target_terms(candidate.target_file, candidate.target_symbol)
        return any(term in text for term in symbol_terms if term and "/" not in term and "." not in term)

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

    def _specific_terms(self, value: str, *, excluded: set[str]) -> set[str]:
        terms = set()
        for token in re.findall(r"[A-Za-zÀ-ÿ0-9_]{4,}", str(value or "").casefold()):
            if token in _GENERIC_TERMS or token in excluded:
                continue
            terms.add(token)
        return terms

    def _snippet_terms(self, snippet: str) -> set[str]:
        return {
            token.casefold()
            for token in re.findall(r"[A-Za-zÀ-ÿ0-9_]{3,}", str(snippet or ""))
            if len(token) >= 3
        }

    def _required_domain_terms(self, candidate: PatchCandidateArtifact, repair_intent: dict[str, object]) -> set[str]:
        text = " ".join(
            [
                str(candidate.observed_behavior or ""),
                str(candidate.expected_behavior or ""),
                str(repair_intent.get("success_condition") or ""),
                " ".join(str(item) for item in list(repair_intent.get("reason_codes") or [])),
            ]
        ).casefold()
        terms: set[str] = set()
        for _label, pattern_terms in _DOMAIN_PATTERNS:
            if any(term in text for term in pattern_terms):
                terms.update(pattern_terms)
        return terms

    def _proposal_terms(self, proposal_scaffold: dict[str, object], *, excluded: set[str]) -> set[str]:
        concrete = proposal_scaffold.get("concrete_change") if isinstance(proposal_scaffold.get("concrete_change"), dict) else {}
        values = [
            str(proposal_scaffold.get("intent") or ""),
            str(concrete.get("objective") or ""),
            str(concrete.get("expected_behavior") or ""),
            str(concrete.get("behavior_summary") or ""),
            str(concrete.get("modification_strategy") or ""),
        ]
        return self._specific_terms(" ".join(values), excluded=excluded)

    def _proposal_completeness(self, proposal_scaffold: dict[str, object]) -> float:
        try:
            return float(proposal_scaffold.get("proposal_completeness") or 0.0)
        except (TypeError, ValueError, AttributeError):
            return 0.0

    def _coverage_score(self, artifact: dict[str, object]) -> int:
        try:
            return max(0, min(100, int(artifact.get("coverage_score") or 0)))
        except (TypeError, ValueError, AttributeError):
            return 0

    def _confidence(self, score: int) -> str:
        if score >= 80:
            return "alta"
        if score >= 55:
            return "media"
        return "baixa"
