from __future__ import annotations

from typing import Any

from aipinho.schemas.memory.memory_candidate import MemoryCandidateSource


class MemoryCandidateSourceResolver:
    TRUSTED_SOURCES = {"project_report", "task_run_result", "validation_result", "patch_apply_result", "user_instruction", "manual_payload"}

    def resolve(self, source: MemoryCandidateSource | None, *, metadata: dict[str, Any] | None = None) -> MemoryCandidateSource:
        if source is not None:
            return MemoryCandidateSource(
                source_type=source.source_type,
                source_id=source.source_id,
                source_ref=source.source_ref or source.source_id or source.source_type,
                source_payload=source.source_payload,
                trusted=source.trusted or source.source_type in self.TRUSTED_SOURCES,
            )
        metadata = metadata or {}
        source_type = str(metadata.get("source_type") or "")
        source_id = metadata.get("source_id")
        return MemoryCandidateSource(source_type=source_type, source_id=source_id, source_ref=source_id or source_type or None, source_payload=dict(metadata.get("source_payload") or {}), trusted=source_type in self.TRUSTED_SOURCES)

    def from_project_report(self, report_id: str) -> tuple[MemoryCandidateSource, dict[str, Any] | None]:
        from aipinho.services.reports.project_report_service import ProjectReportService

        report = ProjectReportService().get_report(report_id)
        payload = report.model_dump() if hasattr(report, "model_dump") else (report.dict() if report else None)
        return MemoryCandidateSource(source_type="project_report", source_id=report_id, source_ref=f"report:{report_id}", source_payload={}, trusted=report is not None), payload

    def from_task_run(self, run_id: str) -> tuple[MemoryCandidateSource, dict[str, Any] | None]:
        from aipinho.services.runtime.task_runtime_service import TaskRuntimeService

        result = TaskRuntimeService().get_result(run_id)
        payload = result.model_dump() if hasattr(result, "model_dump") else (result.dict() if result else None)
        return MemoryCandidateSource(source_type="task_run_result", source_id=run_id, source_ref=f"task_run:{run_id}", source_payload={}, trusted=result is not None), payload

    def from_validation(self, validation_id: str) -> tuple[MemoryCandidateSource, dict[str, Any] | None]:
        from aipinho.services.validation.validation_gate_service import ValidationGateService

        result = ValidationGateService().get_result(validation_id)
        payload = result.model_dump() if hasattr(result, "model_dump") else (result.dict() if result else None)
        return MemoryCandidateSource(source_type="validation_result", source_id=validation_id, source_ref=f"validation:{validation_id}", source_payload={}, trusted=result is not None), payload

    def from_patch_apply(self, apply_run_id: str) -> tuple[MemoryCandidateSource, dict[str, Any] | None]:
        from aipinho.services.patching.apply.patch_apply_service import PatchApplyService

        result = PatchApplyService().get_result(apply_run_id)
        payload = result.model_dump() if hasattr(result, "model_dump") else (result.dict() if result else None)
        return MemoryCandidateSource(source_type="patch_apply_result", source_id=apply_run_id, source_ref=f"patch_apply:{apply_run_id}", source_payload={}, trusted=result is not None), payload
