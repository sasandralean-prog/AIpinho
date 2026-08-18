from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.repositories.maintenance.repositories import (
    InvariantRepository,
    LessonCandidateRepository,
    MaintenanceAuditRepository,
    MaintenanceRunRepository,
    MaintenanceTraceRepository,
    RepairProposalRepository,
)
from aipinho.schemas.context.contracts import (
    ContextBuildRequest,
    ContextCandidate,
    ContextCitation,
    ContextEvidenceRef,
    ContextScope,
    ContextSourceRef,
)
from aipinho.schemas.events.contracts import EventPublishRequest, StoredEvent
from aipinho.schemas.maintenance.contracts import *
from aipinho.services.context.context_core import ContextKernelService
from aipinho.services.events.event_core import EventContractValidator, redact_payload
from aipinho.utils.yaml_loader import load_yaml_file


ALLOWED_MODES = {"diagnose", "repair_proposal", "patch_preview", "validation_proposal", "handoff_only"}
BLOCKED_ACTIONS = {
    "apply_patch", "write_config", "write_policy", "write_memory", "install_skill",
    "run_shell", "run_git", "browser_control", "computer_control", "external_api_call",
}


class MaintenanceRequestService:
    def validate(self, request: MaintenanceRequest) -> list[str]:
        reasons: list[str] = []
        if request.mode not in ALLOWED_MODES:
            reasons.append("maintenance_mode_not_allowed")
        requested_actions = request.signals.get("requested_actions", [])
        if isinstance(requested_actions, list) and set(map(str, requested_actions)) & BLOCKED_ACTIONS:
            reasons.append("autocure_action_blocked")
        return reasons


class MaintenanceScopeResolver:
    def resolve(self, request: MaintenanceRequest) -> MaintenanceScope:
        return request.scope


class MaintenanceAuditService:
    def __init__(self, repository: MaintenanceAuditRepository | None = None) -> None:
        self.repository = repository or MaintenanceAuditRepository()

    def record(self, action: str, allowed: bool, reasons: list[str], **details: Any) -> MaintenanceAudit:
        return self.repository.append(
            MaintenanceAudit(
                action=action,
                allowed=allowed,
                reasons=reasons,
                details=redact_payload(details),
            )
        )


class MaintenanceEventEmitter:
    def __init__(self, root: Path | None = None) -> None:
        self.validator = EventContractValidator()
        self.root = root or PATHS.project_root / "data" / "runtime" / "maintenance" / "audit"

    def emit(
        self,
        event_type: str,
        human_summary: str,
        technical_summary: str,
        *,
        run_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> str:
        request = EventPublishRequest(
            event_type=event_type,
            source_service="maintenance_plane",
            human_summary=human_summary,
            payload={
                "run_id": run_id,
                "technical_summary": technical_summary,
                "side_effects_performed": False,
            },
            severity=severity,
            status=status,
            visibility="debugger",
            copy_policy="copy_sanitized",
            correlation_id=run_id,
        )
        validation = self.validator.validate(request)
        if not validation.allowed or validation.contract is None:
            raise ValueError(",".join(validation.reasons))
        contract = validation.contract
        event = StoredEvent(
            event_type=request.event_type,
            source_service=request.source_service,
            human_summary=str(redact_payload(request.human_summary)),
            payload=redact_payload(request.payload),
            severity=request.severity or contract.default_severity,
            status=request.status or contract.default_status,
            visibility=request.visibility or contract.default_visibility,
            copy_policy=request.copy_policy or contract.copy_policy,
            speaker_allowed=contract.speaker_allowed,
            correlation_id=request.correlation_id,
        )
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "maintenance_events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")
        return event.event_id


class MaintenanceTraceService:
    def __init__(self, repository: MaintenanceTraceRepository | None = None) -> None:
        self.repository = repository or MaintenanceTraceRepository()

    def save(self, trace: MaintenanceTrace) -> MaintenanceTrace:
        return self.repository.save(trace)

    def get_for_run(self, run: MaintenanceRun) -> MaintenanceTrace | None:
        return self.repository.get(run.trace_id) if run.trace_id else None


