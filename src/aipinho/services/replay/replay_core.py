from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.repositories.replay.repositories import ReplayCaseRepository, ReplayDiffRepository, ReplayRunRepository, ReplaySnapshotRepository, ReplayTraceRepository
from aipinho.schemas.events.contracts import EventPublishRequest, StoredEvent
from aipinho.schemas.replay.contracts import *
from aipinho.services.events.event_core import EventContractValidator, redact_payload
from aipinho.utils.yaml_loader import load_yaml_file


SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
]


class ReplayAuditService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "replay" / "audit"

    def record(self, action: str, allowed: bool, **details: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "replay_audit.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"action": action, "allowed": allowed, "details": redact_payload(details)}, ensure_ascii=True) + "\n")


class ReplayEventEmitter:
    def __init__(self, root: Path | None = None) -> None:
        self.validator = EventContractValidator()
        self.root = root or PATHS.project_root / "data" / "runtime" / "replay" / "audit"

    def emit(self, event_type: str, human_summary: str, technical_summary: str, *, status: str = "created", severity: str = "info", correlation_id: str | None = None) -> str:
        request = EventPublishRequest(event_type=event_type, source_service="replay_harness", human_summary=human_summary, payload={"technical_summary": technical_summary, "side_effects_performed": False}, status=status, severity=severity, visibility="debugger", copy_policy="copy_sanitized", correlation_id=correlation_id)
        validation = self.validator.validate(request)
        if not validation.allowed or validation.contract is None:
            raise ValueError(",".join(validation.reasons))
        contract = validation.contract
        event = StoredEvent(event_type=request.event_type, source_service=request.source_service, human_summary=str(redact_payload(request.human_summary)), payload=redact_payload(request.payload), severity=request.severity or contract.default_severity, status=request.status or contract.default_status, visibility=request.visibility or contract.default_visibility, copy_policy=request.copy_policy or contract.copy_policy, speaker_allowed=contract.speaker_allowed, correlation_id=correlation_id)
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / "replay_events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")
        return event.event_id


class ReplaySnapshotSanitizer:
    def _sanitize_text(self, value: str, redactions: list[str]) -> str:
        sanitized = value
        for pattern in SECRET_PATTERNS:
            if pattern.search(sanitized):
                redactions.append(pattern.pattern[:24])
                sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
        return sanitized

    def sanitize_payload(self, value: Any, redactions: list[str] | None = None) -> Any:
        redactions = redactions if redactions is not None else []
        value = redact_payload(value)
        if isinstance(value, str):
            return self._sanitize_text(value, redactions)
        if isinstance(value, dict):
            return {str(k): self.sanitize_payload(v, redactions) for k, v in value.items()}
        if isinstance(value, list):
            return [self.sanitize_payload(v, redactions) for v in value]
        return value

    def sanitize(self, snapshot: ReplaySnapshot) -> ReplaySnapshot:
        redactions: list[str] = []
        payload = self.sanitize_payload(snapshot.model_dump(), redactions)
        sanitized = ReplaySnapshot(**payload)
        sanitized.metadata.sanitized = True
        sanitized.sanitization = ReplaySanitizationResult(sanitized=True, blocked=False, redactions=sorted(set(redactions)))
        return sanitized


class ReplaySnapshotBuilder:
    def build(self, request: ReplayCaptureRequest) -> ReplaySnapshot:
        payload = request.snapshot_payload
        metadata = ReplaySnapshotMetadata(capture_reason=request.reason, policy_hashes={"policy": "frozen"}, config_hashes={"config": "frozen"})
        snapshot = ReplaySnapshot(
            metadata=metadata,
            input_bundle=ReplayInputBundle(prompt=request.prompt, task_id=request.task_id, trace_id=request.trace_id, event_id=request.event_id, session_id=request.session_id, maintenance_run_id=request.maintenance_run_id, skill_trace_id=request.skill_trace_id, attachments=list(payload.get("attachments", []))),
            decision_bundle=ReplayDecisionBundle(**payload.get("decision_bundle", {})),
            event_timeline=ReplayEventTimeline(events=list(payload.get("events", []))),
            model_run_ref=ReplayModelRunRef(**payload.get("model_run_ref", {})),
            rag_result_ref=ReplayRagResultRef(**payload.get("rag_result_ref", {})),
            memory_usage_ref=ReplayMemoryUsageRef(**payload.get("memory_usage_ref", {})),
            maintenance_ref=ReplayMaintenanceRef(maintenance_run_id=request.maintenance_run_id, **payload.get("maintenance_ref", {})),
        )
        return ReplaySnapshotSanitizer().sanitize(snapshot)


class ReplayStoreService:
    def __init__(self, snapshots: ReplaySnapshotRepository | None = None, cases: ReplayCaseRepository | None = None, runs: ReplayRunRepository | None = None, traces: ReplayTraceRepository | None = None) -> None:
        self.snapshots = snapshots or ReplaySnapshotRepository()
        self.cases = cases or ReplayCaseRepository()
        self.runs = runs or ReplayRunRepository()
        self.traces = traces or ReplayTraceRepository()


class ReplayTraceService:
    def __init__(self, repository: ReplayTraceRepository | None = None) -> None:
        self.repository = repository or ReplayTraceRepository()
    def save(self, trace: ReplayTrace) -> ReplayTrace: return self.repository.save(trace)
    def get(self, trace_id: str) -> ReplayTrace | None: return self.repository.get(trace_id)


