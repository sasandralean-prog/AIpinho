from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import PolicyDecision, ToolDefinition, WorkspaceResolution
from aipinho.services.agents.multi_agent_policy_kernel_service import MultiAgentPolicyKernelService


class AgentToolPolicyDecisionService:
    """Compatibility adapter from Sprint 3 Tool Gateway to Sprint 4 Policy Kernel."""

    def __init__(self, path: Path | None = None, *, root: Path | None = None, kernel: MultiAgentPolicyKernelService | None = None) -> None:
        self.path = path or PATHS.config_root / "agents" / "tool_gateway_policy.yaml"
        self.root = root or PATHS.config_root
        self.kernel = kernel or MultiAgentPolicyKernelService(root=self.root)

    def evaluate_tool_invocation(
        self,
        *,
        agent_id: str,
        session_id: str,
        run_id: str,
        tool: ToolDefinition,
        workspace: WorkspaceResolution | None,
        input_summary_sanitized: str,
        shell_category: str | None = None,
        tool_invocation_id: str | None = None,
        operation_type: str | None = None,
        execution_mode: str | None = None,
    ) -> PolicyDecision:
        return self.kernel.evaluate_tool_invocation(
            agent_id=agent_id,
            session_id=session_id,
            run_id=run_id,
            tool=tool,
            workspace=workspace,
            input_summary_sanitized=input_summary_sanitized,
            shell_category=shell_category,
            tool_invocation_id=tool_invocation_id,
            operation_type=operation_type,
            execution_mode=execution_mode,
        )