class MaintenanceRunService:
    def __init__(self, repository: MaintenanceRunRepository | None = None) -> None:
        self.repository = repository or MaintenanceRunRepository()

    def create(self, request: MaintenanceRequest) -> MaintenanceRun:
        return self.repository.save(
            MaintenanceRun(
                request_id=request.request_id,
                mode=request.mode,
                scope=request.scope,
            )
        )

    def save(self, run: MaintenanceRun) -> MaintenanceRun:
        run.updated_at = utc_now_iso()
        return self.repository.save(run)

    def get(self, run_id: str) -> MaintenanceRun | None:
        return self.repository.get(run_id)

    def list(self) -> list[MaintenanceRun]:
        return self.repository.list()


class InvariantLoader:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "maintenance" / "invariant_registry.yaml"

    def load(self) -> dict[str, InvariantDefinition]:
        raw = load_yaml_file(self.path, root=PATHS.project_root).get("invariants", {})
        return {
            invariant_id: InvariantDefinition(invariant_id=invariant_id, **definition)
            for invariant_id, definition in raw.items()
        }


class InvariantRegistryService:
    def __init__(self, loader: InvariantLoader | None = None) -> None:
        self.loader = loader or InvariantLoader()

    def list(self) -> list[InvariantDefinition]:
        return sorted(self.loader.load().values(), key=lambda item: item.invariant_id)

    def get(self, invariant_id: str) -> InvariantDefinition | None:
        return self.loader.load().get(invariant_id)


class InvariantViolationClassifier:
    ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

    def highest(self, violations: list[InvariantViolation]) -> str:
        if not violations:
            return "none"
        return max((item.severity for item in violations), key=lambda value: self.ORDER.get(value, -1))


class InvariantResultBuilder:
    def build(self, checked: list[str], violations: list[InvariantViolation]) -> InvariantCheckResult:
        status = "violations_detected" if violations else "passed"
        return InvariantCheckResult(status=status, checked_invariants=checked, violations=violations)


class InvariantChecker:
    def __init__(
        self,
        registry: InvariantRegistryService | None = None,
        repository: InvariantRepository | None = None,
        emitter: MaintenanceEventEmitter | None = None,
    ) -> None:
        self.registry = registry or InvariantRegistryService()
        self.repository = repository or InvariantRepository()
        self.emitter = emitter or MaintenanceEventEmitter()

    def _matches(self, condition: dict[str, Any], signals: dict[str, Any]) -> bool:
        checks: list[bool] = []
        for key, expected in condition.items():
            if key == "any":
                checks.append(any(self._matches(item, signals) for item in expected))
            elif key == "all":
                checks.append(all(self._matches(item, signals) for item in expected))
            elif key == "not":
                checks.append(not self._matches(expected, signals))
            elif isinstance(expected, dict) and isinstance(signals.get(key), dict):
                checks.append(self._matches(expected, signals[key]))
            else:
                checks.append(signals.get(key) == expected)
        return bool(checks) and all(checks)

    def check(self, request: InvariantCheckRequest, *, persist: bool = True, emit: bool = True) -> InvariantCheckResult:
        definitions = self.registry.list()
        if request.invariant_ids:
            selected = set(request.invariant_ids)
            definitions = [item for item in definitions if item.invariant_id in selected]
        violations: list[InvariantViolation] = []
        event_ids: list[str] = []
        if emit:
            event_ids.append(self.emitter.emit(
                "invariant_check_started",
                "Checagem de invariantes iniciada.",
                f"Checking {len(definitions)} registered invariants.",
            ))
        source_refs = [str(item) for item in request.signals.get("source_refs", [])]
        for definition in definitions:
            if definition.violation_if and self._matches(definition.violation_if, request.signals):
                violation = InvariantViolation(
                    invariant_id=definition.invariant_id,
                    severity=definition.severity,
                    description=definition.description,
                    evidence=InvariantEvidence(
                        invariant_id=definition.invariant_id,
                        matched_conditions=definition.violation_if,
                        source_refs=source_refs,
                    ),
                    recommended_action=definition.recommended_action,
                )
                violations.append(violation)
                if emit:
                    event_ids.append(self.emitter.emit(
                        "invariant_violation_detected",
                        f"Invariante violada: {definition.invariant_id}.",
                        definition.description,
                        severity=definition.severity,
                        status="blocked",
                    ))
        result = InvariantResultBuilder().build(
            [item.invariant_id for item in definitions],
            violations,
        )
        if persist:
            self.repository.save_result(result)
        if emit:
            self.emitter.emit(
                "invariant_check_completed",
                "Checagem de invariantes concluida.",
                f"Detected {len(violations)} violations.",
                severity=InvariantViolationClassifier().highest(violations),
                status=result.status,
            )
        return result


