from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.agents.hybrid_execution import CodexModeSelectRequest, IslandChatRequest
from aipinho.schemas.agents.ownership import AgentHopCheckRequest, WorkspaceLockCreateRequest
from aipinho.schemas.artifacts.artifact_generation import ArtifactRequest
from aipinho.services.agents.agent_delegation_service import AgentDelegationService, AgentDelegationStore
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_text_artifact_service import AgentTextArtifactService
from aipinho.services.agents.codex_hybrid_service import CodexHybridService
from aipinho.services.agents.interpretation_agent_service import InterpretationAgentService
from aipinho.services.agents.workspace_lock_service import WorkspaceLockService, WorkspaceLockStore
from aipinho.services.artifacts.artifact_generator_service import ArtifactGeneratorService
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.debugger.multi_island_trace_service import MultiIslandTraceService
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
    monkeypatch.setenv("AIPINHO_GEMINI_EXECUTOR_ROOT", str(tmp_path / "gemini"))
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


def _registry(tmp_path: Path) -> UniversalArtifactRegistryService:
    suffix = uuid4().hex
    return UniversalArtifactRegistryService(
        registry=ArtifactRegistryRepository(PATHS.project_root / "data" / "test_artifacts" / f"registry_sprint1011_{suffix}.json"),
        store_root=PATHS.project_root / "data" / "test_artifacts" / f"universal_sprint1011_{suffix}",
    )


def _interpretation_service(tmp_path: Path, kernel: AgentSessionKernelService, delegations: AgentDelegationService) -> InterpretationAgentService:
    return InterpretationAgentService(
        kernel=kernel,
        delegations=delegations,
        artifacts=AgentTextArtifactService(registry=_registry(tmp_path)),
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


def test_sprint11_simple_chat_stays_inside_lucio_and_gemini(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    delegations = _delegations(tmp_path, kernel)
    service = _interpretation_service(tmp_path, kernel, delegations)

    lucio = service.chat("lucio", IslandChatRequest(message="Me ajude a decidir o proximo sprint.", mode="chat"))
    gemini = service.chat("gemini", IslandChatRequest(message="Me de tres ideias de nomes.", mode="chat"))

    assert lucio.delegated is False
    assert lucio.executor_agent == "lucio"
    assert gemini.delegated is False
    assert gemini.executor_agent == "gemini"
    assert delegations.store.list_requests() == []


def test_sprint11_operational_lucio_and_gemini_delegate_to_aipinho(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    delegations = _delegations(tmp_path, kernel)
    service = _interpretation_service(tmp_path, kernel, delegations)

    for agent_id in ["lucio", "gemini"]:
        response = service.chat(
            agent_id,
            IslandChatRequest(
                message="Use a AIpinho para criar um arquivo governado.",
                workspace=str(tmp_path / "workspace"),
                operation_type="workspace_operation",
                requested_capabilities=["create_file", "validation"],
            ),
        )

        assert response.delegated is True
        assert response.executor_agent == "aipinho"
        assert response.bridge_task_id
        assert response.events_poll_url and response.events_poll_url.endswith("/details")


def test_sprint11_codex_mode_matrix_respects_owner_and_locks(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    locks = WorkspaceLockService(WorkspaceLockStore(tmp_path / "locks"))
    service = CodexHybridService(kernel=kernel, delegations=_delegations(tmp_path, kernel), locks=locks)
    workspace = str(tmp_path / "workspace")

    assert service.select_mode(CodexModeSelectRequest(user_prompt="Explique patch.")).selected_mode == "codex_observe_only"
    assert service.select_mode(CodexModeSelectRequest(user_prompt="Crie arquivo.", workspace=workspace, available_capabilities=["create_file"])).selected_mode == "codex_direct_executor"
    assert service.select_mode(CodexModeSelectRequest(user_prompt="Rode build.", workspace=workspace, available_capabilities=["build"])).selected_mode == "codex_delegated_to_aipinho"
    assert service.select_mode(CodexModeSelectRequest(user_prompt="Diagnostique e corrija.", workspace=workspace, available_capabilities=["patch_preview", "validation"])).selected_mode == "codex_hybrid_supervisor"

    locks.create(WorkspaceLockCreateRequest(workspace=workspace, owner_agent="aipinho", owner_task_id="run_a"))
    locked = service.select_mode(CodexModeSelectRequest(user_prompt="Crie arquivo.", workspace=workspace, available_capabilities=["create_file"]))
    assert locked.selected_mode == "codex_observe_only"
    assert locked.reason_code == "workspace_locked_by_other_agent"


def test_sprint11_loop_guard_and_false_ready_guard(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    locks = WorkspaceLockService(WorkspaceLockStore(tmp_path / "locks"))
    hop = locks.check_hop(AgentHopCheckRequest(source_agent="aipinho", target_agent="lucio", lineage=["lucio"]))
    assert hop.allowed is False
    assert hop.reason_code == "recursion_blocked"

    generator = ArtifactGeneratorService(_registry(tmp_path))
    result = generator.generate(
        ArtifactRequest(
            source_agent="aipinho",
            artifact_type="text_export",
            requested_filename="missing.txt",
            content_source="inline",
            content_inline="",
        )
    )
    assert result.status == "BLOCKED"
    assert "ready_artifact_must_have_non_empty_file" in result.validation_errors


def test_sprint10_trace_links_delegation_artifact_and_final_answer(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    delegations = _delegations(tmp_path, kernel)
    registry = _registry(tmp_path)
    generator = ArtifactGeneratorService(registry)
    trace_service = MultiIslandTraceService(
        sessions=kernel.store,
        delegations=delegations.store,
        artifacts=registry,
        generator=generator,
    )
    parent_session = kernel.create_session("lucio", AgentSessionCreateRequest(title="Lucio"))
    parent_run = kernel.create_run("lucio", parent_session.session_id, AgentRunCreateRequest(operation_type="readonly_analysis", status="running"))
    delegation = delegations.create_delegation(
        "lucio",
        parent_run.run_id,
        DelegationCreateRequest(
            target_agent_id="aipinho",
            user_goal="analise governada",
            requested_operation="readonly_analysis",
            operation_type="readonly_analysis",
            capabilities_requested=["read_workspace"],
            execution_mode="governed_autorun",
        ),
    ).delegation
    artifact = generator.generate(
        ArtifactRequest(
            source_agent="aipinho",
            owner_task_id=delegation.child_run_id,
            bridge_task_id=delegation.delegation_id,
            artifact_type="markdown_report",
            requested_filename="report.md",
            content_source="inline",
            content_inline="# Report\n\nok",
        )
    )
    kernel.add_event(
        delegation.child_run_id,
        AgentEventCreateRequest(
            event_type="artifact_ready",
            status="ready",
            severity="info",
            human_message="Artifact pronto.",
            artifact_ids=[str(artifact.artifact_id)],
            delegation_id=delegation.delegation_id,
        ),
    )
    kernel.add_event(
        delegation.child_run_id,
        AgentEventCreateRequest(
            event_type="final_answer",
            status="completed",
            severity="info",
            human_message="Resposta final confirmada.",
        ),
    )

    trace = trace_service.by_bridge_task(delegation.delegation_id)

    assert trace.source_agent == "lucio"
    assert trace.target_agent == "aipinho"
    assert trace.bridge_task_id == delegation.delegation_id
    assert trace.artifacts[0]["artifact_id"] == artifact.artifact_id
    assert trace.final_answer == "Resposta final confirmada."
    assert trace.raw_default_visible is False


