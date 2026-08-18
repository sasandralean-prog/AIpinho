from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from aipinho.schemas.agents.hybrid_execution import (
    CodexDelegationRequest,
    CodexDiagnosticRequest,
    CodexModeSelectRequest,
    IslandChatRequest,
)
from aipinho.schemas.agents.ownership import AgentHopCheckRequest, WorkspaceLockCreateRequest
from aipinho.core.paths import PATHS
from aipinho.schemas.codex_agent import CodexAgentRequest
from aipinho.services.agents.agent_delegation_service import AgentDelegationService, AgentDelegationStore
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_text_artifact_service import AgentTextArtifactService
from aipinho.services.agents.codex_hybrid_service import CodexHybridService
from aipinho.services.agents.delegation_log_summary_service import DelegationLogSummaryService
from aipinho.services.agents.interpretation_agent_service import InterpretationAgentService
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService, WorkspaceLockStore
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.codex_agent.codex_agent_config_service import CodexAgentConfigService
from aipinho.services.codex_agent.codex_agent_service import CodexAgentService
from aipinho.services.codex_agent.codex_agent_store import CodexAgentStore
from aipinho.services.codex_agent.codex_cli_adapter import FakeCodexCliAdapter
from aipinho.services.gemini_executor import GeminiExecutorService
from aipinho.services.gemini_executor.gemini_executor_client import FakeGeminiClient
from aipinho.services.gemini_executor.gemini_executor_session_store import GeminiExecutorSessionStore
from aipinho.services.lucio_agent import LucioAgentService
from aipinho.services.lucio_agent.lucio_agent_config_service import LucioAgentConfigService
from aipinho.services.lucio_agent.lucio_openai_client import FakeLucioClient


def _env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "memory"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events" / "store"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "events" / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "events" / "audit"))
    monkeypatch.setenv("AIPINHO_WORKSPACE_LOCK_ROOT", str(tmp_path / "locks"))
    monkeypatch.setenv("AIPINHO_CODEX_AGENT_ROOT", str(tmp_path / "codex"))
    monkeypatch.setenv("AIPINHO_GEMINI_EXECUTOR_ROOT", str(tmp_path / "gemini"))
    monkeypatch.setenv("CODEX_AGENT_ENABLED", "true")
    monkeypatch.setenv("CODEX_AGENT_ALLOW_READ", "true")
    monkeypatch.setenv("CODEX_AGENT_ALLOW_WRITE", "true")
    monkeypatch.setenv("CODEX_AGENT_ALLOW_SHELL", "true")
    monkeypatch.setenv("CODEX_AGENT_DEFAULT_WORKDIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LUCIO_ENABLED", "true")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "true")
    monkeypatch.setenv("LUCIO_PROVIDER", "openai")
    monkeypatch.setenv("LUCIO_ALLOW_NEW_SESSIONS", "true")
    monkeypatch.setenv("LUCIO_AGENT_USE_DELEGATION", "true")
    monkeypatch.setenv("GEMINI_EXECUTOR_ENABLED", "true")


def _kernel(tmp_path: Path) -> AgentSessionKernelService:
    return AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))


def _delegations(tmp_path: Path, kernel: AgentSessionKernelService) -> AgentDelegationService:
    return AgentDelegationService(store=AgentDelegationStore(tmp_path / "delegations"), kernel=kernel)


def _artifacts() -> UniversalArtifactRegistryService:
    suffix = uuid4().hex
    return UniversalArtifactRegistryService(
        registry=ArtifactRegistryRepository(PATHS.project_root / "data" / "test_artifacts" / f"registry_{suffix}.json"),
        store_root=PATHS.project_root / "data" / "test_artifacts" / f"universal_{suffix}",
    )


