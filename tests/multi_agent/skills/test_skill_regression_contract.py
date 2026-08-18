from __future__ import annotations

from aipinho.schemas.agents.contracts import AgentSessionCreateRequest
from aipinho.schemas.skills.contracts import SkillExecutionRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.skills.skill_execution_service import SkillExecutionService
from aipinho.services.skills.skill_manifest_registry_service import SkillManifestRegistryService


def test_internal_skill_execution_keeps_policy_trace_and_raw_hidden(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    registry = SkillManifestRegistryService(root=tmp_path / "registry")
    kernel = AgentSessionKernelService()
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="skills regression"))
    service = SkillExecutionService(registry=registry, kernel=kernel, executions_root=tmp_path / "executions")

    result = service.execute(
        SkillExecutionRequest(
            skill_id="internal.safe_markdown_report_generator",
            requesting_agent_id="aipinho",
            session_id=session.session_id,
            requested_capabilities=["report_generate", "artifact_create"],
            inputs={"summary": "Regression evidence"},
        )
    )

    trace = service.trace(result.skill_execution_id)

    assert result.status == "completed"
    assert result.policy_decision_ids
    assert result.output_artifact_refs
    assert trace is not None
    assert trace["raw_default_visible"] is False
    assert f"skill_execution:{result.skill_execution_id}" in trace["evidence_refs"]
