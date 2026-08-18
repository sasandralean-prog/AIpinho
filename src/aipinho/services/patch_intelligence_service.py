from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.patch_intelligence import (
    IntelligentPatchProposal,
    IntelligentPatchProposalRequest,
    IntelligentPatchProposalResult,
    PatchCategory,
    PatchPatternMatch,
    PatchPatternRecognitionRequest,
    PatchPatternRecognitionResult,
    PatchEvidence,
    PatchKnowledgeBase,
    PatchKnowledgeEntry,
    PatchKnowledgeQuery,
    PatchKnowledgeQueryResult,
    PatchPattern,
)


CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
PATCH_CATEGORIES: set[str] = {
    "intent_regression",
    "lifecycle_regression",
    "workspace_binding_regression",
    "artifact_contract_regression",
    "validation_regression",
    "speaker_truth_regression",
    "approval_regression",
    "dispatcher_regression",
    "timeline_regression",
    "execution_plan_regression",
    "contract_regression",
}

DOCTOR_CATEGORY_TO_PATCH_CATEGORY: dict[str, PatchCategory] = {
    "Intent": "intent_regression",
    "Lifecycle": "lifecycle_regression",
    "Workspace": "workspace_binding_regression",
    "Artifacts": "artifact_contract_regression",
    "Approval": "approval_regression",
    "Validation": "validation_regression",
    "Completion": "validation_regression",
    "SpeakerTruth": "speaker_truth_regression",
    "Dispatcher": "dispatcher_regression",
    "Timeline": "timeline_regression",
    "ExecutionPlan": "execution_plan_regression",
    "Contracts": "contract_regression",
    "RoleSelection": "dispatcher_regression",
}


class PatchKnowledgeSerializer:
    def to_dict(self, base: PatchKnowledgeBase) -> dict[str, Any]:
        return base.model_dump(mode="json")

    def to_json(self, base: PatchKnowledgeBase) -> str:
        return json.dumps(self.to_dict(base), ensure_ascii=False, sort_keys=True)

    def from_dict(self, payload: dict[str, Any]) -> PatchKnowledgeBase:
        return PatchKnowledgeBase.model_validate(payload)

    def from_json(self, payload: str) -> PatchKnowledgeBase:
        return PatchKnowledgeBase.model_validate_json(payload)


