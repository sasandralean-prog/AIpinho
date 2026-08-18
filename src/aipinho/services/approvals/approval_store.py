from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_event import ApprovalEvent
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.utils.safe_paths import resolve_within_root


def _dump_model(model) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _parse_request(data: dict) -> ApprovalRequest:
    if hasattr(ApprovalRequest, "model_validate"):
        return ApprovalRequest.model_validate(data)
    return ApprovalRequest.parse_obj(data)


def _parse_event(data: dict) -> ApprovalEvent:
    if hasattr(ApprovalEvent, "model_validate"):
        return ApprovalEvent.model_validate(data)
    return ApprovalEvent.parse_obj(data)


class ApprovalStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "approvals"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, approval_id: str) -> Path:
        return resolve_within_root(self.root / f"{approval_id}.json", self.root)

    def _events_path(self, approval_id: str) -> Path:
        return resolve_within_root(self.root / f"{approval_id}.events.json", self.root)

    def save(self, approval: ApprovalRequest) -> ApprovalRequest:
        path = self._path(approval.approval_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(_dump_model(approval), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return approval

    def get(self, approval_id: str) -> ApprovalRequest | None:
        path = self._path(approval_id)
        if not path.exists():
            return None
        return _parse_request(json.loads(path.read_text(encoding="utf-8")))

    def list(self, *, status: str | None = None, session_id: str | None = None, limit: int = 100) -> list[ApprovalRequest]:
        approvals: list[ApprovalRequest] = []
        for path in self.root.glob("approval_*.json"):
            if path.name.endswith(".events.json"):
                continue
            try:
                approval = _parse_request(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            if status is not None and approval.status != status:
                continue
            if session_id is not None and approval.session_id != session_id:
                continue
            approvals.append(approval)
        approvals.sort(key=lambda item: item.updated_at or item.created_at, reverse=True)
        return approvals[: max(0, limit)]

    def append_event(self, event: ApprovalEvent) -> None:
        events = self.list_events(event.approval_id)
        events.append(event)
        path = self._events_path(event.approval_id)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps([_dump_model(item) for item in events], ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def list_events(self, approval_id: str) -> list[ApprovalEvent]:
        path = self._events_path(approval_id)
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [_parse_event(item) for item in data if isinstance(item, dict)]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "store": "local_json", "path": str(self.root)}
