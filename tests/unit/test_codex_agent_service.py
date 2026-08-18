from __future__ import annotations

import json
import hashlib
from pathlib import Path

from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactRecord, ArtifactUploadResponse
from aipinho.schemas.codex_agent import CodexAgentRequest
from aipinho.services.codex_agent.codex_agent_config_service import (
    CodexAgentConfigService,
    CodexAgentRuntimeConfig,
)
from aipinho.services.codex_agent.codex_agent_service import CodexAgentService
from aipinho.services.codex_agent.codex_agent_store import CodexAgentStore
from aipinho.services.codex_agent.codex_cli_adapter import CodexCliAdapter, FakeCodexCliAdapter


def _service(tmp_path: Path, monkeypatch, *, enabled: bool = True) -> CodexAgentService:
    monkeypatch.setenv("CODEX_AGENT_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("CODEX_AGENT_ALLOW_READ", "true")
    monkeypatch.setenv("CODEX_AGENT_ALLOW_WRITE", "true")
    monkeypatch.setenv("CODEX_AGENT_ALLOW_SHELL", "true")
    monkeypatch.setenv("CODEX_AGENT_DEFAULT_WORKDIR", str(tmp_path))
    monkeypatch.setenv("AIPINHO_CODEX_AGENT_ROOT", str(tmp_path / "codex_agent"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "agent_memory"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy_kernel"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events" / "store"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "events" / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "events" / "audit"))
    service = CodexAgentService(
        config_service=CodexAgentConfigService(policy_path=tmp_path / "missing.yaml"),
        store=CodexAgentStore(tmp_path / "codex_store"),
        adapter=FakeCodexCliAdapter(),
    )
    service._publish = lambda *args, **kwargs: None
    return service


def test_codex_chat_is_persistent_and_uses_separate_namespace(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Revisao")

    response = service.send(CodexAgentRequest(session_id=session.session_id, prompt="Analise este contexto."))

    assert response.status == "completed"
    assert response.cli_status == "fake_adapter"
    messages = service.messages(session.session_id)
    assert [message.role for message in messages] == ["user", "codex"]
    assert all(message.session_id.startswith("codex_session_") for message in messages)


def test_codex_session_can_be_renamed_switched_and_soft_deleted(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    first = service.create_session("Primeira")
    second = service.create_session("Segunda")

    renamed = service.rename_session(first.session_id, "Arquitetura")
    assert renamed is not None
    assert renamed.title == "Arquitetura"
    assert {item.session_id for item in service.sessions()} == {first.session_id, second.session_id}

    assert service.delete_session(first.session_id) is True
    assert service.get_session(first.session_id) is None
    assert [item.session_id for item in service.sessions()] == [second.session_id]


def test_codex_readonly_exec_uses_json_without_shell_or_auth_copy(tmp_path, monkeypatch):
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        payload = {
            "type": "item.completed",
            "item": {"id": "item_final", "type": "agent_message", "text": "Resposta segura."},
        }
        return type("Completed", (), {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""})()

    monkeypatch.setattr("aipinho.services.codex_agent.codex_cli_adapter.subprocess.run", fake_run)
    config = CodexAgentRuntimeConfig(
        enabled=True,
        cli_path="codex",
        default_workdir=str(tmp_path),
        timeout_seconds=30,
        require_approval_for_write=True,
        require_approval_for_shell=True,
        allow_read=True,
        allow_write=True,
        allow_shell=True,
        use_staging_worktree=True,
        max_output_chars=20000,
        history_retention_days=90,
        history_context_messages=20,
        history_context_chars=24000,
    )

    result = CodexCliAdapter("ready_or_help_available").run_prompt(
        prompt="Explique a estrutura.",
        config=config,
        workdir=str(tmp_path),
    )

    command = captured["command"]
    assert result.status == "completed"
    assert result.text == "Resposta segura."
    assert command[:4] == ["codex", "--ask-for-approval", "never", "exec"]
    assert "--json" in command
    assert "--skip-git-repo-check" in command
    sandbox_index = command.index("--sandbox")
    assert ["--sandbox", "read-only"] == command[sandbox_index : sandbox_index + 2]
    assert "--ask-for-approval" in command
    assert captured["kwargs"].get("shell") is None
    assert "auth.json" not in " ".join(command)


def test_codex_exec_keeps_git_repository_check_for_git_worktree(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        payload = {
            "type": "item.completed",
            "item": {"id": "item_final", "type": "agent_message", "text": "Resposta segura."},
        }
        return type("Completed", (), {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""})()

    monkeypatch.setattr("aipinho.services.codex_agent.codex_cli_adapter.subprocess.run", fake_run)
    config = CodexAgentRuntimeConfig(
        enabled=True,
        cli_path="codex",
        default_workdir=str(tmp_path),
        timeout_seconds=30,
        require_approval_for_write=True,
        require_approval_for_shell=True,
        allow_read=True,
        allow_write=True,
        allow_shell=True,
        use_staging_worktree=True,
        max_output_chars=20000,
        history_retention_days=90,
        history_context_messages=20,
        history_context_chars=24000,
    )

    result = CodexCliAdapter("ready_or_help_available").run_prompt(
        prompt="Explique a estrutura.",
        config=config,
        workdir=str(tmp_path),
    )

    assert result.status == "completed"
    assert "--skip-git-repo-check" not in captured["command"]


def test_codex_governed_proposal_uses_readonly_sandbox_and_output_schema(
    tmp_path, monkeypatch
):
    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        payload = {
            "type": "item.completed",
            "item": {
                "id": "item_final",
                "type": "agent_message",
                "text": json.dumps(
                    {
                        "objective": "Create a file.",
                        "actions": [
                            {
                                "action_type": "create_file",
                                "target_path": "notes.txt",
                                "content": "hello",
                                "argv": [],
                                "expected_side_effects": ["create_file"],
                                "validation_required": True,
                                "metadata": {},
                            }
                        ],
                    }
                ),
            },
        }
        return type(
            "Completed",
            (),
            {"returncode": 0, "stdout": json.dumps(payload), "stderr": ""},
        )()

    monkeypatch.setattr(
        "aipinho.services.codex_agent.codex_cli_adapter.subprocess.run", fake_run
    )
    config = CodexAgentRuntimeConfig(
        enabled=True,
        cli_path="codex",
        default_workdir=str(tmp_path),
        timeout_seconds=30,
        require_approval_for_write=True,
        require_approval_for_shell=True,
        allow_read=True,
        allow_write=True,
        allow_shell=True,
        use_staging_worktree=True,
        max_output_chars=20000,
        history_retention_days=90,
        history_context_messages=20,
        history_context_chars=24000,
    )
    schema = tmp_path / "schema.json"
    schema.write_text("{}", encoding="utf-8")

    proposal = CodexCliAdapter(
        "ready_or_help_available"
    ).run_governed_proposal(
        prompt="Create a file.",
        config=config,
        workdir=str(tmp_path),
        output_schema_path=schema,
    )

    command = captured["command"]
    assert proposal.result.status == "completed"
    assert proposal.payload["actions"][0]["action_type"] == "create_file"
    assert command[command.index("--sandbox") : command.index("--sandbox") + 2] == [
        "--sandbox",
        "read-only",
    ]
    assert command[command.index("--output-schema") + 1] == str(schema)


def test_codex_exec_surfaces_sanitized_stderr_on_failure(tmp_path, monkeypatch):
    def fake_run(command, **kwargs):
        return type(
            "Completed",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": "Workspace sem repositorio Git valido.",
            },
        )()

    monkeypatch.setattr("aipinho.services.codex_agent.codex_cli_adapter.subprocess.run", fake_run)
    config = CodexAgentRuntimeConfig(
        enabled=True,
        cli_path="codex",
        default_workdir=str(tmp_path),
        timeout_seconds=30,
        require_approval_for_write=True,
        require_approval_for_shell=True,
        allow_read=True,
        allow_write=True,
        allow_shell=True,
        use_staging_worktree=True,
        max_output_chars=20000,
        history_retention_days=90,
        history_context_messages=20,
        history_context_chars=24000,
    )

    result = CodexCliAdapter("ready_or_help_available").run_prompt(
        prompt="Explique a estrutura.",
        config=config,
        workdir=str(tmp_path),
    )

    assert result.status == "failed"
    assert result.text == "Workspace sem repositorio Git valido."


def test_codex_side_effect_capability_requires_governed_policy(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(
        CodexAgentRequest(
            session_id=session.session_id,
            prompt="Crie um patch.",
            requested_capabilities=["create_patch_preview"],
        )
    )

    assert response.structured_actions
    assert response.structured_actions[0]["requires_approval"] is True
    assert response.structured_actions[0]["validation_required"] is True


def test_codex_send_creates_run_events_and_incremental_polling(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(CodexAgentRequest(session_id=session.session_id, prompt="Leia o contexto.", requested_capabilities=["read_workspace"]))

    assert response.run_id
    events = service.events(response.run_id)
    assert [event.event_type for event in events][:3] == ["codex_run_created", "codex_run_started", "codex_run_autorun_enabled"]
    assert any(event.event_type == "codex_auto_approval_granted" for event in events)
    after_first = service.events(response.run_id, after_event_id=events[0].event_id)
    assert all(event.event_id != events[0].event_id for event in after_first)
    view_model = service.mobile_view_model(session.session_id, after_event_id=events[0].event_id)
    assert view_model["raw_default_visible"] is False
    assert view_model["token_in_url"] is False
    assert view_model["active_run"]["run_id"] == response.run_id


def test_codex_tool_request_runs_through_gateway_and_registers_artifact(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(
        CodexAgentRequest(
            session_id=session.session_id,
            prompt="Crie um artifact governado com a resposta.",
            requested_capabilities=["artifact_create"],
            tool_requests=[
                {
                    "tool_name": "create_artifact",
                    "input": {"filename": "answer.txt", "content": "4"},
                    "metadata_sanitized": {"source": "unit_test"},
                }
            ],
        )
    )

    assert response.status == "completed"
    assert response.artifact_ids
    artifact = service.artifacts(session.session_id)[0]
    assert artifact.requires_token is True
    assert artifact.download_endpoint == f"/api/v1/agents/artifacts/{artifact.artifact_id}/download"
    assert "token" not in artifact.download_endpoint.lower()
    events = service.events(response.run_id)
    assert any(event.event_type == "codex_tool_requested" for event in events)
    assert any(event.event_type == "codex_tool_succeeded" for event in events)
    assert any(event.event_type == "codex_memory_candidate_created" for event in events)


def test_codex_cancel_run_records_visible_terminal_state(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()
    run = service.store.create_run(
        session_id=session.session_id,
        user_prompt="Tarefa longa",
        workspace_path=None,
        requested_capabilities=[],
        autorun_enabled=True,
        autoreview_enabled=True,
        autoapproval_enabled=True,
        autopilot_mode="governed_autorun",
    )

    result = service.cancel_run(run.run_id)

    assert result["status"] == "ok"
    assert result["run"]["status"] == "cancelled"
    assert service.events(run.run_id)[0].event_type == "codex_run_cancelled"


def test_codex_artifact_upload_registers_artifact_without_public_token_url(tmp_path, monkeypatch):
    class FakeArtifactUploadService:
        def upload(self, request):
            artifact = ArtifactRecord(
                filename=request.filename,
                content_type=request.content_type,
                size_bytes=len(request.content),
                sha256=hashlib.sha256(request.content.encode("utf-8")).hexdigest(),
                storage_path=f"test/{request.filename}",
                metadata=request.metadata,
            )
            return ArtifactUploadResponse(
                artifact=artifact,
                download_path=f"/api/v1/artifacts/{artifact.artifact_id}/download",
            )

    monkeypatch.setattr(
        "aipinho.services.codex_agent.codex_agent_service.ArtifactUploadService",
        FakeArtifactUploadService,
    )
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    artifact = service.attach_uploaded_artifact(
        session_id=session.session_id,
        filename="context.txt",
        content=b"hello",
        content_type="text/plain",
    )

    assert artifact.artifact_id.startswith("artifact_")
    assert artifact.requires_token is True
    assert artifact.download_endpoint == f"/api/v1/artifacts/{artifact.artifact_id}/download"
    assert "token" not in artifact.download_endpoint.lower()
    assert service.artifacts(session.session_id)[0].artifact_id == artifact.artifact_id
