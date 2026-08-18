from patch_fixtures import patch_workspace
from aipinho.services.patching.patch_target_guard import PatchTargetGuard


def test_patch_target_guard_allowed_high_risk_and_blocked(tmp_path):
    workspace = patch_workspace(tmp_path)
    guard = PatchTargetGuard()
    allowed = guard.validate(str(workspace), "src/app.py")
    assert allowed.status == "allowed"
    config = guard.validate(str(workspace), "config/policies/x.yaml")
    assert config.risk_level == "high"
    traversal = guard.validate(str(workspace), "../outside.py")
    assert traversal.status == "blocked"
    binary = guard.validate(str(workspace), "data/runtime/x.sqlite")
    assert binary.status == "blocked"
