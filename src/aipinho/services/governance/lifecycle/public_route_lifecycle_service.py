from __future__ import annotations

import re
from typing import Any

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.governance.lifecycle import GovernanceLifecycleState
from aipinho.services.governance.lifecycle.governance_lifecycle_service import GovernanceLifecycleService
from aipinho.services.semantic_runtime.semantic_ingress_doctor_service import SemanticIngressDoctorService


class PublicRouteLifecycleService:
    """Applies the canonical lifecycle snapshot to public route responses.

    Public routes keep their existing response shapes, but the operational truth
    attached to those responses comes from GovernanceLifecycleService.
    """

    SUCCESS_CLAIM_PATTERN = re.compile(
        r"(?is)\b(conclui|concluido|criei|criado|escrevi|modifiquei|apliquei|executei|validado|validation:\s*passed|validacao:\s*passed)\b"
    )
    WRITE_OPERATIONS = {
        "governed_file_write",
        "filesystem_write_file",
        "filesystem_create_directory",
        "filesystem_append_file",
        "workspace_artifact_write_request",
        "sandbox_batch_artifact_request",
        "project_generation",
        "project_bootstrap",
        "governed_project_rebuild",
        "android_project_create",
        "android_apk_build",
        "patch_request",
        "patch_preview",
        "patch_apply",
        "governed_shell_request",
        "shell_command",
        "run_command",
        "artifact_request",
        "readonly_analysis_with_artifact_output",
    }

    def __init__(self, lifecycle: GovernanceLifecycleService | None = None) -> None:
        self.lifecycle = lifecycle or GovernanceLifecycleService()
        self.semantic_ingress_doctor = SemanticIngressDoctorService()

    def finalize_chat_response(
        self,
        response: ChatResponse,
        *,
        prompt: str,
        source_channel: str,
        workspace_path: str | None = None,
    ) -> ChatResponse:
        operation_type = self._operation_type(response)
        actions = self._actions(response, operation_type)
        policy_decisions = self._policy_decisions(response)
        executable_plan_ref = self._executable_plan_ref(response)
        expected_outputs = self._expected_outputs(response, operation_type, actions)
        outputs = self._outputs(response, expected_outputs)
        proposed_status = self._proposed_completion_status(response)
        snapshot = self.lifecycle.evaluate(
            user_text=prompt,
            source_channel=source_channel,
            session_id=response.session_id,
            requested_actions=actions,
            operation_type=operation_type,
            contract_type=self._contract_type(response, operation_type),
            runtime_profile=self._runtime_profile(response, operation_type),
            target_paths=self._target_paths(response),
            workspace_path=workspace_path or self._workspace_path(response),
            explicit_policy_decisions=policy_decisions,
            executable_plan_ref=executable_plan_ref,
            expected_outputs=expected_outputs,
            source_message_id=self._contract_value(response, "source_message_id"),
            context_ref=self._contract_value(response, "context_ref"),
            discovery_ref=self._contract_value(response, "discovery_ref"),
            analysis_ref=self._contract_value(response, "analysis_ref"),
            validation_plan=self._contract_payload(response, "validation_plan"),
            rollback_plan=self._contract_payload(response, "rollback_plan"),
            plan_payload=self._plan_payload(response),
            outputs=outputs,
            proposed_completion_status=proposed_status,
        )
        lifecycle_payload = snapshot.model_dump()
        lifecycle_payload["semantic_ingress_doctor"] = self.semantic_ingress_doctor.analyze(
            prompt,
            source_channel=source_channel,
            actual_intent=lifecycle_payload.get("intent") if isinstance(lifecycle_payload.get("intent"), dict) else None,
            actual_operation_contract=(
                lifecycle_payload.get("operation_contract")
                if isinstance(lifecycle_payload.get("operation_contract"), dict)
                else None
            ),
        ).model_dump(mode="json")
        lifecycle_payload["pre_task_bootstrap"] = self._pre_task_bootstrap_trace(
            prompt=prompt,
            source_channel=source_channel,
            response=response,
            lifecycle_payload=lifecycle_payload,
        )
        policy = dict(response.policy)
        policy["canonical_lifecycle"] = {
            "lifecycle_id": snapshot.lifecycle_id,
            "state": snapshot.state.value,
            "reason_code": snapshot.reason_code.value,
            "permission": snapshot.policy.permission.value,
            "approval_gate_status": snapshot.approval_gate.status,
            "completion_status": snapshot.completion.status,
            "safe_to_report_success": snapshot.completion.safe_to_report_success,
            "speaker_can_claim_success": snapshot.speaker_truth.can_claim_success,
        }
        warnings = list(response.warnings)
        for disclosure in snapshot.speaker_truth.required_disclosures:
            marker = f"canonical_lifecycle:{disclosure}"
            if marker not in warnings:
                warnings.append(marker)

        updates: dict[str, Any] = {
            "policy": policy,
            "warnings": warnings,
            "governance_lifecycle": lifecycle_payload,
        }
        corrected_status = self._corrected_status(response, snapshot)
        if corrected_status != response.status:
            updates["status"] = corrected_status
            if corrected_status in {"degraded", "blocked"} and response.message_type == "assistant_final_answer":
                updates["message_type"] = "assistant_degraded_answer"
        if corrected_status in {"degraded", "blocked"} and self._has_unsupported_success_claim(response, snapshot):
            updates["message"] = (
                "Nao vou declarar sucesso operacional sem evidencias completas no lifecycle canonico. "
                f"Estado canonico: {snapshot.state.value}; motivo: {snapshot.reason_code.value}. "
                f"Mensagem original sanitizada: {response.message}"
            )
            updates["is_final_answer"] = False
            updates["grounded"] = False
            updates["grounding_required"] = True
            updates["grounding_missing_reason"] = "canonical_lifecycle_missing_required_outputs"
        return response.model_copy(update=updates)

    def _pre_task_bootstrap_trace(
        self,
        *,
        prompt: str,
        source_channel: str,
        response: ChatResponse,
        lifecycle_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Read-only bootstrap trace derived from canonical lifecycle outputs."""

        operation_contract = lifecycle_payload.get("operation_contract")
        intent = lifecycle_payload.get("intent")
        requires_task = self._requires_task(response, lifecycle_payload)
        task_run_id = response.result_ref_id if str(response.result_ref_id or "").startswith("task_run_") else None
        stages: list[dict[str, Any]] = []

        def add(stage: str, ok: bool, *, reason: str, data: dict[str, Any] | None = None, skipped: bool = False) -> None:
            stages.append(
                {
                    "stage": stage,
                    "status": "skipped" if skipped else "complete" if ok else "blocked",
                    "reason": reason,
                    "data": data or {},
                }
            )

        has_prompt = bool(str(prompt or "").strip())
        add("ChatIngressReceived", has_prompt, reason="prompt_received" if has_prompt else "prompt_missing", data={"source_channel": source_channel})
        add("PromptNormalized", has_prompt, reason="prompt_normalized" if has_prompt else "prompt_not_normalized")
        add("PreviewStarted", True, reason="canonical_lifecycle_preview_started", data={"mode": response.status})
        add("IntentResolutionStarted", True, reason="canonical_intent_resolution_started")
        add("IntentResolutionFinished", isinstance(intent, dict) and bool(intent), reason="canonical_intent_resolved" if intent else "intent_missing")
        add(
            "OperationContractSelected",
            isinstance(operation_contract, dict) and bool(operation_contract),
            reason="operation_contract_selected" if operation_contract else "operation_contract_missing",
            data={"operation_type": response.operation_type},
        )
        add(
            "TaskBootstrapStarted",
            requires_task,
            reason="task_bootstrap_required" if requires_task else "task_not_required_by_contract",
            skipped=not requires_task,
        )
        add(
            "TaskBootstrapFinished",
            bool(response.task_id) if requires_task else False,
            reason="task_bootstrap_finished" if response.task_id else "task_bootstrap_not_completed",
            data={"task_id": response.task_id},
            skipped=not requires_task,
        )
        add(
            "TaskCreated",
            bool(response.task_id) if requires_task else False,
            reason="task_created" if response.task_id else "task_missing",
            data={"task_id": response.task_id},
            skipped=not requires_task,
        )
        add(
            "TaskRunCreated",
            bool(task_run_id) if requires_task else False,
            reason="task_run_created" if task_run_id else "task_run_missing",
            data={"task_run_id": task_run_id},
            skipped=not requires_task,
        )
        required = [item for item in stages if item["status"] != "skipped"]
        return {
            "status": "complete" if all(item["status"] == "complete" for item in required) else "blocked",
            "requires_task": requires_task,
            "task_id": response.task_id,
            "task_run_id": task_run_id,
            "stages": stages,
        }

    def _requires_task(self, response: ChatResponse, lifecycle_payload: dict[str, Any]) -> bool:
        if response.task_id or str(response.result_ref_id or "").startswith("task_run_"):
            return True
        if isinstance(response.intent, dict) and response.intent.get("requires_task") is True:
            return True
        operation_contract = lifecycle_payload.get("operation_contract")
        if isinstance(operation_contract, dict):
            if operation_contract.get("requires_task") is True:
                return True
            expected_outputs = operation_contract.get("expected_outputs")
            if isinstance(expected_outputs, list) and expected_outputs:
                return True
        return False

    def _operation_type(self, response: ChatResponse) -> str:
        if response.operation_type:
            return str(response.operation_type)
        intent_type = response.intent.get("intent_type") if isinstance(response.intent, dict) else None
        return str(intent_type or "conversation")

    def _contract_type(self, response: ChatResponse, operation_type: str) -> str:
        contract_type = response.contract_preview.get("contract_type") if isinstance(response.contract_preview, dict) else None
        if contract_type:
            return str(contract_type)
        if operation_type in {"patch_request", "patch_preview", "patch_apply", "governed_project_rebuild"}:
            return "patch_request"
        if operation_type in {"project_generation", "project_bootstrap", "android_project_create", "android_apk_build"}:
            return "project_generation"
        if self._actions(response, operation_type):
            return "filesystem_write"
        return operation_type

    def _runtime_profile(self, response: ChatResponse, operation_type: str) -> str:
        runtime_profile = response.contract_preview.get("runtime_profile") if isinstance(response.contract_preview, dict) else None
        if runtime_profile:
            return str(runtime_profile)
        if operation_type in {"project_generation", "project_bootstrap", "android_project_create", "android_apk_build"}:
            return "project_generation"
        if operation_type in {"patch_request", "patch_preview", "patch_apply", "governed_project_rebuild"}:
            return "patch"
        if operation_type in {"governed_shell_request", "shell_command", "run_command"}:
            return "shell_build_test"
        if self._actions(response, operation_type):
            return "write_file"
        return operation_type

    def _actions(self, response: ChatResponse, operation_type: str) -> list[str]:
        actions: list[str] = []
        for item in response.actions:
            if str(item).strip():
                actions.append(str(item))
        approval_for = response.policy.get("approval_required_for") if isinstance(response.policy, dict) else None
        if isinstance(approval_for, list):
            actions.extend(str(item) for item in approval_for if str(item).strip())
        contract = response.contract_preview.get("operation_contract") if isinstance(response.contract_preview, dict) else None
        if isinstance(contract, dict):
            for key in ("normalized_actions", "requested_actions"):
                values = contract.get(key)
                if isinstance(values, list):
                    actions.extend(str(item) for item in values if str(item).strip())
        if (
            not actions
            and (response.artifact_links or response.artifact_id)
            and response.intent.get("requires_task") is False
            and response.policy.get("workspace_write") is False
        ):
            return []
        if not actions:
            if operation_type in {"governed_shell_request", "shell_command", "run_command"}:
                actions.append("run_command")
            elif operation_type in {"patch_request", "patch_preview", "patch_apply", "governed_project_rebuild"}:
                actions.append("apply_patch")
            elif operation_type in {"project_generation", "project_bootstrap", "android_project_create", "android_apk_build"}:
                actions.append("write_files")
            elif operation_type in {"filesystem_create_directory"}:
                actions.append("create_directory")
            elif operation_type in self.WRITE_OPERATIONS:
                actions.append("write_files")
        return list(dict.fromkeys(actions))

    def _policy_decisions(self, response: ChatResponse) -> list[str]:
        if response.status == "blocked":
            return ["denied"]
        if response.status == "needs_clarification":
            return ["needs_clarification"]
        if response.status == "pending_approval" or response.approval_id:
            return ["ask"]
        approval_for = response.policy.get("approval_required_for") if isinstance(response.policy, dict) else None
        if isinstance(approval_for, list) and approval_for:
            return ["ask"]
        if response.status in {"ok", "ready"}:
            return ["allowed"]
        if response.status in {"error", "failed"}:
            return ["denied"]
        return []

    def _executable_plan_ref(self, response: ChatResponse) -> str | None:
        for key in ("executable_plan_ref", "plan_id", "patch_plan_id"):
            value = response.contract_preview.get(key) if isinstance(response.contract_preview, dict) else None
            if value:
                return str(value)
        if response.preview_id and response.status in {"pending_approval", "preview"} and response.approval_id:
            return str(response.preview_id)
        return None

    def _expected_outputs(self, response: ChatResponse, operation_type: str, actions: list[str]) -> list[str]:
        value = response.contract_preview.get("expected_outputs") if isinstance(response.contract_preview, dict) else None
        if isinstance(value, list) and value:
            return [str(item) for item in value if str(item).strip()]
        if response.artifact_links or response.artifact_id:
            return ["artifact_result", "validation_result"]
        if operation_type in {"patch_request", "patch_preview", "patch_apply", "governed_project_rebuild"}:
            return ["patch_result", "validation_result"]
        if operation_type in {"project_generation", "project_bootstrap", "android_project_create", "android_apk_build"}:
            return ["project_generation_result", "validation_result"]
        if operation_type in {"governed_shell_request", "shell_command", "run_command"} or "run_command" in actions:
            return ["command_result", "validation_result"]
        if any(action in {"write_files", "write_file", "create_file", "create_directory", "modify_file"} for action in actions):
            return ["filesystem_operation", "validation_result"]
        return []

    def _outputs(self, response: ChatResponse, expected_outputs: list[str]) -> dict[str, Any]:
        outputs: dict[str, Any] = {}
        if isinstance(response.contract_preview, dict):
            for output_id in expected_outputs:
                if output_id in response.contract_preview and response.contract_preview.get(output_id) is not None:
                    outputs[output_id] = response.contract_preview.get(output_id)
                elif output_id.startswith("artifact_semantic_profile:"):
                    validation = response.contract_preview.get("validation_result")
                    profile = self._semantic_profile_output(validation, output_id.removeprefix("artifact_semantic_profile:"))
                    if profile is not None:
                        outputs[output_id] = profile
        if response.artifact_links or response.artifact_id:
            outputs["artifact_result"] = {
                "artifact_id": response.artifact_id,
                "artifact_links": [item.model_dump() for item in response.artifact_links],
            }
            logical_paths = set()
            if isinstance(response.contract_preview, dict):
                logical_paths = {
                    str(item)
                    for item in response.contract_preview.get("logical_artifact_paths", []) or []
                    if str(item).strip()
                }
            for link in response.artifact_links:
                logical_path = str(link.label or "")
                if logical_path in logical_paths:
                    outputs[f"artifact:{logical_path}"] = {
                        "artifact_id": link.artifact_id,
                        "download_endpoint": link.download_endpoint,
                    }
        validation_status = response.policy.get("validation_status") or response.evaluation_status
        if validation_status in {"passed", "passed_with_warnings"}:
            outputs["validation_result"] = {"status": validation_status}
        if response.task_id and response.status in {"ok", "ready"}:
            if "filesystem_operation" in expected_outputs:
                outputs["filesystem_operation"] = {"task_id": response.task_id, "status": response.status}
            if "project_generation_result" in expected_outputs:
                outputs["project_generation_result"] = {"task_id": response.task_id, "status": response.status}
            if "command_result" in expected_outputs:
                outputs["command_result"] = {"task_id": response.task_id, "status": response.status}
        if response.status in {"ok", "ready"} and not expected_outputs:
            outputs["chat_result"] = {"status": response.status}
        return outputs

    def _semantic_profile_output(self, validation: Any, logical_path: str) -> dict[str, Any] | None:
        if not isinstance(validation, dict):
            return None
        for item in validation.get("artifact_semantic_validations") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("logical_path") or "") != logical_path:
                continue
            profile = item.get("profile") if isinstance(item.get("profile"), dict) else {}
            if item.get("status") == "passed" and profile.get("semantic_status") == "passed":
                return {
                    "logical_path": logical_path,
                    "status": item.get("status"),
                    "profile_id": profile.get("profile_id"),
                    "completeness_score": profile.get("completeness_score"),
                }
        return None

    def _target_paths(self, response: ChatResponse) -> list[str]:
        paths: list[str] = []
        for key in ("target_paths", "files", "paths"):
            value = response.contract_preview.get(key) if isinstance(response.contract_preview, dict) else None
            if isinstance(value, list):
                paths.extend(str(item) for item in value if str(item).strip())
        return list(dict.fromkeys(paths))

    def _contract_value(self, response: ChatResponse, key: str) -> str | None:
        value = response.contract_preview.get(key) if isinstance(response.contract_preview, dict) else None
        return str(value) if value else None

    def _contract_payload(self, response: ChatResponse, key: str) -> Any | None:
        return response.contract_preview.get(key) if isinstance(response.contract_preview, dict) else None

    def _plan_payload(self, response: ChatResponse) -> dict[str, Any]:
        if not isinstance(response.contract_preview, dict):
            return {}
        return {
            key: response.contract_preview.get(key)
            for key in ("project_generation_plan", "patch_plan", "concrete_file_operations", "validation_plan", "rollback_plan")
            if response.contract_preview.get(key)
        }

    def _workspace_path(self, response: ChatResponse) -> str | None:
        for container in (response.intent, response.policy, response.contract_preview):
            if isinstance(container, dict):
                for key in ("workspace", "workspace_path", "target_workspace", "source_workspace"):
                    value = container.get(key)
                    if isinstance(value, str) and value.strip():
                        return value
        return None

    def _proposed_completion_status(self, response: ChatResponse) -> str:
        if response.status in {"ok", "ready"}:
            return "completed"
        if response.status == "accepted_running":
            return "not_run"
        if response.status == "timeout_blocked":
            return "blocked"
        if response.status in {"blocked", "failed", "error"}:
            return "blocked"
        if response.status == "degraded":
            return "completed_with_warnings"
        return "not_run"

    def _corrected_status(self, response: ChatResponse, snapshot) -> str:
        if response.status in {"pending_approval", "preview", "needs_clarification", "accepted_running", "timeout_blocked", "blocked", "error", "failed"}:
            return response.status
        if not self._is_operational_response(response):
            return response.status
        if snapshot.state == GovernanceLifecycleState.BLOCKED:
            return "blocked"
        if snapshot.completion.missing_outputs and self._has_unsupported_success_claim(response, snapshot):
            return "degraded"
        return response.status

    def _is_operational_response(self, response: ChatResponse) -> bool:
        operation_type = self._operation_type(response)
        return bool(response.task_id or response.preview_id or response.approval_id or response.artifact_id or response.artifact_links or operation_type in self.WRITE_OPERATIONS)

    def _has_unsupported_success_claim(self, response: ChatResponse, snapshot) -> bool:
        if snapshot.speaker_truth.can_claim_success:
            return False
        return bool(self.SUCCESS_CLAIM_PATTERN.search(response.message or ""))
