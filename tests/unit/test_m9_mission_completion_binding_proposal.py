from __future__ import annotations

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionEvidenceCatalog,
    MissionCompletionEvidenceItem,
    MissionCompletionSnapshot,
)
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.roles.role_model_binding_service import (
    RoleModelBindingService,
)
from aipinho.services.roles.role_registry_service import RoleRegistryService
from aipinho.services.runtime.mission_completion_binding_proposal_service import (
    MissionCompletionBindingProposalService,
)


class _FakeReasoner:
    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = []

    def propose_json(self, **kwargs):
        self.calls.append(kwargs)
        candidate = (
            self.candidate(kwargs)
            if callable(self.candidate)
            else self.candidate
        )
        return {
            "status": "candidate",
            "candidate": candidate,
            "model_id": "fake-model",
            "response_id": "fake-response",
            "real_inference": False,
            "warnings": [],
        }


def _snapshot():
    return MissionCompletionSnapshot(
        mission_id="mission_binding",
        status="ready",
        source_prompt_sha256="a" * 64,
        strategy="end_to_end_governed",
        semantic_context={
            "intent_type": "workspace_fix_request",
            "semantic_intent_graph": {
                "mutation_intent": True,
                "execution_intent": True,
            },
        },
        completion_requirements=["validated_change"],
        validation_requirements=["tests_pass"],
        task_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_authority_sha256s=["b" * 64, "c" * 64],
        evidence_refs=["artifact:patch", "evidence:tests"],
        authority_sha256="d" * 64,
    )


def _catalog(snapshot):
    return MissionCompletionEvidenceCatalog(
        mission_id=snapshot.mission_id,
        snapshot_authority_sha256=snapshot.authority_sha256,
        items=[
            MissionCompletionEvidenceItem(
                evidence_ref="artifact:patch",
                producer_task_run_id="task_run_a",
                phase_id="implementation",
                phase_outcome_authority_sha256="b" * 64,
                runtime_status="completed",
                result_status="completed",
                runtime_truth_status="completed",
                runtime_truth_safe_to_report_success=True,
                phase_dependency_status="satisfied",
                artifact_descriptors=[
                    {
                        "artifact_id": "artifact_patch",
                        "logical_path": "src/example.py",
                        "validation_status": "passed",
                    }
                ],
            ),
            MissionCompletionEvidenceItem(
                evidence_ref="evidence:tests",
                producer_task_run_id="task_run_b",
                phase_id="validation",
                phase_outcome_authority_sha256="c" * 64,
                runtime_status="completed",
                result_status="completed",
                runtime_truth_status="completed",
                runtime_truth_safe_to_report_success=True,
                phase_dependency_status="satisfied",
            ),
        ],
        authority_sha256="e" * 64,
    )


def test_reasoner_receives_bounded_frozen_semantics_and_catalog() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot)

    def candidate_for_call(kwargs):
        requirement = kwargs["payload"]["requirement"]
        if requirement["requirement"] == "validated_change":
            ref = "artifact:patch"
            producer = "task_run_a"
        else:
            ref = "evidence:tests"
            producer = "task_run_b"
        return {
            "bindings": [
                {
                    "requirement": requirement["requirement"],
                    "requirement_kind": requirement["requirement_kind"],
                    "semantic_relation": "supports",
                    "evidence_refs": [ref],
                    "producer_task_run_ids": [producer],
                    "confidence": 0.92,
                    "rationale": "Supplied evidence is semantically relevant.",
                }
            ]
        }

    reasoner = _FakeReasoner(candidate_for_call)
    proposal = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)

    assert proposal.status == "candidate"
    assert proposal.reason_code == "MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED"
    assert len(proposal.bindings) == 2
    assert len(proposal.proposal_sha256) == 64
    assert len(reasoner.calls) == 2
    assert proposal.provenance["reasoner_calls"] == 2
    assert proposal.provenance["binding_mode"] == "bounded_evidence_batches_v1"

    seen_requirements = []
    for call in reasoner.calls:
        payload = call["payload"]
        seen_requirements.append(payload["requirement"])
        assert payload["mission"]["semantic_context"] == snapshot.semantic_context
        assert "raw_prompt" not in str(payload)
        assert "source_prompt_sha256" not in str(payload)
        assert "phase_outcome_authority_sha256" not in str(payload)
        assert len(payload["evidence_catalog"]) == 2
        assert any(
            "Runtime success/safety status alone" in rule
            for rule in payload["rules"]
        )
        assert call["role_id"] == "mission_completion_evidence_binder"
        assert call["max_tokens"] == 900

    assert seen_requirements == [
        {
            "requirement": "validated_change",
            "requirement_kind": "completion",
        },
        {
            "requirement": "tests_pass",
            "requirement_kind": "validation",
        },
    ]


