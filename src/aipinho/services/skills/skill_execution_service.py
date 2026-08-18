from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentEventCreateRequest, AgentRunCreateRequest, AgentRunUpdateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest, ToolInvocationResult
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.skills.contracts import SkillExecutionRequest, SkillExecutionResult, SkillManifest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.events.event_core import redact_payload
from aipinho.services.skills.skill_manifest_registry_service import SKILL_STATUS_ACTIVE, SkillManifestRegistryService


class SkillExecutionService:
    """Governed execution adapter for internal skills.

    This service intentionally delegates every effect to the shared Tool Gateway.
    Skills define *what* is allowed; Tool Gateway/Policy decides whether it runs.
    """

    def __init__(
        self,
        *,
        registry: SkillManifestRegistryService | None = None,
        kernel: AgentSessionKernelService | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
        executions_root: Path | None = None,
    ) -> None:
        self.registry = registry or SkillManifestRegistryService()
        self.kernel = kernel or AgentSessionKernelService()
        self.tool_gateway = tool_gateway or AgentToolGatewayService(kernel=self.kernel)
        self.executions_root = executions_root or PATHS.project_root / "data" / "runtime" / "skills" / "executions"
        self.executions_root.mkdir(parents=True, exist_ok=True)

    def execute(self, request: SkillExecutionRequest) -> SkillExecutionResult:
        try:
            manifest = self.registry.get(request.skill_id)
        except KeyError:
            result = self._blocked(request, ["skill_not_found"])
            self._save(result)
            return result

        result = SkillExecutionResult(
            skill_execution_id=request.skill_execution_id,
            skill_id=manifest.skill_id,
            skill_version=manifest.version,
            status="running",
            metadata_sanitized=redact_payload(
                {
                    "requesting_agent_id": request.requesting_agent_id,
                    "session_id": request.session_id,
                    "project_profile_id": request.project_profile_id,
                    "workspace_profile_id": request.workspace_profile_id,
                    "sandbox_workspace_id": request.sandbox_workspace_id,
                    "sandbox_task_id": request.sandbox_task_id,
                    "execution_mode": request.execution_mode,
                }
            ),
        )
        self._save(result)

        validation = self.registry.validate_manifest(manifest)
        if not validation.valid:
            return self._finish_blocked(request, manifest, result, validation.reason_codes or ["skill_manifest_invalid"])
        if manifest.status not in SKILL_STATUS_ACTIVE:
            return self._finish_blocked(request, manifest, result, [f"skill_status_{manifest.status}_not_executable"])
        capability_block = self._capability_block(manifest, request)
        if capability_block:
            return self._finish_blocked(request, manifest, result, capability_block)

        run = self._run_for_request(request, manifest)
        self._event(run.run_id, "skill_execution_started", "Skill governada iniciada.", request, manifest)
        if manifest.status == "deprecated":
            self._event(run.run_id, "skill_deprecated_warning", "Skill marcada como deprecated; execucao continua com aviso.", request, manifest, severity="warning")
            result.warnings.append("deprecated_skill_warning")
        if manifest.status == "experimental":
            self._event(run.run_id, "skill_experimental_warning", "Skill experimental; resultado deve ser revisado.", request, manifest, severity="warning")
            result.warnings.append("experimental_skill_warning")

        tool_results: list[ToolInvocationResult] = []
        for tool_name, payload in self._planned_tool_calls(manifest, request):
            if tool_name not in manifest.allowed_tools:
                self._event(run.run_id, "skill_tool_denied_by_manifest", "Ferramenta nao permitida pelo manifest.", request, manifest, {"tool_name": tool_name}, severity="warning")
                continue
            tool_result = self.tool_gateway.invoke(
                request.requesting_agent_id,
                run.run_id,
                tool_name,
                ToolInvocationCreateRequest(
                    operation_type=f"skill:{manifest.skill_id}:{tool_name}",
                    workspace_id=str(request.inputs.get("workspace_id") or request.workspace_profile_id or "") or None,
                    project_profile_id=request.project_profile_id,
                    workspace_profile_id=request.workspace_profile_id,
                    sandbox_workspace_id=request.sandbox_workspace_id,
                    sandbox_task_id=request.sandbox_task_id,
                    relative_path=str(payload.get("relative_path")) if payload.get("relative_path") else None,
                    cwd_inside_sandbox=str(payload.get("cwd_relative")) if payload.get("cwd_relative") else None,
                    operation_scope="sandbox" if request.sandbox_workspace_id else None,
                    validation_profile_id=str(request.inputs.get("validation_profile_id") or "") or None,
                    skill_id=manifest.skill_id,
                    skill_execution_id=request.skill_execution_id,
                    requesting_agent_id=request.requesting_agent_id,
                    input=payload,
                    metadata_sanitized={
                        "skill_id": manifest.skill_id,
                        "skill_execution_id": request.skill_execution_id,
                        "skill_pack_id": request.metadata_sanitized.get("skill_pack_id"),
                        "skill_pack_execution_id": request.metadata_sanitized.get("skill_pack_execution_id"),
                        "execution_mode": request.execution_mode,
                        "sandbox_workspace_id": request.sandbox_workspace_id,
                        "sandbox_task_id": request.sandbox_task_id,
                    },
                ),
            )
            tool_results.append(tool_result)
            result.tool_invocation_ids.append(tool_result.tool_invocation.tool_invocation_id)
            if tool_result.policy_decision:
                result.policy_decision_ids.append(tool_result.policy_decision.policy_decision_id)
            if tool_result.validation_result:
                result.validation_ids.append(tool_result.validation_result.validation_id)
            for artifact in tool_result.artifacts:
                result.output_artifact_refs.append(artifact.artifact_id)
                result.report_refs.append(artifact.artifact_id)
            result.evidence_refs.extend(tool_result.tool_invocation.evidence_refs)
            if tool_result.status in {"blocked", "approval_required", "failed"}:
                result.status = "pending_approval" if tool_result.status == "approval_required" else "blocked" if tool_result.status == "blocked" else "failed"
                reason = tool_result.tool_invocation.block_reason_code or tool_result.tool_invocation.error_code or tool_result.status
                result.blocked_reasons.append(str(reason))
                result.completed_at = utc_now_iso()
                self._save(result)
                self._event(run.run_id, "skill_execution_blocked", "Skill interrompida por policy/gate da ferramenta.", request, manifest, {"reason_code": reason}, severity="warning")
                self.kernel.update_run(run.run_id, AgentRunUpdateRequest(status=result.status, error_code=str(reason), metadata_sanitized={"skill_execution_id": result.skill_execution_id}))
                return result

        result = self._complete_result(result, manifest, tool_results)
        self._save(result)
        self._event(
            run.run_id,
            "skill_execution_completed",
            "Skill governada concluida.",
            request,
            manifest,
            {"artifact_ids": result.output_artifact_refs, "validation_ids": result.validation_ids},
            artifact_ids=result.output_artifact_refs,
        )
        final_message = self.kernel.add_message(
            request.requesting_agent_id,
            request.session_id,
            request=self._assistant_message_request(result, manifest),
        )
        self.kernel.update_run(
            run.run_id,
            AgentRunUpdateRequest(
                status=result.status,
                validation_status="passed" if result.validation_ids and result.status == "completed" else None,
                artifact_ids=result.output_artifact_refs,
                memory_candidates_created=result.memory_candidate_ids,
                final_message_id=final_message.message_id,
                metadata_sanitized={"skill_execution_id": result.skill_execution_id},
            ),
        )
        return result

    def get(self, skill_execution_id: str) -> SkillExecutionResult | None:
        path = self.executions_root / f"{skill_execution_id}.json"
        if not path.exists():
            return None
        return SkillExecutionResult(**json.loads(path.read_text(encoding="utf-8")))

    def trace(self, skill_execution_id: str) -> dict[str, Any] | None:
        result = self.get(skill_execution_id)
        if result is None:
            return None
        return {
            "status": "ok",
            "skill_execution": result.model_dump(),
            "raw_default_visible": False,
            "evidence_refs": result.evidence_refs,
        }

    def _run_for_request(self, request: SkillExecutionRequest, manifest: SkillManifest):
        if request.run_id:
            existing = self.kernel.get_run(request.run_id)
            if existing is None:
                raise FileNotFoundError(request.run_id)
            return existing
        return self.kernel.create_run(
            request.requesting_agent_id,
            request.session_id,
            AgentRunCreateRequest(
                operation_type=f"skill_execution:{manifest.skill_id}",
                status="running",
                workspace_id=str(request.inputs.get("workspace_id") or "") or None,
                project_profile_id=request.project_profile_id,
                workspace_profile_id=request.workspace_profile_id,
                capabilities_requested=request.requested_capabilities,
                metadata_sanitized={
                    "skill_id": manifest.skill_id,
                    "skill_version": manifest.version,
                    "skill_execution_id": request.skill_execution_id,
                    "category": manifest.category,
                },
            ),
        )

    def _planned_tool_calls(self, manifest: SkillManifest, request: SkillExecutionRequest) -> list[tuple[str, dict[str, Any]]]:
        title = str(request.inputs.get("title") or manifest.display_name)
        summary = str(request.inputs.get("summary") or request.user_goal or manifest.description)
        content = str(request.inputs.get("content") or self._default_report_content(manifest, request, summary))
        if manifest.sandbox_required and not request.sandbox_workspace_id:
            return []
        if manifest.skill_id == "internal.sandbox_file_writer":
            return [(
                "sandbox_write_file",
                {
                    "relative_path": str(request.inputs.get("relative_path") or "output.txt"),
                    "content": content,
                    "overwrite": bool(request.inputs.get("overwrite", False)),
                },
            )]
        if manifest.skill_id == "internal.sandbox_project_generator":
            calls: list[tuple[str, dict[str, Any]]] = []
            for item in request.inputs.get("directories", []):
                calls.append(("sandbox_mkdir", {"relative_path": str(item)}))
            for item in request.inputs.get("files", []):
                if isinstance(item, dict):
                    calls.append(("sandbox_write_file", {
                        "relative_path": str(item.get("relative_path") or "output.txt"),
                        "content": str(item.get("content") or ""),
                        "overwrite": bool(item.get("overwrite", True)),
                    }))
            return calls
        if manifest.skill_id == "internal.sandbox_shell_runner":
            return [(
                "sandbox_run_shell",
                {
                    "command": str(request.inputs.get("command") or ""),
                    "cwd_relative": str(request.inputs.get("cwd_relative") or "."),
                    "category": request.inputs.get("category"),
                    "timeout_seconds": int(request.inputs.get("timeout_seconds", 120)),
                },
            )]
        if manifest.skill_id == "internal.sandbox_artifact_exporter":
            return [(
                "sandbox_zip_export",
                {
                    "filename": str(request.inputs.get("filename") or "sandbox_artifact.zip"),
                    "include_paths": request.inputs.get("include_paths") or ["."],
                    "exclude_globs": request.inputs.get("exclude_globs") or [],
                },
            )]
        if manifest.skill_id == "internal.sandbox_validation_runner":
            return [(
                "sandbox_validate",
                {
                    "relative_paths": request.inputs.get("relative_paths") or [],
                    "artifact_ids": request.inputs.get("artifact_ids") or [],
                },
            )]
        if manifest.skill_id == "internal.project_readonly_inventory":
            calls: list[tuple[str, dict[str, Any]]] = []
            if request.inputs.get("workspace_id") or request.workspace_profile_id:
                calls.append(("list_dir", {"max_depth": int(request.inputs.get("max_depth", 2)), "include_hidden": False}))
            calls.append(("generate_report", {"filename": str(request.inputs.get("filename") or "project_inventory.md"), "content": content, "content_type": "text/markdown"}))
            return calls
        if manifest.skill_id == "internal.validation_runner":
            return [
                ("validate", {"name": str(request.inputs.get("name") or "skill_validation"), "status": str(request.inputs.get("status") or "passed")}),
                ("generate_report", {"filename": str(request.inputs.get("filename") or "validation_report.md"), "content": content, "content_type": "text/markdown"}),
            ]
        if manifest.skill_id == "internal.mobile_ux_static_audit":
            calls = []
            if request.inputs.get("workspace_id") or request.workspace_profile_id:
                calls.append(("list_dir", {"max_depth": int(request.inputs.get("max_depth", 2)), "include_hidden": False}))
            if request.inputs.get("query"):
                calls.append(("search_files", {"query": str(request.inputs.get("query")), "max_results": int(request.inputs.get("max_results", 20))}))
            calls.append(("generate_report", {"filename": str(request.inputs.get("filename") or "mobile_ux_audit.md"), "content": content, "content_type": "text/markdown"}))
            return calls
        if manifest.skill_id == "internal.artifact_bundle_exporter":
            return [
                ("create_artifact", {"filename": str(request.inputs.get("filename") or "artifact_bundle_manifest.json"), "content": json.dumps({"artifact_ids": request.inputs.get("artifact_ids", [])}, ensure_ascii=False, indent=2), "content_type": "application/json"})
            ]
        return [("generate_report", {"filename": str(request.inputs.get("filename") or "skill_report.md"), "content": content, "content_type": "text/markdown"})]

    def _default_report_content(self, manifest: SkillManifest, request: SkillExecutionRequest, summary: str) -> str:
        return "\n".join(
            [
                f"# {manifest.display_name}",
                "",
                f"Skill: `{manifest.skill_id}`",
                f"Agent: `{request.requesting_agent_id}`",
                "",
                "## Resumo",
                summary,
                "",
                "## Evidencias",
                "A execucao foi registrada pelo Skill Execution Service e pelas invocacoes governadas do Tool Gateway.",
            ]
        )

    def _capability_block(self, manifest: SkillManifest, request: SkillExecutionRequest) -> list[str]:
        granted = set(request.requested_capabilities)
        missing = [capability for capability in manifest.required_capabilities if capability not in granted]
        reasons = [f"missing_capability:{item}" for item in missing]
        if manifest.sandbox_required and not request.sandbox_workspace_id:
            reasons.append("sandbox_workspace_required")
        return reasons

    def _complete_result(self, result: SkillExecutionResult, manifest: SkillManifest, tool_results: list[ToolInvocationResult]) -> SkillExecutionResult:
        result.status = "completed"
        if manifest.validation_policy.get("required") and not result.validation_ids:
            result.status = "validation_failed"
            result.errors.append("validation_required_but_missing")
        if manifest.side_effects and not result.evidence_refs:
            result.status = "completed_with_warnings"
            result.warnings.append("side_effect_without_evidence_refs")
        result.completed_at = utc_now_iso()
        result.real_execution_performed = bool(tool_results)
        result.output = {
            "summary": "Skill executada por Tool Gateway governado.",
            "artifact_ids": result.output_artifact_refs,
            "validation_ids": result.validation_ids,
        }
        result.evidence_refs = sorted(set(result.evidence_refs + [f"skill_execution:{result.skill_execution_id}"]))
        return result

    def _assistant_message_request(self, result: SkillExecutionResult, manifest: SkillManifest):
        from aipinho.schemas.agents.contracts import AgentMessageCreateRequest

        artifacts = ", ".join(result.output_artifact_refs) if result.output_artifact_refs else "sem artifacts"
        return AgentMessageCreateRequest(
            role="assistant",
            message_kind="final_answer",
            content_sanitized=f"Skill {manifest.display_name} concluida com status {result.status}. Artifacts: {artifacts}.",
            run_id=None,
            artifact_ids=result.output_artifact_refs,
            metadata_sanitized={"skill_execution_id": result.skill_execution_id, "skill_id": manifest.skill_id},
        )

    def _finish_blocked(self, request: SkillExecutionRequest, manifest: SkillManifest, result: SkillExecutionResult, reasons: list[str]) -> SkillExecutionResult:
        result.status = "blocked"
        result.blocked_reasons = list(dict.fromkeys(reasons))
        result.completed_at = utc_now_iso()
        result.metadata_sanitized["skill_id"] = manifest.skill_id
        self._save(result)
        return result

    def _blocked(self, request: SkillExecutionRequest, reasons: list[str]) -> SkillExecutionResult:
        return SkillExecutionResult(
            skill_execution_id=request.skill_execution_id,
            skill_id=request.skill_id,
            status="blocked",
            completed_at=utc_now_iso(),
            blocked_reasons=list(dict.fromkeys(reasons)),
            metadata_sanitized={"requesting_agent_id": request.requesting_agent_id, "session_id": request.session_id},
        )

    def _event(
        self,
        run_id: str,
        event_type: str,
        human_message: str,
        request: SkillExecutionRequest,
        manifest: SkillManifest,
        payload: dict[str, Any] | None = None,
        *,
        severity: str = "info",
        artifact_ids: list[str] | None = None,
    ) -> None:
        self.kernel.add_event(
            run_id,
            AgentEventCreateRequest(
                event_type=event_type,
                status="running" if event_type.endswith("started") else "completed" if event_type.endswith("completed") else "received",
                severity=severity,
                human_message=human_message,
                technical_summary_sanitized=event_type,
                payload_sanitized=redact_payload(
                    {
                        "skill_id": manifest.skill_id,
                        "skill_version": manifest.version,
                        "skill_execution_id": request.skill_execution_id,
                        **(payload or {}),
                    }
                ),
                evidence_refs=[f"skill:{manifest.skill_id}", f"skill_execution:{request.skill_execution_id}"],
                artifact_ids=artifact_ids or [],
            ),
        )

    def _save(self, result: SkillExecutionResult) -> None:
        path = self.executions_root / f"{result.skill_execution_id}.json"
        path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
