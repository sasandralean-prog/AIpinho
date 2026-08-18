from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RegressionWorkspaces:
    root: Path
    source_readonly: Path
    target_mutable: Path
    protected: Path
    forbidden: Path
    artifact_root: Path


def create_regression_workspaces(tmp_path: Path) -> RegressionWorkspaces:
    root = tmp_path / "multi_agent_workspaces"
    source = root / "source_readonly"
    target = root / "target_mutable"
    protected = target / "protected_child"
    forbidden = root / "forbidden"
    artifacts = root / "artifacts"
    for item in [source, target, protected, forbidden, artifacts]:
        item.mkdir(parents=True, exist_ok=True)
    (source / "README.md").write_text("# Source\nToken Bearer SECRET_VALUE_12345 must be redacted.\n", encoding="utf-8")
    (target / "existing.txt").write_text("old", encoding="utf-8")
    return RegressionWorkspaces(root, source, target, protected, forbidden, artifacts)


def write_gateway_config(tmp_path: Path, workspaces: RegressionWorkspaces) -> Path:
    config_root = tmp_path / "config"
    (config_root / "agents").mkdir(parents=True, exist_ok=True)
    for filename in ["tool_gateway_registry.yaml", "tool_gateway_policy.yaml"]:
        (config_root / "agents" / filename).write_text(
            Path("config/agents", filename).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (config_root / "agents" / "tool_gateway_workspaces.yaml").write_text(
        f"""
version: 1
workspaces:
  - workspace_id: source
    root: {workspaces.source_readonly}
    role: source_readonly
    enabled: true
  - workspace_id: target
    root: {workspaces.target_mutable}
    role: target_mutable
    enabled: true
  - workspace_id: protected_child
    root: {workspaces.protected}
    role: forbidden
    enabled: true
  - workspace_id: forbidden
    root: {workspaces.forbidden}
    role: forbidden
    enabled: true
""",
        encoding="utf-8",
    )
    return config_root

