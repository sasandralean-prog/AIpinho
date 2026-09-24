from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_library import ArtifactContextUseRequest
from aipinho.schemas.context.contracts import (
    ContextBuildRequest,
    ContextCandidate,
    ContextCitation,
    ContextEvidenceRef,
    ContextScope,
    ContextSourceRef,
)
from aipinho.schemas.runtime.phase_outcome import PhaseOutcome
from aipinho.services.artifacts.artifact_library_service import ArtifactLibraryService
from aipinho.services.context.context_core import (
    ContextKernelService,
    ContextPurposePolicyService,
)
from aipinho.services.context.context_plan_runtime_service import ContextPlanRuntimeService
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class MissionContextHandoffResult:
    status: str
    purpose: str | None = None
    plan_id: str | None = None
    bundle_id: str | None = None
    admitted_artifacts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MissionContextHandoffService:
    """Builds a governed child-context plan from canonical phase artifacts.

    It does not grant authority and never reads artifact storage directly.
    ArtifactLibrary materializes/sanitizes content; ContextKernel admits it.
    """

    def __init__(
        self,
        *,
        artifacts: ArtifactLibraryService | None = None,
        kernel: ContextKernelService | None = None,
        plans: ContextPlanRuntimeService | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.artifacts = artifacts or ArtifactLibraryService()
        self.kernel = kernel or ContextKernelService()
        self.plans = plans or ContextPlanRuntimeService()
        self.config_path = (
            config_path
            or PATHS.config_root / "context" / "runtime_context_handoff_policy.yaml"
        )
        self.config = load_yaml_file(
            self.config_path,
            critical=True,
            root=self.config_path.parent,
        )

    def purpose_for(
        self,
        *,
        contract_type: str | None,
        operation_type: str | None,
    ) -> str | None:
        settings = self._settings()
        if not bool(settings.get("enabled", False)):
            return None
        contract = str(contract_type or "")
        operation = str(operation_type or "")
        for binding in list(settings.get("consumer_bindings") or []):
            if not isinstance(binding, dict):
                continue
            contract_types = {
                str(item) for item in list(binding.get("contract_types") or [])
            }
            operation_types = {
                str(item) for item in list(binding.get("operation_types") or [])
            }
            if contract_types and contract not in contract_types:
                continue
            if operation_types and operation not in operation_types:
                continue
            purpose = str(binding.get("purpose") or "").strip()
            if purpose:
                return purpose
        return None

    def materialize(
        self,
        *,
        outcome: PhaseOutcome,
        purpose: str,
        child_task_id: str | None,
        child_workspace_id: str | None,
        role_id: str | None = None,
    ) -> MissionContextHandoffResult:
        settings = self._settings()
        if not bool(settings.get("enabled", False)):
            return MissionContextHandoffResult(status="disabled", purpose=purpose)
        purpose_policy = ContextPurposePolicyService()
        if not purpose_policy.known(purpose):
            return MissionContextHandoffResult(
                status="blocked",
                purpose=purpose,
                warnings=["mission_context_handoff_unknown_purpose"],
            )

        artifact_ids = self._unique(outcome.artifact_refs)
        if not artifact_ids:
            return MissionContextHandoffResult(
                status="not_applicable",
                purpose=purpose,
                warnings=["mission_context_handoff_no_artifact_refs"],
            )

        max_budget = purpose_policy.max_budget(purpose)
        layer = str(settings.get("source_layer") or "attachments_artifacts")
        source_type = str(settings.get("source_type") or "artifact_record")
        trust_level = str(settings.get("trust_level") or "cited")
        priority = max(1, int(settings.get("candidate_priority", 5) or 5))
        candidates: list[ContextCandidate] = []
        admitted_artifacts: list[str] = []
        warnings: list[str] = []

        for artifact_id in artifact_ids:
            try:
                record = self.artifacts.get(artifact_id)
            except FileNotFoundError:
                warnings.append(f"context_artifact_not_found:{artifact_id}")
                continue
            if (
                outcome.session_id
                and record.session_id
                and record.session_id != outcome.session_id
            ):
                warnings.append(f"context_artifact_session_mismatch:{artifact_id}")
                continue
            if (
                record.run_id
                and record.run_id != outcome.producer_task_run_id
            ):
                warnings.append(f"context_artifact_run_mismatch:{artifact_id}")
                continue
            try:
                materialized = self.artifacts.use_as_context(
                    ArtifactContextUseRequest(
                        artifact_id=artifact_id,
                        session_id=outcome.session_id or "mission_context_handoff",
                        sanitization_required=True,
                        max_context_bytes=max_budget,
                        metadata_sanitized={
                            "producer_task_run_id": outcome.producer_task_run_id,
                            "phase_id": outcome.phase_id,
                            "purpose": purpose,
                        },
                    )
                )
            except FileNotFoundError:
                warnings.append(f"context_artifact_not_found:{artifact_id}")
                continue
            if materialized.status != "allowed" or not materialized.context_preview:
                warnings.append(
                    f"context_artifact_not_admitted:{artifact_id}:{materialized.reason_code}"
                )
                continue

            logical_path = str(
                (record.metadata_sanitized or {}).get("logical_path")
                or record.filename
            )
            source_ref = ContextSourceRef(
                source_type=source_type,
                source_id=artifact_id,
                path=logical_path,
            )
            citation = ContextCitation(
                source_ref=source_ref,
                label=record.display_name or logical_path,
            )
            candidates.append(
                ContextCandidate(
                    layer=layer,
                    source_type=source_type,
                    source_ref=source_ref,
                    summary=record.display_name or record.filename,
                    content=materialized.context_preview,
                    priority=priority,
                    trust_level=trust_level,
                    citations=[citation],
                    evidence_refs=[
                        ContextEvidenceRef(
                            source_ref=source_ref,
                            summary=(
                                "Governed phase artifact admitted as downstream "
                                "read-only context."
                            ),
                        )
                    ],
                    metadata={
                        "producer_task_run_id": outcome.producer_task_run_id,
                        "phase_id": outcome.phase_id,
                        "artifact_id": artifact_id,
                    },
                )
            )
            admitted_artifacts.append(artifact_id)
            warnings.extend(materialized.warnings)

        if not candidates:
            return MissionContextHandoffResult(
                status="blocked",
                purpose=purpose,
                warnings=self._unique(
                    [*warnings, "mission_context_handoff_no_admissible_artifacts"]
                ),
            )

        built = self.kernel.build(
            ContextBuildRequest(
                purpose=purpose,
                scope=ContextScope(
                    session_id=outcome.session_id,
                    task_id=child_task_id,
                    workspace_id=child_workspace_id,
                    role_id=role_id,
                ),
                candidates=candidates,
                role_id=role_id,
                max_budget_chars=max_budget,
                requested_by="mission_phase_coordinator",
            )
        )
        if built.status != "ok" or not built.bundle.safe_for_prompt:
            return MissionContextHandoffResult(
                status="blocked",
                purpose=purpose,
                bundle_id=built.bundle.bundle_id,
                admitted_artifacts=admitted_artifacts,
                warnings=self._unique(
                    [*warnings, "mission_context_handoff_context_kernel_blocked"]
                ),
            )

        plan = self.kernel.injection_plan(built.bundle.bundle_id, role_id)
        self.plans.persist(plan)
        return MissionContextHandoffResult(
            status="ready",
            purpose=purpose,
            plan_id=plan.plan_id,
            bundle_id=built.bundle.bundle_id,
            admitted_artifacts=admitted_artifacts,
            warnings=self._unique(warnings),
        )

    def _settings(self) -> dict[str, Any]:
        value = self.config.get("mission_context_handoff", {})
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))
