from __future__ import annotations

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionBindingCandidate,
    MissionCompletionBindingProposal,
    MissionCompletionEvidenceCatalog,
    MissionCompletionEvidenceItem,
    MissionCompletionSnapshot,
)
from aipinho.schemas.runtime.mission_contract import MissionContractBinding
from aipinho.services.runtime.mission_completion_resolution_service import (
    MissionCompletionResolutionService,
)
from aipinho.services.runtime.task_run_store import TaskRunStore
from tests.support.runtime_fixtures import runtime_run


class _Projection:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def project(self, *, mission_id: str, limit: int = 1000):
        assert mission_id == self.snapshot.mission_id
        return self.snapshot


class _Catalog:
    def __init__(self, catalog):
        self.catalog = catalog

    def build(self, snapshot, *, limit: int = 1000):
        assert snapshot.authority_sha256 == self.catalog.snapshot_authority_sha256
        return self.catalog


class _Proposer:
    def __init__(self, proposal):
        self.proposal = proposal
        self.calls = 0

    def propose(self, snapshot, catalog):
        self.calls += 1
        return self.proposal


class _RejectProposer:
    def propose(self, snapshot, catalog):
        raise AssertionError("restart rehydration must not invoke semantic reasoner")


def _snapshot():
    return MissionCompletionSnapshot(
        mission_id="mission_resolution",
        status="ready",
        semantic_context={"intent_type": "workspace_fix_request"},
        completion_requirements=["validated_change"],
        validation_requirements=[],
        task_run_ids=["task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        terminal_task_run_ids=["task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        phase_outcome_run_ids=["task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
        phase_outcome_authority_sha256s=["a" * 64],
        evidence_refs=["artifact:patch"],
        authority_sha256="b" * 64,
    )


def _catalog(snapshot, *, authority="c" * 64):
    return MissionCompletionEvidenceCatalog(
        mission_id=snapshot.mission_id,
        snapshot_authority_sha256=snapshot.authority_sha256,
        items=[
            MissionCompletionEvidenceItem(
                evidence_ref="artifact:patch",
                producer_task_run_id="task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                phase_id="implementation",
                phase_outcome_authority_sha256="a" * 64,
                runtime_status="completed",
                result_status="completed",
                runtime_truth_status="completed",
                runtime_truth_safe_to_report_success=True,
                phase_dependency_status="satisfied",
                use_safety={"safe_for_truth_claim": True},
            )
        ],
        authority_sha256=authority,
    )


def _proposal(snapshot, catalog):
    return MissionCompletionBindingProposal(
        mission_id=snapshot.mission_id,
        snapshot_authority_sha256=snapshot.authority_sha256,
        catalog_authority_sha256=catalog.authority_sha256,
        status="candidate",
        reason_code="MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED",
        bindings=[
            MissionCompletionBindingCandidate(
                requirement="validated_change",
                requirement_kind="completion",
                semantic_relation="supports",
                evidence_refs=["artifact:patch"],
                producer_task_run_ids=[
                    "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                ],
                confidence=0.94,
                rationale="canonical patch evidence matches the frozen requirement",
            )
        ],
        proposal_sha256="d" * 64,
    )


def _seed_store(root):
    store = TaskRunStore(root=root)
    run = runtime_run().model_copy(
        update={
            "run_id": "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "task_run_id": "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "mission_binding": MissionContractBinding(
                mission_id="mission_resolution",
                authority_sha256="e" * 64,
                revision=1,
                source_prompt_sha256="f" * 64,
                strategy="end_to_end_governed",
            ),
            "status": "completed",
        }
    )
    store.create_run(run)
    return store, run


def test_generated_proposal_is_persisted_only_after_successful_compilation(
    tmp_path,
) -> None:
    root = tmp_path / "runs"
    store, run = _seed_store(root)
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    proposer = _Proposer(_proposal(snapshot, catalog))
    service = MissionCompletionResolutionService(
        store=store,
        projection=_Projection(snapshot),  # type: ignore[arg-type]
        catalog=_Catalog(catalog),  # type: ignore[arg-type]
        proposer=proposer,  # type: ignore[arg-type]
    )

    resolution = service.resolve(
        mission_id=snapshot.mission_id,
        anchor_run_id=run.run_id,
        allow_inference=True,
    )

    assert resolution.status == "ready"
    assert resolution.proposal_source == "generated"
    assert resolution.compilation_status == "compiled"
    assert resolution.facet is not None
    assert resolution.facet.safe_to_report_success is True
    assert proposer.calls == 1
    persisted = store.get_run(run.run_id)
    assert persisted is not None
    payload = persisted.intent_map[
        MissionCompletionResolutionService.PERSISTED_PROPOSAL_KEY
    ]
    assert payload["proposal_sha256"] == "d" * 64


def test_restart_rehydrates_persisted_proposal_without_model_reinvocation(
    tmp_path,
) -> None:
    root = tmp_path / "runs"
    store, run = _seed_store(root)
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    first = MissionCompletionResolutionService(
        store=store,
        projection=_Projection(snapshot),  # type: ignore[arg-type]
        catalog=_Catalog(catalog),  # type: ignore[arg-type]
        proposer=_Proposer(_proposal(snapshot, catalog)),  # type: ignore[arg-type]
    ).resolve(
        mission_id=snapshot.mission_id,
        anchor_run_id=run.run_id,
        allow_inference=True,
    )
    assert first.status == "ready"

    restarted_store = TaskRunStore(root=root)
    restarted = MissionCompletionResolutionService(
        store=restarted_store,
        projection=_Projection(snapshot),  # type: ignore[arg-type]
        catalog=_Catalog(catalog),  # type: ignore[arg-type]
        proposer=_RejectProposer(),  # type: ignore[arg-type]
    ).resolve(
        mission_id=snapshot.mission_id,
        allow_inference=False,
    )

    assert restarted.status == first.status
    assert restarted.proposal_source == "persisted"
    assert restarted.proposal_sha256 == first.proposal_sha256
    assert restarted.facet is not None
    assert first.facet is not None
    assert restarted.facet.authority_sha256 == first.facet.authority_sha256


def test_restart_fails_closed_when_catalog_changed_and_inference_disabled(
    tmp_path,
) -> None:
    root = tmp_path / "runs"
    store, run = _seed_store(root)
    snapshot = _snapshot()
    original_catalog = _catalog(snapshot)
    MissionCompletionResolutionService(
        store=store,
        projection=_Projection(snapshot),  # type: ignore[arg-type]
        catalog=_Catalog(original_catalog),  # type: ignore[arg-type]
        proposer=_Proposer(_proposal(snapshot, original_catalog)),  # type: ignore[arg-type]
    ).resolve(
        mission_id=snapshot.mission_id,
        anchor_run_id=run.run_id,
        allow_inference=True,
    )

    changed_catalog = _catalog(snapshot, authority="9" * 64)
    restarted = MissionCompletionResolutionService(
        store=TaskRunStore(root=root),
        projection=_Projection(snapshot),  # type: ignore[arg-type]
        catalog=_Catalog(changed_catalog),  # type: ignore[arg-type]
        proposer=_RejectProposer(),  # type: ignore[arg-type]
    ).resolve(
        mission_id=snapshot.mission_id,
        allow_inference=False,
    )

    assert restarted.status == "unavailable"
    assert restarted.reason_codes == [
        "MISSION_COMPLETION_BINDING_PROPOSAL_NOT_PERSISTED"
    ]
    assert restarted.proposal_source == "none"
