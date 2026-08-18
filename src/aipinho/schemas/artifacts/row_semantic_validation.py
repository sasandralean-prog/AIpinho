from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class SemanticColumnCoverage(AIpinhoModel):
    declared_columns: list[str] = Field(default_factory=list)
    rendered_columns: list[str] = Field(default_factory=list)
    missing_columns: list[str] = Field(default_factory=list)
    extra_columns: list[str] = Field(default_factory=list)
    status: str = "unknown"


class RowEvidenceCoverage(AIpinhoModel):
    total_rows: int = 0
    rows_with_evidence_ref: int = 0
    rows_without_evidence_ref: int = 0
    evidence_ref_count: int = 0
    evidence_refs_sample: list[str] = Field(default_factory=list)
    status: str = "not_available"
    reason_code: str | None = None


class ArtifactRowValidationSummary(AIpinhoModel):
    status: str
    row_count: int = 0
    column_coverage: SemanticColumnCoverage = Field(default_factory=SemanticColumnCoverage)
    row_evidence_coverage: RowEvidenceCoverage = Field(default_factory=RowEvidenceCoverage)
    rows_with_required_identity: int = 0
    rows_missing_required_identity: int = 0
    value_counts_by_column: dict[str, int] = Field(default_factory=dict)
    absence_counts_by_column: dict[str, dict[str, int]] = Field(default_factory=dict)
    missing_required_row_values: dict[str, int] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    truth_eligible: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