class DiagnosisEvidenceCollector:
    def collect(self, request: DiagnosisRequest) -> tuple[list[DiagnosisEvidence], str | None, str | None]:
        if not request.evidence:
            raise ValueError("diagnosis_evidence_required")
        candidates: list[ContextCandidate] = []
        for evidence in request.evidence:
            ref = ContextSourceRef(
                source_type=evidence.source_type,
                source_id=evidence.source_id,
            )
            candidates.append(
                ContextCandidate(
                    layer=self._layer_for(evidence.source_type),
                    source_type=evidence.source_type,
                    source_ref=ref,
                    summary=evidence.summary,
                    content=json.dumps(redact_payload(evidence.details), ensure_ascii=True),
                    priority=8,
                    trust_level="verified" if evidence.confidence >= 0.8 else "derived",
                    citations=[ContextCitation(source_ref=ref, label="maintenance-evidence", confidence=evidence.confidence)],
                    evidence_refs=[ContextEvidenceRef(source_ref=ref, summary=evidence.summary, confidence=evidence.confidence)],
                    metadata={"sanitized": True, "raw_ref": evidence.raw_ref},
                )
            )
        scope_payload = request.scope.model_dump(exclude_none=True)
        context_scope = {
            key: scope_payload[key]
            for key in ("session_id", "task_id", "trace_id")
            if key in scope_payload
        }
        context_request = ContextBuildRequest(
            purpose="maintenance_diagnosis",
            scope=ContextScope(**context_scope),
            current_message=request.reason or "Maintenance diagnosis request.",
            candidates=candidates,
            persist=True,
            requested_by="maintenance_plane",
            max_budget_chars=80000,
        )
        built = ContextKernelService().build_ephemeral(context_request)
        return request.evidence, built.bundle.bundle_id, built.bundle.trace_id

    @staticmethod
    def _layer_for(source_type: str) -> str:
        mapping = {
            "event": "events",
            "event_summary": "events",
            "debugger_trace": "debugger_eval_traces",
            "context_bundle": "context_bundles",
            "skill_trace": "skill_traces",
            "validation_result": "validation_results",
            "rag_chunk": "governed_rag",
            "curated_memory": "curated_memory",
            "task": "active_task",
        }
        return mapping.get(source_type, "events")


class AnomalyDetector:
    def detect(self, signals: dict[str, Any]) -> list[AnomalySignal]:
        anomalies: list[AnomalySignal] = []
        for key, value in signals.items():
            if key.endswith("_violation") and value is True:
                anomalies.append(
                    AnomalySignal(
                        signal_type=key,
                        source_ref="structured_signal",
                        severity="high",
                        summary=f"Structured anomaly signal: {key}.",
                        details={key: True},
                    )
                )
        return anomalies


class ConfidenceEstimator:
    def estimate(self, evidence: list[DiagnosisEvidence], violations: list[InvariantViolation]) -> DiagnosisConfidence:
        direct = [item for item in evidence if item.event_ref or item.trace_ref or item.confidence >= 0.8]
        score = min(1.0, (sum(item.confidence for item in evidence) / len(evidence)) if evidence else 0.0)
        if direct and violations:
            level = "high"
        elif len(evidence) >= 2:
            level = "medium"
        else:
            level = "low"
        return DiagnosisConfidence(
            level=level,
            score=round(score, 3),
            reasons=["evidence_present", f"violation_count:{len(violations)}"],
        )


class RootCauseAnalyzer:
    def analyze(
        self,
        violations: list[InvariantViolation],
        evidence: list[DiagnosisEvidence],
        confidence: DiagnosisConfidence,
    ) -> list[RootCauseCandidate]:
        refs = [item.evidence_id for item in evidence]
        return [
            RootCauseCandidate(
                summary=f"Candidate root cause linked to invariant {violation.invariant_id}.",
                evidence_refs=refs + violation.evidence.source_refs,
                confidence=confidence,
            )
            for violation in violations
        ]


class DiagnosisReportBuilder:
    def findings(self, violations: list[InvariantViolation], evidence: list[DiagnosisEvidence]) -> list[DiagnosisFinding]:
        refs = [item.evidence_id for item in evidence]
        return [
            DiagnosisFinding(
                title=violation.invariant_id,
                summary=violation.description,
                severity=violation.severity,
                evidence_refs=refs + violation.evidence.source_refs,
                invariant_id=violation.invariant_id,
            )
            for violation in violations
        ]


