from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionBindingCandidate,
    MissionCompletionBindingProposal,
    MissionCompletionEvidenceCatalog,
    MissionCompletionSnapshot,
)
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)
from aipinho.utils.yaml_loader import load_yaml_file


class MissionCompletionBindingProposalService:
    """Produce non-authoritative semantic requirement/evidence bindings."""

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
    ) -> None:
        self.reasoner = reasoner or ContractBoundSemanticReasoner()
        config_path = (
            PATHS.config_root
            / "runtime"
            / "mission_completion_binding_policy.yaml"
        )
        self.policy = load_yaml_file(
            config_path,
            critical=True,
            root=config_path.parent,
        )

    def propose(
        self,
        snapshot: MissionCompletionSnapshot,
        catalog: MissionCompletionEvidenceCatalog,
    ) -> MissionCompletionBindingProposal:
        if snapshot.status != "ready":
            return self._proposal(
                snapshot,
                catalog,
                status="invalid",
                reason_code="MISSION_COMPLETION_SNAPSHOT_NOT_READY",
            )
        if (
            catalog.mission_id != snapshot.mission_id
            or catalog.snapshot_authority_sha256
            != snapshot.authority_sha256
        ):
            return self._proposal(
                snapshot,
                catalog,
                status="invalid",
                reason_code="MISSION_COMPLETION_CATALOG_BINDING_MISMATCH",
            )

        expected = [
            *[
                {
                    "requirement": item,
                    "requirement_kind": "completion",
                }
                for item in snapshot.completion_requirements
            ],
            *[
                {
                    "requirement": item,
                    "requirement_kind": "validation",
                }
                for item in snapshot.validation_requirements
            ],
        ]
        if not expected:
            return self._proposal(
                snapshot,
                catalog,
                status="candidate",
                reason_code="MISSION_COMPLETION_REQUIREMENTS_ABSENT",
                bindings=[],
            )

        response = self.reasoner.propose_json(
            semantic_goal=(
                "Map each frozen mission completion or validation requirement "
                "to canonical evidence that is semantically relevant. Propose "
                "relations only; do not claim truth, completion, authorization, "
                "or policy. Use only exact supplied requirement names, evidence "
                "refs and producer TaskRun ids."
            ),
            payload={
                "mission": {
                    "mission_id": snapshot.mission_id,
                    "strategy": snapshot.strategy,
                    "source_prompt_sha256": snapshot.source_prompt_sha256,
                    "semantic_context": dict(snapshot.semantic_context),
                },
                "requirements": expected,
                "evidence_catalog": [
                    item.model_dump(mode="json")
                    for item in catalog.items
                ],
                "rules": [
                    "Return one or more candidate bindings per requirement only when evidence is semantically relevant.",
                    "semantic_relation is supports, does_not_support, or ambiguous; it is not a truth verdict.",
                    "Never invent requirement names, evidence refs, producer ids, statuses, permissions, or authority.",
                    "Use evidence_refs and producer_task_run_ids exactly as supplied.",
                    "Do not infer from raw prompt text; only frozen semantic_context is available.",
                ],
                "output_schema": {
                    "bindings": [
                        {
                            "requirement": "exact supplied requirement",
                            "requirement_kind": "completion|validation",
                            "semantic_relation": "supports|does_not_support|ambiguous",
                            "evidence_refs": ["exact catalog evidence_ref"],
                            "producer_task_run_ids": ["exact catalog producer_task_run_id"],
                            "confidence": "number_between_0_and_1",
                            "rationale": "brief semantic rationale",
                        }
                    ]
                },
            },
            allowed_fields=["bindings"],
            required_fields=["bindings"],
            role_id="mission_completion_evidence_binder",
            max_tokens=1200,
        )
        provenance = {
            "model_id": response.get("model_id"),
            "response_id": response.get("response_id"),
            "real_inference": response.get("real_inference"),
            "evaluation_status": response.get("evaluation_status"),
            "warnings": list(response.get("warnings") or []),
        }
        if response.get("status") != "candidate":
            return self._proposal(
                snapshot,
                catalog,
                status="unavailable",
                reason_code=str(
                    response.get("reason_code")
                    or "MISSION_COMPLETION_BINDING_REASONER_UNAVAILABLE"
                ),
                provenance=provenance,
            )

        candidate = response.get("candidate")
        raw_bindings = (
            candidate.get("bindings")
            if isinstance(candidate, dict)
            else None
        )
        if not isinstance(raw_bindings, list):
            return self._proposal(
                snapshot,
                catalog,
                status="invalid",
                reason_code="MISSION_COMPLETION_BINDINGS_LIST_REQUIRED",
                provenance=provenance,
            )

        max_bindings = int(
            (
                self.policy.get("semantic_binding", {})
                or {}
            ).get("max_bindings", 64)
        )
        if len(raw_bindings) > max_bindings:
            return self._proposal(
                snapshot,
                catalog,
                status="invalid",
                reason_code="MISSION_COMPLETION_BINDING_LIMIT_EXCEEDED",
                provenance=provenance,
            )

        bindings: list[MissionCompletionBindingCandidate] = []
        try:
            for row in raw_bindings:
                bindings.append(
                    MissionCompletionBindingCandidate.model_validate(row)
                )
        except Exception as exc:
            return self._proposal(
                snapshot,
                catalog,
                status="invalid",
                reason_code=(
                    "MISSION_COMPLETION_BINDING_CANDIDATE_INVALID:"
                    f"{exc.__class__.__name__}"
                ),
                provenance=provenance,
            )

        return self._proposal(
            snapshot,
            catalog,
            status="candidate",
            reason_code="MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED",
            bindings=bindings,
            provenance=provenance,
        )

    def _proposal(
        self,
        snapshot: MissionCompletionSnapshot,
        catalog: MissionCompletionEvidenceCatalog,
        *,
        status: str,
        reason_code: str,
        bindings: list[MissionCompletionBindingCandidate] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> MissionCompletionBindingProposal:
        selected = sorted(
            list(bindings or []),
            key=lambda item: (
                item.requirement_kind,
                item.requirement,
                item.semantic_relation,
                tuple(item.producer_task_run_ids),
                tuple(item.evidence_refs),
            ),
        )
        stable_payload = {
            "mission_id": snapshot.mission_id,
            "snapshot_authority_sha256": snapshot.authority_sha256,
            "catalog_authority_sha256": catalog.authority_sha256,
            "status": status,
            "reason_code": reason_code,
            "bindings": [
                item.model_dump(mode="json") for item in selected
            ],
        }
        proposal_sha256 = hashlib.sha256(
            json.dumps(
                stable_payload,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return MissionCompletionBindingProposal(
            **stable_payload,
            provenance=dict(provenance or {}),
            proposal_sha256=proposal_sha256,
        )
