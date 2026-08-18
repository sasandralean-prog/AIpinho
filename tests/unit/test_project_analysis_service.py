from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_analysis_budget import ProjectAnalysisBudget
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_selection import FileSelectionCandidate, FileSelectionResult
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
import time


class SlowRootScanTree:
    def build_tree_summary(self, request, *, progress=None):
        if progress:
            progress("before_path_resolution", {"workspace": request.workspace})
            progress("after_path_resolution", {"current_root": request.workspace})
            time.sleep(0.02)
            progress("before_workspace_root_scan", {"current_root": request.workspace})
        return ProjectTreeSummary(workspace=request.workspace, status="ok")

    def status(self):
        return {"status": "ok"}


class SlowEnumerationTree:
    def build_tree_summary(self, request, *, progress=None):
        if progress:
            progress("before_path_resolution", {"workspace": request.workspace})
            progress("after_path_resolution", {"current_root": request.workspace})
            progress("before_workspace_root_scan", {"current_root": request.workspace})
            progress("after_workspace_root_scan", {"current_root": request.workspace})
            time.sleep(0.02)
            progress("during_file_enumeration", {"files_scan_attempted": 1, "current_path_sample": "src/App.kt"})
        return ProjectTreeSummary(workspace=request.workspace, status="ok", total_files_seen=1, candidate_files=["src/App.kt"])

    def status(self):
        return {"status": "ok"}


class OneFileTree:
    def build_tree_summary(self, request, *, progress=None):
        if progress:
            progress("before_path_resolution", {"workspace": request.workspace})
            progress("after_path_resolution", {"current_root": request.workspace})
            progress("before_workspace_root_scan", {"current_root": request.workspace})
            progress("after_workspace_root_scan", {"current_root": request.workspace})
            progress("after_file_enumeration", {"files_scan_attempted": 1, "files_scanned": 1, "files_discovered": 1})
        return ProjectTreeSummary(workspace=request.workspace, status="ok", total_files_seen=1, candidate_files=["src/App.kt"])

    def status(self):
        return {"status": "ok"}


class ZeroProgressTree:
    def build_tree_summary(self, request, *, progress=None):
        if progress:
            progress("before_path_resolution", {"workspace": request.workspace})
            progress("after_path_resolution", {"current_root": request.workspace})
            progress("before_workspace_root_scan", {"current_root": request.workspace})
            progress("after_workspace_root_scan", {"current_root": request.workspace})
            progress("after_file_enumeration", {"files_scan_attempted": 0, "files_scanned": 0, "files_discovered": 0})
        return ProjectTreeSummary(workspace=request.workspace, status="ok", total_files_seen=0, candidate_files=[])

    def status(self):
        return {"status": "ok"}


class OneFileSelection:
    def select_files(self, request, *, project_tree=None):
        return FileSelectionResult(
            status="ok",
            selected_files=[FileSelectionCandidate(path="src/App.kt", score=10, reason="test", size_bytes=10)],
        )

    def status(self):
        return {"status": "ok"}


class SlowOneFileSelection:
    def select_files(self, request, *, project_tree=None, progress=None):
        time.sleep(0.2)
        return FileSelectionResult(
            status="ok",
            selected_files=[FileSelectionCandidate(path="src/App.kt", score=10, reason="test", size_bytes=10)],
        )

    def status(self):
        return {"status": "ok"}


class BudgetExceededOneFileSelection:
    def select_files(self, request, *, project_tree=None, progress=None):
        return FileSelectionResult(
            status="partial",
            selected_files=[FileSelectionCandidate(path="src/App.kt", score=10, reason="test", size_bytes=10)],
            warnings=["file_selection_budget_partial"],
            plan={
                "plan_id": "selection_plan_test",
                "workspace_root": request.workspace,
                "candidate_count": 1,
                "selected_count": 1,
                "selection_strategy": "cheap_path_metadata_ranking",
                "elapsed_ms": 75,
                "selected_files": [{"path": "src/App.kt", "score": 10, "reason": "test", "size_bytes": 10, "blocked": False, "blocked_reason": None}],
                "rejected_files_summary": {},
                "selection_reason_codes": ["PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED"],
                "budget_exceeded": True,
                "partial": True,
            },
        )

    def status(self):
        return {"status": "ok"}


