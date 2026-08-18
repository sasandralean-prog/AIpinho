from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.delegation import DelegationCreateRequest
from aipinho.schemas.artifacts.artifact_generation import ArtifactRequest
from aipinho.schemas.debugger.multi_island_trace import TraceExportRequest
from aipinho.services.agents.agent_delegation_service import AgentDelegationService, AgentDelegationStore
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.artifacts.artifact_generator_service import ArtifactGeneratorService
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.debugger.multi_island_trace_service import MultiIslandTraceService


def _env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy_kernel"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events" / "store"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "events" / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "events" / "audit"))
    monkeypatch.setenv("AIPINHO_WORKSPACE_LOCK_ROOT", str(tmp_path / "locks"))
    monkeypatch.setenv("AIPINHO_AGENT_LUCIO_ENABLED", "true")
    monkeypatch.setenv("AIPINHO_AGENT_AIPINHO_ENABLED", "true")


def _artifact_registry() -> UniversalArtifactRegistryService:
    suffix = uuid4().hex
    return UniversalArtifactRegistryService(
        registry=ArtifactRegistryRepository(PATHS.project_root / "data" / "test_artifacts" / f"registry_sprint89_{suffix}.json"),
        store_root=PATHS.project_root / "data" / "test_artifacts" / f"universal_sprint89_{suffix}",
    )


def _kernel(tmp_path: Path) -> AgentSessionKernelService:
    return AgentSessionKernelService(store=AgentSessionStore(tmp_path / "agent_kernel"))


def test_artifact_generator_creates_markdown_for_lucio_gemini_codex_and_aipinho(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    generator = ArtifactGeneratorService(_artifact_registry())

    for agent_id, filename in [
        ("lucio", "lucio_plan.md"),
        ("gemini", "gemini_brainstorm.md"),
        ("codex", "codex_report.md"),
        ("aipinho", "aipinho_execution.md"),
    ]:
        result = generator.generate(
            ArtifactRequest(
                source_agent=agent_id,
                artifact_type="markdown_report",
                requested_filename=filename,
                content_source="inline",
                content_inline=f"# {agent_id}\n\nconteudo validado",
            )
        )

        assert result.status == "READY"
        assert result.artifact_id
        assert result.size_bytes > 0
        assert result.provenance["source_agent"] == agent_id
        assert result.provenance["executor_agent"] == agent_id
        assert result.download_endpoint == f"/api/v1/artifacts/{result.artifact_id}/download"


def test_zip_evidence_validates_entries_and_delegated_provenance(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    source = tmp_path / "evidence.log"
    source.write_text("build ok", encoding="utf-8")
    generator = ArtifactGeneratorService(_artifact_registry())

    result = generator.generate(
        ArtifactRequest(
            source_agent="codex",
            bridge_task_id="delegation_test",
            owner_task_id="run_test",
            artifact_type="zip_evidence",
            requested_filename="evidence.zip",
            content_source="source_paths",
            source_paths=[str(source)],
            workspace=str(tmp_path),
        )
    )

    assert result.status == "READY"
    assert result.content_type == "application/zip"
    assert result.size_bytes > 0
    assert result.provenance["bridge_task_id"] == "delegation_test"
    assert result.artifact_refs[0]["bridge_task_id"] == "delegation_test"


def test_artifact_ready_requires_nonzero_file_and_revalidation_marks_missing(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    registry = _artifact_registry()
    generator = ArtifactGeneratorService(registry)
    blocked = generator.generate(
        ArtifactRequest(
            source_agent="gemini",
            artifact_type="text_export",
            requested_filename="empty.txt",
            content_source="inline",
            content_inline="",
        )
    )
    ready = generator.generate(
        ArtifactRequest(
            source_agent="gemini",
            artifact_type="text_export",
            requested_filename="real.txt",
            content_source="inline",
            content_inline="conteudo",
        )
    )
    Path(str(ready.local_path)).unlink()
    revalidated = registry.revalidate(str(ready.artifact_id))

    assert blocked.status == "BLOCKED"
    assert "ready_artifact_must_have_non_empty_file" in blocked.validation_errors
    assert revalidated is not None
    assert revalidated["status"] == "missing"


def test_artifact_generator_rejects_path_traversal_and_secret_content(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    generator = ArtifactGeneratorService(_artifact_registry())

    traversal = generator.generate(
        ArtifactRequest(
            source_agent="aipinho",
            artifact_type="text_export",
            requested_filename="../escape.txt",
            content_source="inline",
            content_inline="ok",
        )
    )
    secret = generator.generate(
        ArtifactRequest(
            source_agent="aipinho",
            artifact_type="text_export",
            requested_filename="secret.txt",
            content_source="inline",
            content_inline="OPENAI_API_KEY=sk-proj-secret",
        )
    )

    assert traversal.status == "BLOCKED"
    assert secret.status == "BLOCKED"
    assert "secret_detected" in secret.validation_errors[0]


def test_debugger_trace_links_bridge_task_run_artifact_and_exports(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    kernel = _kernel(tmp_path)
    delegations = AgentDelegationService(store=AgentDelegationStore(tmp_path / "delegations"), kernel=kernel)
    registry = _artifact_registry()
    generator = ArtifactGeneratorService(registry)
    trace_service = MultiIslandTraceService(
        sessions=kernel.store,
        delegations=delegations.store,
        artifacts=registry,
        generator=generator,
    )
    parent_session = kernel.create_session("lucio", AgentSessionCreateRequest(title="Lucio"))
    parent = kernel.create_run("lucio", parent_session.session_id, AgentRunCreateRequest(operation_type="readonly_analysis", status="running"))
    delegation = delegations.create_delegation(
        "lucio",
        parent.run_id,
        DelegationCreateRequest(
            target_agent_id="aipinho",
            user_goal="analise",
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
    exported = trace_service.export(parent.run_id, TraceExportRequest(format="markdown"))

    assert trace.source_agent == "lucio"
    assert trace.target_agent == "aipinho"
    assert trace.bridge_task_id == delegation.delegation_id
    assert trace.artifacts[0]["artifact_id"] == artifact.artifact_id
    assert trace.final_answer == "Resposta final confirmada."
    assert exported.status == "READY"
    assert exported.artifact_id


def test_debugger_recent_endpoint_and_agent_artifact_endpoint(tmp_path, monkeypatch) -> None:
    _env(monkeypatch, tmp_path)
    client = TestClient(create_app())
    kernel = AgentSessionKernelService()
    session = kernel.create_session("codex", AgentSessionCreateRequest(title="Trace endpoint"))
    run = kernel.create_run("codex", session.session_id, AgentRunCreateRequest(operation_type="technical_report", status="completed"))

    generated = client.post(
        "/api/v1/agents/codex/artifacts",
        json={
            "source_agent": "codex",
            "owner_task_id": run.run_id,
            "artifact_type": "markdown_report",
            "requested_filename": f"codex_{uuid4().hex}.md",
            "content_source": "inline",
            "content_inline": "# Codex\n\nok",
        },
    )
    recent = client.get("/api/v1/debugger/recent", params={"limit": 10})
    by_agent = client.get("/api/v1/debugger/by-agent/codex", params={"limit": 10})

    assert generated.status_code == 200
    assert generated.json()["result"]["status"] == "READY"
    assert recent.status_code == 200
    assert by_agent.status_code == 200
    assert any(item["run_id"] == run.run_id for item in by_agent.json()["traces"])
