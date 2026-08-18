from aipinho.services.patching.patch_scope_service import PatchScopeService


def test_patch_scope_limits_files():
    scope = PatchScopeService().build("w", [f"f{i}.py" for i in range(8)])
    assert len(scope.affected_paths) <= scope.max_files
    assert scope.omitted_paths
