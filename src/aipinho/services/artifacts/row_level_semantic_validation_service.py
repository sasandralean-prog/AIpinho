from __future__ import annotations

import csv
import io
import re
from typing import Any

from aipinho.schemas.artifacts.row_semantic_validation import (
    ArtifactRowValidationSummary,
    RowEvidenceCoverage,
    SemanticColumnCoverage,
)


class RowLevelSemanticValidationService:
    """Builds lightweight row/column/evidence coverage for rendered artifacts.

    The service validates already-rendered content and already-governed row
    bindings. It does not inspect the filesystem and does not produce Truth.
    """

    ABSENCE_VALUES = {
        "",
        "unknown",
        "not_observed",
        "not_configured",
        "unsupported",
        "blocked",
    }

    IDENTITY_FIELDS = {"entity_id", "relative_path", "filename", "name"}
    COLUMN_ALIASES = {
        "name": {"filename"},
        "filename": {"name"},
        "size_bytes": {"size", "tamanho"},
        "channels": {"canais"},
        "observations": {"observa_es", "observacoes"},
        "duration": {"duration_ms", "duracao"},
        "duration_ms": {"duration", "duracao"},
        "bitrate": {"bitrate_bps"},
        "bitrate_bps": {"bitrate"},
        "sample_rate": {"sample_rate_hz", "taxa_amostragem"},
        "sample_rate_hz": {"sample_rate", "taxa_amostragem"},
        "artwork": {"artwork_present", "capa"},
        "artwork_present": {"artwork", "capa"},
    }

    def summarize_csv(
        self,
        *,
        content: str,
        declared_columns: list[str],
        required_columns: list[str] | None = None,
        row_bindings: list[dict[str, Any]] | None = None,
        evidence_ref_column: str = "evidence_ref",
    ) -> ArtifactRowValidationSummary:
        rendered_columns, rows = self._read_csv(content)
        declared = [self._canonical(item) for item in declared_columns if str(item or "").strip()]
        rendered = [self._canonical(item) for item in rendered_columns if str(item or "").strip()]
        required = [self._canonical(item) for item in (required_columns or declared) if str(item or "").strip()]
        rendered_set = set(rendered)
        declared_set = set(declared)
        missing_columns = [item for item in required if not self._column_available(item, rendered_set)]
        extra_columns = [item for item in rendered if declared and not self._column_available(item, declared_set)]
        column_status = "satisfied" if not missing_columns else "missing_columns"

        value_counts: dict[str, int] = {}
        absence_counts: dict[str, dict[str, int]] = {}
        missing_required_values: dict[str, int] = {}
        rows_with_identity = 0
        rows_missing_identity = 0
        evidence_refs: list[str] = []
        evidence_key = self._canonical(evidence_ref_column)
        identity_keys = self.IDENTITY_FIELDS.intersection(set(rendered))
        for row in rows:
            canonical_row = {self._canonical(key): "" if value is None else str(value) for key, value in row.items()}
            if any(canonical_row.get(key, "").strip() for key in identity_keys):
                rows_with_identity += 1
            else:
                rows_missing_identity += 1
            for column in rendered:
                normalized_value = self._absence_key(canonical_row.get(column, ""))
                if normalized_value is None:
                    value_counts[column] = value_counts.get(column, 0) + 1
                else:
                    bucket = absence_counts.setdefault(column, {})
                    bucket[normalized_value] = bucket.get(normalized_value, 0) + 1
            for column in required:
                value = self._row_value_for_column(canonical_row, column)
                if value is not None and self._absence_key(value) is not None:
                    missing_required_values[column] = missing_required_values.get(column, 0) + 1
            for ref in self._split_refs(canonical_row.get(evidence_key, "")):
                if ref and ref not in evidence_refs:
                    evidence_refs.append(ref)

        for binding in row_bindings or []:
            if not isinstance(binding, dict):
                continue
            for ref in binding.get("evidence_refs") or []:
                text = str(ref or "")
                if text and text not in evidence_refs:
                    evidence_refs.append(text)

        rows_with_evidence = sum(1 for row in rows if self._split_refs(row.get(evidence_ref_column, "")))
        if row_bindings:
            rows_with_evidence = max(
                rows_with_evidence,
                len([row for row in row_bindings if isinstance(row, dict) and row.get("evidence_refs")]),
            )
        evidence_status = "satisfied" if rows and rows_with_evidence >= len(rows) else "partial" if rows_with_evidence else "missing"
        reason_codes: list[str] = []
        limitations: list[str] = []
        if missing_columns:
            reason_codes.append("ARTIFACT_RENDERED_COLUMNS_MISSING")
        if rows and evidence_status != "satisfied":
            reason_codes.append("ARTIFACT_ROW_EVIDENCE_PARTIAL")
            limitations.append("row_evidence_refs_not_complete")
        if not rows:
            reason_codes.append("ARTIFACT_ROWS_MISSING")
        if missing_required_values:
            reason_codes.append("ARTIFACT_REQUIRED_ROW_VALUES_PARTIAL")
            limitations.append("row_values_include_unknown_or_unavailable_states")
        status = "satisfied" if not reason_codes else "partial" if rows and not missing_columns else "blocked"
        return ArtifactRowValidationSummary(
            status=status,
            row_count=len(rows),
            column_coverage=SemanticColumnCoverage(
                declared_columns=declared,
                rendered_columns=rendered,
                missing_columns=missing_columns,
                extra_columns=extra_columns,
                status=column_status,
            ),
            row_evidence_coverage=RowEvidenceCoverage(
                total_rows=len(rows),
                rows_with_evidence_ref=rows_with_evidence,
                rows_without_evidence_ref=max(0, len(rows) - rows_with_evidence),
                evidence_ref_count=len(evidence_refs),
                evidence_refs_sample=evidence_refs[:20],
                status=evidence_status,
                reason_code=None if evidence_status == "satisfied" else "ARTIFACT_EVIDENCE_BINDING_MISSING",
            ),
            rows_with_required_identity=rows_with_identity,
            rows_missing_required_identity=rows_missing_identity,
            value_counts_by_column=value_counts,
            absence_counts_by_column=absence_counts,
            missing_required_row_values=missing_required_values,
            reason_codes=list(dict.fromkeys(reason_codes)),
            limitations=list(dict.fromkeys(limitations)),
            truth_eligible=False,
            metadata={
                "source": "row_level_semantic_validation",
                "filesystem_observed": False,
                "renderer_observer": False,
            },
        )

    def _read_csv(self, content: str) -> tuple[list[str], list[dict[str, str]]]:
        try:
            sample = content[:4096]
            dialect = csv.Sniffer().sniff(sample) if sample.strip() else csv.excel
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(content), dialect=dialect)
        return [str(item or "") for item in (reader.fieldnames or [])], [
            {str(key or ""): "" if value is None else str(value) for key, value in row.items()}
            for row in reader
            if isinstance(row, dict)
        ]

    def _canonical(self, value: Any) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        normalized = text.strip("_")
        for canonical, aliases in self.COLUMN_ALIASES.items():
            if normalized == canonical or normalized in aliases:
                return canonical
        return normalized

    def _absence_key(self, value: Any) -> str | None:
        normalized = str(value or "").strip().lower()
        return normalized if normalized in self.ABSENCE_VALUES else None

    def _column_available(self, column: str, available: set[str]) -> bool:
        return column in available or bool(self.COLUMN_ALIASES.get(column, set()).intersection(available))

    def _row_value_for_column(self, row: dict[str, str], column: str) -> str | None:
        if column in row:
            return row.get(column)
        for alias in self.COLUMN_ALIASES.get(column, set()):
            if alias in row:
                return row.get(alias)
        return None

    def _split_refs(self, value: Any) -> list[str]:
        return [part.strip() for part in str(value or "").split(";") if part.strip()]
