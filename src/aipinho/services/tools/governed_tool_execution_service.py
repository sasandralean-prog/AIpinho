from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.session.session_store import utc_now
from aipinho.services.tools.execution_audit_service import ExecutionAuditService
from aipinho.services.tools.shell_command_policy_service import ShellCommandPolicyService
from aipinho.services.tools.tool_registry_service import ToolRegistryService
from aipinho.services.tools.write_capability_envelope_service import WriteCapabilityEnvelopeService
from aipinho.utils.yaml_loader import load_yaml_file


class GovernedToolExecutionService:
    def __init__(
        self,
        registry: ToolRegistryService | None = None,
        approvals: ApprovalService | None = None,
        audit: ExecutionAuditService | None = None,
        policy_path: Path | None = None,
        runner=subprocess.run,
        opener=urlopen,
        shell_policy: ShellCommandPolicyService | None = None,
        write_envelopes: WriteCapabilityEnvelopeService | None = None,
    ) -> None:
        self.registry = registry or ToolRegistryService().load()
        self.approvals = approvals or ApprovalService()
        self.audit = audit or ExecutionAuditService()
        self.policy_path = policy_path or PATHS.config_root / "policies" / "governed_tool_execution_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, critical=True, root=self.policy_path.parent)
        self.runner = runner
        self.opener = opener
        self.shell_policy = shell_policy or ShellCommandPolicyService(policy_path=self.policy_path)
        self.write_envelopes = write_envelopes or WriteCapabilityEnvelopeService()

    def request_approval(self, request: ToolExecutionRequest) -> dict[str, object]:
        decision = self._decision(request)
        if not decision["allowed"]:
            result = self._result_from_decision(request, decision)
            self.audit.record(result)
            return {"status": result.status, "result": result}

        tool = decision["tool"]
        assert isinstance(tool, ToolDefinition)
        now = datetime.now(timezone.utc)
        snapshot = self._policy_snapshot(request, tool, decision)
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=request.preview_id or request.tool_execution_request_id,
            draft_id=request.draft_id or request.tool_execution_request_id,
            session_id=request.session_id,
            status="pending",
            actions_requested=[tool.action],
            approval_scope="future_execution",
            reason=f"Governed tool execution requested for {tool.tool_id}.",
            risk_level=tool.risk_level,
            policy_snapshot=snapshot,
            expires_at=(now + timedelta(minutes=self.approvals.policy.ttl_minutes())).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=request.requested_by or Actor(type="user", id="local_user"),
            trace=[
                {
                    "stage": "governed_tool_approval",
                    "decision": "pending",
                    "reason": "approval_required_before_execution",
                    "tool_id": tool.tool_id,
                    "action": tool.action,
                }
            ],
            execution_status="not_executed",
        )
        self.approvals.store.save(approval)
        self.approvals.append_event(
            approval.approval_id,
            "approval_created",
            "ApprovalRequest criado para execucao governada de tool; nada foi executado.",
            data={"tool_id": tool.tool_id, "action": tool.action},
        )
        return {
            "status": "approval_required",
            "approval": approval,
            "tool_execution_request_id": request.tool_execution_request_id,
            "request_fingerprint": self._request_fingerprint(request),
            "safe_to_execute_after_approval": True,
        }

    def preview_decision(self, request: ToolExecutionRequest) -> dict[str, Any]:
        """Evaluate a governed tool request without executing or creating approval."""
        decision = self._decision(request)
        tool = decision.get("tool")
        return {
            "allowed": bool(decision.get("allowed")),
            "tool_id": tool.tool_id if isinstance(tool, ToolDefinition) else request.tool_id,
            "action": tool.action if isinstance(tool, ToolDefinition) else None,
            "capability": tool.capability if isinstance(tool, ToolDefinition) else None,
            "violations": list(decision.get("violations", [])),
            "warnings": list(decision.get("warnings", [])),
            "trace": list(decision.get("trace", [])),
            "shell_classification": (
                decision["shell_classification"].model_dump()
                if hasattr(decision.get("shell_classification"), "model_dump")
                else None
            ),
        }

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        execution_id = f"exec_{uuid4().hex}"
        decision = self._decision(request)
        if not decision["allowed"]:
            result = self._result_from_decision(request, decision, execution_id=execution_id)
            self.audit.record(result)
            return result

        approval_error = self._approval_error(request, decision)
        if approval_error:
            decision["violations"].append(approval_error)
            result = self._result_from_decision(request, decision, execution_id=execution_id)
            self.audit.record(result)
            return result

        tool = decision["tool"]
        assert isinstance(tool, ToolDefinition)
        timeout = self._timeout_seconds(request)
        if tool.adapter == "shell" and tool.action == "run_command":
            result = self._execute_shell(request, tool, decision, execution_id=execution_id, timeout=timeout)
        elif tool.adapter == "web" and tool.action == "web_request":
            result = self._execute_web(request, tool, decision, execution_id=execution_id, timeout=timeout)
        else:
            decision["violations"].append("governed_adapter_not_implemented")
            result = self._result_from_decision(request, decision, execution_id=execution_id)
        self.audit.record(result)
        return result

    def _decision(self, request: ToolExecutionRequest) -> dict[str, Any]:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        tool = self.registry.get_tool(request.tool_id)
        violations: list[str] = []
        warnings: list[str] = []
        trace: list[dict[str, Any]] = []
        if not config.get("enabled", False):
            violations.append("governed_tool_execution_disabled")
        if request.mode != "governed":
            violations.append("mode_not_governed")
        if tool is None:
            violations.append("unknown_tool")
            return {"allowed": False, "tool": None, "violations": violations, "warnings": warnings, "trace": trace}
        if not tool.enabled:
            violations.append("disabled_tool")
        if not tool.execute_supported:
            violations.append("execute_not_supported")
        if not tool.requires_approval:
            violations.append("approval_required_for_governed_execution")
        if tool.action not in set(config.get("allowed_actions", []) or []):
            violations.append("action_not_allowed_for_governed_execution")
        if tool.action in set(config.get("denied_actions", []) or []):
            violations.append("action_denied_for_governed_execution")
        if tool.capability not in set(config.get("allowed_capabilities", []) or []):
            violations.append("capability_not_allowed_for_governed_execution")
        if tool.capability in set(config.get("denied_capabilities", []) or []):
            violations.append("capability_denied_for_governed_execution")
        if tool.action in set(config.get("workspace_required_for", []) or []):
            workspace_error = self._workspace_error(str(request.input.get("workspace") or ""))
            if workspace_error:
                violations.append(workspace_error)
        shell_decision: dict[str, Any] | None = None
        if tool.adapter == "shell" and tool.action == "run_command":
            shell_decision = self._shell_decision(request)
            trace.extend(shell_decision["trace"])
            warnings.extend(shell_decision["warnings"])
            violations.extend(shell_decision["violations"])
        trace.append(
            {
                "stage": "governed_tool_policy",
                "decision": "blocked" if violations else "allowed",
                "action": tool.action,
                "capability": tool.capability,
                "requires_approval": tool.requires_approval,
            }
        )
        return {
            "allowed": not violations,
            "tool": tool,
            "violations": list(dict.fromkeys(violations)),
            "warnings": list(dict.fromkeys(warnings)),
            "trace": trace,
            "shell_classification": shell_decision.get("classification") if shell_decision else None,
            "write_envelope": shell_decision.get("envelope_decision").envelope if shell_decision and shell_decision.get("envelope_decision") else None,
        }

    def _shell_decision(self, request: ToolExecutionRequest) -> dict[str, Any]:
        workspace = str(request.input.get("workspace") or "")
        argv = request.input.get("argv")
        command = str(request.input.get("command") or "")
        normalized_argv = [str(item) for item in argv] if isinstance(argv, list) else None
        classification = self.shell_policy.classify(argv=normalized_argv, command=command, working_dir=workspace)
        violations: list[str] = []
        warnings: list[str] = []
        if classification.policy_decision == "blocked":
            violations.append(f"shell_category_blocked:{classification.category}")
        elif classification.policy_decision == "approval_required":
            warnings.append(f"shell_category_requires_approval:{classification.category}")
        envelope_decision = None
        operation_type = self._operation_type_for_shell_category(classification.category)
        if operation_type:
            envelope_decision = self.write_envelopes.create(
                task_id=request.draft_id or request.tool_execution_request_id,
                session_id=request.session_id,
                workspace_path=workspace,
                target_path=workspace,
                operation_type=operation_type,
                preview_id=request.preview_id,
                approval_id=request.approval_id,
                expected_side_effects=classification.expected_side_effects,
                risk_score=classification.risk_score,
                actor="governed_tool_execution",
            )
            if not envelope_decision.allowed:
                violations.append(f"write_envelope:{envelope_decision.reason}")
        trace = [
            {
                "stage": "shell_policy",
                "decision": classification.policy_decision,
                "command_id": classification.command_id,
                "category": classification.category,
                "risk_score": classification.risk_score,
                "expected_side_effects": classification.expected_side_effects,
            }
        ]
        if envelope_decision is not None:
            trace.append(
                {
                    "stage": "write_capability_envelope",
                    "decision": "allowed" if envelope_decision.allowed else "blocked",
                    "operation_id": envelope_decision.envelope.operation_id,
                    "workspace_id": envelope_decision.envelope.workspace_id,
                    "workspace_role": envelope_decision.envelope.workspace_role,
                    "reason": envelope_decision.reason,
                }
            )
        return {
            "classification": classification,
            "envelope_decision": envelope_decision,
            "violations": violations,
            "warnings": warnings,
            "trace": trace,
        }

    @staticmethod
    def _operation_type_for_shell_category(category: str) -> str | None:
        return {
            "readonly_shell": "run_shell_readonly",
            "git_read_shell": "run_shell_readonly",
            "test_shell": "run_shell_test",
            "build_shell": "run_shell_build",
            "package_shell": "run_shell_build",
            "write_shell": "run_shell_write",
        }.get(category)

    def _approval_error(self, request: ToolExecutionRequest, decision: dict[str, Any]) -> str | None:
        if not request.approval_id:
            return "approval_id_required"
        approval = self.approvals.get_approval(request.approval_id)
        if approval is None:
            return "approval_not_found"
        if approval.status != "approved":
            return f"approval_not_approved:{approval.status}"
        tool = decision["tool"]
        assert isinstance(tool, ToolDefinition)
        if tool.action not in approval.actions_requested:
            return "approval_action_mismatch"
        approved_hash = str(approval.policy_snapshot.config_versions.get("tool_execution_request_hash") or "")
        if approved_hash and approved_hash != self._request_fingerprint(request):
            return "approval_request_fingerprint_mismatch"
        return None

    def _execute_shell(
        self,
        request: ToolExecutionRequest,
        tool: ToolDefinition,
        decision: dict[str, Any],
        *,
        execution_id: str,
        timeout: int,
    ) -> ToolExecutionResult:
        argv, parse_error = self._command_argv(request.input)
        if parse_error:
            decision["violations"].append(parse_error)
            return self._result_from_decision(request, decision, execution_id=execution_id)
        executable_error = self._executable_error(argv)
        if executable_error:
            decision["violations"].append(executable_error)
            return self._result_from_decision(request, decision, execution_id=execution_id)
        workspace = str(request.input.get("workspace") or "")
        classification = decision.get("shell_classification")
        shell_metadata = self._shell_metadata(classification)
        started = time.perf_counter()
        try:
            completed = self.runner(
                argv,
                cwd=workspace,
                timeout=timeout,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_id=request.tool_id,
                status="timeout",
                action=tool.action,
                capability=tool.capability,
                workspace=workspace,
                content=self._limit_text((exc.stdout or "") + (exc.stderr or "")),
                metadata={**shell_metadata, "timeout_seconds": timeout, "timeout": True, "duration_ms": int((time.perf_counter() - started) * 1000)},
                warnings=list(decision["warnings"]),
                violations=["tool_execution_timeout"],
                trace=[*decision["trace"], {"stage": "shell_command_finished", "decision": "timeout"}],
                side_effects=tool.side_effect,
                safe_to_execute=False,
            )
        except Exception as exc:
            result = ToolExecutionResult(
                execution_id=execution_id,
                tool_id=request.tool_id,
                status="degraded",
                action=tool.action,
                capability=tool.capability,
                workspace=workspace,
                content=None,
                metadata={**shell_metadata, "error": exc.__class__.__name__, "duration_ms": int((time.perf_counter() - started) * 1000)},
                warnings=[*decision["warnings"], str(exc)],
                violations=["tool_execution_failed"],
                trace=[*decision["trace"], {"stage": "shell_adapter", "decision": "failed"}],
                side_effects=tool.side_effect,
                safe_to_execute=False,
            )
            return result
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        status = "executed_governed" if completed.returncode == 0 else "degraded"
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ToolExecutionResult(
            execution_id=execution_id,
            tool_id=request.tool_id,
            status=status,
            action=tool.action,
            capability=tool.capability,
            workspace=workspace,
            content=self._limit_text(stdout if stdout else stderr),
            content_truncated=len(stdout if stdout else stderr) > self._max_output_chars(),
            metadata={
                **shell_metadata,
                "exit_code": completed.returncode,
                "stderr_preview": self._limit_text(stderr, max_chars=1000),
                "argv_length": len(argv),
                "duration_ms": duration_ms,
            },
            warnings=list(decision["warnings"]),
            violations=[] if completed.returncode == 0 else ["tool_exit_code_nonzero"],
            trace=[
                *decision["trace"],
                {"stage": "shell_command_started", "decision": "started", **shell_metadata},
                {"stage": "shell_command_finished", "decision": status, "exit_code": completed.returncode, "duration_ms": duration_ms},
            ],
            side_effects=tool.side_effect,
            safe_to_execute=completed.returncode == 0,
        )

    @staticmethod
    def _shell_metadata(classification: Any) -> dict[str, Any]:
        if classification is None:
            return {}
        return {
            "command_id": getattr(classification, "command_id", None),
            "normalized_command": getattr(classification, "normalized_command", None),
            "shell_category": getattr(classification, "category", None),
            "shell_policy_decision": getattr(classification, "policy_decision", None),
            "risk_score": getattr(classification, "risk_score", None),
            "expected_side_effects": getattr(classification, "expected_side_effects", []),
        }

    def _execute_web(
        self,
        request: ToolExecutionRequest,
        tool: ToolDefinition,
        decision: dict[str, Any],
        *,
        execution_id: str,
        timeout: int,
    ) -> ToolExecutionResult:
        url = str(request.input.get("url") or "")
        method = str(request.input.get("method") or "GET").upper()
        network_error = self._network_error(url, method)
        if network_error:
            decision["violations"].append(network_error)
            return self._result_from_decision(request, decision, execution_id=execution_id)
        try:
            response = self.opener(Request(url, method=method), timeout=timeout)
            with response:
                body = response.read(self._max_output_chars() + 1)
                text = body.decode("utf-8", errors="replace")
                status_code = getattr(response, "status", None) or getattr(response, "code", None)
        except Exception as exc:
            return ToolExecutionResult(
                execution_id=execution_id,
                tool_id=request.tool_id,
                status="degraded",
                action=tool.action,
                capability=tool.capability,
                content=None,
                metadata={"url_host": urlparse(url).hostname, "method": method, "error": exc.__class__.__name__},
                warnings=[*decision["warnings"], str(exc)],
                violations=["web_request_failed"],
                trace=[*decision["trace"], {"stage": "web_adapter", "decision": "failed"}],
                side_effects=tool.side_effect,
                safe_to_execute=False,
            )
        return ToolExecutionResult(
            execution_id=execution_id,
            tool_id=request.tool_id,
            status="executed_governed",
            action=tool.action,
            capability=tool.capability,
            content=self._limit_text(text),
            content_truncated=len(text) > self._max_output_chars(),
            metadata={"url_host": urlparse(url).hostname, "method": method, "http_status": status_code},
            warnings=list(decision["warnings"]),
            trace=[*decision["trace"], {"stage": "web_adapter", "decision": "executed_governed", "http_status": status_code}],
            side_effects=tool.side_effect,
            safe_to_execute=True,
        )

    def _command_argv(self, payload: dict[str, Any]) -> tuple[list[str], str | None]:
        raw_argv = payload.get("argv")
        if isinstance(raw_argv, list) and all(isinstance(item, str) and item for item in raw_argv):
            return [str(item) for item in raw_argv], None
        command = str(payload.get("command") or "").strip()
        if not command:
            return [], "command_or_argv_required"
        denied = [str(item) for item in (self.policy.get("shell", {}) or {}).get("denied_tokens", []) or []]
        lowered = command.lower()
        for token in denied:
            if token.lower() in lowered:
                return [], "shell_metacharacter_denied"
        try:
            argv = shlex.split(command, posix=False)
        except ValueError:
            return [], "command_parse_failed"
        argv = [self._strip_wrapping_quotes(str(part)) for part in argv]
        return argv, None if argv else "command_or_argv_required"

    @staticmethod
    def _strip_wrapping_quotes(value: str) -> str:
        text = str(value)
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            return text[1:-1]
        return text

    def _executable_error(self, argv: list[str]) -> str | None:
        shell_policy = self.policy.get("shell", {}) if isinstance(self.policy, dict) else {}
        allowed = {str(item).lower() for item in shell_policy.get("allowed_executables", []) or []}
        denied = {str(item).lower() for item in shell_policy.get("denied_executables", []) or []}
        executable = Path(argv[0].strip('"')).name.lower() if argv else ""
        if executable in denied:
            return "executable_denied"
        if allowed and executable not in allowed:
            return "executable_not_allowlisted"
        return None

    def _network_error(self, url: str, method: str) -> str | None:
        network = self.policy.get("network", {}) if isinstance(self.policy, dict) else {}
        parsed = urlparse(url)
        if method not in set(network.get("allowed_methods", []) or []):
            return "network_method_not_allowed"
        if parsed.scheme.lower() in {str(item).lower() for item in network.get("denied_schemes", []) or []}:
            return "network_scheme_denied"
        if parsed.scheme.lower() not in {"http", "https"}:
            return "network_scheme_not_allowed"
        host = (parsed.hostname or "").lower()
        if not host:
            return "network_host_required"
        if host in {str(item).lower() for item in network.get("denied_hosts", []) or []}:
            return "network_host_denied"
        if host in {"localhost", "127.0.0.1", "::1"} and not bool(network.get("allow_localhost", False)):
            return "network_localhost_denied"
        return None

    def _workspace_error(self, workspace: str) -> str | None:
        if not workspace:
            return "workspace_required"
        workspace_path = Path(workspace).resolve(strict=False)
        allowed = [
            Path(str(item)).resolve(strict=False)
            for item in (self.policy.get("governed_tool_execution", {}) or {}).get("allowed_workspace_roots", []) or []
        ]
        normalized_workspace = os.path.normcase(str(workspace_path))
        for root in allowed:
            normalized_root = os.path.normcase(str(root))
            if normalized_workspace == normalized_root or normalized_workspace.startswith(normalized_root + os.sep):
                return None
        return "workspace_not_allowlisted_for_governed_execution"

    def _timeout_seconds(self, request: ToolExecutionRequest) -> int:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        requested = int(request.input.get("timeout_seconds") or config.get("default_timeout_seconds", 30) or 30)
        maximum = int(config.get("max_timeout_seconds", 120) or 120)
        return max(1, min(requested, maximum))

    def _max_output_chars(self) -> int:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        return int(config.get("max_output_chars", 12000) or 12000)

    def _limit_text(self, value: str, *, max_chars: int | None = None) -> str:
        limit = max_chars or self._max_output_chars()
        if len(value) <= limit:
            return value
        return value[:limit] + f"\n...[truncated {len(value) - limit} chars]"

    def _result_from_decision(
        self,
        request: ToolExecutionRequest,
        decision: dict[str, Any],
        *,
        execution_id: str | None = None,
    ) -> ToolExecutionResult:
        tool = decision.get("tool")
        status = "invalid" if "unknown_tool" in decision.get("violations", []) else "blocked"
        return ToolExecutionResult(
            execution_id=execution_id or f"exec_{uuid4().hex}",
            tool_id=request.tool_id,
            status=status,
            action=tool.action if isinstance(tool, ToolDefinition) else None,
            capability=tool.capability if isinstance(tool, ToolDefinition) else None,
            workspace=str(request.input.get("workspace") or "") or None,
            target_path=str(request.input.get("path") or "") or None,
            warnings=list(decision.get("warnings", [])),
            violations=list(decision.get("violations", [])),
            trace=list(decision.get("trace", [])),
            side_effects=bool(tool.side_effect) if isinstance(tool, ToolDefinition) else False,
            safe_to_execute=False,
        )

    def _policy_snapshot(self, request: ToolExecutionRequest, tool: ToolDefinition, decision: dict[str, Any]) -> ApprovalPolicySnapshot:
        fingerprint = self._request_fingerprint(request)
        trace_hash = hashlib.sha256(json.dumps(decision.get("trace", []), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        return ApprovalPolicySnapshot(
            policy_status="approval_required",
            allowed_actions=[tool.action],
            denied_actions=list((self.policy.get("governed_tool_execution", {}) or {}).get("denied_actions", []) or []),
            approval_required_for=[tool.action],
            granted_capabilities=[tool.capability],
            denied_capabilities=list((self.policy.get("governed_tool_execution", {}) or {}).get("denied_capabilities", []) or []),
            workspace_status="governed_allowlisted",
            risk_level=tool.risk_level,
            trace_hash=trace_hash,
            config_versions={
                "governed_tool_execution_policy": int(self.policy.get("schema_version", 1) or 1),
                "tool_id": tool.tool_id,
                "tool_action": tool.action,
                "tool_execution_request_hash": fingerprint,
            },
        )

    def _request_fingerprint(self, request: ToolExecutionRequest) -> str:
        payload = {
            "tool_id": request.tool_id,
            "input": request.input,
            "mode": "governed",
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def status(self) -> dict[str, object]:
        config = self.policy.get("governed_tool_execution", {}) if isinstance(self.policy, dict) else {}
        return {
            "status": "ok" if config.get("enabled", False) else "disabled",
            "service": "governed_tool_execution",
            "mode": config.get("mode", "unknown"),
            "approval_required": bool(config.get("require_approval", True)),
            "audit_required": bool(config.get("require_audit", True)),
            "allowed_actions": list(config.get("allowed_actions", []) or []),
            "denied_actions": list(config.get("denied_actions", []) or []),
            "shell_free": True,
            "uses_shell_true": False,
            "timeout_seconds": {
                "default": config.get("default_timeout_seconds"),
                "max": config.get("max_timeout_seconds"),
            },
        }