class PatchKnowledgeRepository:
    def __init__(self, entries: list[PatchKnowledgeEntry] | None = None) -> None:
        self._base = PatchKnowledgeBase(entries=entries or self._seed_entries())

    def list_entries(self) -> list[PatchKnowledgeEntry]:
        return list(self._base.entries)

    def get(self, entry_id: str) -> PatchKnowledgeEntry | None:
        for entry in self._base.entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def base(self) -> PatchKnowledgeBase:
        return self._base

    def _seed_entries(self) -> list[PatchKnowledgeEntry]:
        return [
            self._entry(
                "intent_regression",
                "Intent classifier diverges from explicit read-only or operational constraints.",
                "Intent precedence allowed weak positive signals to override explicit negative constraints.",
                "Extract negative constraints before mutable intent classification and add regression fixtures for precedence.",
                ["semantic_runtime", "semantic_intent_resolution", "runtime_dispatcher"],
                ["services/semantic_runtime", "services/governance/lifecycle", "services/runtime"],
                ["intent_precedence_tests", "readonly_negative_constraint_tests"],
                ["firetest_governance_readonly"],
                "high",
            ),
            self._entry(
                "workspace_binding_regression",
                "Runtime loses one or more workspace roots during multi-workspace execution.",
                "Workspace context was represented as a single path instead of a structured root set.",
                "Normalize workspace context into project_root, external_roots, library_roots, readonly flags, and workspace ids.",
                ["workspace_context", "task_bootstrap", "runtime_context"],
                ["services/runtime", "services/workspaces"],
                ["workspace_binding_tests", "context_chain_tests"],
                ["firetest_multi_workspace"],
                "high",
            ),
            self._entry(
                "artifact_contract_regression",
                "Expected artifacts are missing, orphaned, or not bound to the producing TaskRun.",
                "Artifact creation was coupled to workspace mutation or not linked to runtime identity.",
                "Route outputs through Artifact Runtime and bind artifact_id, task_id, task_run_id, logical_path, and producer_step.",
                ["artifact_runtime", "canonical_operation_state", "validation"],
                ["services/artifacts", "services/runtime"],
                ["artifact_binding_tests", "readonly_artifact_tests"],
                ["firetest_artifact_runtime"],
                "high",
            ),
            self._entry(
                "validation_regression",
                "Validation reports pass while required outputs are absent or completion is blocked.",
                "Schema validation and operational completion validation were conflated.",
                "Separate structural validation from completion validation and make missing required outputs block final success.",
                ["validation", "completion", "speaker_truth"],
                ["services/validation", "services/runtime"],
                ["validation_ordering_tests", "speaker_truth_completion_tests"],
                ["firetest_validation_ordering"],
                "medium",
            ),
            self._entry(
                "speaker_truth_regression",
                "Speaker Truth allows success claims without timeline, artifact, validation, or completion evidence.",
                "Final response renderer consumed optimistic status instead of canonical operation state.",
                "Derive final claim permission from canonical state, timeline, validation, artifacts, and completion.",
                ["speaker_truth", "canonical_operation_state", "response_renderer"],
                ["services/runtime", "services/speaker"],
                ["speaker_truth_no_false_success_tests"],
                ["firetest_speaker_truth"],
                "high",
            ),
        ]

    def _entry(
        self,
        category: PatchCategory,
        regression: str,
        root_cause: str,
        correction_strategy: str,
        affected_modules: list[str],
        affected_files: list[str],
        related_tests: list[str],
        related_firetests: list[str],
        confidence: str,
    ) -> PatchKnowledgeEntry:
        return PatchKnowledgeEntry(
            entry_id=f"patch_knowledge_{category}",
            category=category,
            regression=regression,
            root_cause=root_cause,
            correction_strategy=correction_strategy,
            affected_modules=affected_modules,
            affected_files=affected_files,
            related_tests=related_tests,
            related_firetests=related_firetests,
            confidence=confidence,  # type: ignore[arg-type]
            risk="medium",
            runtime_version="SR-GR-RO-RD",
            patterns=[
                PatchPattern(
                    category=category,
                    name=f"{category}_pattern",
                    description=regression,
                    signals=[category, *related_tests],
                    anti_patterns=["project_specific_patch", "absolute_path_rule", "silent_fallback"],
                )
            ],
            evidence=[
                PatchEvidence(
                    evidence_type="generic_regression_pattern",
                    summary=f"Pattern derived from repeated runtime contract regressions in category {category}.",
                    refs=related_firetests,
                )
            ],
        )


class PatchKnowledgeQueryService:
    def __init__(self, repository: PatchKnowledgeRepository | None = None) -> None:
        self.repository = repository or PatchKnowledgeRepository()

    def list_entries(self) -> PatchKnowledgeQueryResult:
        entries = sorted(self.repository.list_entries(), key=lambda item: item.entry_id)
        return PatchKnowledgeQueryResult(version=self.repository.base().version, count=len(entries), entries=entries)

    def get_entry(self, entry_id: str) -> PatchKnowledgeEntry | None:
        return self.repository.get(entry_id)

    def query(self, request: PatchKnowledgeQuery) -> PatchKnowledgeQueryResult:
        entries = self.repository.list_entries()
        if request.category:
            entries = [entry for entry in entries if entry.category == request.category]
        if request.regression:
            term = request.regression.lower()
            entries = [entry for entry in entries if term in entry.regression.lower() or term in entry.root_cause.lower()]
        if request.module:
            term = request.module.lower()
            entries = [entry for entry in entries if any(term in module.lower() for module in entry.affected_modules)]
        if request.test:
            term = request.test.lower()
            entries = [entry for entry in entries if any(term in test.lower() for test in entry.related_tests)]
        if request.min_confidence:
            threshold = CONFIDENCE_ORDER[request.min_confidence]
            entries = [entry for entry in entries if CONFIDENCE_ORDER[entry.confidence] >= threshold]
        entries = sorted(entries, key=lambda item: (item.category, item.entry_id))[: request.limit]
        return PatchKnowledgeQueryResult(version=self.repository.base().version, count=len(entries), entries=entries)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "patch_intelligence_knowledge_base",
            "version": self.repository.base().version,
            "entries": len(self.repository.list_entries()),
            "deterministic": True,
            "stores_patch_code": False,
        }


