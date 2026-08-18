from __future__ import annotations

from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from patch_fixtures import patch_request, patch_workspace


class FakeReadonlyArtifactRuntime:
    def __init__(self, context):
        self.context = context

    def latest_patch_plan_context(self, *, session_id, workspace=None):
        return self.context


def test_patch_request_uses_latest_concrete_patch_plan_from_session(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan
    context = {
        "patch_plan_id": plan.plan_id,
        "patch_plan": plan.model_dump(mode="json"),
        "workspace": str(workspace),
        "target_paths": [file.normalized_path or file.path for file in plan.affected_files],
    }
    service = CanonicalPublicChatService(
        readonly_artifact_runtime=FakeReadonlyArtifactRuntime(context)
    )

    metadata = service._operation_metadata(
        "Aplique o plano aprovado.",
        "patch_apply",
        str(workspace),
        session_id="session_test",
    )

    assert metadata["operation_type"] == "patch_request"
    assert metadata["executable_plan_ref"]
    assert metadata["patch_plan"]["patch_plan_id"] == plan.plan_id
    assert metadata["patch_plan"]["hunks"]
    assert metadata["target_paths"]
    assert "execution_intent" in metadata
    assert "executable_patch_plan" in metadata
    assert "execution_preview" in metadata
