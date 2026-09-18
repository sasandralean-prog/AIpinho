from __future__ import annotations

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionBindingCandidate,
    MissionCompletionBindingProposal,
    MissionCompletionEvidenceCatalog,
    MissionCompletionEvidenceItem,
    MissionCompletionSnapshot,
)
from aipinho.services.runtime.mission_completion_binding_compiler import (
    MissionCompletionBindingCompiler,
)
from aipinho.services.runtime.mission_completion_facet_service import (
    MissionCompletionFacetService,
)


def _snapshot(*, allow_limited=False):
    return MissionCompletionSnapshot(
        mission_id="mission_compile",
        status="ready",
        semantic_context={"intent_type": "workspace_fix_request"},
        completion_requirements=["validated_change"],
        validation_requirements=["tests_pass"],
        allow_limited_completion=allow_limited,
        task_run_ids=["task_run_a", "task_run_b"],
        terminal_task_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_authority_sha256s=["a" * 64, "b" * 64],
        evidence_refs=["artifact:patch", "evidence:tests"],
        authority_sha256="c" * 64,
    )


def _item(
    ref,
    producer,
    *,
    phase,
    authority,
    safe=True,
    result_status="completed",
    runtime_truth_status="completed",
    dependency_status="satisfied",
    limitations=None,
    missing_truth=None,
    truth_claim=True,
):
    return MissionCompletionEvidenceItem(
        evidence_ref=ref,
        producer_task_run_id=producer,
        phase_id=phase,
        phase_outcome_authority_sha256=authority,
        runtime_status="completed",
        result_status=result_status,
        runtime_truth_status=runtime_truth_status,
        runtime_truth_safe_to_report_success=safe,
        phase_dependency_status=dependency_status,
        limitations=list(limitations or []),
        missing_truth=list(missing_truth or []),
        use_safety={"safe_for_truth_claim": truth_claim},
    )


def _catalog(snapshot, *, patch=None, tests=None):
    return MissionCompletionEvidenceCatalog(
        mission_id=snapshot.mission_id,
        snapshot_authority_sha256=snapshot.authority_sha256,
        items=[
            patch
            or _item(
                "artifact:patch",
                "task_run_a",
                phase="implementation",
                authority="a" * 64,
            ),
            tests
            or _item(
                "evidence:tests",
                "task_run_b",
                phase="validation",
                authority="b" * 64,
            ),
        ],
        authority_sha256="d" * 64,
    )


def _binding(
    requirement,
    *,
    kind,
    ref,
    producer,
    relation="supports",
    confidence=0.9,
):
    return MissionCompletionBindingCandidate(
        requirement=requirement,
        requirement_kind=kind,
        semantic_relation=relation,
        evidence_refs=[ref] if ref else [],
        producer_task_run_ids=[producer] if producer else [],
        confidence=confidence,
        rationale="semantic match candidate",
    )


def _proposal(snapshot, catalog, bindings):
    return MissionCompletionBindingProposal(
        mission_id=snapshot.mission_id,
        snapshot_authority_sha256=snapshot.authority_sha256,
        catalog_authority_sha256=catalog.authority_sha256,
        status="candidate",
        reason_code="MISSION_COMPLETION_BINDING_CANDIDATE_PROPOSED",
        bindings=list(bindings),
        proposal_sha256="e" * 64,
    )


def _all_bindings():
    return [
        _binding(
            "validated_change",
            kind="completion",
            ref="artifact:patch",
            producer="task_run_a",
        ),
        _binding(
            "tests_pass",
            kind="validation",
            ref="evidence:tests",
            producer="task_run_b",
        ),
    ]


def test_safe_canonical_evidence_compiles_satisfied_and_facet_ready() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    proposal = _proposal(snapshot, catalog, _all_bindings())

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )
    facet = MissionCompletionFacetService().evaluate(
        snapshot,
        evaluations=compilation.evaluations,
    )

    assert compilation.status == "compiled"
    assert [row.status for row in compilation.evaluations] == [
        "satisfied",
        "satisfied",
    ]
    assert facet.status == "ready"
    assert facet.safe_to_report_success is True


