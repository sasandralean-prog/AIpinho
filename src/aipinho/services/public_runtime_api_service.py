from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from aipinho import __version__
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.external_gateway import GatewayRequest
from aipinho.schemas.public_runtime_api import ApiAudit, PublicContract, PublicContractRegistry, PublicOperation, PublicRuntimeRequest, PublicRuntimeResponse
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.telemetry.event import TelemetryRecordRequest
from aipinho.services.approvals.approval_service import snapshot_hash
from aipinho.services.external_gateway_service import ExternalGateway
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService
from aipinho.services.runtime.runtime_kernel_service import ModuleLoader, RuntimeKernel
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.telemetry.runtime_telemetry_service import RuntimeTelemetryService


class ApiVersionManager:
    supported_versions = ["1.0"]

    def validate(self, version: str) -> bool:
        return version in self.supported_versions

    def version(self) -> dict[str, object]:
        return {"api_version": "1.0", "app_version": __version__, "supported_versions": self.supported_versions}


class PublicContractRegistryService:
    def list(self) -> PublicContractRegistry:
        return PublicContractRegistry(
            contracts=[
                PublicContract(operation="chat", contract_type="conversation", target_module="semantic_interpreter", schema_ref="public.chat.v1"),
                PublicContract(operation="execute", contract_type="execution_plan", target_module="planner", schema_ref="public.execute.v1"),
                PublicContract(operation="analyze", contract_type="analysis", target_module="planner", schema_ref="public.analyze.v1"),
                PublicContract(operation="doctor", contract_type="runtime_doctor_report", target_module="runtime_doctor", schema_ref="public.doctor.v1"),
                PublicContract(operation="validate", contract_type="validation_result", target_module="validator", schema_ref="public.validate.v1"),
                PublicContract(operation="artifacts", contract_type="artifact_report", target_module="reporter", schema_ref="public.artifacts.v1"),
            ]
        )

    def for_operation(self, operation: PublicOperation) -> PublicContract:
        for contract in self.list().contracts:
            if contract.operation == operation:
                return contract
        raise ValueError("public_contract_missing")


class ApiCompatibilityLayer:
    def merge_contract(self, public_contract: PublicContract, request_contract: dict[str, object]) -> dict[str, object]:
        merged = dict(request_contract)
        merged.setdefault("contract_type", public_contract.contract_type)
        merged.setdefault("schema_ref", public_contract.schema_ref)
        merged.setdefault("public_contract_version", public_contract.version)
        return merged