class EmptySelection:
    def select_files(self, request, *, project_tree=None, progress=None):
        return FileSelectionResult(status="blocked")

    def status(self):
        return {"status": "ok"}


class SlowEmptySelection:
    def select_files(self, request, *, project_tree=None, progress=None):
        time.sleep(0.2)
        return FileSelectionResult(status="blocked")

    def status(self):
        return {"status": "ok"}


class SingleFileBudgetExceededContext:
    def build_context(self, request, selection, *, progress=None):
        if progress:
            progress("project_analysis_file_read_started", {"selected": len(selection.selected_files), "files_read": 0, "bytes_read": 0})
            progress("before_file_read_batch", {"files_discovered": len(selection.selected_files), "files_read": 0, "bytes_read": 0})
            progress("before_file_read_item", {"current_path_sample": "src/App.kt", "files_discovered": len(selection.selected_files), "files_read": 0, "bytes_read": 0})
            progress(
                "project_analysis_single_file_read_budget_exceeded",
                {
                    "current_path_sample": "src/App.kt",
                    "single_file_elapsed_ms": 10,
                    "max_single_file_read_ms": 1,
                    "files_read": 0,
                    "bytes_read": 0,
                },
            )
        return FileContextBundle(bundle_id="ctx", workspace=request.workspace, status="partial")

    def status(self):
        return {"status": "ok"}


class ManyFileTree:
    def build_tree_summary(self, request, *, progress=None):
        if progress:
            progress("before_path_resolution", {"workspace": request.workspace})
            progress("after_path_resolution", {"current_root": request.workspace})
            progress("before_workspace_root_scan", {"current_root": request.workspace})
            progress("after_workspace_root_scan", {"current_root": request.workspace})
            progress("after_file_enumeration", {"files_scan_attempted": 3, "files_scanned": 3, "files_discovered": 3})
        return ProjectTreeSummary(
            workspace=request.workspace,
            status="ok",
            total_files_seen=3,
            candidate_files=["src/App.kt", "src/Feature.kt", "README.md"],
        )

    def status(self):
        return {"status": "ok"}


class SlowFileReadContext:
    def build_context(self, request, selection, *, progress=None):
        if progress:
            progress("before_file_read_batch", {"files_discovered": len(selection.selected_files), "files_read": 0, "bytes_read": 0})
            time.sleep(0.02)
            progress("before_file_read_item", {"current_path_sample": "src/App.kt", "files_discovered": len(selection.selected_files), "files_read": 0, "bytes_read": 0})
        return FileContextBundle(bundle_id="ctx", workspace=request.workspace, status="ok")

    def status(self):
        return {"status": "ok"}


class SlowZeroProgressContext:
    def build_context(self, request, selection, *, progress=None):
        if progress:
            time.sleep(0.02)
            progress("before_file_read_batch", {"files_discovered": 0, "files_read": 0, "bytes_read": 0})
        return FileContextBundle(bundle_id="ctx", workspace=request.workspace, status="ok")

    def status(self):
        return {"status": "ok"}


def test_project_analysis_service_builds_report_without_side_effects(tmp_path):
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\\nname='demo'", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app_factory.py").write_text("from fastapi import FastAPI", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_demo.py").write_text("def test_ok(): assert True", encoding="utf-8")

    result = ProjectAnalysisService().analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path), max_files=5))

    assert result.status in {"ok", "partial"}
    assert result.file_context.items
    assert result.report.findings
    assert "python_project" in result.structures
    assert result.file_context.violations == []