class PatternNormalizer:
    def normalize(self, request: PatchPatternRecognitionRequest) -> dict[str, dict[str, object]]:
        rows = self._matrix_rows(request.regression_matrix) or self._matrix_rows(request.doctor_report.get("matrix", {}))
        findings = request.doctor_report.get("findings", [])
        normalized: dict[str, dict[str, object]] = {}
        for row in rows:
            category = self._patch_category(str(row.get("category", "")))
            if not category:
                continue
            status = str(row.get("status", "NOT_APPLICABLE"))
            if status not in {"FAIL", "WARN"}:
                continue
            normalized.setdefault(category, {"statuses": [], "reason_codes": [], "suspected_modules": [], "regressions": []})
            normalized[category]["statuses"].append(status)  # type: ignore[index]
            reason = row.get("reason_code")
            if reason:
                normalized[category]["reason_codes"].append(str(reason))  # type: ignore[index]
        for finding in findings if isinstance(findings, list) else []:
            if not isinstance(finding, dict):
                continue
            category = self._patch_category(str(finding.get("category", "")))
            if not category:
                continue
            normalized.setdefault(category, {"statuses": [], "reason_codes": [], "suspected_modules": [], "regressions": []})
            reason = finding.get("reason_code")
            if reason:
                normalized[category]["reason_codes"].append(str(reason))  # type: ignore[index]
                normalized[category]["regressions"].append(str(reason))  # type: ignore[index]
            for module in finding.get("suspected_modules", []) or []:
                normalized[category]["suspected_modules"].append(str(module))  # type: ignore[index]
        for data in normalized.values():
            for key in ("statuses", "reason_codes", "suspected_modules", "regressions"):
                data[key] = list(dict.fromkeys(data[key]))  # type: ignore[index]
        return normalized

    def _matrix_rows(self, matrix: object) -> list[dict[str, object]]:
        if isinstance(matrix, dict):
            rows = matrix.get("rows", [])
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
        return []

    def _patch_category(self, doctor_category: str) -> PatchCategory | None:
        if doctor_category in DOCTOR_CATEGORY_TO_PATCH_CATEGORY:
            return DOCTOR_CATEGORY_TO_PATCH_CATEGORY[doctor_category]
        lowered = doctor_category.lower()
        if lowered in PATCH_CATEGORIES:
            return lowered  # type: ignore[return-value]
        return None


class PatternScorer:
    def score(self, entry: PatchKnowledgeEntry, normalized: dict[str, object]) -> float:
        score = 0.0
        if normalized.get("statuses"):
            score += 0.45
        if normalized.get("reason_codes"):
            score += 0.2
        suspected = {str(item) for item in normalized.get("suspected_modules", []) if item}
        modules = set(entry.affected_modules)
        if suspected and modules.intersection(suspected):
            score += 0.2
        elif suspected:
            score += 0.08
        score += {"low": 0.03, "medium": 0.08, "high": 0.15}[entry.confidence]
        return min(score, 0.99)


class PatternConfidenceCalculator:
    def confidence(self, score: float) -> float:
        return round(max(0.0, min(score, 1.0)), 2)


