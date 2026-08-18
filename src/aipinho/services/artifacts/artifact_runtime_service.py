from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_interaction_contracts import (
    ArtifactRecord,
    UniversalArtifactCreateRequest,
)
from aipinho.schemas.artifacts.artifact_runtime import (
    ArtifactRuntimeCreateRequest,
    ArtifactRuntimeLookupResult,
    ArtifactRuntimeValidationResult,
)
from aipinho.services.artifacts.artifact_interaction_core import _safe_filename
from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.artifacts.universal_artifact_registry_service import (
    UniversalArtifactRegistryService,
)


_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
ArtifactPersistProgress = Callable[[str, dict[str, Any]], None]


class ArtifactRuntimeService:
    """Canonical runtime facade for governed artifacts.

    The service intentionally reuses the existing Universal Artifact Registry.
    It does not write to, serve from, or infer storage inside the analyzed
    workspace. Prompt paths are treated as logical paths only.
    """

    def __init__(
        self,
        *,
        registry: UniversalArtifactRegistryService | None = None,
        semantic_contracts: ArtifactSemanticContractService | None = None,
    ) -> None:
        self.registry = registry or UniversalArtifactRegistryService()
        self.semantic_contracts = semantic_contracts or ArtifactSemanticContractService()

    def create(
        self,
        request: ArtifactRuntimeCreateRequest,
        *,
        progress_observer: ArtifactPersistProgress | None = None,
    ) -> ArtifactRecord:
        self._validate_create_request(request)
        logical_path = self.normalize_logical_path(request.logical_path)
        filename = self.filename_for_logical_path(logical_path)
        artifact = self.registry.create(
            UniversalArtifactCreateRequest(
                source_agent=request.source_agent,
                filename=filename,
                logical_path=logical_path,
                artifact_type=request.artifact_type,
                producer_step=request.producer_step,
                event_id=request.event_id,
                task_id=request.task_id,
                task_run_id=request.task_run_id,
                owner_task_id=request.task_run_id or request.task_id,
                session_id=request.session_id,
                content_type=request.content_type,
                content=request.content,
                encoding=request.encoding,
                validation_status=request.validation_status,
                status=request.status,
                evidence_refs=list(request.evidence_refs),
                provenance={
                    **request.provenance,
                    "artifact_runtime": "canonical",
                    "logical_path": logical_path,
                    "storage_scope": "runtime_artifact_store",
                    "workspace_mutation": False,
                    "producer_step": request.producer_step,
                    "event_id": request.event_id,
                },
                metadata={
                    **request.metadata,
                    "logical_path": logical_path,
                    "artifact_type": request.artifact_type,
                    "producer_step": request.producer_step,
                    "event_id": request.event_id,
                    "task_id": request.task_id,
                    "task_run_id": request.task_run_id,
                    "evidence_refs": list(request.evidence_refs),
                    "storage_scope": "runtime_artifact_store",
                    "workspace_mutation": False,
                },
            ),
            progress_observer=progress_observer,
        )
        return self._ensure_runtime_fields(artifact, logical_path=logical_path)

    def can_create_from_universal_request(self, request: UniversalArtifactCreateRequest) -> bool:
        task_id = str(request.task_id or request.owner_task_id or "").strip()
        task_run_id = str(request.task_run_id or request.owner_task_id or "").strip()
        return bool(
            task_id
            and task_run_id
            and str(request.producer_step or "").strip()
            and str(request.logical_path or request.filename or "").strip()
            and request.content is not None
        )

    def create_from_universal_request(self, request: UniversalArtifactCreateRequest) -> ArtifactRecord:
        if not self.can_create_from_universal_request(request):
            raise ValueError("artifact_runtime_public_binding_required")
        task_id = str(request.task_id or request.owner_task_id)
        task_run_id = str(request.task_run_id or request.owner_task_id)
        return self.create(
            ArtifactRuntimeCreateRequest(
                logical_path=str(request.logical_path or request.filename),
                content=str(request.content or ""),
                artifact_type=request.artifact_type,
                content_type=request.content_type,
                producer_step=str(request.producer_step),
                event_id=request.event_id,
                task_id=task_id,
                task_run_id=task_run_id,
                source_agent=request.source_agent,
                session_id=request.session_id,
                validation_status=request.validation_status,
                status=request.status,
                evidence_refs=list(request.evidence_refs),
                provenance={
                    **request.provenance,
                    "public_contract_source": "UniversalArtifactCreateRequest",
                },
                metadata={
                    **request.metadata,
                    "public_contract_source": "UniversalArtifactCreateRequest",
                    "requested_filename": request.filename,
                    "bridge_task_id": request.bridge_task_id,
                },
            )
        )

    def get(self, artifact_id: str) -> dict[str, Any] | None:
        artifact = self.registry.get(artifact_id)
        if artifact is None:
            return None
        artifact.setdefault("storage_ref", artifact.get("storage_path"))
        artifact.setdefault("logical_path", (artifact.get("metadata") or {}).get("logical_path"))
        artifact.setdefault("producer_step", (artifact.get("metadata") or {}).get("producer_step"))
        artifact.setdefault("task_id", (artifact.get("metadata") or {}).get("task_id") or artifact.get("owner_task_id"))
        artifact.setdefault("task_run_id", (artifact.get("metadata") or {}).get("task_run_id") or artifact.get("owner_task_id"))
        artifact.setdefault("evidence_refs", (artifact.get("metadata") or {}).get("evidence_refs") or [])
        artifact.setdefault("reason_code", (artifact.get("metadata") or {}).get("reason_code"))
        artifact.setdefault("semantic_contract_status", (artifact.get("metadata") or {}).get("semantic_contract_status"))
        artifact.setdefault("semantic_contract_validation", (artifact.get("metadata") or {}).get("semantic_contract_validation"))
        artifact.setdefault("safe_to_use", (artifact.get("metadata") or {}).get("safe_to_use"))
        artifact.setdefault("limitations", (artifact.get("metadata") or {}).get("limitations") or [])
        artifact.setdefault("partial_rows", (artifact.get("metadata") or {}).get("partial_rows"))
        artifact.setdefault("expected_rows", (artifact.get("metadata") or {}).get("expected_rows"))
        artifact.setdefault("selected_rows", (artifact.get("metadata") or {}).get("selected_rows"))
        artifact.setdefault("bound_rows", (artifact.get("metadata") or {}).get("bound_rows"))
        artifact.setdefault("evidence_ref_count", (artifact.get("metadata") or {}).get("evidence_ref_count"))
        artifact.setdefault("evidence_refs_sample", (artifact.get("metadata") or {}).get("evidence_refs_sample") or [])
        artifact.setdefault("row_evidence_coverage", (artifact.get("metadata") or {}).get("row_evidence_coverage") or {})
        artifact.setdefault("row_validation_summary", (artifact.get("metadata") or {}).get("row_validation_summary") or {})
        artifact.setdefault("rendered_columns", (artifact.get("metadata") or {}).get("rendered_columns") or [])
        artifact.setdefault("missing_columns", (artifact.get("metadata") or {}).get("missing_columns") or [])
        return artifact

    def provenance(self, artifact_id: str) -> dict[str, Any] | None:
        return self.registry.provenance(artifact_id)

    def revalidate_public(self, artifact_id: str) -> dict[str, Any] | None:
        public = self.registry.revalidate(artifact_id)
        if public is None:
            return None
        artifact = self.get(artifact_id)
        return artifact or public

    def list_all(self, *, limit: int = 200) -> list[dict[str, Any]]:
        return self.registry.list_all(limit=limit)

    def by_agent(self, agent_id: str, *, session_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        return self.registry.by_agent(agent_id, session_id=session_id, limit=limit)

    def by_bridge_task(self, bridge_task_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        return self.registry.by_bridge_task(bridge_task_id, limit=limit)

    def validate(self, artifact_id: str) -> ArtifactRuntimeValidationResult:
        public = self.registry.revalidate(artifact_id)
        if public is None:
            return ArtifactRuntimeValidationResult(
                artifact_id=artifact_id,
                status="missing",
                validation_status="missing",
                missing_reasons=["artifact_record_missing"],
                safe_to_use_as_evidence=False,
            )
        missing: list[str] = []
        local_path = public.get("local_path")
        storage_ref = str(public.get("storage_ref") or public.get("storage_path") or "")
        path = Path(str(local_path)) if local_path else PATHS.project_root / storage_ref
        if not storage_ref:
            missing.append("storage_ref_missing")
        if not public.get("logical_path"):
            missing.append("logical_path_missing")
        if not public.get("task_id"):
            missing.append("task_id_missing")
        if not public.get("task_run_id"):
            missing.append("task_run_id_missing")
        if not public.get("producer_step"):
            missing.append("producer_step_missing")
        if not public.get("event_id"):
            missing.append("producer_event_missing")
        if not path.exists() or not path.is_file():
            missing.append("artifact_file_missing")
        elif public.get("sha256"):
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != public.get("sha256"):
                missing.append("artifact_hash_mismatch")
        semantic_validation = self.semantic_contracts.validate_artifact(public)
        semantic_profile = semantic_validation.profile
        semantic_gaps = list(semantic_validation.missing_requirements)
        missing.extend(f"artifact_semantic:{item}" for item in semantic_gaps)
        status = "passed" if public.get("status") == "ready" and not missing else "blocked"
        validation_status = "validated" if status == "passed" else "blocked"
        if public.get("validation_status") in {"missing", "stale"}:
            validation_status = str(public["validation_status"])
            missing.append(f"artifact_{public['validation_status']}")
        return ArtifactRuntimeValidationResult(
            artifact_id=artifact_id,
            status=status,
            validation_status=validation_status,
            logical_path=public.get("logical_path"),
            storage_ref=storage_ref or None,
            size_bytes=int(public.get("size_bytes") or public.get("size") or 0),
            sha256=public.get("sha256"),
            missing_reasons=list(dict.fromkeys(missing)),
            semantic_profile=semantic_profile,
            semantic_gaps=semantic_gaps,
            safe_to_use_as_evidence=status == "passed",
        )

    def by_task(self, task_id: str, *, logical_path: str | None = None, limit: int = 200) -> ArtifactRuntimeLookupResult:
        logical = self.normalize_logical_path(logical_path) if logical_path else None
        artifacts = [
            item
            for item in self.registry.by_task(task_id, limit=limit)
            if logical is None or item.get("logical_path") == logical or (item.get("metadata") or {}).get("logical_path") == logical
        ]
        return ArtifactRuntimeLookupResult(status="ok", artifacts=artifacts, count=len(artifacts))

    def normalize_logical_path(self, value: str) -> str:
        raw = str(value or "").strip().strip("\"'`")
        if not raw:
            raise ValueError("artifact_logical_path_required")
        if _DRIVE_PATH_RE.match(raw) or raw.startswith(("/", "\\")):
            raise ValueError("artifact_logical_path_must_not_be_absolute")
        normalized = raw.replace("\\", "/")
        normalized = re.sub(r"/+", "/", normalized)
        parts = [part for part in normalized.split("/") if part not in {"", "."}]
        if not parts or any(part == ".." for part in parts):
            raise ValueError("artifact_logical_path_invalid")
        return "/".join(parts)

    def filename_for_logical_path(self, logical_path: str) -> str:
        return _safe_filename(re.sub(r"[^A-Za-z0-9._-]+", "_", logical_path.replace("/", "__")))

    def _validate_create_request(self, request: ArtifactRuntimeCreateRequest) -> None:
        if not str(request.producer_step or "").strip():
            raise ValueError("artifact_producer_step_required")
        if not (str(request.task_id or "").strip() or str(request.task_run_id or "").strip()):
            raise ValueError("artifact_task_binding_required")

    def _ensure_runtime_fields(self, artifact: ArtifactRecord, *, logical_path: str) -> ArtifactRecord:
        updates: dict[str, Any] = {}
        if artifact.logical_path != logical_path:
            updates["logical_path"] = logical_path
        if not artifact.storage_ref:
            updates["storage_ref"] = artifact.storage_path
        if not artifact.task_id:
            updates["task_id"] = artifact.owner_task_id
        if not artifact.task_run_id:
            updates["task_run_id"] = artifact.owner_task_id
        if updates:
            artifact = artifact.model_copy(update=updates)
            artifact = self.registry.registry.save(artifact)
        return artifact
