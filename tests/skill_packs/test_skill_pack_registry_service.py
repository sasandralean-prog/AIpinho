from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from aipinho.schemas.agents.contracts import AgentSessionCreateRequest
from aipinho.schemas.artifacts.artifact_library import ArtifactQuery
from aipinho.schemas.skills.skill_packs import (
    SkillPackExecutionRequest,
    SkillPackSelectionRequest,
)
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.artifacts.artifact_library_service import ArtifactLibraryService
from aipinho.services.skills.skill_execution_service import SkillExecutionService
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService
from aipinho.services.skills.skill_pack_registry_service import (
    SkillPackExecutionService,
    SkillPackRegistry,
    SkillPackValidator,
)

ROOT = Path(__file__).resolve().parents[2]


def _copy_registry(tmp_path: Path) -> tuple[Path, Path]:
    skill_root = tmp_path / "skill_registry"
    pack_root = tmp_path / "skill_packs"
    shutil.copytree(ROOT / "config" / "skills" / "registry", skill_root, ignore=shutil.ignore_patterns("__pycache__", "backups"))
    shutil.copytree(ROOT / "config" / "skills" / "packs", pack_root, ignore=shutil.ignore_patterns("__pycache__"))
    return skill_root, pack_root


def _registry(tmp_path: Path) -> SkillPackRegistry:
    skill_root, pack_root = _copy_registry(tmp_path)
    skill_registry = SkillManifestRegistryService(root=skill_root)
    return SkillPackRegistry(root=pack_root, skill_registry=skill_registry)


def _fixture(name: str) -> dict:
    return yaml.safe_load((ROOT / "tests" / "fixtures" / "skill_packs" / name).read_text(encoding="utf-8"))


def test_skill_pack_registry_loads(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    packs = registry.list_packs()

    assert len(packs) >= 10
    assert {pack.skill_pack_id for pack in packs} >= {
        "android_pack",
        "python_pack",
        "docs_pack",
        "artifact_pack",
        "sandbox_pack",
        "debug_pack",
        "ux_audit_pack",
        "workspace_pack",
        "promotion_pack",
        "validation_release_pack",
    }


def test_skill_pack_manifest_validates(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    validation = registry.validate_pack("android_pack")

    assert validation.valid is True
    assert validation.health_status in {"ok", "degraded"}


def test_skill_pack_invalid_missing_skill_blocks(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    validation = SkillPackValidator(registry.skill_registry).validate(_fixture("invalid_missing_skill_pack.yaml"))

    assert validation.valid is False
    assert any(reason.startswith("missing_included_skill") for reason in validation.reason_codes)


def test_skill_pack_fake_secret_blocks(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    validation = SkillPackValidator(registry.skill_registry).validate(_fixture("pack_with_fake_secret.yaml"))

    assert validation.valid is False
    assert "secret_detected" in validation.reason_codes


def test_skill_pack_deprecated_warns(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    validation = SkillPackValidator(registry.skill_registry).validate(_fixture("deprecated_pack.yaml"))

    assert validation.valid is True
    assert "deprecated_pack" in validation.warnings


def test_skill_pack_experimental_requires_enable(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    validation = SkillPackValidator(registry.skill_registry).validate(_fixture("experimental_pack.yaml"))

    assert validation.valid is False
    assert "experimental_pack_not_enabled" in validation.reason_codes


def test_required_pack_health_ok(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    health = registry.health()
    by_id = {item["skill_pack_id"]: item for item in health["packs"]}

    for pack_id in [
        "android_pack",
        "python_pack",
        "docs_pack",
        "artifact_pack",
        "sandbox_pack",
        "debug_pack",
        "ux_audit_pack",
        "workspace_pack",
        "promotion_pack",
        "validation_release_pack",
    ]:
        assert by_id[pack_id]["health_status"] in {"ok", "degraded"}


def test_autopilot_selects_android_pack(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    result = registry.select(SkillPackSelectionRequest(
        user_goal="Create an Android Kotlin app in the sandbox and generate a zip artifact.",
        agent_id="autopilot",
        project_stack="android_gradle",
        execution_mode="sandbox_autopilot",
        requested_capabilities=["sandbox_write", "sandbox_artifact_export"],
    ))

    assert result.status == "selected"
    assert result.candidates[0].skill_pack_id == "android_pack"


def test_autopilot_selects_debug_pack_for_artifact_failure(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    result = registry.select(SkillPackSelectionRequest(
        user_goal="Analyze why the artifact failed and the download does not work.",
        agent_id="autopilot",
        execution_mode="assisted_execution",
        requested_capabilities=["artifact_download", "report_generate"],
    ))

    assert result.status == "selected"
    assert "debug_pack" in {candidate.skill_pack_id for candidate in result.candidates[:3]}


def test_skill_pack_mobile_view_model_available(tmp_path: Path) -> None:
    registry = _registry(tmp_path)

    mobile = registry.mobile_view_model()

    assert mobile["state"]["screen"] == "skill_packs"
    assert mobile["state"]["raw_default_visible"] is False
    assert mobile["packs"]
    assert all("skill_pack_id" in item for item in mobile["packs"])


def test_skill_pack_execution_records_pack_id_and_artifacts_indexed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_ARTIFACT_LIBRARY_ROOT", str(tmp_path / "artifact_library"))
    registry = _registry(tmp_path)
    kernel = AgentSessionKernelService()
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="skill pack test"))
    service = SkillPackExecutionService(
        registry=registry,
        skill_execution=SkillExecutionService(registry=registry.skill_registry, kernel=kernel, executions_root=tmp_path / "skill_executions"),
        executions_root=tmp_path / "skill_pack_executions",
    )

    result = service.execute(SkillPackExecutionRequest(
        skill_pack_id="docs_pack",
        requested_skill_id="internal.safe_markdown_report_generator",
        requesting_agent_id="aipinho",
        session_id=session.session_id,
        user_goal="Generate a governed docs report.",
        requested_capabilities=["report_generate", "artifact_create"],
        inputs={"title": "Pack report", "summary": "Skill pack execution report."},
    ))
    library = ArtifactLibraryService(
        tool_store=AgentToolInvocationStore(root=tmp_path / "tool_gateway"),
        index_path=tmp_path / "artifact_library" / "ARTIFACT_INDEX.json",
    )
    query = library.query(ArtifactQuery(skill_pack_id="docs_pack"))

    assert result.status == "completed"
    assert result.selected_skills == ["internal.safe_markdown_report_generator"]
    assert result.skill_execution_ids
    assert result.artifacts
    assert result.evidence_refs
    assert query.total >= 1
    assert query.items[0].skill_pack_id == "docs_pack"
    assert query.items[0].skill_pack_execution_id == result.skill_pack_execution_id


def test_skill_pack_source_readonly_write_denied_by_validator(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    payload = _fixture("valid_android_pack.yaml")
    payload["included_skills"] = ["internal.safe_markdown_report_generator"]
    payload["metadata_sanitized"] = {"note": "source_readonly_write is forbidden by pack policy"}

    validation = SkillPackValidator(registry.skill_registry).validate(payload)

    assert validation.valid is True
    assert not any("source_readonly_write_declared" in reason for reason in validation.reason_codes)
