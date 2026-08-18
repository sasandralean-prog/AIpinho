from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import time
import traceback
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.artifacts.artifact_runtime import ArtifactRuntimeCreateRequest
from aipinho.schemas.chat.chat_response import ChatArtifactLink, ChatResponse
from aipinho.schemas.runtime.task_completion import (
    TaskCompletionCriterion,
    TaskCompletionEvaluation,
)
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.patching.repair_proposal_artifact import RepairProposalArtifact
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.artifacts.contract_driven_perception_service import ContractDrivenPerceptionService
from aipinho.services.artifacts.media_inventory_sufficiency_service import MediaInventorySufficiencyService
from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.artifacts.row_level_semantic_validation_service import RowLevelSemanticValidationService
from aipinho.services.artifacts.semantic_artifact_intent_resolver import SemanticArtifactIntentResolver
from aipinho.services.artifacts.semantic_entity_selection_service import SemanticEntitySelectionService
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.cvl.cognitive_readiness_service import CognitiveReadinessService
from aipinho.services.governance.lifecycle.governance_lifecycle_service import (
    GovernanceLifecycleService,
)
from aipinho.services.patching.model_assisted_patch_planner_service import ModelAssistedPatchPlannerService
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.phase_semantic_completion_policy import (
    PhaseCompletionDecision,
    PhaseSemanticCompletionPolicy,
)
from aipinho.services.session.session_store import utc_now


_ARTIFACT_PATH_RE = re.compile(
    r"(?<![A-Za-z]:)(?P<path>(?:[A-Za-z0-9_.-]+[\\/])+[A-Za-z0-9_. -]+"
    r"\.(?:md|json|txt|csv|html|yaml|yml|zip))",
    re.IGNORECASE,
)
_PHASE_RE = re.compile(r"\b(?:fase|phase)\s*(?P<phase>[0-9]+[A-Za-z]?)\b", re.IGNORECASE)
_PUBLIC_BOUNDARY_THREADS: list[Thread] = []
_PUBLIC_BOUNDARY_GUARD_THREADS: list[Thread] = []
_MEDIA_INVENTORY_STAGE_STALL_REASONS: dict[str, str] = {
    "after_entity_selection": "MUSIC_INVENTORY_PERCEPTION_PAYLOAD_COMPILE_STALLED",
    "before_perception_payload_compile": "MUSIC_INVENTORY_PERCEPTION_PAYLOAD_COMPILE_STALLED",
    "before_compile_request_normalization": "PERCEPTION_PAYLOAD_COMPILE_BUDGET_EXCEEDED",
    "after_compile_request_normalization": "PERCEPTION_REQUIREMENT_RESOLUTION_STALLED",
    "before_requirement_resolution": "PERCEPTION_REQUIREMENT_RESOLUTION_STALLED",
    "after_requirement_resolution": "PERCEPTION_ENTITY_PROJECTION_STALLED",
    "before_entity_projection": "PERCEPTION_ENTITY_PROJECTION_STALLED",
    "entity_projection_checkpoint": "PERCEPTION_ENTITY_PROJECTION_STALLED",
    "after_entity_projection": "PERCEPTION_RELATIONSHIP_PROJECTION_STALLED",
    "before_relationship_projection": "PERCEPTION_RELATIONSHIP_PROJECTION_STALLED",
    "after_relationship_projection": "PERCEPTION_OBSERVATION_BINDING_STALLED",
    "before_observation_binding": "PERCEPTION_OBSERVATION_BINDING_STALLED",
    "before_observation_goal_projection": "PERCEPTION_OBSERVATION_GOAL_PROJECTION_STALLED",
    "after_observation_goal_projection": "PERCEPTION_OBSERVATION_STRATEGY_PROJECTION_STALLED",
    "before_observation_strategy_projection": "PERCEPTION_OBSERVATION_STRATEGY_PROJECTION_STALLED",
    "after_observation_strategy_projection": "PERCEPTION_CAPABILITY_MATCH_PROJECTION_STALLED",
    "before_capability_match_projection": "PERCEPTION_CAPABILITY_MATCH_PROJECTION_STALLED",
    "after_capability_match_projection": "PERCEPTION_CAPABILITY_DECISION_PROJECTION_STALLED",
    "before_capability_decision_projection": "PERCEPTION_CAPABILITY_DECISION_PROJECTION_STALLED",
    "after_capability_decision_projection": "PERCEPTION_OBSERVATION_TASK_PROJECTION_STALLED",
    "before_observation_task_projection": "PERCEPTION_OBSERVATION_TASK_PROJECTION_STALLED",
    "after_observation_task_projection": "PERCEPTION_OBSERVATION_REQUIREMENT_PROJECTION_STALLED",
    "before_observation_requirement_projection": "PERCEPTION_OBSERVATION_REQUIREMENT_PROJECTION_STALLED",
    "after_observation_requirement_projection": "PERCEPTION_OBSERVATION_BINDING_STALLED",
    "after_observation_binding": "PERCEPTION_FACT_PROJECTION_STALLED",
    "before_fact_projection": "PERCEPTION_FACT_PROJECTION_STALLED",
    "before_fact_source_binding": "PERCEPTION_FACT_SOURCE_BINDING_STALLED",
    "before_source_index_build": "PERCEPTION_FACT_SOURCE_BINDING_STALLED",
    "after_source_index_build": "PERCEPTION_ATTRIBUTE_OBSERVATION_PROJECTION_STALLED",
    "before_attribute_observation_projection": "PERCEPTION_ATTRIBUTE_OBSERVATION_PROJECTION_STALLED",
    "attribute_observation_projection_checkpoint": "PERCEPTION_ATTRIBUTE_OBSERVATION_PROJECTION_STALLED",
    "after_attribute_observation_projection": "PERCEPTION_EVIDENCE_REF_RESOLUTION_STALLED",
    "before_evidence_ref_resolution": "PERCEPTION_EVIDENCE_REF_RESOLUTION_STALLED",
    "after_evidence_ref_resolution": "PERCEPTION_EVIDENCE_SET_MATERIALIZATION_STALLED",
    "before_evidence_set_materialization": "PERCEPTION_EVIDENCE_SET_MATERIALIZATION_STALLED",
    "evidence_set_materialization_checkpoint": "PERCEPTION_EVIDENCE_SET_MATERIALIZATION_STALLED",
    "after_evidence_set_materialization": "PERCEPTION_SOURCE_PROVENANCE_BINDING_STALLED",
    "before_source_provenance_binding": "PERCEPTION_SOURCE_PROVENANCE_BINDING_STALLED",
    "after_source_provenance_binding": "PERCEPTION_SOURCE_BINDING_BOUND_CHECK_STALLED",
    "before_source_binding_bound_check": "PERCEPTION_SOURCE_BINDING_BOUND_CHECK_STALLED",
    "after_source_binding_bound_check": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "fact_source_binding_completed": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "after_fact_source_binding": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "before_fact_candidate_projection": "PERCEPTION_FACT_CANDIDATE_PROJECTION_STALLED",
    "after_fact_candidate_projection": "PERCEPTION_FACT_DERIVATION_STALLED",
    "before_fact_derivation": "PERCEPTION_FACT_DERIVATION_STALLED",
    "fact_derivation_checkpoint": "PERCEPTION_FACT_DERIVATION_STALLED",
    "after_fact_derivation": "PERCEPTION_FACT_PROVENANCE_BINDING_STALLED",
    "before_fact_provenance_binding": "PERCEPTION_FACT_PROVENANCE_BINDING_STALLED",
    "after_fact_provenance_binding": "PERCEPTION_FACT_DEDUPLICATION_STALLED",
    "before_fact_deduplication": "PERCEPTION_FACT_DEDUPLICATION_STALLED",
    "after_fact_deduplication": "PERCEPTION_FACT_VALIDATION_PROJECTION_STALLED",
    "before_fact_validation_projection": "PERCEPTION_FACT_VALIDATION_PROJECTION_STALLED",
    "after_fact_validation_projection": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "fact_projection_completed": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "after_fact_projection": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "before_payload_assembly": "PERCEPTION_PAYLOAD_ASSEMBLY_STALLED",
    "after_payload_assembly": "PERCEPTION_PAYLOAD_BOUND_EXCEEDED",
    "before_payload_bound_check": "PERCEPTION_PAYLOAD_BOUND_EXCEEDED",
    "after_payload_bound_check": "PERCEPTION_PAYLOAD_COMPILE_BUDGET_EXCEEDED",
    "perception_compile_completed": "MUSIC_INVENTORY_CONTRACT_PERCEPTION_STALLED",
    "after_perception_payload_compile": "MUSIC_INVENTORY_CONTRACT_PERCEPTION_STALLED",
    "before_contract_perception": "MUSIC_INVENTORY_CONTRACT_PERCEPTION_STALLED",
    "after_contract_perception": "MUSIC_INVENTORY_ROW_BINDING_STALLED",
    "before_row_binding": "MUSIC_INVENTORY_ROW_BINDING_STALLED",
    "after_row_binding": "MUSIC_INVENTORY_METADATA_COVERAGE_CALCULATION_STALLED",
    "before_metadata_coverage_summary": "MUSIC_INVENTORY_METADATA_COVERAGE_CALCULATION_STALLED",
    "after_metadata_coverage_summary": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "before_csv_row_stream": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "csv_row_stream_checkpoint": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "before_csv_cell_render": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "after_entity_batch": "MUSIC_INVENTORY_CSV_STREAMING_STALLED",
    "after_csv_row_stream": "MUSIC_INVENTORY_SEMANTIC_PROFILE_BUILD_STALLED",
    "before_artifact_semantic_profile": "MUSIC_INVENTORY_SEMANTIC_PROFILE_BUILD_STALLED",
    "after_artifact_semantic_profile": "MUSIC_INVENTORY_SUFFICIENCY_EVALUATION_STALLED",
    "before_inventory_sufficiency": "MUSIC_INVENTORY_SUFFICIENCY_EVALUATION_STALLED",
    "after_inventory_sufficiency": "MUSIC_INVENTORY_ARTIFACT_PERSIST_STALLED",
    "before_artifact_persist": "MUSIC_INVENTORY_ARTIFACT_PERSIST_STALLED",
    "before_persist_payload_classification": "ARTIFACT_PERSIST_PAYLOAD_CLASSIFICATION_STALLED",
    "after_persist_payload_classification": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "before_payload_materialization": "ARTIFACT_PERSIST_PAYLOAD_MATERIALIZATION_STALLED",
    "after_payload_materialization": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "before_payload_serialization": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "payload_serialization_checkpoint": "ARTIFACT_PERSIST_PAYLOAD_SERIALIZATION_STALLED",
    "after_payload_serialization": "ARTIFACT_PERSIST_PAYLOAD_REF_DECISION_STALLED",
    "before_payload_ref_decision": "ARTIFACT_PERSIST_PAYLOAD_REF_DECISION_STALLED",
    "after_payload_ref_decision": "ARTIFACT_PERSIST_PAYLOAD_REF_PERSIST_STALLED",
    "before_payload_ref_persist": "ARTIFACT_PERSIST_PAYLOAD_REF_PERSIST_STALLED",
    "after_payload_ref_persist": "ARTIFACT_PERSIST_ARTIFACT_CONTENT_WRITE_STALLED",
    "before_artifact_content_write": "ARTIFACT_PERSIST_ARTIFACT_CONTENT_WRITE_STALLED",
    "artifact_content_write_checkpoint": "ARTIFACT_PERSIST_ARTIFACT_CONTENT_WRITE_STALLED",
    "after_artifact_content_write": "ARTIFACT_PERSIST_MANIFEST_BUILD_STALLED",
    "before_manifest_build": "ARTIFACT_PERSIST_MANIFEST_BUILD_STALLED",
    "after_manifest_build": "ARTIFACT_PERSIST_MANIFEST_WRITE_STALLED",
    "before_manifest_persist": "ARTIFACT_PERSIST_MANIFEST_WRITE_STALLED",
    "before_sharded_manifest_persist": "ARTIFACT_PERSIST_MANIFEST_WRITE_STALLED",
    "after_sharded_manifest_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "after_manifest_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "before_registry_index_update": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "before_light_index_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "after_light_index_persist": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "before_legacy_registry_projection": "ARTIFACT_PERSIST_LEGACY_REGISTRY_PROJECTION_STALLED",
    "after_legacy_registry_projection": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "legacy_registry_projection_skipped": "ARTIFACT_PERSIST_REGISTRY_INDEX_UPDATE_STALLED",
    "after_registry_index_update": "ARTIFACT_PERSIST_COMMIT_STALLED",
    "before_artifact_commit": "ARTIFACT_PERSIST_COMMIT_STALLED",
    "after_artifact_commit": "ARTIFACT_PERSIST_COMPLETED",
    "artifact_persist_completed": "ARTIFACT_PERSIST_COMPLETED",
    "after_artifact_persist": "ARTIFACT_PERSIST_COMPLETED",
}

_CSV_RENDER_PROGRESS_STAGES = {
    "before_csv_cell_render",
    "csv_row_stream_checkpoint",
    "after_entity_batch",
    "before_csv_row_stream",
    "after_csv_row_stream",
}

_POST_ARTIFACT_COMMIT_CHECKPOINT_STAGES = {
    "after_artifact_commit",
    "artifact_persist_completed",
    "after_artifact_persist",
    "after_registry_create_before_event",
}


@dataclass(frozen=True)
class ReadonlyArtifactExecution:
    response: ChatResponse
    run_id: str | None
    created_artifacts: list[dict[str, Any]]
    validation: dict[str, Any]


@dataclass(frozen=True)
class ArtifactRenderResult:
    content: str
    semantic_gaps: list[dict[str, Any]]
    schema_coverage: dict[str, Any]
    entity_summary: dict[str, Any]
    status: str = "completed"
    reason_code: str | None = None
    partial_rows: int | None = None
    expected_rows: int | None = None
    selected_rows: int | None = None
    bound_rows: int | None = None
    evidence_ref_count: int | None = None
    rendered_columns: list[str] | None = None
    missing_columns: list[str] | None = None
    row_validation_summary: dict[str, Any] | None = None
    evidence_refs_sample: list[str] | None = None
    row_evidence_coverage: dict[str, Any] | None = None
    safe_to_use: bool = True


