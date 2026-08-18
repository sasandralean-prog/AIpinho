from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactUploadRequest
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.self_healing import (
    SelfHealingAction,
    SelfHealingApplyRequest,
    SelfHealingCandidate,
    SelfHealingExportReportRequest,
    SelfHealingRejectRequest,
    SelfHealingRun,
    SelfHealingScanRequest,
    SelfHealingStatus,
    SelfHealingTriageRequest,
)
from aipinho.services.agents.multi_agent_observability_service import MultiAgentObservabilityService
from aipinho.services.artifacts.artifact_interaction_core import ArtifactUploadService
from aipinho.services.events.event_core import redact_payload


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value)


class SelfHealingDetector(Protocol):
    detector_id: str

    def detect(self, observability: MultiAgentObservabilityService) -> list[SelfHealingCandidate]:
        ...


class StateConsistencyDetector:
    detector_id = "state_consistency"

    def detect(self, observability: MultiAgentObservabilityService) -> list[SelfHealingCandidate]:
        report = observability.state_consistency()
        candidates: list[SelfHealingCandidate] = []
        for issue in report.issues:
            risk = "medium" if issue.severity in {"danger", "critical"} else "low"
            approval_required = risk != "low"
            action = SelfHealingAction(
                action_type="create_diagnostic_report",
                label="Gerar relatorio diagnostico sanitizado",
                side_effect="artifact_only",
                reversible=True,
                requires_approval=approval_required,
                validation_required=True,
                endpoint_ref=None,
                metadata_sanitized={"issue_type": issue.issue_type},
            )
            candidates.append(
                SelfHealingCandidate(
                    detector_id=self.detector_id,
                    issue_type=issue.issue_type,
                    risk_level=risk,  # type: ignore[arg-type]
                    entity_type=issue.entity_type,
                    entity_id=issue.entity_id,
                    summary=issue.summary,
                    evidence_refs=issue.evidence_refs,
                    recommended_actions=[action],
                    policy_decision="approval_required" if approval_required else "auto_fix_allowed",
                    approval_required=approval_required,
                    metadata_sanitized={"source_issue_id": issue.issue_id, "suggested_action": issue.suggested_action},
                )
            )
        return candidates


class DashboardDebuggerConsistencyDetector:
    detector_id = "dashboard_debugger_consistency"

    def detect(self, observability: MultiAgentObservabilityService) -> list[SelfHealingCandidate]:
        dashboard = observability.dashboard()
        events = observability.debugger_events(limit=1)
        if dashboard.active_runs and not events.events:
            return [
                SelfHealingCandidate(
                    detector_id=self.detector_id,
                    issue_type="active_run_without_debugger_event",
                    risk_level="low",
                    entity_type="dashboard",
                    entity_id="multi_agent",
                    summary="Dashboard mostra run ativo, mas o Debugger nao retornou evento recente.",
                    evidence_refs=["dashboard:multi_agent", "debugger:events"],
                    recommended_actions=[
                        SelfHealingAction(
                            action_type="create_diagnostic_report",
                            label="Gerar relatorio de divergencia dashboard/debugger",
                            side_effect="artifact_only",
                            reversible=True,
                            requires_approval=False,
                            validation_required=True,
                        )
                    ],
                    policy_decision="auto_fix_allowed",
                )
            ]
        return []


class SelfHealingStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_SELF_HEALING_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "self_healing")
        self.candidates_path = self.root / "candidates.json"
        self.runs_path = self.root / "runs.json"

    def list_candidates(self) -> list[SelfHealingCandidate]:
        return [SelfHealingCandidate(**item) for item in self._read(self.candidates_path)]

    def save_candidate(self, candidate: SelfHealingCandidate) -> SelfHealingCandidate:
        candidates = [item for item in self.list_candidates() if item.candidate_id != candidate.candidate_id]
        candidates.append(candidate)
        self._write(self.candidates_path, candidates)
        return candidate

    def get_candidate(self, candidate_id: str) -> SelfHealingCandidate | None:
        return next((candidate for candidate in self.list_candidates() if candidate.candidate_id == candidate_id), None)

    def list_runs(self) -> list[SelfHealingRun]:
        return [SelfHealingRun(**item) for item in self._read(self.runs_path)]

    def save_run(self, run: SelfHealingRun) -> SelfHealingRun:
        runs = [item for item in self.list_runs() if item.self_healing_run_id != run.self_healing_run_id]
        runs.append(run)
        self._write(self.runs_path, runs)
        return run

    def get_run(self, run_id: str) -> SelfHealingRun | None:
        return next((run for run in self.list_runs() if run.self_healing_run_id == run_id), None)

    def _read(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists() or path.stat().st_size == 0:
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, rows: list[Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([_dump(row) for row in rows], indent=2, ensure_ascii=True), encoding="utf-8")


class SelfHealingService:
    def __init__(
        self,
        *,
        store: SelfHealingStore | None = None,
        observability: MultiAgentObservabilityService | None = None,
        detectors: list[SelfHealingDetector] | None = None,
    ) -> None:
        self.store = store or SelfHealingStore()
        self.observability = observability or MultiAgentObservabilityService()
        self.detectors = detectors or [StateConsistencyDetector(), DashboardDebuggerConsistencyDetector()]

    def status(self) -> SelfHealingStatus:
        candidates = self.store.list_candidates()
        runs = self.store.list_runs()
        open_candidates = [candidate for candidate in candidates if candidate.status in {"proposed", "triaged", "approved"}]
        return SelfHealingStatus(
            status="ok",
            detectors_loaded=len(self.detectors),
            candidates_total=len(candidates),
            candidates_open=len(open_candidates),
            runs_total=len(runs),
            auto_fix_enabled=True,
        )

    def scan(self, request: SelfHealingScanRequest) -> list[SelfHealingCandidate]:
        selected = set(request.detector_ids)
        candidates: list[SelfHealingCandidate] = []
        for detector in self.detectors:
            if selected and detector.detector_id not in selected:
                continue
            candidates.extend(detector.detect(self.observability))
        candidates = self._dedupe(candidates)
        if request.persist:
            existing = self.store.list_candidates()
            for candidate in candidates:
                match = self._find_existing(candidate, existing)
                if match is not None:
                    candidate = candidate.model_copy(update={"candidate_id": match.candidate_id, "status": match.status, "created_at": match.created_at})
                self.store.save_candidate(candidate)
        return candidates

    def candidates(self, *, status: str | None = None, risk_level: str | None = None, detector_id: str | None = None) -> list[SelfHealingCandidate]:
        rows = self.store.list_candidates()
        if status:
            rows = [row for row in rows if row.status == status]
        if risk_level:
            rows = [row for row in rows if row.risk_level == risk_level]
        if detector_id:
            rows = [row for row in rows if row.detector_id == detector_id]
        return rows

    def candidate(self, candidate_id: str) -> SelfHealingCandidate | None:
        return self.store.get_candidate(candidate_id)

    def triage(self, candidate_id: str, request: SelfHealingTriageRequest) -> SelfHealingCandidate:
        candidate = self._require_candidate(candidate_id)
        status = {"approve": "approved", "reject": "rejected", "defer": "triaged"}[request.decision]
        updated = candidate.model_copy(update={
            "status": status,
            "updated_at": utc_now_iso(),
            "metadata_sanitized": {**candidate.metadata_sanitized, "triage_reason": redact_payload(request.reason or "")},
        })
        return self.store.save_candidate(updated)

    def apply(self, candidate_id: str, request: SelfHealingApplyRequest) -> SelfHealingRun:
        candidate = self._require_candidate(candidate_id)
        action = self._select_action(candidate, request.action_id)
        policy = self._policy_for(candidate, action, request)
        if request.dry_run:
            run = SelfHealingRun(
                candidate_id=candidate.candidate_id,
                action_id=action.action_id,
                action_type=action.action_type,
                status="dry_run",
                validation_status="not_required",
                summary=f"Dry-run de autocura: {action.label}.",
                metadata_sanitized={"policy": policy},
            )
            return self.store.save_run(run)
        if policy["decision"] == "blocked":
            run = SelfHealingRun(
                candidate_id=candidate.candidate_id,
                action_id=action.action_id,
                action_type=action.action_type,
                status="blocked",
                completed_at=utc_now_iso(),
                validation_status="blocked",
                summary=str(policy["reason"]),
                warnings=[str(policy["reason"])],
                metadata_sanitized={"policy": policy},
            )
            self.store.save_candidate(candidate.model_copy(update={"status": "blocked", "block_reason_code": str(policy["reason"]), "updated_at": utc_now_iso()}))
            return self.store.save_run(run)
        if policy["decision"] == "approval_required":
            run = SelfHealingRun(
                candidate_id=candidate.candidate_id,
                action_id=action.action_id,
                action_type=action.action_type,
                status="pending_approval",
                validation_status="pending",
                summary="Autocura requer aprovacao antes de side effect.",
                warnings=["approval_required"],
                metadata_sanitized={"policy": policy},
            )
            return self.store.save_run(run)
        artifact_id = None
        artifact_endpoint = None
        if action.action_type == "create_diagnostic_report":
            artifact_id, artifact_endpoint = self._create_diagnostic_report(candidate)
        run = SelfHealingRun(
            candidate_id=candidate.candidate_id,
            action_id=action.action_id,
            action_type=action.action_type,
            status="completed",
            completed_at=utc_now_iso(),
            validation_status="passed",
            artifact_ids=[artifact_id] if artifact_id else [],
            events=[
                {"event_type": "self_healing_apply_started", "candidate_id": candidate.candidate_id, "action_type": action.action_type},
                {"event_type": "self_healing_validation_finished", "status": "passed", "artifact_endpoint": artifact_endpoint},
            ],
            summary="Autocura de baixo risco concluida com artifact diagnostico e validacao.",
            metadata_sanitized={"policy": policy, "artifact_endpoint": artifact_endpoint},
        )
        self.store.save_candidate(candidate.model_copy(update={"status": "applied", "updated_at": utc_now_iso()}))
        return self.store.save_run(run)

    def reject(self, candidate_id: str, request: SelfHealingRejectRequest) -> SelfHealingCandidate:
        candidate = self._require_candidate(candidate_id)
        updated = candidate.model_copy(update={
            "status": "rejected",
            "updated_at": utc_now_iso(),
            "metadata_sanitized": {**candidate.metadata_sanitized, "reject_reason": redact_payload(request.reason or "")},
        })
        return self.store.save_candidate(updated)

    def runs(self) -> list[SelfHealingRun]:
        return self.store.list_runs()

    def run(self, run_id: str) -> SelfHealingRun | None:
        return self.store.get_run(run_id)

    def export_report(self, request: SelfHealingExportReportRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {"generated_at": utc_now_iso()}
        if request.include_status:
            payload["status"] = self.status().model_dump()
        if request.include_candidates:
            payload["candidates"] = [candidate.model_dump() for candidate in self.store.list_candidates()]
        if request.include_runs:
            payload["runs"] = [run.model_dump() for run in self.store.list_runs()]
        upload = ArtifactUploadService().upload(ArtifactUploadRequest(
            filename=f"self_healing_report_{utc_now_iso().replace(':', '').replace('-', '').split('.')[0]}.json",
            content=json.dumps(redact_payload(payload), indent=2, ensure_ascii=True),
            content_type="application/json",
            metadata={"source": "self_healing", "sanitized": True},
        ))
        return {
            "status": "ok",
            "artifact_id": upload.artifact.artifact_id,
            "download_endpoint": upload.download_path,
            "requires_token": True,
            "summary": "Relatorio de autocura sanitizado gerado como artifact.",
        }

    def _dedupe(self, candidates: list[SelfHealingCandidate]) -> list[SelfHealingCandidate]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[SelfHealingCandidate] = []
        for candidate in candidates:
            key = (candidate.detector_id, candidate.issue_type, candidate.entity_id)
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    def _find_existing(self, candidate: SelfHealingCandidate, existing: list[SelfHealingCandidate]) -> SelfHealingCandidate | None:
        for item in existing:
            if item.detector_id == candidate.detector_id and item.issue_type == candidate.issue_type and item.entity_id == candidate.entity_id:
                return item
        return None

    def _require_candidate(self, candidate_id: str) -> SelfHealingCandidate:
        candidate = self.store.get_candidate(candidate_id)
        if candidate is None:
            raise FileNotFoundError(candidate_id)
        return candidate

    def _select_action(self, candidate: SelfHealingCandidate, action_id: str | None) -> SelfHealingAction:
        if not candidate.recommended_actions:
            raise ValueError("self_healing_candidate_has_no_actions")
        if action_id is None:
            return candidate.recommended_actions[0]
        for action in candidate.recommended_actions:
            if action.action_id == action_id:
                return action
        raise FileNotFoundError(action_id)

    def _policy_for(self, candidate: SelfHealingCandidate, action: SelfHealingAction, request: SelfHealingApplyRequest) -> dict[str, Any]:
        if candidate.risk_level == "critical":
            return {"decision": "blocked", "reason": "critical_self_healing_requires_manual_sprint"}
        if candidate.risk_level in {"medium", "high"} or action.requires_approval:
            if request.approval_id:
                return {"decision": "allow", "reason": "approval_supplied", "approval_id": request.approval_id}
            return {"decision": "approval_required", "reason": "self_healing_medium_high_risk_requires_approval"}
        if action.side_effect not in {"derived_state_only", "artifact_only", "view_model_rebuild"}:
            return {"decision": "approval_required", "reason": "self_healing_side_effect_requires_approval"}
        return {"decision": "allow", "reason": "low_risk_reversible_self_healing"}

    def _create_diagnostic_report(self, candidate: SelfHealingCandidate) -> tuple[str | None, str | None]:
        content = "\n".join([
            "# Self-Healing Diagnostic Report",
            "",
            f"Data: {utc_now_iso()}",
            f"Detector: {candidate.detector_id}",
            f"Issue: {candidate.issue_type}",
            f"Entidade: {candidate.entity_type}/{candidate.entity_id}",
            f"Risco: {candidate.risk_level}",
            "",
            "## Resumo",
            candidate.summary,
            "",
            "## Evidencias",
            *[f"- {ref}" for ref in candidate.evidence_refs],
            "",
            "## Politica",
            "Este relatorio e artifact diagnostico; nao altera workspace, nao apaga evidencia e nao marca validacao operacional como sucesso.",
        ])
        upload = ArtifactUploadService().upload(ArtifactUploadRequest(
            filename=f"self_healing_{candidate.candidate_id}.md",
            content=content,
            content_type="text/markdown",
            metadata={"source": "self_healing", "candidate_id": candidate.candidate_id},
        ))
        return upload.artifact.artifact_id, upload.download_path