class DiagnosisService:
    def __init__(
        self,
        runs: MaintenanceRunService | None = None,
        traces: MaintenanceTraceService | None = None,
        emitter: MaintenanceEventEmitter | None = None,
        audit: MaintenanceAuditService | None = None,
    ) -> None:
        self.runs = runs or MaintenanceRunService()
        self.traces = traces or MaintenanceTraceService()
        self.emitter = emitter or MaintenanceEventEmitter()
        self.audit = audit or MaintenanceAuditService()

    def diagnose(self, request: DiagnosisRequest) -> MaintenanceResult:
        reasons = MaintenanceRequestService().validate(request)
        if not request.evidence:
            reasons.append("diagnosis_evidence_required")
        if reasons:
            self.audit.record("diagnose", False, reasons, request_id=request.request_id)
            return MaintenanceResult(status="rejected", reasons=reasons)
        run = self.runs.create(request)
        event_ids = [
            self.emitter.emit(
                "maintenance_run_created",
                "Execucao de manutencao criada em modo diagnostico.",
                "Read-only maintenance run created.",
                run_id=run.run_id,
            ),
            self.emitter.emit(
                "maintenance_diagnosis_started",
                "Diagnostico supervisionado iniciado.",
                "Diagnosis started without side effects.",
                run_id=run.run_id,
            ),
        ]
        try:
            evidence, bundle_id, context_trace_id = DiagnosisEvidenceCollector().collect(request)
            invariant_result = InvariantChecker().check(
                InvariantCheckRequest(signals=request.signals, scope=request.scope),
                persist=True,
                emit=True,
            )
            anomalies = AnomalyDetector().detect(request.signals)
            confidence = ConfidenceEstimator().estimate(evidence, invariant_result.violations)
            findings = DiagnosisReportBuilder().findings(invariant_result.violations, evidence)
            root_causes = RootCauseAnalyzer().analyze(invariant_result.violations, evidence, confidence)
            diagnosis = DiagnosisResult(
                run_id=run.run_id,
                status="completed",
                findings=findings,
                evidence=evidence,
                anomalies=anomalies,
                invariant_result=invariant_result,
                root_causes=root_causes,
                confidence=confidence,
                context_bundle_id=bundle_id,
                context_trace_id=context_trace_id,
            )
            event_ids.append(self.emitter.emit(
                "maintenance_diagnosis_completed",
                "Diagnostico supervisionado concluido.",
                f"Diagnosis completed with {len(findings)} findings.",
                run_id=run.run_id,
                status="completed",
            ))
            trace = MaintenanceTrace(
                run_id=run.run_id,
                steps=[
                    {"step": "scope_resolved", "scope": request.scope.model_dump()},
                    {"step": "context_bundle_built", "bundle_id": bundle_id},
                    {"step": "evidence_collected", "count": len(evidence)},
                    {"step": "invariants_checked", "count": len(invariant_result.checked_invariants)},
                    {"step": "diagnosis_completed", "finding_count": len(findings)},
                ],
                event_ids=event_ids,
                context_bundle_id=bundle_id,
                context_trace_id=context_trace_id,
            )
            self.traces.save(trace)
            run.status = "completed"
            run.diagnosis = diagnosis
            run.trace_id = trace.trace_id
            run.violations = invariant_result.violations
            self.runs.save(run)
            self.audit.record("diagnose", True, [], run_id=run.run_id, side_effects_performed=False)
            return MaintenanceResult(status="completed", run=run)
        except Exception as exc:
            event_ids.append(self.emitter.emit(
                "maintenance_diagnosis_failed",
                "Diagnostico supervisionado falhou.",
                str(exc),
                run_id=run.run_id,
                severity="error",
                status="failed",
            ))
            run.status = "failed"
            self.runs.save(run)
            self.audit.record("diagnose", False, [str(exc)], run_id=run.run_id)
            return MaintenanceResult(status="failed", run=run, reasons=[str(exc)])


class RepairRiskService:
    def assess(self, request: RepairProposalRequest, diagnosis: DiagnosisResult) -> RepairRisk:
        severity_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        highest = max(
            (item.severity for item in diagnosis.findings),
            key=lambda value: severity_order.get(value, 0),
            default="medium",
        )
        level = "high" if highest in {"high", "critical"} or request.risk_signals else "medium"
        return RepairRisk(
            level=level,
            reasons=[f"diagnosis_severity:{highest}", *request.risk_signals],
            approval_required=level == "high",
        )


