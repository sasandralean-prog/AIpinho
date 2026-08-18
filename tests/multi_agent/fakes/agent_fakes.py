from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeAgentResponse:
    status: str = "completed"
    text: str = "Resposta fake governada."
    structured_actions: list[dict[str, Any]] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    provider: str = "fake_provider"
    raw_hidden_by_default: bool = True


class FakeCodexAdapter:
    def respond(self, prompt: str, *, mode: str = "technical_execution") -> FakeAgentResponse:
        return FakeAgentResponse(
            text=f"Codex fake executou modo {mode} sem provider real.",
            structured_actions=[{"action": "tool_plan", "capability": "read_workspace"}],
            evidence_refs=["fake:codex:response"],
        )


class FakeGeminiClient:
    def generate(self, prompt: str, *, fail: bool = False) -> FakeAgentResponse:
        if fail:
            return FakeAgentResponse(status="failed", text="Provider fake falhou de forma controlada.", evidence_refs=["fake:gemini:error"])
        return FakeAgentResponse(text="Gemini fake respondeu sem tocar ferramentas locais.", evidence_refs=["fake:gemini:response"])


class FakeLucioClient:
    def route(self, prompt: str, *, target_agent: str = "codex") -> FakeAgentResponse:
        return FakeAgentResponse(
            text=f"Lucio fake recomendou delegacao para {target_agent}.",
            structured_actions=[{"action": "delegate", "target_agent": target_agent}],
            evidence_refs=["fake:lucio:route"],
        )


class FakeShellRunner:
    def run(self, argv, cwd, timeout):
        if "--fail" in argv:
            return subprocess.CompletedProcess(argv, 2, stdout="", stderr="failed")
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


class FakeArtifactStore:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def upload(self, artifact_id: str, *, filename: str, content: bytes, requires_token: bool = True) -> dict[str, Any]:
        record = {
            "artifact_id": artifact_id,
            "filename": filename,
            "size": len(content),
            "requires_token": requires_token,
            "download_endpoint": f"/api/v1/artifacts/{artifact_id}/download",
        }
        self._items[artifact_id] = record
        return record

    def download(self, artifact_id: str) -> dict[str, Any] | None:
        return self._items.get(artifact_id)

