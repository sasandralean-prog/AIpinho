from aipinho.services.artifacts.artifact_semantic_contract_service import ArtifactSemanticContractService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)


def test_patch_preview_is_derived_from_structured_repair_proposal_without_diff() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()

    content = service._patch_preview_content(
        logical_path="reports/firetest5/patch_preview.md",
        run_id="task_run_test",
        workspace=r"C:\Workspace",
        workspace_context={"project_root": r"C:\Workspace"},
        phase_id="phase_4",
        analysis_payload={
            "summary": "phase 4",
            "patch_planning": {
                "status": "proposal_ready",
                "repair_proposal": {
                    "proposal_id": "repair_proposal_123",
                    "intent": "repair obsolete output behavior",
                    "target": {
                        "workspace": r"C:\Workspace",
                        "file": "src/app.py",
                        "symbol": "src/app.py",
                        "symbol_kind": "file",
                    },
                    "concrete_change": {
                        "objective": "replace obsolete output semantics in the selected file",
                        "current_behavior": "print('old')",
                        "expected_behavior": "print the new runtime output instead of the obsolete output",
                        "behavior_summary": "Replace the obsolete output path in the selected file.",
                        "modification_strategy": "replace the focused print statement with the updated output expression",
                        "affected_symbols": ["src/app.py"],
                        "constraints": ["Preserve the public file contract."],
                        "invariants": ["Keep the edit scoped to src/app.py."],
                        "success_criteria": ["The selected file no longer prints the obsolete output."],
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
                    "field_origins": {
                        "target": ["technical_localization"],
                        "concrete_change": ["repair_task", "candidate_transformation"],
                    },
                    "assembly": {
                        "assembly_status": "complete",
                        "assembly_score": 0.95,
                        "semantic_evidence": {"status": "complete", "coverage_score": 90},
                        "behavior_localization": {"status": "complete", "coverage_score": 95},
                        "behavior_justification": {"status": "complete", "coverage_score": 95},
                        "candidate_transformation": {"status": "complete", "coverage_score": 100},
                    },
                },
            },
        },
        dependency_check={"artifacts": [], "missing": [], "status": "passed"},
    )

    validation = ArtifactSemanticContractService().validate(
        logical_path="reports/firetest5/patch_preview.md",
        content=content,
    )

    assert "## Repair Proposal" in content
    assert "## Concrete Change Preview" in content
    assert "## Proposal Assembly" in content
    assert "## Field Origins" in content
    assert "## Impact" in content
    assert "## Risks" in content
    assert "## Rollback" in content
    assert validation.status == "passed"


def test_patch_preview_keeps_partial_repair_proposal_visible_when_components_are_missing() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()

    content = service._patch_preview_content(
        logical_path="reports/firetest5/patch_preview.md",
        run_id="task_run_test",
        workspace=r"C:\Workspace",
        workspace_context={"project_root": r"C:\Workspace"},
        phase_id="phase_4",
        analysis_payload={
            "summary": "phase 4",
            "patch_planning": {
                "status": "blocked",
                "repair_proposal": {
                    "proposal_id": "repair_proposal_partial",
                    "proposal_status": "partial",
                    "proposal_completeness": 0.5,
                    "intent": "repair obsolete output behavior",
                    "target": {
                        "workspace": r"C:\Workspace",
                        "file": "src/app.py",
                        "symbol": "src/app.py",
                        "symbol_kind": "file",
                    },
                    "concrete_change": {
                        "objective": "replace obsolete output semantics in the selected file",
                        "current_behavior": "print('old')",
                        "expected_behavior": "print the new runtime output instead of the obsolete output",
                        "behavior_summary": "Replace the obsolete output path in the selected file.",
                        "modification_strategy": "",
                        "affected_symbols": ["src/app.py"],
                        "constraints": [],
                        "invariants": [],
                        "success_criteria": [],
                        "reasoning": "",
                        "suggested_replacement": "",
                    },
                    "rollback": {
                        "possible": False,
                        "strategy": "",
                        "affected_symbols": [],
                        "side_effects": [],
                    },
                    "impact": {
                        "scope": "",
                        "affected_modules": [],
                        "runtime_behavior": "",
                        "compatibility": "",
                        "risk_level": "",
                    },
                    "risks": {
                        "technical": [],
                        "behavioral": [],
                        "regression": [],
                        "confidence": "",
                    },
                        "components": {
                            "target": {"status": "complete", "reason_codes": [], "diagnostics": []},
                            "behavior": {"status": "complete", "reason_codes": [], "diagnostics": []},
                            "strategy": {"status": "partial", "reason_codes": ["PROPOSAL_STRATEGY_MISSING"], "diagnostics": ["strategy:missing_fields"]},
                            "impact": {"status": "missing", "reason_codes": ["PROPOSAL_IMPACT_MISSING"], "diagnostics": ["impact:missing_fields"]},
                            "rollback": {"status": "missing", "reason_codes": ["PROPOSAL_ROLLBACK_MISSING"], "diagnostics": ["rollback:missing_fields"]},
                            "confidence": {"status": "missing", "reason_codes": ["PROPOSAL_RISK_MISSING"], "diagnostics": ["confidence:missing_fields"]},
                        },
                        "assembly": {
                            "assembly_status": "partial",
                            "assembly_score": 0.75,
                            "semantic_evidence": {"status": "complete", "coverage_score": 90},
                            "behavior_localization": {"status": "complete", "coverage_score": 90},
                            "behavior_justification": {"status": "partial", "coverage_score": 70, "reason_codes": ["BEHAVIOR_JUSTIFICATION_MISSING"]},
                            "candidate_transformation": {"status": "missing", "coverage_score": 0, "reason_codes": ["TRANSFORMATION_MISSING"]},
                        },
                        "field_origins": {
                            "target": ["technical_localization"],
                            "impact": ["patch_candidate"],
                        },
                    },
                },
            },
        dependency_check={"artifacts": [], "missing": [], "status": "passed"},
    )

    validation = ArtifactSemanticContractService().validate(
        logical_path="reports/firetest5/patch_preview.md",
        content=content,
    )

    assert "proposal_status: partial" in content
    assert "proposal_completeness: 0.5" in content
    assert "- target: complete" in content
    assert "- strategy: partial" in content
    assert "- impact: missing" in content
    assert "- semantic_evidence: complete" in content
    assert "- candidate_transformation: missing" in content
    assert "## Field Origins" in content
    assert "Repair proposal not available because the canonical patch pipeline has not produced a governed proposal or compiler preview." not in content
    assert validation.status == "blocked"
    assert "PROPOSAL_CONCRETE_CHANGE_MISSING" in validation.missing_requirements
    assert "PROPOSAL_IMPACT_MISSING" in validation.missing_requirements


def test_patch_preview_can_render_repair_proposal_from_planning_metadata() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()

    content = service._patch_preview_content(
        logical_path="reports/firetest5/patch_preview.md",
        run_id="task_run_test",
        workspace=r"C:\Workspace",
        workspace_context={"project_root": r"C:\Workspace"},
        phase_id="phase_4",
        analysis_payload={
            "summary": "phase 4",
            "patch_planning": {
                "status": "blocked",
                "metadata": {
                    "repair_proposal": {
                        "proposal_id": "repair_proposal_meta",
                        "proposal_status": "partial",
                        "proposal_completeness": 0.5,
                        "intent": "repair obsolete output behavior",
                        "target": {
                            "workspace": r"C:\Workspace",
                            "file": "src/app.py",
                            "symbol": "src/app.py",
                            "symbol_kind": "file",
                        },
                        "concrete_change": {
                            "objective": "replace obsolete output semantics in the selected file",
                            "current_behavior": "print('old')",
                            "expected_behavior": "print the new runtime output instead of the obsolete output",
                            "behavior_summary": "Replace the obsolete output path in the selected file.",
                            "modification_strategy": "",
                            "affected_symbols": ["src/app.py"],
                            "constraints": [],
                            "invariants": [],
                            "success_criteria": [],
                            "reasoning": "",
                            "suggested_replacement": "",
                        },
                    }
                },
            },
        },
        dependency_check={"artifacts": [], "missing": [], "status": "passed"},
    )

    assert "proposal_id: repair_proposal_meta" in content
    assert "proposal_status: partial" in content
