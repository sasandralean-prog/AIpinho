from __future__ import annotations

import os
import shutil
from pathlib import Path

from aipinho.schemas.projects.project_rebuild_preview import ProjectRebuildPreviewRequest
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.projects.project_rebuild_preview_service import ProjectRebuildPreviewService


def _root(tmp_path: Path) -> Path:
    base = Path(os.environ.get("AIPINHO_TEST_MUTABLE_ROOT", r"C:\Users\rafae\Documents\AIpinhoTestes\.pytest"))
    root = base / tmp_path.name / "project_rebuild"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def test_project_rebuild_preview_creates_patch_plan_and_approval_without_writing_target(tmp_path: Path) -> None:
    root = _root(tmp_path)
    source = root / "source"
    target = root / "target"
    (source / "src" / "main" / "kotlin").mkdir(parents=True)
    (source / "settings.gradle.kts").write_text('rootProject.name = "Example"\n', encoding="utf-8")
    (source / "build.gradle.kts").write_text('plugins { kotlin("jvm") version "2.1.21" }\n', encoding="utf-8")
    (source / "src" / "main" / "kotlin" / "Main.kt").write_text("fun main() = println(\"ok\")\n", encoding="utf-8")
    target.mkdir()

    plan_store = PatchPlanStore(root=root / "plans")
    service = ProjectRebuildPreviewService(plan_store=plan_store)

    result = service.create_preview(
        ProjectRebuildPreviewRequest(
            session_id="chat_test_project_rebuild",
            prompt="Execute o rebuild governado do projeto.",
            source_workspace=str(source),
            target_workspace=str(target),
        )
    )

    assert result.status == "pending_approval"
    assert result.plan_id
    assert result.approval_id
    assert len(result.files) == 3
    assert not list(target.rglob("*"))
    plan = plan_store.get_plan(result.plan_id)
    assert plan is not None
    assert plan.diff_proposal is not None
    assert plan.diff_proposal.status == "generated"
    assert plan.apply_enabled is True
    assert plan.safe_to_apply is True


def test_project_rebuild_preview_blocks_same_source_and_target(tmp_path: Path) -> None:
    root = _root(tmp_path)
    source = root / "same"
    source.mkdir()

    result = ProjectRebuildPreviewService(plan_store=PatchPlanStore(root=root / "plans")).create_preview(
        ProjectRebuildPreviewRequest(
            session_id="chat_test_project_rebuild",
            prompt="Execute o rebuild governado do projeto.",
            source_workspace=str(source),
            target_workspace=str(source),
        )
    )

    assert result.status == "blocked"
    assert "source_and_target_must_differ" in result.blocked_reasons


def test_project_rebuild_preview_large_diff_requires_approval_without_blocking_plan(tmp_path: Path) -> None:
    root = _root(tmp_path)
    source = root / "source"
    target = root / "target"
    source_dir = source / "src" / "main" / "kotlin"
    source_dir.mkdir(parents=True)
    (source / "settings.gradle.kts").write_text('rootProject.name = "LargeExample"\n', encoding="utf-8")
    (source_dir / "LargeFile.kt").write_text(
        "\n".join(f"val item{index} = \"line with enough content to raise diff risk\"" for index in range(900)),
        encoding="utf-8",
    )
    target.mkdir()

    plan_store = PatchPlanStore(root=root / "plans")
    result = ProjectRebuildPreviewService(plan_store=plan_store).create_preview(
        ProjectRebuildPreviewRequest(
            session_id="chat_test_project_rebuild",
            prompt="Execute o rebuild governado do projeto com preview e approval.",
            source_workspace=str(source),
            target_workspace=str(target),
        )
    )

    assert result.status == "pending_approval"
    assert result.blocked_reasons == []
    assert result.approval_id
    plan = plan_store.get_plan(result.plan_id or "")
    assert plan is not None
    assert plan.status == "needs_review"
    assert plan.blocked_reasons == []
    assert plan.risk.risk_level == "high"
    assert "large_diff" in plan.risk.reasons
    assert plan.safe_to_apply is True


def test_project_rebuild_preview_omits_already_synchronized_files(tmp_path: Path) -> None:
    root = _root(tmp_path)
    source = root / "source"
    target = root / "target"
    (source / "src" / "main" / "kotlin").mkdir(parents=True)
    (target / "src" / "main" / "kotlin").mkdir(parents=True)
    (source / "settings.gradle.kts").write_text('rootProject.name = "Example"\n', encoding="utf-8")
    (target / "settings.gradle.kts").write_text('rootProject.name = "Example"\n', encoding="utf-8")
    (source / "src" / "main" / "kotlin" / "Main.kt").write_text("fun main() = println(\"ok\")\n", encoding="utf-8")
    (target / "src" / "main" / "kotlin" / "Main.kt").write_text("", encoding="utf-8")

    result = ProjectRebuildPreviewService(plan_store=PatchPlanStore(root=root / "plans")).create_preview(
        ProjectRebuildPreviewRequest(
            session_id="chat_test_project_rebuild",
            prompt="Sincronize o projeto por preview governado.",
            source_workspace=str(source),
            target_workspace=str(target),
        )
    )

    assert result.status == "pending_approval"
    assert [file.relative_path for file in result.files] == ["src/main/kotlin/Main.kt"]
    omitted = {file.relative_path: file.blocked_reasons for file in result.omitted_files}
    assert omitted["settings.gradle.kts"] == ["already_synchronized"]
