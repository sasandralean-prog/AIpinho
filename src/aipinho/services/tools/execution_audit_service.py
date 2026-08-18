from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.tools.execution_audit import ExecutionAuditEvent
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


def _dump_model(model) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


class ExecutionAuditService:
    def __init__(self, root: Path | None = None, audit_log_root: Path | None = None, config_path: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "executions"
        self.audit_log_root = audit_log_root or PATHS.project_root / "data" / "logs" / "audit"
        self.config_path = config_path or PATHS.config_root / "runtime" / "execution_audit_policy.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit_log_root.mkdir(parents=True, exist_ok=True)

    def record(self, result: ToolExecutionResult, *, policy_decision_id: str | None = None) -> ExecutionAuditEvent:
        event = ExecutionAuditEvent(
            audit_event_id=f"audit_{uuid4().hex}",
            execution_id=result.execution_id,
            tool_id=result.tool_id,
            action=result.action,
            workspace=result.workspace,
            target_path=result.target_path,
            status=result.status,
            bytes_read=int(result.metadata.get("bytes_read", 0) or 0),
            side_effects=result.side_effects,
            policy_decision_id=policy_decision_id,
            timestamp=utc_now(),
            trace_summary=self._trace_summary(result.trace),
            violations=list(result.violations),
            warnings=list(result.warnings),
        )
        result.audit_event_id = event.audit_event_id
        try:
            self._write_result(result)
            self._append_event(event)
        except OSError as exc:
            warning = f"audit_persist_failed:{exc.__class__.__name__}"
            result.warnings = list(dict.fromkeys([*result.warnings, warning]))
            event.warnings = list(dict.fromkeys([*event.warnings, warning]))
        return event

    def get_result(self, execution_id: str) -> ToolExecutionResult | None:
        path = self._result_path(execution_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if hasattr(ToolExecutionResult, "model_validate"):
            return ToolExecutionResult.model_validate(data)
        return ToolExecutionResult.parse_obj(data)

    def get_events(self, execution_id: str) -> list[ExecutionAuditEvent]:
        path = self._event_path(execution_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        if hasattr(ExecutionAuditEvent, "model_validate"):
            return [ExecutionAuditEvent.model_validate(item) for item in data if isinstance(item, dict)]
        return [ExecutionAuditEvent.parse_obj(item) for item in data if isinstance(item, dict)]

    def _write_result(self, result: ToolExecutionResult) -> None:
        path = self._result_path(result.execution_id)
        temp = path.with_suffix(".tmp")
        safe = _dump_model(result)
        safe["content"] = None
        temp.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def _append_event(self, event: ExecutionAuditEvent) -> None:
        events = self.get_events(event.execution_id)
        events.append(event)
        path = self._event_path(event.execution_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps([_dump_model(item) for item in events], ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        jsonl = resolve_within_root(self.audit_log_root / "executions.jsonl", self.audit_log_root)
        with jsonl.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump_model(event), ensure_ascii=False) + "\n")

    def _result_path(self, execution_id: str) -> Path:
        return resolve_within_root(self.root / f"{execution_id}.json", self.root)

    def _event_path(self, execution_id: str) -> Path:
        return resolve_within_root(self.root / f"{execution_id}.events.json", self.root)

    def _trace_summary(self, trace: list[dict]) -> list[str]:
        values = []
        for item in trace[:20]:
            stage = item.get("stage", "unknown")
            decision = item.get("decision", item.get("status", "unknown"))
            reason = item.get("reason", "")
            values.append(f"{stage}:{decision}:{reason}")
        return values

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "execution_audit", "root": str(self.root), "log_content": False}