class PatternMatcher:
    def __init__(self, repository: PatchKnowledgeRepository | None = None, scorer: PatternScorer | None = None, confidence: PatternConfidenceCalculator | None = None) -> None:
        self.repository = repository or PatchKnowledgeRepository()
        self.scorer = scorer or PatternScorer()
        self.confidence = confidence or PatternConfidenceCalculator()

    def match(self, normalized: dict[str, dict[str, object]], *, limit: int) -> list[PatchPatternMatch]:
        matches: list[PatchPatternMatch] = []
        entries_by_category = {entry.category: entry for entry in self.repository.list_entries()}
        for category, data in normalized.items():
            entry = entries_by_category.get(category)  # type: ignore[arg-type]
            if entry is None:
                continue
            score = self.confidence.confidence(self.scorer.score(entry, data))
            pattern_id = entry.patterns[0].pattern_id if entry.patterns else f"{entry.entry_id}_pattern"
            matches.append(
                PatchPatternMatch(
                    pattern_id=pattern_id,
                    knowledge_entry_id=entry.entry_id,
                    category=entry.category,
                    confidence=score,
                    regressions_related=[str(item) for item in data.get("regressions", [])],
                    suspected_modules=list(dict.fromkeys([*entry.affected_modules, *[str(item) for item in data.get("suspected_modules", [])]])),
                    recommended_strategy=entry.correction_strategy,
                    justification="Matched by canonical regression category, matrix status, reason codes, and structured suspected modules.",
                    risks=[entry.risk, "Patch plan must be reviewed by a governed executor before any change."],
                    deterministic=True,
                    prompt_used=False,
                )
            )
        return sorted(matches, key=lambda item: (-item.confidence, item.category, item.knowledge_entry_id))[:limit]


class PatchPatternEngine:
    def __init__(self, normalizer: PatternNormalizer | None = None, matcher: PatternMatcher | None = None) -> None:
        self.normalizer = normalizer or PatternNormalizer()
        self.matcher = matcher or PatternMatcher()

    def recognize(self, request: PatchPatternRecognitionRequest) -> PatchPatternRecognitionResult:
        normalized = self.normalizer.normalize(request)
        matches = self.matcher.match(normalized, limit=request.limit)
        return PatchPatternRecognitionResult(
            count=len(matches),
            matches=matches,
            deterministic=True,
            prompt_used=False,
            text_full_match_used=False,
        )