@dataclass(frozen=True)
class ArtifactRenderBudget:
    max_total_seconds: float = 900.0
    max_artifact_seconds: float = 420.0
    max_rows: int = 100_000
    max_entities: int = 5_000
    max_columns: int = 200
    max_cells: int = 2_000_000
    max_cell_bytes: int = 2_000
    max_total_bytes: int = 5_000_000
    max_metadata_inline_bytes: int = 2_000
    max_evidence_refs_inline: int = 20
    cancel_poll_interval: int = 50
    allow_partial_artifact: bool = False
    late_artifact_policy: str = "reject"

    @classmethod
    def from_environment(cls) -> "ArtifactRenderBudget":
        return cls(
            max_total_seconds=float(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_SECONDS", os.environ.get("AIPINHO_PHASE1_MAX_RUNTIME_SECONDS", "900"))),
            max_artifact_seconds=float(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_ARTIFACT_SECONDS", os.environ.get("AIPINHO_PHASE1_MAX_ARTIFACT_RENDER_SECONDS", "420"))),
            max_rows=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_ROWS", "100000")),
            max_entities=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_ENTITIES", "5000")),
            max_columns=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_COLUMNS", "200")),
            max_cells=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_CELLS", "2000000")),
            max_cell_bytes=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_CELL_BYTES", os.environ.get("AIPINHO_PHASE1_MAX_CSV_CELL_BYTES", "2000"))),
            max_total_bytes=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_TOTAL_BYTES", os.environ.get("AIPINHO_PHASE1_MAX_CSV_TOTAL_BYTES", "5000000"))),
            max_metadata_inline_bytes=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_METADATA_INLINE_BYTES", os.environ.get("AIPINHO_PHASE1_MAX_CSV_CELL_BYTES", "2000"))),
            max_evidence_refs_inline=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_EVIDENCE_REFS_INLINE", "20")),
            cancel_poll_interval=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_CANCEL_POLL_INTERVAL", os.environ.get("AIPINHO_PHASE1_CANCEL_POLL_INTERVAL", "50"))),
            allow_partial_artifact=str(os.environ.get("AIPINHO_ARTIFACT_RENDER_ALLOW_PARTIAL", "false")).lower() in {"1", "true", "yes", "on"},
            late_artifact_policy=str(os.environ.get("AIPINHO_ARTIFACT_RENDER_LATE_POLICY", "reject") or "reject"),
        )


@dataclass(frozen=True)
class Phase1RuntimeBudget:
    max_runtime_seconds: float = 900.0
    max_artifact_render_seconds: float = 420.0
    max_csv_cell_bytes: int = 2_000
    max_csv_total_bytes: int = 5_000_000
    cancel_poll_interval: int = 50
    max_artifact_rows: int = 100_000
    max_artifact_entities: int = 5_000
    max_artifact_columns: int = 200
    max_artifact_cells: int = 2_000_000
    artifact_checkpoint_event_interval_ms: int = 5_000
    allow_partial_artifact: bool = False
    late_artifact_policy: str = "reject"

    @classmethod
    def from_environment(cls) -> "Phase1RuntimeBudget":
        return cls(
            max_runtime_seconds=float(os.environ.get("AIPINHO_PHASE1_MAX_RUNTIME_SECONDS", "900")),
            max_artifact_render_seconds=float(os.environ.get("AIPINHO_PHASE1_MAX_ARTIFACT_RENDER_SECONDS", "420")),
            max_csv_cell_bytes=int(os.environ.get("AIPINHO_PHASE1_MAX_CSV_CELL_BYTES", "2000")),
            max_csv_total_bytes=int(os.environ.get("AIPINHO_PHASE1_MAX_CSV_TOTAL_BYTES", "5000000")),
            cancel_poll_interval=int(os.environ.get("AIPINHO_PHASE1_CANCEL_POLL_INTERVAL", "50")),
            max_artifact_rows=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_ROWS", "100000")),
            max_artifact_entities=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_ENTITIES", "5000")),
            max_artifact_columns=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_COLUMNS", "200")),
            max_artifact_cells=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_MAX_CELLS", "2000000")),
            artifact_checkpoint_event_interval_ms=int(os.environ.get("AIPINHO_ARTIFACT_RENDER_CHECKPOINT_EVENT_INTERVAL_MS", "5000")),
            allow_partial_artifact=str(os.environ.get("AIPINHO_ARTIFACT_RENDER_ALLOW_PARTIAL", "false")).lower() in {"1", "true", "yes", "on"},
            late_artifact_policy=str(os.environ.get("AIPINHO_ARTIFACT_RENDER_LATE_POLICY", "reject") or "reject"),
        )

    def artifact_render_budget(self) -> ArtifactRenderBudget:
        return ArtifactRenderBudget(
            max_total_seconds=self.max_runtime_seconds,
            max_artifact_seconds=self.max_artifact_render_seconds,
            max_rows=self.max_artifact_rows,
            max_entities=self.max_artifact_entities,
            max_columns=self.max_artifact_columns,
            max_cells=self.max_artifact_cells,
            max_cell_bytes=self.max_csv_cell_bytes,
            max_total_bytes=self.max_csv_total_bytes,
            max_metadata_inline_bytes=self.max_csv_cell_bytes,
            cancel_poll_interval=self.cancel_poll_interval,
            allow_partial_artifact=self.allow_partial_artifact,
            late_artifact_policy=self.late_artifact_policy,
        )


@dataclass(frozen=True)
class PublicRuntimeResponsePolicy:
    initial_response_budget_ms: int = 2500
    accepted_running_enabled: bool = True
    accepted_running_minimum_state_required: str = "task_run_persisted"
    timeout_blocked_enabled: bool = True
    max_client_sync_wait_ms: int = 5000
    result_finalization_required: bool = True
    terminal_event_required: bool = True
    polling_endpoints_required: bool = True
    safe_to_report_success_default: bool = False

    @classmethod
    def from_environment(cls) -> "PublicRuntimeResponsePolicy":
        return cls(
            initial_response_budget_ms=int(os.environ.get("AIPINHO_PUBLIC_RUNTIME_INITIAL_RESPONSE_BUDGET_MS", "2500")),
            accepted_running_enabled=str(os.environ.get("AIPINHO_PUBLIC_RUNTIME_ACCEPTED_RUNNING_ENABLED", "true")).lower()
            in {"1", "true", "yes", "on"},
            timeout_blocked_enabled=str(os.environ.get("AIPINHO_PUBLIC_RUNTIME_TIMEOUT_BLOCKED_ENABLED", "true")).lower()
            in {"1", "true", "yes", "on"},
            max_client_sync_wait_ms=int(os.environ.get("AIPINHO_PUBLIC_RUNTIME_MAX_CLIENT_SYNC_WAIT_MS", "5000")),
            result_finalization_required=True,
            terminal_event_required=True,
            polling_endpoints_required=True,
            safe_to_report_success_default=False,
        )


@dataclass(frozen=True)
class PublicPreAcceptancePolicy:
    """Limits public chat pre-acceptance to lightweight routing/bootstrap work."""

    allowed_steps: tuple[str, ...] = (
        "parse_prompt",
        "resolve_intent",
        "resolve_operation_contract",
        "policy_gate",
        "light_phase_dependency_preflight",
        "create_task_run",
    )
    heavy_work_reason_code: str = "PUBLIC_RUNTIME_PREACCEPTANCE_HEAVY_WORK_DETECTED"
    create_run_not_reached_reason_code: str = "PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED"


@dataclass(frozen=True)
class AcceptedRunningWorkerTerminalityPolicy:
    """Guards accepted public workers after the client receives accepted_running."""

    enabled: bool = True
    poll_interval_ms: int = 250
    max_artifact_silence_ms: int = 60_000
    max_worker_exit_grace_ms: int = 500
    result_source: str = "artifact_worker_terminalization_guard"
    stalled_reason_code: str = "ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED"
    media_inventory_stalled_reason_code: str = "MUSIC_INVENTORY_ARTIFACT_STALLED_AFTER_CREATION_STARTED"
    exited_reason_code: str = "ARTIFACT_WORKER_EXITED_WITHOUT_TERMINAL_RESULT"
    exception_reason_code: str = "ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING"

    @classmethod
    def from_environment(cls) -> "AcceptedRunningWorkerTerminalityPolicy":
        artifact_seconds = float(
            os.environ.get(
                "AIPINHO_ARTIFACT_RENDER_MAX_ARTIFACT_SECONDS",
                os.environ.get("AIPINHO_PHASE1_MAX_ARTIFACT_RENDER_SECONDS", "420"),
            )
        )
        return cls(
            enabled=str(os.environ.get("AIPINHO_ACCEPTED_WORKER_TERMINALITY_GUARD_ENABLED", "true")).lower()
            in {"1", "true", "yes", "on"},
            poll_interval_ms=int(os.environ.get("AIPINHO_ACCEPTED_WORKER_GUARD_POLL_INTERVAL_MS", "250")),
            max_artifact_silence_ms=int(
                os.environ.get("AIPINHO_ACCEPTED_WORKER_ARTIFACT_STALL_MS", str(int(min(60.0, artifact_seconds) * 1000)))
            ),
            max_worker_exit_grace_ms=int(os.environ.get("AIPINHO_ACCEPTED_WORKER_EXIT_GRACE_MS", "500")),
        )


class GovernedPhase1Block(RuntimeError):
    def __init__(self, reason_code: str, message: str, *, status: str = "blocked", details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.status = status
        self.details = details or {}


class ReadonlyAnalysisArtifactRuntimeService:
    """Executes read-only analysis tasks that explicitly request artifacts.

    Source workspaces remain read-only. Generated reports are persisted only in
    the governed artifact registry and are tied to a real TaskRun.
    """

    ARTIFACT_REQUEST_TERMS = (
        "artifact",
        "artifacts",
        "artefato",
        "artefatos",
        "entregavel",
        "entregaveis",
        "entregável",
        "entregáveis",
        "storage",
        "gerar arquivos",
        "gere arquivos",
        "salve em",
        "grave em",
    )
    ARTIFACT_FORBIDDEN_TERMS = (
        "nao criar artifact",
        "não criar artifact",
        "nao criar artifacts",
        "não criar artifacts",
        "nao criar artefato",
        "não criar artefato",
        "nao gerar artifact",
        "não gerar artifact",
        "nao gere artifact",
        "não gere artifact",
    )

    def __init__(
        self,
        *,
        runtime: TaskRuntimeService | None = None,
        analysis: ProjectAnalysisService | None = None,
        artifacts: UniversalArtifactRegistryService | None = None,
        artifact_runtime: ArtifactRuntimeService | None = None,
        artifact_semantic_contracts: ArtifactSemanticContractService | None = None,
        observed_entities: ObservedEntityCompilationService | None = None,
        perception: ContractDrivenPerceptionService | None = None,
        semantic_intents: SemanticArtifactIntentResolver | None = None,
        semantic_entity_selection: SemanticEntitySelectionService | None = None,
        row_level_validation: RowLevelSemanticValidationService | None = None,
        media_inventory_sufficiency: MediaInventorySufficiencyService | None = None,
        model_patch_planner: ModelAssistedPatchPlannerService | None = None,
        lifecycle: TaskRunLifecycleService | None = None,
        governance: GovernanceLifecycleService | None = None,
        phase_store_path: Path | None = None,
        budget: Phase1RuntimeBudget | None = None,
        public_response_policy: PublicRuntimeResponsePolicy | None = None,
        public_preacceptance_policy: PublicPreAcceptancePolicy | None = None,
        accepted_worker_terminality_policy: AcceptedRunningWorkerTerminalityPolicy | None = None,
        phase_semantic_completion_policy: PhaseSemanticCompletionPolicy | None = None,
    ) -> None:
        self.runtime = runtime or TaskRuntimeService()
        self.analysis = analysis or ProjectAnalysisService()
        self.artifact_runtime = artifact_runtime or ArtifactRuntimeService(registry=artifacts)
        self.artifacts = self.artifact_runtime
        self.artifact_semantic_contracts = artifact_semantic_contracts or ArtifactSemanticContractService()
        self.observed_entities = observed_entities or ObservedEntityCompilationService()
        self.perception = perception or ContractDrivenPerceptionService(observed_entities=self.observed_entities)
        self.semantic_intents = semantic_intents or SemanticArtifactIntentResolver()
        self.semantic_entity_selection = semantic_entity_selection or SemanticEntitySelectionService()
        self.row_level_validation = row_level_validation or RowLevelSemanticValidationService()
        self.media_inventory_sufficiency = media_inventory_sufficiency or MediaInventorySufficiencyService()
        self.model_patch_planner = model_patch_planner or ModelAssistedPatchPlannerService()
        self.lifecycle = lifecycle or TaskRunLifecycleService()
        self.governance = governance or GovernanceLifecycleService()
        self.phase_store_path = phase_store_path or (
            PATHS.project_root / "data" / "runtime" / "readonly_analysis_artifact_phases.json"
        )
        self.budget = budget or Phase1RuntimeBudget.from_environment()
        self.public_response_policy = public_response_policy or PublicRuntimeResponsePolicy.from_environment()
        self.public_preacceptance_policy = public_preacceptance_policy or PublicPreAcceptancePolicy()
        self.accepted_worker_terminality_policy = accepted_worker_terminality_policy or AcceptedRunningWorkerTerminalityPolicy.from_environment()
        self.phase_semantic_completion_policy = phase_semantic_completion_policy or PhaseSemanticCompletionPolicy()
        self._artifact_checkpoint_emitted: dict[tuple[str, str, str], float] = {}

    def requested_artifact_paths(self, text: str) -> list[str]:
        if not self._artifact_generation_requested(text):
            return []
        paths: list[str] = []
        for match in _ARTIFACT_PATH_RE.finditer(text or ""):
            candidate = self._normalize_logical_path(match.group("path"))
            if candidate and candidate not in paths:
                paths.append(candidate)
        return paths

    def should_handle(self, text: str, *, intent_type: str, workspace: str | None) -> bool:
        if intent_type != "workspace_analysis_readonly":
            return False
        return bool(workspace and self.requested_artifact_paths(text))

    def workspace_from_phase_dependencies(self, *, text: str, session_id: str | None) -> str | None:
        phase_id = self._phase_id(text) or "phase_unknown"
        dependency_phase_ids = self._dependency_phase_ids(text, current_phase_id=phase_id)
        store = self._load_phase_store()
        for dependency_phase_id in dependency_phase_ids:
            record = self._latest_phase_record(store, session_id=session_id, phase_id=dependency_phase_id)
            if record and record.get("workspace"):
                return str(record.get("workspace"))
        return None

    def latest_patch_plan_context(
        self,
        *,
        session_id: str | None,
        workspace: str | None = None,
    ) -> dict[str, Any] | None:
        store = self._load_phase_store()
        candidates = [
            item
            for item in store
            if item.get("status") == "completed"
            and (not session_id or item.get("session_id") == session_id)
        ]
        if not candidates and session_id:
            candidates = [item for item in store if item.get("status") == "completed"]
        for record in sorted(candidates, key=lambda item: str(item.get("created_at") or ""), reverse=True):
            plan_id = self._phase_record_patch_plan_id(record)
            if not plan_id:
                continue
            plan = PatchPlanStore().get_plan(plan_id)
            if plan is None:
                continue
            if workspace and plan.workspace and Path(plan.workspace) != Path(str(workspace)):
                continue
            plan_payload = plan.model_dump(mode="json")
            if not self._plan_has_concrete_hunks(plan_payload):
                continue
            target_paths = [
                str(item.get("normalized_path") or item.get("path") or item.get("relative_path"))
                for item in plan_payload.get("affected_files", [])
                if isinstance(item, dict)
                and (item.get("normalized_path") or item.get("path") or item.get("relative_path"))
            ]
            return {
                "patch_plan_id": plan.plan_id,
                "patch_plan": plan_payload,
                "workspace": plan.workspace,
                "target_paths": list(dict.fromkeys(target_paths)),
                "source_run_id": record.get("run_id"),
                "logical_paths": list(record.get("logical_paths") or []),
                "artifacts": list(record.get("artifacts") or []),
            }
        return None

    def start_public_boundary(
        self,
        *,
        request,
        workspace: str,
        label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY",
    ) -> ReadonlyArtifactExecution:
        policy = self.public_response_policy
        if not policy.accepted_running_enabled:
            return self.execute(request=request, workspace=workspace, label=label)
        self._reap_public_boundary_threads(max_wait_seconds=2.0)
        holder: dict[str, Any] = {}
        original_store_create_run = self.runtime.store.create_run
        original_runtime_create_run = self.runtime.create_run

        def capture_store_create_run(run):
            created = original_store_create_run(run)
            if (
                created.workspace == workspace
                and created.operation_type == "workspace_analysis_readonly"
                and (created.intent_map or {}).get("raw_prompt") == request.message
            ):
                holder["store_run_id"] = created.run_id
            return created

        def capture_runtime_create_run(run_request):
            holder["runtime_create_started"] = True
            created = original_runtime_create_run(run_request)
            if (
                created.workspace == workspace
                and created.operation_type == "workspace_analysis_readonly"
                and (created.intent_map or {}).get("raw_prompt") == request.message
            ):
                holder["run_id"] = created.run_id
                holder["runtime_create_completed"] = True
            return created

        def worker() -> None:
            try:
                self.runtime.store.create_run = capture_store_create_run  # type: ignore[method-assign]
                self.runtime.create_run = capture_runtime_create_run  # type: ignore[method-assign]
                holder["execution"] = self.execute(request=request, workspace=workspace, label=label)
            except Exception as exc:  # pragma: no cover - defensive public boundary guard
                holder["exception"] = exc
                run_id = holder.get("run_id") or holder.get("store_run_id")
                if run_id:
                    self._terminalize_accepted_worker_gap(
                        str(run_id),
                        reason_code=self.accepted_worker_terminality_policy.exception_reason_code,
                        message="Accepted public artifact worker raised an exception after TaskRun bootstrap.",
                        exception=exc,
                    )
            finally:
                self.runtime.create_run = original_runtime_create_run  # type: ignore[method-assign]
                self.runtime.store.create_run = original_store_create_run  # type: ignore[method-assign]
                run_id = holder.get("run_id") or holder.get("store_run_id")
                if run_id and "exception" not in holder:
                    self._terminalize_accepted_worker_gap(
                        str(run_id),
                        reason_code=self.accepted_worker_terminality_policy.exited_reason_code,
                        message="Accepted public artifact worker exited without a terminal TaskRunResult.",
                        only_if_artifact_started=False,
                    )

        thread = Thread(target=worker, name="aipinho-public-runtime-boundary", daemon=True)
        thread.start()
        _PUBLIC_BOUNDARY_THREADS.append(thread)
        deadline = time.monotonic() + max(0.4, policy.initial_response_budget_ms / 1000)
        discovered_run = None
        while time.monotonic() < deadline:
            run_id = holder.get("run_id") or holder.get("store_run_id")
            discovered_run = self.runtime.store.get_run(str(run_id)) if run_id else None
            runtime_create_in_progress = bool(holder.get("runtime_create_started")) and not bool(holder.get("runtime_create_completed"))
            direct_store_create = bool(holder.get("store_run_id")) and not bool(holder.get("runtime_create_started"))
            if discovered_run is not None and (not runtime_create_in_progress or direct_store_create):
                if holder.get("runtime_create_completed") and thread.is_alive():
                    thread.join(timeout=0.25)
                self._start_accepted_worker_guard(discovered_run.run_id, thread=thread, holder=holder)
                self._mark_accepted_running(discovered_run, policy=policy)
                return ReadonlyArtifactExecution(
                    response=self._accepted_running_response(
                        request,
                        workspace=workspace,
                        run=discovered_run,
                        policy=policy,
                    ),
                    run_id=discovered_run.run_id,
                    created_artifacts=[],
                    validation={
                        "status": "accepted_running",
                        "safe_to_report_success": False,
                        "reason_code": "RUN_ACCEPTED_ASYNC",
                    },
                )
            if "execution" in holder:
                return holder["execution"]
            if "exception" in holder:
                raise holder["exception"]
            time.sleep(0.01)
        run_id = holder.get("run_id") or holder.get("store_run_id")
        discovered_run = self.runtime.store.get_run(str(run_id)) if run_id else None
        if discovered_run is not None:
            if holder.get("runtime_create_completed") and thread.is_alive():
                thread.join(timeout=0.25)
            self._start_accepted_worker_guard(discovered_run.run_id, thread=thread, holder=holder)
            self._mark_accepted_running(discovered_run, policy=policy)
            return ReadonlyArtifactExecution(
                response=self._accepted_running_response(
                    request,
                    workspace=workspace,
                    run=discovered_run,
                    policy=policy,
                ),
                run_id=discovered_run.run_id,
                created_artifacts=[],
                validation={
                    "status": "accepted_running",
                    "safe_to_report_success": False,
                    "reason_code": "RUN_ACCEPTED_ASYNC",
                },
            )
        if "execution" in holder:
            return holder["execution"]
        return ReadonlyArtifactExecution(
            response=self._timeout_blocked_response(
                request,
                workspace=workspace,
                reason_code=self.public_preacceptance_policy.create_run_not_reached_reason_code,
                policy=policy,
            ),
            run_id=None,
            created_artifacts=[],
            validation={
                "status": "blocked",
                "reason_code": self.public_preacceptance_policy.create_run_not_reached_reason_code,
                "safe_to_report_success": False,
            },
        )

    def _reap_public_boundary_threads(self, *, max_wait_seconds: float = 0.0) -> None:
        deadline = time.monotonic() + max(0.0, max_wait_seconds)
        alive: list[Thread] = []
        for thread in list(_PUBLIC_BOUNDARY_THREADS):
            if thread.is_alive() and time.monotonic() < deadline:
                thread.join(timeout=max(0.0, min(0.05, deadline - time.monotonic())))
            if thread.is_alive():
                alive.append(thread)
        _PUBLIC_BOUNDARY_THREADS[:] = alive
        guard_alive: list[Thread] = []
        for thread in list(_PUBLIC_BOUNDARY_GUARD_THREADS):
            if thread.is_alive() and time.monotonic() < deadline:
                thread.join(timeout=max(0.0, min(0.05, deadline - time.monotonic())))
            if thread.is_alive():
                guard_alive.append(thread)
        _PUBLIC_BOUNDARY_GUARD_THREADS[:] = guard_alive

    def _start_accepted_worker_guard(self, run_id: str, *, thread: Thread, holder: dict[str, Any]) -> None:
        policy = self.accepted_worker_terminality_policy
        if not policy.enabled or holder.get("accepted_worker_guard_started"):
            return
        holder["accepted_worker_guard_started"] = True

        def guard() -> None:
            self._accepted_worker_guard_loop(run_id, thread=thread, holder=holder, policy=policy)

        guard_thread = Thread(target=guard, name="aipinho-accepted-worker-terminality-guard", daemon=True)
        guard_thread.start()
        _PUBLIC_BOUNDARY_GUARD_THREADS.append(guard_thread)

    def _accepted_worker_guard_loop(
        self,
        run_id: str,
        *,
        thread: Thread,
        holder: dict[str, Any],
        policy: AcceptedRunningWorkerTerminalityPolicy,
    ) -> None:
        try:
            self.runtime.events.create(
                run_id,
                "artifact_creation_terminalization_guard_started",
                "running",
                "Accepted-running artifact worker terminalization guard started.",
                metadata={
                    "source": policy.result_source,
                    "max_artifact_silence_ms": policy.max_artifact_silence_ms,
                    "poll_interval_ms": policy.poll_interval_ms,
                },
            )
        except Exception:
            return
        while True:
            if self.runtime.store.get_result(run_id) is not None or self._first_terminal_event(run_id) is not None:
                self._emit_guard_marker(
                    run_id,
                    "artifact_creation_terminalization_guard_skipped",
                    "ignored",
                    "Accepted-running worker guard skipped because a terminal result or event already exists.",
                    {"source": policy.result_source, "reason": "terminal_state_already_set"},
                )
                return
            run = self.runtime.store.get_run(run_id)
            if run is None:
                return
            if run.cancellation_requested or str(run.status) == "cancelled":
                self._emit_guard_marker(
                    run_id,
                    "artifact_creation_terminalization_guard_skipped",
                    "ignored",
                    "Accepted-running worker guard skipped because governed cancellation is in progress.",
                    {"source": policy.result_source, "reason": "governed_cancellation_in_progress"},
                )
                return
            in_progress = self._artifact_creation_in_progress(run_id)
            if in_progress is not None:
                elapsed_ms = self._event_elapsed_ms(in_progress)
                last_checkpoint = self._last_artifact_render_checkpoint(run_id, in_progress)
                silence_ms = self._event_elapsed_ms(last_checkpoint) if last_checkpoint is not None else elapsed_ms
                if not thread.is_alive():
                    self._emit_guard_marker(
                        run_id,
                        "artifact_creation_worker_silent_exit_detected",
                        "blocked",
                        "Accepted-running worker exited while an artifact had no terminal state.",
                        {
                            "source": policy.result_source,
                            "logical_path": (in_progress.metadata or {}).get("logical_path"),
                            "created_event_source_id": in_progress.event_id,
                            "elapsed_ms": elapsed_ms,
                            "silence_ms": silence_ms,
                        },
                    )
                    self._terminalize_accepted_worker_gap(
                        run_id,
                        reason_code=self._reason_code_for_artifact_stall(in_progress, policy.stalled_reason_code),
                        message="Artifact worker exited after artifact creation started without terminal artifact state.",
                        artifact_event=in_progress,
                    )
                    return
                if silence_ms is not None and silence_ms >= policy.max_artifact_silence_ms:
                    self._terminalize_accepted_worker_gap(
                        run_id,
                        reason_code=self._reason_code_for_artifact_stall(in_progress, policy.stalled_reason_code),
                        message="Artifact worker exceeded the artifact heartbeat silence budget after artifact creation started.",
                        artifact_event=in_progress,
                        elapsed_ms=silence_ms,
                    )
                    return
            elif not thread.is_alive():
                time.sleep(max(0.0, policy.max_worker_exit_grace_ms / 1000))
                if self.runtime.store.get_result(run_id) is None and self._first_terminal_event(run_id) is None:
                    self._terminalize_accepted_worker_gap(
                        run_id,
                        reason_code=policy.exited_reason_code,
                        message="Accepted public artifact worker exited without a terminal TaskRunResult.",
                        only_if_artifact_started=False,
                    )
                return
            time.sleep(max(0.01, policy.poll_interval_ms / 1000))

    def _terminalize_accepted_worker_gap(
        self,
        run_id: str,
        *,
        reason_code: str,
        message: str,
        artifact_event=None,
        exception: Exception | None = None,
        elapsed_ms: int | None = None,
        only_if_artifact_started: bool = True,
    ) -> TaskRunResult | None:
        if not self._looks_like_task_run_id(run_id):
            return None
        existing = self.runtime.store.get_result(run_id)
        if existing is not None:
            return existing
        terminal = self._first_terminal_event(run_id)
        run = self.runtime.store.get_run(run_id)
        if run is None:
            return None
        if terminal is not None:
            return self.runtime.store.ensure_terminal_result(run_id, reason_code=reason_code)
        if run.cancellation_requested or str(run.status) == "cancelled":
            return None
        artifact_event = artifact_event or self._artifact_creation_in_progress(run_id)
        if only_if_artifact_started and artifact_event is None:
            return None
        now = datetime.now(timezone.utc).isoformat()
        logical_path = str((artifact_event.metadata or {}).get("logical_path") or "") if artifact_event is not None else ""
        producer_step = str((artifact_event.metadata or {}).get("producer_step") or "readonly_analysis_artifact_runtime") if artifact_event is not None else "readonly_analysis_artifact_runtime"
        last_checkpoint = self._last_artifact_render_checkpoint(run_id, artifact_event)
        reason_code = self._reason_code_for_artifact_stall(artifact_event, reason_code)
        artifact_row = self._guard_artifact_row(
            task_run_id=run_id,
            logical_path=logical_path,
            producer_step=producer_step,
            reason_code=reason_code,
            artifact_event_id=getattr(artifact_event, "event_id", None),
        )
        created_artifacts = [item for item in run.produced_artifacts if isinstance(item, dict)]
        if artifact_row and not self._has_artifact_for_logical_path(created_artifacts, logical_path):
            created_artifacts.append(artifact_row)
        exception_summary = self._safe_exception_summary(
            exception,
            run_id=run_id,
            component="readonly_analysis_artifact_runtime",
            function="_accepted_worker_guard_loop",
            stage="accepted_worker_terminalization",
            artifact_event=artifact_event,
        ) if exception is not None else None
        if exception_summary is not None:
            self._emit_guard_marker(
                run_id,
                "artifact_creation_exception_captured",
                "blocked",
                "Accepted-running artifact worker exception captured.",
                {"source": self.accepted_worker_terminality_policy.result_source, "exception": exception_summary},
            )
        self._emit_guard_marker(
            run_id,
            "artifact_creation_terminalization_guard_triggered",
            "blocked",
            message,
            {
                "source": self.accepted_worker_terminality_policy.result_source,
                "reason_code": reason_code,
                "logical_path": logical_path or None,
                "producer_step": producer_step,
                "created_event_source_id": getattr(artifact_event, "event_id", None),
                "elapsed_ms": elapsed_ms,
                "last_checkpoint_stage": ((last_checkpoint.metadata or {}).get("stage") if last_checkpoint is not None else None),
                "last_checkpoint_sequence": getattr(last_checkpoint, "sequence", None),
            },
        )
        if artifact_event is not None and not self._has_artifact_terminal_after(run_id, artifact_event):
            self.runtime.events.create(
                run_id,
                "artifact_failed",
                "blocked",
                "Artifact worker failed to produce a terminal artifact state.",
                metadata={
                    "source": self.accepted_worker_terminality_policy.result_source,
                    "reason_code": reason_code,
                    "logical_path": logical_path,
                    "producer_step": producer_step,
                    "created_event_source_id": getattr(artifact_event, "event_id", None),
                    "last_checkpoint_stage": ((last_checkpoint.metadata or {}).get("stage") if last_checkpoint is not None else None),
                    "last_checkpoint_sequence": getattr(last_checkpoint, "sequence", None),
                    "safe_to_use": False,
                },
            )
        artifact_state = self._artifact_state(
            created_artifacts,
            {
                "status": "blocked",
                "reason_code": reason_code,
                "phase": "artifact_runtime",
                "safe_to_report_success": False,
            },
        )
        validation = {
            "status": "blocked",
            "reason_code": reason_code,
            "safe_to_display": True,
            "safe_to_report_success": False,
            "safe_to_continue": False,
            "blocking_findings": [reason_code],
            "phase": "phase1",
            "component": "readonly_analysis_artifact_runtime",
            "frontier": "ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP",
        }
        completion = TaskCompletionEvaluation(
            status="blocked",
            safe_to_report_success=False,
            missing_outcomes=[reason_code],
            warnings=["artifact_worker_terminalization_guard_triggered"],
            limitations=["accepted_running_worker_did_not_produce_terminal_artifact_or_result"],
            metadata={
                "reason_code": reason_code,
                "source": self.accepted_worker_terminality_policy.result_source,
                "artifact_state": artifact_state,
            },
        )
        result = TaskRunResult(
            run_id=run_id,
            status="blocked",
            source=self.accepted_worker_terminality_policy.result_source,
            reason_code=reason_code,
            finished_at=run.finished_at or now,
            summary=message,
            outputs={
                "artifact_worker_terminalization_guard": {
                    "reason_code": reason_code,
                    "source": self.accepted_worker_terminality_policy.result_source,
                    "artifact_terminal_state_missing": artifact_event is not None,
                    "logical_path": logical_path or None,
                        "producer_step": producer_step,
                        "created_event_source_id": getattr(artifact_event, "event_id", None),
                        "elapsed_ms": elapsed_ms,
                        "last_checkpoint_stage": ((last_checkpoint.metadata or {}).get("stage") if last_checkpoint is not None else None),
                        "last_checkpoint_sequence": getattr(last_checkpoint, "sequence", None),
                        "exception": exception_summary,
                        "safe_to_report_success": False,
                    },
                "artifact_result": {
                    "artifact_ids": [str(item.get("artifact_id")) for item in created_artifacts if item.get("artifact_id")],
                    "logical_paths": [str(item.get("logical_path")) for item in created_artifacts if item.get("logical_path")],
                    "artifacts": created_artifacts,
                    "artifact_state": artifact_state,
                },
                "validation_result": validation,
            },
            warnings=["artifact_worker_terminalization_guard_triggered"],
            blocked_items=[reason_code],
            events_count=len(self.runtime.events.list(run_id)),
            trace_ref=f"task-runs/{run_id}/trace",
            validation=validation,
            completion=completion,
        )
        saved = self.runtime.store.save_result(run_id, result)
        run = self.runtime.store.get_run(run_id) or run
        run.status = "blocked"  # type: ignore[assignment]
        run.finished_at = run.finished_at or now
        run.current_step_id = None
        run.produced_artifacts = created_artifacts
        run.blocked_reasons = list(dict.fromkeys([*run.blocked_reasons, reason_code]))
        run.warnings = list(dict.fromkeys([*run.warnings, "artifact_worker_terminalization_guard_triggered"]))
        run.revision += 1
        self.runtime.store.update_run(run)
        self._emit_terminal_event(
            run_id,
            "run_blocked",
            "blocked",
            message,
            metadata={
                "source": self.accepted_worker_terminality_policy.result_source,
                "reason_code": reason_code,
                "logical_path": logical_path or None,
                "producer_step": producer_step,
                "last_checkpoint_stage": ((last_checkpoint.metadata or {}).get("stage") if last_checkpoint is not None else None),
                "last_checkpoint_sequence": getattr(last_checkpoint, "sequence", None),
            },
        )
        self._emit_guard_marker(
            run_id,
            "artifact_creation_terminalization_guard_completed",
            "blocked",
            "Accepted-running artifact worker terminalization guard persisted a blocked result.",
            {"source": self.accepted_worker_terminality_policy.result_source, "reason_code": reason_code},
        )
        return saved

    def _guard_artifact_row(
        self,
        *,
        task_run_id: str,
        logical_path: str,
        producer_step: str,
        reason_code: str,
        artifact_event_id: str | None,
    ) -> dict[str, Any] | None:
        if not logical_path:
            return None
        return {
            "artifact_id": None,
            "logical_path": logical_path,
            "task_run_id": task_run_id,
            "status": "blocked",
            "reason_code": reason_code,
            "storage_ref": None,
            "safe_to_use": False,
            "visible_in_endpoint": True,
            "source": self.accepted_worker_terminality_policy.result_source,
            "producer_step": producer_step,
            "created_event_source_id": artifact_event_id,
            "semantic_contract_status": "not_evaluated",
            "artifact_terminal_state_missing": True,
        }

    def _reason_code_for_artifact_stall(self, artifact_event, fallback: str) -> str:
        metadata = artifact_event.metadata if artifact_event is not None and isinstance(artifact_event.metadata, dict) else {}
        artifact_kind = str(metadata.get("artifact_kind") or "")
        contract_id = str(metadata.get("contract_id") or "")
        if artifact_kind == "media_corpus_inventory" or contract_id == "media_corpus_inventory_artifact":
            checkpoint = self._last_artifact_render_checkpoint(getattr(artifact_event, "run_id", ""), artifact_event)
            checkpoint_metadata = checkpoint.metadata if checkpoint is not None and isinstance(checkpoint.metadata, dict) else {}
            stage_reason = _MEDIA_INVENTORY_STAGE_STALL_REASONS.get(str(checkpoint_metadata.get("stage") or ""))
            if stage_reason:
                return stage_reason
            return self.accepted_worker_terminality_policy.media_inventory_stalled_reason_code
        return fallback

    def _last_artifact_render_checkpoint(self, run_id: str, artifact_event):
        if artifact_event is None or not self._looks_like_task_run_id(run_id):
            return None
        artifact_metadata = artifact_event.metadata if isinstance(artifact_event.metadata, dict) else {}
        logical_path = str(artifact_metadata.get("logical_path") or "")
        artifact_attempt_id = str(artifact_metadata.get("artifact_attempt_id") or "")
        last = None
        for event in self.runtime.store.get_events(run_id):
            if event.sequence <= artifact_event.sequence or event.type != "artifact_render_checkpoint":
                continue
            metadata = event.metadata if isinstance(event.metadata, dict) else {}
            if artifact_attempt_id and str(metadata.get("artifact_attempt_id") or "") == artifact_attempt_id:
                last = event
                continue
            if logical_path and str(metadata.get("logical_path") or "") == logical_path:
                last = event
        return last

    def _artifact_creation_in_progress(self, run_id: str):
        for event in sorted(self.runtime.store.get_events(run_id), key=lambda item: item.sequence, reverse=True):
            if event.type == "artifact_creation_started" and not self._has_artifact_terminal_after(run_id, event):
                return event
        return None

    def _has_artifact_terminal_after(self, run_id: str, artifact_event) -> bool:
        metadata = artifact_event.metadata or {}
        logical_path = str(metadata.get("logical_path") or "")
        terminal_types = {
            "artifact_created",
            "artifact_partial",
            "artifact_blocked",
            "artifact_failed",
            "artifact_interrupted",
            "artifact_late_rejected",
        }
        for event in self.runtime.store.get_events(run_id):
            if event.sequence <= artifact_event.sequence or event.type not in terminal_types:
                continue
            event_metadata = event.metadata or {}
            source_id = event_metadata.get("created_event_source_id")
            event_logical_path = str(event_metadata.get("logical_path") or "")
            if source_id == artifact_event.event_id or (logical_path and event_logical_path == logical_path):
                return True
        return False

    def _event_elapsed_ms(self, event) -> int | None:
        try:
            timestamp = str(event.timestamp or "")
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            started = datetime.fromisoformat(timestamp)
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            return int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        except Exception:
            return None

    def _safe_exception_summary(
        self,
        exc: Exception,
        *,
        run_id: str | None = None,
        component: str = "readonly_analysis_artifact_runtime",
        function: str | None = None,
        stage: str | None = None,
        artifact_event: Any | None = None,
    ) -> dict[str, Any]:
        message = self.runtime.store.sanitize(str(exc) or type(exc).__name__)
        stack_trace_ref = None
        if run_id:
            try:
                stack = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                stack_trace_ref = self._write_exception_payload_ref(
                    run_id,
                    {
                        "exception_class": type(exc).__name__,
                        "exception_message_sanitized": str(message)[:1000],
                        "component": component,
                        "function": function,
                        "stage": stage,
                        "artifact_logical_path": str(((artifact_event.metadata or {}) if artifact_event is not None else {}).get("logical_path") or ""),
                        "producer_step": str(((artifact_event.metadata or {}) if artifact_event is not None else {}).get("producer_step") or ""),
                        "source_event_id": getattr(artifact_event, "event_id", None),
                        "stack_trace_sanitized": self.runtime.store.sanitize(stack[:20000]),
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception:
                stack_trace_ref = None
        return {
            "type": type(exc).__name__,
            "message": str(message)[:500],
            "component": component,
            "function": function,
            "stage": stage,
            "stack_trace_ref": stack_trace_ref,
        }

    def _write_exception_payload_ref(self, run_id: str, payload: dict[str, Any]) -> str | None:
        try:
            encoded = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
            digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            ref_dir = PATHS.project_root / "data" / "runtime" / "artifact_exception_refs" / self._safe_ref_segment(run_id)
            ref_dir.mkdir(parents=True, exist_ok=True)
            path = ref_dir / f"{digest}.json"
            if not path.exists():
                path.write_text(encoded, encoding="utf-8")
            return str(path.relative_to(PATHS.project_root))
        except Exception:
            return None

    def _emit_guard_marker(self, run_id: str, event_type: str, status: str, message: str, metadata: dict[str, Any]) -> None:
        try:
            self.runtime.events.create(run_id, event_type, status, message, metadata=metadata)
        except Exception:
            return

    def _new_public_run(self, before_ids: set[str], *, request, workspace: str):
        candidates = [
            run
            for run in self.runtime.store.list_runs(limit=1000)
            if run.run_id not in before_ids
            and run.workspace == workspace
            and run.operation_type == "workspace_analysis_readonly"
            and (run.intent_map or {}).get("raw_prompt") == request.message
        ]
        return sorted(candidates, key=lambda run: run.created_at, reverse=True)[0] if candidates else None

    def _mark_accepted_running(self, run, *, policy: PublicRuntimeResponsePolicy) -> None:
        boundary = {
            "status": "accepted_running",
            "client_response_budget_ms": policy.initial_response_budget_ms,
            "continuation_available": True,
            "polling_available": True,
            "result_finalized": False,
            "reason_codes": ["RUN_ACCEPTED_ASYNC"],
            "safe_to_report_success": False,
            "accepted_at": utc_now(),
        }
        run.intent_map["public_response_boundary"] = boundary
        run.bootstrap_context["public_response_boundary"] = boundary
        self.runtime.store.update_run(run)
        existing = [
            event
            for event in self.runtime.events.list(run.run_id)
            if event.type == "public_response_accepted_running"
        ]
        if not existing:
            self.runtime.events.create(
                run.run_id,
                "public_response_accepted_running",
                "accepted_running",
                "Public chat response returned while governed runtime continues.",
                metadata=boundary,
            )

    def _accepted_running_response(
        self,
        request,
        *,
        workspace: str,
        run,
        policy: PublicRuntimeResponsePolicy,
    ) -> ChatResponse:
        polling = self._polling_links(run.run_id)
        return ChatResponse(
            response_id=f"chat_accepted_running_{uuid4().hex}",
            session_id=request.session_id,
            task_id=run.task_id,
            task_run_id=run.run_id,
            result_ref_id=run.run_id,
            operation_id=run.operation_id,
            operation_type="workspace_analysis_readonly",
            message_type="task_status_update",
            status="accepted_running",
            message=(
                "PUBLIC_RUNTIME_ACCEPTED_RUNNING\n"
                f"task_run_id={run.run_id}\n"
                f"workspace={workspace}\n"
                "safe_to_report_success=false\n"
                "Run accepted and still executing under governed runtime."
            ),
            intent={
                "intent_type": "workspace_analysis_readonly",
                "requires_task": True,
                "readonly": True,
                "artifact_generation": True,
            },
            policy={
                "read_only": True,
                "workspace_mutation": False,
                "artifact_generation": True,
                "public_response_boundary": {
                    "status": "accepted_running",
                    "client_response_budget_ms": policy.initial_response_budget_ms,
                    "continuation_available": True,
                    "polling_available": True,
                    "result_finalized": False,
                    "reason_codes": ["RUN_ACCEPTED_ASYNC"],
                    "safe_to_report_success": False,
                },
            },
            contract_preview={
                "task_run_id": run.run_id,
                "run_status": run.status,
                "safe_to_report_success": False,
                "accepted_at": utc_now(),
                "polling": polling,
                "current_phase": run.current_phase,
                "known_frontier": None,
            },
            warnings=["accepted_running_is_not_success"],
            is_final_answer=False,
            grounded=True,
            grounding_required=False,
            model_used="readonly_analysis_artifact_runtime",
            real_inference=False,
            governance_lifecycle={
                "public_response_boundary": {
                    "status": "accepted_running",
                    "task_run_id": run.run_id,
                    "polling": polling,
                    "safe_to_report_success": False,
                }
            },
        )

    def _timeout_blocked_response(
        self,
        request,
        *,
        workspace: str,
        reason_code: str,
        policy: PublicRuntimeResponsePolicy,
    ) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_timeout_blocked_{uuid4().hex}",
            session_id=request.session_id,
            operation_type="workspace_analysis_readonly",
            message_type="blocked_policy_message",
            status="timeout_blocked",
            message=(
                "PUBLIC_RUNTIME_TIMEOUT_BLOCKED\n"
                f"reason_code={reason_code}\n"
                f"workspace={workspace}\n"
                "safe_to_report_success=false"
            ),
            intent={
                "intent_type": "workspace_analysis_readonly",
                "requires_task": False,
                "readonly": True,
                "artifact_generation": True,
            },
            policy={
                "read_only": True,
                "workspace_mutation": False,
                "artifact_generation": True,
                "reason_code": reason_code,
                "public_response_boundary": {
                    "status": "timeout_blocked",
                    "client_response_budget_ms": policy.initial_response_budget_ms,
                    "continuation_available": False,
                    "polling_available": False,
                    "result_finalized": False,
                    "reason_codes": [reason_code],
                    "safe_to_report_success": False,
                },
            },
            contract_preview={"workspace": workspace, "reason_code": reason_code},
            warnings=["timeout_blocked_is_not_success"],
            is_final_answer=False,
            grounded=False,
            grounding_required=True,
            grounding_missing_reason=reason_code,
            model_used="readonly_analysis_artifact_runtime",
            real_inference=False,
        )

    def _polling_links(self, run_id: str) -> dict[str, str]:
        return {
            "summary_url": f"/api/v1/task_runs/{run_id}/summary",
            "truth_url": f"/api/v1/task_runs/{run_id}/truth",
            "events_url": f"/api/v1/task_runs/{run_id}/events",
            "artifacts_url": f"/api/v1/task_runs/{run_id}/artifacts",
            "result_url": f"/api/v1/task-runs/{run_id}/result",
        }

    def execute(
        self,
        *,
        request,
        workspace: str,
        label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY",
    ) -> ReadonlyArtifactExecution:
        request_context = self._request_workspace_context(request)
        logical_paths = self.requested_artifact_paths(request.message)
        if not logical_paths:
            return ReadonlyArtifactExecution(
                response=self._blocked_response(
                    request,
                    workspace=workspace,
                    reason_code="artifact_paths_missing",
                    missing=["requested_artifact_paths"],
                ),
                run_id=None,
                created_artifacts=[],
                validation={"status": "blocked", "missing_outputs": ["requested_artifact_paths"]},
            )

        phase_id = self._phase_id(request.message) or "phase_unknown"
        dependency_phase_ids = self._dependency_phase_ids(request.message, current_phase_id=phase_id)
        dependency_preflight = self._validate_phase_dependencies(
            session_id=request.session_id,
            dependency_phase_ids=dependency_phase_ids,
            semantic=False,
        )
        dependency_check = dependency_preflight
        if dependency_preflight["status"] != "passed":
            dependency_reason = str(dependency_preflight.get("reason_code") or "phase_dependency_artifacts_missing")
            return ReadonlyArtifactExecution(
                response=self._blocked_response(
                    request,
                    workspace=workspace,
                    reason_code=dependency_reason,
                    missing=dependency_preflight["missing"],
                    dependency_check=dependency_preflight,
                ),
                run_id=None,
                created_artifacts=[],
                validation=dependency_preflight,
            )

        run = self.runtime.create_run(
            TaskRunRequest(
                source_type="direct",
                session_id=request.session_id,
                workspace=workspace,
                contract_type="analysis_readonly",
                operation_type="workspace_analysis_readonly",
                runtime_profile="readonly_analysis",
                capabilities_required=["read_workspace", "artifact_generate"],
                intent_map={
                    "intent_type": "workspace_analysis_readonly",
                    "operation_type": "workspace_analysis_readonly",
                    "artifact_generation": True,
                    "workspace_mutation": False,
                    "requested_artifact_paths": logical_paths,
                    "phase_id": phase_id,
                    "dependency_phase_ids": dependency_phase_ids,
                    "raw_prompt": request.message,
                    "external_roots": request_context.get("external_roots", []),
                    "library_roots": request_context.get("library_roots", []),
                    "readonly_flags": request_context.get("readonly_flags", {}),
                    "workspace_ids": request_context.get("workspace_ids", []),
                    "cognitive_readiness": self._phase0_readiness_ref(request),
                },
                policy_decision={
                    "status": "allowed",
                    "policy_status": "allowed",
                    "allowed_actions": ["read_workspace", "read_files"],
                    "approval_required_for": [],
                    "denied_actions": [],
                },
                requested_actions=["read_workspace"],
                mode="read_only",
                start_immediately=False,
            )
        )

        phase0_ref = self._phase0_readiness_ref(request)
        if phase0_ref.get("phase0_result_ref") or phase0_ref.get("cognitive_readiness_id"):
            run.intent_map["cognitive_readiness"] = phase0_ref
            run.bootstrap_context["cognitive_readiness"] = phase0_ref
            self.runtime.store.update_run(run)
            self.runtime.events.create(
                run.run_id,
                "phase0_prediction_attached",
                "recorded",
                "Phase 0 cognitive readiness reference attached to Phase 1 TaskRun.",
                metadata=phase0_ref,
            )

        self._transition(run, "queued")
        self.runtime.events.create(run.run_id, "run_queued", "queued", "Read-only artifact analysis queued.")
        self._transition(run, "running")
        self.runtime.events.create(run.run_id, "run_started", "running", "Read-only artifact analysis started.")
        self.runtime.store.update_run(run)

        created_artifacts: list[dict[str, Any]] = []
        analysis_payload: dict[str, Any] | None = None
        validation: dict[str, Any]
        status = "completed"
        started_monotonic = time.monotonic()
        try:
            dependency_check = self._validate_phase_dependencies(
                session_id=request.session_id,
                dependency_phase_ids=dependency_phase_ids,
                semantic=True,
            )
            if dependency_check["status"] != "passed":
                raise GovernedPhase1Block(
                    str(dependency_check.get("reason_code") or "phase_dependency_artifacts_missing"),
                    "Phase dependency check blocked inside governed TaskRun.",
                    details={
                        "phase": "phase_dependency",
                        "component": "readonly_analysis_artifact_runtime",
                        "frontier": "PHASE_DEPENDENCY",
                        "dependency_check": dependency_check,
                        "missing_outputs": list(dependency_check.get("missing") or []),
                        "safe_to_report_success": False,
                    },
                )
            self._check_phase1_budget(run.run_id, started_monotonic, stage="before_project_analysis")
            self.runtime.events.create(run.run_id, "project_analysis_started", "running", "Project analysis started.")
            analysis_prompt = self._analysis_prompt_with_dependencies(request.message, dependency_check)
            analysis_result = self.analysis.analyze_project(
                ProjectAnalysisRequest(
                    workspace=workspace,
                    prompt=analysis_prompt,
                    goal="readonly_analysis_with_artifact_output",
                    workspace_context=request_context,
                    include_trace=False,
                ),
                cancel_requested=lambda: bool((self.runtime.store.get_run(run.run_id) or run).cancellation_requested),
            )
            self._emit_project_analysis_boundary_events(run.run_id, analysis_result)
            if not analysis_result.safe_to_continue:
                raise GovernedPhase1Block(
                    analysis_result.reason_code or "PROJECT_ANALYSIS_BOUNDARY_ERROR",
                    analysis_result.error_message or "Project analysis stopped at a governed boundary.",
                    status="cancelled" if analysis_result.status == "cancelled" else "blocked",
                    details={
                        "phase": "project_analysis",
                        "component": "ProjectAnalysisService",
                        "frontier": "PROJECT_ANALYSIS",
                        "project_analysis_status": analysis_result.status,
                        "project_analysis_reason_code": analysis_result.reason_code,
                        "error_type": analysis_result.error_type,
                        "error_message": analysis_result.error_message,
                        "safe_to_continue": False,
                        "artifacts_created": 0,
                        "artifact_index_exercised": False,
                        "next_frontier": "artifact_creation",
                        "budget": analysis_result.budget,
                        "duration_ms": analysis_result.duration_ms,
                        "last_checkpoint": analysis_result.last_checkpoint,
                        "last_completed_checkpoint": analysis_result.last_completed_checkpoint,
                        "elapsed_ms_by_checkpoint": analysis_result.elapsed_ms_by_checkpoint,
                        "files_discovered": analysis_result.files_discovered,
                        "files_scan_attempted": analysis_result.files_scan_attempted,
                        "files_scanned": analysis_result.files_scanned,
                        "files_read": analysis_result.files_read,
                        "bytes_read": analysis_result.bytes_read,
                        "current_root": analysis_result.current_root,
                        "current_path_sample": analysis_result.current_path_sample,
                        "blocking_operation": analysis_result.blocking_operation,
                        "budget_exceeded_at": analysis_result.budget_exceeded_at,
                        "partial_readiness": analysis_result.partial_readiness,
                        "file_selection_plan": self._compact_project_analysis_plan(analysis_result.file_selection_plan),
                        "file_read_plan": self._compact_project_analysis_plan(analysis_result.file_read_plan),
                        "remaining_budget_ms_at_return": analysis_result.remaining_budget_ms_at_return,
                        "handoff_reserve_reached": analysis_result.handoff_reserve_reached,
                    },
                )
            self._check_phase1_budget(run.run_id, started_monotonic, stage="after_project_analysis")
            analysis_payload = self._analysis_payload(analysis_result)
            patch_planning_result = self._create_patch_plan_if_requested(
                logical_paths=logical_paths,
                workspace=workspace,
                objective=request.message,
                source_id=run.run_id,
                file_context_bundle=analysis_result.file_context,
                evidence_context=self._dependency_artifact_texts(dependency_check),
            )
            if patch_planning_result:
                analysis_payload["patch_planning"] = patch_planning_result
            entity_graph = self.observed_entities.compile(
                workspace=workspace,
                workspace_context=request_context,
                analysis_payload=analysis_payload,
                dependency_check=dependency_check,
            )
            analysis_payload["observed_entity_graph"] = entity_graph.model_dump(mode="json")
            self.runtime.events.create(
                run.run_id,
                "project_analysis_finished",
                "completed" if analysis_result.status in {"ok", "partial"} else analysis_result.status,
                "Project analysis finished.",
                metadata={
                    "analysis_result_id": analysis_result.result_id,
                    "analysis_status": analysis_result.status,
                    "reason_code": analysis_result.reason_code,
                    "safe_to_continue": analysis_result.safe_to_continue,
                    "partial_readiness": analysis_result.partial_readiness,
                },
            )

            for logical_path in logical_paths:
                self._check_phase1_budget(run.run_id, started_monotonic, stage=f"before_artifact:{logical_path}")
                started_content_type = self._content_type(logical_path)
                started_contract = dict(
                    self.artifact_semantic_contracts.compile_contract_from_prompt(
                        logical_path=logical_path,
                        prompt=request.message,
                        content_type=started_content_type,
                    )
                )
                artifact_attempt_id = f"artifact_attempt_{uuid4().hex}"
                artifact_event = self.runtime.events.create(
                    run.run_id,
                    "artifact_creation_started",
                    "running",
                    f"Artifact creation started for {logical_path}.",
                    metadata={
                        "artifact_attempt_id": artifact_attempt_id,
                        "logical_path": logical_path,
                        "producer_step": "readonly_analysis_artifact_runtime",
                        "content_type": started_content_type,
                        "contract_id": started_contract.get("contract_id"),
                        "artifact_kind": started_contract.get("expected_kind") or started_content_type,
                        "artifact_budget_ms": int(self.budget.max_artifact_render_seconds * 1000),
                        "checkpoint_interval_ms": self.budget.artifact_checkpoint_event_interval_ms,
                    },
                )
                record = self._create_artifact(
                    logical_path=logical_path,
                    request_text=request.message,
                    task_id=run.task_id,
                    task_run_id=run.run_id,
                    event_id=artifact_event.event_id,
                    session_id=request.session_id,
                    workspace=workspace,
                    workspace_context=request_context,
                    phase_id=phase_id,
                    analysis_payload=analysis_payload,
                    dependency_check=dependency_check,
                    phase_started_monotonic=started_monotonic,
                )
                record_payload = record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record)
                indexed_record = self.artifact_runtime.get(record.artifact_id) or {}
                public_record = {**indexed_record, **record_payload}
                self._reject_late_artifact_if_terminal(run.run_id, logical_path=logical_path, artifact_event_id=artifact_event.event_id)
                created_artifacts.append(public_record)
                artifact_status = str(public_record.get("status") or record.status or "ready")
                artifact_event_type = {
                    "ready": "artifact_created",
                    "partial": "artifact_partial",
                    "blocked": "artifact_blocked",
                    "interrupted": "artifact_interrupted",
                    "rejected": "artifact_late_rejected",
                }.get(artifact_status, "artifact_blocked")
                event_status = "completed" if artifact_event_type == "artifact_created" else artifact_status
                self.runtime.events.create(
                    run.run_id,
                    artifact_event_type,
                    event_status,
                    f"Artifact {artifact_status} for {logical_path}.",
                    metadata={
                        "logical_path": logical_path,
                        "artifact_id": record.artifact_id,
                        "storage_ref": record.storage_ref or record.storage_path,
                        "size_bytes": record.size_bytes,
                        "producer_step": "readonly_analysis_artifact_runtime",
                        "artifact_attempt_id": artifact_attempt_id,
                        "created_event_source_id": artifact_event.event_id,
                        "reason_code": public_record.get("reason_code") or (public_record.get("metadata") or {}).get("reason_code"),
                        "semantic_contract_status": (public_record.get("metadata") or {}).get("semantic_contract_status"),
                        "safe_to_use": public_record.get("safe_to_use", (public_record.get("metadata") or {}).get("safe_to_use")),
                    },
                )
                run.produced_artifacts = created_artifacts
                self.runtime.store.update_run(run)

            self._check_phase1_budget(run.run_id, started_monotonic, stage="before_validation")
            validation = self._validate_outputs(
                logical_paths=logical_paths,
                artifacts=created_artifacts,
                analysis_payload=analysis_payload,
            )
            self.runtime.canonical_states.bind_artifacts(run, created_artifacts, required=logical_paths)
            run.canonical_state = self.runtime.canonical_states.derive(run, artifacts=created_artifacts)
            self.runtime.store.update_run(run)
            self.runtime.events.create(
                run.run_id,
                "validation_finished",
                validation["status"],
                "Read-only artifact output validation finished.",
                metadata=validation,
            )
            if validation["status"] != "passed":
                status = "blocked"
        except GovernedPhase1Block as exc:
            status = "cancelled" if exc.status == "cancelled" else "blocked"
            effective_reason_code = str(exc.details.get("terminal_reason_code") or exc.reason_code)
            interrupted = self._interrupted_artifact_row(run.run_id, {**exc.details, "reason_code": effective_reason_code})
            if interrupted and not self._has_artifact_for_logical_path(created_artifacts, str(interrupted.get("logical_path") or "")):
                created_artifacts.append(interrupted)
                self.runtime.events.create(
                    run.run_id,
                    "artifact_interrupted" if interrupted.get("status") != "rejected" else "artifact_late_rejected",
                    str(interrupted.get("status") or "interrupted"),
                    f"Artifact render ended as {interrupted.get('status')} for {interrupted.get('logical_path')}.",
                    metadata=interrupted,
                )
            validation = {
                "status": "blocked",
                "reason_code": effective_reason_code,
                "missing_outputs": ["phase1_terminal_success_contract"],
                "safe_to_report_success": False,
                "details": exc.details,
                "phase": exc.details.get("phase") or "phase1",
                "component": exc.details.get("component") or "readonly_analysis_artifact_runtime",
                "frontier": exc.details.get("frontier") or str(exc.details.get("stage") or "PHASE1_RUNTIME"),
                "artifacts_created": len(created_artifacts),
                "artifact_index_exercised": bool(created_artifacts),
            }
            self._emit_terminal_event(
                run.run_id,
                "run_cancelled" if status == "cancelled" else "run_blocked",
                status,
                str(exc),
                metadata={"reason_code": effective_reason_code, **exc.details},
            )
        except Exception as exc:
            status = "blocked"
            artifact_event = self._artifact_creation_in_progress(run.run_id)
            artifact_failure_reason = (
                "ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING"
                if artifact_event is not None
                else "readonly_artifact_execution_failed"
            )
            exception_context = self._safe_exception_summary(
                exc,
                run_id=run.run_id,
                component="readonly_analysis_artifact_runtime",
                function="execute",
                stage="artifact_creation" if artifact_event is not None else "readonly_artifact_execution",
                artifact_event=artifact_event,
            )
            if artifact_event is not None:
                logical_path = str((artifact_event.metadata or {}).get("logical_path") or "")
                artifact_row = self._guard_artifact_row(
                    task_run_id=run.run_id,
                    logical_path=logical_path,
                    producer_step=str((artifact_event.metadata or {}).get("producer_step") or "readonly_analysis_artifact_runtime"),
                    reason_code=artifact_failure_reason,
                    artifact_event_id=artifact_event.event_id,
                )
                if artifact_row and not self._has_artifact_for_logical_path(created_artifacts, logical_path):
                    created_artifacts.append(artifact_row)
                self.runtime.events.create(
                    run.run_id,
                    "artifact_creation_exception_captured",
                    "blocked",
                    "Artifact creation exception captured after accepted_running.",
                    metadata={
                        "logical_path": logical_path,
                        "reason_code": artifact_failure_reason,
                        "producer_step": (artifact_event.metadata or {}).get("producer_step"),
                        "created_event_source_id": artifact_event.event_id,
                        "exception": exception_context,
                    },
                )
                self.runtime.events.create(
                    run.run_id,
                    "artifact_failed",
                    "blocked",
                    "Artifact creation failed before producing a terminal artifact.",
                    metadata={
                        "logical_path": logical_path,
                        "reason_code": artifact_failure_reason,
                        "producer_step": (artifact_event.metadata or {}).get("producer_step"),
                        "created_event_source_id": artifact_event.event_id,
                        "safe_to_use": False,
                        "exception": exception_context,
                    },
                )
            validation = {
                "status": "blocked",
                "reason_code": artifact_failure_reason,
                "error_type": type(exc).__name__,
                "error_message": (str(exc) or type(exc).__name__)[:500],
                "exception_context": exception_context,
                "failure_source": "artifact_runtime_exception" if artifact_event is not None else "readonly_artifact_execution",
                "result_builder_source": "phase_semantic_completion_policy",
                "reason_family": "artifact_runtime_exception" if artifact_event is not None else "readonly_artifact_execution",
                "missing_outputs": [artifact_failure_reason, "artifact_result", "validation_result"],
                "safe_to_report_success": False,
                "phase": "phase1",
                "component": "readonly_analysis_artifact_runtime",
                "frontier": "ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP"
                if artifact_event is not None
                else "READONLY_ARTIFACT_EXECUTION",
            }
            self._emit_terminal_event(
                run.run_id,
                "run_failed",
                "blocked",
                "Read-only artifact analysis failed before completion.",
                metadata=validation,
            )

        final_artifacts = self._terminal_artifact_summaries(created_artifacts)
        self.runtime.events.create(
            run.run_id,
            "runtime_finalization_checkpoint",
            "running",
            "Post-validation result finalization reached before phase semantic completion policy.",
            metadata={
                "stage": "before_phase_semantic_completion_policy",
                "artifact_count": len(final_artifacts),
                "reason_code": validation.get("reason_code"),
                "bounded": True,
            },
        )
        phase_completion_decision = self.phase_semantic_completion_policy.evaluate(
            phase_id=phase_id,
            phase_kind="discovery",
            runtime_status=status,
            validation=validation,
            artifacts=final_artifacts,
        )
        self.runtime.events.create(
            run.run_id,
            "runtime_finalization_checkpoint",
            "running",
            "Post-validation result finalization reached after phase semantic completion policy.",
            metadata={
                "stage": "after_phase_semantic_completion_policy",
                "artifact_count": len(final_artifacts),
                "reason_code": phase_completion_decision.reason_code,
                "bounded": True,
            },
        )
        validation = self._apply_phase_completion_decision(validation, phase_completion_decision)
        completion = self._completion(
            logical_paths,
            final_artifacts,
            validation,
            status=status,
            phase_decision=phase_completion_decision,
        )
        result_status = "completed" if status == "completed" and completion.status == "completed" else "cancelled" if status == "cancelled" else "blocked"
        self.runtime.events.create(
            run.run_id,
            "runtime_finalization_checkpoint",
            "running",
            "Post-validation result finalization reached before TaskRunResult build.",
            metadata={
                "stage": "before_taskrun_result_build",
                "artifact_count": len(final_artifacts),
                "result_status": result_status,
                "reason_code": validation.get("reason_code"),
                "bounded": True,
            },
        )
        result = TaskRunResult(
            run_id=run.run_id,
            status=result_status,
            source="phase_semantic_completion_policy",
            reason_code=None if result_status == "completed" else str(validation.get("reason_code") or ""),
            finished_at=datetime.now(timezone.utc).isoformat(),
            summary=(
                f"Read-only analysis generated {len(created_artifacts)} governed artifact(s)."
                if result_status == "completed"
                else "Read-only analysis was cancelled at a governed checkpoint."
                if result_status == "cancelled"
                else "Read-only analysis did not satisfy required artifact outputs."
            ),
            outputs={
                "project_analysis_report": analysis_payload,
                "project_analysis_boundary": validation.get("details", {}) if validation.get("phase") == "project_analysis" else {},
                "artifact_result": {
                    "artifact_ids": [item.get("artifact_id") for item in final_artifacts],
                    "logical_paths": logical_paths,
                    "artifacts": final_artifacts,
                    "artifact_state": self._artifact_state(final_artifacts, validation),
                },
                "artifact_runtime_failure": {
                    "status": "present" if validation.get("exception_context") else "not_available",
                    "reason_code": validation.get("reason_code"),
                    "failure_source": validation.get("failure_source"),
                    "result_builder_source": validation.get("result_builder_source"),
                    "reason_family": validation.get("reason_family"),
                    "exception": validation.get("exception_context") or {},
                    "safe_to_report_success": False,
                },
                "validation_result": validation,
                "phase_dependency_result": dependency_check,
                "phase_semantic_completion_decision": phase_completion_decision.metadata
                | {
                    "status": phase_completion_decision.status,
                    "reason_code": phase_completion_decision.reason_code,
                    "safe_to_report_success": phase_completion_decision.safe_to_report_success,
                    "phase_contract_status": phase_completion_decision.phase_contract_status,
                    "artifact_sufficiency_status": phase_completion_decision.artifact_sufficiency_status,
                    "safe_for_limited_discovery": phase_completion_decision.safe_for_limited_discovery,
                    "partial_artifact_accepted": phase_completion_decision.partial_artifact_accepted,
                    "phase_dependency": phase_completion_decision.phase_dependency,
                },
            },
            warnings=[] if result_status == "completed" else ["task_run_cancelled"] if result_status == "cancelled" else ["artifact_validation_failed"],
            blocked_items=list(validation.get("blocking_findings") or validation.get("missing_outputs") or []),
            events_count=len(self.runtime.events.list(run.run_id)),
            trace_ref=f"task-runs/{run.run_id}/trace",
            validation={
                "status": validation["status"],
                "score": 1.0 if validation["status"] == "passed" else 0.0,
                "safe_to_display": True,
                "reason_code": validation.get("reason_code"),
                "phase_contract_status": validation.get("phase_contract_status"),
                "artifact_sufficiency_status": validation.get("artifact_sufficiency_status"),
                "safe_for_limited_discovery": validation.get("safe_for_limited_discovery"),
                "blocking_findings": list(validation.get("blocking_findings") or validation.get("missing_outputs") or []),
                "limiting_findings": list(validation.get("limiting_findings") or []),
            },
            completion=completion,
        )

        self.runtime.events.create(
            run.run_id,
            "runtime_finalization_checkpoint",
            "running",
            "Post-validation result finalization reached before result persistence.",
            metadata={
                "stage": "before_taskrun_result_persist",
                "artifact_count": len(final_artifacts),
                "result_status": result_status,
                "reason_code": result.reason_code,
                "bounded": True,
            },
        )
        self._transition(run, result_status)
        self.runtime.canonical_states.bind_artifacts(run, final_artifacts, required=logical_paths)
        self.runtime.store.save_result(run.run_id, result)
        self.runtime.events.create(
            run.run_id,
            "runtime_finalization_checkpoint",
            "running",
            "Post-validation result finalization persisted TaskRunResult.",
            metadata={
                "stage": "after_taskrun_result_persist",
                "artifact_count": len(final_artifacts),
                "result_status": result_status,
                "reason_code": result.reason_code,
                "bounded": True,
            },
        )
        self._emit_terminal_event(
            run.run_id,
            "run_completed" if result_status == "completed" else "run_cancelled" if result_status == "cancelled" else "run_blocked",
            result_status,
            result.summary,
        )
        self._calibrate_phase0_prediction(run.run_id, phase0_ref)
        truth = self.runtime.truth.evaluate(run, result=result, timeline=self.runtime.timeline.build(run.run_id))
        run.canonical_state = self.runtime.canonical_states.derive(
            run,
            result=result,
            truth=truth,
            artifacts=final_artifacts,
        )
        self.runtime.store.update_run(run)
        if status == "completed":
            self._record_phase(
                session_id=request.session_id,
                phase_id=phase_id,
                run_id=run.run_id,
                workspace=workspace,
                artifacts=final_artifacts,
                logical_paths=logical_paths,
                patch_plan_id=self._patch_plan_id(analysis_payload),
            )

        response = self._response(
            request,
            workspace=workspace,
            label=label,
            task_id=run.task_id,
            run_id=run.run_id,
            logical_paths=logical_paths,
            artifacts=final_artifacts,
            validation=validation,
            completion=completion,
            dependency_check=dependency_check,
            status=status,
        )
        return ReadonlyArtifactExecution(
            response=response,
            run_id=run.run_id,
            created_artifacts=created_artifacts,
            validation=validation,
        )

    def _create_artifact(
        self,
        *,
        logical_path: str,
        request_text: str,
        task_id: str | None,
        task_run_id: str,
        event_id: str,
        session_id: str | None,
        workspace: str,
        workspace_context: dict[str, Any],
        phase_id: str,
        analysis_payload: dict[str, Any],
        dependency_check: dict[str, Any],
        phase_started_monotonic: float | None = None,
    ):
        content_type = self._content_type(logical_path)
        declared_contract = self.artifact_semantic_contracts.compile_contract_from_prompt(
            logical_path=logical_path,
            prompt=request_text,
            content_type=content_type,
        )
        declared_contract = dict(declared_contract)
        declared_contract["artifact_logical_path"] = logical_path
        declared_contract["artifact_kind"] = declared_contract.get("expected_kind") or content_type
        declared_contract["task_run_id"] = task_run_id
        declared_contract["workspace_context"] = workspace_context
        render_started = time.monotonic()
        render_result = self._artifact_content(
            logical_path=logical_path,
            request_text=request_text,
            content_type=content_type,
            run_id=task_run_id,
            workspace=workspace,
            workspace_context=workspace_context,
            phase_id=phase_id,
            analysis_payload=analysis_payload,
            dependency_check=dependency_check,
            declared_contract=declared_contract,
            phase_started_monotonic=phase_started_monotonic,
            artifact_started_monotonic=render_started,
        )
        render_elapsed = time.monotonic() - render_started
        if render_elapsed > self.budget.max_artifact_render_seconds:
            raise GovernedPhase1Block(
                "ARTIFACT_RENDER_BUDGET_EXCEEDED",
                f"Artifact render budget exceeded for {logical_path}.",
                details={
                    "logical_path": logical_path,
                    "elapsed_seconds": round(render_elapsed, 3),
                    "max_artifact_render_seconds": self.budget.max_artifact_render_seconds,
                },
            )
        self._check_artifact_render_checkpoint(
            task_run_id,
            phase_started_monotonic or render_started,
            render_started,
            stage="before_registry_create",
            logical_path=logical_path,
        )
        if render_result.semantic_gaps:
            declared_contract["runtime_semantic_gaps"] = render_result.semantic_gaps
        if render_result.schema_coverage:
            declared_contract["schema_coverage"] = render_result.schema_coverage
        if render_result.entity_summary:
            declared_contract["observed_entities"] = render_result.entity_summary.get("entities", [])
            declared_contract["observed_entity_summary"] = render_result.entity_summary
            if render_result.entity_summary.get("perception"):
                declared_contract["perception"] = render_result.entity_summary.get("perception")
                plan = (render_result.entity_summary.get("perception") or {}).get("contract_observation_plan") or {}
                declared_contract["attribute_contracts"] = plan.get("attribute_contracts") or []
                declared_contract["canonical_schema"] = plan.get("expected_attributes") or declared_contract.get("expected_schema") or []
            if render_result.entity_summary.get("semantic_coverage"):
                declared_contract["semantic_coverage"] = render_result.entity_summary.get("semantic_coverage")
        self._check_artifact_render_checkpoint(
            task_run_id,
            phase_started_monotonic or render_started,
            render_started,
            stage="before_artifact_semantic_profile",
            logical_path=logical_path,
            rows_rendered=render_result.bound_rows,
            rows_expected=render_result.expected_rows,
            cells_rendered=None,
        )
        semantic_decision = self._semantic_artifact_render_decision(
            logical_path=logical_path,
            content_type=content_type,
            content=render_result.content,
            declared_contract=declared_contract,
            render_result=render_result,
        )
        self._check_artifact_render_checkpoint(
            task_run_id,
            phase_started_monotonic or render_started,
            render_started,
            stage="after_artifact_semantic_profile",
            logical_path=logical_path,
            rows_rendered=render_result.bound_rows,
            rows_expected=render_result.expected_rows,
            cells_rendered=None,
        )
        declared_contract["artifact_render_semantic_decision"] = semantic_decision
        declared_contract = self._compact_declared_contract_for_artifact(declared_contract)
        encoding = "base64" if content_type == "application/zip" else "text"
        artifact_evidence_refs = list(
            dict.fromkeys(
                [
                    f"task_run:{task_run_id}",
                    f"phase:{phase_id}",
                    *(str(ref) for ref in (render_result.evidence_refs_sample or []) if ref),
                ]
            )
        )
        self._check_artifact_render_checkpoint(
            task_run_id,
            phase_started_monotonic or render_started,
            render_started,
            stage="before_artifact_persist",
            logical_path=logical_path,
            rows_rendered=render_result.bound_rows,
            rows_expected=render_result.expected_rows,
            cells_rendered=None,
        )
        artifact = self.artifact_runtime.create(
            ArtifactRuntimeCreateRequest(
                source_agent="aipinho",
                task_id=task_id,
                task_run_id=task_run_id,
                session_id=session_id,
                logical_path=logical_path,
                artifact_type="readonly_analysis_report",
                content_type=content_type,
                content=render_result.content,
                encoding=encoding,
                producer_step="readonly_analysis_artifact_runtime",
                event_id=event_id,
                validation_status=str(semantic_decision.get("validation_status") or "validated"),
                status=str(semantic_decision.get("artifact_status") or "ready"),
                evidence_refs=artifact_evidence_refs,
                provenance={
                    "runtime": "readonly_analysis_artifact_runtime",
                    "workspace": workspace,
                    "workspace_context": workspace_context,
                    "phase_id": phase_id,
                    "logical_path": logical_path,
                    "project_analysis_status": analysis_payload.get("status"),
                    "project_analysis_reason_code": analysis_payload.get("reason_code"),
                    "project_analysis_partial_readiness": analysis_payload.get("partial_readiness"),
                    "declared_contract": declared_contract,
                    "workspace_mutation": False,
                    "semantic_contract_status": semantic_decision.get("semantic_contract_status"),
                    "semantic_contract_reason_code": semantic_decision.get("reason_code"),
                    "row_evidence_coverage": render_result.row_evidence_coverage or {},
                },
                metadata={
                    "logical_path": logical_path,
                    "declared_contract": declared_contract,
                    "phase_id": phase_id,
                    "workspace": workspace,
                    "owner_task_id": task_id,
                    "task_run_id": task_run_id,
                    "artifact_generation": True,
                    "project_analysis_status": analysis_payload.get("status"),
                    "project_analysis_reason_code": analysis_payload.get("reason_code"),
                    "project_analysis_partial_readiness": analysis_payload.get("partial_readiness"),
                    "patch_plan_id": self._patch_plan_id(analysis_payload),
                    "status": semantic_decision.get("artifact_status"),
                    "validation_status": semantic_decision.get("validation_status"),
                    "reason_code": semantic_decision.get("reason_code"),
                    "semantic_contract_status": semantic_decision.get("semantic_contract_status"),
                    "semantic_contract_validation": semantic_decision.get("semantic_contract_validation"),
                    "limitations": semantic_decision.get("limitations"),
                    "safe_to_use": semantic_decision.get("safe_to_use"),
                    "safe_for_limited_discovery": semantic_decision.get("safe_for_limited_discovery"),
                    "partial_rows": render_result.partial_rows,
                    "expected_rows": render_result.expected_rows,
                    "selected_rows": render_result.selected_rows,
                    "bound_rows": render_result.bound_rows,
                    "evidence_ref_count": render_result.evidence_ref_count,
                    "evidence_refs_sample": render_result.evidence_refs_sample or [],
                    "row_evidence_coverage": render_result.row_evidence_coverage or {},
                    "row_validation_summary": render_result.row_validation_summary or {},
                    "schema_coverage": render_result.schema_coverage or {},
                    "metadata_coverage_summary": (render_result.schema_coverage or {}).get("metadata_coverage_summary", {}),
                    "inventory_sufficiency_summary": (render_result.schema_coverage or {}).get("inventory_sufficiency_summary", {}),
                    "rendered_columns": render_result.rendered_columns or [],
                    "missing_columns": render_result.missing_columns or [],
                },
            ),
            progress_observer=lambda stage, metrics: self._check_artifact_render_checkpoint(
                task_run_id,
                phase_started_monotonic or render_started,
                render_started,
                stage=stage,
                logical_path=logical_path,
                rows_rendered=render_result.bound_rows,
                rows_expected=render_result.expected_rows,
                cells_rendered=None,
                extra_metadata=self._artifact_persist_checkpoint_metrics(
                    metrics,
                    render_result=render_result,
                    semantic_decision=semantic_decision,
                ),
            ),
        )
        self._check_artifact_render_checkpoint(
            task_run_id,
            phase_started_monotonic or render_started,
            render_started,
            stage="after_artifact_persist",
            logical_path=logical_path,
            rows_rendered=render_result.bound_rows,
            rows_expected=render_result.expected_rows,
            cells_rendered=None,
            extra_metadata={
                "artifact_id": artifact.artifact_id,
                "artifact_content_bytes": artifact.size_bytes,
                "checksum": artifact.sha256,
                "storage_ref_present": bool(artifact.storage_ref or artifact.storage_path),
            },
        )
        self._check_artifact_render_checkpoint(
            task_run_id,
            phase_started_monotonic or render_started,
            render_started,
            stage="after_registry_create_before_event",
            logical_path=logical_path,
        )
        return artifact

    def _semantic_artifact_render_decision(
        self,
        *,
        logical_path: str,
        content_type: str,
        content: str,
        declared_contract: dict[str, Any],
        render_result: ArtifactRenderResult,
    ) -> dict[str, Any]:
        contract_id = str(declared_contract.get("contract_id") or "")
        if render_result.semantic_gaps:
            declared_contract["runtime_semantic_gaps"] = render_result.semantic_gaps
        validation = self.artifact_semantic_contracts.validate(
            logical_path=logical_path,
            content=content,
            content_type=content_type,
            declared_contract=declared_contract,
        )
        profile = validation.profile.model_dump(mode="json") if validation.profile else None
        missing = list(validation.missing_requirements)
        warnings = list(validation.warnings)
        reason_codes = self._semantic_validation_reason_codes(profile, missing)
        if render_result.status == "partial":
            render_reason = render_result.reason_code or "ARTIFACT_RENDER_PARTIAL"
            artifact_status = "partial" if self.budget.allow_partial_artifact else "blocked"
            validation_status = "partial" if self.budget.allow_partial_artifact else "blocked"
            return {
                "artifact_status": artifact_status,
                "validation_status": validation_status,
                "semantic_contract_status": "partial",
                "reason_code": render_reason,
                "safe_to_use": False,
                "safe_for_limited_discovery": bool(
                    (render_result.bound_rows or 0) > 0
                    and (render_result.evidence_ref_count or 0) > 0
                    and (render_result.row_evidence_coverage or {}).get("status") == "satisfied"
                ),
                "limitations": list(dict.fromkeys([*missing, *warnings, render_reason])),
                "semantic_contract_validation": {
                    "status": validation.status,
                    "contract_id": validation.contract_id,
                    "missing_requirements": missing,
                    "warnings": warnings,
                    "reason_codes": list(dict.fromkeys([*reason_codes, render_reason])),
                    "profile": profile,
                    "render_status": render_result.status,
                    "partial_rows": render_result.partial_rows,
                    "expected_rows": render_result.expected_rows,
                    "selected_rows": render_result.selected_rows,
                    "bound_rows": render_result.bound_rows,
                    "evidence_ref_count": render_result.evidence_ref_count,
                    "row_validation_summary": render_result.row_validation_summary or {},
                },
            }
        if validation.status == "passed":
            return {
                "artifact_status": "ready",
                "validation_status": "validated",
                "semantic_contract_status": "satisfied",
                "reason_code": None,
                "safe_to_use": True,
                "safe_for_limited_discovery": True,
                "limitations": [],
                "semantic_contract_validation": {
                    "status": validation.status,
                    "contract_id": validation.contract_id,
                    "missing_requirements": missing,
                    "warnings": warnings,
                    "reason_codes": reason_codes,
                    "profile": profile,
                    "row_validation_summary": render_result.row_validation_summary or {},
                },
            }
        semantic_contract_status = "insufficient"
        artifact_status = "blocked"
        validation_status = "blocked"
        safe_to_use = False
        if self._semantic_partial_allowed(contract_id, profile=profile, missing=missing, reason_codes=reason_codes):
            semantic_contract_status = "partial"
            artifact_status = "partial"
            validation_status = "partial"
        reason_code = self._semantic_decision_reason_code(reason_codes, missing, semantic_contract_status=semantic_contract_status)
        return {
            "artifact_status": artifact_status,
            "validation_status": validation_status,
            "semantic_contract_status": semantic_contract_status,
            "reason_code": reason_code,
            "safe_to_use": safe_to_use,
            "limitations": list(dict.fromkeys([*missing, *warnings, reason_code])),
            "semantic_contract_validation": {
                "status": validation.status,
                "contract_id": validation.contract_id,
                "missing_requirements": missing,
                "warnings": warnings,
                "reason_codes": reason_codes,
                "profile": profile,
                "row_validation_summary": render_result.row_validation_summary or {},
            },
        }

    def _semantic_partial_allowed(
        self,
        contract_id: str,
        *,
        profile: dict[str, Any] | None,
        missing: list[str],
        reason_codes: list[str],
    ) -> bool:
        if contract_id != "media_corpus_inventory_artifact":
            return False
        critical = {
            "media_inventory_findings_shape_mismatch",
            "media_inventory_rows_missing",
            "media_inventory_entity_identity_missing",
            "media_inventory_source_root_role_missing",
            "media_inventory_evidence_ref_missing",
        }
        if any(item in critical for item in missing):
            return False
        observed = (profile or {}).get("observed_semantics") if isinstance((profile or {}).get("observed_semantics"), dict) else {}
        row_count = int(observed.get("row_count") or 0)
        return row_count > 0 and "MUSIC_INVENTORY_PARTIAL_EVIDENCE" in reason_codes

    def _semantic_validation_reason_codes(self, profile: dict[str, Any] | None, missing: list[str]) -> list[str]:
        reason_codes: list[str] = []
        for gap in (profile or {}).get("semantic_gaps") or []:
            if isinstance(gap, dict) and gap.get("reason_code"):
                reason_codes.append(str(gap.get("reason_code")))
        if not reason_codes and missing:
            reason_codes.append("MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT")
        return list(dict.fromkeys(reason_codes))

    def _semantic_decision_reason_code(
        self,
        reason_codes: list[str],
        missing: list[str],
        *,
        semantic_contract_status: str,
    ) -> str:
        if semantic_contract_status == "partial" and "MUSIC_INVENTORY_PARTIAL_EVIDENCE" in reason_codes:
            return "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
        return next(iter(reason_codes), None) or next(iter(missing), None) or "ARTIFACT_SEMANTIC_CONTRACT_BLOCKED"

    def _compact_declared_contract_for_artifact(self, declared_contract: dict[str, Any]) -> dict[str, Any]:
        contract = dict(declared_contract)
        perception = contract.get("perception") if isinstance(contract.get("perception"), dict) else {}
        if not perception:
            return contract
        binding = self._artifact_observation_binding(perception)
        if binding:
            contract["artifact_observation_binding"] = binding
        relationship_binding = self._artifact_relationship_binding(perception)
        if relationship_binding:
            contract["artifact_relationship_binding"] = relationship_binding
        compact_perception = {
            "media_metadata_capability": perception.get("media_metadata_capability", {}),
            "relationship_summary": perception.get("relationship_summary", {}),
            "relationship_rendering": perception.get("relationship_rendering", {}),
            "semantic_coverage_report": perception.get("semantic_coverage_report", {}),
            "semantic_coverage_2": perception.get("semantic_coverage_2", {}),
            "semantic_self_review": self._compact_self_review(perception.get("semantic_self_review")),
            "observation_summary": self._observation_summary(perception),
            "large_payload_policy": {
                "status": "summarized",
                "reason_code": "RUNTIME_PAYLOAD_SPILLED_TO_REF",
                "full_runtime_payload_inline": False,
            },
        }
        contract["perception"] = compact_perception
        summary = contract.get("observed_entity_summary") if isinstance(contract.get("observed_entity_summary"), dict) else {}
        if summary:
            contract["observed_entity_summary"] = self._compact_entity_summary(summary)
        return contract

    def _artifact_observation_binding(self, perception: dict[str, Any]) -> dict[str, Any]:
        observations = perception.get("attribute_observations") if isinstance(perception.get("attribute_observations"), list) else []
        counts: dict[str, int] = {}
        evidence_refs: dict[str, list[str]] = {}
        sample: list[dict[str, Any]] = []
        for item in observations:
            if not isinstance(item, dict) or item.get("observation_state") != "observed":
                continue
            value = item.get("observed_value")
            if value in (None, ""):
                continue
            key = str(item.get("canonical_key") or item.get("attribute_name") or "")
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
            refs = evidence_refs.setdefault(key, [])
            refs.extend(str(ref) for ref in item.get("evidence_refs") or [] if ref and str(ref) not in refs)
            if len(sample) < 100:
                sample.append(
                    {
                        "observation_id": item.get("observation_id"),
                        "entity_id": item.get("entity_id"),
                        "canonical_key": key,
                        "attribute_name": item.get("attribute_name") or key,
                        "evidence_refs": list(item.get("evidence_refs") or [])[:5],
                        "capability_id": item.get("capability_id"),
                        "observer_id": item.get("observer_id"),
                        "confidence": item.get("confidence"),
                        "provenance": {
                            "source": (item.get("provenance") or {}).get("source"),
                            "capability_decision_id": (item.get("provenance") or {}).get("capability_decision_id"),
                        },
                    }
                )
        return {
            "status": "bound" if counts else "empty",
            "bound_counts_by_canonical_key": counts,
            "bound_observed_canonical_keys": sorted(counts),
            "bound_evidence_refs_by_canonical_key": {key: refs[:20] for key, refs in evidence_refs.items()},
            "bound_observations": sample,
            "bound_observation_count": sum(counts.values()),
            "source": "AttributeObservation",
        }

    def _artifact_relationship_binding(self, perception: dict[str, Any]) -> dict[str, Any]:
        observations = perception.get("relationship_observations") if isinstance(perception.get("relationship_observations"), list) else []
        candidates = perception.get("relationship_candidates") if isinstance(perception.get("relationship_candidates"), list) else []
        evidence = perception.get("relationship_evidence") if isinstance(perception.get("relationship_evidence"), list) else []
        traces = perception.get("relationship_provenance_traces") if isinstance(perception.get("relationship_provenance_traces"), list) else []
        candidate_by_id = {
            str(item.get("candidate_id")): item
            for item in candidates
            if isinstance(item, dict) and item.get("candidate_id")
        }
        sample: list[dict[str, Any]] = []
        family_counts: dict[str, int] = {}
        confidence_values: list[float] = []
        for item in observations:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or "")
            candidate = candidate_by_id.get(candidate_id, {})
            family = str(item.get("observed_relation_family") or candidate.get("relation_family") or "")
            if family:
                family_counts[family] = family_counts.get(family, 0) + 1
            confidence = float(item.get("confidence") or candidate.get("confidence") or 0.0)
            confidence_values.append(confidence)
            if len(sample) < 100:
                sample.append(
                    {
                        "observation_id": item.get("observation_id"),
                        "candidate_id": candidate_id,
                        "source_entity_id": candidate.get("source_entity_id"),
                        "target_entity_id": candidate.get("target_entity_id"),
                        "relation_family": family,
                        "relation_kind_candidate": item.get("observed_relation_kind_candidate") or candidate.get("relation_kind_candidate"),
                        "evidence_refs": list(item.get("evidence_refs") or candidate.get("evidence_refs") or [])[:10],
                        "provenance_trace_id": item.get("provenance_trace_id") or candidate.get("provenance_trace_id"),
                        "capability_id": item.get("producer_capability_id") or candidate.get("capability_id"),
                        "confidence": confidence,
                        "confidence_model": item.get("confidence_model") or candidate.get("confidence_model") or {},
                        "negative_evidence": list(item.get("negative_evidence") or candidate.get("negative_evidence") or [])[:10],
                        "conflicts": list(item.get("conflicts") or candidate.get("conflicts") or [])[:10],
                        "truth_eligible": False,
                        "validation_required": True,
                        "limitations": list(candidate.get("limitations") or [])[:10],
                    }
                )
        return {
            "status": "bound" if sample else "empty",
            "bound_relationship_observations": sample,
            "relationship_provenance_traces": [
                {
                    "trace_id": item.get("trace_id"),
                    "candidate_id": item.get("candidate_id"),
                    "producer_capability_id": item.get("producer_capability_id"),
                    "relationship_goal_id": item.get("relationship_goal_id"),
                    "signals_used_count": len(item.get("signals_used") or []),
                    "signals_rejected_count": len(item.get("signals_rejected") or []),
                    "policy_checks": list(item.get("policy_checks") or [])[:20],
                    "arbitration_decision_ref": item.get("arbitration_decision_ref"),
                    "evidence_record_refs": list(item.get("evidence_record_refs") or [])[:20],
                    "created_at": item.get("created_at"),
                }
                for item in traces[:100]
                if isinstance(item, dict)
            ],
            "bound_relationship_observation_count": len(observations),
            "candidate_count": len(candidates),
            "evidence_signal_count": len(evidence),
            "relation_families": sorted(family_counts),
            "relationship_confidence_summary": {
                "count": len(confidence_values),
                "max": round(max(confidence_values), 4) if confidence_values else 0.0,
                "average": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
            },
            "truth_eligible": False,
            "source": "RelationshipObservation",
        }

    def _observation_summary(self, perception: dict[str, Any]) -> dict[str, Any]:
        observations = perception.get("attribute_observations") if isinstance(perception.get("attribute_observations"), list) else []
        execution_results = perception.get("observation_execution_results") if isinstance(perception.get("observation_execution_results"), list) else []
        evidence_set = perception.get("evidence_set") if isinstance(perception.get("evidence_set"), dict) else {}
        records = evidence_set.get("records") if isinstance(evidence_set.get("records"), list) else []
        observed_keys = sorted({
            str(item.get("canonical_key") or item.get("attribute_name") or "")
            for item in observations
            if isinstance(item, dict) and item.get("observation_state") == "observed" and str(item.get("canonical_key") or item.get("attribute_name") or "")
        })
        return {
            "attribute_observations_total": len(observations),
            "attribute_observations_observed": len([
                item for item in observations if isinstance(item, dict) and item.get("observation_state") == "observed"
            ]),
            "observed_canonical_keys": observed_keys,
            "observation_execution_result_count": len(execution_results),
            "evidence_record_count": len(records),
            "evidence_canonical_keys": list(evidence_set.get("canonical_keys") or []),
        }

    def _compact_self_review(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {
            "truth_readiness": value.get("truth_readiness"),
            "can_promote_to_validation": value.get("can_promote_to_validation"),
            "can_speaker_claim": value.get("can_speaker_claim"),
            "reason_codes": list(value.get("reason_codes") or []),
            "evidence_count": value.get("evidence_count"),
            "assertion_count": value.get("assertion_count"),
            "knowledge_count": value.get("knowledge_count"),
        }

    def _compact_entity_summary(self, summary: dict[str, Any]) -> dict[str, Any]:
        compact = dict(summary)
        if isinstance(compact.get("perception"), dict):
            compact["perception"] = {
                "media_metadata_capability": compact["perception"].get("media_metadata_capability", {}),
                "relationship_summary": compact["perception"].get("relationship_summary", {}),
                "relationship_rendering": compact["perception"].get("relationship_rendering", {}),
                "semantic_coverage_report": compact["perception"].get("semantic_coverage_report", {}),
                "compile_stage_trace": compact["perception"].get("compile_stage_trace", [])[:40],
                "payload_metrics": compact["perception"].get("payload_metrics", {}),
                "compile_policy": compact["perception"].get("compile_policy", {}),
                "internal_reason_code": compact["perception"].get("internal_reason_code"),
            }
        if isinstance(compact.get("evidence_binding"), dict):
            binding = dict(compact["evidence_binding"])
            if isinstance(binding.get("evidence_refs_sample"), list):
                binding["evidence_refs_sample"] = binding["evidence_refs_sample"][:20]
            compact["evidence_binding"] = binding
        if isinstance(compact.get("entities"), list):
            compact["entities"] = compact["entities"][:50]
        if isinstance(compact.get("entities_rejected_by_policy"), list):
            compact["entities_rejected_by_policy"] = compact["entities_rejected_by_policy"][:100]
        return compact

    def _create_patch_plan_if_requested(
        self,
        *,
        logical_paths: list[str],
        workspace: str,
        objective: str,
        source_id: str,
        file_context_bundle: Any,
        evidence_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        if not any(
            self.artifact_semantic_contracts.contract_id_for(path)
            in {"patch_planning_artifact", "patch_preview_artifact", "risk_analysis_artifact"}
            for path in logical_paths
        ):
            return None
        planned = self.model_patch_planner.create_plan(
            workspace=workspace,
            objective=objective,
            source_id=source_id,
            file_context_bundle=file_context_bundle,
            evidence_context=evidence_context or [],
            include_trace=True,
        )
        return planned.model_dump(mode="json") if hasattr(planned, "model_dump") else dict(planned)

    def _artifact_content(
        self,
        *,
        logical_path: str,
        content_type: str,
        run_id: str,
        workspace: str,
        workspace_context: dict[str, Any],
        phase_id: str,
        analysis_payload: dict[str, Any],
        dependency_check: dict[str, Any],
        declared_contract: dict[str, Any],
        request_text: str = "",
        phase_started_monotonic: float | None = None,
        artifact_started_monotonic: float | None = None,
    ) -> ArtifactRenderResult:
        phase_started = phase_started_monotonic or time.monotonic()
        artifact_started = artifact_started_monotonic or time.monotonic()
        self._check_artifact_render_checkpoint(
            run_id,
            phase_started,
            artifact_started,
            stage="before_artifact_render",
            logical_path=logical_path,
        )
        payload = {
            "logical_path": logical_path,
            "task_run_id": run_id,
            "workspace": workspace,
            "workspace_context": workspace_context,
            "phase_id": phase_id,
            "workspace_mutation": False,
            "artifact_generation": True,
            "analysis": analysis_payload,
            "dependencies": dependency_check,
        }
        if content_type == "application/json":
            return self._render_result(json.dumps(payload, ensure_ascii=False, indent=2))
        if content_type == "application/zip":
            return self._render_result(self._evidence_archive_content(payload))
        if content_type == "text/csv":
            expected_schema = [str(item) for item in declared_contract.get("expected_schema") or [] if str(item).strip()]
            if expected_schema:
                return self._contract_tabular_collection_content(
                    expected_schema=expected_schema,
                    request_text=request_text,
                    analysis_payload=analysis_payload,
                    declared_contract=declared_contract,
                    run_id=run_id,
                    phase_started_monotonic=phase_started,
                    artifact_started_monotonic=artifact_started,
                )
            findings = analysis_payload.get("findings") or []
            rows = ["severity,title,summary"]
            for item in findings:
                rows.append(
                    ",".join(
                        json.dumps(str(item.get(key, "")), ensure_ascii=False)
                        for key in ("severity", "title", "summary")
                    )
                )
            return self._render_result("\n".join(rows) + "\n")
        contract_id = self.artifact_semantic_contracts.contract_id_for(logical_path)
        if contract_id == "patch_planning_artifact":
            return self._render_result(self._patch_planning_content(
                logical_path=logical_path,
                run_id=run_id,
                workspace=workspace,
                workspace_context=workspace_context,
                phase_id=phase_id,
                analysis_payload=analysis_payload,
                dependency_check=dependency_check,
            ))
        if contract_id == "patch_preview_artifact":
            return self._render_result(self._patch_preview_content(
                logical_path=logical_path,
                run_id=run_id,
                workspace=workspace,
                workspace_context=workspace_context,
                phase_id=phase_id,
                analysis_payload=analysis_payload,
                dependency_check=dependency_check,
            ))
        if contract_id == "risk_analysis_artifact":
            return self._render_result(self._risk_analysis_content(
                logical_path=logical_path,
                run_id=run_id,
                workspace=workspace,
                workspace_context=workspace_context,
                phase_id=phase_id,
                analysis_payload=analysis_payload,
                dependency_check=dependency_check,
            ))
        return self._render_result(
            f"# {logical_path}\n\n"
            f"- task_run_id: {run_id}\n"
            f"- workspace: {workspace}\n"
            f"- phase_id: {phase_id}\n"
            "- workspace_mutation: false\n"
            "- artifact_generation: true\n\n"
            "## Summary\n\n"
            f"{analysis_payload.get('summary') or 'No summary produced.'}\n\n"
            "## Structures\n\n"
            + "\n".join(f"- {item}" for item in analysis_payload.get("structures", []) or ["not_detected"])
            + "\n\n## Findings\n\n"
            + "\n".join(
                f"- {item.get('severity', 'info').upper()}: {item.get('title')} - {item.get('summary')}"
                for item in analysis_payload.get("findings", [])[:20]
            )
            + "\n\n## Dependency Evidence\n\n"
            + json.dumps(dependency_check, ensure_ascii=False, indent=2)
            + "\n"
        )

    def _render_result(
        self,
        content: str,
        *,
        semantic_gaps: list[dict[str, Any]] | None = None,
        schema_coverage: dict[str, Any] | None = None,
        entity_summary: dict[str, Any] | None = None,
        status: str = "completed",
        reason_code: str | None = None,
        partial_rows: int | None = None,
        expected_rows: int | None = None,
        selected_rows: int | None = None,
        bound_rows: int | None = None,
        evidence_ref_count: int | None = None,
        rendered_columns: list[str] | None = None,
        missing_columns: list[str] | None = None,
        row_validation_summary: dict[str, Any] | None = None,
        evidence_refs_sample: list[str] | None = None,
        row_evidence_coverage: dict[str, Any] | None = None,
        safe_to_use: bool = True,
    ) -> ArtifactRenderResult:
        return ArtifactRenderResult(
            content=content,
            semantic_gaps=semantic_gaps or [],
            schema_coverage=schema_coverage or {},
            entity_summary=entity_summary or {},
            status=status,
            reason_code=reason_code,
            partial_rows=partial_rows,
            expected_rows=expected_rows,
            selected_rows=selected_rows,
            bound_rows=bound_rows,
            evidence_ref_count=evidence_ref_count,
            rendered_columns=rendered_columns,
            missing_columns=missing_columns,
            row_validation_summary=row_validation_summary,
            evidence_refs_sample=evidence_refs_sample,
            row_evidence_coverage=row_evidence_coverage,
            safe_to_use=safe_to_use,
        )

    def _contract_tabular_collection_content(
        self,
        *,
        expected_schema: list[str],
        analysis_payload: dict[str, Any],
        declared_contract: dict[str, Any] | None = None,
        request_text: str = "",
        run_id: str | None = None,
        phase_started_monotonic: float | None = None,
        artifact_started_monotonic: float | None = None,
    ) -> ArtifactRenderResult:
        render_run_id = run_id or str((declared_contract or {}).get("task_run_id") or "unbound")
        phase_started = phase_started_monotonic or time.monotonic()
        artifact_started = artifact_started_monotonic or time.monotonic()
        logical_path = str((declared_contract or {}).get("artifact_logical_path") or "")
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="before_entity_iteration",
            logical_path=logical_path,
        )
        graph = analysis_payload.get("observed_entity_graph")
        graph_payload = graph if isinstance(graph, dict) else {"entities": [], "semantic_gaps": []}
        all_entities = [item for item in graph_payload.get("entities") or [] if isinstance(item, dict)]
        max_entities = max(1, min(int(getattr(self.budget, "max_artifact_entities", 100) or 100), self.budget.max_artifact_rows))
        intent_plan = self.semantic_intents.resolve(
            prompt=request_text,
            declared_contract=declared_contract,
            workspace_context=(declared_contract or {}).get("workspace_context")
            if isinstance((declared_contract or {}).get("workspace_context"), dict)
            else {},
            artifact_logical_path=logical_path,
            known_phase_context={"phase": (declared_contract or {}).get("phase_id")},
        )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_intent_resolution",
            logical_path=logical_path,
            rows_expected=len(all_entities),
        )
        selection_result = self.semantic_entity_selection.select(
            graph=graph_payload,
            intent=intent_plan,
            max_entities=max_entities,
        )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_entity_selection",
            logical_path=logical_path,
            rows_rendered=0,
            rows_expected=selection_result.selected_rows,
        )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="before_perception_payload_compile",
            logical_path=logical_path,
            rows_rendered=0,
            rows_expected=selection_result.selected_rows,
        )
        semantic_selection_applies = intent_plan.semantic_domain != "generic"
        selected_entity_ids = set(selection_result.selected_entity_ids)
        if semantic_selection_applies:
            selected_for_window = [
                item
                for item in all_entities
                if str(item.get("entity_id") or "") in selected_entity_ids
            ]
            graph_payload = {**graph_payload, "entities": selected_for_window}
        else:
            selected_for_window = all_entities[:max_entities]
        entity_budget_gap: dict[str, Any] | None = None
        if len(all_entities) > max_entities or (semantic_selection_applies and selection_result.expected_rows > selection_result.selected_rows):
            if not semantic_selection_applies:
                graph_payload = {**graph_payload, "entities": selected_for_window}
            entity_budget_gap = {
                "gap_type": "artifact_render_entity_budget_partial",
                "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
                if intent_plan.artifact_kind == "media_corpus_inventory"
                else "ARTIFACT_RENDER_PARTIAL",
                "perception_domain": "artifact_runtime",
                "severity": "medium",
                "expected": selection_result.expected_rows if semantic_selection_applies else len(all_entities),
                "observed": selection_result.selected_rows if semantic_selection_applies else max_entities,
                "confidence": 1.0,
                "repair_hint": "Artifact render used a governed entity window to avoid unbounded perception/render work.",
                "evidence_refs": [],
                "details": {
                    "total_entities": len(all_entities),
                    "eligible_entities": selection_result.expected_rows,
                    "selected_entities": selection_result.selected_rows,
                    "bound_rows": selection_result.bound_rows,
                    "rendered_entity_budget": max_entities,
                    "partial_artifact": True,
                },
            }
        semantic_selection_gaps = [item for item in selection_result.semantic_gaps if isinstance(item, dict)]
        perception_contract = dict(declared_contract or {})
        perception_contract["expected_schema"] = expected_schema
        perception_contract["artifact_intent_plan"] = intent_plan.model_dump(mode="json")
        perception_contract["semantic_entity_selection"] = selection_result.model_dump(mode="json")
        perception_contract["perception_compile_policy"] = {
            "mode": "compile_only",
            "execute_observers": False,
            "execute_relationship_detection": False,
            "max_observer_executions": 0,
            "max_materialized_payload_bytes": 2_000_000,
            "max_payload_items": 250_000,
            **dict((declared_contract or {}).get("perception_compile_policy") or {}),
            "caller_component": "readonly_analysis_artifact_runtime",
        }
        perception_result = self.perception.compile(
            graph=graph_payload,
            declared_contract=perception_contract,
            stage_observer=lambda item: self._check_artifact_render_checkpoint(
                render_run_id,
                phase_started,
                artifact_started,
                stage=str(item.get("stage") or "perception_compile"),
                logical_path=logical_path,
                rows_rendered=self._int_or_none(item.get("projected_entity_count")),
                rows_expected=self._int_or_none(item.get("input_entity_count")) or selection_result.selected_rows,
                cells_rendered=self._int_or_none(item.get("payload_item_count") or item.get("required_attribute_count")),
                extra_metadata={
                    "perception_compile_stage": True,
                    "internal_reason_code": item.get("reason_code"),
                    "estimated_payload_bytes": item.get("estimated_payload_bytes"),
                    "materialized_payload_bytes": item.get("materialized_payload_bytes"),
                    "payload_ref_count": item.get("payload_ref_count"),
                    "observation_execution_result_count": item.get("observation_execution_result_count"),
                    "relationship_candidate_count": item.get("relationship_candidate_count"),
                },
            ),
        )
        perception_payload = perception_result.model_dump(mode="json")
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_perception_payload_compile",
            logical_path=logical_path,
            rows_rendered=0,
            rows_expected=selection_result.selected_rows,
            extra_metadata={
                "internal_reason_code": perception_payload.get("internal_reason_code"),
                "payload_metrics": self._bounded_perception_payload_metrics(perception_payload.get("payload_metrics")),
            },
        )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="before_contract_perception",
            logical_path=logical_path,
            rows_rendered=0,
            rows_expected=selection_result.selected_rows,
        )
        attribute_contracts = perception_payload["contract_observation_plan"].get("attribute_contracts") or []
        render_columns = [
            {
                "canonical_key": str(item.get("canonical_key") or item.get("raw_label") or ""),
                "display_label": str(item.get("display_label") or item.get("raw_label") or item.get("canonical_key") or ""),
                "raw_label": str(item.get("raw_label") or item.get("display_label") or item.get("canonical_key") or ""),
                "required": bool(item.get("evidence_required", True)) and str(item.get("requiredness") or "required") == "required" and not bool(item.get("nullable")),
            }
            for item in attribute_contracts
            if isinstance(item, dict)
        ] or [{"canonical_key": field, "display_label": field, "raw_label": field, "required": True} for field in expected_schema]
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_contract_perception",
            logical_path=logical_path,
            rows_rendered=0,
            rows_expected=selection_result.selected_rows,
            cells_rendered=len(render_columns),
        )
        if len(render_columns) > self.budget.max_artifact_columns:
            raise GovernedPhase1Block(
                "ARTIFACT_RENDER_OUTPUT_BUDGET_EXCEEDED",
                "Artifact render column budget exceeded.",
                details={
                    "phase": "artifact_render",
                    "component": "readonly_analysis_artifact_runtime",
                    "frontier": "ARTIFACT_RENDER",
                    "stage": "before_csv_row_write",
                    "logical_path": logical_path,
                    "observed_columns": len(render_columns),
                    "max_columns": self.budget.max_artifact_columns,
                },
            )
        selected_ids = set(perception_result.candidate_entity_set.selected_entity_ids)
        source_entity_ids = [str(item.get("entity_id") or "") for item in all_entities if isinstance(item, dict)]
        projected_entity_ids = [str(item.get("entity_id") or "") for item in graph_payload.get("entities") or [] if isinstance(item, dict)]
        selected_id_order = [str(item) for item in perception_result.candidate_entity_set.selected_entity_ids]
        row_model_started = time.monotonic()
        selected_entities = [
            item
            for item in graph_payload.get("entities") or []
            if isinstance(item, dict) and str(item.get("entity_id") or "") in selected_ids
        ]
        row_model_build_elapsed_ms = int(max(0.0, (time.monotonic() - row_model_started) * 1000))
        row_entity_ids = [str(item.get("entity_id") or "") for item in selected_entities]
        row_model_metrics = {
            "source_input_entity_count": len(all_entities),
            "selected_entity_count": selection_result.selected_rows,
            "projected_entity_count": len(projected_entity_ids),
            "row_model_candidate_count": len(selected_id_order),
            "row_model_accepted_count": len(selected_entities),
            "row_model_rejected_count": max(0, len(selected_id_order) - len(selected_entities)),
            "row_model_skipped_count": max(0, len(projected_entity_ids) - len(selected_entities)),
            "input_entity_set_digest": self._stable_digest(sorted(source_entity_ids)),
            "projected_entity_set_digest": self._stable_digest(sorted(projected_entity_ids)),
            "row_model_digest": self._stable_digest(sorted(row_entity_ids)),
            "render_order_digest": self._stable_digest(row_entity_ids),
            "column_schema_digest": self._stable_digest([item["canonical_key"] for item in render_columns]),
            "row_model_build_elapsed_ms": row_model_build_elapsed_ms,
            "row_order_elapsed_ms": 0,
            "cardinality_domain": "row_model",
        }
        if len(selected_entities) > self.budget.max_artifact_rows:
            raise GovernedPhase1Block(
                "ARTIFACT_RENDER_BUDGET_EXCEEDED",
                "Artifact render row budget exceeded.",
                details={
                    "phase": "artifact_render",
                    "component": "readonly_analysis_artifact_runtime",
                    "frontier": "ARTIFACT_RENDER",
                    "stage": "before_csv_row_write",
                    "logical_path": logical_path,
                    "observed_rows": len(selected_entities),
                    "max_rows": self.budget.max_artifact_rows,
                },
            )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="before_row_binding",
            logical_path=logical_path,
            rows_rendered=0,
            rows_expected=len(selected_entities),
            cells_rendered=len(render_columns),
            extra_metadata=row_model_metrics,
        )
        observed_values: dict[tuple[str, str], Any] = {}
        for observation in perception_payload.get("attribute_observations") or []:
            if not isinstance(observation, dict) or observation.get("observation_state") != "observed":
                continue
            observed_values[
                (
                    str(observation.get("entity_id") or ""),
                    str(observation.get("canonical_key") or observation.get("attribute_name") or ""),
                )
            ] = observation.get("observed_value")
        cells_rendered = len(render_columns)
        csv_cells_expected = len(selected_entities) * len(render_columns)
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow([item["display_label"] for item in render_columns])
        csv_stream_started = time.monotonic()
        csv_row_render_elapsed_ms = 0
        csv_cell_render_elapsed_ms = 0
        csv_cell_serialization_elapsed_ms = 0
        max_batch_elapsed_ms = 0
        last_batch_monotonic = csv_stream_started
        rows_written = 0
        rows_failed = 0
        semantic_gaps = [
            item
            for item in [
                *(graph_payload.get("semantic_gaps") or []),
                *perception_payload["semantic_coverage"].get("semantic_gaps", []),
                *semantic_selection_gaps,
            ]
            if isinstance(item, dict)
        ]
        if entity_budget_gap:
            semantic_gaps.append(entity_budget_gap)
        relationship_summary = perception_payload.get("relationship_summary") if isinstance(perception_payload.get("relationship_summary"), dict) else {}
        if int(relationship_summary.get("candidate_count") or 0) > 0:
            semantic_gaps.append(
                {
                    "gap_type": "relationship_final_validation_missing",
                    "reason_code": "RELATIONSHIP_VALIDATION_REQUIRED",
                    "perception_domain": "relationship_cognition",
                    "severity": "medium",
                    "expected": "validated_relationship",
                    "observed": "relationship_candidate_present",
                    "confidence": 1.0,
                    "repair_hint": "Relationship candidate fields are rendered, but final relationship validation remains required.",
                    "evidence_refs": [],
                    "details": {
                        "relationship_fields_rendered": True,
                        "relationship_truth_not_eligible": True,
                    },
                }
            )
        missing_fields_seen: set[str] = set()
        if not selected_entities:
            semantic_gaps.append(
                {
                    "gap_type": "ENTITY_NOT_OBSERVED",
                    "severity": "high",
                    "expected": "one_or_more_entities_matching_artifact_contract",
                    "observed": 0,
                    "confidence": 1.0,
                    "repair_hint": "Compile observed entities before rendering the governed collection artifact.",
                    "evidence_refs": [],
                }
            )
        for row_index, entity in enumerate(selected_entities, start=1):
            if row_index == 1 or row_index % max(1, self.budget.cancel_poll_interval) == 0:
                batch_elapsed_ms = int(max(0.0, (time.monotonic() - last_batch_monotonic) * 1000))
                max_batch_elapsed_ms = max(max_batch_elapsed_ms, batch_elapsed_ms)
                last_batch_monotonic = time.monotonic()
                self._check_artifact_render_checkpoint(
                    render_run_id,
                    phase_started,
                    artifact_started,
                    stage="after_entity_batch",
                    logical_path=logical_path,
                    rows_rendered=row_index - 1,
                    rows_expected=len(selected_entities),
                    cells_rendered=cells_rendered,
                    extra_metadata={
                        **row_model_metrics,
                        "cardinality_domain": "csv_stream",
                        "csv_rows_expected_at_stream_start": len(selected_entities),
                        "csv_rows_attempted": row_index - 1,
                        "csv_rows_rendered": row_index - 1,
                        "csv_rows_written": rows_written,
                        "csv_rows_failed": rows_failed,
                        "csv_cells_expected": csv_cells_expected,
                        "csv_cells_attempted": max(0, cells_rendered - len(render_columns)),
                        "csv_cells_rendered": max(0, cells_rendered - len(render_columns)),
                        "csv_cells_written": max(0, rows_written * len(render_columns)),
                        "csv_stream_elapsed_ms": int(max(0.0, (time.monotonic() - csv_stream_started) * 1000)),
                        "csv_row_render_elapsed_ms": int(csv_row_render_elapsed_ms),
                        "csv_cell_render_elapsed_ms": int(csv_cell_render_elapsed_ms),
                        "csv_cell_serialization_elapsed_ms": int(csv_cell_serialization_elapsed_ms),
                        "max_batch_elapsed_ms": max_batch_elapsed_ms,
                        "progress_semantics": "progressing",
                    },
                )
            row_started = time.monotonic()
            row: list[Any] = []
            evidence_refs = [str(item) for item in entity.get("evidence_refs") or [] if item]
            for column_index, column in enumerate(render_columns, start=1):
                field = column["canonical_key"]
                cells_rendered += 1
                full_cell_started = time.monotonic()
                if cells_rendered > self.budget.max_artifact_cells:
                    raise GovernedPhase1Block(
                        "ARTIFACT_RENDER_OUTPUT_BUDGET_EXCEEDED",
                        "Artifact render cell budget exceeded.",
                        details={
                            "phase": "artifact_render",
                            "component": "readonly_analysis_artifact_runtime",
                            "frontier": "ARTIFACT_RENDER",
                            "stage": "before_csv_cell_render",
                            "logical_path": logical_path,
                            "cells_rendered": cells_rendered,
                            "max_cells": self.budget.max_artifact_cells,
                        },
                    )
                if cells_rendered % max(1, self.budget.cancel_poll_interval) == 0:
                    self._check_artifact_render_checkpoint(
                        render_run_id,
                        phase_started,
                        artifact_started,
                        stage="before_csv_cell_render",
                        logical_path=logical_path,
                        rows_rendered=row_index - 1,
                        rows_expected=len(selected_entities),
                        cells_rendered=cells_rendered,
                        extra_metadata={
                            **row_model_metrics,
                            "cardinality_domain": "csv_cell_render",
                            "csv_rows_expected_at_stream_start": len(selected_entities),
                            "csv_rows_attempted": row_index,
                            "csv_rows_rendered": row_index - 1,
                            "csv_rows_written": rows_written,
                            "csv_rows_failed": rows_failed,
                            "csv_cells_expected": csv_cells_expected,
                            "csv_cells_attempted": max(0, cells_rendered - len(render_columns)),
                            "csv_cells_rendered": max(0, cells_rendered - len(render_columns)),
                            "csv_cells_written": max(0, rows_written * len(render_columns)),
                            "csv_stream_elapsed_ms": int(max(0.0, (time.monotonic() - csv_stream_started) * 1000)),
                            "csv_row_render_elapsed_ms": int(csv_row_render_elapsed_ms),
                            "csv_cell_render_elapsed_ms": int(csv_cell_render_elapsed_ms),
                            "csv_cell_serialization_elapsed_ms": int(csv_cell_serialization_elapsed_ms),
                            "progress_semantics": "progressing",
                        },
                    )
                relationship_value, relationship_present = self._relationship_render_field_value(
                    field,
                    perception_payload=perception_payload,
                )
                if relationship_present:
                    value = relationship_value
                    present = True
                else:
                    value, present = self._semantic_inventory_field_value(
                        entity,
                        field,
                        perception_payload=perception_payload,
                        semantic_gaps=semantic_gaps,
                    )
                    if not present:
                        value, present = self.observed_entities.value_for_field(entity, field)
                if not present:
                    derived_value = observed_values.get((str(entity.get("entity_id") or ""), field))
                    if derived_value not in (None, ""):
                        value = derived_value
                        present = True
                cell_started = time.monotonic()
                rendered_cell = (
                    ""
                    if value is None
                    else self._render_csv_cell(
                        value,
                        canonical_key=field,
                        task_run_id=str((declared_contract or {}).get("task_run_id") or "unbound"),
                    )
                )
                csv_cell_serialization_elapsed_ms += max(0.0, (time.monotonic() - cell_started) * 1000)
                csv_cell_render_elapsed_ms += max(0.0, (time.monotonic() - full_cell_started) * 1000)
                row.append(rendered_cell)
                if column["required"] and not present and field not in missing_fields_seen:
                    missing_fields_seen.add(field)
                    if not any(str(item.get("gap_type") or "") == f"ATTRIBUTE_NOT_OBSERVED:{field}" for item in semantic_gaps):
                        semantic_gaps.append(
                            {
                                "gap_type": f"ATTRIBUTE_NOT_OBSERVED:{field}",
                                "reason_code": "ATTRIBUTE_VALUE_NOT_OBSERVED",
                                "perception_domain": "attribute_observation",
                                "severity": "high",
                                "expected": field,
                                "observed": "missing",
                                "confidence": 1.0,
                                "repair_hint": "Collect or infer the declared entity attribute with evidence before claiming semantic completeness.",
                                "evidence_refs": evidence_refs,
                                "details": {
                                    "candidate_entity_count": len(perception_result.candidate_entity_set.candidates),
                                    "selected_entity_count": len(selected_entities),
                                },
                            }
                        )
            writer.writerow(row)
            rows_written += 1
            csv_row_render_elapsed_ms += max(0.0, (time.monotonic() - row_started) * 1000)
            if row_index % max(1, self.budget.cancel_poll_interval) == 0:
                self._check_artifact_render_checkpoint(
                    render_run_id,
                    phase_started,
                    artifact_started,
                    stage="csv_row_stream_checkpoint",
                    logical_path=logical_path,
                    rows_rendered=row_index,
                    rows_expected=len(selected_entities),
                    cells_rendered=cells_rendered,
                    extra_metadata={
                        **row_model_metrics,
                        "cardinality_domain": "csv_stream",
                        "csv_rows_expected_at_stream_start": len(selected_entities),
                        "csv_rows_attempted": row_index,
                        "csv_rows_rendered": row_index,
                        "csv_rows_written": rows_written,
                        "csv_rows_failed": rows_failed,
                        "csv_cells_expected": csv_cells_expected,
                        "csv_cells_attempted": max(0, cells_rendered - len(render_columns)),
                        "csv_cells_rendered": max(0, cells_rendered - len(render_columns)),
                        "csv_cells_written": max(0, rows_written * len(render_columns)),
                        "csv_stream_elapsed_ms": int(max(0.0, (time.monotonic() - csv_stream_started) * 1000)),
                        "csv_row_render_elapsed_ms": int(csv_row_render_elapsed_ms),
                        "csv_cell_render_elapsed_ms": int(csv_cell_render_elapsed_ms),
                        "csv_cell_serialization_elapsed_ms": int(csv_cell_serialization_elapsed_ms),
                        "max_batch_elapsed_ms": max_batch_elapsed_ms,
                        "rows_per_second": round(row_index / max(0.001, time.monotonic() - csv_stream_started), 3),
                        "cells_per_second": round(max(0, cells_rendered - len(render_columns)) / max(0.001, time.monotonic() - csv_stream_started), 3),
                        "average_cell_us": round((csv_cell_render_elapsed_ms * 1000) / max(1, cells_rendered - len(render_columns)), 3),
                        "progress_semantics": "progressing",
                    },
                )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_row_binding",
            logical_path=logical_path,
            rows_rendered=len(selected_entities),
            rows_expected=len(selected_entities),
            cells_rendered=cells_rendered,
            extra_metadata={
                **row_model_metrics,
                "cardinality_domain": "row_binding",
                "csv_rows_expected_at_stream_start": len(selected_entities),
                "csv_rows_attempted": len(selected_entities),
                "csv_rows_rendered": len(selected_entities),
                "csv_rows_written": rows_written,
                "csv_rows_failed": rows_failed,
                "csv_cells_expected": csv_cells_expected,
                "csv_cells_attempted": max(0, cells_rendered - len(render_columns)),
                "csv_cells_rendered": max(0, cells_rendered - len(render_columns)),
                "csv_cells_written": max(0, rows_written * len(render_columns)),
                "csv_stream_elapsed_ms": int(max(0.0, (time.monotonic() - csv_stream_started) * 1000)),
                "csv_row_render_elapsed_ms": int(csv_row_render_elapsed_ms),
                "csv_cell_render_elapsed_ms": int(csv_cell_render_elapsed_ms),
                "csv_cell_serialization_elapsed_ms": int(csv_cell_serialization_elapsed_ms),
                "csv_serialization_elapsed_ms": 0,
                "csv_finalize_elapsed_ms": 0,
                "rows_per_second": round(len(selected_entities) / max(0.001, time.monotonic() - csv_stream_started), 3),
                "cells_per_second": round(max(0, cells_rendered - len(render_columns)) / max(0.001, time.monotonic() - csv_stream_started), 3),
                "average_cell_us": round((csv_cell_render_elapsed_ms * 1000) / max(1, cells_rendered - len(render_columns)), 3),
                "progress_semantics": "completed",
            },
        )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="before_csv_row_stream",
            logical_path=logical_path,
            rows_rendered=len(selected_entities),
            rows_expected=len(selected_entities),
            cells_rendered=cells_rendered,
            extra_metadata={
                **row_model_metrics,
                "cardinality_domain": "csv_stream_finalize",
                "csv_rows_expected_at_stream_start": len(selected_entities),
                "csv_rows_attempted": len(selected_entities),
                "csv_rows_rendered": len(selected_entities),
                "csv_rows_written": rows_written,
                "csv_rows_failed": rows_failed,
                "csv_cells_expected": csv_cells_expected,
                "csv_cells_attempted": max(0, cells_rendered - len(render_columns)),
                "csv_cells_rendered": max(0, cells_rendered - len(render_columns)),
                "csv_cells_written": max(0, rows_written * len(render_columns)),
                "csv_stream_elapsed_ms": int(max(0.0, (time.monotonic() - csv_stream_started) * 1000)),
                "csv_row_render_elapsed_ms": int(csv_row_render_elapsed_ms),
                "csv_cell_render_elapsed_ms": int(csv_cell_render_elapsed_ms),
                "csv_cell_serialization_elapsed_ms": int(csv_cell_serialization_elapsed_ms),
                "progress_semantics": "completed",
            },
        )
        finalize_started = time.monotonic()
        csv_content = stream.getvalue()
        csv_finalize_elapsed_ms = int(max(0.0, (time.monotonic() - finalize_started) * 1000))
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_csv_row_stream",
            logical_path=logical_path,
            rows_rendered=len(selected_entities),
            rows_expected=len(selected_entities),
            cells_rendered=cells_rendered,
            extra_metadata={
                **row_model_metrics,
                "cardinality_domain": "csv_stream",
                "csv_rows_expected_at_stream_start": len(selected_entities),
                "csv_rows_attempted": len(selected_entities),
                "csv_rows_rendered": len(selected_entities),
                "csv_rows_written": rows_written,
                "csv_rows_failed": rows_failed,
                "csv_cells_expected": csv_cells_expected,
                "csv_cells_attempted": max(0, cells_rendered - len(render_columns)),
                "csv_cells_rendered": max(0, cells_rendered - len(render_columns)),
                "csv_cells_written": max(0, rows_written * len(render_columns)),
                "csv_stream_elapsed_ms": int(max(0.0, (time.monotonic() - csv_stream_started) * 1000)),
                "csv_row_render_elapsed_ms": int(csv_row_render_elapsed_ms),
                "csv_cell_render_elapsed_ms": int(csv_cell_render_elapsed_ms),
                "csv_cell_serialization_elapsed_ms": int(csv_cell_serialization_elapsed_ms),
                "csv_finalize_elapsed_ms": csv_finalize_elapsed_ms,
                "progress_semantics": "completed",
            },
        )
        if len(csv_content.encode("utf-8")) > self.budget.max_csv_total_bytes:
            raise GovernedPhase1Block(
                "ARTIFACT_RENDER_OUTPUT_BUDGET_EXCEEDED",
                "Artifact render output byte budget exceeded.",
                details={
                    "phase": "artifact_render",
                    "component": "readonly_analysis_artifact_runtime",
                    "frontier": "ARTIFACT_RENDER",
                    "stage": "after_artifact_write_before_registry",
                    "logical_path": logical_path,
                    "observed_bytes": len(csv_content.encode("utf-8")),
                    "max_total_bytes": self.budget.max_csv_total_bytes,
                    "rows_rendered": len(selected_entities),
                    "rows_expected": len(selected_entities),
                },
            )
        canonical_schema = [item["canonical_key"] for item in render_columns]
        row_validation = self.row_level_validation.summarize_csv(
            content=csv_content,
            declared_columns=canonical_schema,
            required_columns=[item["canonical_key"] for item in render_columns if item.get("required")],
            row_bindings=selection_result.rows if semantic_selection_applies else [
                {
                    "entity_id": entity.get("entity_id"),
                    "source_root_role": entity.get("source_root_role"),
                    "evidence_refs": entity.get("evidence_refs") or [],
                    "safe_to_use": bool(entity.get("entity_id") and entity.get("evidence_refs")),
                }
                for entity in selected_entities
            ],
        ).model_dump(mode="json")
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_row_validation",
            logical_path=logical_path,
            rows_rendered=len(selected_entities),
            rows_expected=len(selected_entities),
            cells_rendered=cells_rendered,
        )
        row_evidence_coverage = dict(row_validation.get("row_evidence_coverage") or {})
        column_coverage = dict(row_validation.get("column_coverage") or {})
        evidence_refs_sample = [
            str(item)
            for item in row_evidence_coverage.get("evidence_refs_sample", []) or []
            if item
        ]
        schema_coverage = dict(self.observed_entities.schema_coverage(selected_entities, canonical_schema))
        schema_coverage["canonical_schema"] = canonical_schema
        schema_coverage["display_schema"] = [item["display_label"] for item in render_columns]
        schema_coverage["row_level_validation"] = row_validation
        schema_coverage["column_coverage"] = column_coverage
        schema_coverage["row_evidence_coverage"] = row_evidence_coverage
        semantic_coverage = perception_payload["semantic_coverage"]
        schema_coverage["semantic_coverage"] = {
            "status": semantic_coverage.get("status"),
            "coverage_ratio": semantic_coverage.get("coverage_ratio"),
            "observed_fields": semantic_coverage.get("observed_fields", []),
            "missing_fields": semantic_coverage.get("missing_fields", []),
            "unsupported_fields": semantic_coverage.get("unsupported_fields", []),
            "ambiguous_fields": semantic_coverage.get("ambiguous_fields", []),
            "candidate_entity_count": semantic_coverage.get("candidate_entity_count"),
            "selected_entity_count": semantic_coverage.get("selected_entity_count"),
        }
        schema_coverage["semantic_coverage_report"] = perception_payload.get("semantic_coverage_report", {})
        schema_coverage["semantic_entity_selection"] = selection_result.model_dump(mode="json")
        schema_coverage["artifact_intent_plan"] = intent_plan.model_dump(mode="json")
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="before_metadata_coverage_summary",
            logical_path=logical_path,
            rows_rendered=len(selected_entities),
            rows_expected=len(selected_entities),
            cells_rendered=cells_rendered,
        )
        metadata_coverage = self._metadata_coverage_summary(
            perception_payload=perception_payload,
            selected_entities=selected_entities,
        )
        self._check_artifact_render_checkpoint(
            render_run_id,
            phase_started,
            artifact_started,
            stage="after_metadata_coverage_summary",
            logical_path=logical_path,
            rows_rendered=len(selected_entities),
            rows_expected=len(selected_entities),
            cells_rendered=cells_rendered,
        )
        schema_coverage["metadata_coverage_summary"] = metadata_coverage
        schema_status = "satisfied" if not column_coverage.get("missing_columns") else "blocked"
        inventory_sufficiency = None
        if intent_plan.artifact_kind == "media_corpus_inventory":
            self._check_artifact_render_checkpoint(
                render_run_id,
                phase_started,
                artifact_started,
                stage="before_inventory_sufficiency",
                logical_path=logical_path,
                rows_rendered=selection_result.bound_rows,
                rows_expected=selection_result.expected_rows,
                cells_rendered=cells_rendered,
            )
            inventory_sufficiency = self.media_inventory_sufficiency.evaluate(
                expected_rows=selection_result.expected_rows,
                selected_rows=selection_result.selected_rows,
                bound_rows=selection_result.bound_rows,
                evidence_ref_count=selection_result.evidence_ref_count,
                row_validation=row_validation,
                media_metadata_capability=perception_payload.get("media_metadata_capability", {}),
                metadata_coverage=metadata_coverage,
                schema_status=schema_status,
            )
            schema_coverage["inventory_sufficiency_summary"] = inventory_sufficiency.model_dump(mode="json")
            for reason in inventory_sufficiency.reason_codes:
                semantic_gaps.append(
                    {
                        "gap_type": reason,
                        "reason_code": reason,
                        "perception_domain": "media_inventory_sufficiency",
                        "severity": "high",
                        "expected": "complete_media_inventory_sufficiency",
                        "observed": inventory_sufficiency.coverage_summary,
                        "confidence": 1.0,
                        "repair_hint": "Complete governed media metadata observation and inventory coverage before claiming Phase 1 sufficiency.",
                        "evidence_refs": evidence_refs_sample,
                        "details": {
                            "use_safety": inventory_sufficiency.use_safety,
                            "limitations": inventory_sufficiency.limitations,
                        },
                    }
                )
            self._check_artifact_render_checkpoint(
                render_run_id,
                phase_started,
                artifact_started,
                stage="after_inventory_sufficiency",
                logical_path=logical_path,
                rows_rendered=selection_result.bound_rows,
                rows_expected=selection_result.expected_rows,
                cells_rendered=cells_rendered,
            )
        candidates = perception_payload["candidate_entity_set"].get("candidates") or []
        rejected_candidates = [
            item for item in candidates if isinstance(item, dict) and item.get("status") == "rejected"
        ]
        entity_summary = {
            "entity_set_id": graph_payload.get("entity_set_id"),
            "entity_count": len(selected_entities),
            "observed_entities_count": len(all_entities),
            "roots_scanned_by_role": graph_payload.get("roots_scanned_by_role", {}),
            "entities_by_root_role": graph_payload.get("entities_by_root_role", {}),
            "root_bindings": [
                {
                    "root_id": item.get("root_id"),
                    "role": item.get("role"),
                    "source": item.get("source"),
                    "purposes": item.get("purposes") or [],
                    "policy_status": ((item.get("policy_decision") or {}).get("policy_status") if isinstance(item.get("policy_decision"), dict) else item.get("policy_status")),
                    "observation_allowed": bool(item.get("observation_allowed")),
                    "mutation_allowed": bool(item.get("mutation_allowed")),
                    "access_scope": ((item.get("policy_decision") or {}).get("access_scope") if isinstance(item.get("policy_decision"), dict) else item.get("access_scope")) or [],
                    "reason_codes": ((item.get("policy_decision") or {}).get("reason_codes") if isinstance(item.get("policy_decision"), dict) else item.get("policy_reason_codes")) or [],
                    "evidence_ref_count": len([ref for ref in item.get("evidence_refs") or [] if ref]),
                }
                for item in (graph_payload.get("root_bindings") or [])[:20]
                if isinstance(item, dict)
            ],
            "root_policy_decisions": [
                {
                    "root_id": item.get("root_id"),
                    "role": item.get("role"),
                    "policy_status": ((item.get("policy_decision") or {}).get("policy_status") if isinstance(item.get("policy_decision"), dict) else item.get("policy_status")),
                    "observation_allowed": bool(item.get("observation_allowed")),
                    "reason_codes": ((item.get("policy_decision") or {}).get("reason_codes") if isinstance(item.get("policy_decision"), dict) else item.get("policy_reason_codes")) or [],
                }
                for item in (graph_payload.get("root_bindings") or [])[:20]
                if isinstance(item, dict)
            ],
            "corpus_roots_policy_allowed_count": sum(
                1
                for item in graph_payload.get("root_bindings") or []
                if isinstance(item, dict)
                and item.get("role") in {"library_root", "corpus_root"}
                and bool(item.get("observation_allowed"))
            ),
            "entities_selected_by_artifact": {
                logical_path: len(selected_entities),
            }
            if logical_path
            else {},
            "entities_rejected_by_policy": [
                {
                    "entity_id": item.get("entity_id"),
                    "source_root_role": item.get("source_root_role"),
                    "entity_role": item.get("entity_role"),
                    "policy_rejection_reasons": item.get("policy_rejection_reasons") or [],
                }
                for item in rejected_candidates[:100]
            ],
            "workspace_role_mismatches": [
                item
                for item in rejected_candidates[:100]
                if "ROOT_ROLE_NOT_ALLOWED" in (item.get("policy_rejection_reasons") or [])
            ],
            "selection_counts": {
                "candidate_count": len(candidates),
                "selected_count": len(selected_entities),
                "rejected_count": len(rejected_candidates),
                "expected_rows": selection_result.expected_rows if semantic_selection_applies else len(all_entities),
                "selected_rows": selection_result.selected_rows if semantic_selection_applies else len(selected_entities),
                "bound_rows": selection_result.bound_rows if semantic_selection_applies else len(selected_entities),
                "evidence_ref_count": selection_result.evidence_ref_count if semantic_selection_applies else len(
                    list(dict.fromkeys(ref for entity in selected_entities for ref in (entity.get("evidence_refs") or [])))
                ),
            },
            "semantic_entity_selection": selection_result.model_dump(mode="json"),
            "artifact_intent_plan": intent_plan.model_dump(mode="json"),
            "evidence_binding": {
                "expected_rows": selection_result.expected_rows,
                "selected_rows": selection_result.selected_rows,
                "bound_rows": selection_result.bound_rows,
                "evidence_ref_count": selection_result.evidence_ref_count,
                "evidence_refs_sample": evidence_refs_sample,
                "row_evidence_coverage": row_evidence_coverage,
                "status": selection_result.status,
                "reason_code": selection_result.reason_code,
                "limitations": selection_result.limitations,
            },
            "metadata_coverage_summary": metadata_coverage,
            "inventory_sufficiency_summary": inventory_sufficiency.model_dump(mode="json") if inventory_sufficiency else {},
            "selected_entity_kinds": sorted({str(item.get("entity_kind") or "") for item in selected_entities}),
            "entities": [
                {
                    "entity_id": entity.get("entity_id"),
                    "entity_kind": entity.get("entity_kind"),
                    "source": entity.get("source"),
                    "source_root_role": entity.get("source_root_role"),
                    "entity_role": entity.get("entity_role"),
                    "selection_eligibility": entity.get("selection_eligibility") or {},
                    "exclusion_reasons": entity.get("exclusion_reasons") or [],
                    "confidence": entity.get("confidence"),
                    "evidence_refs": entity.get("evidence_refs") or [],
                }
                for entity in selected_entities[:50]
            ],
            "perception": {
                "contract_observation_plan": perception_payload["contract_observation_plan"],
                "candidate_entity_set": perception_payload["candidate_entity_set"],
                "specialization_hypotheses": perception_payload["specialization_hypotheses"][:50],
                "observation_plan": perception_payload["observation_plan"],
                "observation_execution_results": perception_payload.get("observation_execution_results", [])[:100],
                "media_metadata_capability": perception_payload.get("media_metadata_capability", {}),
                "metadata_coverage_summary": metadata_coverage,
                "relationship_goal": perception_payload.get("relationship_goal"),
                "relationship_summary": perception_payload.get("relationship_summary", {}),
                "relationship_candidates": perception_payload.get("relationship_candidates", [])[:100],
                "relationship_evidence": perception_payload.get("relationship_evidence", [])[:200],
                "relationship_observations": perception_payload.get("relationship_observations", [])[:100],
                "relationship_provenance_traces": perception_payload.get("relationship_provenance_traces", [])[:100],
                "relationship_rendering": self._relationship_rendering_summary(perception_payload),
                "attribute_observations": perception_payload["attribute_observations"][:100],
                "evidence_set": perception_payload.get("evidence_set", {}),
                "semantic_coverage_report": perception_payload.get("semantic_coverage_report", {}),
                "compile_stage_trace": [
                    self._bounded_checkpoint_metadata(item)
                    for item in perception_payload.get("compile_stage_trace", [])
                    if isinstance(item, dict)
                ][:40],
                "payload_metrics": self._bounded_perception_payload_metrics(perception_payload.get("payload_metrics")),
                "compile_policy": perception_payload.get("compile_policy", {}),
                "internal_reason_code": perception_payload.get("internal_reason_code"),
            },
            "semantic_coverage": semantic_coverage,
        }
        sufficiency_blocked = inventory_sufficiency is not None and inventory_sufficiency.status != "satisfied"
        artifact_status = (
            "partial"
            if entity_budget_gap
            or (semantic_selection_applies and selection_result.bound_rows > 0 and selection_result.bound_rows < max(1, selection_result.expected_rows))
            or sufficiency_blocked
            else "completed"
        )
        artifact_reason = (
            (entity_budget_gap or {}).get("reason_code")
            if entity_budget_gap
            else inventory_sufficiency.reason_code
            if sufficiency_blocked and inventory_sufficiency is not None
            else "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
            if semantic_selection_applies and selection_result.bound_rows > 0 and selection_result.bound_rows < max(1, selection_result.expected_rows)
            else None
        )
        return self._render_result(
            csv_content,
            semantic_gaps=semantic_gaps,
            schema_coverage=schema_coverage,
            entity_summary=entity_summary,
            status=artifact_status,
            reason_code=artifact_reason,
            partial_rows=selection_result.bound_rows if semantic_selection_applies else len(selected_entities) if entity_budget_gap else None,
            expected_rows=selection_result.expected_rows if semantic_selection_applies else len(all_entities) if entity_budget_gap else len(selected_entities),
            selected_rows=selection_result.selected_rows if semantic_selection_applies else len(selected_entities),
            bound_rows=selection_result.bound_rows if semantic_selection_applies else len(selected_entities),
            evidence_ref_count=selection_result.evidence_ref_count
            if semantic_selection_applies
            else len(list(dict.fromkeys(ref for entity in selected_entities for ref in (entity.get("evidence_refs") or [])))),
            rendered_columns=canonical_schema,
            missing_columns=list(column_coverage.get("missing_columns") or []),
            row_validation_summary=row_validation,
            evidence_refs_sample=evidence_refs_sample,
            row_evidence_coverage=row_evidence_coverage,
            safe_to_use=(
                entity_budget_gap is None
                and (not semantic_selection_applies or selection_result.bound_rows >= max(1, selection_result.expected_rows))
                and (inventory_sufficiency.safe_to_use if inventory_sufficiency is not None else True)
            ),
        )

    def _semantic_inventory_field_value(
        self,
        entity: dict[str, Any],
        field: str,
        *,
        perception_payload: dict[str, Any],
        semantic_gaps: list[dict[str, Any]],
    ) -> tuple[Any | None, bool]:
        canonical = self.observed_entities.canonical_attribute_name(field)
        canonical_key = str(canonical or "").replace(" ", "_")
        if canonical_key == "entity_id":
            return entity.get("entity_id"), bool(entity.get("entity_id"))
        if canonical_key == "evidence_ref":
            refs = [str(item) for item in entity.get("evidence_refs") or [] if item]
            max_refs = int(getattr(self.budget, "max_evidence_refs_inline", 20) or 20)
            return ";".join(refs[:max_refs]), bool(refs)
        if canonical_key == "metadata_status":
            return self._metadata_status_for_entity(entity, perception_payload=perception_payload), True
        if canonical_key == "metadata_source":
            return self._metadata_source_for_entity(entity, perception_payload=perception_payload), True
        if canonical_key == "probe_status":
            return self._metadata_probe_status_for_entity(entity, perception_payload=perception_payload), True
        if canonical_key == "validation_status":
            return "semantic_validation_required", True
        if canonical_key == "limitations":
            limitation_codes = [
                str(item.get("reason_code") or item.get("gap_type") or "")
                for item in semantic_gaps
                if isinstance(item, dict) and (item.get("reason_code") or item.get("gap_type"))
            ]
            media = perception_payload.get("media_metadata_capability")
            media_status = str((media or {}).get("status") or "") if isinstance(media, dict) else ""
            if media_status in {"not_configured", "missing_dependency", "blocked", "unsupported"}:
                limitation_codes.append(f"media_metadata_capability_{media_status}")
            elif not media_status:
                limitation_codes.append("media_metadata_capability_not_configured")
            if not limitation_codes:
                limitation_codes = ["none_observed"]
            return ";".join(list(dict.fromkeys(limitation_codes))[:20]), True
        if canonical_key == "relationship_candidate_refs":
            observations = perception_payload.get("relationship_observations")
            if not isinstance(observations, list):
                return "", False
            entity_id = str(entity.get("entity_id") or "")
            refs = [
                str(item.get("candidate_id") or item.get("observation_id") or "")
                for item in observations
                if isinstance(item, dict)
                and entity_id
                and entity_id in {
                    str(item.get("source_entity_id") or ""),
                    str(item.get("target_entity_id") or ""),
                }
                and (item.get("candidate_id") or item.get("observation_id"))
            ]
            max_refs = int(getattr(self.budget, "max_evidence_refs_inline", 20) or 20)
            return ";".join(refs[:max_refs]), bool(refs)
        if canonical_key == "media_type":
            hypotheses = entity.get("entity_domain_hypotheses")
            if isinstance(hypotheses, list):
                domains = [
                    str(item.get("domain") or "")
                    for item in hypotheses
                    if isinstance(item, dict) and item.get("domain")
                ]
                if domains:
                    return domains[0], True
            return "not_observed", True
        return None, False

    def _metadata_status_for_entity(self, entity: dict[str, Any], *, perception_payload: dict[str, Any]) -> str:
        entity_id = str(entity.get("entity_id") or "")
        observations = self._media_metadata_observations_for_entity(entity_id, perception_payload=perception_payload)
        if any(item.get("observation_state") == "observed" for item in observations):
            observed_keys = {
                str(item.get("canonical_key") or item.get("attribute_name") or "")
                for item in observations
                if item.get("observation_state") == "observed"
            }
            return "observed" if {"codec", "container", "duration", "bitrate", "sample_rate", "channels"}.issubset(observed_keys) else "partially_observed"
        if observations:
            return "not_observed"
        media = perception_payload.get("media_metadata_capability")
        status = str((media or {}).get("status") or "") if isinstance(media, dict) else ""
        if status in {"not_configured", "missing_dependency", "blocked", "unavailable", "failed"}:
            return "not_configured" if status in {"not_configured", "missing_dependency", "unavailable"} else status
        return "not_observed"

    def _metadata_source_for_entity(self, entity: dict[str, Any], *, perception_payload: dict[str, Any]) -> str:
        entity_id = str(entity.get("entity_id") or "")
        observations = self._media_metadata_observations_for_entity(entity_id, perception_payload=perception_payload)
        backends = sorted({
            str(((item.get("provenance") or {}).get("backend_id") or (item.get("evidence") or {}).get("backend_id") or ""))
            for item in observations
            if isinstance(item, dict)
        })
        backends = [item for item in backends if item]
        if backends:
            return ";".join(backends[:5])
        media = perception_payload.get("media_metadata_capability")
        selected = str((media or {}).get("selected_backend") or "") if isinstance(media, dict) else ""
        return selected or "not_configured"

    def _metadata_probe_status_for_entity(self, entity: dict[str, Any], *, perception_payload: dict[str, Any]) -> str:
        entity_id = str(entity.get("entity_id") or "")
        observations = self._media_metadata_observations_for_entity(entity_id, perception_payload=perception_payload)
        if any(item.get("observation_state") == "observed" for item in observations):
            return "executed"
        if observations:
            return "executed_no_evidence"
        media = perception_payload.get("media_metadata_capability")
        status = str((media or {}).get("status") or "") if isinstance(media, dict) else ""
        return "not_configured" if status in {"", "not_configured", "missing_dependency", "unavailable"} else "not_observed"

    def _media_metadata_observations_for_entity(self, entity_id: str, *, perception_payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not entity_id:
            return []
        rows = perception_payload.get("attribute_observations") if isinstance(perception_payload.get("attribute_observations"), list) else []
        return [
            item
            for item in rows
            if isinstance(item, dict)
            and str(item.get("entity_id") or "") == entity_id
            and str(item.get("capability_id") or "") == "media_metadata_reader"
        ]

    def _metadata_coverage_summary(self, *, perception_payload: dict[str, Any], selected_entities: list[dict[str, Any]]) -> dict[str, Any]:
        selected_ids = [str(item.get("entity_id") or "") for item in selected_entities if item.get("entity_id")]
        selected_id_set = set(selected_ids)
        observations = [
            item
            for item in (perception_payload.get("attribute_observations") if isinstance(perception_payload.get("attribute_observations"), list) else [])
            if isinstance(item, dict)
            and str(item.get("entity_id") or "") in selected_id_set
            and str(item.get("capability_id") or "") == "media_metadata_reader"
        ]
        attempted_ids = {
            str(item.get("entity_id") or "")
            for item in observations
            if item.get("entity_id")
        }
        observed_ids = {
            str(item.get("entity_id") or "")
            for item in observations
            if item.get("entity_id") and item.get("observation_state") == "observed"
        }
        media = perception_payload.get("media_metadata_capability") if isinstance(perception_payload.get("media_metadata_capability"), dict) else {}
        errors = media.get("backend_error_counts") if isinstance(media.get("backend_error_counts"), dict) else {}
        raw_unsupported_count = sum(
            int(count or 0)
            for code, count in errors.items()
            if "UNSUPPORTED" in str(code)
        )
        raw_read_error_count = sum(
            int(count or 0)
            for code, count in errors.items()
            if any(token in str(code) for token in ("RUNTIME_ERROR", "READ_ERROR", "TIMEOUT", "INVALID_JSON"))
        )
        files_attempted = len(attempted_ids)
        files_succeeded = len(observed_ids)
        files_failed = max(0, files_attempted - files_succeeded)
        unsupported_count = min(files_failed, raw_unsupported_count)
        read_error_count = min(files_failed, raw_read_error_count)
        selected_count = len(selected_ids)
        coverage_ratio = files_succeeded / max(1, selected_count)
        status = (
            "satisfied"
            if selected_count > 0 and files_succeeded == selected_count
            else "partial"
            if files_attempted > 0
            else "not_configured"
        )
        return {
            "status": status,
            "capability_id": "media_metadata_reader",
            "files_expected": selected_count,
            "files_attempted": files_attempted,
            "files_succeeded": files_succeeded,
            "files_failed": files_failed,
            "unsupported_count": unsupported_count,
            "read_error_count": read_error_count,
            "coverage_ratio": round(coverage_ratio, 4),
            "attributes_observed": list(media.get("attributes_observed") or []),
            "attributes_missing": list(media.get("attributes_missing") or []),
            "backend_error_counts": dict(errors),
            "reason_codes": self._metadata_coverage_reason_codes(
                status=status,
                selected_count=selected_count,
                files_attempted=files_attempted,
                files_succeeded=files_succeeded,
                capability_status=str(media.get("status") or "not_configured"),
            ),
        }

    def _metadata_coverage_reason_codes(
        self,
        *,
        status: str,
        selected_count: int,
        files_attempted: int,
        files_succeeded: int,
        capability_status: str,
    ) -> list[str]:
        reasons: list[str] = []
        if selected_count > 0 and files_attempted <= 0:
            reasons.append("MEDIA_METADATA_PROBE_NOT_RUN")
        if capability_status in {"not_configured", "missing_dependency", "unavailable"}:
            reasons.append("MEDIA_METADATA_CAPABILITY_NOT_CONFIGURED")
        if selected_count > 0 and files_succeeded < selected_count:
            reasons.append("MEDIA_METADATA_OBSERVATION_INCOMPLETE")
        if status == "satisfied":
            reasons.append("MEDIA_INVENTORY_COMPLETE_SUFFICIENCY_SATISFIED")
        return list(dict.fromkeys(reasons))

    def _relationship_render_field_value(self, field: str, *, perception_payload: dict[str, Any]) -> tuple[Any, bool]:
        if not str(field or "").startswith("relationship_"):
            return None, False
        summary = perception_payload.get("relationship_summary") if isinstance(perception_payload.get("relationship_summary"), dict) else {}
        observations = perception_payload.get("relationship_observations") if isinstance(perception_payload.get("relationship_observations"), list) else []
        candidates = perception_payload.get("relationship_candidates") if isinstance(perception_payload.get("relationship_candidates"), list) else []
        traces = perception_payload.get("relationship_provenance_traces") if isinstance(perception_payload.get("relationship_provenance_traces"), list) else []
        families = list(summary.get("relation_families") or [])
        top_family = families[0] if families else None
        confidence = summary.get("confidence_summary") if isinstance(summary.get("confidence_summary"), dict) else {}
        validation = summary.get("validation_summary") if isinstance(summary.get("validation_summary"), dict) else {}
        confidence_band = next(
            (
                (candidate.get("confidence_model") or {}).get("confidence_band")
                for candidate in candidates
                if isinstance(candidate, dict) and isinstance(candidate.get("confidence_model"), dict)
            ),
            None,
        )
        evidence_ref_count = len({
            str(ref)
            for observation in observations
            if isinstance(observation, dict)
            for ref in observation.get("evidence_refs", []) or []
            if ref
        })
        provenance_ref_count = len({
            str(candidate.get("provenance_trace_id"))
            for candidate in candidates
            if isinstance(candidate, dict) and candidate.get("provenance_trace_id")
        } | {
            str(trace.get("trace_id"))
            for trace in traces
            if isinstance(trace, dict) and trace.get("trace_id")
        })
        conflict_count = int(summary.get("conflict_count") or 0)
        validation_ready_count = int(validation.get("validation_ready_count") or summary.get("validation_ready_count") or 0)
        conflicted_count = int(validation.get("conflicted_relationship_count") or summary.get("conflicted_relationship_count") or 0)
        validation_status = (
            "validation_ready"
            if validation_ready_count > 0
            else "conflicted"
            if conflicted_count > 0 or conflict_count > 0
            else "validation_required"
            if candidates or observations
            else "blocked"
        )
        limitation_count = sum(len(candidate.get("limitations") or []) for candidate in candidates if isinstance(candidate, dict))
        values = {
            "relationship_candidate_summary": {
                "candidate_count": int(summary.get("candidate_count") or len(candidates)),
                "top_family": top_family,
                "confidence_band": confidence_band,
                "confidence_max": confidence.get("max"),
                "validation_status": validation_status,
                "truth_eligible": False,
            },
            "relationship_candidate_count": int(summary.get("candidate_count") or len(candidates)),
            "relationship_candidate_families": families,
            "relationship_top_family": top_family,
            "relationship_confidence_band": confidence_band,
            "relationship_validation_status": validation_status,
            "relationship_validation_reason_codes": list(validation.get("reason_codes") or summary.get("reason_codes") or []),
            "relationship_validation_ready_count": validation_ready_count,
            "relationship_conflicted_count": conflicted_count,
            "relationship_evidence_ref_count": evidence_ref_count,
            "relationship_provenance_ref_count": provenance_ref_count,
            "relationship_conflict_count": conflict_count,
            "relationship_limitations_summary": {
                "limitation_count": limitation_count,
                "candidate_only": True,
                "truth_eligible": False,
            },
        }
        if field not in values:
            return None, False
        return values[field], True

    def _relationship_rendering_summary(self, perception_payload: dict[str, Any]) -> dict[str, Any]:
        fields = [
            "relationship_candidate_summary",
            "relationship_candidate_count",
            "relationship_top_family",
            "relationship_confidence_band",
            "relationship_validation_status",
            "relationship_validation_reason_codes",
            "relationship_validation_ready_count",
            "relationship_conflicted_count",
            "relationship_evidence_ref_count",
            "relationship_provenance_ref_count",
            "relationship_conflict_count",
            "relationship_limitations_summary",
        ]
        rendered = [
            field
            for field in fields
            if self._relationship_render_field_value(field, perception_payload=perception_payload)[1]
        ]
        summary = perception_payload.get("relationship_summary") if isinstance(perception_payload.get("relationship_summary"), dict) else {}
        candidate_count = int(summary.get("candidate_count") or 0)
        validation_summary = summary.get("validation_summary") if isinstance(summary.get("validation_summary"), dict) else {}
        validation_status = (
            "validation_ready"
            if int(validation_summary.get("validation_ready_count") or summary.get("validation_ready_count") or 0) > 0
            else "conflicted"
            if int(validation_summary.get("conflicted_relationship_count") or summary.get("conflicted_relationship_count") or 0) > 0
            else "validation_required"
            if candidate_count > 0
            else "blocked"
        )
        return {
            "status": "available" if candidate_count > 0 else "not_available",
            "rendered_field_count": len(rendered),
            "rendered_fields": rendered,
            "candidate_count": candidate_count,
            "truth_eligible": False,
            "validation_status": validation_status,
            "validation_ready_count": int(validation_summary.get("validation_ready_count") or summary.get("validation_ready_count") or 0),
            "conflicted_relationship_count": int(validation_summary.get("conflicted_relationship_count") or summary.get("conflicted_relationship_count") or 0),
            "source": "perception_relationship_binding",
        }

    def _render_csv_cell(self, value: Any, *, canonical_key: str, task_run_id: str) -> Any:
        if isinstance(value, (dict, list)):
            encoded = json.dumps(value, ensure_ascii=False, default=str)
        else:
            encoded = str(value)
        size = len(encoded.encode("utf-8"))
        if size <= self.budget.max_csv_cell_bytes:
            return encoded if isinstance(value, (dict, list)) else value
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        ref_dir = PATHS.project_root / "data" / "runtime" / "render_payload_refs" / self._safe_ref_segment(task_run_id)
        ref_dir.mkdir(parents=True, exist_ok=True)
        ref_path = ref_dir / f"{digest}.json"
        if not ref_path.exists():
            ref_path.write_text(encoded, encoding="utf-8")
        try:
            content_ref = str(ref_path.relative_to(PATHS.project_root))
        except Exception:
            content_ref = str(ref_path)
        summary = {
            "content_ref": content_ref,
            "hash": digest,
            "size_bytes": size,
            "canonical_key": canonical_key,
            "reason_code": "CSV_FIELD_SPILLED_TO_REF",
            "preview": encoded[:200],
        }
        return json.dumps(summary, ensure_ascii=False, separators=(",", ":"))

    def _safe_ref_segment(self, value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "unbound"))[:120] or "unbound"

    def _evidence_archive_content(self, payload: dict[str, Any]) -> str:
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            diagnostics = self._evidence_archive_diagnostics(payload)
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "artifact_kind": "evidence_archive",
                        "logical_path": payload.get("logical_path"),
                        "task_run_id": payload.get("task_run_id"),
                        "phase_id": payload.get("phase_id"),
                        "workspace_mutation": False,
                        "entries": [
                            "analysis.json",
                            "dependencies.json",
                            "semantic_artifact_contract.json",
                            "observation_goals.json",
                            "entity_selection_report.json",
                            "capability_status.json",
                            "artifact_binding_report.json",
                            "limitations.json",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            archive.writestr(
                "analysis.json",
                json.dumps(payload.get("analysis") or {}, ensure_ascii=False, indent=2, default=str),
            )
            archive.writestr(
                "dependencies.json",
                json.dumps(payload.get("dependencies") or {}, ensure_ascii=False, indent=2, default=str),
            )
            for name, value in diagnostics.items():
                archive.writestr(name, json.dumps(value, ensure_ascii=False, indent=2, default=str))
        return base64.b64encode(memory.getvalue()).decode("ascii")

    def _evidence_archive_diagnostics(self, payload: dict[str, Any]) -> dict[str, Any]:
        analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
        graph = analysis.get("observed_entity_graph") if isinstance(analysis.get("observed_entity_graph"), dict) else {}
        semantic_gaps = [item for item in graph.get("semantic_gaps") or [] if isinstance(item, dict)]
        capability_status = {
            "media_metadata_capability": {
                "status": "not_configured",
                "reason_code": "MEDIA_METADATA_CAPABILITY_NOT_CONFIGURED",
                "truth_eligible": False,
            },
            "relationship_cognition": {
                "status": "not_available",
                "reason_code": "RELATIONSHIP_OBSERVATION_NOT_BOUND",
                "truth_eligible": False,
                "speaker_claim_allowed": False,
            },
        }
        return {
            "semantic_artifact_contract.json": {
                "source": "readonly_analysis_artifact_runtime",
                "phase_id": payload.get("phase_id"),
                "artifact_kind": "evidence_archive",
                "workspace_mutation": False,
                "truth_eligible": False,
            },
            "observation_goals.json": {
                "source": "artifact_contract_diagnostics",
                "status": "diagnostic_only",
                "goals": [],
                "reason_code": "OBSERVATION_GOALS_NOT_BOUND_TO_EVIDENCE_ARCHIVE",
            },
            "entity_selection_report.json": {
                "source": "observed_entity_graph",
                "roots_scanned_by_role": graph.get("roots_scanned_by_role") or {},
                "entities_by_root_role": graph.get("entities_by_root_role") or {},
                "entity_count": len([item for item in graph.get("entities") or [] if isinstance(item, dict)]),
                "semantic_gaps": semantic_gaps[:200],
            },
            "capability_status.json": capability_status,
            "artifact_binding_report.json": {
                "source": "artifact_runtime_evidence_archive",
                "status": "diagnostic_only",
                "reason_code": "ARTIFACT_BINDING_REPORT_DIAGNOSTIC_ONLY",
                "truth_eligible": False,
            },
            "limitations.json": {
                "limitations": list(
                    dict.fromkeys(
                        [
                            *(str(item.get("reason_code") or item.get("gap_type") or "") for item in semantic_gaps if item),
                            "evidence_archive_is_diagnostic_when_phase_artifacts_block",
                        ]
                    )
                ),
            },
        }

    def _patch_planning_content(
        self,
        *,
        logical_path: str,
        run_id: str,
        workspace: str,
        workspace_context: dict[str, Any],
        phase_id: str,
        analysis_payload: dict[str, Any],
        dependency_check: dict[str, Any],
    ) -> str:
        supported = self._supported_patch_evidence(analysis_payload, dependency_check)
        headers = self._artifact_header(logical_path, run_id, workspace, workspace_context, phase_id)
        if not supported["has_root_cause"]:
            return (
                headers
                + "## Root Cause\n\n"
                "Root cause not identified with sufficient evidence from the governed analysis artifacts.\n\n"
                "## Target Files\n\n"
                + self._bullet_list(supported["target_files"] or ["not established"])
                + "\n\n## Target Functions\n\n"
                + self._bullet_list(supported["target_functions"] or ["not established"])
                + "\n\n## Strategy\n\n"
                "Strategy not available until a supported root cause exists.\n\n"
                "## Rollback\n\n"
                "Rollback not available until concrete target files and changes are identified.\n\n"
                "## Alternatives\n\n"
                "Alternatives not available until a supported root cause exists.\n\n"
                "## Validation\n\n"
                "Validation must remain blocked because required planning evidence is incomplete.\n\n"
                "## Risk\n\n"
                "Risk is high while the root cause and concrete changes are not established.\n"
            )
        return (
            headers
            + "## Patch Plan\n\n"
            + f"- patch_plan_id: {supported['patch_plan_id'] or 'not available'}\n"
            + f"- patch_plan_status: {supported['patch_plan_status'] or 'not available'}\n"
            + f"- diff_ref: {supported['diff_ref'] or 'not available'}\n"
            + "\n"
            + "## Root Cause\n\n"
            + supported["root_cause"]
            + "\n\n## Target Files\n\n"
            + self._bullet_list(supported["target_files"])
            + "\n\n## Target Functions\n\n"
            + self._bullet_list(supported["target_functions"])
            + "\n\n## Strategy\n\n"
            + supported["strategy"]
            + "\n\n## Rollback\n\n"
            + supported["rollback"]
            + "\n\n## Alternatives\n\n"
            + supported["alternatives"]
            + "\n\n## Validation\n\n"
            + supported["validation"]
            + "\n\n## Risk\n\n"
            + supported["risk"]
            + "\n\n## Evidence\n\n"
            + self._bullet_list(supported["evidence"])
            + "\n"
        )

    def _patch_preview_content(
        self,
        *,
        logical_path: str,
        run_id: str,
        workspace: str,
        workspace_context: dict[str, Any],
        phase_id: str,
        analysis_payload: dict[str, Any],
        dependency_check: dict[str, Any],
    ) -> str:
        supported = self._supported_patch_evidence(analysis_payload, dependency_check)
        headers = self._artifact_header(logical_path, run_id, workspace, workspace_context, phase_id)
        repair_proposal = supported.get("repair_proposal") if isinstance(supported.get("repair_proposal"), dict) else {}
        if not supported["patch_preview_supported"]:
            return (
                headers
                + "## Target Files\n\n"
                + self._bullet_list(supported["target_files"] or ["not established"])
                + "\n\n## Concrete Change Preview\n\n"
                "Repair proposal not available because the canonical patch pipeline has not produced a governed proposal or compiler preview.\n\n"
                "## Validation\n\n"
                "Validation must remain blocked until a governed Repair Proposal exists.\n\n"
                "## Rollback\n\n"
                "Rollback not available until concrete changes are identified.\n"
            )
        if repair_proposal:
            repair_proposal = self._normalized_repair_proposal_payload(repair_proposal)
            target = repair_proposal.get("target") if isinstance(repair_proposal.get("target"), dict) else {}
            concrete = repair_proposal.get("concrete_change") if isinstance(repair_proposal.get("concrete_change"), dict) else {}
            rollback = repair_proposal.get("rollback") if isinstance(repair_proposal.get("rollback"), dict) else {}
            impact = repair_proposal.get("impact") if isinstance(repair_proposal.get("impact"), dict) else {}
            risks = repair_proposal.get("risks") if isinstance(repair_proposal.get("risks"), dict) else {}
            components = repair_proposal.get("components") if isinstance(repair_proposal.get("components"), dict) else {}
            assembly = repair_proposal.get("assembly") if isinstance(repair_proposal.get("assembly"), dict) else {}
            field_origins = repair_proposal.get("field_origins") if isinstance(repair_proposal.get("field_origins"), dict) else {}
            replacement = str(concrete.get("suggested_replacement") or "").rstrip()
            compiler_preview = ""
            if supported["patch_plan_concrete"] and supported["diff_text"]:
                compiler_preview = (
                    "\n\n## Compiler Preview\n\n"
                    + "```diff\n"
                    + supported["diff_text"].rstrip()
                    + "\n```\n"
                )
            elif replacement:
                compiler_preview = (
                    "\n\n## Suggested Replacement\n\n"
                    + "```text\n"
                    + replacement
                    + "\n```\n"
                )
            return (
                headers
                + "## Repair Proposal\n\n"
                + f"- proposal_id: {repair_proposal.get('proposal_id') or 'not available'}\n"
                + f"- proposal_status: {repair_proposal.get('proposal_status') or 'not available'}\n"
                + f"- proposal_completeness: {repair_proposal.get('proposal_completeness') if repair_proposal.get('proposal_completeness') is not None else 'not available'}\n"
                + f"- intent: {repair_proposal.get('intent') or 'not available'}\n"
                + f"- target_file: {target.get('file') or 'not available'}\n"
                + f"- target_symbol: {target.get('symbol') or 'not available'}\n"
                + f"- symbol_kind: {target.get('symbol_kind') or 'not available'}\n"
                + "\n## Proposal Components\n\n"
                + self._proposal_component_section(components)
                + "\n## Target Files\n\n"
                + self._bullet_list(supported["target_files"] or [str(target.get("file") or "not established")])
                + "\n\n## Concrete Change Preview\n\n"
                + f"- objective: {concrete.get('objective') or 'not available'}\n"
                + f"- current_behavior: {concrete.get('current_behavior') or 'not available'}\n"
                + f"- expected_behavior: {concrete.get('expected_behavior') or 'not available'}\n"
                + f"- behavior_summary: {concrete.get('behavior_summary') or 'not available'}\n"
                + f"- modification_strategy: {concrete.get('modification_strategy') or 'not available'}\n"
                + "\n### Affected Symbols\n\n"
                + self._bullet_list(list(concrete.get("affected_symbols") or []) or [str(target.get("symbol") or "not established")])
                + "\n\n### Constraints\n\n"
                + self._bullet_list(list(concrete.get("constraints") or []) or ["not available"])
                + "\n\n### Invariants\n\n"
                + self._bullet_list(list(concrete.get("invariants") or []) or ["not available"])
                + "\n\n### Success Criteria\n\n"
                + self._bullet_list(list(concrete.get("success_criteria") or []) or ["not available"])
                + "\n\n### Reasoning\n\n"
                + str(concrete.get("reasoning") or "not available")
                + compiler_preview
                + "\n\n## Proposal Assembly\n\n"
                + f"- assembly_status: {assembly.get('assembly_status') or 'not available'}\n"
                + f"- assembly_score: {assembly.get('assembly_score') if assembly.get('assembly_score') is not None else 'not available'}\n"
                + "\n### Assembly Stages\n\n"
                + self._proposal_assembly_section(assembly)
                + "\n\n## Field Origins\n\n"
                + self._proposal_field_origins_section(field_origins)
                + "\n\n## Impact\n\n"
                + f"- scope: {impact.get('scope') or 'not available'}\n"
                + f"- runtime_behavior: {impact.get('runtime_behavior') or 'not available'}\n"
                + f"- compatibility: {impact.get('compatibility') or 'not available'}\n"
                + f"- risk_level: {impact.get('risk_level') or 'not available'}\n"
                + "\n### Affected Modules\n\n"
                + self._bullet_list(list(impact.get("affected_modules") or []) or ["not established"])
                + "\n\n## Risks\n\n"
                + "\n".join(
                    [
                        f"- confidence: {risks.get('confidence') or 'not available'}",
                        "- technical:",
                        self._indented_list(list(risks.get("technical") or [])),
                        "- behavioral:",
                        self._indented_list(list(risks.get("behavioral") or [])),
                        "- regression:",
                        self._indented_list(list(risks.get("regression") or [])),
                    ]
                )
                + "\n\n## Validation\n\n"
                + supported["validation"]
                + "\n\n## Rollback\n\n"
                + f"- possible: {rollback.get('possible')}\n"
                + f"- strategy: {rollback.get('strategy') or 'not available'}\n"
                + "\n### Rollback Affected Symbols\n\n"
                + self._bullet_list(list(rollback.get("affected_symbols") or []) or ["not established"])
                + "\n\n### Rollback Side Effects\n\n"
                + self._bullet_list(list(rollback.get("side_effects") or []) or ["not established"])
                + "\n\n## Evidence\n\n"
                + self._bullet_list(supported["evidence"])
                + "\n"
            )
        return (
            headers
            + "## Patch Plan\n\n"
            + f"- patch_plan_id: {supported['patch_plan_id']}\n"
            + f"- patch_plan_status: {supported['patch_plan_status']}\n"
            + f"- diff_ref: {supported['diff_ref']}\n"
            + "\n"
            + "## Target Files\n\n"
            + self._bullet_list(supported["target_files"])
            + "\n\n## Concrete Change Preview\n\n"
            + "```diff\n"
            + supported["diff_text"].rstrip()
            + "\n```\n\n"
            "## Validation\n\n"
            + supported["validation"]
            + "\n\n## Rollback\n\n"
            + supported["rollback"]
            + "\n\n## Evidence\n\n"
            + self._bullet_list(supported["evidence"])
            + "\n"
        )

    def _risk_analysis_content(
        self,
        *,
        logical_path: str,
        run_id: str,
        workspace: str,
        workspace_context: dict[str, Any],
        phase_id: str,
        analysis_payload: dict[str, Any],
        dependency_check: dict[str, Any],
    ) -> str:
        supported = self._supported_patch_evidence(analysis_payload, dependency_check)
        headers = self._artifact_header(logical_path, run_id, workspace, workspace_context, phase_id)
        if not supported["has_root_cause"]:
            return (
                headers
                + "## Risk\n\n"
                "Risk is high because the governed artifacts have not established a supported root cause.\n\n"
                "## Impact\n\n"
                "Impact not established with sufficient evidence.\n\n"
                "## Mitigation\n\n"
                "Mitigation not available until the target behavior and concrete change are supported by evidence.\n\n"
                "## Rollback\n\n"
                "Rollback not available until concrete changes are identified.\n"
            )
        return (
            headers
            + "## Patch Plan\n\n"
            + f"- patch_plan_id: {supported['patch_plan_id'] or 'not available'}\n"
            + f"- patch_plan_status: {supported['patch_plan_status'] or 'not available'}\n"
            + f"- diff_ref: {supported['diff_ref'] or 'not available'}\n"
            + "\n"
            + "## Risk\n\n"
            + supported["risk"]
            + "\n\n## Impact\n\n"
            + supported["impact"]
            + "\n\n## Mitigation\n\n"
            + supported["mitigation"]
            + "\n\n## Rollback\n\n"
            + supported["rollback"]
            + "\n\n## Evidence\n\n"
            + self._bullet_list(supported["evidence"])
            + "\n"
        )

    def _supported_patch_evidence(
        self,
        analysis_payload: dict[str, Any],
        dependency_check: dict[str, Any],
    ) -> dict[str, Any]:
        findings = [item for item in analysis_payload.get("findings", []) or [] if isinstance(item, dict)]
        patch_plan = self._patch_plan_payload(analysis_payload)
        repair_proposal = self._repair_proposal_payload(analysis_payload, patch_plan)
        patch_plan_id = str(patch_plan.get("plan_id") or "") if patch_plan else ""
        patch_plan_status = str(patch_plan.get("status") or "") if patch_plan else ""
        diff_text = self._patch_plan_diff_text(patch_plan)
        diff_ref = str((patch_plan.get("diff_proposal") or {}).get("proposal_id") or "") if patch_plan else ""
        patch_plan_targets = self._patch_plan_target_files(patch_plan)
        patch_plan_hunks = patch_plan.get("hunks") if isinstance(patch_plan.get("hunks"), list) else []
        proposal_preview_ready = self._repair_proposal_ready(repair_proposal)
        patch_plan_concrete = bool(patch_plan_id and diff_text and patch_plan_hunks)
        dependency_texts = self._dependency_artifact_texts(dependency_check)
        text = self._normalize_text(
            "\n".join(
                [
                    str(analysis_payload.get("summary") or ""),
                    *[str(item.get("summary") or "") for item in findings],
                    *[item["content"] for item in dependency_texts],
                ]
            )
        )
        evidence_paths = self._evidence_paths(findings)
        semantic_findings = [
            item for item in findings if str(item.get("category") or "") == "semantic_code_evidence"
        ]
        semantic_evidence_paths = self._evidence_paths(semantic_findings)
        semantic_domains = {
            self._semantic_domain_name(item)
            for item in semantic_findings
            if self._semantic_domain_name(item)
        }
        analysis_domains = {
            str(item.get("category") or "")
            for item in findings
            if str(item.get("category") or "")
        }
        has_code_evidence = bool(semantic_evidence_paths)
        has_prior_evidence = any(item.get("content") for item in dependency_texts)
        has_behavioral_terms = any(term in text for term in semantic_domains)
        has_root_cause = (
            has_code_evidence
            and has_prior_evidence
            and has_behavioral_terms
            and len(semantic_domains) >= 2
        )
        target_files = (patch_plan_targets or semantic_evidence_paths)[:12]
        target_functions = self._function_candidates(findings)
        root_cause = (
            "Causa raiz suportada por evidencias: os artifacts governados anteriores e o recorte "
            "de codigo atual apontam para uma divergencia entre comportamento de reproducao, "
            "decodificacao/metadata e tratamento de erro nos arquivos alvo listados."
        )
        strategy = (
            "Estrategia: aplicar uma correcao minima e governada nos arquivos alvo, preservando "
            "compatibilidade, sem alterar workspaces durante o planejamento, e validar por testes "
            "que cubram reproducao, formatos, metadata e tratamento de erro."
        )
        rollback = (
            "Rollback: reverter exclusivamente os hunks aplicados aos arquivos alvo pelo patch "
            "aprovado e restaurar artifacts gerados a partir do manifest do Artifact Runtime."
        )
        alternatives = (
            "Alternativas: ajustar apenas validacao defensiva, trocar seletor de decoder por contrato "
            "de capacidade, ou bloquear formatos sem suporte explicito quando a evidencia nao sustentar patch seguro."
        )
        validation = (
            "Validation: executar testes focados nos modulos afetados, validar artifacts obrigatorios "
            "e exigir concordancia entre Validation, Completion e Speaker Truth antes de READY."
        )
        risk = (
            "Risco: alteracoes em pipeline de reproducao ou decodificacao podem afetar formatos "
            "previamente suportados; risco mitigado por mudanca pequena, testes focados e rollback."
        )
        impact = (
            "Impacto: limitado aos arquivos alvo e aos fluxos diretamente evidenciados pelos artifacts; "
            "nao deve alterar contratos publicos nem o workspace fora do plano aprovado."
        )
        mitigation = (
            "Mitigacao: manter a mudanca atras de contratos existentes, validar entradas positivas "
            "e negativas, e bloquear conclusao se algum artifact obrigatorio ou validacao faltar."
        )
        evidence = [
            f"analysis_domain:{item}" for item in sorted(analysis_domains)
        ] + [
            f"target_file:{item}" for item in target_files
        ] + [
            f"dependency_artifact:{item['logical_path']}:{item['artifact_id']}" for item in dependency_texts
        ]
        if patch_plan_id:
            evidence.append(f"patch_plan:{patch_plan_id}")
        if diff_ref:
            evidence.append(f"diff_ref:{diff_ref}")
        if repair_proposal:
            proposal_id = str(repair_proposal.get("proposal_id") or "")
            if proposal_id:
                evidence.append(f"repair_proposal:{proposal_id}")
        return {
            "has_root_cause": has_root_cause,
            "patch_plan_id": patch_plan_id,
            "patch_plan_status": patch_plan_status,
            "patch_plan_concrete": patch_plan_concrete,
            "patch_preview_supported": bool(repair_proposal or patch_plan_concrete),
            "diff_ref": diff_ref,
            "diff_text": diff_text,
            "root_cause": root_cause,
            "target_files": target_files,
            "target_functions": target_functions,
            "strategy": strategy,
            "rollback": rollback,
            "alternatives": alternatives,
            "validation": validation,
            "risk": risk,
            "impact": impact,
            "mitigation": mitigation,
            "evidence": evidence or ["not established"],
            "repair_proposal": repair_proposal,
        }

    def _patch_plan_payload(self, analysis_payload: dict[str, Any]) -> dict[str, Any]:
        planning = analysis_payload.get("patch_planning")
        if not isinstance(planning, dict):
            return {}
        plan = planning.get("plan")
        return plan if isinstance(plan, dict) else {}

    def _patch_plan_id(self, analysis_payload: dict[str, Any] | None) -> str | None:
        if not analysis_payload:
            return None
        plan_id = self._patch_plan_payload(analysis_payload).get("plan_id")
        return str(plan_id) if plan_id else None

    def _patch_plan_diff_text(self, patch_plan: dict[str, Any]) -> str:
        if not patch_plan:
            return ""
        proposal = patch_plan.get("diff_proposal")
        if not isinstance(proposal, dict):
            return ""
        diff = proposal.get("diff")
        if not isinstance(diff, dict):
            return ""
        return str(diff.get("diff_text") or "")

    def _repair_proposal_payload(
        self,
        analysis_payload: dict[str, Any],
        patch_plan: dict[str, Any],
    ) -> dict[str, Any]:
        proposal = patch_plan.get("repair_proposal") if isinstance(patch_plan.get("repair_proposal"), dict) else None
        if proposal:
            return self._normalized_repair_proposal_payload(proposal)
        planning = analysis_payload.get("patch_planning")
        if not isinstance(planning, dict):
            return {}
        proposal = planning.get("repair_proposal")
        if isinstance(proposal, dict):
            return self._normalized_repair_proposal_payload(proposal)
        metadata = planning.get("metadata")
        if isinstance(metadata, dict):
            proposal = metadata.get("repair_proposal")
            if isinstance(proposal, dict):
                return self._normalized_repair_proposal_payload(proposal)
        return {}

    def _normalized_repair_proposal_payload(self, proposal: dict[str, Any]) -> dict[str, Any]:
        try:
            normalized = dict(proposal)
            assembly = normalized.get("assembly")
            if isinstance(assembly, dict):
                assembly = dict(assembly)
                assembly.pop("assembly_status", None)
                assembly.pop("assembly_score", None)
                normalized["assembly"] = assembly
            artifact = RepairProposalArtifact(**normalized)
            payload = artifact.model_dump(mode="json")
            if isinstance(payload.get("assembly"), dict):
                payload["assembly"] = {
                    **dict(payload.get("assembly") or {}),
                    "assembly_status": artifact.assembly.assembly_status,
                    "assembly_score": artifact.assembly.assembly_score,
                }
            return payload
        except Exception:
            return dict(proposal)

    def _repair_proposal_ready(self, proposal: dict[str, Any]) -> bool:
        if not proposal:
            return False
        if isinstance(proposal.get("proposal_status"), str) and proposal.get("proposal_status") == "complete":
            return True
        target = proposal.get("target") if isinstance(proposal.get("target"), dict) else {}
        concrete = proposal.get("concrete_change") if isinstance(proposal.get("concrete_change"), dict) else {}
        rollback = proposal.get("rollback") if isinstance(proposal.get("rollback"), dict) else {}
        impact = proposal.get("impact") if isinstance(proposal.get("impact"), dict) else {}
        risks = proposal.get("risks") if isinstance(proposal.get("risks"), dict) else {}
        return bool(
            str(target.get("file") or "").strip()
            and str(target.get("symbol") or "").strip()
            and str(proposal.get("intent") or "").strip()
            and str(concrete.get("objective") or "").strip()
            and str(concrete.get("current_behavior") or "").strip()
            and str(concrete.get("expected_behavior") or "").strip()
            and str(concrete.get("modification_strategy") or "").strip()
            and list(concrete.get("affected_symbols") or [])
            and str(concrete.get("reasoning") or "").strip()
            and str(rollback.get("strategy") or "").strip()
            and str(impact.get("scope") or "").strip()
            and list(impact.get("affected_modules") or [])
            and str(impact.get("runtime_behavior") or "").strip()
            and str(impact.get("compatibility") or "").strip()
            and str(impact.get("risk_level") or "").strip()
            and (
                list(risks.get("technical") or [])
                or list(risks.get("behavioral") or [])
                or list(risks.get("regression") or [])
                or str(risks.get("confidence") or "").strip()
            )
        )

    def _proposal_component_section(self, components: dict[str, Any]) -> str:
        if not components:
            return "- status: not available\n- diagnostics: repair proposal components not available"
        lines: list[str] = []
        for key in ["target", "behavior", "strategy", "impact", "rollback", "confidence"]:
            component = components.get(key) if isinstance(components.get(key), dict) else {}
            status = str(component.get("status") or "missing")
            reason_codes = list(component.get("reason_codes") or [])
            diagnostics = list(component.get("diagnostics") or [])
            lines.append(f"- {key}: {status}")
            if reason_codes:
                lines.append(f"  - reason_codes: {', '.join(str(item) for item in reason_codes)}")
            if diagnostics:
                lines.append(f"  - diagnostics: {', '.join(str(item) for item in diagnostics)}")
        return "\n".join(lines)

    def _proposal_assembly_section(self, assembly: dict[str, Any]) -> str:
        if not assembly:
            return "- status: not available\n- diagnostics: repair proposal assembly not available"
        lines: list[str] = []
        for key in ["semantic_evidence", "behavior_localization", "behavior_justification", "candidate_transformation"]:
            stage = assembly.get(key) if isinstance(assembly.get(key), dict) else {}
            status = str(stage.get("status") or "missing")
            coverage_score = stage.get("coverage_score")
            reason_codes = list(stage.get("reason_codes") or [])
            diagnostics = list(stage.get("diagnostics") or [])
            lines.append(f"- {key}: {status}")
            if coverage_score is not None:
                lines.append(f"  - coverage_score: {coverage_score}")
            if reason_codes:
                lines.append(f"  - reason_codes: {', '.join(str(item) for item in reason_codes)}")
            if diagnostics:
                lines.append(f"  - diagnostics: {', '.join(str(item) for item in diagnostics)}")
        return "\n".join(lines)

    def _proposal_field_origins_section(self, field_origins: dict[str, Any]) -> str:
        if not field_origins:
            return "- not available"
        lines: list[str] = []
        for key in ["target", "intent", "concrete_change", "rollback", "impact", "risks"]:
            values = field_origins.get(key)
            if isinstance(values, list) and values:
                lines.append(f"- {key}: {', '.join(str(item) for item in values if str(item).strip())}")
        return "\n".join(lines) if lines else "- not available"

    def _patch_plan_target_files(self, patch_plan: dict[str, Any]) -> list[str]:
        if not patch_plan:
            return []
        values: list[str] = []
        for item in patch_plan.get("affected_files", []) or []:
            if not isinstance(item, dict):
                continue
            value = item.get("relative_path") or item.get("path") or item.get("normalized_path")
            if value:
                values.append(str(value))
        return list(dict.fromkeys(values))

    def _plan_has_concrete_hunks(self, patch_plan: dict[str, Any]) -> bool:
        if not patch_plan:
            return False
        proposal = patch_plan.get("diff_proposal")
        diff = proposal.get("diff") if isinstance(proposal, dict) else None
        diff_text = str((diff or {}).get("diff_text") or "") if isinstance(diff, dict) else ""
        hunks = patch_plan.get("hunks")
        return bool(diff_text and isinstance(hunks, list) and hunks)

    def _semantic_domain_name(self, finding: dict[str, Any]) -> str:
        title = str(finding.get("title") or "")
        if ":" in title:
            return self._normalize_text(title.rsplit(":", 1)[-1])
        return ""

    def _dependency_artifact_texts(self, dependency_check: dict[str, Any]) -> list[dict[str, str]]:
        values: list[dict[str, str]] = []
        for artifact in dependency_check.get("artifacts", []) or []:
            if not isinstance(artifact, dict):
                continue
            content = self._artifact_content_from_record(artifact)
            if not content:
                continue
            values.append(
                {
                    "artifact_id": str(artifact.get("artifact_id") or ""),
                    "logical_path": str(
                        (artifact.get("metadata") or {}).get("logical_path")
                        or (artifact.get("provenance") or {}).get("logical_path")
                        or artifact.get("logical_path")
                        or artifact.get("filename")
                        or "artifact"
                    ),
                    "content": content[:6000],
                }
            )
        return values

    def _analysis_prompt_with_dependencies(self, prompt: str, dependency_check: dict[str, Any]) -> str:
        dependency_texts = self._dependency_artifact_texts(dependency_check)
        if not dependency_texts:
            return prompt
        excerpts = [
            f"{item['logical_path']}\n{item['content'][:2000]}"
            for item in dependency_texts[:8]
            if item.get("content")
        ]
        if not excerpts:
            return prompt
        return f"{prompt}\n\nGoverned dependency artifact context:\n" + "\n\n".join(excerpts)

    def _evidence_paths(self, findings: list[dict[str, Any]]) -> list[str]:
        paths: list[str] = []
        for item in findings:
            for path in item.get("evidence_paths", []) or []:
                value = str(path)
                if value and value not in paths:
                    paths.append(value)
        return paths

    def _function_candidates(self, findings: list[dict[str, Any]]) -> list[str]:
        candidates: list[str] = []
        pattern = re.compile(r"\b(?:fun|def|function|class|method)\s+([A-Za-z_][A-Za-z0-9_]*)")
        for item in findings:
            summary = str(item.get("summary") or "")
            for match in pattern.finditer(summary):
                value = match.group(1)
                if value not in candidates:
                    candidates.append(value)
            symbol_match = re.search(r"\bSymbols:\s*(?P<symbols>[^.]+)", summary)
            if symbol_match:
                for raw_symbol in symbol_match.group("symbols").split(","):
                    value = raw_symbol.strip()
                    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) and value not in candidates:
                        candidates.append(value)
        return candidates[:20]

    def _artifact_header(
        self,
        logical_path: str,
        run_id: str,
        workspace: str,
        workspace_context: dict[str, Any],
        phase_id: str,
    ) -> str:
        return (
            f"# {logical_path}\n\n"
            f"- task_run_id: {run_id}\n"
            f"- workspace: {workspace}\n"
            f"- phase_id: {phase_id}\n"
            "- workspace_mutation: false\n"
            "- artifact_generation: true\n"
            f"- workspace_context: {json.dumps(workspace_context, ensure_ascii=False)}\n\n"
        )

    def _bullet_list(self, values: list[str]) -> str:
        return "\n".join(f"- {item}" for item in values) if values else "- not established"

    def _indented_list(self, values: list[str]) -> str:
        return "\n".join(f"  - {item}" for item in values) if values else "  - not available"

    def _normalize_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        normalized = normalized.casefold().replace("_", " ").replace("-", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _request_workspace_context(self, request) -> dict[str, Any]:
        value = getattr(request, "workspace_context", None)
        context = dict(value) if isinstance(value, dict) else {}
        message = getattr(request, "message", "") or ""
        extracted_roots = PathExtractionService().extract(message)
        explicit_roots = [item.value for item in extracted_roots]
        role_by_root = self._explicit_root_roles(message, extracted_roots)
        project_roots_from_prompt = [root for root in explicit_roots if role_by_root.get(root) == "project_root"]
        project_root = str(
            context.get("project_root")
            or context.get("workspace")
            or (project_roots_from_prompt[0] if project_roots_from_prompt else explicit_roots[0] if explicit_roots else "")
        )
        external_roots = self._string_list(context.get("external_roots"))
        for root in explicit_roots:
            if root and root != project_root and role_by_root.get(root) not in {"library_root", "corpus_root"} and root not in external_roots:
                external_roots.append(root)
        library_roots = self._string_list(context.get("library_roots"))
        for root in explicit_roots:
            if role_by_root.get(root) in {"library_root", "corpus_root"} and root not in library_roots:
                library_roots.append(root)
        if len(explicit_roots) > 1:
            for root in explicit_roots[1:]:
                if root and root not in library_roots:
                    library_roots.append(root)
        readonly_flags = {
            str(key): bool(item)
            for key, item in (context.get("readonly_flags") or {}).items()
        } if isinstance(context.get("readonly_flags"), dict) else {}
        for root in explicit_roots:
            readonly_flags.setdefault(root, True)
        return {
            "external_roots": external_roots,
            "library_roots": library_roots,
            "readonly_flags": readonly_flags,
            "workspace_ids": self._string_list(context.get("workspace_ids")),
            "project_root": project_root,
        }

    def _phase0_readiness_ref(self, request) -> dict[str, Any]:
        context = getattr(request, "context", None)
        phase0_result_ref = getattr(context, "phase0_result_ref", None) if context is not None else None
        cognitive_readiness_id = getattr(context, "cognitive_readiness_id", None) if context is not None else None
        phase0_prediction_id = getattr(context, "phase0_prediction_id", None) if context is not None else None
        phase0_decision = getattr(context, "phase0_decision", None) if context is not None else None
        no_go = str(phase0_decision or "").startswith("NO_GO")
        return {
            "cognitive_readiness_id": cognitive_readiness_id,
            "phase0_result_ref": phase0_result_ref,
            "phase0_prediction_id": phase0_prediction_id,
            "phase0_decision": phase0_decision,
            "runtime_executed_despite_cvl_no_go": no_go,
        }

    def _calibrate_phase0_prediction(self, run_id: str, phase0_ref: dict[str, Any]) -> None:
        ref = str(phase0_ref.get("phase0_result_ref") or phase0_ref.get("cognitive_readiness_id") or "")
        if not ref:
            return
        try:
            service = CognitiveReadinessService(store=self.runtime.store)
            readiness = service.load_readiness(ref)
            if readiness is None:
                self.runtime.events.create(
                    run_id,
                    "phase0_prediction_calibration_unavailable",
                    "missing",
                    "Phase 0 cognitive readiness reference could not be loaded for calibration.",
                    metadata={"phase0_result_ref": ref},
                )
                return
            calibration_path = None
            ref_path = Path(ref)
            if ref_path.exists():
                calibration_path = ref_path.parent / "firetest5_phase0_vs_phase1_calibration.json"
            calibration = service.calibrate_phase1(readiness=readiness, task_run_id=run_id, write_path=calibration_path)
            self.runtime.events.create(
                run_id,
                "phase0_prediction_calibrated",
                calibration.status,
                "Phase 0 prediction calibrated against Phase 1 runtime result.",
                metadata={
                    "readiness_id": readiness.readiness_id,
                    "calibration_id": calibration.calibration_id,
                    "overall_accuracy_score": calibration.overall_accuracy_score,
                    "confidence_error": calibration.confidence_error,
                    "status": calibration.status,
                },
            )
        except Exception as exc:
            self.runtime.events.create(
                run_id,
                "phase0_prediction_calibration_failed",
                "failed",
                "Phase 0 prediction calibration failed without changing runtime result authority.",
                metadata={"phase0_result_ref": ref, "error_type": type(exc).__name__, "error_message": str(exc)[:300]},
            )

    def _explicit_root_roles(self, message: str, extracted_roots: list[Any]) -> dict[str, str]:
        policy = self.observed_entities.policy.get("root_role_policy") if isinstance(self.observed_entities.policy.get("root_role_policy"), dict) else {}
        marker_policy = policy.get("root_role_markers") if isinstance(policy.get("root_role_markers"), dict) else {}
        default_markers = {
            "project_root": ["project", "projeto", "workspace", "app"],
            "library_root": ["library", "biblioteca", "corpus", "collection", "colecao", "dataset"],
        }
        markers = {
            role: [self._normalize_text(item) for item in (marker_policy.get(role) or defaults) if str(item).strip()]
            for role, defaults in default_markers.items()
        }
        roles: dict[str, str] = {}
        for item in extracted_roots:
            prefix = message[max(0, int(getattr(item, "start", 0)) - 120): int(getattr(item, "start", 0))]
            nearby_lines = [self._normalize_text(line) for line in prefix.splitlines() if line.strip()]
            nearby = " ".join(nearby_lines[-3:])
            for role in ("library_root", "project_root"):
                if any(marker and re.search(rf"\b{re.escape(marker)}\b", nearby) for marker in markers.get(role, [])):
                    roles[str(getattr(item, "value", "") or "")] = role
                    break
        return roles

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if item]
        return []

    def _analysis_payload(self, result: Any) -> dict[str, Any]:
        tree = result.tree_summary
        report = result.report
        return {
            "result_id": result.result_id,
            "status": result.status,
            "reason_code": result.reason_code,
            "safe_to_continue": result.safe_to_continue,
            "partial": result.partial,
            "workspace": tree.workspace,
            "tree_status": tree.status,
            "total_files_seen": tree.total_files_seen,
            "total_dirs_seen": tree.total_dirs_seen,
            "files_discovered": result.files_discovered,
            "files_selected": result.files_selected,
            "files_read": result.files_read,
            "files_partial_read": getattr(result, "files_partial_read", 0),
            "files_skipped": getattr(result, "files_skipped", 0),
            "bytes_read": result.bytes_read,
            "bytes_skipped_estimated": getattr(result, "bytes_skipped_estimated", 0),
            "read_decisions": list(getattr(result, "read_decisions", []) or [])[:100],
            "remaining_budget_ms_at_return": result.remaining_budget_ms_at_return,
            "handoff_reserve_reached": result.handoff_reserve_reached,
            "file_selection_plan": self._compact_project_analysis_plan(result.file_selection_plan),
            "file_read_plan": self._compact_project_analysis_plan(result.file_read_plan),
            "partial_readiness": result.partial_readiness,
            "corpus_handoff": getattr(result, "corpus_handoff", None),
            "budget_cooperation_policy": result.budget_cooperation_policy,
            "top_level": list(tree.top_level[:50]),
            "important_paths": list(tree.important_paths[:50]),
            "candidate_files": list(tree.candidate_files[:50]),
            "structures": list(result.structures[:50]),
            "summary": report.summary,
            "findings": [
                {
                    "severity": item.severity,
                    "category": item.category,
                    "title": item.title,
                    "summary": item.summary,
                    "evidence_paths": list(item.evidence_paths),
                    "recommendation": item.recommendation,
                }
                for item in result.findings[:50]
            ],
            "warnings": list(result.warnings),
            "violations": list(result.violations),
        }

    def _compact_project_analysis_plan(self, plan: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(plan, dict):
            return None
        compact = dict(plan)
        if isinstance(compact.get("selected_files"), list):
            compact["selected_files_count"] = len(compact["selected_files"])
            compact["selected_files_sample"] = compact["selected_files"][:10]
            compact.pop("selected_files", None)
        if isinstance(compact.get("read_order"), list):
            compact["read_order_count"] = len(compact["read_order"])
            compact["read_order_sample"] = compact["read_order"][:10]
            compact.pop("read_order", None)
        if isinstance(compact.get("skipped_files"), list):
            compact["skipped_files_count"] = len(compact["skipped_files"])
            compact["skipped_files_sample"] = compact["skipped_files"][:10]
            compact.pop("skipped_files", None)
        if isinstance(compact.get("read_errors"), list):
            compact["read_errors_count"] = len(compact["read_errors"])
            compact["read_errors_sample"] = compact["read_errors"][:10]
            compact.pop("read_errors", None)
        return compact

    def _validate_outputs(
        self,
        *,
        logical_paths: list[str],
        artifacts: list[dict[str, Any]],
        analysis_payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        by_logical = {
            str((item.get("metadata") or {}).get("logical_path") or (item.get("provenance") or {}).get("logical_path") or item.get("logical_path")): item
            for item in artifacts
            if isinstance(item, dict)
        }
        missing: list[str] = []
        ready_artifacts: list[str] = []
        semantic_validations: list[dict[str, Any]] = []
        for logical_path in logical_paths:
            record = by_logical.get(logical_path)
            artifact_id = str(record.get("artifact_id")) if record else ""
            public = self.artifact_runtime.revalidate_public(artifact_id) if artifact_id else None
            if not public or public.get("status") != "ready":
                missing.append(f"artifact:{logical_path}")
            else:
                semantic_validation = self._validate_artifact_semantic_contract(logical_path, public)
                semantic_validations.append(semantic_validation)
                if not semantic_validation.get("profile"):
                    missing.append(f"artifact_semantic_profile:{logical_path}")
                if semantic_validation["status"] == "blocked":
                    missing.extend(
                        f"artifact_semantic_contract:{logical_path}:{item}"
                        for item in semantic_validation.get("missing_requirements", [])
                    )
                ready_artifacts.append(artifact_id)
        if not analysis_payload:
            missing.append("project_analysis_report")
        status = "passed" if not missing else "blocked"
        return {
            "status": status,
            "safe_to_report_success": status == "passed",
            "expected_outputs": [
                "project_analysis_report",
                "artifact_result",
                "validation_result",
                *[f"artifact:{item}" for item in logical_paths],
                *[f"artifact_semantic_profile:{item}" for item in logical_paths],
            ],
            "fulfilled_outputs": [
                "project_analysis_report",
                "artifact_result",
                "validation_result",
                *[f"artifact:{item}" for item in logical_paths if f"artifact:{item}" not in missing],
                *[
                    f"artifact_semantic_profile:{item}"
                    for item in logical_paths
                    if f"artifact_semantic_profile:{item}" not in missing
                ],
            ]
            if status == "passed"
            else [
                "artifact_result",
                *[f"artifact:{item}" for item in logical_paths if f"artifact:{item}" not in missing],
                *[
                    f"artifact_semantic_profile:{item}"
                    for item in logical_paths
                    if f"artifact_semantic_profile:{item}" not in missing
                    and any(validation.get("logical_path") == item and validation.get("profile") for validation in semantic_validations)
                ],
            ]
            if ready_artifacts
            else [],
            "missing_outputs": missing,
            "artifact_ids": ready_artifacts,
            "artifact_semantic_validations": semantic_validations,
            "artifact_semantic_profiles": [
                item.get("profile")
                for item in semantic_validations
                if isinstance(item.get("profile"), dict)
            ],
        }

    def _validate_artifact_semantic_contract(self, logical_path: str, artifact: dict[str, Any]) -> dict[str, Any]:
        result = self.artifact_semantic_contracts.validate_artifact(artifact)
        return {
            "logical_path": logical_path,
            "artifact_id": artifact.get("artifact_id"),
            "status": result.status,
            "contract_id": result.contract_id,
            "missing_requirements": list(result.missing_requirements),
            "warnings": list(result.warnings),
            "profile": result.profile.model_dump(mode="json") if result.profile else None,
        }

    def _artifact_content_from_record(self, artifact: dict[str, Any]) -> str:
        local_path = artifact.get("local_path") or artifact.get("storage_path")
        if not local_path:
            return ""
        try:
            path = Path(str(local_path))
            if not path.is_absolute():
                path = PATHS.project_root / path
            return path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def _apply_phase_completion_decision(
        self,
        validation: dict[str, Any],
        decision: PhaseCompletionDecision,
    ) -> dict[str, Any]:
        patched = dict(validation)
        patch = decision.validation_patch()
        patched.update(patch)
        if decision.status == "blocked":
            patched["status"] = "blocked"
            patched["safe_to_report_success"] = False
        elif decision.status == "completed_with_limitations":
            patched["status"] = "passed_with_limitations"
            patched["safe_to_report_success"] = bool(decision.safe_to_report_success)
        elif decision.status == "completed":
            patched["status"] = "passed"
            patched["safe_to_report_success"] = bool(decision.safe_to_report_success)
        if decision.missing_outputs:
            patched["missing_outputs"] = list(decision.missing_outputs)
        if decision.fulfilled_outputs:
            patched["fulfilled_outputs"] = list(decision.fulfilled_outputs)
        patched["limited_outputs"] = list(decision.limited_outputs)
        patched["semantic_completion_reason_code"] = decision.reason_code
        return patched

    def _completion(
        self,
        logical_paths: list[str],
        artifacts: list[dict[str, Any]],
        validation: dict[str, Any],
        *,
        status: str,
        phase_decision: PhaseCompletionDecision | None = None,
    ) -> TaskCompletionEvaluation:
        if phase_decision is not None:
            criteria = [
                TaskCompletionCriterion(
                    criterion_id=item,
                    kind="phase_semantic_completion_output",
                    status="missing" if item in phase_decision.missing_outputs else "fulfilled",
                    summary=(
                        f"Expected semantic output {item} is missing or blocked."
                        if item in phase_decision.missing_outputs
                        else f"Expected semantic output {item} is fulfilled or available with limitations."
                    ),
                    evidence_refs=[item] if item not in phase_decision.missing_outputs else [],
                    metadata={"phase_contract_status": phase_decision.phase_contract_status},
                )
                for item in phase_decision.expected_outputs
            ]
            return TaskCompletionEvaluation(
                status=phase_decision.status,  # type: ignore[arg-type]
                safe_to_report_success=phase_decision.safe_to_report_success,
                expected_outcomes=list(phase_decision.expected_outputs),
                fulfilled_outcomes=list(phase_decision.fulfilled_outputs),
                missing_outcomes=list(phase_decision.missing_outputs),
                criteria=criteria,
                warnings=[],
                limitations=list(phase_decision.limitations),
                metadata={
                    "reason_code": phase_decision.reason_code,
                    "artifact_count": len(artifacts),
                    "logical_paths": logical_paths,
                    "artifact_semantic_profiles": validation.get("artifact_semantic_profiles") or [],
                    "limited_outputs": list(phase_decision.limited_outputs),
                    "limiting_findings": list(phase_decision.limiting_findings),
                    "blocking_findings": list(phase_decision.blocking_findings),
                    "safe_for_limited_discovery": phase_decision.safe_for_limited_discovery,
                    "partial_artifact_accepted": phase_decision.partial_artifact_accepted,
                    "allowed_claims": list(phase_decision.allowed_claims),
                    "forbidden_claims": list(phase_decision.forbidden_claims),
                    "required_disclosures": list(phase_decision.required_disclosures),
                    "phase_dependency": phase_decision.phase_dependency,
                    "policy": phase_decision.metadata,
                },
            )
        expected = list(validation.get("expected_outputs") or [])
        fulfilled = list(validation.get("fulfilled_outputs") or [])
        missing = list(validation.get("missing_outputs") or [])
        criteria = [
            TaskCompletionCriterion(
                criterion_id=item,
                kind="runtime_vertical_slice_output",
                status="missing" if item in missing else "fulfilled",
                summary=(
                    f"Expected output {item} is missing."
                    if item in missing
                    else f"Expected output {item} is present."
                ),
                evidence_refs=[item] if item not in missing else [],
            )
            for item in expected
        ]
        completed = status == "completed" and not missing
        return TaskCompletionEvaluation(
            status="completed" if completed else "blocked",
            safe_to_report_success=completed,
            expected_outcomes=expected,
            fulfilled_outcomes=fulfilled,
            missing_outcomes=missing,
            criteria=criteria,
            limitations=[] if completed else ["missing_required_expected_outcomes:" + ",".join(missing)],
            metadata={
                "artifact_count": len(artifacts),
                "logical_paths": logical_paths,
                "artifact_semantic_profiles": validation.get("artifact_semantic_profiles") or [],
                "semantic_gaps": [
                    gap
                    for item in validation.get("artifact_semantic_validations") or []
                    for gap in (item.get("missing_requirements") or [])
                    if isinstance(item, dict)
                ],
            },
        )

    def _response(
        self,
        request,
        *,
        workspace: str,
        label: str,
        task_id: str | None,
        run_id: str,
        logical_paths: list[str],
        artifacts: list[dict[str, Any]],
        validation: dict[str, Any],
        completion: TaskCompletionEvaluation,
        dependency_check: dict[str, Any],
        status: str,
    ) -> ChatResponse:
        artifact_links = [
            ChatArtifactLink(
                artifact_id=str(item.get("artifact_id")),
                filename=str(item.get("filename")),
                content_type=str(item.get("content_type") or "text/plain"),
                size_bytes=int(item.get("size_bytes") or item.get("size") or 0),
                download_endpoint=str(item.get("download_endpoint") or f"/api/v1/artifacts/{item.get('artifact_id')}/download"),
                download_path=str(item.get("download_endpoint") or f"/api/v1/artifacts/{item.get('artifact_id')}/download"),
                label=str((item.get("metadata") or {}).get("logical_path") or item.get("filename") or "Baixar artifact"),
                requires_token=bool(item.get("requires_token", True)),
            )
            for item in artifacts
            if item.get("artifact_id")
        ]
        message = (
            f"{label if status == 'completed' else 'RUNTIME_ANALYSIS_VERTICAL_SLICE_BLOCKED'}\n"
            "TaskRun read-only executada pelo runtime governado.\n\n"
            f"- task_run_id: {run_id}\n"
            f"- workspace: {workspace}\n"
            "- workspace_mutation: false\n"
            "- artifact_generation: true\n"
            f"- artifacts_requested: {len(logical_paths)}\n"
            f"- artifacts_created: {len(artifact_links)}\n"
            f"- validation_status: {validation['status']}\n"
            f"- completion_status: {completion.status}\n"
            f"- safe_to_report_success: {str(completion.safe_to_report_success).lower()}\n\n"
            "Artifacts:\n"
            + "\n".join(f"- {link.label}: {link.artifact_id}" for link in artifact_links)
            + "\n\n"
            f"Phase dependency validation: {dependency_check['status']}"
        )
        return ChatResponse(
            response_id=f"chat_{run_id.replace('task_run_', '')}",
            session_id=request.session_id,
            task_id=task_id,
            task_run_id=run_id,
            result_ref_id=run_id,
            operation_id=f"chatop_{run_id.replace('task_run_', '')}",
            operation_type="workspace_analysis_readonly",
            message_type="assistant_final_answer" if status == "completed" else "assistant_degraded_answer",
            status="ok" if status == "completed" else "blocked",
            message=message,
            intent={
                "intent_type": "workspace_analysis_readonly",
                "operation_type": "workspace_analysis_readonly",
                "requires_task": True,
                "readonly": True,
                "side_effect_requested": False,
                "workspace_mutation": False,
                "artifact_generation": True,
            },
            policy={
                "read_only": True,
                "workspace_mutation": False,
                "artifact_generation": True,
                "approval_required_for": [],
                "write_allowed": False,
                "shell_allowed": False,
                "workspace": workspace,
                "validation_status": validation["status"],
                "completion_status": completion.status,
                "safe_to_report_success": completion.safe_to_report_success,
            },
            contract_preview={
                "contract_type": "analysis_readonly",
                "runtime_profile": "readonly_analysis",
                "workspace": workspace,
                "task_run_id": run_id,
                "executable_plan_ref": run_id,
                "expected_outputs": list(validation.get("expected_outputs") or []),
                "logical_artifact_paths": logical_paths,
                "artifact_ids": [link.artifact_id for link in artifact_links],
                "project_analysis_report": {"task_run_id": run_id, "status": "present"},
                "validation_result": validation,
                "completion": completion.model_dump(),
                "phase_dependency_result": dependency_check,
            },
            actions=[],
            artifact_links=artifact_links,
            evidence_refs=[
                {"kind": "task_run", "id": run_id},
                *[{"kind": "artifact", "id": link.artifact_id, "logical_path": link.label} for link in artifact_links],
            ],
            grounded=completion.safe_to_report_success,
            is_final_answer=status == "completed",
            model_used="readonly_analysis_artifact_runtime",
            real_inference=False,
            fallback_used=False,
        )

    def _blocked_response(
        self,
        request,
        *,
        workspace: str,
        reason_code: str,
        missing: list[str],
        dependency_check: dict[str, Any] | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            response_id=f"chat_blocked_{abs(hash((request.message, reason_code))) & 0xffffffff:x}",
            session_id=request.session_id,
            operation_type="workspace_analysis_readonly",
            message_type="blocked_policy_message",
            status="blocked",
            message=(
                "RUNTIME_ANALYSIS_VERTICAL_SLICE_BLOCKED\n"
                f"reason_code={reason_code}\n"
                f"workspace={workspace}\n"
                f"missing_outputs={missing}\n"
                "Nenhuma escrita no workspace foi executada."
            ),
            intent={
                "intent_type": "workspace_analysis_readonly",
                "requires_task": False,
                "readonly": True,
                "artifact_generation": True,
            },
            policy={
                "read_only": True,
                "workspace_mutation": False,
                "artifact_generation": True,
                "validation_status": "blocked",
                "reason_code": reason_code,
            },
            contract_preview={
                "workspace": workspace,
                "reason_code": reason_code,
                "expected_outputs": ["artifact_result", "validation_result"],
                "missing_outputs": missing,
                "phase_dependency_result": dependency_check or {},
            },
            is_final_answer=False,
            grounded=False,
            grounding_required=True,
            grounding_missing_reason=reason_code,
            model_used="readonly_analysis_artifact_runtime",
            real_inference=False,
        )

    def _validate_phase_dependencies(
        self,
        *,
        session_id: str | None,
        dependency_phase_ids: list[str],
        semantic: bool = True,
    ) -> dict[str, Any]:
        if not dependency_phase_ids:
            return {"status": "passed", "dependency_phase_ids": [], "artifacts": [], "missing": [], "semantic_check_performed": False}
        store = self._load_phase_store()
        missing: list[str] = []
        artifacts: list[dict[str, Any]] = []
        semantic_validations: list[dict[str, Any]] = []
        semantic_missing: list[str] = []
        for phase_id in dependency_phase_ids:
            match = self._latest_phase_record(store, phase_id=phase_id, session_id=session_id)
            if not match:
                missing.append(f"phase:{phase_id}")
                continue
            for item in match.get("artifacts", []) or []:
                artifact_id = str(item.get("artifact_id") or "")
                if not semantic:
                    if not artifact_id:
                        missing.append("artifact:missing")
                    else:
                        artifacts.append(
                            {
                                "artifact_id": artifact_id,
                                "logical_path": item.get("logical_path")
                                or (item.get("metadata") or {}).get("logical_path")
                                or (item.get("provenance") or {}).get("logical_path"),
                                "status": item.get("status") or "phase_recorded",
                                "preflight_only": True,
                            }
                        )
                    continue
                public = self.artifact_runtime.revalidate_public(artifact_id) if artifact_id else None
                if not public or public.get("status") != "ready":
                    missing.append(f"artifact:{artifact_id or 'missing'}")
                else:
                    if semantic:
                        semantic_validation = self._validate_artifact_semantic_contract(
                            str(public.get("logical_path") or (public.get("metadata") or {}).get("logical_path") or artifact_id),
                            public,
                        )
                        semantic_validations.append(semantic_validation)
                        if semantic_validation["status"] == "blocked":
                            logical_path = semantic_validation.get("logical_path") or public.get("logical_path") or artifact_id
                            semantic_missing.extend(
                                f"artifact_semantic_contract:{logical_path}:{item}"
                                for item in semantic_validation.get("missing_requirements", [])
                            )
                    artifacts.append(public)
        all_missing = [*missing, *semantic_missing]
        reason_code = (
            "PHASE_DEPENDENCY_SEMANTIC_INSUFFICIENT"
            if semantic_missing
            else "phase_dependency_artifacts_missing"
            if missing
            else None
        )
        return {
            "status": "passed" if not all_missing else "blocked",
            "reason_code": reason_code,
            "safe_to_report_success": not all_missing,
            "dependency_phase_ids": dependency_phase_ids,
            "artifacts": artifacts,
            "missing": all_missing,
            "artifact_semantic_validations": semantic_validations,
            "semantic_check_performed": semantic,
        }

    def _record_phase(
        self,
        *,
        session_id: str | None,
        phase_id: str,
        run_id: str,
        workspace: str,
        artifacts: list[dict[str, Any]],
        logical_paths: list[str],
        patch_plan_id: str | None = None,
    ) -> None:
        store = self._load_phase_store()
        store.append(
            {
                "session_id": session_id,
                "phase_id": phase_id,
                "run_id": run_id,
                "workspace": workspace,
                "logical_paths": logical_paths,
                "artifacts": artifacts,
                "patch_plan_id": patch_plan_id,
                "status": "completed",
                "created_at": utc_now(),
            }
        )
        self.phase_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.phase_store_path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_phase_store(self) -> list[dict[str, Any]]:
        if not self.phase_store_path.exists():
            return []
        try:
            data = json.loads(self.phase_store_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return []
        return data if isinstance(data, list) else []

    def _latest_phase_record(
        self,
        store: list[dict[str, Any]],
        *,
        phase_id: str,
        session_id: str | None,
    ) -> dict[str, Any] | None:
        candidates = [
            item
            for item in store
            if item.get("phase_id") == phase_id
            and (not session_id or item.get("session_id") == session_id)
        ]
        if not candidates and session_id:
            candidates = [item for item in store if item.get("phase_id") == phase_id]
        return sorted(candidates, key=lambda item: str(item.get("created_at") or ""), reverse=True)[0] if candidates else None

    def _phase_record_patch_plan_id(self, record: dict[str, Any]) -> str | None:
        value = record.get("patch_plan_id")
        if value:
            return str(value)
        for artifact in record.get("artifacts", []) or []:
            if not isinstance(artifact, dict):
                continue
            metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
            value = metadata.get("patch_plan_id")
            if value:
                return str(value)
        return None

    def _artifact_generation_requested(self, text: str) -> bool:
        normalized = str(text or "").casefold()
        if any(term in normalized for term in self.ARTIFACT_FORBIDDEN_TERMS):
            return False
        if not any(term in normalized for term in self.ARTIFACT_REQUEST_TERMS):
            return False
        return bool(_ARTIFACT_PATH_RE.search(text or ""))

    def _phase_id(self, text: str) -> str | None:
        matches = [match.group("phase").lower() for match in _PHASE_RE.finditer(text or "")]
        return f"phase_{matches[0]}" if matches else None

    def _dependency_phase_ids(self, text: str, *, current_phase_id: str) -> list[str]:
        phase_ids = [f"phase_{match.group('phase').lower()}" for match in _PHASE_RE.finditer(text or "")]
        normalized = str(text or "").casefold()
        normalized_ascii = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")
        explicit_dependency_reference = any(
            term in normalized_ascii
            for term in (
                "depende da fase",
                "depende de fase",
                "depende dos artefatos",
                "depende de artefatos",
                "dependency phase",
                "depends on phase",
                "depend on phase",
                "requires phase",
                "required phase",
                "fase anterior",
                "phase anterior",
                "previous phase",
                "fases anteriores",
                "phases anteriores",
                "previous phases",
                "evidencias anteriores",
                "previous evidence",
                "artifacts anteriores",
                "artefatos anteriores",
                "previous artifacts",
            )
        )
        if not explicit_dependency_reference:
            return []
        dependencies = [phase for phase in phase_ids if phase != current_phase_id]
        previous_match = re.search(r"phase_([0-9]+)", current_phase_id)
        has_plural_previous_reference = any(
            term in normalized_ascii
            for term in (
                "fases anteriores",
                "phases anteriores",
                "previous phases",
                "evidencias anteriores",
                "previous evidence",
                "artifacts anteriores",
                "artefatos anteriores",
                "previous artifacts",
            )
        ) or (
            "anteriores" in normalized_ascii
            and any(stem in normalized_ascii for stem in ("fase", "phase", "evid", "artifact", "artefat"))
        )
        if previous_match and has_plural_previous_reference:
            current_number = int(previous_match.group(1))
            dependencies.extend(f"phase_{number}" for number in range(1, current_number))
        elif previous_match and any(
            term in normalized_ascii
            for term in (
                "fase anterior",
                "phase anterior",
                "previous phase",
            )
        ):
            previous = int(previous_match.group(1)) - 1
            if previous > 0:
                dependencies.append(f"phase_{previous}")
        return list(dict.fromkeys(dependencies))

    def _normalize_logical_path(self, path: str) -> str:
        normalized = path.replace("\\", "/").strip().strip("\"'`.,;:")
        normalized = re.sub(r"/+", "/", normalized)
        parts = [part for part in normalized.split("/") if part not in {"", ".", ".."}]
        if len(parts) < 2:
            return ""
        return "/".join(parts)

    def _filename_for_logical_path(self, logical_path: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", logical_path.replace("\\", "/"))
        return safe[:180]

    def _content_type(self, logical_path: str) -> str:
        suffix = Path(logical_path).suffix.casefold()
        return {
            ".json": "application/json",
            ".md": "text/markdown",
            ".csv": "text/csv",
            ".html": "text/html",
            ".yaml": "application/yaml",
            ".yml": "application/yaml",
            ".zip": "application/zip",
        }.get(suffix, "text/plain")

    def _check_phase1_budget(self, run_id: str, started_monotonic: float, *, stage: str) -> None:
        run = self.runtime.store.get_run(run_id)
        if run is not None and run.cancellation_requested:
            raise GovernedPhase1Block(
                "CANCEL_CHECKPOINT_REACHED",
                f"Cancellation checkpoint reached during {stage}.",
                status="cancelled",
                details={
                    "stage": stage,
                    "cancel_requested": True,
                    "cooperative_cancel_checkpoint_seen": True,
                    "cancellation_reason": run.cancellation_reason,
                },
            )
        elapsed = time.monotonic() - started_monotonic
        if elapsed > self.budget.max_runtime_seconds:
            raise GovernedPhase1Block(
                "PHASE1_RUNTIME_BUDGET_EXCEEDED",
                f"Phase 1 runtime budget exceeded during {stage}.",
                status="blocked",
                details={
                    "stage": stage,
                    "elapsed_seconds": round(elapsed, 3),
                    "max_runtime_seconds": self.budget.max_runtime_seconds,
                    "terminal_reason": "TASKRUN_LIFECYCLE_TIMEOUT",
                },
            )

    def _check_artifact_render_checkpoint(
        self,
        run_id: str,
        phase_started_monotonic: float,
        artifact_started_monotonic: float,
        *,
        stage: str,
        logical_path: str,
        rows_rendered: int | None = None,
        rows_expected: int | None = None,
        cells_rendered: int | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        terminal = self._first_terminal_event(run_id)
        if terminal is not None:
            terminal_reason_code = (terminal.metadata or {}).get("reason_code") if isinstance(terminal.metadata, dict) else None
            self.runtime.events.create(
                run_id,
                "artifact_late_rejected",
                "rejected",
                f"Artifact render rejected after terminal event for {logical_path}.",
                metadata={
                    "logical_path": logical_path,
                    "reason_code": "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED",
                    "terminal_reason_code": terminal_reason_code,
                    "terminal_event_id": terminal.event_id,
                    "terminal_sequence": terminal.sequence,
                    "stage": stage,
                    "safe_to_use": False,
                    "rows_rendered": rows_rendered,
                    "rows_expected": rows_expected,
                    "cells_rendered": cells_rendered,
                },
            )
            raise GovernedPhase1Block(
                "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED",
                f"Artifact render rejected after terminal event for {logical_path}.",
                details={
                    "phase": "artifact_render",
                    "component": "readonly_analysis_artifact_runtime",
                    "frontier": "ARTIFACT_RENDER_TERMINALITY",
                    "stage": stage,
                    "logical_path": logical_path,
                    "terminal_event_id": terminal.event_id,
                    "terminal_reason_code": terminal_reason_code,
                    "safe_to_use": False,
                    "rows_rendered": rows_rendered,
                    "rows_expected": rows_expected,
                    "cells_rendered": cells_rendered,
                },
            )
        self._maybe_emit_artifact_render_checkpoint(
            run_id,
            stage=stage,
            logical_path=logical_path,
            rows_rendered=rows_rendered,
            rows_expected=rows_expected,
            cells_rendered=cells_rendered,
            extra_metadata=extra_metadata,
        )
        if stage in _POST_ARTIFACT_COMMIT_CHECKPOINT_STAGES:
            return
        run = self.runtime.store.get_run(run_id) if self._looks_like_task_run_id(run_id) else None
        if run is not None and run.cancellation_requested:
            raise GovernedPhase1Block(
                "ARTIFACT_RENDER_CANCELLED",
                f"Artifact render cancellation checkpoint reached during {stage}.",
                status="cancelled",
                details={
                    "phase": "artifact_render",
                    "component": "readonly_analysis_artifact_runtime",
                    "frontier": "ARTIFACT_RENDER",
                    "stage": stage,
                    "logical_path": logical_path,
                    "cancel_requested": True,
                    "cancellation_reason": run.cancellation_reason,
                    "rows_rendered": rows_rendered,
                    "rows_expected": rows_expected,
                    "cells_rendered": cells_rendered,
                },
            )
        phase_elapsed = time.monotonic() - phase_started_monotonic
        artifact_elapsed = time.monotonic() - artifact_started_monotonic
        if phase_elapsed > self.budget.max_runtime_seconds:
            raise GovernedPhase1Block(
                "PHASE1_RUNTIME_BUDGET_EXCEEDED",
                f"Phase 1 runtime budget exceeded during {stage}.",
                details={
                    "phase": "artifact_render",
                    "component": "readonly_analysis_artifact_runtime",
                    "frontier": "ARTIFACT_RENDER",
                    "stage": stage,
                    "logical_path": logical_path,
                    "elapsed_seconds": round(phase_elapsed, 3),
                    "max_runtime_seconds": self.budget.max_runtime_seconds,
                    "terminal_reason": "TASKRUN_LIFECYCLE_TIMEOUT",
                    "rows_rendered": rows_rendered,
                    "rows_expected": rows_expected,
                    "cells_rendered": cells_rendered,
                },
            )
        if artifact_elapsed > self.budget.max_artifact_render_seconds:
            reason_code = self._artifact_render_budget_reason(
                stage=stage,
                rows_rendered=rows_rendered,
                cells_rendered=cells_rendered,
            )
            raise GovernedPhase1Block(
                reason_code,
                f"Artifact render budget exceeded for {logical_path}.",
                details={
                    "phase": "artifact_render",
                    "component": "readonly_analysis_artifact_runtime",
                    "frontier": "ARTIFACT_RENDER",
                    "stage": stage,
                    "fallback_reason_code": "ARTIFACT_RENDER_TIMEOUT",
                    "logical_path": logical_path,
                    "elapsed_seconds": round(artifact_elapsed, 3),
                    "max_artifact_render_seconds": self.budget.max_artifact_render_seconds,
                    "rows_rendered": rows_rendered,
                    "rows_expected": rows_expected,
                    "cells_rendered": cells_rendered,
                },
            )

    def _artifact_render_budget_reason(
        self,
        *,
        stage: str,
        rows_rendered: int | None,
        cells_rendered: int | None,
    ) -> str:
        if stage in _CSV_RENDER_PROGRESS_STAGES and (int(rows_rendered or 0) > 0 or int(cells_rendered or 0) > 0):
            return "MUSIC_INVENTORY_CSV_STREAMING_BUDGET_EXCEEDED"
        return _MEDIA_INVENTORY_STAGE_STALL_REASONS.get(stage) or "ARTIFACT_RENDER_TIMEOUT"

    def _maybe_emit_artifact_render_checkpoint(
        self,
        run_id: str,
        *,
        stage: str,
        logical_path: str,
        rows_rendered: int | None = None,
        rows_expected: int | None = None,
        cells_rendered: int | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self._looks_like_task_run_id(run_id):
            return
        now = time.monotonic()
        key = (run_id, logical_path, stage)
        last = self._artifact_checkpoint_emitted.get(key)
        interval = max(0.0, float(self.budget.artifact_checkpoint_event_interval_ms) / 1000)
        if last is not None and now - last < interval:
            return
        self._artifact_checkpoint_emitted[key] = now
        artifact_event = self._latest_artifact_creation_started(run_id, logical_path)
        artifact_metadata = artifact_event.metadata if artifact_event is not None and isinstance(artifact_event.metadata, dict) else {}
        bounded_extra = self._bounded_checkpoint_metadata(extra_metadata)
        bounded_extra.pop("stage", None)
        bounded_extra.pop("bounded", None)
        try:
            self.runtime.events.create(
                run_id,
                "artifact_render_checkpoint",
                "running",
                f"Artifact render checkpoint reached during {stage}.",
                metadata={
                    "logical_path": logical_path,
                    "producer_step": "readonly_analysis_artifact_runtime",
                    "stage": stage,
                    "checkpoint_stage": stage,
                    "artifact_attempt_id": artifact_metadata.get("artifact_attempt_id"),
                    "created_event_source_id": getattr(artifact_event, "event_id", None),
                    "artifact_kind": artifact_metadata.get("artifact_kind"),
                    "contract_id": artifact_metadata.get("contract_id"),
                    "rows_rendered": rows_rendered,
                    "rows_expected": rows_expected,
                    "cells_rendered": cells_rendered,
                    "bounded": True,
                    **bounded_extra,
                },
            )
        except Exception:
            return

    def _bounded_checkpoint_metadata(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(metadata, dict):
            return {}
        allowed = {
            "elapsed_ms",
            "perception_compile_stage",
            "internal_reason_code",
            "estimated_payload_bytes",
            "materialized_payload_bytes",
            "payload_ref_count",
            "observation_execution_result_count",
            "relationship_candidate_count",
            "observations_in",
            "relationships_in",
            "candidate_fact_count",
            "observed_fact_count",
            "derived_fact_count",
            "projected_fact_count",
            "deduplicated_fact_count",
            "facts_with_evidence_count",
            "facts_with_provenance_count",
            "truth_eligible_count",
            "fact_provenance_issue_count",
            "fact_projection_elapsed_ms",
            "entity_count",
            "source_entity_processed_count",
            "observation_requirement_count",
            "observation_record_count",
            "attribute_observation_count",
            "attribute_observation_attempt_count",
            "evidence_ref_count",
            "unique_evidence_ref_count",
            "duplicate_evidence_ref_avoided_count",
            "evidence_set_count",
            "evidence_record_referenced_count",
            "evidence_record_copied_count",
            "evidence_record_materialized_count",
            "provenance_ref_count",
            "missing_observation_count",
            "unsupported_observation_count",
            "failed_observation_count",
            "observed_null_count",
            "materialized_bytes_estimate",
            "source_index_entry_count",
            "capability_decision_count",
            "capability_index_entry_count",
            "artifact_id",
            "payload_kind",
            "payload_bytes",
            "serialized_bytes",
            "artifact_content_bytes",
            "bytes_written",
            "write_elapsed_ms",
            "manifest_bytes",
            "manifest_inline_bytes",
            "payload_ref_bytes",
            "payload_ref_dedup_hit_count",
            "serialization_count",
            "copy_count_estimate",
            "checksum",
            "storage_ref_present",
            "payload_ref_decision",
            "source_input_entity_count",
            "selected_entity_count",
            "projected_entity_count",
            "row_model_candidate_count",
            "row_model_accepted_count",
            "row_model_rejected_count",
            "row_model_skipped_count",
            "csv_rows_expected_at_stream_start",
            "csv_rows_attempted",
            "csv_rows_rendered",
            "csv_rows_written",
            "csv_rows_failed",
            "csv_cells_expected",
            "csv_cells_attempted",
            "csv_cells_rendered",
            "csv_cells_written",
            "row_model_build_elapsed_ms",
            "row_order_elapsed_ms",
            "csv_stream_elapsed_ms",
            "csv_row_render_elapsed_ms",
            "csv_cell_render_elapsed_ms",
            "csv_cell_serialization_elapsed_ms",
            "csv_serialization_elapsed_ms",
            "csv_finalize_elapsed_ms",
            "rows_per_second",
            "cells_per_second",
            "average_cell_us",
            "max_batch_elapsed_ms",
            "input_entity_set_digest",
            "projected_entity_set_digest",
            "row_model_digest",
            "column_schema_digest",
            "render_order_digest",
            "cardinality_domain",
            "progress_semantics",
        }
        bounded: dict[str, Any] = {}
        for key in allowed:
            value = metadata.get(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                bounded[key] = value
        payload_metrics = metadata.get("payload_metrics")
        if isinstance(payload_metrics, dict):
            bounded["payload_metrics"] = self._bounded_perception_payload_metrics(payload_metrics)
        return bounded

    def _bounded_perception_payload_metrics(self, metrics: Any) -> dict[str, Any]:
        if not isinstance(metrics, dict):
            return {}
        allowed = {
            "input_entity_count",
            "projected_entity_count",
            "payload_item_count",
            "estimated_payload_bytes",
            "materialized_payload_bytes",
            "payload_ref_count",
            "bound_status",
            "reason_code",
            "observation_execution_result_count",
            "relationship_candidate_count",
            "observations_in",
            "relationships_in",
            "candidate_fact_count",
            "observed_fact_count",
            "derived_fact_count",
            "projected_fact_count",
            "deduplicated_fact_count",
            "facts_with_evidence_count",
            "facts_with_provenance_count",
            "truth_eligible_count",
            "fact_provenance_issue_count",
            "fact_projection_elapsed_ms",
            "entity_count",
            "source_entity_processed_count",
            "observation_requirement_count",
            "observation_record_count",
            "attribute_observation_count",
            "attribute_observation_attempt_count",
            "evidence_ref_count",
            "unique_evidence_ref_count",
            "duplicate_evidence_ref_avoided_count",
            "evidence_set_count",
            "evidence_record_referenced_count",
            "evidence_record_copied_count",
            "evidence_record_materialized_count",
            "provenance_ref_count",
            "missing_observation_count",
            "unsupported_observation_count",
            "failed_observation_count",
            "observed_null_count",
            "materialized_bytes_estimate",
            "source_index_entry_count",
            "capability_decision_count",
            "capability_index_entry_count",
        }
        return {
            key: value
            for key, value in metrics.items()
            if key in allowed and (isinstance(value, (str, int, float, bool)) or value is None)
        }

    def _artifact_persist_checkpoint_metrics(
        self,
        metrics: dict[str, Any] | None,
        *,
        render_result: ArtifactRenderResult,
        semantic_decision: dict[str, Any],
    ) -> dict[str, Any]:
        payload = dict(metrics or {})
        content_bytes = len((render_result.content or "").encode("utf-8"))
        payload.setdefault("artifact_content_bytes", content_bytes)
        payload.setdefault("payload_bytes", content_bytes)
        payload.setdefault("payload_ref_count", 0)
        payload.setdefault("copy_count_estimate", 1)
        payload.setdefault("payload_ref_decision", "INLINE")
        if int(payload.get("payload_ref_count") or 0) > 0:
            payload["payload_ref_decision"] = "PAYLOAD_REF"
        payload.setdefault("bound_status", str(semantic_decision.get("semantic_contract_status") or "unknown"))
        return payload

    def _int_or_none(self, value: Any) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _stable_digest(self, values: list[Any] | tuple[Any, ...]) -> str:
        encoded = json.dumps([str(item) for item in values], ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _latest_artifact_creation_started(self, run_id: str, logical_path: str):
        if not self._looks_like_task_run_id(run_id) or not logical_path:
            return None
        for event in sorted(self.runtime.store.get_events(run_id), key=lambda item: item.sequence, reverse=True):
            metadata = event.metadata if isinstance(event.metadata, dict) else {}
            if event.type == "artifact_creation_started" and str(metadata.get("logical_path") or "") == logical_path:
                return event
        return None

    def _terminal_event_types(self) -> set[str]:
        return {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}

    def _looks_like_task_run_id(self, run_id: str) -> bool:
        return bool(re.fullmatch(r"task_run_[a-f0-9]+", str(run_id or "")))

    def _first_terminal_event(self, run_id: str):
        if not self._looks_like_task_run_id(run_id):
            return None
        for event in sorted(self.runtime.store.get_events(run_id), key=lambda item: item.sequence):
            if event.type in self._terminal_event_types():
                return event
        return None

    def _emit_terminal_event(
        self,
        run_id: str,
        event_type: str,
        status: str,
        message: str,
        *,
        metadata: dict[str, Any] | None = None,
    ):
        existing = self._first_terminal_event(run_id)
        if existing is not None:
            return self.runtime.events.create(
                run_id,
                "terminalization_already_applied",
                "ignored",
                "Terminalization ignored because the TaskRun already has a terminal event.",
                metadata={
                    "terminal_event_id": existing.event_id,
                    "terminal_status": existing.status,
                    "terminal_reason_code": (existing.metadata or {}).get("reason_code"),
                    "attempted_event_type": event_type,
                    "attempted_status": status,
                    "attempted_reason_code": (metadata or {}).get("reason_code"),
                    "ignored": True,
                    "reason": "terminal_state_already_set",
                },
            )
        return self.runtime.events.create(run_id, event_type, status, message, metadata=metadata)

    def _reject_late_artifact_if_terminal(self, run_id: str, *, logical_path: str, artifact_event_id: str) -> None:
        terminal = self._first_terminal_event(run_id)
        if terminal is None:
            return
        terminal_reason_code = (terminal.metadata or {}).get("reason_code") if isinstance(terminal.metadata, dict) else None
        self.runtime.events.create(
            run_id,
            "artifact_late_rejected",
            "rejected",
            f"Artifact rejected after terminal event for {logical_path}.",
            metadata={
                "logical_path": logical_path,
                "reason_code": "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED",
                "terminal_reason_code": terminal_reason_code,
                "terminal_event_id": terminal.event_id,
                "created_event_source_id": artifact_event_id,
                "safe_to_use": False,
            },
        )
        raise GovernedPhase1Block(
            "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED",
            f"Artifact rejected after terminal event for {logical_path}.",
            details={
                "phase": "artifact_render",
                "component": "readonly_analysis_artifact_runtime",
                "frontier": "ARTIFACT_RENDER_TERMINALITY",
                "stage": "after_registry_create_before_event",
                "logical_path": logical_path,
                "terminal_event_id": terminal.event_id,
                "terminal_reason_code": terminal_reason_code,
                "safe_to_use": False,
            },
        )

    def _emit_project_analysis_boundary_events(self, run_id: str, analysis_result) -> None:
        metadata = {
            "analysis_result_id": analysis_result.result_id,
            "analysis_status": analysis_result.status,
            "reason_code": analysis_result.reason_code,
            "duration_ms": analysis_result.duration_ms,
            "last_checkpoint": analysis_result.last_checkpoint,
            "last_completed_checkpoint": analysis_result.last_completed_checkpoint,
            "elapsed_ms_by_checkpoint": analysis_result.elapsed_ms_by_checkpoint,
            "files_discovered": analysis_result.files_discovered,
            "files_scan_attempted": analysis_result.files_scan_attempted,
            "files_scanned": analysis_result.files_scanned,
            "files_read": analysis_result.files_read,
            "bytes_read": analysis_result.bytes_read,
            "current_root": analysis_result.current_root,
            "current_path_sample": analysis_result.current_path_sample,
            "blocking_operation": analysis_result.blocking_operation,
            "budget_exceeded_at": analysis_result.budget_exceeded_at,
            "safe_to_continue": analysis_result.safe_to_continue,
            "budget_exceeded": analysis_result.budget_exceeded,
            "error_type": analysis_result.error_type,
            "error_message": analysis_result.error_message,
            "files_selected": analysis_result.files_selected,
            "remaining_budget_ms_at_return": analysis_result.remaining_budget_ms_at_return,
            "handoff_reserve_reached": analysis_result.handoff_reserve_reached,
            "partial_readiness": analysis_result.partial_readiness,
            "file_selection_plan": self._compact_project_analysis_plan(analysis_result.file_selection_plan),
            "file_read_plan": self._compact_project_analysis_plan(analysis_result.file_read_plan),
        }
        if analysis_result.status in {"ok", "partial", "degraded"} and analysis_result.safe_to_continue:
            if analysis_result.status == "partial":
                if analysis_result.handoff_reserve_reached:
                    self.runtime.events.create(
                        run_id,
                        "project_analysis_handoff_reserve_reached",
                        "partial",
                        "Project analysis stopped before exhausting budget to preserve handoff reserve.",
                        metadata=metadata,
                    )
                self.runtime.events.create(
                    run_id,
                    "project_analysis_partial",
                    "partial",
                    "Project analysis returned a governed partial result safe for artifact runtime handoff.",
                    metadata=metadata,
                )
            return
        self.runtime.events.create(
            run_id,
            "project_analysis_blocked",
            str(analysis_result.status),
            analysis_result.error_message or analysis_result.reason_code or "Project analysis blocked before artifact runtime.",
            metadata=metadata,
        )
        event_type = {
            "cancelled": "project_analysis_cancelled",
            "timeout": "project_analysis_budget_exceeded",
            "failed": "project_analysis_failed",
        }.get(str(analysis_result.status), "project_analysis_partial_result" if analysis_result.partial else "project_analysis_failed")
        self.runtime.events.create(
            run_id,
            event_type,
            str(analysis_result.status),
            analysis_result.error_message or analysis_result.reason_code or "Project analysis stopped at governed boundary.",
            metadata=metadata,
        )

    def _terminal_artifact_summaries(self, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self._terminal_artifact_summary(item) for item in artifacts if isinstance(item, dict)]

    def _terminal_artifact_summary(self, artifact: dict[str, Any]) -> dict[str, Any]:
        metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
        schema_coverage = artifact.get("schema_coverage") if isinstance(artifact.get("schema_coverage"), dict) else metadata.get("schema_coverage")
        if not isinstance(schema_coverage, dict):
            schema_coverage = {}
        inventory_sufficiency = artifact.get("inventory_sufficiency_summary") or metadata.get("inventory_sufficiency_summary")
        if not isinstance(inventory_sufficiency, dict):
            inventory_sufficiency = schema_coverage.get("inventory_sufficiency_summary") if isinstance(schema_coverage.get("inventory_sufficiency_summary"), dict) else {}
        row_evidence = artifact.get("row_evidence_coverage") or metadata.get("row_evidence_coverage")
        if not isinstance(row_evidence, dict):
            row_evidence = {}
        evidence_refs = artifact.get("evidence_refs") or metadata.get("evidence_refs") or []
        return {
            "artifact_id": artifact.get("artifact_id"),
            "logical_path": artifact.get("logical_path") or metadata.get("logical_path"),
            "task_id": artifact.get("task_id") or metadata.get("task_id"),
            "task_run_id": artifact.get("task_run_id") or metadata.get("task_run_id"),
            "operation_id": artifact.get("operation_id") or metadata.get("operation_id"),
            "storage_ref": artifact.get("storage_ref") or artifact.get("storage_path") or metadata.get("storage_ref"),
            "content_type": artifact.get("content_type") or metadata.get("content_type"),
            "artifact_type": artifact.get("artifact_type") or metadata.get("artifact_type"),
            "producer_step": artifact.get("producer_step") or metadata.get("producer_step"),
            "status": artifact.get("status") or metadata.get("status"),
            "validation_status": artifact.get("validation_status") or metadata.get("validation_status"),
            "reason_code": artifact.get("reason_code") or metadata.get("reason_code"),
            "semantic_contract_status": artifact.get("semantic_contract_status") or metadata.get("semantic_contract_status"),
            "safe_to_use": artifact.get("safe_to_use") if "safe_to_use" in artifact else metadata.get("safe_to_use"),
            "limitations": list(artifact.get("limitations") or metadata.get("limitations") or [])[:20],
            "partial_rows": artifact.get("partial_rows") or metadata.get("partial_rows"),
            "expected_rows": artifact.get("expected_rows") or metadata.get("expected_rows"),
            "selected_rows": artifact.get("selected_rows") or metadata.get("selected_rows"),
            "bound_rows": artifact.get("bound_rows") or metadata.get("bound_rows"),
            "evidence_ref_count": artifact.get("evidence_ref_count") or metadata.get("evidence_ref_count"),
            "evidence_refs": [str(ref) for ref in evidence_refs if ref][:20],
            "row_evidence_coverage": row_evidence,
            "schema_coverage": {
                key: value
                for key, value in schema_coverage.items()
                if key
                in {
                    "status",
                    "missing_columns",
                    "extra_columns",
                    "rendered_columns_count",
                    "declared_columns_count",
                    "metadata_coverage_summary",
                    "inventory_sufficiency_summary",
                }
            },
            "metadata_coverage_summary": artifact.get("metadata_coverage_summary")
            or metadata.get("metadata_coverage_summary")
            or schema_coverage.get("metadata_coverage_summary")
            or {},
            "inventory_sufficiency_summary": inventory_sufficiency,
            "size_bytes": artifact.get("size_bytes") or metadata.get("size_bytes"),
            "sha256": artifact.get("sha256") or metadata.get("sha256"),
            "source": artifact.get("source") or "artifact_summary",
        }

    def _artifact_state(self, created_artifacts: list[dict[str, Any]], validation: dict[str, Any]) -> dict[str, Any]:
        if created_artifacts:
            unsafe = [
                item
                for item in created_artifacts
                if str(item.get("status") or "") in {"partial", "blocked", "interrupted", "failed", "rejected", "late_rejected"}
                or item.get("safe_to_use") is False
            ]
            return {
                "status": "partial" if unsafe else "available",
                "count": len(created_artifacts),
                "artifact_ids": [str(item.get("artifact_id")) for item in created_artifacts if item.get("artifact_id")],
                "safe_to_use": not bool(unsafe),
                "partial_or_interrupted": unsafe,
            }
        reason_code = str(validation.get("reason_code") or "")
        if str(validation.get("phase") or "") == "project_analysis":
            return {
                "status": "blocked_before_artifact_creation",
                "reason_code": reason_code or "PROJECT_ANALYSIS_BOUNDARY_ERROR",
                "count": 0,
            }
        return {"status": "none", "reason_code": reason_code or "NO_ARTIFACTS_CREATED", "count": 0}

    def _has_artifact_for_logical_path(self, artifacts: list[dict[str, Any]], logical_path: str) -> bool:
        return any(
            str((item.get("metadata") or {}).get("logical_path") or item.get("logical_path") or "") == logical_path
            for item in artifacts
            if isinstance(item, dict)
        )

    def _interrupted_artifact_row(self, task_run_id: str, details: dict[str, Any]) -> dict[str, Any] | None:
        logical_path = str(details.get("logical_path") or "")
        phase = str(details.get("phase") or "")
        reason_code = str(details.get("reason_code") or details.get("terminal_reason") or "")
        if not logical_path or phase != "artifact_render":
            return None
        if str(details.get("frontier") or "") == "ARTIFACT_RENDER_TERMINALITY":
            status = "rejected"
            terminal_reason_code = str(details.get("terminal_reason_code") or "")
            reason_code = terminal_reason_code or "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED"
        else:
            status = "interrupted"
            reason_code = reason_code or "ARTIFACT_RENDER_INTERRUPTED"
        return {
            "artifact_id": None,
            "logical_path": logical_path,
            "task_run_id": task_run_id,
            "status": status,
            "reason_code": reason_code,
            "storage_ref": None,
            "partial_rows": details.get("rows_rendered"),
            "expected_rows": details.get("rows_expected"),
            "rendered_columns": details.get("rendered_columns") or [],
            "missing_columns": details.get("missing_columns") or [],
            "safe_to_use": False,
            "visible_in_endpoint": True,
            "source": "readonly_analysis_artifact_runtime",
        }

    def _transition(self, run, target: str) -> None:
        try:
            self.lifecycle.transition(run, target)
        except ValueError:
            if self.lifecycle.is_terminal(str(run.status)):
                return
            run.status = target
