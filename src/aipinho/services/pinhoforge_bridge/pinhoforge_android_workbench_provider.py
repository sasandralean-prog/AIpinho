from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from aipinho.core.paths import PATHS
from aipinho.schemas.pinhoforge_bridge.android_workbench import (
    PinhoForgeAndroidArtifact,
    PinhoForgeAndroidWorkbenchRequest,
    PinhoForgeAndroidWorkbenchResult,
    PinhoForgeGradleExecutionResult,
)
from aipinho.services.pinhoforge_bridge.pinhoforge_hardware_profiler_provider import PinhoForgeHardwareProfilerProvider
from aipinho.services.pinhoforge_bridge.workflow_context import workflow_evidence_refs
from aipinho.utils.yaml_loader import load_yaml_file


class BridgeProcessRunner(Protocol):
    def run(self, argv: list[str], cwd: str | None, timeout: int) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessBridgeProcessRunner:
    def run(self, argv: list[str], cwd: str | None, timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run(argv, cwd=cwd, timeout=timeout, text=True, capture_output=True, shell=False)


class PinhoForgeAndroidWorkbenchProvider:
    def __init__(
        self,
        config_path: Path | None = None,
        *,
        root: Path | None = None,
        runner: BridgeProcessRunner | None = None,
        hardware_provider: PinhoForgeHardwareProfilerProvider | None = None,
    ) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_android_workbench.yaml"
        self.root = root or PATHS.project_root
        self.runner = runner or SubprocessBridgeProcessRunner()
        self.hardware_provider = hardware_provider or PinhoForgeHardwareProfilerProvider()

    def config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def handle(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        blocked_reason = self._blocked_operation_reason(request)
        if blocked_reason:
            return self._blocked(request, *blocked_reason)

        if request.operation == "detect_project":
            return self._detect_project(request)
        if request.operation == "environment_readiness":
            return self._environment_readiness(request)
        if request.operation == "list_gradle_tasks":
            return self._list_gradle_tasks(request)
        if request.operation == "execute_gradle_task":
            return self._execute_gradle_task(request)
        if request.operation == "adb_devices":
            return self._adb_devices(request)
        if request.operation == "logcat_readonly":
            return self._logcat(request)
        if request.operation == "export_report":
            return self._export_report(request)
        return self._blocked(request, "unsupported_android_operation", "Operacao Android Workbench nao suportada.")

    def _detect_project(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        path = self._project_path(request)
        if path is None:
            return self._blocked(request, "android_project_path_required", "Path do projeto Android e obrigatorio.")
        profile = self._project_profile(path)
        status = "completed" if profile["exists"] else "blocked"
        return PinhoForgeAndroidWorkbenchResult(
            request_id=request.request_id,
            operation=request.operation,
            status=status,
            reason_code=None if status == "completed" else "android_project_path_not_found",
            human_message="Projeto Android analisado." if status == "completed" else "Projeto Android nao encontrado.",
            project_profile=profile,
            evidence_refs=self._evidence(request),
        )

    def _environment_readiness(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        profile = self.hardware_provider.handle(
            PinhoForgeHardwareProfilerRequestShim(
                operation="get_readiness_summary",
            ).to_request()
        )
        return PinhoForgeAndroidWorkbenchResult(
            request_id=request.request_id,
            operation=request.operation,
            status="completed",
            human_message="Readiness Android consultado em modo governado.",
            environment_readiness={
                "android_readiness": profile.readiness_summary.android_readiness if profile.readiness_summary else "unknown",
                "conversion_readiness": profile.readiness_summary.conversion_readiness if profile.readiness_summary else "unknown",
                "warnings": profile.warnings,
                "blockers": profile.readiness_summary.blockers if profile.readiness_summary else [],
            },
            evidence_refs=self._evidence(request),
        )

    def _list_gradle_tasks(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        provider = self.config().get("provider") or {}
        tasks = list(provider.get("gradle_tasks") or [])
        return PinhoForgeAndroidWorkbenchResult(
            request_id=request.request_id,
            operation=request.operation,
            status="completed",
            human_message="Tasks Gradle allowlisted consultadas.",
            gradle_tasks=tasks,
            evidence_refs=self._evidence(request),
        )

    def _execute_gradle_task(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        path = self._project_path(request)
        if path is None:
            return self._blocked(request, "android_project_path_required", "Path do projeto Android e obrigatorio.")
        task = request.task_id
        if not task:
            return self._blocked(request, "android_gradle_task_required", "Task Gradle e obrigatoria.")
        definition = self._task_definition(task)
        if definition is None:
            return self._blocked(request, "android_unknown_gradle_task_blocked", "Task Gradle desconhecida foi bloqueada.")
        command = self._build_gradle_command(path, definition["args"])
        timeout = int(definition.get("timeout_seconds") or request.timeout_seconds)
        output_limit = int(request.output_limit_kb * 1024)
        try:
            completed = self.runner.run(command, str(path), timeout)
            stdout = (completed.stdout or "")[:output_limit]
            stderr = (completed.stderr or "")[:output_limit]
            status = "completed" if completed.returncode == 0 else "failed"
            execution = PinhoForgeGradleExecutionResult(
                task_id=task,
                command_preview=command,
                cwd_redacted=str(path),
                status=status,
                exit_code=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                stdout_truncated=len(completed.stdout or "") > output_limit,
                stderr_truncated=len(completed.stderr or "") > output_limit,
                duration_ms=None,
                warnings=[],
                errors=[] if completed.returncode == 0 else ["gradle_task_failed"],
            )
        except subprocess.TimeoutExpired as exc:
            execution = PinhoForgeGradleExecutionResult(
                task_id=task,
                command_preview=command,
                cwd_redacted=str(path),
                status="timeout",
                exit_code=None,
                stdout=(exc.stdout or "")[:output_limit] if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "")[:output_limit] if isinstance(exc.stderr, str) else "",
                stdout_truncated=False,
                stderr_truncated=False,
                duration_ms=timeout * 1000,
                warnings=["gradle_timeout"],
                errors=["gradle_task_timeout"],
            )
        report_markdown = self._render_android_report(request, path, execution)
        report_json = {
            "request_id": request.request_id,
            "task_id": task,
            "status": execution.status,
            "exit_code": execution.exit_code,
        }
        return PinhoForgeAndroidWorkbenchResult(
            request_id=request.request_id,
            operation=request.operation,
            status="completed" if execution.status == "completed" else execution.status,
            reason_code=None if execution.status != "blocked" else "android_gradle_task_blocked",
            human_message=f"Task Gradle {task} executada de forma governada." if execution.status == "completed" else f"Task Gradle {task} terminou com status {execution.status}.",
            project_profile=self._project_profile(path),
            environment_readiness=self._environment_summary(),
            command_preview={
                "task_id": task,
                "command_preview": command,
                "cwd_redacted": str(path),
                "allowed": True,
            },
            execution_result=execution,
            report_markdown=report_markdown,
            report_json=report_json,
            artifacts=[
                PinhoForgeAndroidArtifact(filename="android_workbench_report.md", content_type="text/markdown"),
                PinhoForgeAndroidArtifact(filename="android_workbench_report.json", content_type="application/json"),
            ],
            warnings=execution.warnings,
            errors=execution.errors,
            evidence_refs=self._evidence(request),
        )

    def _adb_devices(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        try:
            completed = self.runner.run(["adb", "devices"], None, 15)
            devices = []
            for line in (completed.stdout or "").splitlines()[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                serial = parts[0]
                state = parts[1] if len(parts) > 1 else "unknown"
                devices.append({"serial_redacted": serial[:4] + "***", "state": state, "details": line})
            return PinhoForgeAndroidWorkbenchResult(
                request_id=request.request_id,
                operation=request.operation,
                status="completed",
                human_message="ADB devices consultado em modo read-only.",
                adb_devices=devices,
                evidence_refs=self._evidence(request),
            )
        except Exception as exc:
            return PinhoForgeAndroidWorkbenchResult(
                request_id=request.request_id,
                operation=request.operation,
                status="completed_with_warnings",
                human_message="ADB devices consultado com warnings.",
                adb_devices=[],
                warnings=[type(exc).__name__],
                evidence_refs=self._evidence(request),
            )

    def _logcat(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        output_limit = int(request.output_limit_kb * 1024)
        try:
            completed = self.runner.run(["adb", "logcat", "-d"], None, 20)
            lines = (completed.stdout or "").splitlines()
            if request.logcat_filter:
                lines = [line for line in lines if request.logcat_filter.lower() in line.lower()]
            truncated = "\n".join(lines)
            truncated = truncated[:output_limit]
            return PinhoForgeAndroidWorkbenchResult(
                request_id=request.request_id,
                operation=request.operation,
                status="completed",
                human_message="Logcat capturado em modo read-only.",
                logcat={
                    "status": "completed",
                    "lines": truncated.splitlines(),
                    "filter": request.logcat_filter,
                    "truncated": len(truncated) >= output_limit,
                    "warnings": [],
                },
                artifacts=[PinhoForgeAndroidArtifact(filename="android_logcat.txt", content_type="text/plain")],
                evidence_refs=self._evidence(request),
            )
        except Exception as exc:
            return PinhoForgeAndroidWorkbenchResult(
                request_id=request.request_id,
                operation=request.operation,
                status="completed_with_warnings",
                human_message="Logcat nao pode ser capturado, mas a operacao foi tratada.",
                logcat={"status": "failed", "lines": [], "filter": request.logcat_filter, "truncated": False, "warnings": [type(exc).__name__]},
                warnings=[type(exc).__name__],
                evidence_refs=self._evidence(request),
            )

    def _export_report(self, request: PinhoForgeAndroidWorkbenchRequest) -> PinhoForgeAndroidWorkbenchResult:
        path = self._project_path(request)
        profile = self._project_profile(path) if path else None
        report_markdown = self._render_android_report(request, path, None)
        report_json = {
            "request_id": request.request_id,
            "project_profile": profile,
            "environment_readiness": self._environment_summary(),
        }
        return PinhoForgeAndroidWorkbenchResult(
            request_id=request.request_id,
            operation=request.operation,
            status="completed",
            human_message="Relatorio Android exportado em modo governado.",
            project_profile=profile,
            environment_readiness=self._environment_summary(),
            report_markdown=report_markdown,
            report_json=report_json,
            artifacts=[
                PinhoForgeAndroidArtifact(filename="android_workbench_report.md", content_type="text/markdown"),
                PinhoForgeAndroidArtifact(filename="android_workbench_report.json", content_type="application/json"),
            ],
            evidence_refs=self._evidence(request),
        )

    def _blocked_operation_reason(self, request: PinhoForgeAndroidWorkbenchRequest) -> tuple[str, str] | None:
        if request.source_scope not in {"sandbox", "target_mutable", "registered_workspace", "import_authorized"}:
            return "android_external_path_unregistered", "Path externo nao registrado foi bloqueado."
        mapping = {
            "adb_shell": ("android_adb_shell_blocked", "ADB shell esta bloqueado por policy."),
            "adb_install": ("android_adb_install_blocked", "ADB install esta bloqueado por policy."),
            "adb_uninstall": ("android_adb_uninstall_blocked", "ADB uninstall esta bloqueado por policy."),
            "adb_push": ("android_adb_push_pull_blocked", "ADB push/pull esta bloqueado por policy."),
            "adb_pull": ("android_adb_push_pull_blocked", "ADB push/pull esta bloqueado por policy."),
            "clear_app_data": ("android_clear_data_blocked", "Limpar dados de app esta bloqueado por policy."),
        }
        return mapping.get(request.operation)

    def _task_definition(self, task_id: str) -> dict[str, Any] | None:
        provider = self.config().get("provider") or {}
        return next((task for task in provider.get("gradle_tasks") or [] if task.get("task_id") == task_id), None)

    def _project_path(self, request: PinhoForgeAndroidWorkbenchRequest) -> Path | None:
        if not request.project_path:
            return None
        return Path(str(request.project_path).strip().strip('"')).expanduser()

    def _project_profile(self, path: Path) -> dict[str, Any]:
        exists = path.exists() and path.is_dir()
        settings = any((path / name).exists() for name in ("settings.gradle", "settings.gradle.kts"))
        wrapper = next((name for name in ("gradlew.bat", "gradlew") if (path / name).exists()), None)
        manifest_files = list(path.glob("**/AndroidManifest.xml"))
        build_files = list(path.glob("**/build.gradle")) + list(path.glob("**/build.gradle.kts"))
        modules = sorted({item.parent.name for item in build_files if item.parent != path})
        return {
            "project_root_redacted": str(path),
            "exists": exists,
            "is_android_project": bool(manifest_files or settings or build_files),
            "uses_gradle_wrapper": wrapper is not None,
            "gradle_wrapper_path_redacted": str(path / wrapper) if wrapper else None,
            "modules": modules,
            "manifest_paths_redacted": [str(item) for item in manifest_files[:20]],
            "build_files_redacted": [str(item) for item in build_files[:20]],
            "warnings": [] if exists else ["project_directory_not_found"],
            "errors": [],
        }

    def _build_gradle_command(self, path: Path, args: list[str]) -> list[str]:
        if (path / "gradlew.bat").exists():
            return [str(path / "gradlew.bat"), *args]
        if (path / "gradlew").exists():
            return [str(path / "gradlew"), *args]
        return ["gradle", *args]

    def _render_android_report(
        self,
        request: PinhoForgeAndroidWorkbenchRequest,
        path: Path | None,
        execution: PinhoForgeGradleExecutionResult | None,
    ) -> str:
        return "\n".join(
            [
                "# PinhoForge Android Workbench Report",
                "",
                f"Request: {request.request_id}",
                f"Project: {path or 'not provided'}",
                f"Task: {request.task_id or 'n/a'}",
                f"Status: {execution.status if execution else 'not_run'}",
                f"Exit code: {execution.exit_code if execution else 'n/a'}",
            ]
        ) + "\n"

    def _environment_summary(self) -> dict[str, Any]:
        result = self.hardware_provider.handle(PinhoForgeHardwareProfilerRequestShim(operation="get_readiness_summary").to_request())
        return {
            "android_readiness": result.readiness_summary.android_readiness if result.readiness_summary else "unknown",
            "conversion_readiness": result.readiness_summary.conversion_readiness if result.readiness_summary else "unknown",
            "warnings": result.warnings,
            "blockers": result.readiness_summary.blockers if result.readiness_summary else [],
        }

    def _blocked(self, request: PinhoForgeAndroidWorkbenchRequest, reason_code: str, message: str) -> PinhoForgeAndroidWorkbenchResult:
        return PinhoForgeAndroidWorkbenchResult(
            request_id=request.request_id,
            operation=request.operation,
            status="blocked",
            reason_code=reason_code,
            human_message=message,
            warnings=[message],
            evidence_refs=self._evidence(request),
        )

    def _evidence(self, request: PinhoForgeAndroidWorkbenchRequest) -> list[str]:
        return workflow_evidence_refs(
            request.metadata,
            ["provider:pinhoforge_android_workbench", f"request:{request.request_id}"],
        )


class PinhoForgeHardwareProfilerRequestShim:
    def __init__(self, *, operation: str) -> None:
        self.operation = operation

    def to_request(self):
        from aipinho.schemas.pinhoforge_bridge.hardware_profiler import PinhoForgeHardwareProfilerRequest

        return PinhoForgeHardwareProfilerRequest(operation=self.operation)
