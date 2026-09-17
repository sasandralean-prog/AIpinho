from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from aipinho.core.paths import PATHS
from aipinho.schemas.interaction.session_grant import SessionGrant, SessionGrantDecision
from aipinho.schemas.runtime.mission_contract import MissionContract


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthorityGrantService:
    """Canonical temporary authority-grant store and evaluator.

    Existing chat SessionGrant flows use this same persistence and decision
    model. Mission grants satisfy human-consent facets only; resource/global
    policy remains independently authoritative.
    """

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
        mission_id: str | None = None,
        source_message_id: str | None = None,
        source_prompt_sha256: str | None = None,
        authority_sha256: str | None = None,
        local_resource_ids: Iterable[str] | None = None,
        remote_resource_ids: Iterable[str] | None = None,
        repository_scope: Iterable[str] | None = None,
        branch_scope: dict[str, list[str]] | None = None,
        grant_id: str | None = None,
    ) -> SessionGrant:
        now = _utc_now()
        resolved_scope = scope if scope in {"single_use", "session", "task", "mission", "permanent_preview"} else "single_use"
        grant = SessionGrant(
            grant_id=grant_id or self._new_grant_id(),
            session_id=session_id,
            mission_id=mission_id,
            source_message_id=source_message_id,
            source_prompt_sha256=source_prompt_sha256,
            authority_sha256=authority_sha256,
            workspace_id=workspace_id,
            workspace_path=workspace_path,
            actions=self._unique(actions),
            paths_scope=self._unique(paths_scope or []),
            command_scope=self._unique(command_scope or []),
            local_resource_ids=self._unique(local_resource_ids or []),
            remote_resource_ids=self._unique(remote_resource_ids or []),
            repository_scope=self._unique(repository_scope or []),
            branch_scope=self._normalized_branch_scope(branch_scope or {}),
            scope=resolved_scope,
            source_channel=source_channel,
            status="pending",
            expires_at=now + timedelta(minutes=max(1, int(ttl_minutes))),
            max_uses=max_uses,
            created_at=now,
            updated_at=now,
            reason=reason,
            evidence=evidence or [],
        )
        return self.save(grant)

    def ensure_mission_grant(self, contract: MissionContract) -> SessionGrant | None:
        authorized = list(contract.authority.authorized_capabilities)
        evidence = list(contract.authority.explicit_evidence)
        if not authorized:
            return None
        if not evidence:
            raise ValueError("mission_authority_evidence_required")
        grant_id = self._mission_grant_id(contract)
        existing = self.get(grant_id)
        if existing is not None:
            self._validate_existing_mission_grant(existing, contract)
            return self._expire_if_needed(existing)

        local_resources = [
            item for item in contract.local_resources
            if set(item.permissions).intersection(authorized)
        ]
        remote_resources = [
            item for item in contract.remote_resources
            if set(item.permissions).intersection(authorized)
        ]
        repositories = [
            item.normalized_identity
            for item in remote_resources
            if item.normalized_identity
        ]
        branches = {
            str(item.normalized_identity): list(item.allowed_branches)
            for item in remote_resources
            if item.normalized_identity
        }
        now = _utc_now()
        grant = SessionGrant(
            grant_id=grant_id,
            session_id=contract.session_id or "mission",
            mission_id=contract.mission_id,
            source_message_id=contract.source_message_id,
            source_prompt_sha256=contract.source_prompt_sha256,
            authority_sha256=contract.authority_sha256,
            workspace_id=None,
            workspace_path=None,
            actions=self._unique(authorized),
            paths_scope=self._unique(
                item.locator for item in local_resources if item.locator
            ),
            local_resource_ids=self._unique(item.resource_id for item in local_resources),
            remote_resource_ids=self._unique(item.resource_id for item in remote_resources),
            repository_scope=self._unique(repositories),
            branch_scope=self._normalized_branch_scope(branches),
            scope="mission",
            source_channel="mission_contract",
            approved_by=f"source_message:{contract.source_message_id}",
            status="approved",
            expires_at=now + timedelta(hours=24),
            max_uses=None,
            used_count=0,
            created_at=now,
            updated_at=now,
            reason="explicit_human_authorization_in_source_prompt",
            evidence=[item.model_dump(mode="json") for item in evidence],
        )
        return self.save(grant)

    def decision_for_contract(
        self,
        contract: MissionContract,
        *,
        action: str,
        path: str | None = None,
        command: str | None = None,
        resource_id: str | None = None,
        repository_identity: str | None = None,
        branch: str | None = None,
        consume: bool = False,
    ) -> SessionGrantDecision | None:
        grant = self.ensure_mission_grant(contract)
        if grant is None:
            return None
        evaluator = self.consume if consume else self.is_effective
        return evaluator(
            grant.grant_id,
            action=action,
            path=path,
            command=command,
            mission_id=contract.mission_id,
            source_message_id=contract.source_message_id,
            source_prompt_sha256=contract.source_prompt_sha256,
            resource_id=resource_id,
            repository_identity=repository_identity,
            branch=branch,
        )

    def save(self, grant: SessionGrant) -> SessionGrant:
        payload = grant.model_dump(mode="json")
        self._path(grant.grant_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return grant

    def get(self, grant_id: str) -> SessionGrant | None:
        path = self._path(grant_id)
        if not path.exists():
            return None
        return SessionGrant.model_validate_json(path.read_text(encoding="utf-8"))

    def list_grants(
        self,
        *,
        session_id: str | None = None,
        mission_id: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[SessionGrant]:
        grants: list[SessionGrant] = []
        paths = sorted(
            self.store_dir.glob("grant_*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for path in paths:
            try:
                grant = SessionGrant.model_validate_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            grant = self._expire_if_needed(grant)
            if session_id and grant.session_id != session_id:
                continue
            if mission_id and grant.mission_id != mission_id:
                continue
            if status and grant.status != status:
                continue
            grants.append(grant)
            if len(grants) >= limit:
                break
        return grants

    def approve(self, grant_id: str, *, actor: str = "user") -> SessionGrantDecision:
        grant = self._expire_if_needed(self._required(grant_id))
        if grant.status != "pending":
            return self._decision(grant, f"grant_not_pending:{grant.status}")
        grant.status = "approved"
        grant.approved_by = actor
        grant.updated_at = _utc_now()
        self.save(grant)
        return self._decision(grant, "grant_approved")

    def deny(self, grant_id: str, *, actor: str = "user") -> SessionGrantDecision:
        return self._terminalize_pending(grant_id, status="denied", actor=actor)

    def revoke(self, grant_id: str, *, actor: str = "user") -> SessionGrantDecision:
        grant = self._required(grant_id)
        if grant.status in {"revoked", "expired"}:
            return self._decision(grant, f"grant_not_revocable:{grant.status}")
        grant.status = "revoked"
        grant.approved_by = actor
        grant.updated_at = _utc_now()
        self.save(grant)
        return self._decision(grant, "grant_revoked")

    def is_effective(
        self,
        grant_id: str,
        *,
        action: str,
        path: str | None = None,
        command: str | None = None,
        mission_id: str | None = None,
        source_message_id: str | None = None,
        source_prompt_sha256: str | None = None,
        resource_id: str | None = None,
        repository_identity: str | None = None,
        branch: str | None = None,
    ) -> SessionGrantDecision:
        grant = self._expire_if_needed(self._required(grant_id))
        if grant.status != "approved":
            return self._decision(grant, f"grant_not_approved:{grant.status}")
        reason = self._scope_reason(
            grant,
            action=action,
            path=path,
            command=command,
            mission_id=mission_id,
            source_message_id=source_message_id,
            source_prompt_sha256=source_prompt_sha256,
            resource_id=resource_id,
            repository_identity=repository_identity,
            branch=branch,
        )
        if reason:
            return self._decision(grant, reason)
        if grant.max_uses is not None and grant.used_count >= grant.max_uses:
            grant.status = "expired"
            grant.updated_at = _utc_now()
            self.save(grant)
            return self._decision(grant, "grant_use_limit_reached")
        return self._decision(grant, "grant_effective")

    def consume(self, grant_id: str, **scope) -> SessionGrantDecision:
        decision = self.is_effective(grant_id, **scope)
        if decision.reason_code != "grant_effective":
            return decision
        grant = decision.grant
        grant.used_count += 1
        grant.updated_at = _utc_now()
        if grant.max_uses is not None and grant.used_count >= grant.max_uses:
            grant.status = "expired"
        self.save(grant)
        return self._decision(grant, "grant_consumed")

    def _scope_reason(
        self,
        grant: SessionGrant,
        *,
        action: str,
        path: str | None,
        command: str | None,
        mission_id: str | None,
        source_message_id: str | None,
        source_prompt_sha256: str | None,
        resource_id: str | None,
        repository_identity: str | None,
        branch: str | None,
    ) -> str | None:
        if action not in grant.actions:
            return "grant_action_out_of_scope"
        if mission_id and grant.mission_id and mission_id != grant.mission_id:
            return "grant_mission_out_of_scope"
        if source_message_id and grant.source_message_id and source_message_id != grant.source_message_id:
            return "grant_source_message_mismatch"
        if source_prompt_sha256 and grant.source_prompt_sha256 and source_prompt_sha256 != grant.source_prompt_sha256:
            return "grant_source_prompt_mismatch"
        if path and grant.paths_scope and not any(self._is_inside(path, scope) for scope in grant.paths_scope):
            return "grant_path_out_of_scope"
        if command and grant.command_scope and command not in grant.command_scope:
            return "grant_command_out_of_scope"
        if resource_id and not self._resource_allowed(grant, resource_id):
            return "grant_resource_out_of_scope"
        if repository_identity:
            if grant.repository_scope and repository_identity not in grant.repository_scope:
                return "grant_repository_out_of_scope"
            if branch and grant.branch_scope:
                allowed = set(grant.branch_scope.get(repository_identity, []))
                if not allowed or branch not in allowed:
                    return "grant_branch_out_of_scope"
        return None

    def _resource_allowed(self, grant: SessionGrant, resource_id: str) -> bool:
        scoped = set(grant.local_resource_ids) | set(grant.remote_resource_ids)
        return not scoped or resource_id in scoped

    def _terminalize_pending(
        self,
        grant_id: str,
        *,
        status: str,
        actor: str,
    ) -> SessionGrantDecision:
        grant = self._expire_if_needed(self._required(grant_id))
        if grant.status != "pending":
            return self._decision(grant, f"grant_not_pending:{grant.status}")
        grant.status = status
        grant.approved_by = actor
        grant.updated_at = _utc_now()
        self.save(grant)
        return self._decision(grant, f"grant_{status}")

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

    def _decision(self, grant: SessionGrant, reason_code: str) -> SessionGrantDecision:
        return SessionGrantDecision(
            grant_id=grant.grant_id,
            status=grant.status,
            reason_code=reason_code,
            grant=grant,
        )

    def _path(self, grant_id: str) -> Path:
        if not str(grant_id).startswith("grant_"):
            raise ValueError("invalid_grant_id")
        return self.store_dir / f"{grant_id}.json"

    def _new_grant_id(self) -> str:
        from uuid import uuid4
        return f"grant_{uuid4().hex}"

    def _mission_grant_id(self, contract: MissionContract) -> str:
        seed = f"{contract.mission_id}:{contract.authority_sha256}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
        return f"grant_mission_{digest}"

    def _validate_existing_mission_grant(
        self,
        grant: SessionGrant,
        contract: MissionContract,
    ) -> None:
        expected = {
            "mission_id": contract.mission_id,
            "source_message_id": contract.source_message_id,
            "source_prompt_sha256": contract.source_prompt_sha256,
            "authority_sha256": contract.authority_sha256,
        }
        actual = {key: getattr(grant, key) for key in expected}
        if actual != expected:
            raise ValueError("mission_grant_binding_mismatch")
        if set(grant.actions) != set(contract.authority.authorized_capabilities):
            raise ValueError("mission_grant_capability_mismatch")

    def _normalized_branch_scope(self, value: dict[str, list[str]]) -> dict[str, list[str]]:
        return {
            str(key): self._unique(branches)
            for key, branches in sorted(value.items())
            if str(key).strip()
        }

    def _unique(self, values: Iterable[str]) -> list[str]:
        return sorted({str(item).strip() for item in values if str(item).strip()})

    def _is_inside(self, path: str, scope: str) -> bool:
        try:
            target = Path(path).resolve(strict=False)
            root = Path(scope).resolve(strict=False)
            return target == root or root in target.parents
        except OSError:
            return False