class RepairValidationPlanService:
    def build(self, checks: list[str]) -> RepairValidationPlan:
        return RepairValidationPlan(
            checks=checks or ["contract_tests", "focused_regression", "post_change_validation"],
            execution_performed=False,
        )


class RepairPlannerService:
    def plan(self, request: RepairProposalRequest, diagnosis: DiagnosisResult) -> RepairPlan:
        steps = [
            RepairStep(
                action="preview_change",
                target=target,
                description=description,
                side_effect=False,
            )
            for target, description in zip(
                request.affected_targets or [None],
                request.proposed_steps or ["Prepare a governed repair preview."],
            )
        ]
        return RepairPlan(
            steps=steps,
            validation=RepairValidationPlanService().build(request.validation_checks),
            rollback_required=request.repair_type in {"config_change_preview", "policy_change_preview", "patch_plan_preview"},
        )


class RepairProposalService:
    def __init__(
        self,
        runs: MaintenanceRunService | None = None,
        repository: RepairProposalRepository | None = None,
        emitter: MaintenanceEventEmitter | None = None,
    ) -> None:
        self.runs = runs or MaintenanceRunService()
        self.repository = repository or RepairProposalRepository()
        self.emitter = emitter or MaintenanceEventEmitter()

    def propose(self, request: RepairProposalRequest) -> RepairProposal:
        run = self.runs.get(request.diagnosis_run_id)
        if run is None or run.diagnosis is None:
            self.emitter.emit(
                "repair_proposal_blocked",
                "Proposta de reparo bloqueada por ausencia de diagnostico.",
                "A completed diagnosis is required.",
                status="blocked",
            )
            raise ValueError("diagnosis_result_required")
        if not run.diagnosis.evidence:
            raise ValueError("diagnosis_evidence_required")
        risk = RepairRiskService().assess(request, run.diagnosis)
        proposal = RepairProposal(
            diagnosis_run_id=run.run_id,
            repair_type=request.repair_type,
            summary=request.summary,
            evidence_refs=[item.evidence_id for item in run.diagnosis.evidence],
            affected_targets=request.affected_targets,
            plan=RepairPlannerService().plan(request, run.diagnosis),
            risk=risk,
            approval_required=risk.approval_required,
            execution_performed=False,
        )
        self.repository.save(proposal)
        self.emitter.emit(
            "repair_proposal_created",
            "Proposta de reparo supervisionada criada.",
            f"Proposal {proposal.proposal_id} created without execution.",
            run_id=run.run_id,
        )
        return proposal

    def list(self) -> list[RepairProposal]:
        return self.repository.list()

    def get(self, proposal_id: str) -> RepairProposal | None:
        return self.repository.get(proposal_id)


class ProposalLookup:
    def __init__(self, repository: RepairProposalRepository | None = None) -> None:
        self.repository = repository or RepairProposalRepository()

    def require(self, proposal_id: str) -> RepairProposal:
        proposal = self.repository.get(proposal_id)
        if proposal is None:
            raise FileNotFoundError(proposal_id)
        return proposal


def persist_preview(folder: str, identifier: str, payload: Any) -> None:
    root = PATHS.project_root / "data" / "runtime" / "maintenance" / folder
    root.mkdir(parents=True, exist_ok=True)
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload
    (root / f"{identifier}.json").write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


class MaintenancePatchPreviewService:
    def create(self, proposal_id: str) -> MaintenancePatchPreview:
        proposal = ProposalLookup().require(proposal_id)
        preview = MaintenancePatchPreview(
            proposal_id=proposal_id,
            summary="Governed handoff prepared for Patch Planning Pipeline; no diff was applied.",
            changes=[{"target": item, "operation": "preview"} for item in proposal.affected_targets],
            diff_proposal_ref=f"patch_planning_handoff:{proposal_id}",
        )
        persist_preview("patch_previews", preview.preview_id, preview)
        MaintenanceEventEmitter().emit(
            "maintenance_patch_preview_created",
            "Preview de patch de manutencao criado.",
            "Delegated to patch_planning_pipeline; apply_performed=false.",
            run_id=proposal.diagnosis_run_id,
        )
        return preview


