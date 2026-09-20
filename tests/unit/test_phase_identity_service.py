from types import SimpleNamespace

from aipinho.services.runtime.phase_identity_service import PhaseIdentityService


def test_phase_identity_accepts_structured_ingress_aliases() -> None:
    phases = PhaseIdentityService()

    assert phases.from_mapping({"mission_phase": "discovery"}) == "discovery"
    assert phases.from_mapping({"phase_id": "validation"}) == "validation"


def test_phase_identity_prefers_materialized_taskrun_phase() -> None:
    run = SimpleNamespace(
        current_phase="materialized_phase",
        intent_map={
            "phase_id": "stale_phase",
            "mission_phase": "stale_mission_phase",
        },
        bootstrap_context={"phase_id": "stale_bootstrap_phase"},
        workflow=SimpleNamespace(current_phase="stale_workflow_phase"),
    )

    assert PhaseIdentityService().from_run(run) == "materialized_phase"
