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

        settings = dict(self.policy.get("semantic_binding", {}) or {})
        max_bindings = int(settings.get("max_bindings", 64))
        max_calls = max(1, int(settings.get("max_reasoner_calls", 64)))
        max_items = max(
            1,
            int(settings.get("max_evidence_items_per_batch", 8)),
        )
        max_prompt_chars = max(
            1,
            int(settings.get("max_batch_prompt_chars", 9000)),
        )
        max_batch_bindings = max(
            1,
            int(settings.get("max_bindings_per_batch", 4)),
        )
        max_tokens = max(
            1,
            int(settings.get("max_output_tokens_per_batch", 900)),
        )

        if not catalog.items:
            return self._proposal(
                snapshot,
                catalog,
                status="candidate",
                reason_code="MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED",
                bindings=[],
                provenance={
                    "role_id": "mission_completion_evidence_binder",
                    "binding_mode": "bounded_evidence_batches_v1",
                    "reasoner_calls": 0,
                    "batch_count": 0,
                    "catalog_items": 0,
                },
            )

        semantic_goal = (
            "Map the single frozen mission completion or validation "
            "requirement in this batch to supplied canonical evidence that "
            "is semantically relevant. Propose relations only; do not claim "
            "truth, completion, authorization, or policy. Use only exact "
            "supplied requirement names, evidence refs and producer TaskRun "
            "ids."
        )
        mission_view = {
            "strategy": snapshot.strategy,
            "semantic_context": dict(snapshot.semantic_context),
        }
        rules = [
            (
                "This batch contains exactly one requirement and a bounded "
                "subset of canonical evidence."
            ),
            (
                "Return candidate bindings only for the supplied requirement; "
                "an empty bindings list is valid when no supplied evidence is "
                "semantically relevant."
            ),
            (
                "semantic_relation is supports, does_not_support, or "
                "ambiguous; it is not a truth verdict."
            ),
            (
                "Use supports only when supplied evidence content, semantic "
                "properties, limitations, or artifact descriptors directly "
                "address the requirement. Runtime success/safety status alone "
                "is never sufficient semantic support."
            ),
            (
                "Never invent requirement names, evidence refs, producer ids, "
                "statuses, permissions, or authority."
            ),
            (
                "Use evidence_refs and producer_task_run_ids exactly as "
                "supplied in this batch."
            ),
            (
                "Do not infer from raw prompt text; only frozen "
                "semantic_context is available."
            ),
            (
                "Prefer grouping relevant evidence refs into one binding when "
                "they share the same semantic relation and rationale."
            ),
            f"Return at most {max_batch_bindings} bindings in this batch.",
        ]
        output_schema = {
            "bindings": [
                {
                    "requirement": "exact supplied requirement",
                    "requirement_kind": "completion|validation",
                    "semantic_relation": (
                        "supports|does_not_support|ambiguous"
                    ),
                    "evidence_refs": ["exact batch evidence_ref"],
                    "producer_task_run_ids": [
                        "exact batch producer_task_run_id"
                    ],
                    "confidence": "number_between_0_and_1",
                    "rationale": "brief semantic rationale",
                }
            ]
        }
        evidence_view = [
            self._model_evidence_item(item)
            for item in catalog.items
        ]

        batch_plan: list[
            tuple[dict[str, str], list[dict[str, Any]], dict[str, Any], int]
        ] = []
        for requirement in expected:
            chunks, failure = self._evidence_batches(
                requirement=requirement,
                evidence=evidence_view,
                mission_view=mission_view,
                rules=rules,
                output_schema=output_schema,
                semantic_goal=semantic_goal,
                max_items=max_items,
                max_prompt_chars=max_prompt_chars,
            )
            if failure is not None:
                return self._proposal(
                    snapshot,
                    catalog,
                    status="unavailable",
                    reason_code=failure,
                    provenance={
                        "role_id": "mission_completion_evidence_binder",
                        "binding_mode": "bounded_evidence_batches_v1",
                        "max_batch_prompt_chars": max_prompt_chars,
                    },
                )
            for chunk, payload, prompt_chars in chunks:
                batch_plan.append(
                    (requirement, chunk, payload, prompt_chars)
                )

        if len(batch_plan) > max_calls:
            return self._proposal(
                snapshot,
                catalog,
                status="unavailable",
                reason_code=(
                    "MISSION_COMPLETION_BINDING_REASONER_CALL_LIMIT_EXCEEDED"
                ),
                provenance={
                    "role_id": "mission_completion_evidence_binder",
                    "binding_mode": "bounded_evidence_batches_v1",
                    "required_reasoner_calls": len(batch_plan),
                    "max_reasoner_calls": max_calls,
                    "catalog_items": len(catalog.items),
                    "requirements": len(expected),
                },
            )

        raw_bindings: list[dict[str, Any]] = []
        batch_provenance: list[dict[str, Any]] = []
        all_warnings: list[str] = []
        for batch_index, (
            requirement,
            chunk,
            payload,
            prompt_chars,
        ) in enumerate(batch_plan, start=1):
            response = self.reasoner.propose_json(
                semantic_goal=semantic_goal,
                payload=payload,
                allowed_fields=["bindings"],
                required_fields=["bindings"],
                role_id="mission_completion_evidence_binder",
                max_tokens=max_tokens,
            )
            response_warnings = [
                str(item)
                for item in list(response.get("warnings") or [])
                if str(item)
            ]
            all_warnings.extend(response_warnings)
            batch_provenance.append(
                {
                    "batch_index": batch_index,
                    "requirement": requirement["requirement"],
                    "requirement_kind": requirement["requirement_kind"],
                    "evidence_items": len(chunk),
                    "prompt_chars": prompt_chars,
                    "model_id": response.get("model_id"),
                    "response_id": response.get("response_id"),
                    "real_inference": response.get("real_inference"),
                    "evaluation_status": response.get(
                        "evaluation_status"
                    ),
                    "retry_attempts": response.get("retry_attempts"),
                    "warnings": response_warnings,
                }
            )
            if response.get("status") != "candidate":
                return self._proposal(
                    snapshot,
                    catalog,
                    status="unavailable",
                    reason_code=str(
                        response.get("reason_code")
                        or "MISSION_COMPLETION_BINDING_REASONER_UNAVAILABLE"
                    ),
                    provenance=self._batch_provenance(
                        batch_provenance,
                        all_warnings,
                        catalog_items=len(catalog.items),
                    ),
                )

            candidate = response.get("candidate")
            rows = (
                candidate.get("bindings")
                if isinstance(candidate, dict)
                else None
            )
            if not isinstance(rows, list):
                return self._proposal(
                    snapshot,
                    catalog,
                    status="invalid",
                    reason_code=(
                        "MISSION_COMPLETION_BINDINGS_LIST_REQUIRED"
                    ),
                    provenance=self._batch_provenance(
                        batch_provenance,
                        all_warnings,
                        catalog_items=len(catalog.items),
                    ),
                )
            if len(rows) > max_batch_bindings:
                return self._proposal(
                    snapshot,
                    catalog,
                    status="invalid",
                    reason_code=(
                        "MISSION_COMPLETION_BINDING_BATCH_LIMIT_EXCEEDED"
                    ),
                    provenance=self._batch_provenance(
                        batch_provenance,
                        all_warnings,
                        catalog_items=len(catalog.items),
                    ),
                )

            scope_error = self._batch_scope_error(
                rows=rows,
                requirement=requirement,
                evidence=chunk,
            )
            if scope_error is not None:
                return self._proposal(
                    snapshot,
                    catalog,
                    status="invalid",
                    reason_code=scope_error,
                    provenance=self._batch_provenance(
                        batch_provenance,
                        all_warnings,
                        catalog_items=len(catalog.items),
                    ),
                )
            raw_bindings.extend(
                row for row in rows if isinstance(row, dict)
            )
            raw_bindings = self._dedupe_raw_bindings(raw_bindings)
            if len(raw_bindings) > max_bindings:
                return self._proposal(
                    snapshot,
                    catalog,
                    status="invalid",
                    reason_code=(
                        "MISSION_COMPLETION_BINDING_LIMIT_EXCEEDED"
                    ),
                    provenance=self._batch_provenance(
                        batch_provenance,
                        all_warnings,
                        catalog_items=len(catalog.items),
                    ),
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
                provenance=self._batch_provenance(
                    batch_provenance,
                    all_warnings,
                    catalog_items=len(catalog.items),
                ),
            )

        return self._proposal(
            snapshot,
            catalog,
            status="candidate",
            reason_code="MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED",
            bindings=bindings,
            provenance=self._batch_provenance(
                batch_provenance,
                all_warnings,
                catalog_items=len(catalog.items),
            ),
        )

    @staticmethod
    def _model_evidence_item(
        item: Any,
    ) -> dict[str, Any]:
        projected = {
            "evidence_ref": item.evidence_ref,
            "producer_task_run_id": item.producer_task_run_id,
            "phase_id": item.phase_id,
            "runtime_status": item.runtime_status,
            "result_status": item.result_status,
            "runtime_truth_status": item.runtime_truth_status,
            "runtime_truth_safe_to_report_success": (
                item.runtime_truth_safe_to_report_success
            ),
            "phase_dependency_status": item.phase_dependency_status,
            "reason_code": item.reason_code,
            "limitations": list(item.limitations),
            "missing_truth": list(item.missing_truth),
            "use_safety": dict(item.use_safety),
            "semantic_properties": dict(item.semantic_properties),
            "artifact_descriptors": list(item.artifact_descriptors),
        }
        return {
            key: value
            for key, value in projected.items()
            if value not in (None, "", [], {})
        }

    def _evidence_batches(
        self,
        *,
        requirement: dict[str, str],
        evidence: list[dict[str, Any]],
        mission_view: dict[str, Any],
        rules: list[str],
        output_schema: dict[str, Any],
        semantic_goal: str,
        max_items: int,
        max_prompt_chars: int,
    ) -> tuple[
        list[tuple[list[dict[str, Any]], dict[str, Any], int]],
        str | None,
    ]:
        batches: list[
            tuple[list[dict[str, Any]], dict[str, Any], int]
        ] = []
        current: list[dict[str, Any]] = []

        def payload_for(
            rows: list[dict[str, Any]],
        ) -> dict[str, Any]:
            return {
                "mission": mission_view,
                "requirement": dict(requirement),
                "evidence_catalog": list(rows),
                "rules": list(rules),
                "output_schema": output_schema,
            }

        for item in evidence:
            candidate = [*current, item]
            payload = payload_for(candidate)
            prompt_chars = self._reasoner_prompt_chars(
                semantic_goal=semantic_goal,
                payload=payload,
            )
            if (
                len(candidate) <= max_items
                and prompt_chars <= max_prompt_chars
            ):
                current = candidate
                continue

            if current:
                current_payload = payload_for(current)
                batches.append(
                    (
                        list(current),
                        current_payload,
                        self._reasoner_prompt_chars(
                            semantic_goal=semantic_goal,
                            payload=current_payload,
                        ),
                    )
                )
                current = [item]
                single_payload = payload_for(current)
                single_chars = self._reasoner_prompt_chars(
                    semantic_goal=semantic_goal,
                    payload=single_payload,
                )
                if single_chars > max_prompt_chars:
                    return (
                        [],
                        (
                            "MISSION_COMPLETION_BINDING_EVIDENCE_ITEM_"
                            "BUDGET_EXCEEDED"
                        ),
                    )
            else:
                return (
                    [],
                    (
                        "MISSION_COMPLETION_BINDING_EVIDENCE_ITEM_"
                        "BUDGET_EXCEEDED"
                    ),
                )

        if current:
            payload = payload_for(current)
            batches.append(
                (
                    list(current),
                    payload,
                    self._reasoner_prompt_chars(
                        semantic_goal=semantic_goal,
                        payload=payload,
                    ),
                )
            )
        return batches, None

    @staticmethod
    def _reasoner_prompt_chars(
        *,
        semantic_goal: str,
        payload: dict[str, Any],
    ) -> int:
        return len(
            json.dumps(
                {
                    "semantic_goal": semantic_goal,
                    "allowed_fields": ["bindings"],
                    "required_fields": ["bindings"],
                    "payload": payload,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )

    @staticmethod
    def _batch_scope_error(
        *,
        rows: list[Any],
        requirement: dict[str, str],
        evidence: list[dict[str, Any]],
    ) -> str | None:
        refs = {
            str(item.get("evidence_ref"))
            for item in evidence
            if item.get("evidence_ref")
        }
        producers = {
            str(item.get("producer_task_run_id"))
            for item in evidence
            if item.get("producer_task_run_id")
        }
        for row in rows:
            if not isinstance(row, dict):
                return "MISSION_COMPLETION_BINDING_CANDIDATE_INVALID:TypeError"
            if (
                row.get("requirement") != requirement["requirement"]
                or row.get("requirement_kind")
                != requirement["requirement_kind"]
            ):
                return "MISSION_COMPLETION_BINDING_BATCH_SCOPE_VIOLATION"
            if any(
                str(ref) not in refs
                for ref in list(row.get("evidence_refs") or [])
            ):
                return "MISSION_COMPLETION_BINDING_BATCH_SCOPE_VIOLATION"
            if any(
                str(run_id) not in producers
                for run_id in list(
                    row.get("producer_task_run_ids") or []
                )
            ):
                return "MISSION_COMPLETION_BINDING_BATCH_SCOPE_VIOLATION"
        return None

    @staticmethod
    def _dedupe_raw_bindings(
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        unique: dict[str, dict[str, Any]] = {}
        for row in rows:
            key = json.dumps(
                row,
                sort_keys=True,
                ensure_ascii=True,
                separators=(",", ":"),
            )
            unique.setdefault(key, row)
        return list(unique.values())

    @staticmethod
    def _batch_provenance(
        batches: list[dict[str, Any]],
        warnings: list[str],
        *,
        catalog_items: int,
    ) -> dict[str, Any]:
        model_ids = list(
            dict.fromkeys(
                str(item.get("model_id"))
                for item in batches
                if item.get("model_id")
            )
        )
        response_ids = [
            str(item.get("response_id"))
            for item in batches
            if item.get("response_id")
        ]
        real_values = [
            bool(item.get("real_inference"))
            for item in batches
            if item.get("real_inference") is not None
        ]
        return {
            "role_id": "mission_completion_evidence_binder",
            "binding_mode": "bounded_evidence_batches_v1",
            "reasoner_calls": len(batches),
            "batch_count": len(batches),
            "catalog_items": catalog_items,
            "model_id": model_ids[0] if len(model_ids) == 1 else None,
            "model_ids": model_ids,
            "response_id": (
                response_ids[0]
                if len(response_ids) == 1
                else None
            ),
            "response_ids": response_ids,
            "real_inference": (
                all(real_values) if real_values else None
            ),
            "evaluation_status": (
                batches[-1].get("evaluation_status")
                if batches
                else None
            ),
            "warnings": list(
                dict.fromkeys(str(item) for item in warnings if str(item))
            ),
            "batches": batches,
        }

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
