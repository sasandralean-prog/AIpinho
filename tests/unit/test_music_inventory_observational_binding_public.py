from pathlib import Path

from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    GovernedPhase1Block,
    Phase1RuntimeBudget,
    ReadonlyAnalysisArtifactRuntimeService,
)


MEDIA_FIELDS = [
    "entity_id",
    "source_root_role",
    "relative_path",
    "filename",
    "extension",
    "media_type",
    "metadata_status",
    "evidence_ref",
    "limitations",
    "validation_status",
]


def test_public_prompt_projects_declared_library_root_into_workspace_context(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    request = type(
        "Request",
        (),
        {
            "workspace_context": {},
            "message": f"Projeto:\n{project}\n\nBiblioteca de midia:\n{library}\n",
        },
    )()

    context = ReadonlyAnalysisArtifactRuntimeService()._request_workspace_context(request)

    assert context["project_root"] == str(project.resolve(strict=False))
    assert context["library_roots"] == [str(library.resolve(strict=False))]
    assert context["readonly_flags"][str(project.resolve(strict=False))] is True
    assert context["readonly_flags"][str(library.resolve(strict=False))] is True


def test_public_structured_library_root_alias_is_preserved_for_selection(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    request = type(
        "Request",
        (),
        {
            "workspace_context": {
                "project_root": str(project),
                "library_root": str(library),
                "external_roots": [str(library)],
            },
            "message": "Generate a governed music inventory for Phase 1.",
        },
    )()

    context = ReadonlyAnalysisArtifactRuntimeService()._request_workspace_context(request)

    assert context["project_root"] == str(project)
    assert context["library_roots"] == [str(library)]
    assert context["external_roots"] == [str(library)]


def test_music_inventory_render_binds_library_entities_before_budget_window(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    (project / "src").mkdir(parents=True)
    library.mkdir()
    for index in range(8):
        (project / "src" / f"Project{index}.any").write_text("project", encoding="utf-8")
    for index in range(3):
        (library / f"Track{index}.any").write_text("media", encoding="utf-8")
    observed = ObservedEntityCompilationService()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    runtime = ReadonlyAnalysisArtifactRuntimeService(
        observed_entities=observed,
        budget=Phase1RuntimeBudget(max_artifact_entities=2, allow_partial_artifact=False),
    )

    render = runtime._contract_tabular_collection_content(
        expected_schema=MEDIA_FIELDS,
        request_text="Inventariar a biblioteca de audio com evidencias.",
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "contract_id": "media_corpus_inventory_artifact",
            "expected_kind": "tabular_collection",
            "expected_schema": MEDIA_FIELDS,
            "workspace_context": {"project_root": str(project), "library_roots": [str(library)]},
        },
    )

    lines = render.content.splitlines()
    assert len(lines) == 3
    assert "Track" in render.content
    assert "Project" not in render.content
    assert render.expected_rows == 3
    assert render.selected_rows == 2
    assert render.bound_rows == 2
    assert render.evidence_ref_count == 2
    selection = render.entity_summary["semantic_entity_selection"]
    assert selection["root_roles_selected"] == {"library_root": 2}
    assert selection["rejection_reasons"]["ROOT_ROLE_NOT_ALLOWED"] >= 1


def test_unsupported_media_source_blocks_before_fake_metadata_render(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    (library / "Track.any").write_text("media", encoding="utf-8")
    observed = ObservedEntityCompilationService()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    runtime = ReadonlyAnalysisArtifactRuntimeService(observed_entities=observed)
    contract = runtime.artifact_semantic_contracts.compile_contract(
        logical_path="reports/media/music_inventory.csv",
        content_type="text/csv",
    )
    contract["workspace_context"] = {"project_root": str(project), "library_roots": [str(library)]}

    try:
        runtime._contract_tabular_collection_content(
            expected_schema=contract["expected_schema"],
            request_text="Inventariar a biblioteca de audio com evidencias.",
            analysis_payload={"observed_entity_graph": graph},
            declared_contract=contract,
        )
    except GovernedPhase1Block as exc:
        telemetry = exc.details["post_compile_observation_execution"]
        assert exc.reason_code == "POST_COMPILE_TARGET_SELECTION_NO_ELIGIBLE_MEDIA_CANDIDATES"
        assert telemetry["groups_created_count"] == 0
        assert telemetry["capability_inapplicable_reasons"] == {"MEDIA_CAPABILITY_EXTENSION_NOT_DECLARED_BY_BACKENDS": 11}
    else:  # pragma: no cover - defensive assertion for the old unsafe path
        raise AssertionError("Unsupported media source should not render fake metadata.")
