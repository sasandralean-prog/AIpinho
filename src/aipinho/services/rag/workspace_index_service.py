from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.workspace_index import WorkspaceIndexRecord, WorkspaceIndexRequest
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.models.capability_router_service import CapabilityRouterService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.session.session_store import utc_now


SECRET_NAME_MARKERS = (".env", "secret", "secrets", "key", "keys", "token", "tokens", "credential", "credentials", ".pem", ".pfx", ".crt")
DEFAULT_IGNORES = {".git", "node_modules", ".venv", "__pycache__", "build", "dist", ".gradle", ".idea"}


class WorkspaceIndexService:
    def __init__(
        self,
        *,
        store_dir: Path | None = None,
        permission_matrix: WorkspacePermissionMatrixService | None = None,
        capability_router: CapabilityRouterService | None = None,
    ) -> None:
        self.store_dir = store_dir or PATHS.project_root / "data" / "runtime" / "workspace_indexes"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.matrix = permission_matrix or WorkspacePermissionMatrixService().load()
        self.capabilities = capability_router or CapabilityRouterService(matrix=self.matrix)

    def preview(self, *, workspace_id: str, source_channel: str = "api", session_id: str | None = None) -> dict[str, Any]:
        entry = self._workspace_entry(workspace_id)
        if entry is None:
            return {"status": "blocked", "reason_code": "workspace_not_registered", "workspace_id": workspace_id}
        request = self._request_from_entry(entry, source_channel=source_channel, session_id=session_id)
        read = self.matrix.decide(path=request.workspace_path, permission="read_file")
        listing = self.matrix.decide(path=request.workspace_path, permission="list_files")
        request.policy_decision = {"read_file": read.model_dump(), "list_files": listing.model_dump()}
        if read.status == "denied" or listing.status == "denied":
            request.status = "blocked"
            record = self._record(request, warnings=["workspace_index_blocked_by_policy"])
            self._save(record)
            return {"status": "blocked", "reason_code": "workspace_index_policy_denied", "index_request": request.model_dump(), "policy_decision": request.policy_decision}
        if read.status == "approval_required" or listing.status == "approval_required":
            approval = self._create_read_approval(request)
            request.approval_id = approval.approval_id
            request.status = "pending_approval"
            record = self._record(request, warnings=["workspace_index_requires_approval"])
            self._save(record)
            return {"status": "pending_approval", "approval_id": approval.approval_id, "index_request": request.model_dump(), "policy_decision": request.policy_decision}
        request.status = "previewed"
        record = self._record(request)
        self._save(record)
        return {"status": "previewed", "index_request": request.model_dump(), "policy_decision": request.policy_decision}

    def start(self, *, workspace_id: str, source_channel: str = "api", session_id: str | None = None) -> dict[str, Any]:
        preview = self.preview(workspace_id=workspace_id, source_channel=source_channel, session_id=session_id)
        if preview.get("status") != "previewed":
            return preview
        request = WorkspaceIndexRequest(**preview["index_request"])
        request.status = "indexing"
        record = self._index(request)
        self._save(record)
        return {"status": record.request.status, "index_request_id": record.request.index_request_id, "record": record.model_dump()}

    def status(self, workspace_id: str) -> dict[str, Any]:
        records = self._records_for_workspace(workspace_id)
        if not records:
            return {"status": "missing", "workspace_id": workspace_id, "indexed": False}
        latest = records[0]
        return {"status": latest.request.status, "workspace_id": workspace_id, "indexed": latest.request.status in {"indexed", "partial"}, "record": latest.model_dump()}

    def search(self, *, workspace_id: str, query: str, limit: int = 10) -> dict[str, Any]:
        entry = self._workspace_entry(workspace_id)
        if entry is None:
            return {"status": "blocked", "reason_code": "workspace_not_registered", "results": []}
        search = self.capabilities.workspace_search(query=query, workspace_path=str(entry.get("root_path")), limit=limit)
        search["workspace_id"] = workspace_id
        return search

    def health(self, workspace_id: str) -> dict[str, Any]:
        status = self.status(workspace_id)
        capabilities = self.capabilities.health()
        return {"status": "ok", "workspace_id": workspace_id, "index": status, "capabilities": capabilities}

    def _index(self, request: WorkspaceIndexRequest) -> WorkspaceIndexRecord:
        root = Path(request.workspace_path).resolve(strict=False)
        indexed: list[dict[str, object]] = []
        skipped: list[dict[str, object]] = []
        total = 0
        if not root.exists() or not root.is_dir():
            request.status = "failed"
            return self._record(request, skipped_files=[{"path": str(root), "reason": "workspace_path_not_found"}])
        candidate_paths = list(root.rglob("*"))
        candidate_paths.extend(path for path in root.rglob(".*") if path not in candidate_paths)
        for file_path in candidate_paths:
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(root).as_posix()
            if any(part in DEFAULT_IGNORES for part in file_path.parts):
                skipped.append({"path": str(file_path), "reason": "ignored_directory"})
                continue
            if request.secret_scan_enabled and self._looks_sensitive(file_path):
                skipped.append({"path": str(file_path), "reason": "secret_or_credential_name"})
                continue
            if not self._matches_patterns(rel, request.include_patterns, request.exclude_patterns):
                skipped.append({"path": str(file_path), "reason": "pattern_excluded"})
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                skipped.append({"path": str(file_path), "reason": "stat_failed"})
                continue
            if size > request.max_file_size:
                skipped.append({"path": str(file_path), "reason": "file_too_large", "size": size})
                continue
            if total + size > request.max_total_size:
                skipped.append({"path": str(file_path), "reason": "total_size_limit_reached"})
                break
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                skipped.append({"path": str(file_path), "reason": "read_failed"})
                continue
            total += size
            indexed.append({"path": str(file_path), "relative_path": rel, "size": size, "snippet": text[:500]})
        route = self.capabilities.route_preview(operation_type="workspace_search", source_channel=request.source_channel)
        request.status = "indexed" if indexed else "partial"
        return self._record(
            request,
            indexed_files=indexed,
            skipped_files=skipped,
            capabilities_used={"keyword_index": True, "embeddings_used": False, "reranker_used": False, "fallback": "keyword_index"},
            warnings=["embeddings_not_executed_keyword_index_used"],
            route_decision=route.get("route_decision", {}),
        )

    def _create_read_approval(self, request: WorkspaceIndexRequest):
        draft_store = TaskDraftStore()
        preview_service = TaskPreviewService(draft_store=draft_store)
        approval_service = ApprovalService(preview_service=preview_service, draft_store=draft_store)
        draft_id = f"workspace_index_{uuid4().hex}"
        draft = TaskContractDraft(
            draft_id=draft_id,
            session_id=request.session_id,
            status="approval_required",
            intent_map={"operation": "workspace_index", "risk": "low", "index_request": request.model_dump()},
            policy_decision={
                "decision_id": f"workspace_index_policy_{uuid4().hex}",
                "status": "needs_approval",
                "allowed_actions": [],
                "denied_actions": [],
                "approval_required_for": ["read_file", "list_files"],
                "granted_capabilities": [],
                "denied_capabilities": [],
            },
            contract_type="readonly_analysis",
            operation_type="workspace_index",
            intent_type="workspace_index_request",
            runtime_profile="governed",
            capabilities_required=["read_file", "list_files", "workspace_search"],
            source_scope=request.source_channel,
            requires_workspace=True,
            workspace=TaskDraftWorkspace(path=request.workspace_path, status="confirmed"),
            requested_actions=["read_file", "list_files"],
            allowed_actions=[],
            denied_actions=[],
            approval_required_for=["read_file", "list_files"],
            safe_to_execute=False,
            safe_to_preview=True,
            clarifying_questions=[],
            warnings=[],
            trace=[{"source": "workspace_index_service", "workspace_id": request.workspace_id}],
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        draft_store.save(draft)
        preview = preview_service.create_preview_from_draft(draft_id)
        if preview is None:
            raise RuntimeError("workspace_index_preview_failed")
        return approval_service.create_approval_for_preview(preview.preview_id, actions=["read_file", "list_files"], reason="Workspace index requires read/list approval")

    def _request_from_entry(self, entry: dict[str, Any], *, source_channel: str, session_id: str | None) -> WorkspaceIndexRequest:
        return WorkspaceIndexRequest(
            index_request_id=f"index_request_{uuid4().hex}",
            workspace_id=str(entry.get("workspace_id")),
            workspace_path=str(entry.get("root_path")),
            source_channel=source_channel,
            session_id=session_id,
        )

    def _record(self, request: WorkspaceIndexRequest, *, indexed_files: list[dict[str, object]] | None = None, skipped_files: list[dict[str, object]] | None = None, capabilities_used: dict[str, object] | None = None, warnings: list[str] | None = None, route_decision: dict[str, object] | None = None) -> WorkspaceIndexRecord:
        now = datetime.now(timezone.utc).isoformat()
        return WorkspaceIndexRecord(request=request, indexed_files=indexed_files or [], skipped_files=skipped_files or [], capabilities_used=capabilities_used or {}, warnings=warnings or [], route_decision=route_decision or {}, created_at=now, updated_at=now)

    def _save(self, record: WorkspaceIndexRecord) -> None:
        path = self.store_dir / f"{record.request.index_request_id}.json"
        path.write_text(json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")

    def _records_for_workspace(self, workspace_id: str) -> list[WorkspaceIndexRecord]:
        records: list[WorkspaceIndexRecord] = []
        for path in sorted(self.store_dir.glob("index_request_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                record = WorkspaceIndexRecord(**json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            if record.request.workspace_id == workspace_id:
                records.append(record)
        return records

    def _workspace_entry(self, workspace_id: str) -> dict[str, Any] | None:
        for item in self.matrix.config.get("workspaces", []) or []:
            if isinstance(item, dict) and str(item.get("workspace_id")) == workspace_id and bool(item.get("enabled", True)):
                return item
        return None

    def _looks_sensitive(self, path: Path) -> bool:
        name = path.name.casefold()
        return any(marker in name for marker in SECRET_NAME_MARKERS)

    def _matches_patterns(self, relative_path: str, includes: list[str], excludes: list[str]) -> bool:
        included = not includes or any(fnmatch.fnmatch(relative_path, pattern) for pattern in includes)
        excluded = any(fnmatch.fnmatch(relative_path, pattern) for pattern in excludes)
        return included and not excluded
