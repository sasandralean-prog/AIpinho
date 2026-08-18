from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.interaction.session_grant import SessionGrant, SessionGrantDecision


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SessionGrantService:
    """Temporary, auditable permission grants scoped to a chat session."""

    def __init__(self, store_dir: Path | None = None) -> None:
        self.store_dir = store_dir or PATHS.project_root / "data" / "runtime" / "session_grants"
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def create_pending(
        self,
        *,
        session_id: str,
        workspace_id: str | None,
        workspace_path: str | None,
        actions: Iterable[str],
        paths_scope: Iterable[str] | None = None,
        command_scope: Iterable[str] | None = None,
        scope: str = "single_use",
        source_channel: str = "api",
        reason: str = "",
        max_uses: int | None = 1,
        ttl_minutes: int = 120,
        evidence: list[dict[str, object]] | None = None,
    ) -> SessionGrant:
        now = _utc_now()
        grant = SessionGrant(
            grant_id=f"grant_{uuid4().hex}",
            session_id=session_id,
            workspace_id=workspace_id,
            workspace_path=workspace_path,
            actions=list(dict.fromkeys(str(item) for item in actions if str(item).strip())),
            paths_scope=list(dict.fromkeys(str(item) for item in (paths_scope or []) if str(item).strip())),
            command_scope=list(dict.fromkeys(str(item) for item in (command_scope or []) if str(item).strip())),
            scope=scope if scope in {"single_use", "session", "task", "permanent_preview"} else "single_use",
            source_channel=source_channel,
            status="pending",
            expires_at=now + timedelta(minutes=max(1, int(ttl_minutes))),
            max_uses=max_uses,
            created_at=now,
            updated_at=now,
            reason=reason,
            evidence=evidence or [],
        )
        self.save(grant)
        return grant

    def save(self, grant: SessionGrant) -> SessionGrant:
        payload = grant.model_dump(mode="json") if hasattr(grant, "model_dump") else grant.dict()
        self._path(grant.grant_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return grant

    def get(self, grant_id: str) -> SessionGrant | None:
        path = self._path(grant_id)
        if not path.exists():
            return None
        return SessionGrant(**json.loads(path.read_text(encoding="utf-8")))

    def list_grants(self, *, session_id: str | None = None, status: str | None = None, limit: int = 200) -> list[SessionGrant]:
        grants: list[SessionGrant] = []
        for path in sorted(self.store_dir.glob("grant_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                grant = SessionGrant(**json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            grant = self._expire_if_needed(grant)
            if session_id and grant.session_id != session_id:
                continue
            if status and grant.status != status:
                continue
            grants.append(grant)
            if len(grants) >= limit:
                break
        return grants

    def approve(self, grant_id: str, *, actor: str = "user") -> SessionGrantDecision:
        grant = self._required(grant_id)
        grant = self._expire_if_needed(grant)
        if grant.status != "pending":
            return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code=f"grant_not_pending:{grant.status}", grant=grant)
        grant.status = "approved"
        grant.approved_by = actor
        grant.updated_at = _utc_now()
        self.save(grant)
        return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code="grant_approved", grant=grant)

    def deny(self, grant_id: str, *, actor: str = "user") -> SessionGrantDecision:
        grant = self._required(grant_id)
        grant = self._expire_if_needed(grant)
        if grant.status != "pending":
            return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code=f"grant_not_pending:{grant.status}", grant=grant)
        grant.status = "denied"
        grant.approved_by = actor
        grant.updated_at = _utc_now()
        self.save(grant)
        return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code="grant_denied", grant=grant)

    def is_effective(self, grant_id: str, *, action: str, path: str | None = None, command: str | None = None) -> SessionGrantDecision:
        grant = self._required(grant_id)
        grant = self._expire_if_needed(grant)
        if grant.status != "approved":
            return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code=f"grant_not_approved:{grant.status}", grant=grant)
        if action not in grant.actions:
            return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code="grant_action_out_of_scope", grant=grant)
        if path and grant.paths_scope and not any(self._is_inside(path, scope) for scope in grant.paths_scope):
            return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code="grant_path_out_of_scope", grant=grant)
        if command and grant.command_scope and command not in grant.command_scope:
            return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code="grant_command_out_of_scope", grant=grant)
        if grant.max_uses is not None and grant.used_count >= grant.max_uses:
            grant.status = "expired"
            grant.updated_at = _utc_now()
            self.save(grant)
            return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code="grant_use_limit_reached", grant=grant)
        return SessionGrantDecision(grant_id=grant.grant_id, status=grant.status, reason_code="grant_effective", grant=grant)

    def _required(self, grant_id: str) -> SessionGrant:
        grant = self.get(grant_id)
        if grant is None:
            raise ValueError("grant_not_found")
        return grant

    def _expire_if_needed(self, grant: SessionGrant) -> SessionGrant:
        if grant.status in {"pending", "approved"} and grant.expires_at and grant.expires_at <= _utc_now():
            grant.status = "expired"
            grant.updated_at = _utc_now()
            self.save(grant)
        return grant

    def _path(self, grant_id: str) -> Path:
        if not grant_id.startswith("grant_"):
            raise ValueError("invalid_grant_id")
        return self.store_dir / f"{grant_id}.json"

    def _is_inside(self, path: str, scope: str) -> bool:
        try:
            target = Path(path).resolve(strict=False)
            root = Path(scope).resolve(strict=False)
            return target == root or root in target.parents
        except OSError:
            return False