def test_codex_mode_selects_expected_modes_and_observe_when_locked(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    locks = WorkspaceLockService(WorkspaceLockStore(tmp_path / "locks"))
    service = CodexHybridService(kernel=_kernel(tmp_path), delegations=_delegations(tmp_path, _kernel(tmp_path)), locks=locks)

    direct = service.select_mode(
        CodexModeSelectRequest(user_prompt="gere patch", workspace=str(tmp_path), available_capabilities=["patch_preview"])
    )
    delegated = service.select_mode(
        CodexModeSelectRequest(user_prompt="rode build", workspace=str(tmp_path), available_capabilities=["run_tests", "validation"])
    )
    hybrid = service.select_mode(
        CodexModeSelectRequest(user_prompt="diagnostique e corrija", workspace=str(tmp_path), available_capabilities=["patch_preview", "validation"])
    )
    locks.create(WorkspaceLockCreateRequest(workspace=str(tmp_path), owner_agent="aipinho", owner_task_id="run_aipinho"))
    locked = service.select_mode(
        CodexModeSelectRequest(user_prompt="gere patch", workspace=str(tmp_path), available_capabilities=["patch_preview"])
    )

    assert direct.selected_mode == "codex_direct_executor"
    assert delegated.selected_mode == "codex_delegated_to_aipinho"
    assert hybrid.selected_mode == "codex_hybrid_supervisor"
    assert locked.selected_mode == "codex_observe_only"
    assert locked.reason_code == "workspace_locked_by_other_agent"


def test_codex_delegation_creates_aipinho_lock_for_write_ownership(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    locks = WorkspaceLockService(WorkspaceLockStore(tmp_path / "locks"))
    service = CodexHybridService(
        kernel=kernel,
        delegations=_delegations(tmp_path, kernel),
        locks=locks,
        artifacts=_artifacts(),
    )

    result = service.delegate_to_aipinho(
            CodexDelegationRequest(
                user_prompt="crie um arquivo governado",
                workspace=str(tmp_path / "workspace"),
                requested_operation="workspace_operation",
                requested_capabilities=["create_file", "write_file"],
            )
    )

    assert result["status"] == "running"
    assert result["bridge_task_id"].startswith("delegation_")
    active_locks = locks.list()
    assert len(active_locks) == 1
    assert active_locks[0].owner_agent == "aipinho"
    assert active_locks[0].bridge_task_id == result["bridge_task_id"]


def test_codex_diagnostics_are_readonly_delegation_with_log_summary(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    service = CodexHybridService(kernel=kernel, delegations=_delegations(tmp_path, kernel), artifacts=_artifacts())

    result = service.collect_diagnostics(
        CodexDiagnosticRequest(user_prompt="colete diagnosticos", workspace=str(tmp_path / "workspace"))
    )

    assert result["status"] == "running"
    assert result["raw_default_visible"] is False
    assert result["log_summary"]["status"] == "running"
    assert result["final_answer"] is None


def test_codex_direct_write_is_blocked_by_other_agent_workspace_lock(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    locks = WorkspaceLockService(WorkspaceLockStore(tmp_path / "locks"))
    workspace = str(tmp_path / "workspace")
    locks.create(WorkspaceLockCreateRequest(workspace=workspace, owner_agent="aipinho", owner_task_id="task_a"))
    service = CodexAgentService(
        config_service=CodexAgentConfigService(policy_path=tmp_path / "missing.yaml"),
        store=CodexAgentStore(tmp_path / "codex_store"),
        adapter=FakeCodexCliAdapter(),
        workspace_locks=locks,
    )
    service._publish = lambda *args, **kwargs: None
    session = service.create_session("Codex")

    response = service.send(
        CodexAgentRequest(
            session_id=session.session_id,
            prompt="crie um arquivo",
            workspace_context=workspace,
            requested_capabilities=["create_file"],
        )
    )

    assert response.status == "blocked"
    assert response.error_code == "codex_workspace_locked_by_other_agent"


def test_lucio_and_gemini_simple_chat_stay_in_their_islands(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    delegations = _delegations(tmp_path, kernel)
    service = InterpretationAgentService(
        kernel=kernel,
        delegations=delegations,
        lucio=LucioAgentService(
            config_service=LucioAgentConfigService(),
            client=FakeLucioClient(),
            kernel=kernel,
            delegation_service=delegations,
        ),
        gemini=GeminiExecutorService(
            session_store=GeminiExecutorSessionStore(tmp_path / "gemini_store"),
            client=FakeGeminiClient(),
            agent_kernel=kernel,
            delegation_service=delegations,
        ),
    )

    lucio = service.chat("lucio", IslandChatRequest(message="Explique em uma frase.", mode="chat"))
    gemini = service.chat("gemini", IslandChatRequest(message="Explique em uma frase.", mode="chat"))

    assert lucio.delegated is False
    assert lucio.executor_agent == "lucio"
    assert "Lucio analisou" in lucio.response_text
    assert gemini.delegated is False
    assert gemini.executor_agent == "gemini"
    assert "Gemini Executor recebeu" in gemini.response_text


def test_interpretation_agents_delegate_operational_requests_to_aipinho(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    delegations = _delegations(tmp_path, kernel)
    service = InterpretationAgentService(kernel=kernel, delegations=delegations)

    response = service.chat(
        "lucio",
        IslandChatRequest(
            message="analise o workspace e gere validacao",
            workspace=str(tmp_path / "workspace"),
            operation_type="readonly_analysis",
            requested_capabilities=["read_workspace", "validation"],
        ),
    )

    assert response.delegated is True
    assert response.executor_agent == "aipinho"
    assert response.bridge_task_id
    assert response.events_poll_url and response.events_poll_url.endswith("/details")


def test_interpretation_text_artifact_is_registered_with_source_agent(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    artifacts = AgentTextArtifactService(registry=_artifacts())
    service = InterpretationAgentService(kernel=kernel, delegations=_delegations(tmp_path, kernel), artifacts=artifacts)

    response = service.chat(
        "gemini",
        IslandChatRequest(message="Resumo textual governado", mode="artifact_text", artifact_filename="resumo.md"),
    )

    assert response.delegated is False
    assert response.executor_agent == "gemini"
    assert response.artifact_refs
    artifact = response.artifact_refs[0]
    assert artifact["source_agent"] == "gemini"
    assert artifact["requires_token"] is True


def test_hop_guard_blocks_interpretation_delegation_loops(tmp_path) -> None:
    locks = WorkspaceLockService(WorkspaceLockStore(tmp_path / "locks"))

    decision = locks.check_hop(AgentHopCheckRequest(source_agent="aipinho", target_agent="lucio", lineage=["lucio"]))

    assert decision.allowed is False
    assert decision.reason_code == "recursion_blocked"


def test_delegation_log_summary_extracts_errors_files_commands_and_artifacts() -> None:
    service = DelegationLogSummaryService()
    events = [
        SimpleNamespace(
            severity="error",
            human_message="Falha no build",
            payload_sanitized={"files_changed": ["src/app.py"], "command": "pytest -q", "exit_code": 1},
        )
    ]
    artifacts = [{"artifact_id": "artifact_1"}]

    summary = service.summarize(status="failed", events=events, artifacts=artifacts, max_items=5)

    assert summary.top_errors == ["Falha no build"]
    assert summary.files_touched == ["src/app.py"]
    assert summary.commands == ["pytest -q"]
    assert summary.exit_code == 1
    assert summary.artifact_refs == ["artifact_1"]
    assert summary.full_log_artifact_id is None
