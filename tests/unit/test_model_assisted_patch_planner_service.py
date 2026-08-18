from __future__ import annotations

import json

from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_context_item import FileContextItem
from aipinho.schemas.roles.role_model_binding import RoleInferenceResult
from aipinho.services.patching.model_assisted_patch_planner_service import ModelAssistedPatchPlannerService

from patch_fixtures import patch_workspace


class FakeRoles:
    def __init__(self, output: str, *, status: str = "completed") -> None:
        self.output = output
        self.status = status
        self.requests = []

    def run(self, role_id, request):
        self.requests.append((role_id, request))
        return RoleInferenceResult(
            role_id=role_id,
            status=self.status,
            selected_model_id="fake-model",
            provider_id="fake-provider",
            output=self.output,
        )


def _bundle(workspace) -> FileContextBundle:
    path = workspace / "src" / "app.py"
    return FileContextBundle(
        bundle_id="bundle_test",
        workspace=str(workspace),
        status="ok",
        items=[FileContextItem(path=str(path), status="included", content=path.read_text(encoding="utf-8"))],
    )


def _relative_bundle(workspace) -> FileContextBundle:
    path = workspace / "src" / "app.py"
    return FileContextBundle(
        bundle_id="bundle_relative_test",
        workspace=str(workspace),
        status="ok",
        items=[FileContextItem(path="src/app.py", status="included", content=path.read_text(encoding="utf-8"))],
    )


def test_model_assisted_patch_planner_prefers_production_context_by_default(tmp_path):
    workspace = patch_workspace(tmp_path)
    main_path = workspace / "src" / "main" / "kotlin" / "Player.kt"
    test_path = workspace / "src" / "test" / "kotlin" / "PlayerTest.kt"
    main_path.parent.mkdir(parents=True)
    test_path.parent.mkdir(parents=True)
    main_path.write_text("fun play() = \"old\"\n", encoding="utf-8")
    test_path.write_text("fun testPlay() = assert(true)\n", encoding="utf-8")
    bundle = FileContextBundle(
        bundle_id="bundle_prod_preference",
        workspace=str(workspace),
        status="ok",
        items=[
            FileContextItem(path=str(test_path), status="included", content=test_path.read_text(encoding="utf-8")),
            FileContextItem(path=str(main_path), status="included", content=main_path.read_text(encoding="utf-8")),
        ],
    )
    output = json.dumps({"replacement": "fun play() = \"new\"\n", "rationale": "Update production behavior."})
    roles = FakeRoles(output)

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="Player.kt should return the new player behavior.",
        file_context_bundle=bundle,
    )

    assert result.status == "ready"
    assert roles.requests[0][1].context["patch_candidate"]["target_file"] == "src/main/kotlin/Player.kt"


def test_model_assisted_patch_planner_creates_governed_preview_without_writing(tmp_path):
    workspace = patch_workspace(tmp_path)
    before = (workspace / "src" / "app.py").read_text(encoding="utf-8")
    output = json.dumps(
        {
            "replacement": "print('new')\n",
            "rationale": "Replace the obsolete output.",
            "confidence": 0.8,
        }
    )
    roles = FakeRoles(output)
    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the printed old output with the new output.",
        file_context_bundle=_bundle(workspace),
    )

    assert result.status == "ready"
    assert result.plan is not None
    assert result.repair_proposal is not None
    assert result.plan.diff_proposal is not None
    assert result.plan.repair_proposal is not None
    assert result.plan.diff_proposal.diff.diff_text
    assert (workspace / "src" / "app.py").read_text(encoding="utf-8") == before
    assert roles.requests[0][0] == "patch_planner"
    assert "patch_candidate" in roles.requests[0][1].context
    assert roles.requests[0][1].context["patch_candidate"]["diagnosis_id"]
    assert roles.requests[0][1].context["patch_candidate"]["technical_context"]["repair_intent"]["expected_behavior"]
    assert result.plan.diagnosis_artifacts
    assert "files" not in roles.requests[0][1].context
    assert "proposal_scaffold" in roles.requests[0][1].context
    assert roles.requests[0][1].context["proposal_scaffold"]["target"]["file"] == "src/app.py"
    assert roles.requests[0][1].context["proposal_scaffold"]["assembly"]["status"] in {"partial", "complete"}
    assert result.repair_proposal.assembly.candidate_transformation.status in {"partial", "complete"}
    assert result.repair_proposal.concrete_change.success_criteria
    assert len(str(roles.requests[0][1].context)) < 8000


