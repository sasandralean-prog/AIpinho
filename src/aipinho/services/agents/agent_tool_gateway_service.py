from __future__ import annotations

import fnmatch
import base64
import hashlib
import json
import os
import shlex
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Protocol

from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunUpdateRequest
from aipinho.schemas.agents.tool_gateway import (
    ArtifactUploadRequest,
    PolicyDecision,
    ToolArtifactRecord,
    ToolDefinition,
    ToolInvocation,
    ToolInvocationCreateRequest,
    ToolInvocationResult,
    ValidationResult,
    ValidationStep,
    WorkspaceResolution,
)
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.services.agents.agent_event_bus import MultiAgentEventBus
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.agents.agent_tool_policy_service import AgentToolPolicyDecisionService
from aipinho.services.agents.agent_tool_registry_service import AgentToolRegistryService
from aipinho.services.agents.agent_tool_workspace_resolver import AgentToolWorkspaceResolver
from aipinho.services.events.event_core import contains_secret, redact_payload


class ShellRunner(Protocol):
    def run(self, argv: list[str], cwd: str | None, timeout: int) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessShellRunner:
    def run(self, argv: list[str], cwd: str | None, timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run(argv, cwd=cwd, timeout=timeout, text=True, capture_output=True, shell=False)


class AgentToolGatewayService:
    def __init__(
        self,
        *,
        kernel: AgentSessionKernelService | None = None,
        registry: AgentToolRegistryService | None = None,
        resolver: AgentToolWorkspaceResolver | None = None,
        policy: AgentToolPolicyDecisionService | None = None,
        store: AgentToolInvocationStore | None = None,
        event_bus: MultiAgentEventBus | None = None,
        shell_runner: ShellRunner | None = None,
    ) -> None:
        shared_store = AgentSessionStore()
        self.kernel = kernel or AgentSessionKernelService(store=shared_store)
        self.event_bus = event_bus or MultiAgentEventBus(self.kernel.store)
        self.registry = registry or AgentToolRegistryService()
        self.resolver = resolver or AgentToolWorkspaceResolver()
        self.policy = policy or AgentToolPolicyDecisionService()
        self.store = store or AgentToolInvocationStore()
        self.shell_runner = shell_runner or SubprocessShellRunner()

    def list_tools(self, *, enabled: bool | None = None) -> list[ToolDefinition]:
        return self.registry.list_tools(enabled=enabled)

    def get_tool(self, tool_name: str) -> ToolDefinition | None:
        return self.registry.get(tool_name)

    def invoke(self, agent_id: str, run_id: str, tool_name: str, request: ToolInvocationCreateRequest) -> ToolInvocationResult:
        run = self.kernel.get_run(run_id)
        if run is None:
            raise FileNotFoundError(run_id)
        if run.agent_id != agent_id:
            raise PermissionError("agent_run_mismatch")
        tool = self.registry.require(tool_name)
        input_sanitized = redact_payload(request.input)
        summary = self._summary(input_sanitized)
        workspace = self._resolve_workspace(tool, request)
        invocation = ToolInvocation(
            run_id=run.run_id,
            parent_run_id=run.parent_run_id,
            delegation_id=run.delegation_id,
            session_id=run.session_id,
            agent_id=run.agent_id,
            tool_name=tool.tool_name,
            capability=tool.capability,
            operation_type=request.operation_type or tool.tool_name,
            workspace_id=workspace.workspace_id if workspace else request.workspace_id,
            project_profile_id=request.project_profile_id or run.project_profile_id,
            workspace_profile_id=request.workspace_profile_id or run.workspace_profile_id,
            validation_profile_id=request.validation_profile_id or run.validation_profile_id,
            command_profile_id=request.command_profile_id,
            skill_id=request.skill_id,
            skill_execution_id=request.skill_execution_id,
            sandbox_task_id=request.sandbox_task_id,
            sandbox_workspace_id=request.sandbox_workspace_id,
            relative_path=request.relative_path,
            cwd_inside_sandbox=request.cwd_inside_sandbox,
            operation_scope=request.operation_scope,
            requesting_agent_id=request.requesting_agent_id or run.agent_id,
            workspace_role=workspace.workspace_role if workspace else None,
            input_summary_sanitized=summary,
            approval_id=request.approval_id,
            auto_approval_id=request.auto_approval_id,
            metadata_sanitized=redact_payload({
                **request.metadata_sanitized,
                "parent_run_id": run.parent_run_id,
                "delegation_id": run.delegation_id,
                "project_profile_id": request.project_profile_id or run.project_profile_id,
                "workspace_profile_id": request.workspace_profile_id or run.workspace_profile_id,
                "validation_profile_id": request.validation_profile_id or run.validation_profile_id,
                "command_profile_id": request.command_profile_id,
                "skill_id": request.skill_id,
                "skill_execution_id": request.skill_execution_id,
                "sandbox_task_id": request.sandbox_task_id,
                "sandbox_workspace_id": request.sandbox_workspace_id,
                "relative_path": request.relative_path,
                "cwd_inside_sandbox": request.cwd_inside_sandbox,
                "operation_scope": request.operation_scope,
                "requesting_agent_id": request.requesting_agent_id or run.agent_id,
            }),
        )
        self.store.save_invocation(invocation)
        event_ids: list[str] = []
        event_ids.append(self._event(run, "tool_invocation_created", "Invocacao de ferramenta criada.", invocation, {"tool_name": tool.tool_name}))
        event_ids.append(self._event(run, "tool_policy_check_started", "Verificando politica da ferramenta.", invocation, {"capability": tool.capability}))
        event_ids.append(self._event(run, "policy_check_started", "Policy Kernel avaliando a acao.", invocation, {"capability": tool.capability}))
        policy = self.policy.evaluate_tool_invocation(
            agent_id=run.agent_id,
            session_id=run.session_id,
            run_id=run.run_id,
            tool=tool,
            workspace=workspace,
            input_summary_sanitized=summary,
            shell_category=str(request.input.get("shell_category", "unknown_shell")) if tool.can_run_shell else None,
            tool_invocation_id=invocation.tool_invocation_id,
            operation_type=invocation.operation_type,
            execution_mode=str(request.metadata_sanitized.get("execution_mode")) if request.metadata_sanitized.get("execution_mode") else None,
        )
        invocation = invocation.model_copy(update={
            "policy_decision_id": policy.policy_decision_id,
            "auto_approval_id": policy.auto_approval_id or invocation.auto_approval_id,
            "status": "policy_checking",
        })
        self.store.save_invocation(invocation)
        event_ids.append(self._event(run, "tool_policy_check_completed", "Politica da ferramenta avaliada.", invocation, {"decision": policy.decision, "reason_code": policy.reason_code}))
        event_ids.append(self._event(run, "policy_check_completed", "Policy Kernel concluiu a avaliacao.", invocation, {"decision": policy.decision, "reason_code": policy.reason_code, "execution_mode": policy.execution_mode}))
        event_ids.append(self._event(run, f"policy_decision_{policy.decision}", policy.human_reason, invocation, {"policy_decision_id": policy.policy_decision_id, "reason_code": policy.reason_code, "safe_alternative": policy.safe_alternative}))
        if policy.decision == "deny":
            invocation = invocation.model_copy(update={
                "status": "blocked",
                "completed_at": utc_now_iso(),
                "block_reason_code": policy.reason_code,
                "output_summary_sanitized": policy.human_reason,
            })
            self.store.save_invocation(invocation)
            event_ids.append(self._event(run, "tool_blocked", policy.human_reason, invocation, {"reason_code": policy.reason_code, "safe_alternative": policy.safe_alternative}, severity="warning"))
            event_ids.append(self._event(run, "operation_blocked", policy.human_reason, invocation, {"reason_code": policy.reason_code, "safe_alternative": policy.safe_alternative}, severity="warning"))
            if policy.safe_alternative:
                event_ids.append(self._event(run, "safe_alternative_available", policy.safe_alternative, invocation, {"reason_code": policy.reason_code}, severity="info"))
            return ToolInvocationResult(status="blocked", tool_invocation=invocation, policy_decision=policy, workspace_resolution=workspace, events_emitted=event_ids)
        if policy.decision == "require_approval" and not (request.approval_id or request.auto_approval_id):
            invocation = invocation.model_copy(update={
                "status": "approval_required",
                "completed_at": utc_now_iso(),
                "block_reason_code": policy.reason_code,
                "output_summary_sanitized": policy.human_reason,
            })
            self.store.save_invocation(invocation)
            event_ids.append(self._event(run, "tool_approval_required", policy.human_reason, invocation, {"reason_code": policy.reason_code, "safe_actions": policy.safe_actions}, severity="warning"))
            return ToolInvocationResult(status="approval_required", tool_invocation=invocation, policy_decision=policy, workspace_resolution=workspace, events_emitted=event_ids)
        if policy.decision == "auto_approve":
            invocation = invocation.model_copy(update={"status": "auto_approved"})
            self.store.save_invocation(invocation)
            event_ids.append(self._event(run, "tool_auto_approved", "Ferramenta autoaprovada pela politica.", invocation, {"auto_approval_id": policy.auto_approval_id}))
            event_ids.append(self._event(run, "auto_approval_granted", "Auto approval aplicado pela politica governada.", invocation, {"auto_approval_id": policy.auto_approval_id, "reason_code": policy.reason_code}))

        invocation = invocation.model_copy(update={"status": "running"})
        self.store.save_invocation(invocation)
        event_ids.append(self._event(run, "tool_started", "Ferramenta iniciada.", invocation, {"tool_name": tool.tool_name}))
        try:
            output, artifacts, validation = self._execute(tool, invocation, request, workspace, event_ids)
            artifact_ids = [artifact.artifact_id for artifact in artifacts]
            invocation = invocation.model_copy(update={
                "status": "succeeded",
                "completed_at": utc_now_iso(),
                "output_summary_sanitized": self._summary(output),
                "artifact_ids": artifact_ids,
                "evidence_refs": [f"tool:{invocation.tool_invocation_id}", *artifact_ids],
            })
            self.store.save_invocation(invocation)
            event_ids.append(self._event(run, "tool_succeeded", "Ferramenta concluiu com sucesso.", invocation, {"tool_name": tool.tool_name, "artifact_ids": artifact_ids}, artifact_ids=artifact_ids))
            return ToolInvocationResult(
                status="succeeded",
                tool_invocation=invocation,
                policy_decision=policy,
                workspace_resolution=workspace,
                output=redact_payload(output),
                validation_result=validation,
                artifacts=artifacts,
                events_emitted=event_ids,
            )
        except Exception as exc:
            invocation = invocation.model_copy(update={
                "status": "failed",
                "completed_at": utc_now_iso(),
                "error_code": type(exc).__name__,
                "output_summary_sanitized": str(redact_payload(str(exc))),
            })
            self.store.save_invocation(invocation)
            event_ids.append(self._event(run, "tool_failed", "Ferramenta falhou de forma controlada.", invocation, {"error_code": invocation.error_code}, severity="error"))
            return ToolInvocationResult(status="failed", tool_invocation=invocation, policy_decision=policy, workspace_resolution=workspace, events_emitted=event_ids)

    def list_invocations(self, *, run_id: str | None = None) -> list[ToolInvocation]:
        return self.store.list_invocations(run_id=run_id)

    def get_invocation(self, tool_invocation_id: str) -> ToolInvocation | None:
        return self.store.get_invocation(tool_invocation_id)

    def cancel_invocation(self, tool_invocation_id: str) -> ToolInvocation | None:
        invocation = self.store.get_invocation(tool_invocation_id)
        if invocation is None:
            return None
        if invocation.status in {"succeeded", "failed", "blocked", "cancelled"}:
            return invocation
        updated = invocation.model_copy(update={"status": "cancelled", "completed_at": utc_now_iso()})
        self.store.save_invocation(updated)
        run = self.kernel.get_run(updated.run_id)
        if run is not None:
            self._event(run, "tool_cancelled", "Invocacao de ferramenta cancelada.", updated, {"tool_name": updated.tool_name})
        return updated

    def upload_artifact(self, agent_id: str, session_id: str, request: ArtifactUploadRequest) -> ToolArtifactRecord:
        content = self._decode_uploaded_artifact(request)
        parent_run_id = None
        delegation_id = None
        if request.run_id:
            run = self.kernel.get_run(request.run_id)
            if run is not None:
                parent_run_id = run.parent_run_id
                delegation_id = run.delegation_id
        artifact = ToolArtifactRecord(
            session_id=session_id,
            run_id=request.run_id,
            parent_run_id=parent_run_id,
            delegation_id=delegation_id,
            agent_id=agent_id,
            project_profile_id=request.project_profile_id,
            filename=self._safe_filename(request.filename),
            content_type=request.content_type,
            size=len(content),
            size_bytes=len(content),
            status=str(request.metadata_sanitized.get("status") or "ready"),
            origin=request.origin,
            download_endpoint=None,
            validation_id=request.metadata_sanitized.get("validation_id"),
            sandbox_task_id=request.metadata_sanitized.get("sandbox_task_id"),
            project_generation_id=request.metadata_sanitized.get("project_generation_id"),
            error_reason=request.metadata_sanitized.get("error_reason"),
            evidence_refs=[str(item) for item in request.metadata_sanitized.get("evidence_refs", [])],
            metadata_sanitized=redact_payload({
                **request.metadata_sanitized,
                "parent_run_id": parent_run_id,
                "delegation_id": delegation_id,
                "project_profile_id": request.project_profile_id,
            }),
        )
        artifact = artifact.model_copy(update={"download_endpoint": f"/api/v1/agents/artifacts/{artifact.artifact_id}/download"})
        return self.store.save_artifact(artifact, content)

    def _decode_uploaded_artifact(self, request: ArtifactUploadRequest) -> bytes:
        if request.encoding == "base64":
            try:
                return base64.b64decode(request.content.encode("ascii"), validate=True)
            except Exception as exc:
                raise ValueError("invalid_base64_artifact_upload") from exc
        if request.encoding in {"text", "utf-8"}:
            return request.content.encode("utf-8")
        raise ValueError("unsupported_artifact_upload_encoding")

    def list_artifacts(self, agent_id: str, session_id: str) -> list[ToolArtifactRecord]:
        return self.store.list_artifacts(agent_id=agent_id, session_id=session_id)

    def get_artifact(self, artifact_id: str) -> ToolArtifactRecord | None:
        return self.store.get_artifact(artifact_id)

    def read_artifact_bytes(self, artifact_id: str) -> tuple[ToolArtifactRecord, bytes]:
        artifact = self.store.get_artifact(artifact_id)
        if artifact is None:
            raise FileNotFoundError(artifact_id)
        path = self.store.artifact_content_path(artifact)
        return artifact, path.read_bytes()

    def _resolve_workspace(self, tool: ToolDefinition, request: ToolInvocationCreateRequest) -> WorkspaceResolution | None:
        if not tool.requires_workspace:
            return None
        access = "read"
        if tool.can_modify_filesystem or tool.capability in {"patch_apply"}:
            access = "write"
        if tool.can_run_shell:
            access = "shell"
        return self.resolver.resolve(
            workspace_id=request.workspace_id,
            path_ref=request.path_ref or request.input.get("path_ref"),
            relative_path=request.input.get("relative_path") or request.input.get("cwd"),
            access=access,
        )

    def _execute(
        self,
        tool: ToolDefinition,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
        workspace: WorkspaceResolution | None,
        event_ids: list[str],
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult | None]:
        if tool.tool_name == "list_dir":
            return self._list_dir(invocation, request, workspace), [], None
        if tool.tool_name == "read_file":
            return self._read_file(invocation, request, workspace), [], None
        if tool.tool_name == "search_files":
            return self._search_files(invocation, request, workspace), [], None
        if tool.tool_name == "create_file":
            output = self._create_file(invocation, request, workspace)
            return output, [], self._file_content_validation("file_exists", request, output)
        if tool.tool_name == "modify_file":
            output = self._modify_file(invocation, request, workspace)
            return output, [], self._file_content_validation("file_modified", request, output)
        if tool.tool_name == "create_directory":
            return self._create_directory(invocation, request, workspace), [], self._simple_validation("directory_exists", "passed")
        if tool.tool_name == "create_archive":
            return self._create_archive(invocation, request, workspace)
        if tool.tool_name == "run_shell":
            return self._run_shell(invocation, request, workspace, event_ids), [], None
        if tool.tool_name == "create_artifact":
            artifact = self._create_artifact(invocation, request)
            return {"artifact_id": artifact.artifact_id, "download_endpoint": artifact.download_endpoint, "requires_token": True}, [artifact], None
        if tool.tool_name == "upload_artifact":
            artifact = self._create_artifact(invocation, request, origin="agent_upload")
            return {"artifact_id": artifact.artifact_id, "download_endpoint": artifact.download_endpoint, "requires_token": True}, [artifact], None
        if tool.tool_name == "download_artifact":
            artifact_id = str(request.input.get("artifact_id", ""))
            artifact = self.store.get_artifact(artifact_id)
            if artifact is None:
                raise FileNotFoundError(artifact_id)
            return {"artifact_id": artifact.artifact_id, "filename": artifact.filename, "download_endpoint": artifact.download_endpoint, "requires_token": True}, [], None
        if tool.tool_name == "validate":
            status = str(request.input.get("status", "passed"))
            validation = self._simple_validation(str(request.input.get("name", "validation")), status)
            return {"validation_id": validation.validation_id, "status": validation.status, "steps": [step.model_dump() for step in validation.steps]}, [], validation
        if tool.tool_name.startswith("pinhoforge_conversion_"):
            return self._execute_pinhoforge_conversion(tool, invocation, request)
        if tool.tool_name.startswith("pinhoforge_command_"):
            return self._execute_pinhoforge_command_catalog(tool, invocation, request)
        if tool.tool_name.startswith("pinhoforge_hardware_") or tool.tool_name in {
            "pinhoforge_tool_availability_get",
            "pinhoforge_readiness_summary_get",
            "pinhoforge_environment_report_export",
        }:
            return self._execute_pinhoforge_hardware_profiler(tool, invocation, request)
        if tool.tool_name.startswith("pinhoforge_android_"):
            return self._execute_pinhoforge_android_workbench(tool, invocation, request)
        if tool.tool_name.startswith("pinhoforge_media_"):
            return self._execute_pinhoforge_media(tool, invocation, request)
        if tool.tool_name.startswith("pinhoforge_terminal_"):
            return self._execute_pinhoforge_terminal(tool, invocation, request)
        if tool.tool_name == "generate_report":
            artifact = self._create_artifact(invocation, request, default_filename="report.md", default_content="# Report\n\nNo evidence provided.\n", origin="validation_report")
            return {"artifact_id": artifact.artifact_id, "download_endpoint": artifact.download_endpoint, "requires_token": True}, [artifact], None
        if tool.tool_name == "patch_preview":
            preview_id = f"patch_preview_{hashlib.sha256(self._summary(request.input).encode()).hexdigest()[:16]}"
            return {"preview_id": preview_id, "risk_level": tool.risk_level, "affected_files": request.input.get("affected_files", [])}, [], None
        if tool.tool_name == "patch_apply":
            apply_id = f"patch_apply_{hashlib.sha256(self._summary(request.input).encode()).hexdigest()[:16]}"
            return {"apply_id": apply_id, "files_changed": request.input.get("files_changed", [])}, [], self._simple_validation("patch_apply_contract", "passed")
        if tool.tool_name.startswith("sandbox_"):
            output = self._execute_sandbox(tool, invocation, request)
            artifacts: list[ToolArtifactRecord] = []
            artifact_id = output.get("artifact_id")
            if artifact_id:
                artifact = self.store.get_artifact(str(artifact_id))
                if artifact is not None:
                    artifacts.append(artifact)
            validation = None
            if tool.tool_name in {
                "sandbox_write_file",
                "sandbox_append_file",
                "sandbox_modify_file",
                "sandbox_mkdir",
                "sandbox_copy",
                "sandbox_move",
                "sandbox_delete_safe",
                "sandbox_zip_export",
            } and output.get("status") in {"succeeded", "ready"}:
                validation = self._simple_validation("sandbox_operation_contract", "passed")
            return output, artifacts, validation
        raise NotImplementedError(tool.tool_name)

    def _execute_pinhoforge_conversion(
        self,
        tool: ToolDefinition,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult | None]:
        from aipinho.schemas.pinhoforge_bridge.conversion import PinhoForgeConversionRequest
        from aipinho.services.pinhoforge_bridge.pinhoforge_conversion_provider import PinhoForgeConversionProvider

        provider = PinhoForgeConversionProvider()
        if tool.tool_name == "pinhoforge_conversion_list_capabilities":
            result = provider.list_capabilities(
                str(request.input.get("request_id") or "pinhoforge_conversion_capabilities"),
                metadata=dict(request.input.get("metadata") or {}),
            )
            return result.model_dump(), [], None
        operation = "dry_run" if tool.tool_name == "pinhoforge_conversion_dry_run" else "execute"
        conversion_request = PinhoForgeConversionRequest(**{**request.input, "operation": operation})
        result = provider.dry_run(conversion_request) if operation == "dry_run" else provider.execute(conversion_request)
        artifacts: list[ToolArtifactRecord] = []
        validation = None
        if operation == "execute" and result.status == "completed" and result.artifact and result.artifact.output_path_sanitized:
            output_path = Path(result.artifact.output_path_sanitized)
            content = base64.b64encode(output_path.read_bytes()).decode("ascii")
            artifact = self.upload_artifact(
                invocation.agent_id,
                invocation.session_id,
                ArtifactUploadRequest(
                    filename=result.artifact.filename,
                    content_type=result.artifact.content_type,
                    content=content,
                    encoding="base64",
                    run_id=invocation.run_id,
                    project_profile_id=invocation.project_profile_id,
                    origin="pinhoforge_conversion_output",
                    metadata_sanitized={
                        "provider_id": result.provider_id,
                        "conversion_request_id": result.request_id,
                        "source_tool_invocation_id": invocation.tool_invocation_id,
                        "route": result.route or {},
                    },
                ),
            )
            artifacts.append(artifact)
            result = result.model_copy(update={
                "artifact": result.artifact.model_copy(update={
                    "artifact_id": artifact.artifact_id,
                    "download_endpoint": artifact.download_endpoint,
                })
            })
            validation = self._simple_validation("pinhoforge_conversion_artifact_registered", "passed")
        return result.model_dump(), artifacts, validation

    def _execute_pinhoforge_command_catalog(
        self,
        tool: ToolDefinition,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult | None]:
        from aipinho.schemas.pinhoforge_bridge.command_catalog import PinhoForgeCommandCatalogQuery, PinhoForgeCommandPreviewRequest
        from aipinho.services.pinhoforge_bridge.pinhoforge_command_catalog_provider import PinhoForgeCommandCatalogProvider

        provider = PinhoForgeCommandCatalogProvider()
        if tool.tool_name == "pinhoforge_command_search":
            result = provider.search(PinhoForgeCommandCatalogQuery(**request.input))
        elif tool.tool_name == "pinhoforge_command_preview":
            result = provider.preview(PinhoForgeCommandPreviewRequest(**request.input))
        else:
            result = provider.execute_blocked(str(request.input.get("request_id") or invocation.tool_invocation_id))
        return result.model_dump(), [], None

    def _execute_pinhoforge_hardware_profiler(
        self,
        tool: ToolDefinition,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult | None]:
        from aipinho.schemas.pinhoforge_bridge.hardware_profiler import PinhoForgeHardwareProfilerRequest
        from aipinho.services.pinhoforge_bridge.pinhoforge_hardware_profiler_provider import PinhoForgeHardwareProfilerProvider

        operation_map = {
            "pinhoforge_hardware_profile_get": "get_environment_profile",
            "pinhoforge_tool_availability_get": "get_tool_availability",
            "pinhoforge_readiness_summary_get": "get_readiness_summary",
            "pinhoforge_environment_report_export": "export_environment_report",
        }
        provider = PinhoForgeHardwareProfilerProvider()
        profiler_request = PinhoForgeHardwareProfilerRequest(**{**request.input, "operation": operation_map[tool.tool_name]})
        result = provider.handle(profiler_request)
        artifacts: list[ToolArtifactRecord] = []
        validation = None
        if tool.tool_name == "pinhoforge_environment_report_export" and result.report_markdown:
            artifacts.extend(
                self._register_bridge_artifacts(
                    invocation,
                    [
                        {
                            "filename": "pinhoforge_environment_report.md",
                            "content_type": "text/markdown",
                            "content": result.report_markdown,
                        },
                        {
                            "filename": "pinhoforge_environment_report.json",
                            "content_type": "application/json",
                            "content": json.dumps(result.report_json or {}, ensure_ascii=True, indent=2),
                        },
                    ],
                    origin="pinhoforge_hardware_profile_report",
                    metadata={
                        "provider_id": result.provider_id,
                        "hardware_request_id": result.request_id,
                        "source_tool_invocation_id": invocation.tool_invocation_id,
                    },
                )
            )
            validation = self._simple_validation("pinhoforge_hardware_report_registered", "passed")
        payload = result.model_dump()
        if artifacts:
            payload["artifacts"] = [
                {"artifact_id": artifact.artifact_id, "filename": artifact.filename, "download_endpoint": artifact.download_endpoint, "requires_token": True}
                for artifact in artifacts
            ]
        return payload, artifacts, validation

    def _execute_pinhoforge_android_workbench(
        self,
        tool: ToolDefinition,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult | None]:
        from aipinho.schemas.pinhoforge_bridge.android_workbench import PinhoForgeAndroidWorkbenchRequest
        from aipinho.services.pinhoforge_bridge.pinhoforge_android_workbench_provider import PinhoForgeAndroidWorkbenchProvider

        operation_map = {
            "pinhoforge_android_project_detect": "detect_project",
            "pinhoforge_android_environment_readiness": "environment_readiness",
            "pinhoforge_android_gradle_task_list": "list_gradle_tasks",
            "pinhoforge_android_gradle_task_execute": "execute_gradle_task",
            "pinhoforge_android_adb_devices": "adb_devices",
            "pinhoforge_android_logcat_readonly": "logcat_readonly",
            "pinhoforge_android_report_export": "export_report",
        }
        provider = PinhoForgeAndroidWorkbenchProvider()
        android_request = PinhoForgeAndroidWorkbenchRequest(**{**request.input, "operation": operation_map[tool.tool_name]})
        result = provider.handle(android_request)
        artifacts: list[ToolArtifactRecord] = []
        validation = None
        artifact_specs: list[dict[str, str]] = []
        if result.report_markdown:
            artifact_specs.append(
                {
                    "filename": "android_workbench_report.md",
                    "content_type": "text/markdown",
                    "content": result.report_markdown,
                }
            )
        if result.report_json is not None:
            artifact_specs.append(
                {
                    "filename": "android_workbench_report.json",
                    "content_type": "application/json",
                    "content": json.dumps(result.report_json, ensure_ascii=True, indent=2),
                }
            )
        if result.logcat and result.logcat.get("lines"):
            artifact_specs.append(
                {
                    "filename": "android_logcat.txt",
                    "content_type": "text/plain",
                    "content": "\n".join(str(line) for line in result.logcat.get("lines", [])),
                }
            )
        if artifact_specs:
            artifacts.extend(
                self._register_bridge_artifacts(
                    invocation,
                    artifact_specs,
                    origin="pinhoforge_android_workbench_output",
                    metadata={
                        "provider_id": result.provider_id,
                        "android_request_id": result.request_id,
                        "source_tool_invocation_id": invocation.tool_invocation_id,
                        "task_id": request.input.get("task_id"),
                    },
                )
            )
            validation = self._simple_validation("pinhoforge_android_artifacts_registered", "passed")
        payload = result.model_dump()
        if artifacts:
            payload["artifacts"] = [
                {"artifact_id": artifact.artifact_id, "filename": artifact.filename, "download_endpoint": artifact.download_endpoint, "requires_token": True}
                for artifact in artifacts
            ]
        return payload, artifacts, validation

    def _execute_pinhoforge_media(
        self,
        tool: ToolDefinition,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult | None]:
        from aipinho.schemas.pinhoforge_bridge.media_3d import PinhoForge3DRequest, PinhoForgeImageRequest
        from aipinho.services.pinhoforge_bridge.pinhoforge_media_3d_provider import PinhoForge3DProvider, PinhoForgeImageProvider

        artifacts: list[ToolArtifactRecord] = []
        validation = None
        if tool.tool_name == "pinhoforge_media_image_operation":
            provider = PinhoForgeImageProvider()
            media_request = PinhoForgeImageRequest(**request.input)
            result = provider.handle(media_request)
            if result.status in {"completed", "completed_with_warnings"} and result.artifact and result.artifact.output_path_sanitized:
                output_path = Path(result.artifact.output_path_sanitized)
                content = base64.b64encode(output_path.read_bytes()).decode("ascii")
                artifact = self.upload_artifact(
                    invocation.agent_id,
                    invocation.session_id,
                    ArtifactUploadRequest(
                        filename=result.artifact.filename,
                        content_type=result.artifact.content_type,
                        content=content,
                        encoding="base64",
                        run_id=invocation.run_id,
                        project_profile_id=invocation.project_profile_id,
                        origin="pinhoforge_media_image_output",
                        metadata_sanitized={
                            "provider_id": result.provider_id,
                            "image_request_id": result.request_id,
                            "source_tool_invocation_id": invocation.tool_invocation_id,
                        },
                    ),
                )
                artifacts.append(artifact)
                result = result.model_copy(
                    update={
                        "artifact": result.artifact.model_copy(
                            update={
                                "artifact_id": artifact.artifact_id,
                                "download_endpoint": artifact.download_endpoint,
                            }
                        )
                    }
                )
            if result.report_markdown:
                artifacts.extend(
                    self._register_bridge_artifacts(
                        invocation,
                        [
                            {
                                "filename": "pinhoforge_media_image_report.md",
                                "content_type": "text/markdown",
                                "content": result.report_markdown,
                            },
                            {
                                "filename": "pinhoforge_media_image_report.json",
                                "content_type": "application/json",
                                "content": json.dumps(result.report_json or {}, ensure_ascii=True, indent=2),
                            },
                        ],
                        origin="pinhoforge_media_image_report",
                        metadata={
                            "provider_id": result.provider_id,
                            "image_request_id": result.request_id,
                            "source_tool_invocation_id": invocation.tool_invocation_id,
                        },
                    )
                )
            if artifacts:
                validation = self._simple_validation("pinhoforge_media_image_artifacts_registered", "passed")
            payload = result.model_dump()
            if artifacts:
                payload["artifacts"] = [
                    {"artifact_id": artifact.artifact_id, "filename": artifact.filename, "download_endpoint": artifact.download_endpoint, "requires_token": True}
                    for artifact in artifacts
                ]
            return payload, artifacts, validation

        provider = PinhoForge3DProvider()
        media_request = PinhoForge3DRequest(**request.input)
        result = provider.handle(media_request)
        if result.status in {"completed", "completed_with_warnings"} and result.artifact and result.artifact.output_path_sanitized:
            output_path = Path(result.artifact.output_path_sanitized)
            content = base64.b64encode(output_path.read_bytes()).decode("ascii")
            artifact = self.upload_artifact(
                invocation.agent_id,
                invocation.session_id,
                ArtifactUploadRequest(
                    filename=result.artifact.filename,
                    content_type=result.artifact.content_type,
                    content=content,
                    encoding="base64",
                    run_id=invocation.run_id,
                    project_profile_id=invocation.project_profile_id,
                    origin="pinhoforge_media_3d_output",
                    metadata_sanitized={
                        "provider_id": result.provider_id,
                        "scene_request_id": result.request_id,
                        "source_tool_invocation_id": invocation.tool_invocation_id,
                    },
                ),
            )
            artifacts.append(artifact)
            result = result.model_copy(
                update={
                    "artifact": result.artifact.model_copy(
                        update={
                            "artifact_id": artifact.artifact_id,
                            "download_endpoint": artifact.download_endpoint,
                        }
                    )
                }
            )
        if result.report_markdown:
            artifacts.extend(
                self._register_bridge_artifacts(
                    invocation,
                    [
                        {
                            "filename": "pinhoforge_media_3d_report.md",
                            "content_type": "text/markdown",
                            "content": result.report_markdown,
                        },
                        {
                            "filename": "pinhoforge_media_3d_report.json",
                            "content_type": "application/json",
                            "content": json.dumps(result.report_json or {}, ensure_ascii=True, indent=2),
                        },
                    ],
                    origin="pinhoforge_media_3d_report",
                    metadata={
                        "provider_id": result.provider_id,
                        "scene_request_id": result.request_id,
                        "source_tool_invocation_id": invocation.tool_invocation_id,
                    },
                )
            )
        if artifacts:
            validation = self._simple_validation("pinhoforge_media_3d_artifacts_registered", "passed")
        payload = result.model_dump()
        if artifacts:
            payload["artifacts"] = [
                {"artifact_id": artifact.artifact_id, "filename": artifact.filename, "download_endpoint": artifact.download_endpoint, "requires_token": True}
                for artifact in artifacts
            ]
        return payload, artifacts, validation

    def _execute_pinhoforge_terminal(
        self,
        tool: ToolDefinition,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult | None]:
        from aipinho.schemas.pinhoforge_bridge.governed_terminal import (
            PinhoForgeTerminalCancelRequest,
            PinhoForgeTerminalExecuteRequest,
            PinhoForgeTerminalPreviewRequest,
        )
        from aipinho.services.pinhoforge_bridge.pinhoforge_governed_terminal_provider import PinhoForgeGovernedTerminalProvider

        provider = PinhoForgeGovernedTerminalProvider()
        artifacts: list[ToolArtifactRecord] = []
        validation = None
        if tool.tool_name == "pinhoforge_terminal_preview":
            result = provider.preview(PinhoForgeTerminalPreviewRequest(**request.input))
            return result.model_dump(), [], None
        if tool.tool_name == "pinhoforge_terminal_cancel":
            result = provider.cancel_execution(PinhoForgeTerminalCancelRequest(**request.input))
            return result.model_dump(), [], None
        if tool.tool_name == "pinhoforge_terminal_status":
            session_id = str(request.input.get("session_id") or "")
            result = provider.session_status(str(request.input.get("request_id") or invocation.tool_invocation_id), session_id)
            return result.model_dump(), [], None

        result = provider.execute(PinhoForgeTerminalExecuteRequest(**request.input))
        if result.report_markdown:
            artifacts.extend(
                self._register_bridge_artifacts(
                    invocation,
                    [
                        {
                            "filename": "pinhoforge_terminal_report.md",
                            "content_type": "text/markdown",
                            "content": result.report_markdown,
                        },
                        {
                            "filename": "pinhoforge_terminal_report.json",
                            "content_type": "application/json",
                            "content": json.dumps(result.report_json or {}, ensure_ascii=True, indent=2),
                        },
                    ],
                    origin="pinhoforge_terminal_report",
                    metadata={
                        "provider_id": result.provider_id,
                        "terminal_request_id": result.request_id,
                        "source_tool_invocation_id": invocation.tool_invocation_id,
                    },
                )
            )
        for item in result.output_artifacts:
            actual_path = item.get("path")
            if not actual_path:
                continue
            output_path = Path(str(actual_path))
            if not output_path.exists() or not output_path.is_file():
                continue
            content = base64.b64encode(output_path.read_bytes()).decode("ascii")
            artifacts.append(
                self.upload_artifact(
                    invocation.agent_id,
                    invocation.session_id,
                    ArtifactUploadRequest(
                        filename=str(item.get("filename") or output_path.name),
                        content_type=str(item.get("content_type") or "application/octet-stream"),
                        content=content,
                        encoding="base64",
                        run_id=invocation.run_id,
                        project_profile_id=invocation.project_profile_id,
                        origin="pinhoforge_terminal_output",
                        metadata_sanitized={
                            "provider_id": result.provider_id,
                            "terminal_request_id": result.request_id,
                            "source_tool_invocation_id": invocation.tool_invocation_id,
                        },
                    ),
                )
            )
        if artifacts:
            validation = self._simple_validation("pinhoforge_terminal_artifacts_registered", "passed")
        payload = result.model_dump()
        if artifacts:
            payload["artifacts"] = [
                {"artifact_id": artifact.artifact_id, "filename": artifact.filename, "download_endpoint": artifact.download_endpoint, "requires_token": True}
                for artifact in artifacts
            ]
        return payload, artifacts, validation

    def _register_bridge_artifacts(
        self,
        invocation: ToolInvocation,
        artifact_specs: list[dict[str, str]],
        *,
        origin: str,
        metadata: dict[str, Any],
    ) -> list[ToolArtifactRecord]:
        artifacts: list[ToolArtifactRecord] = []
        for spec in artifact_specs:
            artifact = self.upload_artifact(
                invocation.agent_id,
                invocation.session_id,
                ArtifactUploadRequest(
                    filename=spec["filename"],
                    content_type=spec["content_type"],
                    content=spec["content"],
                    encoding="text",
                    run_id=invocation.run_id,
                    project_profile_id=invocation.project_profile_id,
                    origin=origin,
                    metadata_sanitized=metadata,
                ),
            )
            artifacts.append(artifact)
        return artifacts

    def _execute_sandbox(self, tool: ToolDefinition, invocation: ToolInvocation, request: ToolInvocationCreateRequest) -> dict[str, Any]:
        from aipinho.schemas.sandbox import SandboxArtifactExportRequest, SandboxCleanupPreviewRequest, SandboxFileRequest, SandboxShellRequest
        from aipinho.services.sandbox.sandbox_artifact_service import SandboxArtifactService
        from aipinho.services.sandbox.sandbox_cleanup_service import SandboxCleanupService
        from aipinho.services.sandbox.sandbox_file_service import SandboxFileService
        from aipinho.services.sandbox.sandbox_shell_service import SandboxShellService
        from aipinho.services.sandbox.sandbox_validation_service import SandboxValidationService

        workspace_id = request.sandbox_workspace_id or str(request.input.get("sandbox_workspace_id") or "sandbox_ws_default")
        task_id = request.sandbox_task_id or request.input.get("sandbox_task_id")
        rel = request.relative_path or str(request.input.get("relative_path") or request.input.get("path") or ".")
        file_request = SandboxFileRequest(
            sandbox_workspace_id=workspace_id,
            sandbox_task_id=str(task_id) if task_id else None,
            relative_path=rel,
            destination_relative_path=request.input.get("destination_relative_path"),
            content=request.input.get("content"),
            overwrite=bool(request.input.get("overwrite", False)),
            expected_hash=request.input.get("expected_hash"),
        )
        files = SandboxFileService()
        if tool.tool_name == "sandbox_read_file":
            return files.read_file(file_request)
        if tool.tool_name == "sandbox_write_file":
            return files.write_file(file_request).model_dump()
        if tool.tool_name == "sandbox_append_file":
            return files.write_file(file_request, append=True).model_dump()
        if tool.tool_name == "sandbox_modify_file":
            return files.modify_file(file_request).model_dump()
        if tool.tool_name == "sandbox_mkdir":
            return files.mkdir(file_request).model_dump()
        if tool.tool_name == "sandbox_list_files":
            return files.list_files(file_request)
        if tool.tool_name == "sandbox_copy":
            return files.copy(file_request).model_dump()
        if tool.tool_name == "sandbox_move":
            return files.move(file_request).model_dump()
        if tool.tool_name == "sandbox_delete_safe":
            return files.delete_safe(file_request).model_dump()
        if tool.tool_name == "sandbox_run_shell":
            shell = SandboxShellService().run(SandboxShellRequest(
                sandbox_workspace_id=workspace_id,
                sandbox_task_id=str(task_id) if task_id else None,
                command=str(request.input.get("command") or ""),
                cwd_relative=str(request.cwd_inside_sandbox or request.input.get("cwd_relative") or "."),
                timeout_seconds=int(request.input.get("timeout_seconds", 120)),
                category=request.input.get("category"),
            ))
            return shell.model_dump()
        if tool.tool_name == "sandbox_zip_export":
            export = SandboxArtifactService(tool_gateway=self).export_zip(SandboxArtifactExportRequest(
                sandbox_workspace_id=workspace_id,
                sandbox_task_id=str(task_id) if task_id else None,
                filename=str(request.input.get("filename") or "sandbox_artifact.zip"),
                project_generation_id=request.input.get("project_generation_id"),
                include_paths=request.input.get("include_paths") or ["."],
                exclude_globs=request.input.get("exclude_globs") or [],
            ))
            return export.model_dump()
        if tool.tool_name == "sandbox_validate":
            return SandboxValidationService(tool_gateway=self).validate(
                sandbox_workspace_id=workspace_id,
                sandbox_task_id=str(task_id) if task_id else None,
                relative_paths=[str(item) for item in (request.input.get("relative_paths") or [])],
                artifact_ids=[str(item) for item in (request.input.get("artifact_ids") or [])],
            ).model_dump()
        if tool.tool_name == "sandbox_cleanup_preview":
            return SandboxCleanupService().preview(SandboxCleanupPreviewRequest()).model_dump()
        if tool.tool_name == "sandbox_cleanup_apply":
            return SandboxCleanupService().apply(str(request.input.get("cleanup_preview_id") or ""))
        raise NotImplementedError(tool.tool_name)

    def _workspace_path(self, workspace: WorkspaceResolution | None) -> Path:
        if workspace is None or not workspace.resolved_path_sanitized:
            raise PermissionError("workspace_not_resolved")
        return Path(workspace.resolved_path_sanitized)

    def _list_dir(self, invocation: ToolInvocation, request: ToolInvocationCreateRequest, workspace: WorkspaceResolution | None) -> dict[str, Any]:
        base = self._workspace_path(workspace)
        max_depth = int(request.input.get("max_depth", 1))
        include_hidden = bool(request.input.get("include_hidden", False))
        entries: list[dict[str, Any]] = []
        for path in base.rglob("*") if max_depth > 1 else base.iterdir():
            if not include_hidden and any(part.startswith(".") for part in path.relative_to(base).parts):
                continue
            depth = len(path.relative_to(base).parts)
            if depth > max_depth:
                continue
            entries.append({"name": path.name, "relative_path": str(path.relative_to(base)), "is_dir": path.is_dir(), "size": path.stat().st_size if path.is_file() else 0})
        return {"entries": entries, "count": len(entries), "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}

    def _read_file(self, invocation: ToolInvocation, request: ToolInvocationCreateRequest, workspace: WorkspaceResolution | None) -> dict[str, Any]:
        path = self._workspace_path(workspace)
        max_bytes = int(request.input.get("max_bytes", 1_000_000))
        mode = str(request.input.get("mode", "text"))
        data = path.read_bytes()[:max_bytes]
        digest = hashlib.sha256(data).hexdigest()
        if mode == "binary_metadata":
            return {"size": path.stat().st_size, "hash": digest, "content_sanitized": None, "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}
        text = data.decode("utf-8", errors="replace")
        return {"content_sanitized": redact_payload(text), "size": path.stat().st_size, "hash": digest, "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}

    def _search_files(self, invocation: ToolInvocation, request: ToolInvocationCreateRequest, workspace: WorkspaceResolution | None) -> dict[str, Any]:
        base = self._workspace_path(workspace)
        query = str(request.input.get("query") or request.input.get("pattern") or "")
        include_globs = request.input.get("include_globs") or ["*"]
        exclude_globs = request.input.get("exclude_globs") or []
        max_results = int(request.input.get("max_results", 50))
        matches: list[dict[str, Any]] = []
        for path in base.rglob("*"):
            if len(matches) >= max_results:
                break
            if not path.is_file():
                continue
            rel = str(path.relative_to(base))
            if not any(fnmatch.fnmatch(rel, glob) for glob in include_globs):
                continue
            if any(fnmatch.fnmatch(rel, glob) for glob in exclude_globs):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if query.lower() in text.lower() or fnmatch.fnmatch(path.name, query):
                matches.append({"relative_path": rel, "size": path.stat().st_size})
        return {"matches": matches, "count": len(matches), "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}

    def _create_file(self, invocation: ToolInvocation, request: ToolInvocationCreateRequest, workspace: WorkspaceResolution | None) -> dict[str, Any]:
        path = self._workspace_path(workspace)
        overwrite = bool(request.input.get("overwrite", False))
        if path.exists() and not overwrite:
            raise FileExistsError("target_file_exists")
        content = str(request.input.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        data = content.encode("utf-8")
        return {"file_path_sanitized": str(path), "bytes_written": len(data), "hash": hashlib.sha256(data).hexdigest(), "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}

    def _modify_file(self, invocation: ToolInvocation, request: ToolInvocationCreateRequest, workspace: WorkspaceResolution | None) -> dict[str, Any]:
        path = self._workspace_path(workspace)
        content = str(request.input.get("content", ""))
        expected_hash = request.input.get("expected_hash")
        if expected_hash and path.exists():
            current = hashlib.sha256(path.read_bytes()).hexdigest()
            if current != expected_hash:
                raise ValueError("expected_hash_mismatch")
        path.write_text(content, encoding="utf-8")
        data = content.encode("utf-8")
        return {"file_path_sanitized": str(path), "bytes_written": len(data), "hash": hashlib.sha256(data).hexdigest(), "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}

    def _create_directory(self, invocation: ToolInvocation, request: ToolInvocationCreateRequest, workspace: WorkspaceResolution | None) -> dict[str, Any]:
        path = self._workspace_path(workspace)
        existed = path.exists()
        path.mkdir(parents=True, exist_ok=True)
        return {"directory_path_sanitized": str(path), "created": not existed, "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}

    def _create_archive(
        self,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
        workspace: WorkspaceResolution | None,
    ) -> tuple[dict[str, Any], list[ToolArtifactRecord], ValidationResult]:
        if workspace is None or not workspace.allowed or not workspace.root_path_sanitized:
            raise PermissionError("workspace_write_denied")
        target = self._workspace_path(workspace)
        if target.suffix.casefold() != ".zip":
            raise ValueError("archive_target_must_be_zip")
        if target.exists() and not bool(request.input.get("overwrite", False)):
            raise FileExistsError("target_archive_exists")

        raw_sources = request.input.get("source_paths") or []
        if not isinstance(raw_sources, list) or not raw_sources:
            raise ValueError("archive_source_path_required")
        root = Path(workspace.root_path_sanitized).resolve()
        base_path_ref = request.input.get("base_path_ref") or request.input.get("archive_base_path")
        if base_path_ref:
            base = Path(str(base_path_ref))
            candidate_base = base.resolve() if base.is_absolute() else (root / base).resolve()
            try:
                candidate_base.relative_to(root)
            except ValueError as exc:
                raise PermissionError("archive_base_outside_workspace") from exc
            if candidate_base.suffix:
                candidate_base = candidate_base.parent
            root = candidate_base
        source_paths: list[Path] = []
        for item in raw_sources:
            source = Path(str(item))
            candidate = source.resolve() if source.is_absolute() else (root / source).resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise PermissionError("archive_source_outside_workspace") from exc
            if candidate == target.resolve():
                continue
            if not candidate.exists():
                if bool(request.input.get("skip_missing", True)):
                    continue
                raise FileNotFoundError(str(candidate))
            source_paths.append(candidate)
        if not source_paths:
            raise ValueError("archive_no_existing_sources")

        from aipinho.services.security.secret_guard_service import SecretGuardService

        guard = SecretGuardService()
        max_files = int(request.input.get("max_files", 20000))
        max_total_bytes = int(request.input.get("max_total_bytes", 536870912))
        scan_extensions = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".kt", ".kts", ".java", ".js", ".ts", ".tsx", ".jsx", ".cs"}
        included: list[tuple[Path, str]] = []
        total_bytes = 0
        for source in source_paths:
            candidates = [source] if source.is_file() else [item for item in source.rglob("*") if item.is_file()]
            for candidate in candidates:
                if len(included) >= max_files:
                    raise ValueError("archive_file_limit_exceeded")
                if candidate.is_symlink() or guard.is_secret_path(candidate):
                    continue
                size = candidate.stat().st_size
                if total_bytes + size > max_total_bytes:
                    raise ValueError("archive_total_size_limit_exceeded")
                if candidate.suffix.casefold() in scan_extensions:
                    text = candidate.read_text(encoding="utf-8", errors="ignore")
                    if contains_secret(text) or guard.redact(text)[1]:
                        continue
                arcname = candidate.relative_to(root).as_posix()
                if all(existing_arcname != arcname for _, existing_arcname in included):
                    included.append((candidate, arcname))
                    total_bytes += size
        if not included:
            raise ValueError("archive_no_allowed_files")

        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for source, arcname in included:
                bundle.write(source, arcname=arcname)
        content = target.read_bytes()

        with zipfile.ZipFile(target, "r") as bundle:
            bad_entry = bundle.testzip()
            entries = bundle.namelist()
        if bad_entry is not None:
            raise ValueError("archive_crc_validation_failed")
        if not entries or not content:
            raise ValueError("archive_empty_after_creation")

        artifact = ToolArtifactRecord(
            session_id=invocation.session_id,
            run_id=invocation.run_id,
            agent_id=invocation.agent_id,
            tool_invocation_id=invocation.tool_invocation_id,
            parent_run_id=invocation.parent_run_id,
            delegation_id=invocation.delegation_id,
            project_profile_id=invocation.project_profile_id,
            filename=target.name,
            content_type="application/zip",
            size=len(content),
            size_bytes=len(content),
            status="ready",
            origin="workspace_evidence_archive",
            download_endpoint=None,
            evidence_refs=[f"tool:{invocation.tool_invocation_id}"],
            metadata_sanitized=redact_payload({
                **invocation.metadata_sanitized,
                "workspace_file": str(target),
                "included_count": len(entries),
            }),
        )
        artifact = artifact.model_copy(update={"download_endpoint": f"/api/v1/agents/artifacts/{artifact.artifact_id}/download"})
        saved = self.store.save_artifact(artifact, content)
        validation = ValidationResult(
            status="passed",
            steps=[
                ValidationStep(name="archive_exists", status="passed", human_message="O ZIP foi criado no workspace.", evidence_refs=[f"tool:{invocation.tool_invocation_id}"]),
                ValidationStep(name="archive_non_empty", status="passed", human_message="O ZIP possui conteudo.", evidence_refs=[f"artifact:{saved.artifact_id}"]),
                ValidationStep(name="archive_entries_valid", status="passed", human_message="As entries do ZIP passaram na verificacao CRC.", evidence_refs=[f"artifact:{saved.artifact_id}"]),
            ],
            evidence_refs=[f"tool:{invocation.tool_invocation_id}", f"artifact:{saved.artifact_id}"],
        )
        output = {
            "archive_path_sanitized": str(target),
            "bytes_written": len(content),
            "hash": hashlib.sha256(content).hexdigest(),
            "entries": entries,
            "included_count": len(entries),
            "artifact_id": saved.artifact_id,
            "download_endpoint": saved.download_endpoint,
            "requires_token": True,
            "evidence_refs": [f"tool:{invocation.tool_invocation_id}", f"artifact:{saved.artifact_id}"],
        }
        return output, [saved], validation

    def _run_shell(
        self,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
        workspace: WorkspaceResolution | None,
        event_ids: list[str],
    ) -> dict[str, Any]:
        command = request.input.get("command")
        argv = request.input.get("argv")
        if not argv:
            if not command:
                raise ValueError("command_required")
            argv = shlex.split(str(command), posix=os.name != "nt")
        argv = [self._strip_wrapping_quotes(str(part)) for part in argv]
        timeout = int(request.input.get("timeout_seconds", 120))
        cwd = workspace.resolved_path_sanitized if workspace and workspace.resolved_path_sanitized else None
        argv = self._resolve_relative_executable(argv, cwd)
        run = self.kernel.get_run(invocation.run_id)
        if run is not None:
            event_ids.append(self._event(run, "shell_started", "Shell governado iniciado.", invocation, {"argv": argv, "cwd": cwd}))
        start = time.perf_counter()
        completed = self.shell_runner.run([str(part) for part in argv], cwd=cwd, timeout=timeout)
        duration = int((time.perf_counter() - start) * 1000)
        stdout = str(redact_payload(completed.stdout or ""))
        stderr = str(redact_payload(completed.stderr or ""))
        if run is not None and stdout:
            event_ids.append(self._event(run, "shell_stdout", "Shell produziu stdout sanitizado.", invocation, {"stdout_sanitized": stdout}, visible=False))
        if run is not None and stderr:
            event_ids.append(self._event(run, "shell_stderr", "Shell produziu stderr sanitizado.", invocation, {"stderr_sanitized": stderr}, severity="warning", visible=False))
        if run is not None:
            event_ids.append(self._event(run, "shell_finished", "Shell governado finalizado.", invocation, {"exit_code": completed.returncode, "duration_ms": duration}))
        return {"command_id": f"command_{invocation.tool_invocation_id}", "exit_code": completed.returncode, "stdout_sanitized": stdout, "stderr_sanitized": stderr, "duration_ms": duration, "evidence_refs": [f"tool:{invocation.tool_invocation_id}"]}

    @staticmethod
    def _strip_wrapping_quotes(value: str) -> str:
        text = str(value)
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            return text[1:-1]
        return text

    @staticmethod
    def _resolve_relative_executable(argv: list[str], cwd: str | None) -> list[str]:
        if not argv or not cwd:
            return argv
        executable = Path(argv[0])
        if executable.is_absolute() or not any(sep in argv[0] for sep in ("/", "\\")):
            return argv
        workspace = Path(cwd).resolve()
        candidate = (workspace / executable).resolve()
        try:
            candidate.relative_to(workspace)
        except ValueError:
            return argv
        if candidate.exists():
            return [str(candidate), *argv[1:]]
        return argv

    def _create_artifact(
        self,
        invocation: ToolInvocation,
        request: ToolInvocationCreateRequest,
        *,
        default_filename: str = "artifact.txt",
        default_content: str = "",
        origin: str = "agent_generated",
    ) -> ToolArtifactRecord:
        filename = self._safe_filename(str(request.input.get("filename") or default_filename))
        content = str(request.input.get("content", default_content)).encode("utf-8")
        artifact = ToolArtifactRecord(
            session_id=invocation.session_id,
            run_id=invocation.run_id,
            agent_id=invocation.agent_id,
            tool_invocation_id=invocation.tool_invocation_id,
            parent_run_id=invocation.parent_run_id,
            delegation_id=invocation.delegation_id,
            project_profile_id=invocation.project_profile_id,
            filename=filename,
            content_type=str(request.input.get("content_type", "text/plain")),
            size=len(content),
            size_bytes=len(content),
            status=str(request.input.get("status") or "ready"),
            origin=origin,
            download_endpoint=None,
            validation_id=request.input.get("validation_id"),
            sandbox_task_id=invocation.sandbox_task_id,
            project_generation_id=request.input.get("project_generation_id"),
            error_reason=request.input.get("error_reason"),
            evidence_refs=[f"tool:{invocation.tool_invocation_id}"],
            metadata_sanitized=redact_payload({
                **invocation.metadata_sanitized,
                "project_profile_id": invocation.project_profile_id,
                "workspace_profile_id": invocation.workspace_profile_id,
                "validation_profile_id": invocation.validation_profile_id,
                "command_profile_id": invocation.command_profile_id,
                "skill_id": invocation.skill_id,
                "skill_execution_id": invocation.skill_execution_id,
                "tool_invocation_id": invocation.tool_invocation_id,
            }),
        )
        artifact = artifact.model_copy(update={"download_endpoint": f"/api/v1/agents/artifacts/{artifact.artifact_id}/download"})
        saved = self.store.save_artifact(artifact, content)
        run = self.kernel.get_run(invocation.run_id)
        if run is not None:
            self._event(run, "artifact_created", "Artifact criado pelo Tool Gateway.", invocation, {"artifact_id": saved.artifact_id, "filename": saved.filename}, artifact_ids=[saved.artifact_id])
            self._create_artifact_memory_candidate(run, invocation, saved)
        return saved

    def _create_artifact_memory_candidate(self, run, invocation: ToolInvocation, artifact: ToolArtifactRecord) -> None:
        try:
            from aipinho.schemas.agents.memory import MemoryCandidateCreateRequest
            from aipinho.services.agents.agent_memory_gateway_service import AgentMemoryGatewayService

            namespace = f"memory:project:{run.project_profile_id}" if run.project_profile_id else "memory:project" if run.workspace_id else f"memory:{invocation.agent_id}"
            scope = "project" if run.project_profile_id or run.workspace_id else "private"
            candidate = AgentMemoryGatewayService(kernel=self.kernel).create_candidate(
                MemoryCandidateCreateRequest(
                    proposed_by_agent_id=invocation.agent_id,
                    namespace=namespace,
                    scope=scope,
                    title=f"Artifact criado: {artifact.filename}",
                    content_sanitized=f"Artifact {artifact.filename} criado pelo Tool Gateway para a operacao {run.operation_type}.",
                    memory_type="artifact_reference",
                    source_ref=f"artifact:{artifact.artifact_id}",
                    evidence_refs=[f"run:{run.run_id}", f"tool:{invocation.tool_invocation_id}", f"artifact:{artifact.artifact_id}"],
                    confidence="medium",
                    reason_to_remember="artifact_created_by_tool_gateway",
                    session_id=run.session_id,
                    run_id=run.run_id,
                    metadata_sanitized={
                        "artifact_id": artifact.artifact_id,
                        "tool_invocation_id": invocation.tool_invocation_id,
                        "workspace_id": run.workspace_id,
                        "project_profile_id": run.project_profile_id,
                    },
                )
            )
            self._event(run, "memory_candidate_created", "Memory candidate criado para artifact.", invocation, {"candidate_id": candidate.candidate_id, "artifact_id": artifact.artifact_id}, visible=False)
        except Exception as exc:
            self._event(run, "memory_candidate_create_failed", "Memory candidate para artifact nao foi criado.", invocation, {"error_type": type(exc).__name__}, severity="warning", visible=False)
            return

    def _simple_validation(self, name: str, status: str) -> ValidationResult:
        return ValidationResult(status=status, steps=[ValidationStep(name=name, status=status, human_message=f"{name}: {status}")])

    def _file_content_validation(self, name: str, request: ToolInvocationCreateRequest, output: dict[str, Any]) -> ValidationResult:
        expected = str(request.input.get("expected_contains") or "").strip()
        if not expected:
            return self._simple_validation(name, "passed")
        content = str(request.input.get("content") or "")
        passed = expected.lower() in content.lower()
        status = "passed" if passed else "failed"
        return ValidationResult(
            status=status,
            steps=[
                ValidationStep(
                    name=f"{name}_contains_expected",
                    status=status,
                    evidence_refs=list(output.get("evidence_refs") or []),
                    human_message=f"{name}_contains_expected: {status}",
                    technical_summary_sanitized="expected content marker was present" if passed else "expected content marker was missing",
                )
            ],
            evidence_refs=list(output.get("evidence_refs") or []),
        )

    def _event(
        self,
        run,
        event_type: str,
        message: str,
        invocation: ToolInvocation,
        payload: dict[str, Any],
        *,
        severity: str = "info",
        visible: bool = True,
        artifact_ids: list[str] | None = None,
    ) -> str:
        event = self.event_bus.append_event(
            run,
            AgentEventCreateRequest(
                event_type=event_type,
                severity=severity,
                human_message=message,
                technical_summary_sanitized=event_type,
                payload_sanitized=redact_payload({
                    "tool_invocation_id": invocation.tool_invocation_id,
                    "delegation_id": invocation.delegation_id,
                    "parent_run_id": invocation.parent_run_id,
                    "project_profile_id": invocation.project_profile_id,
                    "workspace_profile_id": invocation.workspace_profile_id,
                    "validation_profile_id": invocation.validation_profile_id,
                    "command_profile_id": invocation.command_profile_id,
                    "skill_id": invocation.skill_id,
                    "skill_execution_id": invocation.skill_execution_id,
                    "sandbox_task_id": invocation.sandbox_task_id,
                    "sandbox_workspace_id": invocation.sandbox_workspace_id,
                    "relative_path": invocation.relative_path,
                    "cwd_inside_sandbox": invocation.cwd_inside_sandbox,
                    "operation_scope": invocation.operation_scope,
                    **payload,
                }),
                tool_invocation_id=invocation.tool_invocation_id,
                delegation_id=invocation.delegation_id,
                visible_in_timeline=visible,
                artifact_ids=artifact_ids or [],
                evidence_refs=[
                    f"tool:{invocation.tool_invocation_id}",
                    *([f"delegation:{invocation.delegation_id}"] if invocation.delegation_id else []),
                    *([f"project:{invocation.project_profile_id}"] if invocation.project_profile_id else []),
                    *([f"skill:{invocation.skill_id}"] if invocation.skill_id else []),
                    *([f"skill_execution:{invocation.skill_execution_id}"] if invocation.skill_execution_id else []),
                    *([f"sandbox_task:{invocation.sandbox_task_id}"] if invocation.sandbox_task_id else []),
                    *([f"sandbox_workspace:{invocation.sandbox_workspace_id}"] if invocation.sandbox_workspace_id else []),
                ],
            ),
        )
        return event.event_id

    def _summary(self, value: Any) -> str:
        text = str(redact_payload(value))
        return text[:1000] + ("..." if len(text) > 1000 else "")

    def _safe_filename(self, filename: str) -> str:
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in Path(filename).name).strip("._")
        return safe or "artifact.txt"
