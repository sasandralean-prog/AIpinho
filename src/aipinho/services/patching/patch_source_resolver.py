from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest


class PatchSourceResolver:
    def resolve(self, request: PatchPlanRequest) -> tuple[list[PatchEvidence], list[str], list[str]]:
        warnings: list[str] = []
        blocked: list[str] = []
        evidence = list(request.evidence)
        if not evidence and request.source_type in {"project_report", "task_run_result", "validation_result"} and request.source_id:
            evidence.append(PatchEvidence(evidence_id=f"patch_evidence_{uuid4().hex}", source_type=request.source_type, source_id=request.source_id, source_path=request.affected_files[0] if request.affected_files else None, excerpt=f"Evidence placeholder from {request.source_type}:{request.source_id}", confidence=0.5))
            warnings.append("source_evidence_placeholder_requires_review")
        if request.source_type not in {"project_report", "task_run_result", "validation_result", "role_pipeline_run", "user_request", "file_context_bundle"}:
            blocked.append("source_type_not_allowed")
        return evidence, warnings, blocked

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_source_resolver"}
