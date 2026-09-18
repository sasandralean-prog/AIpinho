from __future__ import annotations

from aipinho.schemas.runtime.mission_staging import MissionStagingMaterializationResult
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.mission_staging_resource_service import MissionStagingResourceService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService


class MissionStagingMaterializationService:
    """Thin coordinator over canonical TaskRuntime + GovernedToolExecution."""

    def __init__(
        self,
        *,
        task_runs: TaskRunStore | None = None,
        runtime: TaskRuntimeService | None = None,
        tools: GovernedToolExecutionService | None = None,
        authority_grants: AuthorityGrantService | None = None,
        staging_resources: MissionStagingResourceService | None = None,
    ) -> None:
        self.task_runs = task_runs or TaskRunStore()
        self.authority_grants = authority_grants or AuthorityGrantService()
        self.runtime = runtime or TaskRuntimeService(store=self.task_runs)
        self.tools = tools or GovernedToolExecutionService(
            task_runs=self.task_runs,
            authority_grants=self.authority_grants,
        )
        self.staging_resources = staging_resources or MissionStagingResourceService()

    def materialize(
        self,
        *,
        parent_run_id: str,
        remote_resource_id: str,
        branch: str | None = None,
    ) -> MissionStagingMaterializationResult:
        parent = self.task_runs.get_run(parent_run_id)
        if parent is None or parent.mission_contract is None:
            return self._blocked("mission_staging_parent_run_missing", remote_resource_id)
        try:
            child_contract, derivation = self.staging_resources.derive_child_contract(
                parent.mission_contract,
                remote_resource_id=remote_resource_id,
            )
        except ValueError as exc:
            return self._blocked(str(exc), remote_resource_id)
        resource = derivation.resource
        if resource is None:
            return self._blocked(derivation.reason_code, remote_resource_id)
        remote = next(
            (item for item in child_contract.remote_resources if item.resource_id == remote_resource_id),
            None,
        )
        if remote is None or not remote.locator:
            return self._blocked("mission_staging_source_remote_missing", remote_resource_id)
        selected_branch = branch or (remote.allowed_branches[0] if len(remote.allowed_branches) == 1 else None)
        if not selected_branch or selected_branch not in set(remote.allowed_branches):
            return self._blocked("mission_staging_branch_not_authorized", remote_resource_id)
        if "git_clone" not in set(remote.permissions):
            return self._blocked("mission_staging_clone_not_permitted", remote_resource_id)
        if "git_clone" not in set(child_contract.authority.authorized_capabilities):
            return self._blocked("mission_staging_clone_not_human_authorized", remote_resource_id)

        request = TaskRunRequest(
            source_type="direct",
            parent_task_id=parent.task_id or parent.run_id,
            source_channel="mission_staging",
            session_id=parent.session_id,
            source_message_id=child_contract.source_message_id,
            mission_contract=child_contract,
            workspace=resource.locator,
            contract_type="shell",
            operation_type="git_clone",
            runtime_profile="shell",
            capabilities_required=["git_clone"],
            requested_actions=["run_command"],
            intent_map={
                "intent_type": "git_clone",
                "current_phase": "promotion_staging",
                "derived_resource_id": resource.resource_id,
                "source_remote_resource_id": remote.resource_id,
            },
            mode="governed",
            start_immediately=False,
        )
        child_run = self.runtime.reserve_run(request)

        directory_result = self.tools.execute(
            ToolExecutionRequest(
                tool_id="filesystem.create_directory",
                mode="governed",
                task_run_id=child_run.run_id,
                session_id=child_run.session_id,
                input={"workspace": resource.locator, "path": resource.locator},
            )
        )
        if directory_result.status != "executed_governed":
            return self._from_failure(
                "mission_staging_directory_materialization_failed",
                child_run_id=child_run.run_id,
                resource_id=resource.resource_id,
                workspace=resource.locator,
                remote_resource_id=remote.resource_id,
                repository_identity=remote.normalized_identity,
                branch=selected_branch,
                directory_execution_id=directory_result.execution_id,
                violations=directory_result.violations,
            )

        clone_result = self.tools.execute(
            ToolExecutionRequest(
                tool_id="shell.run_command",
                mode="governed",
                task_run_id=child_run.run_id,
                session_id=child_run.session_id,
                input={
                    "workspace": resource.locator,
                    "argv": ["git", "clone", "--branch", selected_branch, remote.locator, "."],
                    "repository_locator": remote.locator,
                    "branch": selected_branch,
                },
            )
        )
        if clone_result.status != "executed_governed" or not clone_result.safe_to_execute:
            return self._from_failure(
                "mission_staging_clone_failed",
                child_run_id=child_run.run_id,
                resource_id=resource.resource_id,
                workspace=resource.locator,
                remote_resource_id=remote.resource_id,
                repository_identity=remote.normalized_identity,
                branch=selected_branch,
                directory_execution_id=directory_result.execution_id,
                clone_execution_id=clone_result.execution_id,
                violations=clone_result.violations,
            )
        return MissionStagingMaterializationResult(
            status="materialized",
            reason_code="mission_staging_materialized",
            child_task_run_id=child_run.run_id,
            resource_id=resource.resource_id,
            workspace_path=resource.locator,
            source_remote_resource_id=remote.resource_id,
            repository_identity=remote.normalized_identity,
            branch=selected_branch,
            directory_execution_id=directory_result.execution_id,
            clone_execution_id=clone_result.execution_id,
            evidence_refs=[
                *derivation.evidence_refs,
                f"tool_execution:{directory_result.execution_id}",
                f"tool_execution:{clone_result.execution_id}",
            ],
        )

    @staticmethod
    def _blocked(reason: str, remote_resource_id: str) -> MissionStagingMaterializationResult:
        return MissionStagingMaterializationResult(
            status="blocked",
            reason_code=reason,
            source_remote_resource_id=remote_resource_id,
            violations=[reason],
        )

    @staticmethod
    def _from_failure(
        reason: str,
        *,
        child_run_id: str,
        resource_id: str,
        workspace: str | None,
        remote_resource_id: str,
        repository_identity: str | None,
        branch: str | None,
        directory_execution_id: str | None = None,
        clone_execution_id: str | None = None,
        violations: list[str] | None = None,
    ) -> MissionStagingMaterializationResult:
        return MissionStagingMaterializationResult(
            status="degraded",
            reason_code=reason,
            child_task_run_id=child_run_id,
            resource_id=resource_id,
            workspace_path=workspace,
            source_remote_resource_id=remote_resource_id,
            repository_identity=repository_identity,
            branch=branch,
            directory_execution_id=directory_execution_id,
            clone_execution_id=clone_execution_id,
            violations=list(violations or []),
        )