def test_model_assisted_patch_planner_rejects_empty_model_replacement(tmp_path):
    workspace = patch_workspace(tmp_path)
    roles = FakeRoles(json.dumps({"replacement": "", "rationale": "No concrete change."}))

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the printed old output with the new output.",
        file_context_bundle=_bundle(workspace),
    )

    assert result.status == "blocked"
    assert "PATCH_MODEL_EMPTY_OUTPUT" in result.blocked_reasons
    assert result.repair_proposal is not None
    assert result.repair_proposal.proposal_status == "partial"
    assert result.repair_proposal.proposal_completeness > 0
    assert result.repair_proposal.target.file == "src/app.py"
    assert result.repair_proposal.concrete_change.expected_behavior
    assert result.repair_proposal.assembly.candidate_transformation.status in {"partial", "complete"}
    assert "PROPOSAL_STRATEGY_MISSING" in result.blocked_reasons
    assert "repair_proposal_partial_from_patch_candidate" in result.repair_proposal.warnings


def test_model_assisted_patch_planner_accepts_structured_repair_proposal_without_compiler_replacement(tmp_path):
    workspace = patch_workspace(tmp_path)
    roles = FakeRoles(
        json.dumps(
            {
                "target": {
                    "workspace": str(workspace),
                    "file": "src/app.py",
                    "symbol": "src/app.py",
                    "symbol_kind": "file",
                },
                "intent": "repair obsolete output behavior",
                "concrete_change": {
                    "objective": "replace obsolete output semantics in the selected file",
                    "current_behavior": "print('old')",
                    "expected_behavior": "print the new runtime output instead of the obsolete output",
                    "modification_strategy": "replace the focused print statement with the updated output expression",
                    "affected_symbols": ["src/app.py"],
                    "reasoning": "The selected file is the minimal edit unit and the evidence is sufficient to define the desired behavior.",
                    "suggested_replacement": "",
                },
                "rollback": {
                    "possible": True,
                    "strategy": "restore the previous print statement if validation fails",
                    "affected_symbols": ["src/app.py"],
                    "side_effects": ["The obsolete output will return until a stronger proposal is available."],
                },
                "impact": {
                    "scope": "focused_edit_unit",
                    "affected_modules": ["src"],
                    "runtime_behavior": "output changes only in the selected file",
                    "compatibility": "preserve existing public contract and limit change to the selected file",
                    "risk_level": "medium",
                },
                "risks": {
                    "technical": ["The selected replacement still needs compiler reconciliation with adjacent code."],
                    "behavioral": ["The visible output changes and must be validated against a known-good run."],
                    "regression": ["Nearby tests may assert the previous string literal."],
                    "confidence": "medium",
                },
                "confidence": 0.7,
            }
        )
    )

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the printed old output with the new output.",
        file_context_bundle=_bundle(workspace),
    )

    assert result.status == "proposal_ready"
    assert result.plan is None
    assert result.repair_proposal is not None
    assert result.repair_proposal.concrete_change.suggested_replacement == ""
    assert "PATCH_MODEL_EMPTY_OUTPUT" in result.blocked_reasons


def test_model_assisted_patch_planner_accepts_relative_context_paths(tmp_path):
    workspace = patch_workspace(tmp_path)
    output = json.dumps(
        {
            "replacement": "print('relative')\n",
            "rationale": "Relative context paths are canonical workspace members.",
        }
    )

    result = ModelAssistedPatchPlannerService(roles=FakeRoles(output)).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the printed old output with the relative output.",
        file_context_bundle=_relative_bundle(workspace),
    )

    assert result.status == "ready"
    assert result.plan is not None
    assert result.plan.diff_proposal is not None
    assert result.plan.hunks


def test_model_assisted_patch_planner_compacts_large_evidence_for_role_budget(tmp_path):
    workspace = patch_workspace(tmp_path)
    output = json.dumps({"replacement": "print('budget-safe')\n", "rationale": "Budget-safe replacement."})
    roles = FakeRoles(output)
    evidence_context = [
        {
            "artifact_id": f"artifact_{index}",
            "logical_path": f"reports/example/{index}.md",
            "content": "large evidence " * 1000,
        }
        for index in range(12)
    ]

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the old output with the budget-safe output using prior evidence. " * 80,
        file_context_bundle=_bundle(workspace),
        evidence_context=evidence_context,
    )

    assert result.status == "ready"
    assert len(str(roles.requests[0][1].context)) < 8000
    assert "evidence_refs" in roles.requests[0][1].context
    assert "budget-safe output" in roles.requests[0][1].context["objective"]
    assert len(roles.requests[0][1].context["objective"]) < 800