def test_model_cannot_inject_truth_status_into_binding_candidate() -> None:
    snapshot = _snapshot().model_copy(
        update={"validation_requirements": []}
    )
    catalog = _catalog(snapshot)
    reasoner = _FakeReasoner(
        {
            "bindings": [
                {
                    "requirement": "validated_change",
                    "requirement_kind": "completion",
                    "semantic_relation": "supports",
                    "evidence_refs": ["artifact:patch"],
                    "producer_task_run_ids": ["task_run_a"],
                    "confidence": 0.99,
                    "rationale": "candidate",
                    "status": "satisfied",
                }
            ]
        }
    )

    proposal = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)

    assert proposal.status == "invalid"
    assert proposal.reason_code.startswith(
        "MISSION_COMPLETION_BINDING_CANDIDATE_INVALID:"
    )
    assert proposal.bindings == []


def test_catalog_snapshot_mismatch_blocks_without_reasoner_call() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot).model_copy(
        update={"snapshot_authority_sha256": "f" * 64}
    )
    reasoner = _FakeReasoner({"bindings": []})

    proposal = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)

    assert proposal.status == "invalid"
    assert proposal.reason_code == "MISSION_COMPLETION_CATALOG_BINDING_MISMATCH"
    assert reasoner.calls == []


def test_identical_binding_content_has_stable_hash_across_model_response_ids() -> None:
    snapshot = _snapshot().model_copy(
        update={"validation_requirements": []}
    )
    catalog = _catalog(snapshot)
    candidate = {
        "bindings": [
            {
                "requirement": "validated_change",
                "requirement_kind": "completion",
                "semantic_relation": "supports",
                "evidence_refs": ["artifact:patch"],
                "producer_task_run_ids": ["task_run_a"],
                "confidence": 0.9,
                "rationale": "same semantic relation",
            }
        ]
    }
    first_reasoner = _FakeReasoner(candidate)
    second_reasoner = _FakeReasoner(candidate)

    first = MissionCompletionBindingProposalService(
        reasoner=first_reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)
    second = MissionCompletionBindingProposalService(
        reasoner=second_reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)

    assert first.proposal_sha256 == second.proposal_sha256


def _many_catalog(snapshot, count: int, *, semantic_blob: str = ""):
    items = []
    for index in range(count):
        items.append(
            MissionCompletionEvidenceItem(
                evidence_ref=f"evidence:{index}",
                producer_task_run_id=f"task_run_{index}",
                phase_id="validation",
                phase_outcome_authority_sha256=f"{index:064x}"[-64:],
                runtime_status="completed",
                result_status="completed",
                runtime_truth_status="completed",
                runtime_truth_safe_to_report_success=True,
                phase_dependency_status="satisfied",
                semantic_properties=(
                    {"detail": semantic_blob}
                    if semantic_blob
                    else {}
                ),
            )
        )
    return MissionCompletionEvidenceCatalog(
        mission_id=snapshot.mission_id,
        snapshot_authority_sha256=snapshot.authority_sha256,
        items=items,
        authority_sha256="e" * 64,
    )


