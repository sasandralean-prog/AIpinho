from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import zipfile
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_interaction_contracts import (
    ArtifactPathArchiveRequest,
    ArtifactPathArchiveResponse,
    ArtifactPathArchiveSkippedPath,
    ArtifactRecord,
)
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.events.event_core import EventPublisherService, contains_secret
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactPathArchiveService:
    """Creates governed ZIP artifacts from explicit local file and directory paths."""

    def __init__(
        self,
        policy: dict[str, Any] | None = None,
        registry: ArtifactRegistryRepository | None = None,
        workspace_policy: WorkspacePolicyService | None = None,
        secret_guard: SecretGuardService | None = None,
    ) -> None:
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "artifacts" / "path_archive_policy.yaml",
            critical=True,
            root=PATHS.config_root / "artifacts",
        )
        self.registry = registry or ArtifactRegistryRepository()
        self.workspace_policy = workspace_policy or WorkspacePolicyService().load()
        self.secret_guard = secret_guard or SecretGuardService()

    @property
    def settings(self) -> dict[str, Any]:
        value = self.policy.get("path_archive", {})
        return value if isinstance(value, dict) else {}

    def create(self, request: ArtifactPathArchiveRequest) -> ArtifactPathArchiveResponse:
        if not self.settings.get("enabled", True):
            raise ValueError("path_archive_disabled")
        source_paths = [str(item).strip() for item in request.source_paths if str(item).strip()]
        if not source_paths:
            raise ValueError("archive_source_path_required")

        filename = self._safe_zip_filename(request.filename)
        included: list[tuple[Path, str]] = []
        skipped: list[ArtifactPathArchiveSkippedPath] = []
        warnings: list[str] = []
        total_bytes = 0
        max_files = int(self.settings.get("max_files", 20000))
        max_total_bytes = int(self.settings.get("max_total_bytes", 536870912))
        max_file_bytes = int(self.settings.get("max_file_bytes", 104857600))

        used_arcnames: set[str] = set()
        source_roots = [Path(item).expanduser().resolve(strict=False) for item in source_paths]
        root_labels = self._root_labels(source_roots)
        for source, root_label in zip(source_roots, root_labels, strict=False):
            if not source.exists():
                skipped.append(self._skip(source, "source_not_found"))
                continue
            if self._path_block_reason(source):
                skipped.append(self._skip(source, self._path_block_reason(source) or "path_blocked"))
                continue
            if source.is_file():
                total_bytes = self._maybe_add_file(
                    source,
                    self._unique_arcname(root_label, used_arcnames),
                    included,
                    skipped,
                    total_bytes,
                    max_file_bytes,
                    max_total_bytes,
                    max_files,
                )
                continue
            if not source.is_dir():
                skipped.append(self._skip(source, "unsupported_source_type"))
                continue
            for child in source.rglob("*"):
                if len(included) >= max_files:
                    warnings.append("archive_file_limit_reached")
                    break
                if child.is_dir():
                    continue
                if self._should_skip_inside_archive(child, source):
                    skipped.append(self._skip(child, "excluded_by_archive_policy"))
                    continue
                try:
                    relative = child.relative_to(source)
                except ValueError:
                    skipped.append(self._skip(child, "path_not_under_source_root"))
                    continue
                arcname = self._unique_arcname(f"{root_label}/{relative.as_posix()}", used_arcnames)
                total_bytes = self._maybe_add_file(
                    child,
                    arcname,
                    included,
                    skipped,
                    total_bytes,
                    max_file_bytes,
                    max_total_bytes,
                    max_files,
                )
                if total_bytes >= max_total_bytes:
                    warnings.append("archive_total_size_limit_reached")
                    break

        if not included:
            if self.settings.get("block_if_no_allowed_files", True):
                raise ValueError("archive_no_allowed_files")
            warnings.append("archive_created_without_files")

        store_subdir = str(self.settings.get("store_subdir") or "path_archives").strip() or "path_archives"
        store_root = PATHS.project_root / "data" / "artifacts" / store_subdir
        store_root.mkdir(parents=True, exist_ok=True)
        digest_source = "|".join([str(path) for path, _ in included]) + "|" + filename
        path = store_root / f"archive_{hashlib.sha256(digest_source.encode('utf-8')).hexdigest()[:12]}_{filename}"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for source_file, arcname in included:
                bundle.write(source_file, arcname=arcname)
        content = path.read_bytes()
        record = ArtifactRecord(
            filename=filename,
            content_type="application/zip",
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_path=str(path.relative_to(PATHS.project_root)),
            metadata={
                "source_type": "filesystem_archive",
                "operation_id": request.operation_id,
                "source_path_count": len(source_paths),
                "source_labels": root_labels,
                "included_count": len(included),
                "skipped_count": len(skipped),
                "total_source_bytes": total_bytes,
                "warnings": warnings,
            },
        )
        self.registry.save(record)
        self._publish_archive_event(record, len(included), len(skipped), request.operation_id)
        return ArtifactPathArchiveResponse(
            artifact=record,
            download_path=f"/api/v1/artifacts/{record.artifact_id}/download",
            included_paths=[arcname for _, arcname in included],
            skipped_paths=skipped,
            warnings=list(dict.fromkeys(warnings)),
        )

    def _maybe_add_file(
        self,
        source: Path,
        arcname: str,
        included: list[tuple[Path, str]],
        skipped: list[ArtifactPathArchiveSkippedPath],
        total_bytes: int,
        max_file_bytes: int,
        max_total_bytes: int,
        max_files: int,
    ) -> int:
        if len(included) >= max_files:
            skipped.append(self._skip(source, "archive_file_limit_reached"))
            return total_bytes
        if self._should_skip_file(source):
            skipped.append(self._skip(source, "excluded_by_archive_policy"))
            return total_bytes
        size = source.stat().st_size
        if size > max_file_bytes:
            skipped.append(self._skip(source, "file_size_limit_exceeded"))
            return total_bytes
        if total_bytes + size > max_total_bytes:
            skipped.append(self._skip(source, "archive_total_size_limit_exceeded"))
            return total_bytes
        if self._contains_secret_content(source):
            skipped.append(self._skip(source, "secret_content_detected"))
            return total_bytes
        included.append((source, arcname.replace("\\", "/")))
        return total_bytes + size

    def _root_labels(self, sources: list[Path]) -> list[str]:
        counts: dict[str, int] = {}
        labels: list[str] = []
        for source in sources:
            base = self._safe_arc_part(source.name or source.stem or "source")
            counts[base] = counts.get(base, 0) + 1
            labels.append(base if counts[base] == 1 else f"{base}_{counts[base]}")
        return labels

    def _unique_arcname(self, arcname: str, used: set[str]) -> str:
        normalized = "/".join(self._safe_arc_part(part) for part in arcname.replace("\\", "/").split("/") if part)
        candidate = normalized or "file"
        if candidate not in used:
            used.add(candidate)
            return candidate
        path = Path(candidate)
        stem = path.stem or "file"
        suffix = path.suffix
        parent = str(path.parent).replace("\\", "/")
        index = 2
        while True:
            name = f"{stem}_{index}{suffix}"
            deduped = f"{parent}/{name}" if parent and parent != "." else name
            if deduped not in used:
                used.add(deduped)
                return deduped
            index += 1

    def _safe_arc_part(self, value: str) -> str:
        part = re.sub(r"[^A-Za-z0-9._ -]", "_", value).strip(" .")
        return part or "item"

    def _safe_zip_filename(self, filename: str) -> str:
        name = Path(filename).name.strip()
        if not name:
            name = str(self.settings.get("default_filename") or "paths.zip")
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        if not name.lower().endswith(".zip"):
            name = f"{name}.zip"
        if name in {".zip", "..zip"}:
            raise ValueError("invalid_archive_filename")
        return name

    def _path_block_reason(self, path: Path) -> str | None:
        raw = str(path)
        if raw.startswith("\\\\") or raw.startswith("//"):
            return "unc_path_blocked"
        if raw.startswith("\\\\.") or raw.startswith("\\\\?"):
            return "device_path_blocked"
        if self.workspace_policy.evaluate(workspace_path=raw, requires_workspace=True).blocked:
            return "protected_root"
        if self._is_secret_path(path):
            return "secret_path"
        return None

    def _should_skip_inside_archive(self, path: Path, root: Path) -> bool:
        if path.is_symlink():
            return True
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            return True
        excluded_dirs = {str(item).lower() for item in self.settings.get("excluded_directories", []) or []}
        return any(part.lower() in excluded_dirs for part in relative_parts[:-1])

    def _should_skip_file(self, path: Path) -> bool:
        if path.is_symlink() or not path.is_file():
            return True
        if self._is_secret_path(path):
            return True
        blocked_exts = {str(item).lower() for item in self.settings.get("blocked_extensions", []) or []}
        if path.suffix.lower() in blocked_exts:
            return True
        name = path.name.lower()
        for pattern in self.settings.get("excluded_globs", []) or []:
            if fnmatch.fnmatch(name, str(pattern).lower()):
                return True
        return False

    def _is_secret_path(self, path: Path) -> bool:
        name = path.name.lower()
        patterns = [*self.secret_guard.filename_patterns(), *[str(item) for item in self.settings.get("secret_filename_patterns", []) or []]]
        return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in patterns)

    def _contains_secret_content(self, path: Path) -> bool:
        scan_exts = {str(item).lower() for item in self.settings.get("content_secret_scan_extensions", []) or []}
        if path.suffix.lower() not in scan_exts:
            return False
        max_scan = int(self.settings.get("content_secret_scan_max_bytes", 1048576))
        if path.stat().st_size > max_scan:
            return False
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return False
        return contains_secret(text) or bool(self.secret_guard.redact(text)[1])

    def _skip(self, path: Path, reason: str) -> ArtifactPathArchiveSkippedPath:
        return ArtifactPathArchiveSkippedPath(path=str(path), reason=reason)

    def _publish_archive_event(self, record: ArtifactRecord, included_count: int, skipped_count: int, operation_id: str | None) -> None:
        try:
            EventPublisherService().publish(EventPublishRequest(
                event_type="artifact_zip_created",
                source_service="artifact_service",
                human_summary=f"ZIP de paths criado: {record.filename}",
                payload={
                    "artifact_id": record.artifact_id,
                    "filename": record.filename,
                    "included_count": included_count,
                    "skipped_count": skipped_count,
                    "operation_id": operation_id,
                },
            ))
        except Exception:
            return
