from pathlib import Path

import pytest

from aipinho.core.exceptions import ConfigEmptyError, ConfigNotFoundError, UnsafePathError
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file


def test_yaml_loader_loads_valid_file(tmp_path: Path):
    config = tmp_path / "valid.yaml"
    config.write_text("schema_version: 1\nname: test\n", encoding="utf-8")

    assert load_yaml_file(config, root=tmp_path) == {"schema_version": 1, "name": "test"}


def test_missing_critical_file_raises_clear_error(tmp_path: Path):
    with pytest.raises(ConfigNotFoundError):
        load_yaml_file(tmp_path / "missing.yaml", root=tmp_path)


def test_empty_file_has_controlled_degraded_status(tmp_path: Path):
    config = tmp_path / "empty.yaml"
    config.write_text("", encoding="utf-8")

    status = inspect_yaml_file(config, root=tmp_path)
    assert status.status == "degraded"
    with pytest.raises(ConfigEmptyError):
        load_yaml_file(config, root=tmp_path)


def test_path_traversal_is_not_accepted(tmp_path: Path):
    outside = tmp_path.parent / "outside.yaml"

    with pytest.raises(UnsafePathError):
        load_yaml_file(outside, root=tmp_path)
