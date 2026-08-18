from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService


def _protected_service(tmp_path):
    protected_root = tmp_path / "protected"
    protected_root.mkdir()
    config = tmp_path / "protected_workspaces.yaml"
    config.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "protected_roots:",
                f"  - path: \"{str(protected_root).replace(chr(92), chr(92) + chr(92))}\"",
                "    block_task: true",
                "    reason: test_protected_root",
            ]
        ),
        encoding="utf-8",
    )
    return WorkspacePolicyService(config_path=config).load(), protected_root


def test_allowed_workspace_is_allowed():
    result = WorkspacePolicyService().load().evaluate(workspace_path="C:\\Dev\\AIpinho", requires_workspace=True)

    assert result.status == "allowed"
    assert result.blocked is False


def test_missing_workspace_when_required_needs_clarification():
    result = WorkspacePolicyService().load().evaluate(workspace_path=None, requires_workspace=True)

    assert result.status == "needs_clarification"
    assert result.needs_clarification is True


def test_protected_root_is_denied(tmp_path):
    service, protected_root = _protected_service(tmp_path)
    result = service.evaluate(workspace_path=str(protected_root), requires_workspace=True)

    assert result.status == "denied"
    assert result.blocked is True
    assert result.violations[0].code == "forbidden_root"


def test_protected_root_path_normalization_blocks_children(tmp_path):
    service, protected_root = _protected_service(tmp_path)
    result = service.evaluate(workspace_path=str(protected_root / "subdir" / ".." / "child"), requires_workspace=True)

    assert result.status == "denied"