def test_project_analysis_service_reads_kotlin_gradle_sources_generically(tmp_path):
    (tmp_path / "README.md").write_text(
        "# Desktop Studio\n\n"
        "A Kotlin desktop application for organizing projects, notes and exportable reports.",
        encoding="utf-8",
    )
    (tmp_path / "build.gradle.kts").write_text('plugins { kotlin("jvm") }', encoding="utf-8")
    (tmp_path / "settings.gradle.kts").write_text('rootProject.name = "desktop-studio"', encoding="utf-8")
    source = tmp_path / "src" / "main" / "kotlin" / "example"
    source.mkdir(parents=True)
    (source / "App.kt").write_text(
        'fun App() { Text("Projects"); Text("Export report") }',
        encoding="utf-8",
    )

    result = ProjectAnalysisService().analyze_project(
        ProjectAnalysisRequest(workspace=str(tmp_path), max_files=12),
    )

    included = {item.path for item in result.file_context.items if item.status == "included"}
    assert "project_profile:kotlin_gradle" in result.structures
    assert "build.gradle.kts" in included
    assert "settings.gradle.kts" in included
    assert "src/main/kotlin/example/App.kt" in included
    assert all("extension_not_allowed" not in item for item in result.violations)
    assert any(item.category == "functionality" for item in result.findings)


