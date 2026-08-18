from pathlib import Path

import pytest

from aipinho.core.exceptions import ConfigValidationError
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService


def test_action_aliases_normalize_to_canonical_actions():
    registry = ActionRegistryService().load()

    assert registry.normalize_action("write_file") == "write_files"
    assert registry.normalize_action("file_write") == "write_files"
    assert registry.normalize_action("read_file") == "read_files"


def test_apply_patch_requires_approval():
    registry = ActionRegistryService().load()

    assert registry.requires_approval("apply_patch") is True
    assert registry.is_side_effect("apply_patch") is True


def test_unknown_action_is_not_allowed_silently():
    registry = ActionRegistryService().load()

    assert registry.action_exists("unknown_action") is False
    with pytest.raises(ConfigValidationError):
        registry.normalize_action("unknown_action")


def test_duplicate_alias_fails_validation(tmp_path: Path):
    config = tmp_path / "action_registry.yaml"
    config.write_text(
        """
schema_version: 1
actions:
  first:
    aliases: [shared_alias]
    category: test
    side_effect: false
    requires_approval: false
    capability: read_workspace
  second:
    aliases: [shared_alias]
    category: test
    side_effect: false
    requires_approval: false
    capability: read_workspace
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError):
        ActionRegistryService(config_path=config).load()
