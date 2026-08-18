from __future__ import annotations

import base64
import hashlib
import json
import re
import zipfile
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Callable

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_interaction_contracts import (
    ArtifactDownloadLink,
    ArtifactRecord,
    ArtifactUploadRequest,
    ArtifactUploadResponse,
    ArtifactZipRequest,
    ArtifactZipResponse,
)
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.events.event_core import EventPublisherService, contains_secret, redact_payload

_DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".ps1", ".msi", ".com", ".scr"}
_LEGACY_REGISTRY_MAX_BYTES = 25_000_000
ArtifactPersistProgress = Callable[[str, dict[str, Any]], None]


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not name or name in {".", ".."}:
        raise ValueError("invalid_filename")
    if Path(name).suffix.lower() in _DANGEROUS_EXTENSIONS:
        raise ValueError("dangerous_artifact_extension")
    return name


class ArtifactRegistryRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "artifacts" / "manifests" / "artifact_registry.json"
        self.by_artifact_root = self.path.parent / "by_artifact"
        self.index_path = self.path.parent / "artifact_registry_index.json"
        self.diagnostic_path = self.path.parent / "artifact_registry_diagnostic.json"

    def list(self) -> list[ArtifactRecord]:
        records_by_id: dict[str, ArtifactRecord] = {}
        for record in self._list_sharded_records():
            records_by_id[record.artifact_id] = record
        for record in self._read_legacy_records():
            records_by_id.setdefault(record.artifact_id, record)
        return sorted(records_by_id.values(), key=lambda item: item.created_at, reverse=True)

    def save(self, record: ArtifactRecord, *, progress_observer: ArtifactPersistProgress | None = None) -> ArtifactRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.by_artifact_root.mkdir(parents=True, exist_ok=True)
        self._progress(progress_observer, "before_sharded_manifest_persist", artifact_id=record.artifact_id)
        self._atomic_write_json(self._record_path(record.artifact_id), _dump_model(record))
        self._progress(progress_observer, "after_sharded_manifest_persist", artifact_id=record.artifact_id)
        self._progress(progress_observer, "before_light_index_persist", artifact_id=record.artifact_id)
        self._write_light_index(record)
        self._progress(progress_observer, "after_light_index_persist", artifact_id=record.artifact_id)
        if self._legacy_registry_can_be_updated():
            self._progress(progress_observer, "before_legacy_registry_projection", artifact_id=record.artifact_id)
            records = [item for item in self._read_legacy_records() if item.artifact_id != record.artifact_id]
            records.append(record)
            self._atomic_write_json(self.path, [_dump_model(item) for item in records])
            self._progress(progress_observer, "after_legacy_registry_projection", artifact_id=record.artifact_id)
        else:
            self._write_legacy_registry_diagnostic(
                status="legacy_registry_skipped",
                reason_code="ARTIFACT_REGISTRY_LEGACY_TOO_LARGE_OR_INVALID",
            )
            self._progress(
                progress_observer,
                "legacy_registry_projection_skipped",
                artifact_id=record.artifact_id,
                reason_code="ARTIFACT_REGISTRY_LEGACY_TOO_LARGE_OR_INVALID",
            )
        return record

    def _progress(self, observer: ArtifactPersistProgress | None, stage: str, **metrics: Any) -> None:
        if observer is None:
            return
        try:
            observer(stage, metrics)
        except Exception:
            return

    def get(self, artifact_id: str) -> ArtifactRecord | None:
        sharded = self._read_sharded_record(artifact_id)
        if sharded is not None:
            return sharded
        for record in self.list():
            if record.artifact_id == artifact_id:
                return record
        return None

    def _record_path(self, artifact_id: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(artifact_id or "unbound"))[:180] or "unbound"
        return self.by_artifact_root / f"{safe}.json"

    def _list_sharded_records(self) -> list[ArtifactRecord]:
        if not self.by_artifact_root.exists():
            return []
        records: list[ArtifactRecord] = []
        for path in sorted(self.by_artifact_root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(payload, dict):
                    records.append(ArtifactRecord(**payload))
            except Exception:
                continue
        return records

    def _read_sharded_record(self, artifact_id: str) -> ArtifactRecord | None:
        path = self._record_path(artifact_id)
        if not path.exists() or path.stat().st_size == 0:
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            return ArtifactRecord(**payload) if isinstance(payload, dict) else None
        except Exception:
            return None

    def _read_legacy_records(self) -> list[ArtifactRecord]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return []
        size = self.path.stat().st_size
        if size > _LEGACY_REGISTRY_MAX_BYTES:
            self._write_legacy_registry_diagnostic(
                status="legacy_registry_skipped",
                reason_code="ARTIFACT_REGISTRY_LEGACY_TOO_LARGE_FOR_INLINE_READ",
                size_bytes=size,
            )
            return []
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except JSONDecodeError as exc:
            self._write_legacy_registry_diagnostic(
                status="legacy_registry_invalid",
                reason_code="ARTIFACT_REGISTRY_LEGACY_JSON_DECODE_ERROR",
                size_bytes=size,
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
            )
            return []
        except Exception as exc:
            self._write_legacy_registry_diagnostic(
                status="legacy_registry_unreadable",
                reason_code="ARTIFACT_REGISTRY_LEGACY_UNREADABLE",
                size_bytes=size,
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
            )
            return []
        if not isinstance(loaded, list):
            self._write_legacy_registry_diagnostic(
                status="legacy_registry_invalid_shape",
                reason_code="ARTIFACT_REGISTRY_LEGACY_SHAPE_INVALID",
                size_bytes=size,
                observed_type=type(loaded).__name__,
            )
            return []
        records: list[ArtifactRecord] = []
        for item in loaded:
            if not isinstance(item, dict):
                continue
            try:
                records.append(ArtifactRecord(**item))
            except Exception:
                continue
        return records

    def _legacy_registry_can_be_updated(self) -> bool:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return True
        if self.path.stat().st_size > _LEGACY_REGISTRY_MAX_BYTES:
            return False
        return bool(self._read_legacy_records())

    def _write_light_index(self, record: ArtifactRecord) -> None:
        rows: list[dict[str, Any]] = []
        if self.index_path.exists() and self.index_path.stat().st_size <= _LEGACY_REGISTRY_MAX_BYTES:
            try:
                loaded = json.loads(self.index_path.read_text(encoding="utf-8-sig"))
                if isinstance(loaded, list):
                    rows = [item for item in loaded if isinstance(item, dict)]
            except Exception:
                rows = []
        rows = [item for item in rows if item.get("artifact_id") != record.artifact_id]
        rows.append(
            {
                "artifact_id": record.artifact_id,
                "logical_path": record.logical_path,
                "task_run_id": record.task_run_id or record.owner_task_id,
                "storage_ref": record.storage_ref or record.storage_path,
                "status": record.status,
                "validation_status": record.validation_status,
                "size_bytes": record.size_bytes,
                "created_at": record.created_at,
                "source": "artifact_registry_sharded_projection",
            }
        )
        self._atomic_write_json(self.index_path, sorted(rows, key=lambda item: str(item.get("created_at") or ""), reverse=True))

    def _write_legacy_registry_diagnostic(self, **payload: Any) -> None:
        diagnostic = {
            "component": "ArtifactRegistryRepository",
            "legacy_registry_path": str(self.path),
            "sharded_registry_path": str(self.by_artifact_root),
            "index_path": str(self.index_path),
            "legacy_registry_used_for_writes": False,
            **payload,
        }
        self._atomic_write_json(self.diagnostic_path, diagnostic)

    def _atomic_write_json(self, path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding="utf-8")
        temp.replace(path)


class ArtifactUploadService:
    def __init__(self, store_root: Path | None = None) -> None:
        self.store_root = store_root or PATHS.project_root / "data" / "artifacts" / "chat"
        self.registry = ArtifactRegistryRepository()

    def upload(self, request: ArtifactUploadRequest) -> ArtifactUploadResponse:
        filename = _safe_filename(request.filename)
        if contains_secret(request.content) or contains_secret(request.metadata):
            raise ValueError("secret_detected_in_artifact_upload")
        if request.encoding == "base64":
            content_bytes = base64.b64decode(request.content.encode("ascii"), validate=True)
        else:
            content_bytes = request.content.encode("utf-8")
        if request.status == "ready" and not content_bytes and not bool(request.metadata.get("allow_empty")):
            raise ValueError("ready_artifact_must_have_non_empty_file")
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        provisional = ArtifactRecord(
            source_agent=request.source_agent,
            owner_task_id=request.owner_task_id,
            bridge_task_id=request.bridge_task_id,
            session_id=request.session_id,
            filename=filename,
            content_type=request.content_type,
            size_bytes=len(content_bytes),
            sha256=sha256,
            storage_path="pending",
            message_id=request.message_id,
            status=request.status,
            validation_status=request.validation_status,
            provenance=redact_payload(request.provenance),
            metadata=redact_payload(request.metadata),
        )
        self.store_root.mkdir(parents=True, exist_ok=True)
        path = self.store_root / f"{provisional.artifact_id}_{filename}"
        path.write_bytes(content_bytes)
        record = ArtifactRecord(**{
            **_dump_model(provisional),
            "storage_path": str(path.relative_to(PATHS.project_root)),
            "local_path": str(path),
            "download_endpoint": f"/api/v1/artifacts/{provisional.artifact_id}/download",
            "requires_token": True,
        })
        self.registry.save(record)
        EventPublisherService().publish(EventPublishRequest(
            event_type="artifact_created",
            source_service="artifact_service",
            human_summary=f"Artifact registrado: {filename}",
            payload={"artifact_id": record.artifact_id, "filename": filename, "message_id": request.message_id},
        ))
        return ArtifactUploadResponse(artifact=record, download_path=f"/api/v1/artifacts/{record.artifact_id}/download")


class ArtifactDownloadService:
    def __init__(self) -> None:
        self.registry = ArtifactRegistryRepository()

    def link(self, artifact_id: str) -> ArtifactDownloadLink:
        record = self.registry.get(artifact_id)
        if record is None:
            raise FileNotFoundError(artifact_id)
        return ArtifactDownloadLink(artifact_id=artifact_id, download_path=f"/api/v1/artifacts/{artifact_id}/download", requires_token=True)

    def path(self, artifact_id: str) -> Path:
        record = self.registry.get(artifact_id)
        if record is None:
            raise FileNotFoundError(artifact_id)
        path = (PATHS.project_root / record.storage_path).resolve()
        root = (PATHS.project_root / "data" / "artifacts").resolve()
        if not str(path).startswith(str(root)):
            raise PermissionError("direct_workspace_file_serve_blocked")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(artifact_id)
        return path


class ArtifactZipService:
    def __init__(self) -> None:
        self.registry = ArtifactRegistryRepository()
        self.zip_root = PATHS.project_root / "data" / "artifacts" / "zips"

    def create(self, request: ArtifactZipRequest) -> ArtifactZipResponse:
        filename = _safe_filename(request.filename)
        if not filename.lower().endswith(".zip"):
            filename = f"{filename}.zip"
        records: list[ArtifactRecord] = []
        downloader = ArtifactDownloadService()
        for artifact_id in request.artifact_ids:
            record = self.registry.get(artifact_id)
            if record is None:
                raise FileNotFoundError(artifact_id)
            records.append(record)
        self.zip_root.mkdir(parents=True, exist_ok=True)
        temp = self.zip_root / f"bundle_{hashlib.sha256('|'.join(request.artifact_ids).encode('utf-8')).hexdigest()[:12]}_{filename}"
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for record in records:
                source = downloader.path(record.artifact_id)
                bundle.write(source, arcname=_safe_filename(record.filename))
        content = temp.read_bytes()
        record = ArtifactRecord(
            source_agent=self._common_source_agent(records),
            owner_task_id=self._common_value(records, "owner_task_id"),
            bridge_task_id=self._common_value(records, "bridge_task_id"),
            session_id=self._common_value(records, "session_id"),
            filename=filename,
            content_type="application/zip",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_path=str(temp.relative_to(PATHS.project_root)),
            local_path=str(temp),
            download_endpoint=None,
            requires_token=True,
            status="ready",
            validation_status="validated",
            provenance={"included_artifacts": request.artifact_ids},
            metadata={"included_artifacts": request.artifact_ids},
        )
        record = record.model_copy(update={"download_endpoint": f"/api/v1/artifacts/{record.artifact_id}/download"})
        self.registry.save(record)
        EventPublisherService().publish(EventPublishRequest(
            event_type="artifact_zip_created",
            source_service="artifact_service",
            human_summary=f"ZIP de artifacts criado: {filename}",
            payload={"artifact_id": record.artifact_id, "included_artifacts": request.artifact_ids},
        ))
        return ArtifactZipResponse(artifact=record, included_artifacts=request.artifact_ids, download_path=f"/api/v1/artifacts/{record.artifact_id}/download")

    def _common_source_agent(self, records: list[ArtifactRecord]) -> str | None:
        return self._common_value(records, "source_agent")

    def _common_value(self, records: list[ArtifactRecord], field: str) -> str | None:
        values = {str(getattr(record, field, "") or "") for record in records}
        values.discard("")
        return next(iter(values)) if len(values) == 1 else None


class ArtifactMessageLinkService:
    def link_to_message(self, artifact_id: str, message_id: str) -> ArtifactRecord:
        record = ArtifactRegistryRepository().get(artifact_id)
        if record is None:
            raise FileNotFoundError(artifact_id)
        updated = ArtifactRecord(**{**_dump_model(record), "message_id": message_id})
        ArtifactRegistryRepository().save(updated)
        return updated


class ArtifactManifestService:
    def metadata(self, artifact_id: str) -> dict[str, object]:
        record = ArtifactRegistryRepository().get(artifact_id)
        if record is None:
            return {"status": "missing", "artifact_id": artifact_id, "direct_workspace_serve_enabled": False}
        data = _dump_model(record)
        data.update({"status": "ok", "direct_workspace_serve_enabled": False, "download_path": f"/api/v1/artifacts/{artifact_id}/download"})
        return data


class ArtifactInteractionStatusService:
    def status(self) -> dict[str, object]:
        return {"status": "ok", "artifacts": len(ArtifactRegistryRepository().list()), "direct_workspace_serve_enabled": False, "zip_enabled": True, "token_required_for_download": True}
