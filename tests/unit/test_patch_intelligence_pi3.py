from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers.patch_intelligence_router import router
from aipinho.schemas.patch_intelligence import IntelligentPatchProposal, IntelligentPatchProposalRequest
from aipinho.services.patch_intelligence_service import IntelligentPatchProposalService, PatchProposalSerializer, PatchProposalValidator


def _doctor_payload():
    return {
        "matrix": {
            "rows": [
                {"category": "Intent", "status": "FAIL", "severity": "high", "reason_code": "intent_regression"},
            ]
        },
        "findings": [
            {
                "category": "Intent",
                "reason_code": "intent_regression",
                "suspected_modules": ["semantic_runtime", "runtime_dispatcher"],
            }
        ],
    }


def _patch_plan_payload():
    return {
        "patch_plan_id": "runtime_patch_plan_test",
        "affected_modules": ["services/runtime"],
        "tests": ["intent_precedence_tests"],
        "rollback": ["Revert focused intent precedence change if Runtime Doctor does not improve."],
    }


def test_patch_proposal_reuses_knowledge_base_and_pattern_engine():
    result = IntelligentPatchProposalService().create(
        IntelligentPatchProposalRequest(
            doctor_report=_doctor_payload(),
            regression_matrix=_doctor_payload()["matrix"],
            patch_plan=_patch_plan_payload(),
        )
    )

    proposal = result.proposal
    assert result.valid is True
    assert proposal.executor_independent is True
    assert proposal.generates_code is False
    assert proposal.generates_apply_patch is False
    assert proposal.modifies_runtime is False
    assert "patch_knowledge_intent_regression" in proposal.knowledge_entry_ids
    assert proposal.patterns_used
    assert "intent_regression" in proposal.regressions_covered
    assert "semantic_runtime" in proposal.modules_candidates
    assert "intent_precedence_tests" in proposal.tests_required


def test_patch_proposal_validation_blocks_executor_coupled_or_code_generating_proposals():
    proposal = IntelligentPatchProposal(
        regressions_covered=["intent_regression"],
        patterns_used=["pattern"],
        modules_candidates=["semantic_runtime"],
        files_candidates=["services/semantic_runtime"],
        justification="test",
        suggested_strategy="test",
        tests_required=["test"],
        executor_independent=False,
        generates_code=True,
        generates_apply_patch=True,
        modifies_runtime=True,
    )

    errors = PatchProposalValidator().validate(proposal)

    assert "proposal_must_not_generate_code" in errors
    assert "proposal_must_not_generate_apply_patch" in errors
    assert "proposal_must_not_modify_runtime" in errors
    assert "proposal_must_be_executor_independent" in errors


def test_patch_proposal_rejects_absolute_project_paths():
    try:
        IntelligentPatchProposal(
            regressions_covered=["intent_regression"],
            patterns_used=["pattern"],
            modules_candidates=[r"C:\Dev\AIpinho"],
            files_candidates=[],
            justification="bad",
            suggested_strategy="bad",
            tests_required=["test"],
        )
    except ValueError as exc:
        assert "intelligent_patch_proposal_must_not_contain_absolute" in str(exc)
    else:
        raise AssertionError("absolute path should be rejected")


def test_patch_proposal_serializer_roundtrip():
    result = IntelligentPatchProposalService().create(
        IntelligentPatchProposalRequest(
            doctor_report=_doctor_payload(),
            regression_matrix=_doctor_payload()["matrix"],
        )
    )
    serializer = PatchProposalSerializer()

    restored = serializer.from_json(serializer.to_json(result.proposal))

    assert restored.proposal_id == result.proposal.proposal_id
    assert restored.knowledge_entry_ids == result.proposal.knowledge_entry_ids


def test_patch_proposal_router_create_and_get():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    created = client.post(
        "/api/v1/runtime/patch-intelligence/proposal",
        json={
            "doctor_report": _doctor_payload(),
            "regression_matrix": _doctor_payload()["matrix"],
            "patch_plan": _patch_plan_payload(),
        },
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["valid"] is True
    proposal_id = payload["proposal"]["proposal_id"]

    fetched = client.get(f"/api/v1/runtime/patch-intelligence/proposal/{proposal_id}")
    assert fetched.status_code == 200
    assert fetched.json()["proposal_id"] == proposal_id