class PatchProposalBuilder:
    def __init__(self, repository: PatchKnowledgeRepository | None = None, pattern_engine: PatchPatternEngine | None = None) -> None:
        self.repository = repository or PatchKnowledgeRepository()
        self.pattern_engine = pattern_engine or PatchPatternEngine()

    def build(self, request: IntelligentPatchProposalRequest) -> IntelligentPatchProposal:
        matches = list(request.pattern_matches)
        if not matches:
            matches = self.pattern_engine.recognize(
                PatchPatternRecognitionRequest(
                    doctor_report=request.doctor_report,
                    regression_matrix=request.regression_matrix,
                )
            ).matches
        entries = [entry for match in matches if (entry := self.repository.get(match.knowledge_entry_id)) is not None]
        patch_plan = request.patch_plan or {}
        modules = self._unique([module for match in matches for module in match.suspected_modules] + [str(item) for item in patch_plan.get("affected_modules", []) or []])
        files = self._unique([file for entry in entries for file in entry.affected_files])
        tests = self._unique([test for entry in entries for test in entry.related_tests] + [str(item) for item in patch_plan.get("tests", []) or []])
        regressions = self._unique([regression for match in matches for regression in match.regressions_related])
        if not regressions:
            regressions = self._regressions_from_report(request.doctor_report)
        strategies = self._unique([match.recommended_strategy for match in matches] + [entry.correction_strategy for entry in entries])
        risks = self._unique([risk for match in matches for risk in match.risks] + [entry.risk for entry in entries])
        rollback = self._unique([str(item) for item in patch_plan.get("rollback", []) or []] + ["Revert only the focused correction after validating no runtime contract improvement."])
        confidence = round(sum(match.confidence for match in matches) / len(matches), 2) if matches else 0.0
        return IntelligentPatchProposal(
            regressions_covered=regressions,
            patterns_used=self._unique([match.pattern_id for match in matches]),
            modules_candidates=modules,
            files_candidates=files,
            justification=self._justification(matches, entries),
            suggested_strategy="; ".join(strategies) if strategies else "No structured correction strategy available.",
            risks=risks or ["Proposal must be reviewed before any execution."],
            rollback_recommended=rollback,
            tests_required=tests,
            confidence=confidence,
            knowledge_entry_ids=self._unique([entry.entry_id for entry in entries]),
            patch_plan_refs=self._unique([str(patch_plan.get("patch_plan_id"))] if patch_plan.get("patch_plan_id") else []),
            executor_independent=True,
            generates_code=False,
            generates_apply_patch=False,
            modifies_runtime=False,
        )

    def _justification(self, matches: list[PatchPatternMatch], entries: list[PatchKnowledgeEntry]) -> str:
        if not matches:
            return "No pattern match was available; proposal remains a conservative review placeholder."
        categories = self._unique([match.category for match in matches])
        evidence = self._unique([evidence.summary for entry in entries for evidence in entry.evidence])
        return f"Proposal derived from canonical pattern categories {', '.join(categories)} and KB evidence: {'; '.join(evidence) if evidence else 'structured pattern metadata'}."

    def _regressions_from_report(self, report: dict[str, Any]) -> list[str]:
        findings = report.get("findings", [])
        if not isinstance(findings, list):
            return []
        return self._unique([str(item.get("reason_code")) for item in findings if isinstance(item, dict) and item.get("reason_code")])

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys([value for value in values if value and value != "None"]))


class PatchProposalValidator:
    def validate(self, proposal: IntelligentPatchProposal) -> list[str]:
        errors: list[str] = []
        if proposal.generates_code:
            errors.append("proposal_must_not_generate_code")
        if proposal.generates_apply_patch:
            errors.append("proposal_must_not_generate_apply_patch")
        if proposal.modifies_runtime:
            errors.append("proposal_must_not_modify_runtime")
        if not proposal.executor_independent:
            errors.append("proposal_must_be_executor_independent")
        if not proposal.suggested_strategy:
            errors.append("proposal_missing_strategy")
        if not proposal.tests_required:
            errors.append("proposal_missing_tests")
        return errors


class PatchProposalSerializer:
    def to_dict(self, proposal: IntelligentPatchProposal) -> dict[str, Any]:
        return proposal.model_dump(mode="json")

    def to_json(self, proposal: IntelligentPatchProposal) -> str:
        return json.dumps(self.to_dict(proposal), ensure_ascii=False, sort_keys=True)

    def from_dict(self, payload: dict[str, Any]) -> IntelligentPatchProposal:
        return IntelligentPatchProposal.model_validate(payload)

    def from_json(self, payload: str) -> IntelligentPatchProposal:
        return IntelligentPatchProposal.model_validate_json(payload)


class IntelligentPatchProposalService:
    _proposals: dict[str, IntelligentPatchProposal] = {}

    def __init__(self, builder: PatchProposalBuilder | None = None, validator: PatchProposalValidator | None = None) -> None:
        self.builder = builder or PatchProposalBuilder()
        self.validator = validator or PatchProposalValidator()

    def create(self, request: IntelligentPatchProposalRequest) -> IntelligentPatchProposalResult:
        proposal = self.builder.build(request)
        errors = self.validator.validate(proposal)
        self._proposals[proposal.proposal_id] = proposal
        return IntelligentPatchProposalResult(
            proposal=proposal,
            valid=not errors,
            validation_errors=errors,
            deterministic=True,
            read_only=True,
            side_effects=False,
        )

    def get(self, proposal_id: str) -> IntelligentPatchProposal | None:
        return self._proposals.get(proposal_id)
