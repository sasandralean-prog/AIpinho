from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path

from aipinho.schemas.sandbox import SandboxShellCommand, SandboxShellRequest
from aipinho.services.events.event_core import redact_payload
from aipinho.services.sandbox.sandbox_policy_service import SandboxPolicyService
from aipinho.services.sandbox.sandbox_store_service import SandboxStoreService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService


class SandboxShellService:
    def __init__(self, *, store: SandboxStoreService | None = None, policy: SandboxPolicyService | None = None) -> None:
        self.store = store or SandboxStoreService()
        self.policy = policy or SandboxPolicyService()
        self.workspaces = SandboxWorkspaceService(store=self.store, policy=self.policy)

    def run(self, request: SandboxShellRequest) -> SandboxShellCommand:
        workspace = self.workspaces.get_workspace(request.sandbox_workspace_id)
        operation_root = self.workspaces.operation_root(request.sandbox_workspace_id, request.sandbox_task_id)
        if workspace.role == "sandbox_readonly":
            decision = self.policy._decision(False, "source_readonly_write_denied", "Shell foi bloqueado em workspace sandbox read-only.")
        else:
            decision = self.policy.allow_shell(
                workspace_root=operation_root,
                cwd_relative=request.cwd_relative or ".",
                command=request.command,
                category=request.category,
            )
        category = request.category or self.policy.classify_shell(request.command)
        if not decision.allowed:
            command = SandboxShellCommand(
                sandbox_task_id=request.sandbox_task_id,
                sandbox_workspace_id=request.sandbox_workspace_id,
                command=request.command,
                cwd_relative=request.cwd_relative,
                category=category,
                status="blocked",
                reason_code=decision.reason_code,
                evidence_refs=decision.evidence_refs,
            )
            self.store.save_shell_command(command)
            self.store.append_trace(request.sandbox_task_id, {"type": "sandbox_shell_blocked", "reason_code": decision.reason_code, "command_id": command.command_id})
            return command
        cwd = (operation_root / request.cwd_relative).resolve(strict=False)
        argv = shlex.split(request.command, posix=os.name != "nt")
        start = time.perf_counter()
        try:
            completed = subprocess.run(argv, cwd=cwd, timeout=request.timeout_seconds, text=True, capture_output=True, shell=False)
            status = "succeeded" if completed.returncode == 0 else "failed"
            output_limit = int(self.policy.policy().get("shell", {}).get("max_output_kb", 512)) * 1024
            result = SandboxShellCommand(
                sandbox_task_id=request.sandbox_task_id,
                sandbox_workspace_id=request.sandbox_workspace_id,
                command=request.command,
                normalized_command=[str(part) for part in argv],
                cwd_relative=request.cwd_relative,
                category=category,
                status=status,  # type: ignore[arg-type]
                reason_code="sandbox_shell_allowed",
                exit_code=completed.returncode,
                stdout_sanitized=str(redact_payload(self._bounded_output(completed.stdout or "", output_limit))),
                stderr_sanitized=str(redact_payload(self._bounded_output(completed.stderr or "", output_limit))),
                duration_ms=int((time.perf_counter() - start) * 1000),
                evidence_refs=[f"sandbox_shell:{category}"],
            )
        except subprocess.TimeoutExpired as exc:
            result = SandboxShellCommand(
                sandbox_task_id=request.sandbox_task_id,
                sandbox_workspace_id=request.sandbox_workspace_id,
                command=request.command,
                normalized_command=[str(part) for part in argv],
                cwd_relative=request.cwd_relative,
                category=category,
                status="failed",
                reason_code="sandbox_shell_timeout",
                stderr_sanitized=str(redact_payload(str(exc))),
                duration_ms=int((time.perf_counter() - start) * 1000),
                evidence_refs=[f"sandbox_shell:{category}"],
            )
        self.store.save_shell_command(result)
        self.store.append_trace(request.sandbox_task_id, {"type": "sandbox_shell_finished", "status": result.status, "reason_code": result.reason_code, "command_id": result.command_id})
        if request.sandbox_task_id:
            task = self.store.get_task(request.sandbox_task_id)
            if task is not None:
                command_ids = [*task.shell_command_ids]
                if result.command_id not in command_ids:
                    command_ids.append(result.command_id)
                evidence_ref = f"sandbox_shell_command:{result.command_id}"
                evidence_refs = [*task.evidence_refs]
                if evidence_ref not in evidence_refs:
                    evidence_refs.append(evidence_ref)
                self.store.save_task(
                    task.model_copy(
                        update={
                            "shell_command_ids": command_ids,
                            "status": "running" if result.status == "succeeded" else "failed",
                            "updated_at": result.created_at,
                            "evidence_refs": evidence_refs,
                        }
                    )
                )
        return result

    def _bounded_output(self, output: str, limit: int) -> str:
        encoded = output.encode("utf-8")
        if len(encoded) <= limit:
            return output
        suffix = "\n...[sandbox output truncated by configured limit]"
        return encoded[:limit].decode("utf-8", errors="ignore") + suffix
