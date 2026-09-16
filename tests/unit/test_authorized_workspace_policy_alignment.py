from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aipinho.schemas.memory.memory_candidate import MemoryCandidateScope
from aipinho.services.memory.memory_candidate_scope_service import MemoryCandidateScopeService


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "config"


def _load_yaml(relative_path: str) -> dict[str, Any]:
    with (CONFIG_ROOT / relative_path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    assert isinstance(data, dict)
    return data


def _norm(path: str) -> str:
    return str(Path(path).expanduser()).lower().replace("/", "\\").rstrip("\\")


def _authorized_roots() -> set[str]:
    registry = _load_yaml("workspaces/workspace_registry.yaml")
    roots = {
        _norm(str(item.get("root_path")))
        for item in registry.get("workspaces", []) or []
        if isinstance(item, dict) and item.get("root_path")
    }
    assert roots
    return roots


def _collect_path_list(config: dict[str, Any], dotted_key: str) -> list[str]:
    value: Any = config
    for part in dotted_key.split("."):
        if not isinstance(value, dict):
            return []
        value = value.get(part, {})
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def test_authorized_workspaces_are_not_operational_forbidden_roots():
    authorized = _authorized_roots()
    checks = {
        "memory/curated_memory_scope_policy.yaml": ["scope.forbidden_roots"],
        "memory/memory_candidate_scope_policy.yaml": ["workspace.forbidden_roots"],
        "validation/workspace_access_validation_policy.yaml": ["forbidden_roots"],
        "rag/retrieval_scope_policy.yaml": ["workspace.forbidden_roots"],
        "artifacts/artifact_target_policy.yaml": ["forbidden_roots"],
        "patching/patch_target_policy.yaml": ["targets.forbidden_roots"],
    }

    conflicts: list[str] = []
    for relative_path, keys in checks.items():
        config = _load_yaml(relative_path)
        for key in keys:
            blocked = {_norm(item) for item in _collect_path_list(config, key)}
            overlap = sorted(authorized.intersection(blocked))
            conflicts.extend(f"{relative_path}:{key}:{root}" for root in overlap)

    assert conflicts == []


def test_authorized_workspaces_are_not_model_or_mmproj_blocked_roots():
    authorized = _authorized_roots()
    checks = {
        "models/local_model_paths.yaml": ["blocked_model_roots"],
        "models/model_security_policy.yaml": ["security.blocked_roots"],
        "vision/mmproj_policy.yaml": ["blocked_roots"],
    }

    conflicts: list[str] = []
    for relative_path, keys in checks.items():
        config = _load_yaml(relative_path)
        for key in keys:
            blocked = {_norm(item) for item in _collect_path_list(config, key)}
            overlap = sorted(authorized.intersection(blocked))
            conflicts.extend(f"{relative_path}:{key}:{root}" for root in overlap)

    assert conflicts == []


def test_memory_candidate_scope_uses_configured_forbidden_roots_not_project_constant():
    service = MemoryCandidateScopeService(
        config={
            "workspace": {
                "forbidden_roots": ["C:\\Windows"],
            }
        }
    )

    allowed = service.validate(MemoryCandidateScope(scope_type="workspace", workspace="C:\\PinhoabacaxiAI"))
    blocked = service.validate(MemoryCandidateScope(scope_type="workspace", workspace="C:\\Windows\\System32"))

    assert "forbidden_root_scope" not in allowed
    assert "forbidden_root_scope" in blocked
