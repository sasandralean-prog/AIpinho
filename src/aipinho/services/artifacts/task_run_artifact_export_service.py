from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_interaction_contracts import (
    ArtifactUploadRequest,
    ArtifactZipRequest,
    TaskRunArtifactExportRequest,
    TaskRunArtifactExportResponse,
)
from aipinho.schemas.artifacts.artifact_source import ArtifactSource
from aipinho.services.artifacts.artifact_interaction_core import ArtifactUploadService, ArtifactZipService
from aipinho.services.artifacts.artifact_source_resolver import ArtifactSourceResolver
from aipinho.utils.yaml_loader import load_yaml_file


class TaskRunArtifactExportService:
    def __init__(
        self,
        source_resolver: ArtifactSourceResolver | None = None,
        upload_service: ArtifactUploadService | None = None,
        zip_service: ArtifactZipService | None = None,
    ) -> None:
        self.source_resolver = source_resolver or ArtifactSourceResolver()
        self.upload_service = upload_service or ArtifactUploadService()
        self.zip_service = zip_service or ArtifactZipService()
        self.policy = load_yaml_file(
            PATHS.config_root / "artifacts" / "task_run_export_policy.yaml",
            critical=True,
            root=PATHS.config_root / "artifacts",
        )

    def export(
        self,
        run_id: str,
        request: TaskRunArtifactExportRequest,
    ) -> TaskRunArtifactExportResponse:
        source = self.source_resolver.resolve(
            ArtifactSource(
                source_type="task_run_result",
                source_id=run_id,
                format="markdown",
            )
        )
        if source.status != "resolved" or source.blocked_reasons:
            reason = source.blocked_reasons[0] if source.blocked_reasons else "task_run_source_unavailable"
            raise ValueError(reason)
        summary_filename = self._filename(request.summary_filename, "text_filename")
        zip_filename = self._filename(request.zip_filename, "package_filename")
        summary = self.upload_service.upload(
            ArtifactUploadRequest(
                filename=summary_filename,
                content=source.content,
                content_type="text/plain; charset=utf-8",
                metadata={
                    "source_type": "task_run_result",
                    "source_id": run_id,
                    "validation_summary": source.validation_summary,
                },
            )
        )
        zipped = self.zip_service.create(
            ArtifactZipRequest(
                artifact_ids=[summary.artifact.artifact_id],
                filename=zip_filename,
            )
        )
        return TaskRunArtifactExportResponse(
            run_id=run_id,
            summary_artifact=summary.artifact,
            zip_artifact=zipped.artifact,
            summary_download_path=summary.download_path,
            zip_download_path=zipped.download_path,
        )

    def _filename(self, requested: str | None, default_key: str) -> str:
        value = (requested or "").strip()
        if value:
            return value
        defaults = self.policy.get("defaults", {}) if isinstance(self.policy.get("defaults", {}), dict) else {}
        configured = str(defaults.get(default_key) or "").strip()
        if configured:
            return configured
        return "artifact.txt" if default_key == "text_filename" else "artifacts.zip"

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "task_run_artifact_export",
            "workspace_write_enabled": False,
            "requires_validated_task_result": True,
        }