def test_model_assisted_patch_planner_drops_operational_expected_behavior_from_diagnosis(tmp_path):
    workspace = patch_workspace(tmp_path)
    output = json.dumps({"replacement": "print('new')\n", "rationale": "Use bounded replacement."})
    roles = FakeRoles(output)
    evidence_context = [
        {
            "artifact_id": "artifact_runtime_diag",
            "logical_path": "reports/runtime/diagnosis.md",
            "content": "src/app.py raises IndexOutOfBoundsException when input is shorter than the expected header.",
        }
    ]

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective=(
            "Use prior evidence to generate reports/phase4_patch_plan.md, reports/patch_preview.md, "
            "rollback guidance, validation output, and completion status for src/app.py."
        ),
        file_context_bundle=_bundle(workspace),
        evidence_context=evidence_context,
    )

    assert result.status == "ready"
    patch_candidate = roles.requests[0][1].context["patch_candidate"]
    expected_behavior = patch_candidate["expected_behavior"].casefold()
    repair_intent = patch_candidate["technical_context"]["repair_intent"]
    assert "reports/" not in expected_behavior
    assert "patch_preview" not in expected_behavior
    assert "boundar" in expected_behavior
    assert repair_intent["expected_behavior"] == patch_candidate["expected_behavior"]


def test_model_assisted_patch_planner_selects_relevant_evidence_window(tmp_path):
    workspace = patch_workspace(tmp_path)
    output = json.dumps({"replacement": "print('targeted')\n", "rationale": "Use target evidence."})
    roles = FakeRoles(output)
    evidence_context = [
        {
            "artifact_id": "artifact_relevant",
            "logical_path": "reports/example/static_risk_matrix.md",
            "content": (
                "Introductory report header with generic metadata.\n" * 80
                + "Relevant finding: src/app.py contains obsolete behavior in app output.\n"
                + "The expected behavior requires replacing the printed value.\n"
            ),
        }
    ]

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the obsolete app output with the targeted output.",
        file_context_bundle=_bundle(workspace),
        evidence_context=evidence_context,
    )

    assert result.status == "ready"
    evidence = roles.requests[0][1].context["evidence"][0]["excerpt"]
    assert "src/app.py contains obsolete behavior" in evidence
    assert not evidence.startswith("Introductory report header")


def test_model_assisted_patch_planner_blocks_file_replacement_from_truncated_context(tmp_path):
    workspace = patch_workspace(tmp_path)
    path = workspace / "src" / "app.py"
    bundle = FileContextBundle(
        bundle_id="bundle_truncated",
        workspace=str(workspace),
        status="partial",
        items=[
            FileContextItem(
                path=str(path),
                status="included",
                content="print('old')\n",
                content_truncated=True,
            )
        ],
    )
    roles = FakeRoles(json.dumps({"replacement": "print('new')\n", "rationale": "Replace output."}))

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the printed old output with the new output.",
        file_context_bundle=bundle,
    )

    assert result.status == "blocked"
    assert "REPAIR_TASK_NOT_ACTIONABLE" in result.blocked_reasons
    assert "REPAIR_TASK_SNIPPET_INSUFFICIENT" in result.blocked_reasons
    assert result.repair_proposal is not None
    assert result.repair_proposal.proposal_status == "partial"
    assert result.repair_proposal.target.file == "src/app.py"
    assert roles.requests == []


def test_model_assisted_patch_planner_preserves_partial_repair_proposal_when_model_run_is_unavailable(tmp_path):
    workspace = patch_workspace(tmp_path)
    roles = FakeRoles("", status="blocked")

    result = ModelAssistedPatchPlannerService(roles=roles).create_plan(
        workspace=str(workspace),
        objective="src/app.py should replace the printed old output with the new output.",
        file_context_bundle=_bundle(workspace),
    )

    assert result.status == "blocked"
    assert "model_patch_proposal_unavailable" in result.blocked_reasons
    assert result.repair_proposal is not None
    assert result.repair_proposal.proposal_status == "partial"
    assert result.repair_proposal.proposal_completeness > 0
    assert result.metadata["repair_proposal"]["proposal_status"] == "partial"