class ReplayCaptureService:
    def __init__(self, store: ReplayStoreService | None = None, emitter: ReplayEventEmitter | None = None) -> None:
        self.store = store or ReplayStoreService()
        self.emitter = emitter or ReplayEventEmitter()

    def capture(self, request: ReplayCaptureRequest) -> ReplayCaptureResult:
        snapshot = ReplaySnapshotBuilder().build(request)
        if not snapshot.sanitization.sanitized:
            return ReplayCaptureResult(status="blocked", reasons=["unsanitized_snapshot"])
        self.store.snapshots.save(snapshot)
        self.emitter.emit("replay_snapshot_created", "ReplaySnapshot criado.", "Sanitized snapshot persisted.", correlation_id=snapshot.metadata.snapshot_id)
        self.emitter.emit("replay_snapshot_sanitized", "ReplaySnapshot sanitizado.", "Raw/secret content redacted.", correlation_id=snapshot.metadata.snapshot_id)
        ReplayAuditService().record("capture", True, snapshot_id=snapshot.metadata.snapshot_id)
        return ReplayCaptureResult(status="created", snapshot=snapshot)


class ReplayCaseService:
    def __init__(self, store: ReplayStoreService | None = None, emitter: ReplayEventEmitter | None = None) -> None:
        self.store = store or ReplayStoreService()
        self.emitter = emitter or ReplayEventEmitter()
    def create(self, snapshot_id: str, title: str, category: str = "general", golden_expectations: list[dict[str, Any]] | None = None) -> ReplayCase:
        if self.store.snapshots.get(snapshot_id) is None:
            raise FileNotFoundError(snapshot_id)
        case = ReplayCase(snapshot_id=snapshot_id, title=title, category=category, golden_expectations=golden_expectations or [])
        self.store.cases.save(case)
        self.emitter.emit("replay_case_created", "ReplayCase criado.", "Case points to sanitized snapshot.", correlation_id=case.case_id)
        return case
    def get(self, case_id: str) -> ReplayCase | None: return self.store.cases.get(case_id)
    def list(self) -> list[ReplayCase]: return self.store.cases.list()


class ReplayDiffService:
    def __init__(self, repository: ReplayDiffRepository | None = None, emitter: ReplayEventEmitter | None = None) -> None:
        self.repository = repository or ReplayDiffRepository()
        self.emitter = emitter or ReplayEventEmitter()
    def create(self, run: ReplayRun, expected: dict[str, Any] | None = None) -> ReplayDiff:
        expected = expected or {}
        differences = []
        for key, value in expected.items():
            actual = run.result_payload.get(key)
            if actual != value:
                differences.append({"field": key, "expected": value, "actual": actual})
        diff = ReplayDiff(run_id=run.run_id, differences=differences, status="diff" if differences else "no_diff")
        self.repository.save(diff)
        self.emitter.emit("replay_diff_created", "ReplayDiff criado.", f"{len(differences)} differences.", correlation_id=run.run_id)
        return diff
    def get_for_run(self, run_id: str) -> ReplayDiff | None:
        for item in self.repository.list():
            if item.run_id == run_id:
                return item
        return None


class ReplayRunnerService:
    def __init__(self, store: ReplayStoreService | None = None, emitter: ReplayEventEmitter | None = None) -> None:
        self.store = store or ReplayStoreService()
        self.emitter = emitter or ReplayEventEmitter()
    def run(self, case_id: str) -> ReplayRun:
        case = self.store.cases.get(case_id)
        if case is None:
            raise FileNotFoundError(case_id)
        snapshot = self.store.snapshots.get(case.snapshot_id)
        if snapshot is None:
            raise FileNotFoundError(case.snapshot_id)
        self.emitter.emit("replay_run_started", "ReplayRun iniciado em dry-run.", "No real side effects are allowed.", correlation_id=case_id)
        trace = ReplayTrace(snapshot_id=snapshot.metadata.snapshot_id, steps=[{"step": "load_snapshot"}, {"step": "dry_run_compare"}])
        run = ReplayRun(case_id=case.case_id, snapshot_id=snapshot.metadata.snapshot_id, result_payload={"snapshot_id": snapshot.metadata.snapshot_id, "replayed": True})
        trace.run_id = run.run_id
        run.trace_id = trace.trace_id
        self.store.traces.save(trace)
        self.store.runs.save(run)
        ReplayDiffService().create(run)
        self.emitter.emit("replay_run_completed", "ReplayRun concluido em dry-run.", "No shell/git/patch/network/model inference executed.", status="completed", correlation_id=run.run_id)
        return run
    def get(self, run_id: str) -> ReplayRun | None: return self.store.runs.get(run_id)


class ReplayExportService:
    def export(self, snapshot: ReplaySnapshot) -> dict[str, Any]:
        if not snapshot.sanitization.sanitized:
            raise ValueError("export_unsanitized")
        return snapshot.model_dump()


class ReplayImportService:
    def import_snapshot(self, payload: dict[str, Any]) -> ReplaySnapshot:
        snapshot = ReplaySnapshot(**payload)
        if not snapshot.sanitization.sanitized:
            raise ValueError("import_unsanitized")
        return ReplaySnapshotRepository().save(snapshot)


class ReplayHarnessService:
    def status(self) -> ReplayStatus:
        return ReplayStatus()
