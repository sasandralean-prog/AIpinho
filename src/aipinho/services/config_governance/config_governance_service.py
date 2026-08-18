from __future__ import annotations

import difflib
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.config_governance.config_change import (
    ConfigApplyResult,
    ConfigBackup,
    ConfigChangePreview,
    ConfigChangeRecord,
    ConfigChangeRequest,
    ConfigTarget,
)
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.utils.yaml_loader import load_yaml_file

SECRET_KEY_PATTERN = re.compile(r"(api[_-]?key|token|secret|password|credential|authorization)", re.IGNORECASE)
SECRET_VALUE_PATTERN = re.compile(r"(sk-[A-Za-z0-9_\-]{12,}|AIza[0-9A-Za-z_\-]{12,}|Bearer\s+[A-Za-z0-9_\-.]+)")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": value}


class ConfigGovernanceService:
    TARGETS: dict[ConfigTarget, tuple[str, ...]] = {
        "workspace_registry": ("workspaces", "workspace_registry.yaml"),
        "artifact_policy": ("artifacts", "artifact_write_policy.yaml"),
        "patch_policy": ("policies", "patch_policy.yaml"),
        "governed_tool_execution_policy": ("policies", "governed_tool_execution_policy.yaml"),
        "provider_policy": ("models", "local_provider_policy.yaml"),
        "agent_registry": ("agents", "agent_registry.yaml"),
    }

    def __init__(
        self,
        *,
        config_root: Path | None = None,
        data_root: Path | None = None,
        approvals: ApprovalService | None = None,
    ) -> None:
        self.config_root = config_root or PATHS.config_root
        self.data_root = data_root or PATHS.project_root / "data" / "runtime" / "config_governance"
        self.changes_root = self.data_root / "changes"
        self.backups_root = self.data_root / "backups"
        self.events_path = self.data_root / "events.jsonl"
        self.approvals = approvals or ApprovalService()

    def target_path(self, target: ConfigTarget) -> Path:
        return self.config_root.joinpath(*self.TARGETS[target])

    def create_change(self, request: ConfigChangeRequest) -> ConfigChangeRecord:
        record = ConfigChangeRecord(
            change_id=f"config_change_{uuid4().hex}",
            request=request,
            created_at=_utc_now(),
            updated_at=_utc_now(),
        )
        errors, _candidate = self._candidate_config(record)
        if errors:
            record.status = "failed"
            record.errors = errors
            self._append_record_event(record, "config_change_validation_failed", {"errors": errors})
        else:
            self._append_record_event(record, "config_change_created", {"target": request.target, "operation": request.operation})
        self._save_record(record)
        return record

    def list_changes(self) -> list[ConfigChangeRecord]:
        self.changes_root.mkdir(parents=True, exist_ok=True)
        records: list[ConfigChangeRecord] = []
        for path in sorted(self.changes_root.glob("*.json"), reverse=True):
            try:
                records.append(ConfigChangeRecord(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return records

    def get_change(self, change_id: str) -> ConfigChangeRecord | None:
        path = self._record_path(change_id)
        if not path.exists():
            return None
        return ConfigChangeRecord(**json.loads(path.read_text(encoding="utf-8")))

    def preview_change(self, change_id: str) -> ConfigChangePreview:
        record = self._require_change(change_id)
        errors, candidate = self._candidate_config(record)
        current_text = self._target_text(record.request.target)
        candidate_text = yaml.safe_dump(candidate or {}, sort_keys=False, allow_unicode=True)
        diff = "\n".join(
            difflib.unified_diff(
                current_text.splitlines(),
                candidate_text.splitlines(),
                fromfile=f"current/{record.request.target}",
                tofile=f"candidate/{record.request.target}",
                lineterm="",
            )
        )
        requires_approval = self._requires_approval(record.request)
        approval_id = record.approval_id
        validation_status = "failed" if errors else "ok"
        preview = ConfigChangePreview(
            change_id=record.change_id,
            target=record.request.target,
            status="approval_required" if requires_approval else "previewed",
            requires_approval=requires_approval,
            sanitized_diff=self._redact(diff),
            validation_status=validation_status,
            validation_errors=errors,
            approval_id=approval_id,
            changed_paths=[str(self.target_path(record.request.target))],
        )
        record.preview = preview
        record.status = "failed" if errors else preview.status
        record.updated_at = _utc_now()
        self._append_record_event(record, "config_change_preview_created", {"requires_approval": requires_approval, "validation_status": validation_status})
        if errors:
            self._append_record_event(record, "config_change_validation_failed", {"errors": errors})
        elif requires_approval and approval_id is None:
            approval = self._create_approval(record)
            record.approval_id = approval.approval_id
            preview.approval_id = approval.approval_id
            self._append_record_event(record, "config_change_approval_required", {"approval_id": approval.approval_id})
        self._save_record(record)
        return preview

    def approve_change(self, change_id: str, actor: Actor | None = None) -> ConfigChangeRecord:
        record = self._require_change(change_id)
        if record.approval_id:
            self.approvals.approve(record.approval_id, actor=actor or Actor(type="user", id="local_user"), reason="config_change_approved")
        record.status = "approved"
        record.updated_at = _utc_now()
        self._append_record_event(record, "config_change_approved", {"approval_id": record.approval_id})
        self._save_record(record)
        return record

    def apply_change(self, change_id: str) -> ConfigApplyResult:
        record = self._require_change(change_id)
        if record.status != "approved":
            raise ValueError("config_change_apply_requires_approved_status")
        errors, candidate = self._candidate_config(record)
        if errors or candidate is None:
            raise ValueError(";".join(errors or ["candidate_config_missing"]))
        target = self.target_path(record.request.target)
        self._append_record_event(record, "config_change_apply_started", {"path": str(target)})
        backup = self._backup(record, target)
        result = ConfigApplyResult(
            change_id=record.change_id,
            target=record.request.target,
            status="failed",
            backup_id=backup.backup_id,
            reload_status="not_started",
            self_check_status="not_started",
        )
        try:
            self._atomic_write_yaml(target, candidate)
            self._append_record_event(record, "config_file_written", {"path": str(target), "backup_id": backup.backup_id})
            self._append_record_event(record, "config_policy_reload_started", {"target": record.request.target})
            self.reload()
            result.reload_status = "ok"
            self._append_record_event(record, "config_policy_reload_completed", {"target": record.request.target})
            self._append_record_event(record, "config_self_check_started", {"target": record.request.target})
            health = self.health()
            if health["status"] != "ok":
                raise ValueError("config_self_check_failed")
            result.self_check_status = "ok"
            result.status = "applied"
            record.status = "applied"
            self._append_record_event(record, "config_self_check_completed", {"status": "ok"})
            self._append_record_event(record, "config_change_applied", {"backup_id": backup.backup_id})
        except Exception as exc:
            result.errors.append(str(exc))
            self._restore_backup(backup)
            record.status = "failed"
            record.errors.append(str(exc))
            self._append_record_event(record, "config_change_failed", {"error": self._redact(str(exc)), "backup_id": backup.backup_id})
        record.apply_result = result
        record.updated_at = _utc_now()
        self._save_record(record)
        return result

    def cancel_change(self, change_id: str) -> ConfigChangeRecord:
        record = self._require_change(change_id)
        record.status = "cancelled"
        record.updated_at = _utc_now()
        self._append_record_event(record, "config_change_cancelled", {})
        self._save_record(record)
        return record

    def list_backups(self) -> list[ConfigBackup]:
        self.backups_root.mkdir(parents=True, exist_ok=True)
        backups: list[ConfigBackup] = []
        for path in sorted(self.backups_root.glob("*.json"), reverse=True):
            try:
                backups.append(ConfigBackup(**json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return backups

    def get_backup(self, backup_id: str) -> ConfigBackup | None:
        path = self.backups_root / f"{backup_id}.json"
        if not path.exists():
            return None
        return ConfigBackup(**json.loads(path.read_text(encoding="utf-8")))

    def rollback(self, backup_id: str) -> ConfigApplyResult:
        backup = self.get_backup(backup_id)
        if backup is None:
            raise ValueError("backup_not_found")
        self._append_event("config_rollback_started", {"backup_id": backup_id, "target": backup.target})
        self._restore_backup(backup)
        self.reload()
        result = ConfigApplyResult(
            change_id=backup.change_id or backup.backup_id,
            target=backup.target,
            status="applied",
            backup_id=backup.backup_id,
            reload_status="ok",
            self_check_status="ok",
        )
        self._append_event("config_rollback_completed", {"backup_id": backup_id, "target": backup.target})
        return result

    def reload(self) -> dict[str, object]:
        for target in self.TARGETS:
            path = self.target_path(target)
            if path.exists() and path.stat().st_size > 0:
                load_yaml_file(path, critical=True, root=path.parent)
        return {"status": "ok", "targets": list(self.TARGETS)}

    def health(self) -> dict[str, object]:
        target_status: dict[str, object] = {}
        errors: list[str] = []
        for target in self.TARGETS:
            path = self.target_path(target)
            try:
                if path.exists() and path.stat().st_size > 0:
                    load_yaml_file(path, critical=True, root=path.parent)
                target_status[target] = {"status": "ok", "path": str(path), "exists": path.exists()}
            except Exception as exc:
                target_status[target] = {"status": "degraded", "path": str(path), "error": str(exc)}
                errors.append(f"{target}:{exc}")
        return {"status": "ok" if not errors else "degraded", "targets": target_status, "errors": errors}

    def effective_policy(self) -> dict[str, object]:
        matrix = WorkspacePermissionMatrixService(self.target_path("workspace_registry")).load()
        return {
            "status": "ok",
            "workspace_permission_matrix": matrix.effective_policy(),
            "config_targets": {target: str(self.target_path(target)) for target in self.TARGETS},
            "governance": {"approval_required_for_policy_change": True, "backup_before_apply": True, "secrets_redacted": True},
        }

    def _candidate_config(self, record: ConfigChangeRecord) -> tuple[list[str], dict[str, Any] | None]:
        try:
            current = self._target_config(record.request.target)
            payload = dict(record.request.payload)
            if record.request.target == "workspace_registry":
                candidate = self._workspace_candidate(current, record.request.operation, payload)
                errors = WorkspacePermissionMatrixService(self.target_path("workspace_registry")).validate_registry(candidate)
                return errors, candidate
            if record.request.operation == "replace":
                candidate = payload
            elif record.request.operation == "merge":
                candidate = self._deep_merge(current, payload)
            else:
                return [f"operation_not_supported_for_target:{record.request.operation}"], None
            return self._validate_mapping(candidate), candidate
        except Exception as exc:
            return [str(exc)], None

    def _workspace_candidate(self, current: dict[str, Any], operation: str, payload: dict[str, object]) -> dict[str, Any]:
        service = WorkspacePermissionMatrixService(self.target_path("workspace_registry")).load()
        service._config = current
        if operation in {"add_workspace", "update_workspace"}:
            workspace = payload.get("workspace", payload)
            entry = WorkspacePermissionMatrixService(self.target_path("workspace_registry")).workspace_id_for_path
            _ = entry
            from aipinho.schemas.config_governance.workspace_permission import WorkspaceEntry

            return service.add_or_update_workspace(WorkspaceEntry(**workspace))  # type: ignore[arg-type]
        if operation == "set_permissions":
            workspace_id = str(payload.get("workspace_id") or "")
            permissions = payload.get("permissions", {})
            if not isinstance(permissions, dict):
                raise ValueError("permissions_must_be_mapping")
            return service.set_permissions(workspace_id, {str(key): str(value) for key, value in permissions.items()})
        if operation == "merge":
            return self._deep_merge(current, payload)
        if operation == "replace":
            return payload
        raise ValueError("unsupported_workspace_registry_operation")

    def _target_config(self, target: ConfigTarget) -> dict[str, Any]:
        path = self.target_path(target)
        if not path.exists() or path.stat().st_size == 0:
            return {}
        return load_yaml_file(path, critical=True, root=path.parent)

    def _target_text(self, target: ConfigTarget) -> str:
        path = self.target_path(target)
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _requires_approval(self, request: ConfigChangeRequest) -> bool:
        if request.requires_approval is not None:
            return request.requires_approval
        return request.target in set(self.TARGETS)

    def _create_approval(self, record: ConfigChangeRecord) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=f"config_preview_{record.change_id}",
            draft_id=f"config_draft_{record.change_id}",
            agent_id="aipinho",
            workspace_path=str(self.target_path(record.request.target).parent),
            operation_type="config_change",
            target_paths=[str(self.target_path(record.request.target))],
            preview={"available": True, "summary": f"Config change {record.change_id}", "content_preview_ref": record.change_id},
            policy_refs=["config_governance_policy"],
            allowed_by_policy=True,
            forbidden_operations=[],
            actions_requested=["modify_file"],
            approval_scope="single_action",
            reason=record.request.reason or "config_change_requires_approval",
            risk_level="medium",
            policy_snapshot=ApprovalPolicySnapshot(
                policy_decision_id=f"policy_config_{record.change_id}",
                policy_status="needs_approval",
                allowed_actions=["modify_file"],
                denied_actions=[],
                approval_required_for=["modify_file"],
                workspace_status="system_mutable",
                risk_level="medium",
                trace_hash=hashlib.sha256(record.change_id.encode("utf-8")).hexdigest(),
            ),
            expires_at=(now + timedelta(hours=2)).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=record.request.actor,
            trace=[{"stage": "config_governance", "decision": "pending", "reason": "approval_required_before_config_apply"}],
            execution_status="not_executed",
        )
        self.approvals.store.save(approval)
        self.approvals.append_event(approval.approval_id, "approval_created", "ApprovalRequest criado para mudanca governada de config.", {"change_id": record.change_id})
        return approval

    def _backup(self, record: ConfigChangeRecord, target: Path) -> ConfigBackup:
        self.backups_root.mkdir(parents=True, exist_ok=True)
        backup_id = f"config_backup_{uuid4().hex}"
        backup_file = self.backups_root / f"{backup_id}_{target.name}"
        if target.exists():
            backup_file.write_bytes(target.read_bytes())
            digest = hashlib.sha256(backup_file.read_bytes()).hexdigest()
        else:
            backup_file.write_text("", encoding="utf-8")
            digest = hashlib.sha256(b"").hexdigest()
        backup = ConfigBackup(
            backup_id=backup_id,
            change_id=record.change_id,
            target=record.request.target,
            path=str(target),
            backup_path=str(backup_file),
            created_at=_utc_now(),
            sha256=digest,
        )
        (self.backups_root / f"{backup_id}.json").write_text(json.dumps(backup.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        self._append_record_event(record, "config_backup_created", {"backup_id": backup_id, "path": str(target)})
        return backup

    def _restore_backup(self, backup: ConfigBackup) -> None:
        source = Path(backup.backup_path)
        target = Path(backup.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())

    def _atomic_write_yaml(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
        load_yaml_file(tmp, critical=True, root=tmp.parent)
        tmp.replace(path)

    def _validate_mapping(self, payload: dict[str, Any]) -> list[str]:
        return [] if isinstance(payload, dict) else ["config_must_be_mapping"]

    def _deep_merge(self, base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _redact(self, text: str) -> str:
        redacted_lines: list[str] = []
        for line in text.splitlines():
            key = line.split(":", 1)[0] if ":" in line else ""
            if SECRET_KEY_PATTERN.search(key):
                redacted_lines.append(f"{key}: [REDACTED]")
            else:
                redacted_lines.append(SECRET_VALUE_PATTERN.sub("[REDACTED]", line))
        return "\n".join(redacted_lines)

    def _append_record_event(self, record: ConfigChangeRecord, event_type: str, data: dict[str, object]) -> None:
        event = self._append_event(event_type, {"change_id": record.change_id, **data})
        record.events.append(event)

    def _append_event(self, event_type: str, data: dict[str, object]) -> dict[str, object]:
        event = {"event_id": f"config_event_{uuid4().hex}", "event_type": event_type, "created_at": _utc_now(), "data": self._sanitize_data(data)}
        self.data_root.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def _sanitize_data(self, data: dict[str, object]) -> dict[str, object]:
        return self._sanitize_value(data)  # type: ignore[return-value]

    def _sanitize_value(self, value: object) -> object:
        if isinstance(value, dict):
            cleaned: dict[str, object] = {}
            for key, item in value.items():
                text_key = str(key)
                if SECRET_KEY_PATTERN.search(text_key):
                    cleaned[text_key] = "[REDACTED]"
                else:
                    cleaned[text_key] = self._sanitize_value(item)
            return cleaned
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, str):
            return SECRET_VALUE_PATTERN.sub("[REDACTED]", value)
        return value

    def _record_path(self, change_id: str) -> Path:
        return self.changes_root / f"{change_id}.json"

    def _save_record(self, record: ConfigChangeRecord) -> None:
        self.changes_root.mkdir(parents=True, exist_ok=True)
        self._record_path(record.change_id).write_text(json.dumps(record.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _require_change(self, change_id: str) -> ConfigChangeRecord:
        record = self.get_change(change_id)
        if record is None:
            raise ValueError("config_change_not_found")
        return record
