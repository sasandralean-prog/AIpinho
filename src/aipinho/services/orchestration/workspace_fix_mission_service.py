from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.runtime.engineering_autopilot_service import EngineeringAutopilotService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


@dataclass(frozen=True)
class WorkspaceFixDiscoveryStart:
    mission_id: str
    run: TaskRun
    mission_status: str


class WorkspaceFixMissionService:
    """Starts the read-only discovery phase of a governed workspace-fix mission.

    The original mission may request future mutation/build effects. Those effects
    remain mission metadata only. This first TaskRun is intentionally read-only
    and cannot create a write approval or execute a side effect.
    """

    def __init__(
        self,
        *,
        runtime: TaskRuntimeService | None = None,
        missions: EngineeringAutopilotService | None = None,
    ) -> None:
        self.runtime = runtime or TaskRuntimeService()
        self.missions = missions or self.runtime.engineering_autopilot

    def start_discovery(
        self,
        *,
        request: ChatRequest,
        workspace: str,
        source_channel: str,
        operation_id: str | None,
        mission_semantic_intent_graph: dict[str, Any] | None = None,
        mission_evidence: list[str] | None = None,
    ) -> WorkspaceFixDiscoveryStart:
        mission = self.missions.create_mission(
            objective=request.message,
            session_id=request.session_id,
            workspace=workspace,
        )
        original_graph = dict(mission_semantic_intent_graph or {})
        deferred_effects = [
            str(item)
            for item in original_graph.get("requested_effects", []) or []
            if str(item)
            not in {"knowledge_only", "planning_only", "proposal_only"}
        ]
        phase_graph = {
            "observational_intent": True,
            "planning_intent": True,
            "mutation_intent": False,
            "execution_intent": False,
            "approval_intent": False,
            "knowledge_output": True,
            "artifact_output": False,
            "readonly_contract": True,
            "state_effect": "knowledge_only",
            "workspace_effect": "immutable",
            "filesystem_effect": "knowledge_only",
            "runtime_effect": "none",
            "prohibited_effects": [
                "workspace_mutation",
                "filesystem_write",
                "runtime_execution",
                "approval_command",
            ],
            "requested_effects": ["knowledge_only", "planning_only"],
            "evidence": [
                "workspace_fix_discovery_phase",
                "future_side_effects_deferred",
            ],
        }
        run = self.runtime.create_run(
            TaskRunRequest(
                source_type="direct",
                source_channel=source_channel,
                session_id=request.session_id,
                operation_id=operation_id,
                workspace=workspace,
                contract_type="analysis_readonly",
                operation_type="project_analysis",
                runtime_profile="readonly_analysis",
                capabilities_required=["read_workspace"],
                intent_map={
                    "intent_type": "workspace_fix_discovery",
                    "mission_intent_type": "workspace_fix_request",
                    "operation_type": "project_analysis",
                    "requires_task": True,
                    "read_only": True,
                    "workspace_mutation": False,
                    "semantic_goal": (
                        "Discover and diagnose the target workspace before any "
                        "mutation, approval, build, or patch execution."
                    ),
                    "raw_prompt": request.message,
                    "mission_id": mission.mission_id,
                    "mission_semantic_intent_graph": original_graph,
                    "mission_evidence": list(mission_evidence or []),
                    "deferred_effects": deferred_effects,
                    "semantic_intent_graph": phase_graph,
                    "workspace_references": [workspace],
                    "target_paths": [workspace],
                },
                policy_decision={
                    "status": "allowed",
                    "policy_status": "allowed",
                    "allowed_actions": ["read_files"],
                    "denied_actions": [],
                    "approval_required_for": [],
                    "granted_capabilities": ["read_workspace"],
                    "denied_capabilities": [],
                },
                requested_actions=["read_files"],
                mode="read_only",
                start_immediately=True,
                include_trace=True,
            )
        )
        cycle = self.runtime.continuous_runtime.evaluate(
            run,
            objective=mission.objective,
        )
        attached = self.missions.attach_run(mission, run, cycle)
        return WorkspaceFixDiscoveryStart(
            mission_id=attached.mission_id,
            run=run,
            mission_status=attached.lifecycle.status,
        )
