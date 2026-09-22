from __future__ import annotations

from dataclasses import dataclass

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.governance.lifecycle import GovernanceLifecycleSnapshot
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.semantic_runtime.mission_completion_requirement_ingress_service import (
    MissionCompletionRequirementIngressService,
)


@dataclass(frozen=True)
class WorkspaceFixDiscoveryExecution:
    run: TaskRun
    result: TaskRunResult


class MissionCompletionRequirementIngressError(RuntimeError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class WorkspaceFixDiscoveryService:
    """Materializes the first discovery TaskRun for a repair mission.

    It is intentionally thin: lifecycle, execution, validation and truth remain
    owned by the canonical TaskRuntime. Mission continuation belongs to M8.
    """

    def __init__(
        self,
        runtime: TaskRuntimeService | None = None,
        completion_ingress: MissionCompletionRequirementIngressService | None = None,
    ) -> None:
        self.runtime = runtime or TaskRuntimeService()
        self.completion_ingress = (
            completion_ingress or MissionCompletionRequirementIngressService()
        )

    def execute(
        self,
        *,
        request: ChatRequest,
        snapshot: GovernanceLifecycleSnapshot,
        workspace: str | None,
        source_channel: str,
    ) -> WorkspaceFixDiscoveryExecution:
        resources = list(snapshot.intent.local_resources)
        remote_resources = list(snapshot.intent.remote_resources)
        primary = self._primary_workspace(resources, workspace)
        if not primary:
            raise ValueError("workspace_fix_discovery_workspace_missing")
        completion = self.completion_ingress.resolve(
            prompt=request.message,
            enabled=(
                snapshot.intent.mission_execution_mode
                == "end_to_end_governed"
            ),
        )
        if completion.status in {"unavailable", "invalid"}:
            raise MissionCompletionRequirementIngressError(
                completion.reason_code
            )

        requested_capabilities = sorted(
            set(snapshot.intent.requested_capabilities)
        )
        semantic_graph = snapshot.intent.semantic_intent_graph.model_dump(mode="json")
        run_request = TaskRunRequest(
            source_type="direct",
            source_channel=source_channel,
            session_id=request.session_id,
            operation_id=snapshot.operation_contract.operation_id,
            workspace=primary,
            contract_type="analysis_readonly",
            operation_type="project_analysis",
            runtime_profile="readonly_analysis",
            capabilities_required=["read_workspace"],
            requested_actions=["read_workspace"],
            intent_map={
                "intent_type": "workspace_fix_request",
                "operation_type": "project_analysis",
                "mission_phase": "discovery",
                "requires_task": True,
                "read_only": True,
                "readonly_contract": True,
                "future_side_effect_intent": bool(semantic_graph.get("mutation_intent")),
                "mission_execution_strategy": {
                    "mode": snapshot.intent.mission_execution_mode,
                },
                "requested_capabilities": requested_capabilities,
                "authorized_capabilities": list(snapshot.intent.authorized_capabilities),
                "authority_evidence": list(snapshot.intent.authority_evidence),
                "authority_source_refs": [
                    str(item.get("source_ref"))
                    for item in snapshot.intent.authority_evidence
                    if item.get("source_ref")
                ],
                "local_resources": [
                    resource.model_dump(mode="json") for resource in resources
                ],
                "remote_resources": [
                    resource.model_dump(mode="json") for resource in remote_resources
                ],
                "negative_constraints": [
                    constraint.model_dump(mode="json")
                    for constraint in snapshot.intent.mission_constraints
                ],
                "semantic_intent_graph": semantic_graph,
                "semantic_goal": request.message,
                "raw_prompt": request.message,
                "completion_requirements": list(
                    completion.completion_requirements
                ),
                "validation_requirements": list(
                    completion.validation_requirements
                ),
                "allow_limited_completion": bool(
                    completion.allow_limited_completion
                ),
                "mission_completion_requirement_evidence": [
                    item.model_dump(mode="json")
                    for item in completion.evidence
                ],
                "mission_completion_requirement_resolution": {
                    "status": completion.status,
                    "reason_code": completion.reason_code,
                    "provenance": dict(completion.provenance),
                },
                "mission_provenance_refs": list(
                    completion.provenance.get("evidence_refs") or []
                ),
            },
            policy_decision={
                "status": "allowed",
                "policy_status": "allowed",
                "allowed_actions": ["read_workspace", "read_files"],
                "approval_required_for": [],
                "denied_actions": [],
            },
            mode="read_only",
            start_immediately=False,
        )
        run = self.runtime.create_run(run_request)
        run, result = self.runtime.start(run.run_id)
        return WorkspaceFixDiscoveryExecution(run=run, result=result)

    def _primary_workspace(self, resources, workspace: str | None) -> str | None:
        if workspace:
            for resource in resources:
                if resource.locator and self._same_path(resource.locator, workspace):
                    return resource.locator
        for resource in resources:
            if resource.role == "target_mutable" and resource.locator:
                return resource.locator
        return workspace or next(
            (resource.locator for resource in resources if resource.locator),
            None,
        )

    def _same_path(self, left: str, right: str) -> bool:
        from pathlib import Path
        import os

        return os.path.normcase(str(Path(left).resolve(strict=False))) == os.path.normcase(
            str(Path(right).resolve(strict=False))
        )
