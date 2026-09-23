from __future__ import annotations

from types import SimpleNamespace

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.evidence_repair_semantic_service import (
    EvidenceRepairSemanticService,
)


def _run(*, focus_paths: list[str] | None = None):
    repair = {
        "required": bool(focus_paths),
        "focus_paths": list(focus_paths or []),
    }
    return SimpleNamespace(
        intent_map={
            "mission_continuation": {
                "evidence_repair": repair,
            }
        }
    )


def _analysis_result(
    *,
    included: list[tuple[str, bool]],
    status: str = "partial",
    safe_to_continue: bool = True,
    violations: list[str] | None = None,
):
    return SimpleNamespace(
        status=status,
        safe_to_continue=safe_to_continue,
        warnings=[],
        limitations=[],
        violations=list(violations or []),
        file_context=SimpleNamespace(
            items=[
                SimpleNamespace(
                    path=path,
                    status="included",
                    content_truncated=truncated,
                )
                for path, truncated in included
            ]
        ),
    )


def test_specialized_readonly_request_consumes_bounded_repair_focus() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    run = _run(focus_paths=["src/A.kt", "src/B.kt"])

    request = service._project_analysis_request(
        run=run,
        workspace=r"C:\workspace\target",
        analysis_prompt="Inspect project",
        request_context={"readonly_flags": {"workspace": True}},
    )

    assert request.goal == "evidence_repair_analysis"
    assert request.focus_paths == ["src/A.kt", "src/B.kt"]
    assert request.max_files == 40
    assert request.max_total_bytes == 700000
    assert "Evidence repair" in request.prompt


def test_specialized_readonly_request_keeps_normal_analysis_unmodified() -> None:
    service = ReadonlyAnalysisArtifactRuntimeService()
    run = _run(focus_paths=[])

    request = service._project_analysis_request(
        run=run,
        workspace=r"C:\workspace\target",
        analysis_prompt="Inspect project",
        request_context={},
    )

    assert request.goal == "readonly_analysis_with_artifact_output"
    assert request.focus_paths == []
    assert request.max_files is None
    assert request.max_total_bytes is None
    assert request.prompt == "Inspect project"


def test_repair_semantics_promote_destructive_safety_only_after_full_focus() -> None:
    result = _analysis_result(
        included=[
            ("src/A.kt", False),
            ("src/B.kt", False),
        ],
    )

    semantic = EvidenceRepairSemanticService.project_analysis_outcome(
        result,
        repair={
            "required": True,
            "focus_paths": ["src/A.kt", "src/B.kt"],
        },
    )

    assert semantic["use_safety"]["safe_for_destructive_action"] is True
    assert semantic["semantic_properties"][
        "evidence_repair_focus_complete"
    ] is True
    assert semantic["semantic_properties"][
        "evidence_repair_unresolved_paths"
    ] == []


def test_repair_semantics_preserve_exact_unresolved_focus_fail_closed() -> None:
    result = _analysis_result(
        included=[
            ("src/A.kt", False),
            ("src/B.kt", True),
        ],
    )

    semantic = EvidenceRepairSemanticService.project_analysis_outcome(
        result,
        repair={
            "required": True,
            "focus_paths": ["src/A.kt", "src/B.kt", "src/C.kt"],
        },
    )

    assert semantic["use_safety"]["safe_for_destructive_action"] is False
    assert semantic["semantic_properties"][
        "evidence_repair_focus_complete"
    ] is False
    assert semantic["semantic_properties"][
        "evidence_repair_unresolved_paths"
    ] == ["src/B.kt", "src/C.kt"]
    assert "evidence_repair_focus_unresolved" in semantic["limitations"]


def test_repair_semantics_do_not_promote_when_analysis_truth_is_missing() -> None:
    result = _analysis_result(
        included=[("src/A.kt", False)],
        status="ok",
        safe_to_continue=True,
        violations=["analysis_truth_missing"],
    )

    semantic = EvidenceRepairSemanticService.project_analysis_outcome(
        result,
        repair={
            "required": True,
            "focus_paths": ["src/A.kt"],
        },
    )

    assert semantic["use_safety"]["safe_for_destructive_action"] is False
    assert semantic["semantic_properties"][
        "evidence_repair_focus_complete"
    ] is False
    assert semantic["missing_truth"] == ["analysis_truth_missing"]