def test_project_analysis_timeout_during_root_scan_has_specific_reason(tmp_path):
    service = ProjectAnalysisService(
        tree_service=SlowRootScanTree(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=0.001),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.status == "timeout"
    assert result.reason_code == "PROJECT_ANALYSIS_ROOT_SCAN_TIMEOUT"
    assert result.last_checkpoint == "before_workspace_root_scan"
    assert result.blocking_operation == "workspace_root_scan"
    assert result.budget_exceeded_at == "before_workspace_root_scan"
    assert result.safe_to_continue is False


def test_project_analysis_timeout_during_file_enumeration_preserves_progress(tmp_path):
    service = ProjectAnalysisService(
        tree_service=SlowEnumerationTree(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=0.001),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.status == "timeout"
    assert result.reason_code == "PROJECT_ANALYSIS_FILE_ENUMERATION_TIMEOUT"
    assert result.last_checkpoint == "during_file_enumeration"
    assert result.blocking_operation == "file_enumeration"
    assert result.files_scan_attempted == 1
    assert result.current_path_sample == "src/App.kt"
    assert "during_file_enumeration" in result.elapsed_ms_by_checkpoint


def test_project_analysis_timeout_during_file_read_preserves_discovered_files(tmp_path):
    service = ProjectAnalysisService(
        tree_service=OneFileTree(),  # type: ignore[arg-type]
        selection_service=OneFileSelection(),  # type: ignore[arg-type]
        context_builder=SlowFileReadContext(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=0.001, max_files_read=1),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.status == "timeout"
    assert result.reason_code == "PROJECT_ANALYSIS_FILE_READ_TIMEOUT"
    assert result.last_checkpoint == "before_file_read_item"
    assert result.blocking_operation == "file_read"
    assert result.files_discovered == 1
    assert result.files_scan_attempted == 1
    assert result.files_scanned == 1
    assert result.files_read == 0
    assert result.bytes_read == 0


def test_project_analysis_zero_progress_timeout_is_explicit_after_late_checkpoint(tmp_path):
    service = ProjectAnalysisService(
        tree_service=ZeroProgressTree(),  # type: ignore[arg-type]
        selection_service=OneFileSelection(),  # type: ignore[arg-type]
        context_builder=SlowZeroProgressContext(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=0.001, max_files_read=1),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.reason_code == "PROJECT_ANALYSIS_ZERO_PROGRESS_TIMEOUT"
    assert result.files_discovered == 0
    assert result.files_scan_attempted == 0
    assert result.files_scanned == 0
    assert result.files_read == 0
    assert result.bytes_read == 0
    assert result.last_checkpoint == "before_file_read_batch"
    assert result.blocking_operation == "file_read"
    assert result.elapsed_ms_by_checkpoint["before_file_read_batch"] >= 0


def test_project_analysis_file_selection_plan_is_budget_aware_and_does_not_read_content(tmp_path, monkeypatch):
    for rel in ("src/App.kt", "src/Feature.kt", "README.md"):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("demo", encoding="utf-8")
    opened = []
    original_open = open

    def spy_open(*args, **kwargs):
        opened.append(args[0])
        return original_open(*args, **kwargs)

    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MAX_FILES_SELECTED", "2")
    monkeypatch.setattr("builtins.open", spy_open)

    result = ProjectAnalysisService(tree_service=ManyFileTree()).analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.file_selection_plan is not None
    assert result.file_selection_plan["candidate_count"] == 3
    assert result.file_selection_plan["selected_count"] == 2
    assert result.files_selected == 2
    assert not any(str(path).endswith(("App.kt", "Feature.kt", "README.md")) for path in opened)


def test_project_analysis_single_file_read_budget_has_specific_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MAX_SINGLE_FILE_READ_MS", "1")
    service = ProjectAnalysisService(
        tree_service=OneFileTree(),  # type: ignore[arg-type]
        selection_service=OneFileSelection(),  # type: ignore[arg-type]
        context_builder=SingleFileBudgetExceededContext(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=10, max_files_read=1),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.status == "timeout"
    assert result.reason_code == "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED"
    assert result.blocking_operation == "file_read"
    assert result.safe_to_continue is False


def test_project_analysis_handoff_reserve_returns_partial_when_minimum_context_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MIN_REMAINING_MS_FOR_HANDOFF", "9950")
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MIN_REMAINING_MS_FOR_SERIALIZATION", "9950")
    service = ProjectAnalysisService(
        tree_service=OneFileTree(),  # type: ignore[arg-type]
        selection_service=BudgetExceededOneFileSelection(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=10, max_files_read=1),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.status == "partial"
    assert result.reason_code == "PROJECT_ANALYSIS_PARTIAL_HANDOFF"
    assert result.safe_to_continue is True
    assert result.handoff_reserve_reached is True
    assert result.partial_readiness is not None
    assert result.partial_readiness["safe_to_continue_to_artifact_runtime"] is True
    assert result.remaining_budget_ms_at_return is not None


def test_project_analysis_selection_budget_returns_partial_handoff_when_minimum_context_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MAX_SELECTION_SECONDS", "0.05")
    service = ProjectAnalysisService(
        tree_service=OneFileTree(),  # type: ignore[arg-type]
        selection_service=BudgetExceededOneFileSelection(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=10, max_files_read=1),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.status == "partial"
    assert result.reason_code == "PROJECT_ANALYSIS_PARTIAL_HANDOFF"
    assert result.file_selection_plan is not None
    assert result.file_selection_plan["budget_exceeded"] is True
    assert "PROJECT_ANALYSIS_SELECTION_BUDGET_EXCEEDED" in result.limitations
    assert result.safe_to_continue is True


def test_project_analysis_handoff_reserve_blocks_without_minimum_context(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MIN_REMAINING_MS_FOR_HANDOFF", "9950")
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MIN_REMAINING_MS_FOR_SERIALIZATION", "9950")
    service = ProjectAnalysisService(
        tree_service=ZeroProgressTree(),  # type: ignore[arg-type]
        selection_service=SlowEmptySelection(),  # type: ignore[arg-type]
        budget=ProjectAnalysisBudget(max_total_seconds=10, max_files_read=1),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path)))

    assert result.status in {"blocked", "timeout"}
    assert result.reason_code == "PROJECT_ANALYSIS_INSUFFICIENT_PARTIAL_CONTEXT"
    assert result.safe_to_continue is False