class PublicRuntimeExecutionBridge:
    """Connects public contracts to canonical runtime execution paths."""

    def __init__(
        self,
        readonly_artifact_runtime: ReadonlyAnalysisArtifactRuntimeService | None = None,
        task_runtime: TaskRuntimeService | None = None,
    ) -> None:
        self.readonly_artifact_runtime = readonly_artifact_runtime or ReadonlyAnalysisArtifactRuntimeService()
        self.task_runtime = task_runtime or TaskRuntimeService()

    def execute(
        self,
        request: PublicRuntimeRequest,
        *,
        contract: dict[str, object],
        gateway_status: str,
    ) -> dict[str, Any]:
        if gateway_status != "accepted" or not self._requires_runtime_execution(contract):
            return {}

        logical_paths = self._logical_artifact_paths(contract, request.payload)
        workspace_context = self._workspace_context(contract, request.payload)
        workspace = self._workspace_path(workspace_context, contract, request.payload)
        if self._is_readonly_artifact_contract(contract, logical_paths):
            if not workspace:
                return self._blocked(
                    "workspace_required_for_runtime_execution",
                    contract=contract,
                    missing=["workspace"],
                )
            if not logical_paths:
                return self._blocked(
                    "artifact_logical_paths_required",
                    contract=contract,
                    missing=["artifact_logical_paths"],
                )
            execution_request = SimpleNamespace(
                message=self._runtime_message(request, logical_paths),
                session_id=str(request.metadata.get("session_id") or request.payload.get("session_id") or "") or None,
                workspace_context=workspace_context,
            )
            execution = self.readonly_artifact_runtime.execute(
                request=execution_request,
                workspace=workspace,
                label=str(contract.get("success_label") or "PUBLIC_RUNTIME_ANALYSIS_READY"),
            )
            response = execution.response
            run = self.readonly_artifact_runtime.runtime.store.get_run(execution.run_id) if execution.run_id else None
            return {
                "status": response.status,
                "reason_code": response.grounding_missing_reason,
                "task_id": run.task_id if run else response.task_id,
                "task_run_id": execution.run_id or response.result_ref_id or response.task_id,
                "operation_id": run.operation_id if run else response.operation_id,
                "operation_type": response.operation_type,
                "runtime_profile": run.runtime_profile if run else response.contract_preview.get("runtime_profile"),
                "artifacts": [item.model_dump(mode="json") for item in response.artifact_links],
                "artifact_ids": [item.artifact_id for item in response.artifact_links],
                "validation": response.contract_preview.get("validation_result") or {},
                "completion": response.contract_preview.get("completion") or {},
                "speaker_truth": response.governance_lifecycle.get("speaker_truth") or {
                    "can_claim_success": response.grounded,
                    "source": "public_runtime_execution_bridge",
                },
                "workspace_context": workspace_context,
                "message": response.message,
                "source": "public_runtime_execution_bridge",
            }

        if self._is_governed_shell_contract(contract):
            if not workspace:
                return self._blocked(
                    "workspace_required_for_runtime_execution",
                    contract=contract,
                    missing=["workspace"],
                )
            command = self._shell_command(contract, request.payload)
            if not command:
                return self._blocked(
                    "shell_command_plan_required",
                    contract=contract,
                    missing=["shell_command_plan"],
                )
            requested_actions = self._requested_actions(contract, default=["run_command"])
            if "run_command" not in requested_actions:
                requested_actions.append("run_command")
            session_id = str(request.metadata.get("session_id") or request.payload.get("session_id") or "") or None
            shell_category = self._shell_category(command)
            shell_plan = {
                "plan_ref": self._plan_ref({"command": command, "workspace": workspace, "contract": contract}),
                "command": command,
                "cwd": workspace,
                "timeout_seconds": int(contract.get("timeout_seconds") or request.payload.get("timeout_seconds") or 120),
                "expected_exit_code": int(contract.get("expected_exit_code") or request.payload.get("expected_exit_code") or 0),
                "shell_category": shell_category,
            }
            policy_snapshot = ApprovalPolicySnapshot(
                policy_status="approval_required",
                allowed_actions=[],
                denied_actions=[],
                approval_required_for=["run_command"],
                granted_capabilities=["shell"],
                workspace_status="approval_required",
                risk_level="high" if shell_category == "unknown_shell" else "medium",
                trace_hash=self._plan_ref(shell_plan),
                config_versions={
                    "source": "public_runtime_execution_bridge",
                    "runtime_profile": "shell",
                    "public_contract_version": str(contract.get("public_contract_version") or "1.0"),
                },
            )
            approval = self._create_shell_approval(
                contract=contract,
                session_id=session_id,
                workspace=workspace,
                command=command,
                requested_actions=requested_actions,
                shell_plan=shell_plan,
                policy_snapshot=policy_snapshot,
            )
            run = self.task_runtime.create_run(
                TaskRunRequest(
                    source_type="direct",
                    source_channel="public_runtime_api",
                    session_id=session_id,
                    workspace=workspace,
                    contract_type="shell_execution",
                    operation_type="test_run" if shell_category == "test_shell" else ("build_run" if shell_category == "build_shell" else "shell_execute"),
                    runtime_profile="shell",
                    capabilities_required=["shell"],
                    requested_actions=requested_actions,
                    intent_map={
                        "intent_type": "governed_shell_request",
                        "public_operation": request.operation,
                        "shell_plan": shell_plan,
                        "workspace_context": workspace_context,
                        "objective": str(request.payload.get("objective") or contract.get("objective") or ""),
                    },
                    policy_decision={
                        **policy_snapshot.model_dump(mode="json"),
                        "status": "approval_required",
                    },
                    approval_id=approval.approval_id,
                    mode="shell",
                    start_immediately=False,
                    include_trace=True,
                )
            )
            waiting = run.status in {"waiting_input", "created", "queued"} and bool(run.approval_id)
            response_status = "pending_approval" if waiting else run.status
            reason_code = "approval_required_before_shell_execution" if waiting else (
                ",".join(run.blocked_reasons) if run.blocked_reasons else None
            )
            return {
                "status": response_status,
                "reason_code": reason_code,
                "task_id": run.task_id,
                "task_run_id": run.run_id,
                "operation_id": run.operation_id,
                "operation_type": run.operation_type,
                "runtime_profile": run.runtime_profile,
                "approval_id": run.approval_id,
                "artifacts": [],
                "artifact_ids": [],
                "validation": {
                    "status": "waiting_approval" if waiting else "blocked",
                    "reason_code": reason_code,
                    "safe_to_report_success": False,
                    "missing_outputs": [] if waiting else list(run.blocked_reasons),
                },
                "completion": {
                    "status": "waiting_approval" if waiting else "blocked",
                    "safe_to_report_success": False,
                    "missing_outcomes": [] if waiting else list(run.blocked_reasons),
                },
                "speaker_truth": {
                    "can_claim_success": False,
                    "reason_code": reason_code,
                    "source": "public_runtime_execution_bridge",
                },
                "workspace_context": workspace_context,
                "message": "ApprovalRequest criado para execucao governada de shell; nenhuma execucao foi iniciada.",
                "source": "public_runtime_execution_bridge",
            }

        return self._blocked(
            "public_runtime_execution_route_missing",
            contract=contract,
            missing=["runtime_execution_route"],
        )

    def _requires_runtime_execution(self, contract: dict[str, object]) -> bool:
        expected_outputs = contract.get("expected_outputs")
        return bool(
            contract.get("requires_task")
            or contract.get("execution_required")
            or contract.get("artifact_generation")
            or contract.get("validation_required")
            or (isinstance(expected_outputs, list) and expected_outputs)
        )

    def _is_readonly_artifact_contract(self, contract: dict[str, object], logical_paths: list[str]) -> bool:
        workspace_mutation = bool(contract.get("workspace_mutation"))
        runtime_profile = str(contract.get("runtime_profile") or "")
        contract_type = str(contract.get("contract_type") or "")
        operation_type = str(contract.get("operation_type") or "")
        artifact_generation = bool(contract.get("artifact_generation") or logical_paths)
        readonly_analysis = (
            runtime_profile in {"readonly_analysis", "workspace_analysis_readonly"}
            or contract_type in {"analysis", "analysis_readonly", "readonly_analysis"}
            or operation_type in {"workspace_analysis_readonly", "readonly_analysis"}
        )
        return readonly_analysis and artifact_generation and not workspace_mutation

    def _is_governed_shell_contract(self, contract: dict[str, object]) -> bool:
        actions = set(self._requested_actions(contract))
        operation_type = str(contract.get("operation_type") or "")
        runtime_profile = str(contract.get("runtime_profile") or "")
        contract_type = str(contract.get("contract_type") or "")
        return bool(
            "run_command" in actions
            or operation_type in {"run_command", "shell_execute", "shell_test", "test_run", "build_run"}
            or runtime_profile in {"shell", "shell_build_test"}
            or contract_type in {"shell_execution", "governed_shell_request"}
        )

    def _requested_actions(self, contract: dict[str, object], default: list[str] | None = None) -> list[str]:
        value = contract.get("requested_actions")
        actions = [str(item) for item in value] if isinstance(value, list) else list(default or [])
        return list(dict.fromkeys(actions))

    def _shell_command(self, contract: dict[str, object], payload: dict[str, object]) -> str | None:
        for source in (payload, contract):
            value = source.get("command")
            if value:
                return str(value)
            plan = source.get("shell_plan")
            if isinstance(plan, dict) and plan.get("command"):
                return str(plan.get("command"))
        return None

    def _shell_category(self, command: str) -> str:
        lowered = command.lower()
        if any(token in lowered for token in (" test", "gradlew.bat test", "gradlew test", "pytest")):
            return "test_shell"
        if any(token in lowered for token in (" assemble", " build", " check", "gradle", "gradlew")):
            return "build_shell"
        return "unknown_shell"

    def _plan_ref(self, value: dict[str, object]) -> str:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _create_shell_approval(
        self,
        *,
        contract: dict[str, object],
        session_id: str | None,
        workspace: str,
        command: str,
        requested_actions: list[str],
        shell_plan: dict[str, object],
        policy_snapshot: ApprovalPolicySnapshot,
    ) -> ApprovalRequest:
        now = datetime.now(timezone.utc)
        plan_ref = str(shell_plan["plan_ref"])
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=f"preview_{plan_ref[:32]}",
            draft_id=f"draft_{plan_ref[:32]}",
            session_id=session_id,
            workspace_path=workspace,
            operation_type="run_command",
            contract_type="shell_execution",
            runtime_profile="shell",
            target_paths=[workspace],
            commands=[command],
            expected_outcomes=[str(item) for item in contract.get("expected_outputs", [])] if isinstance(contract.get("expected_outputs"), list) else ["command_result", "validation_result"],
            executable_plan_ref=f"shell_plan:{plan_ref}",
            preview_hash=plan_ref,
            policy_snapshot_hash=snapshot_hash(policy_snapshot),
            preview={
                "available": True,
                "summary": "Preview de shell governado criado; nenhuma execucao foi iniciada.",
                "shell_plan": shell_plan,
            },
            policy_refs=["public_runtime_api:shell_execution"],
            allowed_by_policy=True,
            forbidden_operations=[],
            status="pending",
            actions_requested=requested_actions,
            approval_scope="future_execution",
            reason="Public Runtime API requested governed shell execution.",
            risk_level=policy_snapshot.risk_level,
            policy_snapshot=policy_snapshot,
            expires_at=(now + timedelta(minutes=self.task_runtime.approvals.policy.ttl_minutes())).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=Actor(type="system", id="public_runtime_api"),
            trace=[
                {
                    "stage": "public_runtime_shell_approval",
                    "decision": "pending",
                    "reason": "approval_required_before_shell_execution",
                }
            ],
            execution_status="not_executed",
        )
        self.task_runtime.approvals.store.save(approval)
        self.task_runtime.approvals.append_event(
            approval.approval_id,
            "approval_created",
            "ApprovalRequest criado para shell governado via API publica; nada foi executado.",
            {"workspace": workspace, "command": command, "plan_ref": plan_ref},
        )
        return approval

    def _logical_artifact_paths(self, contract: dict[str, object], payload: dict[str, object]) -> list[str]:
        candidates: list[str] = []
        for source in (contract, payload):
            value = source.get("artifact_logical_paths")
            if isinstance(value, list):
                candidates.extend(str(item) for item in value if item)
            expected = source.get("expected_outputs")
            if isinstance(expected, list):
                for item in expected:
                    text = str(item)
                    if text.startswith("artifact:"):
                        candidates.append(text.removeprefix("artifact:"))
        return list(dict.fromkeys(candidates))

    def _workspace_context(self, contract: dict[str, object], payload: dict[str, object]) -> dict[str, Any]:
        for source in (payload, contract):
            value = source.get("workspace_context")
            if isinstance(value, dict):
                return dict(value)
        return {}

    def _workspace_path(self, workspace_context: dict[str, Any], contract: dict[str, object], payload: dict[str, object]) -> str | None:
        for value in (
            workspace_context.get("project_root"),
            workspace_context.get("workspace"),
            payload.get("workspace"),
            contract.get("workspace"),
        ):
            if value:
                return str(value)
        return None

    def _runtime_message(self, request: PublicRuntimeRequest, logical_paths: list[str]) -> str:
        objective = str(request.payload.get("objective") or request.contract.get("objective") or "Execute governed read-only runtime operation.")
        artifacts = ", ".join(logical_paths)
        constraints = "workspace read-only; workspace_mutation false; gere artifacts " + artifacts
        return f"{objective}\n{constraints}"

    def _blocked(self, reason_code: str, *, contract: dict[str, object], missing: list[str]) -> dict[str, Any]:
        return {
            "status": "blocked",
            "reason_code": reason_code,
            "missing_outputs": list(missing),
            "task_id": None,
            "task_run_id": None,
            "artifact_ids": [],
            "validation": {
                "status": "blocked",
                "reason_code": reason_code,
                "safe_to_report_success": False,
                "missing_outputs": list(missing),
            },
            "completion": {
                "status": "blocked",
                "safe_to_report_success": False,
                "missing_outcomes": list(missing),
            },
            "speaker_truth": {
                "can_claim_success": False,
                "reason_code": reason_code,
            },
            "contract": contract,
            "source": "public_runtime_execution_bridge",
        }


