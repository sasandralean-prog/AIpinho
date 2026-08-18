from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_context_item import FileContextItem
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.analysis.file_selection import FileSelectionRequest
from aipinho.services.analysis.file_selection_service import FileSelectionService
from aipinho.services.analysis.functionality_analyzer import FunctionalityAnalyzer
from aipinho.services.analysis.project_profile_service import ProjectProfileService


def test_kotlin_gradle_profile_detects_nested_sources_and_tests():
    tree = ProjectTreeSummary(
        workspace="workspace",
        status="ok",
        top_level=["build.gradle.kts", "settings.gradle.kts", "src"],
        candidate_files=[
            "build.gradle.kts",
            "settings.gradle.kts",
            "src/main/kotlin/example/App.kt",
            "src/test/kotlin/example/AppTest.kt",
        ],
    )

    service = ProjectProfileService()

    assert service.detect(tree) == ["kotlin_gradle"]
    assert "src/**/*.kt" in service.priority_patterns(tree)
    assert "src/test/**/*.kt" in service.test_patterns(tree)
    assert service.matching_paths(tree, service.test_patterns(tree)) == [
        "src/test/kotlin/example/AppTest.kt",
    ]


def test_functionality_analyzer_uses_declared_purpose_and_observed_ui_labels():
    context = FileContextBundle(
        bundle_id="bundle_test",
        workspace="workspace",
        status="ok",
        items=[
            FileContextItem(
                path="README.md",
                status="included",
                content=(
                    "# Sample Studio\n\n"
                    "A desktop application for organizing projects, experiments, notes and exports."
                ),
            ),
            FileContextItem(
                path="src/main/kotlin/example/App.kt",
                status="included",
                content='Text("Projects")\nButton(onClick = {}) { Text("Export JSON") }',
            ),
        ],
    )

    findings = FunctionalityAnalyzer().analyze(context)

    assert any(item.title == "Finalidade declarada do projeto" for item in findings)
    surface = next(item for item in findings if item.title == "Superficies funcionais observadas")
    assert "Projects" in surface.summary
    assert "Export JSON" in surface.summary
    assert surface.evidence_paths == ["src/main/kotlin/example/App.kt"]


def test_functionality_analyzer_extracts_semantic_code_evidence():
    context = FileContextBundle(
        bundle_id="bundle_semantic_test",
        workspace="workspace",
        status="ok",
        items=[
            FileContextItem(
                path="src/main/kotlin/example/audio/AdaptiveDecoder.kt",
                status="included",
                content="class AdaptiveDecoder { fun decode(codec: String, container: String) = codec }",
            ),
            FileContextItem(
                path="src/main/kotlin/example/audio/DesktopPlayer.kt",
                status="included",
                content="class DesktopPlayer { fun playback(track: String) = track }",
            ),
        ],
    )

    findings = FunctionalityAnalyzer().analyze(context)

    semantic_titles = {item.title for item in findings if item.category == "semantic_code_evidence"}
    assert "Evidencia semantica observada: decoding" in semantic_titles
    assert "Evidencia semantica observada: playback" in semantic_titles


def test_file_selection_uses_semantic_query_to_prioritize_relevant_files(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "build.gradle.kts").write_text("plugins {}\n", encoding="utf-8")
    source = workspace / "src" / "main" / "kotlin" / "example" / "audio"
    source.mkdir(parents=True)
    (source / "AdaptiveDecoder.kt").write_text("class AdaptiveDecoder\n", encoding="utf-8")
    (source / "Theme.kt").write_text("class Theme\n", encoding="utf-8")

    result = FileSelectionService().select_files(
        FileSelectionRequest(
            workspace=str(workspace),
            semantic_query="Analyze decoder codec container behavior",
            candidate_files=[
                "build.gradle.kts",
                "src/main/kotlin/example/audio/Theme.kt",
                "src/main/kotlin/example/audio/AdaptiveDecoder.kt",
            ],
            max_files=1,
        )
    )

    assert result.selected_files[0].path == "src/main/kotlin/example/audio/AdaptiveDecoder.kt"
