from __future__ import annotations

from aipinho.schemas.agents.contracts import AgentSessionCreateRequest
from aipinho.schemas.skills.contracts import SkillExecutionRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.skills.skill_execution_service import SkillExecutionService
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService


def _session(kernel: AgentSessionKernelService):
    return kernel.create_session("aipinho", AgentSessionCreateRequest(title="skill test"))


def test_safe_report_skill_executes_through_tool_gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    registry = SkillManifestRegistryService(root=tmp_path / "registry")
    kernel = AgentSessionKernelService()
    session = _session(kernel)
    service = SkillExecutionService(registry=registry, kernel=kernel, executions_root=tmp_path / "executions")

    result = service.execute(
        SkillExecutionRequest(
            skill_id="internal.safe_markdown_report_generator",
            requesting_agent_id="aipinho",
            session_id=session.session_id,
            user_goal="Create a governed report artifact.",
            requested_capabilities=["report_generate", "artifact_create"],
            inputs={"title": "Governed report", "summary": "A reusable report artifact."},
        )
    )

    assert result.status == "completed"
    assert result.real_execution_performed is True
    assert result.output_artifact_refs
    assert result.tool_invocation_ids
    assert result.policy_decision_ids
    assert result.speaker_truth_status == "raw_hidden_by_default"


def test_skill_execution_blocks_missing_capability(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    registry = SkillManifestRegistryService(root=tmp_path / "registry")
    kernel = AgentSessionKernelService()
    session = _session(kernel)
    service = SkillExecutionService(registry=registry, kernel=kernel, executions_root=tmp_path / "executions")

    result = service.execute(
        SkillExecutionRequest(
            skill_id="internal.safe_markdown_report_generator",
            requesting_agent_id="aipinho",
            session_id=session.session_id,
            requested_capabilities=["report_generate"],
        )
    )

    assert result.status == "blocked"
    assert "missing_capability:artifact_create" in result.blocked_reasons
    assert not result.output_artifact_refs


def test_disabled_skill_is_not_executable(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    registry = SkillManifestRegistryService(root=tmp_path / "registry")
    registry.set_status("internal.safe_markdown_report_generator", "disabled")
    kernel = AgentSessionKernelService()
    session = _session(kernel)
    service = SkillExecutionService(registry=registry, kernel=kernel, executions_root=tmp_path / "executions")

    result = service.execute(
        SkillExecutionRequest(
            skill_id="internal.safe_markdown_report_generator",
            requesting_agent_id="aipinho",
            session_id=session.session_id,
            requested_capabilities=["report_generate", "artifact_create"],
        )
    )

    assert result.status == "blocked"
    assert "skill_status_disabled_not_executable" in result.blocked_reasons


def test_validation_runner_requires_validation_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    registry = SkillManifestRegistryService(root=tmp_path / "registry")
    kernel = AgentSessionKernelService()
    session = _session(kernel)
    service = SkillExecutionService(registry=registry, kernel=kernel, executions_root=tmp_path / "executions")

    result = service.execute(
        SkillExecutionRequest(
            skill_id="internal.validation_runner",
            requesting_agent_id="aipinho",
            session_id=session.session_id,
            user_goal="Record validation.",
            requested_capabilities=["validation", "run_tests", "report_generate"],
            inputs={"name": "focused_validation", "status": "passed"},
        )
    )

    assert result.status == "completed"
    assert result.validation_ids
    assert result.output_artifact_refs
