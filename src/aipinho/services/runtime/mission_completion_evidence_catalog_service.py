from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionEvidenceCatalog,
    MissionCompletionEvidenceItem,
    MissionCompletionSnapshot,
)
from aipinho.services.runtime.phase_outcome_repository import PhaseOutcomeRepository


class MissionCompletionEvidenceCatalogService:
    """Project canonical mission evidence into a stable semantic catalog.

    The catalog is descriptive only. It carries no requirement satisfaction
    claim and cannot promote mission truth.
    """

    def __init__(
        self,
        *,
        outcomes: PhaseOutcomeRepository,
    ) -> None:
        self.outcomes = outcomes

    def build(
        self,
        snapshot: MissionCompletionSnapshot,
        *,
        limit: int = 1000,
    ) -> MissionCompletionEvidenceCatalog:
        outcome_rows = self.outcomes.list_for_mission(
            mission_id=snapshot.mission_id,
            limit=limit,
        )
        allowed_runs = set(snapshot.task_run_ids)
        allowed_outcome_hashes = set(
            snapshot.phase_outcome_authority_sha256s
        )
        items: list[MissionCompletionEvidenceItem] = []
        seen: set[tuple[str, str]] = set()

        for outcome in outcome_rows:
            if outcome.producer_task_run_id not in allowed_runs:
                continue
            if (
                allowed_outcome_hashes
                and outcome.authority_sha256 not in allowed_outcome_hashes
            ):
                continue
            descriptors = self._artifact_descriptors(outcome.artifacts)
            for ref in outcome.evidence_refs:
                key = (str(ref), outcome.producer_task_run_id)
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    MissionCompletionEvidenceItem(
                        evidence_ref=str(ref),
                        producer_task_run_id=outcome.producer_task_run_id,
                        phase_id=outcome.phase_id,
                        phase_outcome_authority_sha256=(
                            outcome.authority_sha256
                        ),
                        runtime_status=outcome.runtime_status,
                        result_status=outcome.result_status,
                        runtime_truth_status=(
                            outcome.semantic_properties.get(
                                "runtime_truth_status"
                            )
                        ),
                        runtime_truth_safe_to_report_success=(
                            outcome.semantic_properties.get(
                                "runtime_truth_safe_to_report_success"
                            )
                        ),
                        phase_dependency_status=(
                            outcome.phase_dependency.get("status")
                            if isinstance(outcome.phase_dependency, dict)
                            else None
                        ),
                        reason_code=outcome.reason_code,
                        limitations=list(outcome.limitations),
                        missing_truth=list(outcome.missing_truth),
                        use_safety=dict(outcome.use_safety),
                        semantic_properties=dict(
                            outcome.semantic_properties
                        ),
                        artifact_descriptors=descriptors,
                    )
                )

        items = sorted(
            items,
            key=lambda item: (
                item.producer_task_run_id,
                item.phase_id,
                item.evidence_ref,
            ),
        )
        payload: dict[str, Any] = {
            "mission_id": snapshot.mission_id,
            "snapshot_authority_sha256": snapshot.authority_sha256,
            "items": [
                item.model_dump(mode="json") for item in items
            ],
        }
        authority_sha256 = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return MissionCompletionEvidenceCatalog(
            **payload,
            authority_sha256=authority_sha256,
        )

    def _artifact_descriptors(
        self,
        artifacts: list[dict[str, Any]],
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for artifact in artifacts:
            metadata = (
                artifact.get("metadata")
                if isinstance(artifact.get("metadata"), dict)
                else {}
            )
            row = {
                "artifact_id": artifact.get("artifact_id"),
                "logical_path": (
                    artifact.get("logical_path")
                    or metadata.get("logical_path")
                ),
                "status": artifact.get("status"),
                "validation_status": artifact.get(
                    "validation_status"
                ),
                "producer_step": (
                    artifact.get("producer_step")
                    or metadata.get("producer_step")
                ),
                "evidence_refs": [
                    str(ref)
                    for ref in artifact.get("evidence_refs") or []
                    if ref
                ],
            }
            rows.append(
                {
                    key: value
                    for key, value in row.items()
                    if value not in (None, "", [], {})
                }
            )
        return rows