def test_binder_role_is_registered_and_routes_to_medium_instruct_model() -> None:
    role = RoleRegistryService().require_role(
        "mission_completion_evidence_binder"
    )
    binding = RoleModelBindingService().get_binding(
        "mission_completion_evidence_binder"
    )
    route = ModelRouterService().select_model(
        purpose="chat",
        role_id="mission_completion_evidence_binder",
    )

    assert role.can_call_model is True
    assert role.can_call_tools is False
    assert role.can_execute_tools is False
    assert role.can_write is False
    assert role.can_patch is False
    assert role.can_approve is False
    assert role.output_contract == "mission_completion_binding_output"
    assert binding is not None
    assert binding.primary_model == "qwen2_5_7b_instruct_q5_k_m"
    assert binding.max_latency_class == "medium"
    assert binding.metadata["specialized_child_only"] is True
    assert binding.metadata["truth_authority"] is False
    assert route.status == "ok"
    assert route.model is not None
    assert route.model.model_id == "qwen2_5_7b_instruct_q5_k_m"


def test_evidence_catalog_is_batched_before_reasoning() -> None:
    snapshot = _snapshot().model_copy(
        update={"validation_requirements": []}
    )
    catalog = _many_catalog(snapshot, 19)
    reasoner = _FakeReasoner({"bindings": []})
    service = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    )

    proposal = service.propose(snapshot, catalog)

    assert proposal.status == "candidate"
    assert proposal.provenance["reasoner_calls"] == 3
    assert len(reasoner.calls) == 3
    assert [
        len(call["payload"]["evidence_catalog"])
        for call in reasoner.calls
    ] == [8, 8, 3]
    assert all(
        service._reasoner_prompt_chars(
            semantic_goal=call["semantic_goal"],
            payload=call["payload"],
        )
        <= 9000
        for call in reasoner.calls
    )


def test_reasoner_call_limit_fails_closed_before_any_model_call() -> None:
    snapshot = _snapshot().model_copy(
        update={"validation_requirements": []}
    )
    catalog = _many_catalog(snapshot, 19)
    reasoner = _FakeReasoner({"bindings": []})
    service = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    )
    service.policy["semantic_binding"]["max_reasoner_calls"] = 2

    proposal = service.propose(snapshot, catalog)

    assert proposal.status == "unavailable"
    assert (
        proposal.reason_code
        == "MISSION_COMPLETION_BINDING_REASONER_CALL_LIMIT_EXCEEDED"
    )
    assert proposal.provenance["required_reasoner_calls"] == 3
    assert reasoner.calls == []


def test_single_evidence_item_over_batch_budget_fails_closed() -> None:
    snapshot = _snapshot().model_copy(
        update={"validation_requirements": []}
    )
    catalog = _many_catalog(snapshot, 1, semantic_blob="x" * 12000)
    reasoner = _FakeReasoner({"bindings": []})
    service = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    )

    proposal = service.propose(snapshot, catalog)

    assert proposal.status == "unavailable"
    assert (
        proposal.reason_code
        == "MISSION_COMPLETION_BINDING_EVIDENCE_ITEM_BUDGET_EXCEEDED"
    )
    assert reasoner.calls == []


def test_model_cannot_reference_evidence_outside_current_batch() -> None:
    snapshot = _snapshot().model_copy(
        update={"validation_requirements": []}
    )
    catalog = _many_catalog(snapshot, 9)
    reasoner = _FakeReasoner(
        {
            "bindings": [
                {
                    "requirement": "validated_change",
                    "requirement_kind": "completion",
                    "semantic_relation": "supports",
                    "evidence_refs": ["evidence:8"],
                    "producer_task_run_ids": ["task_run_8"],
                    "confidence": 0.9,
                    "rationale": "Out-of-batch reference.",
                }
            ]
        }
    )

    proposal = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)

    assert proposal.status == "invalid"
    assert (
        proposal.reason_code
        == "MISSION_COMPLETION_BINDING_BATCH_SCOPE_VIOLATION"
    )
    assert len(reasoner.calls) == 1


def test_requirements_with_empty_catalog_skip_model_and_compile_empty_candidate() -> None:
    snapshot = _snapshot().model_copy(
        update={"validation_requirements": []}
    )
    catalog = _many_catalog(snapshot, 0)
    reasoner = _FakeReasoner({"bindings": []})

    proposal = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)

    assert proposal.status == "candidate"
    assert proposal.bindings == []
    assert proposal.provenance["reasoner_calls"] == 0
    assert reasoner.calls == []