def test_model_support_relation_cannot_promote_unsafe_truth() -> None:
    snapshot = _snapshot()
    catalog = _catalog(
        snapshot,
        patch=_item(
            "artifact:patch",
            "task_run_a",
            phase="implementation",
            authority="a" * 64,
            safe=False,
            truth_claim=False,
        ),
    )
    proposal = _proposal(snapshot, catalog, _all_bindings())

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )

    completion = next(
        row
        for row in compilation.evaluations
        if row.requirement == "validated_change"
    )
    assert completion.status == "unsatisfied"
    assert completion.reason_codes == [
        "MISSION_COMPLETION_CANONICAL_EVIDENCE_UNSAFE"
    ]


def test_blocked_runtime_truth_stays_blocked() -> None:
    snapshot = _snapshot()
    catalog = _catalog(
        snapshot,
        tests=_item(
            "evidence:tests",
            "task_run_b",
            phase="validation",
            authority="b" * 64,
            safe=False,
            runtime_truth_status="blocked",
            dependency_status="blocked",
        ),
    )
    proposal = _proposal(snapshot, catalog, _all_bindings())

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )

    validation = next(
        row
        for row in compilation.evaluations
        if row.requirement == "tests_pass"
    )
    assert validation.status == "blocked"


def test_safe_limited_evidence_compiles_limited_not_full_success() -> None:
    snapshot = _snapshot(allow_limited=True)
    catalog = _catalog(
        snapshot,
        patch=_item(
            "artifact:patch",
            "task_run_a",
            phase="implementation",
            authority="a" * 64,
            limitations=["patch_validation_limited"],
        ),
    )
    proposal = _proposal(snapshot, catalog, _all_bindings())

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )
    facet = MissionCompletionFacetService().evaluate(
        snapshot,
        evaluations=compilation.evaluations,
    )

    completion = next(
        row
        for row in compilation.evaluations
        if row.requirement == "validated_change"
    )
    assert completion.status == "satisfied_with_limitations"
    assert "patch_validation_limited" in completion.limitations
    assert facet.status == "constrained"


def test_low_confidence_support_remains_unsatisfied() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    rows = _all_bindings()
    rows[0] = _binding(
        "validated_change",
        kind="completion",
        ref="artifact:patch",
        producer="task_run_a",
        confidence=0.4,
    )
    proposal = _proposal(snapshot, catalog, rows)

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )

    completion = next(
        row
        for row in compilation.evaluations
        if row.requirement == "validated_change"
    )
    assert completion.status == "unsatisfied"
    assert completion.reason_codes == [
        "MISSION_COMPLETION_BINDING_CONFIDENCE_INSUFFICIENT"
    ]


def test_fabricated_evidence_ref_blocks_compilation() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    rows = _all_bindings()
    rows[0] = _binding(
        "validated_change",
        kind="completion",
        ref="artifact:forged",
        producer="task_run_a",
    )
    proposal = _proposal(snapshot, catalog, rows)

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )

    assert compilation.status == "blocked"
    assert (
        "MISSION_COMPLETION_BINDING_EVIDENCE_UNKNOWN:artifact:forged"
        in compilation.reason_codes
    )
    assert compilation.evaluations == []


def test_ref_producer_mismatch_blocks_compilation() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    rows = _all_bindings()
    rows[0] = _binding(
        "validated_change",
        kind="completion",
        ref="artifact:patch",
        producer="task_run_b",
    )
    proposal = _proposal(snapshot, catalog, rows)

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )

    assert compilation.status == "blocked"
    assert (
        "MISSION_COMPLETION_BINDING_REF_PRODUCER_MISMATCH:artifact:patch"
        in compilation.reason_codes
    )


def test_ambiguous_binding_with_unknown_ref_is_still_rejected() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    proposal = _proposal(
        snapshot,
        catalog,
        [
            _binding(
                "validated_change",
                kind="completion",
                ref="artifact:invented",
                producer="task_run_a",
                relation="ambiguous",
            )
        ],
    )

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )

    assert compilation.status == "blocked"
    assert (
        "MISSION_COMPLETION_BINDING_EVIDENCE_UNKNOWN:artifact:invented"
        in compilation.reason_codes
    )


def test_missing_semantic_support_compiles_unsatisfied_not_success() -> None:
    snapshot = _snapshot()
    catalog = _catalog(snapshot)
    proposal = _proposal(
        snapshot,
        catalog,
        [
            _binding(
                "validated_change",
                kind="completion",
                ref=None,
                producer=None,
                relation="does_not_support",
            )
        ],
    )

    compilation = MissionCompletionBindingCompiler().compile(
        snapshot,
        catalog,
        proposal,
    )

    assert compilation.status == "compiled"
    assert all(
        row.status == "unsatisfied"
        for row in compilation.evaluations
    )
