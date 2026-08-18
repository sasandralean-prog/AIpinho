from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_generation import ArtifactGenerationResult, ArtifactRequest
from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactZipRequest, UniversalArtifactCreateRequest
from aipinho.services.artifacts.artifact_interaction_core import _safe_filename
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.events.event_core import contains_secret, redact_payload


CONTENT_TYPES = {
    "markdown_report": "text/markdown",
    "text_export": "text/plain",
    "json_export": "application/json",
    "zip_evidence": "application/zip",
    "patch_diff": "text/x-diff",
    "build_log": "text/plain",
    "test_log": "text/plain",
    "apk": "application/vnd.android.package-archive",
    "jar": "application/java-archive",
    "generic_file": "application/octet-stream",
}

TEXT_TYPES = {"markdown_report", "text_export", "json_export", "patch_diff", "build_log", "test_log"}
PACKAGE_TYPES = {"zip_evidence"}
FILE_TYPES = {"apk", "jar", "generic_file"}
SECRET_ASSIGNMENT_PATTERN = re.compile(r"(?i)(api[_-]?key|token|secret|password|credential)\s*[:=]\s*\S+")


class ArtifactGeneratorService:
    def __init__(self, registry: UniversalArtifactRegistryService | None = None) -> None:
        self.registry = registry or UniversalArtifactRegistryService()

    def generate(self, request: ArtifactRequest) -> ArtifactGenerationResult:
        try:
            return self._generate(request)
        except ValueError as exc:
            return self._blocked(request, str(exc))
        except FileNotFoundError as exc:
            return self._failed(request, f"source_not_found:{exc}")
        except Exception as exc:
            return self._failed(request, exc.__class__.__name__)

    def package_evidence(self, artifact_id: str, *, filename: str | None = None) -> ArtifactGenerationResult:
        artifact = self.registry.get(artifact_id)
        if artifact is None:
            raise FileNotFoundError(artifact_id)
        request = ArtifactRequest(
            source_agent=str(artifact.get("source_agent") or "aipinho"),
            owner_task_id=artifact.get("owner_task_id"),
            bridge_task_id=artifact.get("bridge_task_id"),
            artifact_type="zip_evidence",
            requested_filename=filename or f"{artifact_id}_evidence.zip",
            content_source="artifact_refs",
            source_paths=[],
            metadata={"included_artifact_id": artifact_id},
        )
        try:
            zipped = self.registry.create_zip(ArtifactZipRequest(artifact_ids=[artifact_id], filename=request.requested_filename))
        except AttributeError:
            from aipinho.services.artifacts.artifact_interaction_core import ArtifactZipService

            zipped = ArtifactZipService().create(ArtifactZipRequest(artifact_ids=[artifact_id], filename=request.requested_filename))
        return self._result_from_artifact(request, zipped.artifact.model_dump() if hasattr(zipped.artifact, "model_dump") else zipped.artifact)

    def _generate(self, request: ArtifactRequest) -> ArtifactGenerationResult:
        self._validate_request(request)
        filename = _safe_filename(request.requested_filename)
        if request.artifact_type in TEXT_TYPES:
            content = self._text_content(request)
            artifact = self.registry.create(
                UniversalArtifactCreateRequest(
                    source_agent=request.source_agent,
                    filename=filename,
                    content_type=CONTENT_TYPES[request.artifact_type],
                    content=content,
                    owner_task_id=request.owner_task_id,
                    bridge_task_id=request.bridge_task_id,
                    session_id=request.source_chat_id,
                    validation_status="validated" if request.requires_validation else "not_required",
                    status="ready",
                    provenance=self._provenance(request),
                    metadata={
                        "artifact_request_id": request.artifact_request_id,
                        "artifact_type": request.artifact_type,
                        "executor_agent": request.source_agent,
                        "user_visible": request.user_visible,
                    },
                    visible_to_agent_ids=[request.source_agent, "aipinho"],
                )
            )
            return self._result_from_artifact(request, artifact.model_dump())
        if request.artifact_type in PACKAGE_TYPES:
            return self._zip_from_paths(request, filename)
        if request.artifact_type in FILE_TYPES:
            return self._file_from_path(request, filename)
        raise ValueError("unsupported_artifact_type")

    def _validate_request(self, request: ArtifactRequest) -> None:
        if not request.source_agent.strip():
            raise ValueError("source_agent_required")
        if ".." in Path(request.requested_filename).parts:
            raise ValueError("artifact_generator_path_traversal_blocked")
        if request.content_inline and self._contains_secret(request.content_inline):
            raise ValueError("secret_detected_in_artifact_content")
        if self._contains_secret(request.metadata):
            raise ValueError("secret_detected_in_artifact_metadata")

    def _text_content(self, request: ArtifactRequest) -> str:
        if request.content_inline is not None:
            content = request.content_inline
        elif request.content_source == "metadata":
            content = json.dumps(redact_payload(request.metadata), ensure_ascii=True, indent=2)
        else:
            raise ValueError("artifact_text_content_required")
        if request.artifact_type == "json_export":
            json.loads(content)
        if request.requires_validation and not content.strip():
            raise ValueError("ready_artifact_must_have_non_empty_file")
        return content

    def _zip_from_paths(self, request: ArtifactRequest, filename: str) -> ArtifactGenerationResult:
        paths = self._source_files(request)
        if not paths:
            raise ValueError("zip_evidence_requires_source_paths")
        zip_root = PATHS.project_root / "data" / "artifacts" / "generated"
        zip_root.mkdir(parents=True, exist_ok=True)
        if not filename.lower().endswith(".zip"):
            filename = f"{filename}.zip"
        local_zip = zip_root / f"{request.artifact_request_id}_{filename}"
        with zipfile.ZipFile(local_zip, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in paths:
                bundle.write(path, arcname=path.name)
        self._validate_zip(local_zip)
        artifact = self.registry.create(
            UniversalArtifactCreateRequest(
                source_agent=request.source_agent,
                filename=filename,
                content_type="application/zip",
                local_path=str(local_zip),
                owner_task_id=request.owner_task_id,
                bridge_task_id=request.bridge_task_id,
                session_id=request.source_chat_id,
                validation_status="validated",
                status="ready",
                provenance={**self._provenance(request), "source_paths": [path.name for path in paths]},
                metadata={"artifact_request_id": request.artifact_request_id, "artifact_type": request.artifact_type},
            )
        )
        return self._result_from_artifact(request, artifact.model_dump())

    def _file_from_path(self, request: ArtifactRequest, filename: str) -> ArtifactGenerationResult:
        paths = self._source_files(request)
        if len(paths) != 1:
            raise ValueError("single_source_file_required")
        artifact = self.registry.create(
            UniversalArtifactCreateRequest(
                source_agent=request.source_agent,
                filename=filename,
                content_type=CONTENT_TYPES[request.artifact_type],
                local_path=str(paths[0]),
                owner_task_id=request.owner_task_id,
                bridge_task_id=request.bridge_task_id,
                session_id=request.source_chat_id,
                validation_status="validated",
                status="ready",
                provenance=self._provenance(request),
                metadata={"artifact_request_id": request.artifact_request_id, "artifact_type": request.artifact_type},
            )
        )
        return self._result_from_artifact(request, artifact.model_dump())

    def _source_files(self, request: ArtifactRequest) -> list[Path]:
        root = Path(request.workspace).resolve() if request.workspace else PATHS.project_root.resolve()
        files: list[Path] = []
        for raw in request.source_paths:
            path = Path(raw)
            resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
            if not str(resolved).startswith(str(root)):
                raise ValueError("artifact_generator_path_traversal_blocked")
            if not resolved.exists() or not resolved.is_file():
                raise FileNotFoundError(resolved)
            if resolved.stat().st_size <= 0:
                raise ValueError("ready_artifact_must_have_non_empty_file")
            files.append(resolved)
        return files

    def _validate_zip(self, path: Path) -> None:
        if not path.exists() or path.stat().st_size <= 0:
            raise ValueError("zip_artifact_empty_or_missing")
        with zipfile.ZipFile(path, "r") as bundle:
            if not bundle.namelist():
                raise ValueError("zip_artifact_has_no_entries")

    def _result_from_artifact(self, request: ArtifactRequest, artifact: dict[str, Any]) -> ArtifactGenerationResult:
        size = int(artifact.get("size_bytes") or artifact.get("size") or 0)
        status = "READY" if artifact.get("status") == "ready" and size > 0 else "READY_WITH_WARNINGS"
        if request.requires_validation and size <= 0:
            status = "FAILED"
        return ArtifactGenerationResult(
            artifact_request_id=request.artifact_request_id,
            artifact_id=str(artifact.get("artifact_id") or ""),
            status=status,
            source_agent=request.source_agent,
            executor_agent=str((artifact.get("provenance") or {}).get("executor_agent") or request.source_agent),
            filename=str(artifact.get("filename") or request.requested_filename),
            local_path=artifact.get("local_path"),
            content_type=artifact.get("content_type"),
            size_bytes=size,
            validation_status=str(artifact.get("validation_status") or "unknown"),
            validation_errors=[] if status != "FAILED" else ["artifact_validation_failed"],
            artifact_refs=[artifact],
            provenance=artifact.get("provenance") or {},
            download_endpoint=artifact.get("download_endpoint"),
            requires_token=bool(artifact.get("requires_token", True)),
        )

    def _provenance(self, request: ArtifactRequest) -> dict[str, Any]:
        return redact_payload(
            {
                "artifact_request_id": request.artifact_request_id,
                "source_agent": request.source_agent,
                "executor_agent": request.source_agent,
                "source_chat_id": request.source_chat_id,
                "owner_task_id": request.owner_task_id,
                "bridge_task_id": request.bridge_task_id,
                "workspace": request.workspace,
                "content_source": request.content_source,
            }
        )

    def _contains_secret(self, value: Any) -> bool:
        if contains_secret(value):
            return True
        text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, tuple)) else str(value)
        return bool(SECRET_ASSIGNMENT_PATTERN.search(text))

    def _blocked(self, request: ArtifactRequest, reason: str) -> ArtifactGenerationResult:
        return ArtifactGenerationResult(
            artifact_request_id=request.artifact_request_id,
            status="BLOCKED",
            source_agent=request.source_agent,
            executor_agent=request.source_agent,
            filename=request.requested_filename,
            validation_status="blocked",
            validation_errors=[reason],
            provenance=self._provenance(request),
        )

    def _failed(self, request: ArtifactRequest, reason: str) -> ArtifactGenerationResult:
        return ArtifactGenerationResult(
            artifact_request_id=request.artifact_request_id,
            status="FAILED",
            source_agent=request.source_agent,
            executor_agent=request.source_agent,
            filename=request.requested_filename,
            validation_status="failed",
            validation_errors=[reason],
            provenance=self._provenance(request),
        )
