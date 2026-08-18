from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import ToolArtifactRecord
from aipinho.schemas.artifacts.artifact_interaction_contracts import (
    ArtifactRecord,
    UniversalArtifactCreateRequest,
)
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository, _safe_filename
from aipinho.services.events.event_core import EventPublisherService, contains_secret, redact_payload

ArtifactPersistProgress = Callable[[str, dict[str, Any]], None]
_DEFAULT_MANIFEST_INLINE_MAX_BYTES = 250_000


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


class UniversalArtifactRegistryService:
    """Unified read/write facade over chat artifacts and tool-gateway artifacts."""

    def __init__(
        self,
        *,
        registry: ArtifactRegistryRepository | None = None,
        tool_store: AgentToolInvocationStore | None = None,
        store_root: Path | None = None,
        index_root: Path | None = None,
    ) -> None:
        self.registry = registry or ArtifactRegistryRepository()
        self.tool_store = tool_store or AgentToolInvocationStore()
        self.store_root = store_root or PATHS.project_root / "data" / "artifacts" / "universal"
        self.index_root = index_root or PATHS.project_root / "data" / "runtime" / "artifact_index"

    def create(
        self,
        request: UniversalArtifactCreateRequest,
        *,
        progress_observer: ArtifactPersistProgress | None = None,
    ) -> ArtifactRecord:
        if not request.source_agent.strip():
            raise ValueError("artifact_source_agent_required")
        filename = _safe_filename(request.filename)
        artifact_id = f"artifact_{uuid4().hex}"
        self._progress(progress_observer, "before_persist_payload_classification", artifact_id=artifact_id)
        self._progress(progress_observer, "before_payload_materialization", artifact_id=artifact_id)
        content = self._content_bytes(request)
        self._progress(
            progress_observer,
            "after_payload_materialization",
            artifact_id=artifact_id,
            payload_bytes=len(content),
            artifact_content_bytes=len(content),
        )
        self._progress(
            progress_observer,
            "after_persist_payload_classification",
            artifact_id=artifact_id,
            payload_bytes=len(content),
            artifact_content_bytes=len(content),
            payload_kind="artifact_content",
            payload_ref_count=0,
        )
        if request.status == "ready":
            self._validate_ready_content(content, allow_empty=request.allow_empty)
        self._progress(
            progress_observer,
            "before_payload_serialization",
            artifact_id=artifact_id,
            payload_bytes=len(content),
            artifact_content_bytes=len(content),
        )
        if contains_secret(content.decode("utf-8", errors="ignore")) or contains_secret(request.metadata) or contains_secret(request.provenance):
            raise ValueError("secret_detected_in_artifact")
        self._progress(
            progress_observer,
            "after_payload_serialization",
            artifact_id=artifact_id,
            payload_bytes=len(content),
            artifact_content_bytes=len(content),
            serialized_bytes=len(content),
            serialization_count=1,
        )
        self._progress(progress_observer, "before_payload_ref_decision", artifact_id=artifact_id)
        manifest_payload = self._project_manifest_payloads(
            artifact_id=artifact_id,
            metadata={
                "logical_path": request.logical_path,
                "artifact_type": request.artifact_type,
                "producer_step": request.producer_step,
                "event_id": request.event_id,
                "task_id": request.task_id or request.owner_task_id,
                "task_run_id": request.task_run_id or request.owner_task_id,
                "evidence_refs": list(request.evidence_refs),
                **request.metadata,
                "visible_to_agent_ids": sorted(set(request.visible_to_agent_ids)),
            },
            provenance=request.provenance,
            progress_observer=progress_observer,
        )
        self._progress(
            progress_observer,
            "after_payload_ref_decision",
            artifact_id=artifact_id,
            payload_ref_count=manifest_payload["payload_ref_count"],
            manifest_inline_bytes=manifest_payload["manifest_inline_bytes"],
            payload_ref_bytes=manifest_payload["payload_ref_bytes"],
            payload_ref_dedup_hit_count=manifest_payload["payload_ref_dedup_hit_count"],
        )
        sha256 = hashlib.sha256(content).hexdigest()
        provisional = ArtifactRecord(
            artifact_id=artifact_id,
            logical_path=request.logical_path,
            storage_ref="pending",
            artifact_type=request.artifact_type,
            producer_step=request.producer_step,
            event_id=request.event_id,
            task_id=request.task_id or request.owner_task_id,
            task_run_id=request.task_run_id or request.owner_task_id,
            source_agent=request.source_agent,
            owner_task_id=request.owner_task_id,
            bridge_task_id=request.bridge_task_id,
            session_id=request.session_id,
            filename=filename,
            content_type=request.content_type,
            size_bytes=len(content),
            sha256=sha256,
            storage_path="pending",
            local_path=None,
            download_endpoint=None,
            requires_token=True,
            status=request.status,
            validation_status=request.validation_status,
            evidence_refs=list(request.evidence_refs),
            provenance=manifest_payload["provenance"],
            metadata=manifest_payload["metadata"],
        )
        self.store_root.mkdir(parents=True, exist_ok=True)
        path = self.store_root / f"{provisional.artifact_id}_{filename}"
        self._progress(
            progress_observer,
            "before_artifact_content_write",
            artifact_id=artifact_id,
            artifact_content_bytes=len(content),
        )
        write_result = self._atomic_write_bytes(path, content)
        self._progress(
            progress_observer,
            "after_artifact_content_write",
            artifact_id=artifact_id,
            artifact_content_bytes=len(content),
            bytes_written=write_result["bytes_written"],
            write_elapsed_ms=write_result["write_elapsed_ms"],
            checksum=sha256,
        )
        record = provisional.model_copy(update={
            "storage_path": str(path.relative_to(PATHS.project_root)),
            "storage_ref": str(path.relative_to(PATHS.project_root)),
            "local_path": str(path),
            "download_endpoint": f"/api/v1/artifacts/{provisional.artifact_id}/download",
        })
        try:
            self._progress(progress_observer, "before_manifest_build", artifact_id=artifact_id)
            manifest_bytes = len(json.dumps(_dump_model(record), ensure_ascii=False, default=str).encode("utf-8"))
            self._progress(
                progress_observer,
                "after_manifest_build",
                artifact_id=artifact_id,
                manifest_bytes=manifest_bytes,
                payload_ref_count=manifest_payload["payload_ref_count"],
            )
            self._progress(progress_observer, "before_manifest_persist", artifact_id=artifact_id, manifest_bytes=manifest_bytes)
            saved = self.registry.save(record, progress_observer=progress_observer)
            self._progress(progress_observer, "after_manifest_persist", artifact_id=artifact_id, manifest_bytes=manifest_bytes)
            self._progress(progress_observer, "before_registry_index_update", artifact_id=artifact_id)
            self._index_by_task_run(saved)
            self._progress(progress_observer, "after_registry_index_update", artifact_id=artifact_id)
            self._progress(progress_observer, "before_artifact_commit", artifact_id=artifact_id)
            EventPublisherService().publish(EventPublishRequest(
                event_type="artifact_created",
                source_service="artifact_service",
                human_summary=f"Artifact registrado: {filename}",
                payload={
                    "artifact_id": saved.artifact_id,
                    "source_agent": saved.source_agent,
                    "owner_task_id": saved.owner_task_id,
                    "bridge_task_id": saved.bridge_task_id,
                    "session_id": saved.session_id,
                },
            ))
            self._progress(
                progress_observer,
                "after_artifact_commit",
                artifact_id=artifact_id,
                payload_ref_count=manifest_payload["payload_ref_count"],
                manifest_bytes=manifest_bytes,
                payload_ref_dedup_hit_count=manifest_payload["payload_ref_dedup_hit_count"],
            )
            return saved
        except Exception:
            path.unlink(missing_ok=True)
            raise

    def _project_manifest_payloads(
        self,
        *,
        artifact_id: str,
        metadata: dict[str, Any],
        provenance: dict[str, Any],
        progress_observer: ArtifactPersistProgress | None,
    ) -> dict[str, Any]:
        max_inline = self._manifest_inline_max_bytes()
        payload_ref_count = 0
        payload_ref_bytes = 0
        payload_ref_dedup_hit_count = 0
        refs_by_digest: dict[str, dict[str, Any]] = {}

        def project(kind: str, value: Any) -> Any:
            nonlocal payload_ref_count, payload_ref_bytes, payload_ref_dedup_hit_count
            redacted = redact_payload(value)
            encoded = json.dumps(redacted, ensure_ascii=False, default=str)
            size = len(encoded.encode("utf-8"))
            if size <= max_inline:
                return redacted
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            if digest in refs_by_digest:
                payload_ref_dedup_hit_count += 1
                ref = dict(refs_by_digest[digest])
                ref["payload_kind"] = kind
                ref["dedup_hit"] = True
                ref["dedup_source_payload_ref_id"] = refs_by_digest[digest].get("payload_ref_id")
                self._progress(
                    progress_observer,
                    "payload_ref_dedup_hit",
                    artifact_id=artifact_id,
                    payload_kind=kind,
                    payload_bytes=size,
                    payload_ref_count=payload_ref_count,
                    payload_ref_dedup_hit_count=payload_ref_dedup_hit_count,
                )
                return ref
            self._progress(
                progress_observer,
                "before_payload_ref_persist",
                artifact_id=artifact_id,
                payload_kind=kind,
                payload_bytes=size,
                payload_ref_count=payload_ref_count,
            )
            ref = self._write_payload_ref(artifact_id=artifact_id, kind=kind, encoded=encoded, size=size, digest=digest)
            refs_by_digest[digest] = dict(ref)
            payload_ref_count += 1
            payload_ref_bytes += size
            self._progress(
                progress_observer,
                "after_payload_ref_persist",
                artifact_id=artifact_id,
                payload_kind=kind,
                payload_bytes=size,
                payload_ref_count=payload_ref_count,
                payload_ref_dedup_hit_count=payload_ref_dedup_hit_count,
            )
            return ref

        projected_metadata = self._project_dict_children("metadata", metadata, project)
        projected_provenance = self._project_dict_children("provenance", provenance, project)
        manifest_inline_bytes = len(
            json.dumps({"metadata": projected_metadata, "provenance": projected_provenance}, ensure_ascii=False, default=str).encode("utf-8")
        )
        return {
            "metadata": projected_metadata,
            "provenance": projected_provenance,
            "payload_ref_count": payload_ref_count,
            "payload_ref_bytes": payload_ref_bytes,
            "payload_ref_dedup_hit_count": payload_ref_dedup_hit_count,
            "manifest_inline_bytes": manifest_inline_bytes,
        }

    def _project_dict_children(self, prefix: str, value: dict[str, Any], project: Callable[[str, Any], Any]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, item in value.items():
            output[str(key)] = project(f"{prefix}.{key}", item)
        return output

    def _write_payload_ref(self, *, artifact_id: str, kind: str, encoded: str, size: int, digest: str | None = None) -> dict[str, Any]:
        digest = digest or hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        safe_kind = self._safe_index_name(kind)
        root = PATHS.project_root / "data" / "artifacts" / "payload_refs" / self._safe_index_name(artifact_id)
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"{safe_kind}_{digest[:16]}.json"
        self._atomic_write_text(path, encoded)
        try:
            content_ref = str(path.relative_to(PATHS.project_root))
        except Exception:
            content_ref = str(path)
        return {
            "payload_ref_id": f"artifact_payload_ref_{digest[:24]}",
            "payload_kind": kind,
            "content_ref": content_ref,
            "byte_size": size,
            "sha256": digest,
            "storage_scope": "artifact_payload_ref_store",
            "inline": False,
            "reason_code": "ARTIFACT_MANIFEST_PAYLOAD_SPILLED_TO_REF",
        }

    def _manifest_inline_max_bytes(self) -> int:
        try:
            return max(1, int(os.environ.get("AIPINHO_ARTIFACT_MANIFEST_INLINE_MAX_BYTES", _DEFAULT_MANIFEST_INLINE_MAX_BYTES)))
        except (TypeError, ValueError):
            return _DEFAULT_MANIFEST_INLINE_MAX_BYTES

    def _atomic_write_bytes(self, path: Path, content: bytes) -> dict[str, Any]:
        started = time.monotonic()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            temp.write_bytes(content)
            temp.replace(path)
            elapsed_ms = int(max(0.0, (time.monotonic() - started) * 1000))
            return {"bytes_written": len(content), "write_elapsed_ms": elapsed_ms}
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)

    def _atomic_write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        try:
            temp.write_text(content, encoding="utf-8")
            temp.replace(path)
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)

    def _progress(self, observer: ArtifactPersistProgress | None, stage: str, **metrics: Any) -> None:
        if observer is None:
            return
        try:
            observer(stage, metrics)
        except Exception:
            return

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        indexed = self._indexed_row_by_artifact(artifact_id)
        if indexed is not None:
            return self._public_index_record(indexed)
        record = self.registry.get(artifact_id)
        if record is not None:
            return self._public_interaction_record(record)
        tool = self.tool_store.get_artifact(artifact_id)
        if tool is not None:
            return self._public_tool_record(tool)
        return None

    def provenance(self, artifact_id: str) -> dict[str, Any] | None:
        artifact = self.get(artifact_id)
        if artifact is None:
            return None
        provenance = artifact.get("provenance") if isinstance(artifact.get("provenance"), dict) else {}
        return {
            "artifact_id": artifact_id,
            "source_agent": artifact.get("source_agent"),
            "executor_agent": provenance.get("executor_agent") or artifact.get("source_agent"),
            "owner_task_id": artifact.get("owner_task_id"),
            "bridge_task_id": artifact.get("bridge_task_id"),
            "session_id": artifact.get("session_id"),
            "workspace": provenance.get("workspace"),
            "source_files": provenance.get("source_files") or [],
            "validation_status": artifact.get("validation_status"),
            "status": artifact.get("status"),
            "created_at": artifact.get("created_at"),
            "evidence_refs": provenance.get("evidence_refs") or [],
            "raw_default_visible": False,
        }

    def revalidate(self, artifact_id: str) -> dict[str, Any] | None:
        indexed = self._indexed_row_by_artifact(artifact_id)
        if indexed is not None:
            path = self._artifact_path_from_public(indexed)
            status = str(indexed.get("status") or "ready")
            validation_status = str(indexed.get("validation_status") or "validated")
            reason: str | None = None
            size = int(indexed.get("size_bytes") or indexed.get("size") or 0)
            if path is None or not path.exists() or not path.is_file():
                status = "missing"
                validation_status = "missing"
                reason = "artifact_file_missing"
                size = 0
            elif path.stat().st_size <= 0:
                status = "stale"
                validation_status = "stale"
                reason = "artifact_file_empty"
                size = path.stat().st_size
            updated = {
                **indexed,
                "status": status,
                "validation_status": validation_status,
                "size_bytes": size,
                "error_reason": reason,
            }
            self._write_artifact_index_record(updated)
            return self._public_index_record(updated)
        record = self.registry.get(artifact_id)
        if record is None:
            return self.get(artifact_id)
        path = (PATHS.project_root / record.storage_path).resolve()
        status = "ready"
        validation_status = record.validation_status or "validated"
        reason: str | None = None
        size = record.size_bytes
        if not path.exists() or not path.is_file():
            status = "missing"
            validation_status = "missing"
            reason = "artifact_file_missing"
            size = 0
        elif path.stat().st_size <= 0 and not record.metadata.get("allow_empty"):
            status = "stale"
            validation_status = "stale"
            reason = "artifact_file_empty"
            size = path.stat().st_size
        else:
            size = path.stat().st_size
        saved = self.registry.save(record.model_copy(update={
            "status": status,
            "validation_status": validation_status,
            "size_bytes": size,
            "error_reason": reason,
        }))
        return self._public_interaction_record(saved)

    def list_all(self, *, limit: int = 200) -> list[dict[str, Any]]:
        records = [self._public_interaction_record(record) for record in self.registry.list()]
        records.extend(self._public_tool_record(artifact) for artifact in self.tool_store.list_artifacts(include_all=True))
        return sorted(records, key=lambda item: str(item.get("created_at") or ""), reverse=True)[:limit]

    def by_agent(self, agent_id: str, *, session_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        rows = [
            item
            for item in self.list_all(limit=10000)
            if self._matches_agent(item, agent_id) and (not session_id or item.get("session_id") == session_id)
        ]
        return rows[:limit]

    def by_task(self, task_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = self._indexed_rows_by_task_run(task_id, limit=limit)
        if rows:
            return rows[:limit]
        if str(task_id or "").startswith("task_run_"):
            return rows
        known = {str(item.get("artifact_id")) for item in rows if item.get("artifact_id")}
        for record in self.registry.list():
            if record.artifact_id in known:
                continue
            if (
                record.owner_task_id == task_id
                or record.task_id == task_id
                or record.task_run_id == task_id
            ):
                rows.append(self._public_interaction_record(record))
                known.add(record.artifact_id)
                if len(rows) >= limit:
                    return rows
        if len(rows) < limit:
            for artifact in self.tool_store.list_artifacts(include_all=True):
                item = self._public_tool_record(artifact)
                if (
                    item.get("owner_task_id") == task_id
                    or item.get("task_id") == task_id
                    or item.get("run_id") == task_id
                ):
                    rows.append(item)
                    known.add(str(item.get("artifact_id") or ""))
                    if len(rows) >= limit:
                        break
        return rows

    def _index_by_task_run(self, record: ArtifactRecord) -> None:
        task_run_id = str(record.task_run_id or record.owner_task_id or "")
        if not task_run_id:
            return
        index_dir = self.index_root / "by_task_run"
        index_dir.mkdir(parents=True, exist_ok=True)
        path = index_dir / f"{self._safe_index_name(task_run_id)}.json"
        rows = self._read_index(path)
        rows = [item for item in rows if item.get("artifact_id") != record.artifact_id]
        rows.append(self._light_index_record(record))
        self._atomic_write_json(path, rows)
        by_artifact = self.index_root / "by_artifact"
        by_artifact.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(by_artifact / f"{self._safe_index_name(record.artifact_id)}.json", self._light_index_record(record))

    def _indexed_rows_by_task_run(self, task_run_id: str, *, limit: int) -> list[dict[str, Any]]:
        path = self.index_root / "by_task_run" / f"{self._safe_index_name(task_run_id)}.json"
        rows = self._read_index(path)
        output: list[dict[str, Any]] = []
        for row in rows[: max(1, limit)]:
            output.append(self._public_index_record(row))
        return output

    def _indexed_row_by_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        path = self.index_root / "by_artifact" / f"{self._safe_index_name(artifact_id)}.json"
        if not path.exists() or path.stat().st_size == 0:
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def _write_artifact_index_record(self, row: dict[str, Any]) -> None:
        artifact_id = str(row.get("artifact_id") or "")
        if not artifact_id:
            return
        by_artifact = self.index_root / "by_artifact"
        by_artifact.mkdir(parents=True, exist_ok=True)
        self._atomic_write_json(by_artifact / f"{self._safe_index_name(artifact_id)}.json", row)
        task_run_id = str(row.get("task_run_id") or row.get("owner_task_id") or "")
        if not task_run_id:
            return
        task_path = self.index_root / "by_task_run" / f"{self._safe_index_name(task_run_id)}.json"
        rows = self._read_index(task_path)
        rows = [item for item in rows if item.get("artifact_id") != artifact_id]
        rows.append(row)
        self._atomic_write_json(task_path, rows)

    def _read_index(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists() or path.stat().st_size == 0:
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def _atomic_write_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)

    def _safe_index_name(self, value: str) -> str:
        return "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in str(value or ""))[:180] or "unbound"

    def _light_index_record(self, record: ArtifactRecord) -> dict[str, Any]:
        return {
            "artifact_id": record.artifact_id,
            "logical_path": record.logical_path or record.metadata.get("logical_path"),
            "task_id": record.task_id,
            "task_run_id": record.task_run_id or record.owner_task_id,
            "owner_task_id": record.owner_task_id,
            "session_id": record.session_id,
            "storage_ref": record.storage_ref or record.storage_path,
            "storage_path": record.storage_path,
            "local_path": record.local_path,
            "content_type": record.content_type,
            "artifact_type": record.artifact_type,
            "producer_step": record.producer_step,
            "event_id": record.event_id,
            "status": record.status,
            "validation_status": record.validation_status,
            "reason_code": record.metadata.get("reason_code"),
            "semantic_contract_status": record.metadata.get("semantic_contract_status"),
            "safe_to_use": record.metadata.get("safe_to_use"),
            "limitations": record.metadata.get("limitations") or [],
            "partial_rows": record.metadata.get("partial_rows"),
            "expected_rows": record.metadata.get("expected_rows"),
            "selected_rows": record.metadata.get("selected_rows"),
            "bound_rows": record.metadata.get("bound_rows"),
            "evidence_ref_count": record.metadata.get("evidence_ref_count"),
            "evidence_refs": record.evidence_refs or record.metadata.get("evidence_refs") or [],
            "evidence_refs_sample": record.metadata.get("evidence_refs_sample") or [],
            "row_evidence_coverage": record.metadata.get("row_evidence_coverage") or {},
            "row_validation_summary": record.metadata.get("row_validation_summary") or {},
            "rendered_columns": record.metadata.get("rendered_columns") or [],
            "missing_columns": record.metadata.get("missing_columns") or [],
            "size_bytes": record.size_bytes,
            "sha256": record.sha256,
            "download_endpoint": record.download_endpoint,
            "created_at": record.created_at,
            "source": "artifact_index",
        }

    def _public_index_record(self, row: dict[str, Any]) -> dict[str, Any]:
        data = dict(row)
        path = self._artifact_path_from_public(data)
        if path is not None:
            data.setdefault("local_path", str(path))
        data.setdefault("storage_ref", data.get("storage_path"))
        data.setdefault("download_endpoint", f"/api/v1/artifacts/{data.get('artifact_id')}/download")
        data.setdefault("requires_token", True)
        data.setdefault("size", data.get("size_bytes", 0))
        data.setdefault("evidence_refs", [])
        data.setdefault("metadata", {})
        data.setdefault("provenance", {"source": "artifact_index"})
        for key in (
            "reason_code",
            "semantic_contract_status",
            "safe_to_use",
            "limitations",
            "partial_rows",
            "expected_rows",
            "selected_rows",
            "bound_rows",
            "evidence_ref_count",
            "evidence_refs_sample",
            "row_evidence_coverage",
            "row_validation_summary",
            "rendered_columns",
            "missing_columns",
        ):
            if key not in data and isinstance(data.get("metadata"), dict):
                data[key] = data["metadata"].get(key)
        return data

    def _artifact_path_from_public(self, data: dict[str, Any]) -> Path | None:
        local_path = data.get("local_path")
        storage_ref = str(data.get("storage_ref") or data.get("storage_path") or "")
        if local_path:
            return Path(str(local_path))
        if storage_ref:
            return (PATHS.project_root / storage_ref).resolve()
        return None

    def by_bridge_task(self, bridge_task_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        rows = [
            item
            for item in self.list_all(limit=10000)
            if item.get("bridge_task_id") == bridge_task_id
            or item.get("delegation_id") == bridge_task_id
            or item.get("parent_run_id") == bridge_task_id
        ]
        return rows[:limit]

    def _content_bytes(self, request: UniversalArtifactCreateRequest) -> bytes:
        if request.local_path:
            path = Path(request.local_path)
            if not path.exists() or not path.is_file():
                raise FileNotFoundError("artifact_local_path_not_found")
            return path.read_bytes()
        if request.content is None:
            raise ValueError("artifact_content_or_local_path_required")
        if request.encoding == "base64":
            try:
                return base64.b64decode(request.content.encode("ascii"), validate=True)
            except Exception as exc:
                raise ValueError("invalid_base64_artifact_content") from exc
        if request.encoding in {"text", "utf-8"}:
            return request.content.encode("utf-8")
        raise ValueError("unsupported_artifact_encoding")

    def _validate_ready_content(self, content: bytes, *, allow_empty: bool) -> None:
        if content or allow_empty:
            return
        raise ValueError("ready_artifact_must_have_non_empty_file")

    def _public_interaction_record(self, record: ArtifactRecord) -> dict[str, Any]:
        data = _dump_model(record)
        path = (PATHS.project_root / record.storage_path).resolve()
        ready = record.status == "ready"
        if ready and (not path.exists() or (record.size_bytes <= 0 and not record.metadata.get("allow_empty"))):
            data["status"] = "missing"
            data["validation_status"] = "missing"
            data["error_reason"] = "artifact_file_missing_or_empty"
        self._fill_if_empty(data, "download_endpoint", f"/api/v1/artifacts/{record.artifact_id}/download")
        self._fill_if_empty(data, "requires_token", True)
        self._fill_if_empty(data, "local_path", str(path))
        self._fill_if_empty(data, "size", data.get("size_bytes", 0))
        self._fill_if_empty(data, "source_agent", record.source_agent or record.metadata.get("source_agent"))
        self._fill_if_empty(data, "owner_task_id", record.owner_task_id or record.metadata.get("owner_task_id"))
        self._fill_if_empty(data, "task_id", record.task_id or record.metadata.get("task_id") or record.owner_task_id)
        self._fill_if_empty(data, "task_run_id", record.task_run_id or record.metadata.get("task_run_id") or record.owner_task_id)
        self._fill_if_empty(data, "logical_path", record.logical_path or record.metadata.get("logical_path"))
        self._fill_if_empty(data, "storage_ref", record.storage_ref or record.storage_path)
        self._fill_if_empty(data, "artifact_type", record.artifact_type or record.metadata.get("artifact_type") or "runtime_output")
        self._fill_if_empty(data, "producer_step", record.producer_step or record.metadata.get("producer_step"))
        self._fill_if_empty(data, "event_id", record.event_id or record.metadata.get("event_id") or (record.provenance or {}).get("event_id"))
        self._fill_if_empty(data, "evidence_refs", record.evidence_refs or record.metadata.get("evidence_refs") or [])
        self._fill_if_empty(data, "bridge_task_id", record.bridge_task_id or record.metadata.get("bridge_task_id"))
        self._fill_if_empty(data, "provenance", record.provenance or record.metadata.get("provenance") or {})
        return data

    def _fill_if_empty(self, data: dict[str, Any], key: str, value: Any) -> None:
        current = data.get(key)
        current_empty = current is None or current == "" or current == "pending"
        value_empty = value is None or value == ""
        if current_empty and not value_empty:
            data[key] = value

    def _public_tool_record(self, artifact: ToolArtifactRecord) -> dict[str, Any]:
        data = _dump_model(artifact)
        path = self.tool_store.artifact_content_path(artifact)
        if artifact.status == "ready" and (not path.exists() or (artifact.size_bytes <= 0 and artifact.size <= 0)):
            data["status"] = "missing"
            data["error_reason"] = "artifact_file_missing_or_empty"
        data["source_agent"] = artifact.agent_id
        data["owner_task_id"] = artifact.run_id
        data["bridge_task_id"] = artifact.delegation_id
        data["download_endpoint"] = artifact.download_endpoint or f"/api/v1/agents/artifacts/{artifact.artifact_id}/download"
        data["requires_token"] = artifact.requires_token
        data["local_path"] = str(path)
        data["validation_status"] = artifact.validation_id or ("validated" if data.get("status") == "ready" else data.get("status", "unknown"))
        data["provenance"] = {
            "registry": "agent_tool_gateway",
            "tool_invocation_id": artifact.tool_invocation_id,
            "origin": artifact.origin,
        }
        return data

    def _matches_agent(self, item: dict[str, Any], agent_id: str) -> bool:
        visible = item.get("visible_to_agent_ids")
        if not visible:
            metadata = item.get("metadata") or item.get("metadata_sanitized") or {}
            visible = metadata.get("visible_to_agent_ids") if isinstance(metadata, dict) else []
        return item.get("source_agent") == agent_id or item.get("agent_id") == agent_id or agent_id in set(visible or [])
