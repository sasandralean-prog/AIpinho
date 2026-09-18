from __future__ import annotations

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionEvidenceCatalog,
    MissionCompletionEvidenceItem,
    MissionCompletionSnapshot,
)
from aipinho.services.runtime.mission_completion_binding_proposal_service import (
    MissionCompletionBindingProposalService,
)


class _FakeReasoner:
    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = []

    def propose_json(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "status": "candidate",
            "candidate": self.candidate,
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


def test_reasoner_receives_only_frozen_semantics_requirements_and_catalog() -> None:
    snapshot = _snapshot()
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
                    "confidence": 0.91,
                    "rationale": "Patch artifact semantically addresses the requested change.",
                },
                {
                    "requirement": "tests_pass",
                    "requirement_kind": "validation",
                    "semantic_relation": "supports",
                    "evidence_refs": ["evidence:tests"],
                    "producer_task_run_ids": ["task_run_b"],
                    "confidence": 0.94,
                    "rationale": "Validation evidence semantically addresses the test requirement.",
                },
            ]
        }
    )

    proposal = MissionCompletionBindingProposalService(
        reasoner=reasoner,  # type: ignore[arg-type]
    ).propose(snapshot, catalog)

    assert proposal.status == "candidate"
    assert proposal.reason_code == "MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED"
    assert len(proposal.bindings) == 2
    assert len(proposal.proposal_sha256) == 64
    assert len(reasoner.calls) == 1
    payload = reasoner.calls[0]["payload"]
    assert payload["mission"]["semantic_context"] == snapshot.semantic_context
    assert "raw_prompt" not in str(payload)
    assert payload["requirements"] == [
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
    snapshot = _snapshot()
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
    snapshot = _snapshot()
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
