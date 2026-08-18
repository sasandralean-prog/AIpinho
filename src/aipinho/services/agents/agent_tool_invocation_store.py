from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import ToolArtifactRecord, ToolInvocation


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists() or path.stat().st_size == 0:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


class AgentToolInvocationStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_TOOL_GATEWAY_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "agent_tool_gateway")
        self.invocations_dir = self.root / "invocations"
        self.artifacts_dir = self.root / "artifacts"
        self.artifact_index_path = self.root / "artifacts.json"

    def save_invocation(self, invocation: ToolInvocation) -> ToolInvocation:
        self.invocations_dir.mkdir(parents=True, exist_ok=True)
        (self.invocations_dir / f"{invocation.tool_invocation_id}.json").write_text(
            json.dumps(_dump_model(invocation), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        return invocation

    def get_invocation(self, tool_invocation_id: str) -> ToolInvocation | None:
        path = self.invocations_dir / f"{tool_invocation_id}.json"
        if not path.exists():
            return None
        return ToolInvocation(**json.loads(path.read_text(encoding="utf-8")))

    def list_invocations(self, *, run_id: str | None = None, agent_id: str | None = None, session_id: str | None = None) -> list[ToolInvocation]:
        if not self.invocations_dir.exists():
            return []
        rows = [ToolInvocation(**json.loads(path.read_text(encoding="utf-8"))) for path in self.invocations_dir.glob("*.json")]
        if run_id is not None:
            rows = [row for row in rows if row.run_id == run_id]
        if agent_id is not None:
            rows = [row for row in rows if row.agent_id == agent_id]
        if session_id is not None:
            rows = [row for row in rows if row.session_id == session_id]
        return sorted(rows, key=lambda row: row.started_at, reverse=True)

    def save_artifact(self, artifact: ToolArtifactRecord, content: bytes) -> ToolArtifactRecord:
        artifact_dir = self.artifacts_dir / artifact.artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / artifact.filename).write_bytes(content)
        artifact = artifact.model_copy(update={"size": len(content)})
        artifacts = self.list_artifacts(include_all=True)
        artifacts = [item for item in artifacts if item.artifact_id != artifact.artifact_id]
        artifacts.append(artifact)
        _json_write(self.artifact_index_path, {"artifacts": [_dump_model(item) for item in artifacts]})
        return artifact

    def list_artifacts(
        self,
        *,
        agent_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        include_all: bool = False,
    ) -> list[ToolArtifactRecord]:
        payload = _json_read(self.artifact_index_path, {"artifacts": []})
        rows = [ToolArtifactRecord(**item) for item in payload.get("artifacts", [])]
        if not include_all:
            if agent_id is not None:
                rows = [row for row in rows if row.agent_id == agent_id]
            if session_id is not None:
                rows = [row for row in rows if row.session_id == session_id]
            if run_id is not None:
                rows = [row for row in rows if row.run_id == run_id]
        return sorted(rows, key=lambda row: row.created_at, reverse=True)

    def get_artifact(self, artifact_id: str) -> ToolArtifactRecord | None:
        return next((artifact for artifact in self.list_artifacts(include_all=True) if artifact.artifact_id == artifact_id), None)

    def artifact_content_path(self, artifact: ToolArtifactRecord) -> Path:
        return self.artifacts_dir / artifact.artifact_id / artifact.filename
