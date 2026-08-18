from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService


def test_observed_entity_compiler_creates_generic_file_entities(tmp_path):
    (tmp_path / "alpha.txt").write_text("hello", encoding="utf-8")
    service = ObservedEntityCompilationService(
        policy={
            "scan": {"max_entities": 20, "max_depth": 3},
            "attribute_aliases": {
                "name": ["name", "nome"],
                "extension": ["extension", "extensao"],
                "size_bytes": ["size", "tamanho"],
            },
        }
    )

    graph = service.compile(workspace=str(tmp_path), workspace_context={}, analysis_payload={})

    payload = graph.model_dump(mode="json")
    entities = [item for item in payload["entities"] if item["entity_kind"] == "file"]
    assert entities
    assert service.value_for_field(entities[0], "nome") == ("alpha.txt", True)
    assert service.value_for_field(entities[0], "extensao") == ("txt", True)
    assert service.value_for_field(entities[0], "tamanho")[1] is True


def test_schema_selection_prefers_entities_that_cover_declared_fields():
    service = ObservedEntityCompilationService(
        policy={
            "scan": {"max_entities": 20, "max_depth": 3},
            "attribute_aliases": {
                "name": ["name"],
                "extension": ["extension"],
                "severity": ["severity"],
            },
        }
    )
    graph = service.compile(
        workspace="missing-root",
        workspace_context={},
        analysis_payload={
            "findings": [
                {"severity": "info", "title": "Observed finding", "summary": "Finding summary"},
            ],
        },
    ).model_dump(mode="json")

    selected = service.select_entities_for_schema(graph, ["severity"])

    assert selected
    assert {item["entity_kind"] for item in selected} == {"finding"}


def test_entity_compilation_preserves_declared_library_root_under_project_budget(tmp_path):
    project = tmp_path / "app"
    library = tmp_path / "library"
    (project / "src").mkdir(parents=True)
    library.mkdir()
    for index in range(30):
        (project / "src" / f"Project{index}.txt").write_text("project", encoding="utf-8")
    for index in range(3):
        (library / f"Track{index}.dat").write_text("media", encoding="utf-8")
    service = ObservedEntityCompilationService(
        policy={
            "scan": {"max_entities": 20, "max_depth": 3},
            "root_role_policy": {
                "project_root_role": "project_root",
                "library_root_role": "library_root",
                "external_root_role": "external_root",
                "corpus_preferred_root_roles": ["library_root", "corpus_root"],
                "corpus_excluded_entity_roles": [
                    "project_source_file",
                    "build_output_file",
                    "cache_file",
                    "generated_file",
                ],
                "source_segments": ["src"],
            },
            "attribute_aliases": {
                "name": ["name"],
                "extension": ["extension"],
                "relative_path": ["relative_path"],
                "source_root_role": ["source_root_role"],
            },
        }
    )

    graph = service.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")

    assert graph["entities_by_root_role"]["library_root"] == 3
    assert graph["entities_by_root_role"]["project_root"] == 17
    assert graph["roots_scanned_by_role"]["library_root"] == [str(library.resolve(strict=False))]
    library_binding = next(item for item in graph["root_bindings"] if item["role"] == "library_root")
    assert library_binding["observation_allowed"] is True
    assert library_binding["mutation_allowed"] is False
    assert library_binding["policy_decision"]["policy_status"] == "allowed"
    assert library_binding["evidence_refs"]


def test_entity_compilation_blocks_missing_library_root_with_policy_reason(tmp_path):
    project = tmp_path / "app"
    library = tmp_path / "missing_library"
    project.mkdir()
    service = ObservedEntityCompilationService(
        policy={
            "scan": {"max_entities": 20, "max_depth": 3},
            "root_role_policy": {
                "project_root_role": "project_root",
                "library_root_role": "library_root",
                "external_root_role": "external_root",
                "corpus_preferred_root_roles": ["library_root", "corpus_root"],
            },
            "attribute_aliases": {"name": ["name"]},
        }
    )

    graph = service.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")

    library_binding = next(item for item in graph["root_bindings"] if item["role"] == "library_root")
    assert library_binding["observation_allowed"] is False
    assert library_binding["policy_decision"]["policy_status"] == "blocked"
    assert "CORPUS_ROOT_POLICY_BLOCKED" in library_binding["policy_decision"]["reason_codes"]
    assert any(gap["gap_type"] == "CORPUS_ROOT_POLICY_BLOCKED" for gap in graph["semantic_gaps"])


def test_contract_aware_tabular_renderer_uses_entity_graph_instead_of_findings(tmp_path):
    (tmp_path / "alpha.txt").write_text("hello", encoding="utf-8")
    runtime = ReadonlyAnalysisArtifactRuntimeService(
        observed_entities=ObservedEntityCompilationService(
            policy={
                "scan": {"max_entities": 20, "max_depth": 3},
                "attribute_aliases": {
                    "name": ["name", "nome"],
                    "extension": ["extension", "extensao"],
                    "size_bytes": ["size", "tamanho"],
                },
            }
        )
    )
    graph = runtime.observed_entities.compile(workspace=str(tmp_path)).model_dump(mode="json")

    render = runtime._contract_tabular_collection_content(
        expected_schema=["nome", "extensao", "tamanho"],
        analysis_payload={"observed_entity_graph": graph, "findings": [{"severity": "high"}]},
    )

    assert render.content.splitlines()[0] == "nome,extensao,tamanho"
    assert "alpha.txt,txt,5" in render.content
    assert render.semantic_gaps == []
    assert render.schema_coverage["status"] == "complete"


def test_contract_aware_tabular_renderer_reports_missing_attributes_without_fabricating(tmp_path):
    (tmp_path / "alpha.txt").write_text("hello", encoding="utf-8")
    runtime = ReadonlyAnalysisArtifactRuntimeService(
        observed_entities=ObservedEntityCompilationService(
            policy={
                "scan": {"max_entities": 20, "max_depth": 3},
                "attribute_aliases": {
                    "name": ["name", "nome"],
                    "extension": ["extension", "extensao"],
                },
            }
        )
    )
    graph = runtime.observed_entities.compile(workspace=str(tmp_path)).model_dump(mode="json")

    render = runtime._contract_tabular_collection_content(
        expected_schema=["nome", "extensao", "unobserved_attribute"],
        analysis_payload={"observed_entity_graph": graph},
    )

    assert render.content.splitlines()[0] == "nome,extensao,unobserved_attribute"
    assert "ATTRIBUTE_NOT_OBSERVED:unobserved_attribute" in {
        item["gap_type"] for item in render.semantic_gaps
    }
    assert render.schema_coverage["status"] == "partial"