class PublicRuntimeAPI:
    _audits: list[ApiAudit] = []

    def __init__(
        self,
        gateway: ExternalGateway | None = None,
        contracts: PublicContractRegistryService | None = None,
        versions: ApiVersionManager | None = None,
        compatibility: ApiCompatibilityLayer | None = None,
        telemetry: RuntimeTelemetryService | None = None,
        execution_bridge: PublicRuntimeExecutionBridge | None = None,
    ) -> None:
        self.gateway = gateway or ExternalGateway()
        self.contracts = contracts or PublicContractRegistryService()
        self.versions = versions or ApiVersionManager()
        self.compatibility = compatibility or ApiCompatibilityLayer()
        self.telemetry = telemetry or RuntimeTelemetryService()
        self.execution_bridge = execution_bridge or PublicRuntimeExecutionBridge()

    def handle(self, request: PublicRuntimeRequest) -> PublicRuntimeResponse:
        public_contract = self.contracts.for_operation(request.operation)
        if not self.versions.validate(request.api_version):
            merged_contract: dict[str, object] = {}
            gateway_response = self.gateway.handle(
                GatewayRequest(
                    client_id=request.client_id,
                    client_type=request.client_type,
                    version=request.api_version,
                    target_module=public_contract.target_module,
                    contract={},
                    payload=request.payload,
                )
            )
        else:
            merged_contract = self.compatibility.merge_contract(public_contract, request.contract)
            gateway_response = self.gateway.handle(
                GatewayRequest(
                    client_id=request.client_id,
                    client_type=request.client_type,
                    version=request.api_version,
                    target_module=public_contract.target_module,
                    contract=merged_contract,
                    payload=request.payload,
                    metadata=request.metadata,
                )
            )
        runtime_result = self.execution_bridge.execute(
            request,
            contract=merged_contract,
            gateway_status=gateway_response.status,
        )
        response_status = str(runtime_result.get("status") or gateway_response.status)
        response = PublicRuntimeResponse(
            operation=request.operation,
            api_version=request.api_version,
            status=response_status,
            gateway_response=gateway_response,
            runtime_result=runtime_result,
            task_id=runtime_result.get("task_id"),
            task_run_id=runtime_result.get("task_run_id"),
            operation_id=runtime_result.get("operation_id"),
            artifact_ids=list(runtime_result.get("artifact_ids") or []),
            validation_state=dict(runtime_result.get("validation") or {}),
            completion_state=dict(runtime_result.get("completion") or {}),
            speaker_truth_state=dict(runtime_result.get("speaker_truth") or {}),
            public_contract_version=public_contract.version,
        )
        audit = ApiAudit(
            audit_id=response.audit_id,
            operation=request.operation,
            client_id=request.client_id,
            client_type=request.client_type,
            status=response.status,
            gateway_response_id=gateway_response.response_id,
        )
        self._audits.append(audit)
        self.telemetry.record(
            TelemetryRecordRequest(
                category="governance",
                origin="public_runtime_api",
                module="public_runtime_api_service",
                event_type=f"public_api_{request.operation}",
                correlation_id=response.public_response_id,
                task_id=response.task_id,
                task_run_id=response.task_run_id,
                session_id=gateway_response.gateway_session_id,
                metadata={
                    "operation": request.operation,
                    "status": response.status,
                    "gateway_status": gateway_response.status,
                    "runtime_result_status": runtime_result.get("status"),
                },
            )
        )
        return response

    def runtime(self) -> dict[str, object]:
        kernel = RuntimeKernel()
        health = kernel.boot()
        return {"status": health.status, "kernel_state": health.state, "modules": len(kernel.registry().modules), "gateway_required": True, "kernel_required": True}

    def modules(self) -> dict[str, object]:
        return {"modules": [module.model_dump(mode="json") for module in ModuleLoader().default_modules()], "gateway_required": True, "kernel_required": True}

    def contracts_view(self) -> dict[str, object]:
        return self.contracts.list().model_dump(mode="json")

    def version(self) -> dict[str, object]:
        return self.versions.version()

    def history(self) -> dict[str, object]:
        return {"count": len(self._audits), "audits": [audit.model_dump(mode="json") for audit in self._audits], "mutates_runtime": False}
