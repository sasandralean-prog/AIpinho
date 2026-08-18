from aipinho.schemas.artifacts.artifact_interaction_contracts import (
    ArtifactRecord,
    ArtifactUploadResponse,
    ArtifactZipResponse,
    TaskRunArtifactExportRequest,
)
from aipinho.schemas.artifacts.artifact_source import ArtifactResolvedSource
from aipinho.services.artifacts.task_run_artifact_export_service import (
    TaskRunArtifactExportService,
)


class FakeSourceResolver:
    def resolve(self, source):
        return ArtifactResolvedSource(
            source=source,
            content="# Project Report\n\nObserved functionality with evidence.\n",
            format="markdown",
            status="resolved",
            validation_summary={"status": "passed"},
        )


class FakeUploadService:
    def __init__(self):
        self.request = None

    def upload(self, request):
        self.request = request
        return ArtifactUploadResponse(
            artifact=ArtifactRecord(
                artifact_id="artifact_summary",
                filename=request.filename,
                content_type=request.content_type,
                size_bytes=len(request.content.encode("utf-8")),
                sha256="a" * 64,
                storage_path=f"data/artifacts/chat/{request.filename}",
                metadata=request.metadata,
            ),
            download_path="/api/v1/artifacts/artifact_summary/download",
        )


class FakeZipService:
    def __init__(self):
        self.request = None

    def create(self, request):
        self.request = request
        return ArtifactZipResponse(
            artifact=ArtifactRecord(
                artifact_id="artifact_zip",
                filename=request.filename,
                content_type="application/zip",
                size_bytes=128,
                sha256="b" * 64,
                storage_path=f"data/artifacts/zips/{request.filename}",
                metadata={"included_artifacts": request.artifact_ids},
            ),
            included_artifacts=request.artifact_ids,
            download_path="/api/v1/artifacts/artifact_zip/download",
        )


def test_task_run_export_creates_internal_summary_and_zip_without_workspace_write():
    upload = FakeUploadService()
    zipper = FakeZipService()
    service = TaskRunArtifactExportService(
        source_resolver=FakeSourceResolver(),
        upload_service=upload,
        zip_service=zipper,
    )

    result = service.export(
        "task_run_test",
        TaskRunArtifactExportRequest(),
    )

    assert result.summary_artifact.filename == "artifact.txt"
    assert result.zip_artifact.filename == "artifacts.zip"
    assert result.zip_download_path == "/api/v1/artifacts/artifact_zip/download"
    assert upload.request.content.startswith("# Project Report")
    assert upload.request.metadata["source_type"] == "task_run_result"
    assert zipper.request.artifact_ids == ["artifact_summary"]
    assert service.status()["workspace_write_enabled"] is False


def test_task_run_export_uses_requested_filenames_without_case_specific_defaults():
    upload = FakeUploadService()
    zipper = FakeZipService()
    service = TaskRunArtifactExportService(
        source_resolver=FakeSourceResolver(),
        upload_service=upload,
        zip_service=zipper,
    )

    result = service.export(
        "task_run_test",
        TaskRunArtifactExportRequest(summary_filename="diagnostico.txt", zip_filename="pacote.zip"),
    )

    assert result.summary_artifact.filename == "diagnostico.txt"
    assert result.zip_artifact.filename == "pacote.zip"


def test_task_run_export_rejects_unvalidated_source():
    class BlockedSourceResolver:
        def resolve(self, source):
            return ArtifactResolvedSource(
                source=source,
                content="",
                status="blocked",
                blocked_reasons=["task_run_result_validation_missing"],
            )

    service = TaskRunArtifactExportService(source_resolver=BlockedSourceResolver())

    try:
        service.export("task_run_test", TaskRunArtifactExportRequest())
    except ValueError as exc:
        assert str(exc) == "task_run_result_validation_missing"
    else:
        raise AssertionError("unvalidated task result must not be exported")
