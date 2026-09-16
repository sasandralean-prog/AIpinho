from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.orchestration.intent_workspace_scope_service import (
    IntentWorkspaceScopeService,
)
from aipinho.services.orchestration.mission_execution_strategy_service import (
    MissionExecutionStrategyService,
)
from aipinho.services.runtime.engineering_autopilot_service import EngineeringAutopilotService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


@dataclass(frozen=True)
class WorkspaceFixMissionStart:
    mission_id: str
    run: TaskRun
    mission_status: str
    execution_strategy: dict[str, Any]
    workspace_scope_contract: dict[str, Any]


WorkspaceFixDiscoveryStart = WorkspaceFixMissionStart


class WorkspaceFixMissionService:
    """Bootstraps a governed workspace-repair mission from prompt intent.

    A mission may be end-to-end or staged. Both modes may use multiple internal
    TaskRuns; end-to-end means no new prompt is required between internal phases,
    while staged mode deliberately stops after the requested phase.
    """

    def __init__(
        self,
        *,
        runtime: TaskRuntimeService | None = None,
        missions: EngineeringAutopilotService | None = None,
        strategies: MissionExecutionStrategyService | None = None,
        workspace_scopes: IntentWorkspaceScopeService | None = None,
    ) -> None:
        self.runtime = runtime or TaskRuntimeService()
        self.missions = missions or self.runtime.engineering_autopilot
        self.strategies = strategies or MissionExecutionStrategyService()
        self.workspace_scopes = workspace_scopes or IntentWorkspaceScopeService()

    def start_mission(
        self,
        *,
        request: ChatRequest,
        workspace: str | None,
        source_channel: str,
        operation_id: str | None,
        mission_semantic_intent_graph: dict[str, Any] | None = None,
        mission_evidence: list[str] | None = None,
    ) -> WorkspaceFixMissionStart:
        original_graph = dict(mission_semantic_intent_graph or {})
        strategy = self.strategies.resolve(
            prompt=request.message,
            semantic_graph=original_graph,
        )
        scope_contract = self.workspace_scopes.resolve(
            prompt=request.message,
            workspace_hint=workspace,
            semantic_graph=original_graph,
        )
        primary_workspace = str(
            scope_contract.get("primary_workspace") or workspace or ""
        ).strip()
        if not primary_workspace:
            raise ValueError("mission_primary_workspace_required")

        mission = self.missions.create_mission(
            objective=request.message,
            session_id=request.session_id,
            workspace=primary_workspace,
        )
        deferred_effects = [
            str(item)
            for item in original_graph.get("requested_effects", []) or []
            if str(item)
            not in {"knowledge_only", "planning_only", "proposal_only"}
        ]
        phase_graph = {
            "observational_intent": True,
            "planning_intent": False,
            "mutation_intent": False,
            "execution_intent": False,
            "approval_intent": False,
            "knowledge_output": False,
            "artifact_output": False,
            "readonly_contract": True,
            "state_effect": "knowledge_only",
            "workspace_effect": "knowledge_only",
            "filesystem_effect": "prohibited",
            "runtime_effect": "none",
            "prohibited_effects": [
                "workspace_mutation",
                "filesystem_write",
                "runtime_execution",
                "approval_command",
            ],
            "requested_effects": ["knowledge_only"],
            "evidence": [
                "workspace_fix_discovery_phase",
                (
                    "mission_auto_continuation_authorized"
                    if strategy.auto_continue
                    else "mission_phase_boundary_requires_new_prompt"
                ),
            ],
        }
        continuation_policy = {
            "mode": strategy.mode,
            "auto_continue": strategy.auto_continue,
            "requires_new_prompt_between_phases": (
                strategy.requires_new_prompt_between_phases
            ),
            "stop_at_approval_gate": strategy.stop_at_approval_gate,
            "next_phase": "patch_planning",
        }
        intent_map = {
            "intent_type": "workspace_fix_discovery",
            "mission_intent_type": "workspace_fix_request",
            "operation_type": "project_analysis",
            "requires_task": True,
            "read_only": True,
            "workspace_mutation": False,
            "semantic_goal": (
                "Discover and diagnose the target workspace before any mutation, "
                "approval, build, or patch execution."
            ),
            "raw_prompt": request.message,
            "mission_id": mission.mission_id,
            "mission_execution_strategy": strategy.as_dict(),
            "mission_continuation_policy": continuation_policy,
            "mission_semantic_intent_graph": original_graph,
            "mission_evidence": list(mission_evidence or []),
            "deferred_effects": deferred_effects,
            "semantic_intent_graph": phase_graph,
            "workspace_scope_contract": scope_contract,
            "workspace_references": [
                item["path"]
                for item in scope_contract.get("scopes", [])
                if isinstance(item, dict) and item.get("path")
            ],
            "target_paths": [primary_workspace],
            "library_roots": list(scope_contract.get("library_roots") or []),
            "external_roots": list(scope_contract.get("external_roots") or []),
            "readonly_flags": dict(scope_contract.get("readonly_flags") or {}),
            "workspace_ids": list(scope_contract.get("workspace_ids") or []),
        }
        run = self.runtime.create_run(
            TaskRunRequest(
                source_type="direct",
                source_channel=source_channel,
                session_id=request.session_id,
                operation_id=operation_id,
                workspace=primary_workspace,
                contract_type="analysis_readonly",
                operation_type="project_analysis",
                runtime_profile="readonly_analysis",
                capabilities_required=["read_workspace"],
                intent_map=intent_map,
                policy_decision={
                    "status": "allowed",
                    "policy_status": "allowed",
                    "allowed_actions": ["read_files"],
                    "denied_actions": [],
                    "approval_required_for": [],
                    "granted_capabilities": ["read_workspace"],
                    "denied_capabilities": [],
                    "workspace_scope_contract": scope_contract,
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
        return WorkspaceFixMissionStart(
            mission_id=attached.mission_id,
            run=run,
            mission_status=attached.lifecycle.status,
            execution_strategy=strategy.as_dict(),
            workspace_scope_contract=scope_contract,
        )

    def start_discovery(self, **kwargs: Any) -> WorkspaceFixMissionStart:
        """Backward-compatible adapter for callers created before mission strategy."""
        return self.start_mission(**kwargs)
