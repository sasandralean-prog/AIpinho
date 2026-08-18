from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.ownership import (
    AgentHopCheckRequest,
    AgentHopDecision,
    TaskOwnership,
    WorkspaceLock,
    WorkspaceLockCreateRequest,
    WorkspaceLockOverrideRequest,
    WorkspaceLockReleaseRequest,
    WriteConflictCheckRequest,
    WriteConflictDecision,
)
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.events.event_core import redact_payload
from aipinho.utils.safe_paths import resolve_within_root


TERMINAL_LOCK_STATUSES = {"released", "expired", "overridden"}


def _dump(model) -> dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _parse_lock(data: dict) -> WorkspaceLock:
    if hasattr(WorkspaceLock, "model_validate"):
        return WorkspaceLock.model_validate(data)
    return WorkspaceLock.parse_obj(data)


def _canonical_path(value: str) -> str:
    return str(Path(value).expanduser()).rstrip("\\/").lower()


def _path_overlaps(left: str, right: str) -> bool:
    left_norm = _canonical_path(left)
    right_norm = _canonical_path(right)
    return left_norm == right_norm or left_norm.startswith(right_norm + "\\") or right_norm.startswith(left_norm + "\\")


class WorkspaceLockStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_WORKSPACE_LOCK_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "agent_kernel" / "locks")
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, lock_id: str) -> Path:
        return resolve_within_root(self.root / f"{lock_id}.json", self.root)

    def save(self, lock: WorkspaceLock) -> WorkspaceLock:
        path = self._path(lock.lock_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(_dump(lock), ensure_ascii=True, indent=2), encoding="utf-8")
        tmp.replace(path)
        return lock

    def get(self, lock_id: str) -> WorkspaceLock | None:
        path = self._path(lock_id)
        if not path.exists():
            return None
        return _parse_lock(json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[WorkspaceLock]:
        rows: list[WorkspaceLock] = []
        for path in self.root.glob("lock_*.json"):
            try:
                rows.append(_parse_lock(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return sorted(rows, key=lambda item: item.created_at, reverse=True)


class WorkspaceLockService:
    def __init__(self, store: WorkspaceLockStore | None = None) -> None:
        self.store = store or WorkspaceLockStore()

    def create(self, request: WorkspaceLockCreateRequest) -> WorkspaceLock:
        now = datetime.now(timezone.utc)
        ttl = max(60, min(int(request.ttl_seconds), 86400))
        lock = WorkspaceLock(
            workspace=str(redact_payload(request.workspace)),
            owner_agent=str(redact_payload(request.owner_agent)),
            owner_task_id=request.owner_task_id,
            bridge_task_id=request.bridge_task_id,
            scope=request.scope,
            locked_paths=[str(redact_payload(item)) for item in request.locked_paths] or [str(redact_payload(request.workspace))],
            reason=str(redact_payload(request.reason)),
            created_at=now.isoformat(),
            expires_at=(now + timedelta(seconds=ttl)).isoformat(),
            metadata_sanitized=redact_payload(request.metadata_sanitized),
        )
        return self.store.save(lock)

    def list(self, *, include_inactive: bool = False) -> list[WorkspaceLock]:
        locks = [self._reconcile_expiration(lock) for lock in self.store.list()]
        if include_inactive:
            return locks
        return [lock for lock in locks if lock.status == "active"]

    def by_workspace(self, workspace: str, *, include_inactive: bool = False) -> list[WorkspaceLock]:
        return [
            lock
            for lock in self.list(include_inactive=include_inactive)
            if _path_overlaps(lock.workspace, workspace)
        ]

    def release(self, lock_id: str, request: WorkspaceLockReleaseRequest) -> WorkspaceLock:
        lock = self._require(lock_id)
        if lock.status in TERMINAL_LOCK_STATUSES:
            return lock
        lock.status = "released"
        lock.released_at = utc_now_iso()
        lock.metadata_sanitized = {
            **lock.metadata_sanitized,
            "release_actor": redact_payload(request.actor_agent),
            "release_reason": redact_payload(request.reason),
        }
        return self.store.save(lock)

    def override(self, lock_id: str, request: WorkspaceLockOverrideRequest) -> WorkspaceLock:
        lock = self._require(lock_id)
        if lock.status in TERMINAL_LOCK_STATUSES:
            return lock
        lock.status = "overridden"
        lock.released_at = utc_now_iso()
        lock.metadata_sanitized = {
            **lock.metadata_sanitized,
            "override_actor": redact_payload(request.actor_agent),
            "override_reason": redact_payload(request.reason),
        }
        return self.store.save(lock)

    def check_write_conflict(self, request: WriteConflictCheckRequest) -> WriteConflictDecision:
        requested_paths = request.target_paths or [request.workspace]
        conflicting: list[WorkspaceLock] = []
        for lock in self.by_workspace(request.workspace):
            if lock.owner_agent == request.actor_agent and (
                not request.owner_task_id or not lock.owner_task_id or lock.owner_task_id == request.owner_task_id
            ):
                continue
            locked_paths = lock.locked_paths or [lock.workspace]
            if any(_path_overlaps(target, locked) for target in requested_paths for locked in locked_paths):
                conflicting.append(lock)
        if conflicting:
            return WriteConflictDecision(
                allowed=False,
                status="blocked",
                reason_code="workspace_locked_by_other_agent",
                message="Workspace possui lock ativo de outro agente ou task.",
                conflicting_locks=conflicting,
            )
        return WriteConflictDecision(allowed=True, status="ok", message="Nenhum conflito de escrita detectado.")

    def ownership_for_bridge(self, *, source_agent: str, target_agent: str, bridge_task_id: str | None = None, owner_task_id: str | None = None, workspace: str | None = None) -> TaskOwnership:
        owner = target_agent or source_agent
        return TaskOwnership(
            source_agent=source_agent,
            target_agent=target_agent,
            owner_agent=owner,
            supervisor_agent=source_agent if source_agent != owner else None,
            can_write=owner in {"aipinho", "codex_agent", "gemini_executor", "codex"},
            can_execute_shell=owner in {"aipinho", "codex_agent", "gemini_executor", "codex"},
            can_approve=source_agent in {"user", "lucio", "codex_agent", "gemini_executor"},
            can_cancel=True,
            can_generate_artifact=True,
            bridge_task_id=bridge_task_id,
            owner_task_id=owner_task_id,
            workspace=workspace,
        )

    def check_hop(self, request: AgentHopCheckRequest) -> AgentHopDecision:
        lineage = [*request.lineage, request.source_agent, request.target_agent]
        hop_count = max(0, len(lineage) - 1)
        if not request.recursion_allowed and len(set(lineage)) < len(lineage):
            return AgentHopDecision(
                allowed=False,
                reason_code="recursion_blocked",
                message="Delegacao recursiva bloqueada pela policy multi-ilhas.",
                hop_count=hop_count,
                lineage=lineage,
            )
        if hop_count > request.max_agent_hops:
            return AgentHopDecision(
                allowed=False,
                reason_code="max_agent_hops_exceeded",
                message="Limite de saltos entre agentes excedido.",
                hop_count=hop_count,
                lineage=lineage,
            )
        return AgentHopDecision(
            allowed=True,
            reason_code="hop_allowed",
            message="Delegacao dentro do limite de hops.",
            hop_count=hop_count,
            lineage=lineage,
        )

    def _require(self, lock_id: str) -> WorkspaceLock:
        lock = self.store.get(lock_id)
        if lock is None:
            raise FileNotFoundError(lock_id)
        return self._reconcile_expiration(lock)

    def _reconcile_expiration(self, lock: WorkspaceLock) -> WorkspaceLock:
        if lock.status != "active" or not lock.expires_at:
            return lock
        try:
            expires = datetime.fromisoformat(lock.expires_at.replace("Z", "+00:00"))
        except ValueError:
            return lock
        if expires > datetime.now(timezone.utc):
            return lock
        updated = lock.model_copy(update={"status": "expired", "released_at": utc_now_iso()})
        return self.store.save(updated)
