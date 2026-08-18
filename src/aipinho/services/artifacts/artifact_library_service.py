from __future__ import annotations

import base64
import io
import json
import os
import zipfile
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest, ToolArtifactRecord
from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactRecord
from aipinho.schemas.artifacts.artifact_library import (
    ArtifactBundleRequest,
    ArtifactBundleResult,
    ArtifactCleanupPreview,
    ArtifactContextUseRequest,
    ArtifactContextUseResult,
    ArtifactPreviewRequest,
    ArtifactPreviewResult,
    ArtifactQuery,
    ArtifactRecordV2,
    ArtifactSearchResult,
)
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.artifact_secret_scanner import ArtifactSecretScanner
from aipinho.services.events.event_core import redact_payload
from aipinho.utils.yaml_loader import load_yaml_file


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists() or path.stat().st_size == 0:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


class ArtifactLibraryService:
    def __init__(
        self,
        *,
        index_path: Path | None = None,
        tool_store: AgentToolInvocationStore | None = None,
        legacy_registry: ArtifactRegistryRepository | None = None,
        gateway: AgentToolGatewayService | None = None,
    ) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_library_policy.yaml", critical=False, root=PATHS.config_root)
        env_root = os.getenv("AIPINHO_ARTIFACT_LIBRARY_ROOT")
        configured_index = (self.policy.get("storage") or {}).get("index_path") if isinstance(self.policy, dict) else None
        default_index = Path(env_root) / "ARTIFACT_INDEX.json" if env_root else Path(str(configured_index)) if configured_index else PATHS.project_root / "artifacts" / "ARTIFACT_INDEX.json"
        self.index_path = index_path or default_index
        self.tool_store = tool_store or AgentToolInvocationStore()
        self.legacy_registry = legacy_registry or ArtifactRegistryRepository()
        self.gateway = gateway or AgentToolGatewayService()
        self.secret_scanner = ArtifactSecretScanner()

    def health(self) -> dict[str, object]:
        records = self.reindex(auto_repair=True)
        by_status: dict[str, int] = {}
        for record in records:
            by_status[record.status] = by_status.get(record.status, 0) + 1
        return {
            "status": "ok",
            "artifact_library_enabled": bool(self.policy.get("artifact_library_enabled", True)) if isinstance(self.policy, dict) else True,
            "index_path": str(self.index_path),
            "total": len(records),
            "by_status": by_status,
            "token_in_url": False,
        }

    def reindex(self, *, auto_repair: bool = True) -> list[ArtifactRecordV2]:
        records: dict[str, ArtifactRecordV2] = {}
        for artifact in self.legacy_registry.list():
            normalized = self._from_legacy_artifact(artifact)
            records[normalized.artifact_id] = normalized
        for artifact in self.tool_store.list_artifacts(include_all=True):
            normalized = self._from_tool_artifact(artifact)
            records[normalized.artifact_id] = normalized
        indexed = sorted(records.values(), key=lambda item: item.created_at, reverse=True)
        _json_write(self.index_path, {"updated_at": utc_now_iso(), "artifacts": [item.model_dump() for item in indexed]})
        return indexed

    def list_indexed(self) -> list[ArtifactRecordV2]:
        payload = _json_read(self.index_path, {"artifacts": []})
        return [ArtifactRecordV2(**item) for item in payload.get("artifacts", [])]

    def query(self, query: ArtifactQuery) -> ArtifactSearchResult:
        records = self.reindex(auto_repair=True)
        filtered = [record for record in records if self._matches(record, query)]
        reverse = query.sort_direction != "asc"
        if query.sort_by in {"created_at", "updated_at", "filename", "status", "origin_type"}:
            filtered = sorted(filtered, key=lambda item: str(getattr(item, query.sort_by, "")), reverse=reverse)
        total = len(filtered)
        items = filtered[query.offset : query.offset + query.limit]
        next_offset = query.offset + query.limit if query.offset + query.limit < total else None
        return ArtifactSearchResult(total=total, items=items, next_offset=next_offset)

    def get(self, artifact_id: str) -> ArtifactRecordV2:
        record = next((item for item in self.reindex(auto_repair=True) if item.artifact_id == artifact_id), None)
        if record is None:
            raise FileNotFoundError(artifact_id)
        return record

    def preview(self, request: ArtifactPreviewRequest) -> ArtifactPreviewResult:
        record = self.get(request.artifact_id)
        if record.status != "ready":
            return ArtifactPreviewResult(
                artifact_id=record.artifact_id,
                status=record.status,
                preview_mode=request.preview_mode,
                preview_available=False,
                errors=[record.error_reason or f"artifact_not_ready:{record.status}"],
                evidence_refs=record.evidence_refs,
            )
        path = self._content_path(record)
        if path is None or not path.exists():
            return ArtifactPreviewResult(
                artifact_id=record.artifact_id,
                status="failed",
                preview_mode=request.preview_mode,
                preview_available=False,
                errors=["artifact_file_missing"],
                evidence_refs=record.evidence_refs,
            )
        if request.preview_mode == "metadata_only":
            return ArtifactPreviewResult(artifact_id=record.artifact_id, status=record.status, preview_mode=request.preview_mode, preview_available=True, manifest=record.model_dump(), evidence_refs=record.evidence_refs)
        if record.artifact_type == "zip" or request.preview_mode == "zip_listing":
            return self._zip_preview(record, path, request)
        if record.artifact_type == "image" or request.preview_mode == "image":
            return ArtifactPreviewResult(
                artifact_id=record.artifact_id,
                status=record.status,
                preview_mode=request.preview_mode,
                preview_available=True,
                image_info={"filename": record.filename, "size_bytes": path.stat().st_size, "content_type": record.content_type},
                warnings=["image_preview_metadata_only"],
                evidence_refs=record.evidence_refs,
            )
        if record.artifact_type in {"text", "markdown_report", "json_report", "manifest", "log_sanitized"}:
            return self._text_preview(record, path, request)
        return ArtifactPreviewResult(
            artifact_id=record.artifact_id,
            status=record.status,
            preview_mode=request.preview_mode,
            preview_available=True,
            manifest=record.model_dump(),
            warnings=["binary_preview_metadata_only"],
            evidence_refs=record.evidence_refs,
        )

    def use_as_context(self, request: ArtifactContextUseRequest) -> ArtifactContextUseResult:
        record = self.get(request.artifact_id)
        if record.status != "ready":
            return ArtifactContextUseResult(artifact_id=record.artifact_id, status="blocked", use_mode="deny", reason_code="artifact_not_ready", evidence_refs=record.evidence_refs)
        if not record.context_usable:
            return ArtifactContextUseResult(artifact_id=record.artifact_id, status="blocked", use_mode="deny", reason_code="artifact_context_denied_type", evidence_refs=record.evidence_refs)
        preview = self.preview(ArtifactPreviewRequest(artifact_id=record.artifact_id, preview_mode="text", max_bytes=request.max_context_bytes, sanitize=request.sanitization_required))
        return ArtifactContextUseResult(
            artifact_id=record.artifact_id,
            status="allowed" if preview.preview_available else "blocked",
            use_mode=request.use_mode,
            context_preview=preview.content_preview,
            reason_code="artifact_context_use_allowed" if preview.preview_available else "artifact_context_preview_unavailable",
            warnings=preview.warnings,
            evidence_refs=record.evidence_refs,
        )

    def create_bundle(self, request: ArtifactBundleRequest) -> ArtifactBundleResult:
        records = [self.get(artifact_id) for artifact_id in request.artifact_ids]
        blocked = [record.artifact_id for record in records if record.status != "ready"]
        if blocked:
            raise PermissionError(f"artifact_bundle_blocked_status:{','.join(blocked)}")
        filename = self._safe_filename(request.bundle_name, default="artifacts_bundle.zip")
        if not filename.endswith(".zip"):
            filename += ".zip"
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            manifest = {"bundle_request_id": request.bundle_request_id, "artifact_ids": request.artifact_ids, "created_at": utc_now_iso()}
            bundle.writestr("BUNDLE_MANIFEST.json", json.dumps(manifest, ensure_ascii=True, indent=2))
            for record in records:
                path = self._content_path(record)
                if path is None or not path.exists():
                    raise FileNotFoundError(record.artifact_id)
                bundle.write(path, arcname=self._safe_filename(record.filename, default=record.artifact_id))
        artifact = self.gateway.upload_artifact(
            agent_id="system",
            session_id=request.session_id or "artifact_library",
            request=ArtifactUploadRequest(
                filename=filename,
                content_type="application/zip",
                content=base64.b64encode(memory.getvalue()).decode("ascii"),
                encoding="base64",
                origin="artifact_library_bundle",
                metadata_sanitized={"included_artifacts": request.artifact_ids, "origin_type": "system", "evidence_refs": [f"artifact:{item}" for item in request.artifact_ids]},
            ),
        )
        self.reindex(auto_repair=True)
        return ArtifactBundleResult(bundle_artifact=self.get(artifact.artifact_id), included_artifacts=request.artifact_ids)

    def cleanup_preview(self, *, status: str | None = None) -> ArtifactCleanupPreview:
        candidates: list[ArtifactRecordV2] = []
        preserved: list[str] = []
        blocked: list[str] = []
        for record in self.reindex(auto_repair=True):
            if record.status in {"failed", "expired", "deleted"} and not record.evidence_refs:
                if status and record.status != status:
                    continue
                candidates.append(record)
                continue
            if record.evidence_refs or record.retention_policy in {"keep_final", "preserve"}:
                preserved.append(record.artifact_id)
                continue
            if status and record.status != status:
                continue
            if record.status in {"failed", "expired", "deleted"}:
                candidates.append(record)
            else:
                blocked.append(record.artifact_id)
        return ArtifactCleanupPreview(
            candidate_artifacts=candidates,
            total_size_bytes=sum(item.size_bytes for item in candidates),
            preserved_artifacts=preserved,
            blocked_deletions=blocked,
            warnings=[] if candidates else ["no_cleanup_candidates"],
            evidence_refs=["artifact_library:cleanup_preview"],
        )

    def mobile_view_model(self) -> dict[str, object]:
        result = self.query(ArtifactQuery(limit=50))
        return {
            "ok": True,
            "screen": "artifact_library",
            "title": "Artifact Library",
            "filters": ["Todos", "Prontos", "Falhos", "Bloqueados", "Sandbox", "Projeto", "Reports", "Zips"],
            "cards": [self._mobile_card(item) for item in result.items],
            "raw_default_visible": False,
            "health": self.health(),
        }

    def trace(self, artifact_id: str) -> dict[str, object]:
        record = self.get(artifact_id)
        return {
            "artifact_id": artifact_id,
            "status": record.status,
            "origin_type": record.origin_type,
            "evidence_refs": record.evidence_refs,
            "tool_invocation_ids": record.tool_invocation_ids,
            "policy_decision_ids": record.policy_decision_ids,
            "metadata_sanitized": record.metadata_sanitized,
        }

    def _from_legacy_artifact(self, artifact: ArtifactRecord) -> ArtifactRecordV2:
        path = (PATHS.project_root / artifact.storage_path).resolve()
        exists = path.exists()
        artifact_type = self._artifact_type(artifact.filename, artifact.content_type)
        return ArtifactRecordV2(
            artifact_id=artifact.artifact_id,
            filename=artifact.filename,
            display_name=artifact.filename,
            content_type=artifact.content_type,
            size_bytes=path.stat().st_size if exists else artifact.size_bytes,
            status="ready" if exists else "failed",
            artifact_type=artifact_type,
            origin_type=str(artifact.metadata.get("origin_type") or "chat") if artifact.metadata.get("origin_type") in {"chat", "sandbox", "project_factory", "autopilot", "skill", "promotion", "validation", "debugger", "manual", "system"} else "chat",
            origin_id=artifact.message_id,
            session_id=str(artifact.metadata.get("session_id")) if artifact.metadata.get("session_id") else None,
            project_id=str(artifact.metadata.get("project_id")) if artifact.metadata.get("project_id") else None,
            evidence_refs=[str(item) for item in artifact.metadata.get("evidence_refs", [])],
            storage_path_sanitized=str(path),
            download_endpoint=f"/api/v1/artifacts/{artifact.artifact_id}/download" if exists else None,
            requires_token=True,
            preview_available=exists and artifact_type != "unknown",
            context_usable=artifact_type in {"text", "markdown_report", "json_report", "manifest", "log_sanitized"},
            error_reason=None if exists else "artifact_file_missing",
            created_at=artifact.created_at,
            metadata_sanitized=redact_payload(artifact.metadata),
        )

    def _from_tool_artifact(self, artifact: ToolArtifactRecord) -> ArtifactRecordV2:
        path = self.tool_store.artifact_content_path(artifact)
        exists = path.exists()
        artifact_type = self._artifact_type(artifact.filename, artifact.content_type)
        origin = self._origin_type(artifact)
        metadata = redact_payload(artifact.metadata_sanitized)
        return ArtifactRecordV2(
            artifact_id=artifact.artifact_id,
            filename=artifact.filename,
            display_name=artifact.filename,
            content_type=artifact.content_type,
            size_bytes=path.stat().st_size if exists else artifact.size_bytes or artifact.size,
            status=artifact.status if exists or artifact.status != "ready" else "failed",
            artifact_type=artifact_type,
            origin_type=origin,
            origin_id=artifact.tool_invocation_id or artifact.run_id or artifact.session_id,
            session_id=artifact.session_id,
            run_id=artifact.run_id,
            agent_id=artifact.agent_id,
            project_profile_id=artifact.project_profile_id,
            sandbox_task_id=artifact.sandbox_task_id,
            skill_execution_id=str(metadata.get("skill_execution_id")) if metadata.get("skill_execution_id") else None,
            skill_pack_id=str(metadata.get("skill_pack_id")) if metadata.get("skill_pack_id") else None,
            skill_pack_execution_id=str(metadata.get("skill_pack_execution_id")) if metadata.get("skill_pack_execution_id") else None,
            autopilot_run_id=str(metadata.get("autopilot_run_id")) if metadata.get("autopilot_run_id") else None,
            promotion_plan_id=str(metadata.get("promotion_plan_id")) if metadata.get("promotion_plan_id") else None,
            template_execution_id=str(metadata.get("template_execution_id")) if metadata.get("template_execution_id") else None,
            validation_id=artifact.validation_id,
            policy_decision_ids=[str(metadata["policy_decision_id"])] if metadata.get("policy_decision_id") else [],
            tool_invocation_ids=[artifact.tool_invocation_id] if artifact.tool_invocation_id else [],
            evidence_refs=artifact.evidence_refs,
            storage_path_sanitized=str(path),
            download_endpoint=f"/api/v1/artifacts/{artifact.artifact_id}/download" if exists and artifact.status == "ready" else None,
            requires_token=True,
            preview_available=exists and artifact_type != "unknown",
            context_usable=artifact_type in {"text", "markdown_report", "json_report", "manifest", "log_sanitized"},
            error_reason=None if exists else "artifact_file_missing",
            created_at=artifact.created_at,
            metadata_sanitized=metadata,
        )

    def _matches(self, record: ArtifactRecordV2, query: ArtifactQuery) -> bool:
        for field in ["session_id", "project_id", "sandbox_task_id", "skill_execution_id", "skill_pack_id", "skill_pack_execution_id", "autopilot_run_id", "promotion_plan_id", "template_execution_id", "status", "origin_type", "artifact_type"]:
            expected = getattr(query, field)
            if expected and getattr(record, field) != expected:
                return False
        if query.text_query:
            needle = query.text_query.casefold()
            haystack = f"{record.filename} {record.display_name or ''} {record.origin_type} {record.artifact_type}".casefold()
            if needle not in haystack:
                return False
        return True

    def _content_path(self, record: ArtifactRecordV2) -> Path | None:
        if record.storage_path_sanitized:
            return Path(record.storage_path_sanitized)
        return None

    def _text_preview(self, record: ArtifactRecordV2, path: Path, request: ArtifactPreviewRequest) -> ArtifactPreviewResult:
        max_bytes = request.max_bytes or int(((self.policy.get("preview") or {}).get("max_text_preview_kb", 256))) * 1024
        raw = path.read_bytes()[:max_bytes]
        text = raw.decode("utf-8", errors="replace")
        redacted = self.secret_scanner.redact(text) if request.sanitize else text
        redaction = redacted != text
        return ArtifactPreviewResult(
            artifact_id=record.artifact_id,
            status=record.status,
            preview_mode=request.preview_mode,
            preview_available=True,
            content_preview=redacted,
            redaction_applied=redaction,
            warnings=["preview_truncated"] if path.stat().st_size > len(raw) else [],
            evidence_refs=record.evidence_refs,
        )

    def _zip_preview(self, record: ArtifactRecordV2, path: Path, request: ArtifactPreviewRequest) -> ArtifactPreviewResult:
        max_entries = int(((self.policy.get("preview") or {}).get("max_zip_file_list", 500)))
        entries: list[dict[str, Any]] = []
        warnings: list[str] = []
        errors: list[str] = []
        try:
            with zipfile.ZipFile(path, "r") as archive:
                for info in archive.infolist()[:max_entries]:
                    traversal = self._zip_entry_is_unsafe(info.filename)
                    if traversal:
                        errors.append(f"zip_path_traversal:{info.filename}")
                    entries.append({"filename": info.filename, "size": info.file_size, "unsafe_path": traversal})
                if len(archive.infolist()) > max_entries:
                    warnings.append("zip_listing_truncated")
        except zipfile.BadZipFile:
            errors.append("invalid_zip")
        return ArtifactPreviewResult(
            artifact_id=record.artifact_id,
            status="blocked" if errors else record.status,
            preview_mode="zip_listing",
            preview_available=not bool(errors),
            zip_entries=entries,
            warnings=warnings,
            errors=errors,
            evidence_refs=record.evidence_refs,
        )

    def _artifact_type(self, filename: str, content_type: str) -> str:
        lower = filename.casefold()
        if lower.endswith(".zip") or content_type == "application/zip":
            return "zip"
        if lower.endswith(".md"):
            return "markdown_report"
        if lower.endswith(".json") or content_type == "application/json":
            return "json_report"
        if lower.endswith(".txt") or content_type.startswith("text/"):
            return "text"
        if lower.endswith((".png", ".jpg", ".jpeg", ".webp")) or content_type.startswith("image/"):
            return "image"
        if lower.endswith((".patch", ".diff")):
            return "diff"
        return "unknown"

    def _origin_type(self, artifact: ToolArtifactRecord) -> str:
        metadata = artifact.metadata_sanitized
        if metadata.get("promotion_plan_id"):
            return "promotion"
        if metadata.get("autopilot_run_id"):
            return "autopilot"
        if metadata.get("skill_execution_id"):
            return "skill"
        if metadata.get("template_execution_id"):
            return "project_factory"
        if artifact.project_generation_id:
            return "project_factory"
        if artifact.sandbox_task_id or artifact.origin == "sandbox_export":
            return "sandbox"
        if artifact.origin == "validation_report":
            return "validation"
        return "system"

    def _zip_entry_is_unsafe(self, name: str) -> bool:
        normalized = name.replace("\\", "/")
        return normalized.startswith("/") or ".." in normalized.split("/") or ":" in normalized.split("/")[0]

    def _safe_filename(self, value: str, *, default: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in Path(value).name).strip("._")
        return safe or default

    def _mobile_card(self, record: ArtifactRecordV2) -> dict[str, object]:
        return {
            "artifact_id": record.artifact_id,
            "title": record.display_name or record.filename,
            "filename": record.filename,
            "status": record.status,
            "origin_type": record.origin_type,
            "artifact_type": record.artifact_type,
            "size_bytes": record.size_bytes,
            "created_at": record.created_at,
            "download": {
                "available": record.status == "ready" and bool(record.download_endpoint),
                "endpoint": record.download_endpoint if record.status == "ready" else None,
                "requires_token": True,
            },
            "actions": {
                "preview": record.preview_available,
                "copy_id": True,
                "use_as_context": record.context_usable,
                "details": True,
            },
            "error_reason": record.error_reason,
        }