class MaintenanceConfigChangePreviewService:
    def create(self, proposal_id: str) -> MaintenanceConfigChangePreview:
        proposal = ProposalLookup().require(proposal_id)
        preview = MaintenanceConfigChangePreview(
            proposal_id=proposal_id,
            summary="Conceptual configuration change preview; no file was written.",
            changes=[{"target": item, "operation": "preview_only"} for item in proposal.affected_targets],
        )
        persist_preview("config_previews", preview.preview_id, preview)
        MaintenanceEventEmitter().emit(
            "maintenance_config_preview_created",
            "Preview de configuracao criado.",
            "write_performed=false.",
            run_id=proposal.diagnosis_run_id,
        )
        return preview


class MaintenanceValidationRecommendationService:
    def create(self, proposal_id: str) -> MaintenanceValidationRecommendation:
        proposal = ProposalLookup().require(proposal_id)
        recommendation = MaintenanceValidationRecommendation(
            proposal_id=proposal_id,
            checks=proposal.plan.validation.checks,
            rationale="Validation Gate must execute these checks after an approved change.",
        )
        persist_preview("validation_plans", recommendation.recommendation_id, recommendation)
        MaintenanceEventEmitter().emit(
            "maintenance_validation_plan_created",
            "Plano de validacao recomendado.",
            "No test or command was executed by Maintenance Plane.",
            run_id=proposal.diagnosis_run_id,
        )
        return recommendation


class MaintenanceRollbackPlanner:
    def create(self, proposal_id: str) -> MaintenanceRollbackPlan:
        proposal = ProposalLookup().require(proposal_id)
        plan = MaintenanceRollbackPlan(
            proposal_id=proposal_id,
            steps=[
                "Capture approved pre-change snapshot.",
                "Restore only through the owning governed pipeline.",
                "Run post-rollback validation.",
            ],
        )
        persist_preview("rollback_plans", plan.rollback_id, plan)
        MaintenanceEventEmitter().emit(
            "maintenance_rollback_plan_created",
            "Plano de rollback criado.",
            "execution_performed=false.",
            run_id=proposal.diagnosis_run_id,
        )
        return plan


class RepairHandoffService:
    def create(self, proposal_id: str) -> RepairHandoff:
        proposal = ProposalLookup().require(proposal_id)
        handoff = RepairHandoff(
            proposal_id=proposal_id,
            target_owner="policy_kernel",
            approval=RepairApprovalRequest(
                approval_required=True,
                reason=f"Repair risk is {proposal.risk.level}; execution remains outside Maintenance Plane.",
                requested_action=proposal.repair_type,
            ),
            execution_performed=False,
        )
        persist_preview("repair_proposals", handoff.handoff_id, handoff)
        MaintenanceEventEmitter().emit(
            "repair_handoff_created",
            "Handoff de reparo criado para o fluxo governado.",
            "Policy, capability, approval and validation remain authoritative.",
            run_id=proposal.diagnosis_run_id,
        )
        MaintenanceEventEmitter().emit(
            "autocure_requires_approval",
            "Autocura supervisionada requer aprovacao.",
            "No execution was performed.",
            run_id=proposal.diagnosis_run_id,
            severity="warning",
            status="pending_approval",
        )
        return handoff


class MaintenanceLessonCandidateService:
    def __init__(self, repository: LessonCandidateRepository | None = None) -> None:
        self.repository = repository or LessonCandidateRepository()

    def create(self, request: MaintenanceLessonCandidateRequest) -> MaintenanceLessonCandidate:
        if not request.evidence_refs:
            raise ValueError("lesson_evidence_required")
        candidate = MaintenanceLessonCandidate(**request.model_dump(), memory_mutation_performed=False)
        self.repository.save(candidate)
        MaintenanceEventEmitter().emit(
            "maintenance_lesson_candidate_created",
            "Candidato de licao de manutencao criado.",
            "Candidate only; CuratedMemory was not mutated.",
            run_id=request.run_id,
        )
        return candidate

    def list(self) -> list[MaintenanceLessonCandidate]:
        return self.repository.list()


class RepairRejectionService:
    def reject(self, code: str, human_reason: str) -> RepairRejectionReason:
        return RepairRejectionReason(code=code, human_reason=human_reason)


class MaintenancePlaneService:
    def status(self) -> MaintenanceStatus:
        warnings: list[str] = []
        try:
            count = len(InvariantRegistryService().list())
        except Exception as exc:
            count = 0
            warnings.append(str(exc))
        return MaintenanceStatus(
            status="ok" if not warnings else "degraded",
            invariant_count=count,
            warnings=warnings,
        )

    def diagnose(self, request: DiagnosisRequest) -> MaintenanceResult:
        return DiagnosisService().diagnose(request)
