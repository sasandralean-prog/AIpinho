from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.analysis.file_selection import FileSelectionCandidate
from aipinho.schemas.common.base import AIpinhoModel


@dataclass(frozen=True)
class ProjectAnalysisBudgetCooperationPolicy:
    max_total_seconds: float = 300.0
    max_selection_seconds: float = 60.0
    max_file_read_seconds: float = 120.0
    max_single_file_read_ms: int = 3_000
    max_files_scanned: int = 500
    max_files_selected: int = 12
    max_files_read: int = 12
    max_bytes_read: int = 120_000
    min_remaining_ms_for_handoff: int = 1_500
    min_remaining_ms_for_result_serialization: int = 750
    allow_partial_result: bool = True
    allow_partial_handoff: bool = True
    required_minimum_summary: bool = True

    @classmethod
    def from_environment(
        cls,
        *,
        max_total_seconds: float,
        max_files_scanned: int,
        max_files_read: int,
        max_bytes_read: int,
        allow_partial_result: bool,
    ) -> "ProjectAnalysisBudgetCooperationPolicy":
        def _float(name: str, default: float) -> float:
            try:
                return float(os.environ.get(name, default))
            except Exception:
                return default

        def _int(name: str, default: int) -> int:
            try:
                return int(os.environ.get(name, default))
            except Exception:
                return default

        def _bool(name: str, default: bool) -> bool:
            value = os.environ.get(name)
            if value is None:
                return default
            return str(value).casefold() in {"1", "true", "yes", "sim", "on"}

        reserve_seconds = max(1.0, max_total_seconds * 0.075)
        selection_default = max(0.5, min(max_total_seconds * 0.65, max_total_seconds - reserve_seconds))
        read_default = max(0.5, max_total_seconds * 0.45)
        return cls(
            max_total_seconds=max_total_seconds,
            max_selection_seconds=_float("AIPINHO_PROJECT_ANALYSIS_MAX_SELECTION_SECONDS", selection_default),
            max_file_read_seconds=_float("AIPINHO_PROJECT_ANALYSIS_MAX_FILE_READ_SECONDS", read_default),
            max_single_file_read_ms=_int("AIPINHO_PROJECT_ANALYSIS_MAX_SINGLE_FILE_READ_MS", 3_000),
            max_files_scanned=max_files_scanned,
            max_files_selected=_int("AIPINHO_PROJECT_ANALYSIS_MAX_FILES_SELECTED", max_files_read),
            max_files_read=max_files_read,
            max_bytes_read=max_bytes_read,
            min_remaining_ms_for_handoff=_int("AIPINHO_PROJECT_ANALYSIS_MIN_REMAINING_MS_FOR_HANDOFF", 1_500),
            min_remaining_ms_for_result_serialization=_int(
                "AIPINHO_PROJECT_ANALYSIS_MIN_REMAINING_MS_FOR_SERIALIZATION",
                750,
            ),
            allow_partial_result=allow_partial_result,
            allow_partial_handoff=_bool("AIPINHO_PROJECT_ANALYSIS_ALLOW_PARTIAL_HANDOFF", True),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_total_seconds": self.max_total_seconds,
            "max_selection_seconds": self.max_selection_seconds,
            "max_file_read_seconds": self.max_file_read_seconds,
            "max_single_file_read_ms": self.max_single_file_read_ms,
            "max_files_scanned": self.max_files_scanned,
            "max_files_selected": self.max_files_selected,
            "max_files_read": self.max_files_read,
            "max_bytes_read": self.max_bytes_read,
            "min_remaining_ms_for_handoff": self.min_remaining_ms_for_handoff,
            "min_remaining_ms_for_result_serialization": self.min_remaining_ms_for_result_serialization,
            "allow_partial_result": self.allow_partial_result,
            "allow_partial_handoff": self.allow_partial_handoff,
            "required_minimum_summary": self.required_minimum_summary,
        }


class FileSelectionPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: f"file_selection_plan_{uuid4().hex}")
    workspace_root: str
    candidate_count: int = 0
    selected_count: int = 0
    selection_strategy: str = "cheap_path_metadata_ranking"
    selection_budget_ms: int | None = None
    selection_started_at: str | None = None
    selection_finished_at: str | None = None
    elapsed_ms: int = 0
    selected_files: list[FileSelectionCandidate] = Field(default_factory=list)
    rejected_files_summary: dict[str, int] = Field(default_factory=dict)
    selection_reason_codes: list[str] = Field(default_factory=list)
    root_role: str | None = None
    source_reading_policy_applied: bool = True
    inventory_selection_policy_applied: bool = False
    source_readable_selected_count: int = 0
    inventory_eligible_entities_count: int = 0
    media_entity_candidates_count: int = 0
    source_rejected_inventory_eligible_count: int = 0
    inventory_eligible_sample: list[dict[str, Any]] = Field(default_factory=list)
    budget_exceeded: bool = False
    partial: bool = False


class FileReadPlan(AIpinhoModel):
    plan_id: str = Field(default_factory=lambda: f"file_read_plan_{uuid4().hex}")
    selected_files: list[str] = Field(default_factory=list)
    read_order: list[str] = Field(default_factory=list)
    max_files_read: int = 0
    max_bytes_read: int = 0
    max_single_file_read_ms: int | None = None
    read_started_at: str | None = None
    read_finished_at: str | None = None
    files_read: int = 0
    files_partial_read: int = 0
    files_skipped: int = 0
    bytes_read: int = 0
    bytes_skipped_estimated: int = 0
    read_decisions: list[dict[str, Any]] = Field(default_factory=list)
    skipped_files: list[dict[str, Any]] = Field(default_factory=list)
    read_errors: list[dict[str, Any]] = Field(default_factory=list)
    budget_exceeded: bool = False
    partial: bool = False


class ProjectAnalysisPartialReadiness(AIpinhoModel):
    safe_to_continue_to_artifact_runtime: bool = False
    minimum_context_available: bool = False
    workspace_root_resolved: bool = False
    tree_summary_available: bool = False
    file_selection_available: bool = False
    file_context_available: bool = False
    contract_context_available: bool = True
    known_limitations: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    confidence: float = 0.0
