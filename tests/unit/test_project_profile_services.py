from __future__ import annotations

from pathlib import Path

import pytest

from aipinho.schemas.projects import ProjectProfileCreateRequest
from aipinho.schemas.projects.project_profile import ProjectProfileSelectionRequest
from aipinho.services.projects import ProjectProfileDetector, ProjectProfileRegistryService


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "project_profiles"


def test_detector_identifies_android_python_node_and_unknown_projects():
    detector = ProjectProfileDetector()

    android = detector.detect(FIXTURES / "android_gradle_project")
    python = detector.detect(FIXTURES / "python_project")
    node = detector.detect(FIXTURES / "node_project")
    unknown = detector.detect(FIXTURES / "unknown_project")

    assert android.detected_stack == "android_gradle"
    assert python.detected_stack == "python"
    assert node.detected_stack == "node"
    assert unknown.detected_stack == "unknown"
    assert android.suggested_workspaces[0].role == "source_readonly"
    assert android.suggested_validation_profile is not None


def test_registry_persists_profile_index_and_selection(tmp_path):
    service = ProjectProfileRegistryService(root=tmp_path / "profiles_root")
    candidate = service.detect(FIXTURES / "python_project")
    profile = service.create(ProjectProfileCreateRequest(profile=candidate["proposed_profile"]))

    listed = service.list_profiles()
    selected = service.select(ProjectProfileSelectionRequest(project_id=profile.project_id))
    status = service.status()

    assert listed[0].project_id == profile.project_id
    assert selected["selection"]["project_id"] == profile.project_id
    assert status["profile_count"] == 1
    assert (tmp_path / "profiles_root" / f"{profile.project_id}.yaml").exists()
    assert (tmp_path / "profiles_root" / "PROJECT_PROFILES_INDEX.json").exists()


def test_registry_blocks_profile_that_contains_fake_secret(tmp_path):
    service = ProjectProfileRegistryService(root=tmp_path / "profiles_root")
    candidate = service.detect(FIXTURES / "project_with_fake_secret")

    with pytest.raises(ValueError, match="project_profile_secret_detected"):
        service.create(ProjectProfileCreateRequest(profile=candidate["proposed_profile"]))


def test_profile_context_does_not_turn_source_readonly_into_write_permission(tmp_path):
    service = ProjectProfileRegistryService(root=tmp_path / "profiles_root")
    candidate = service.detect(FIXTURES / "python_project")
    profile = service.create(ProjectProfileCreateRequest(profile=candidate["proposed_profile"]))
    source = next(workspace for workspace in profile.workspace_profiles if workspace.role == "source_readonly")

    assert source.access_policy == "read_allowed"
    assert source.write_policy == "write_denied"
    assert source.shell_policy == "readonly_shell_only"
