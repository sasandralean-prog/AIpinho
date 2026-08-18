from __future__ import annotations

import os
import re
import shutil
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.pinhoforge_bridge.hardware_profiler import (
    PinhoForgeHardwareProfilerRequest,
    PinhoForgeHardwareProfilerResult,
    PinhoForgeReadinessSummary,
    PinhoForgeToolAvailabilityItem,
)
from aipinho.services.pinhoforge_bridge.workflow_context import workflow_evidence_refs
from aipinho.utils.yaml_loader import load_yaml_file


class PinhoForgeHardwareProfilerProvider:
    def __init__(self, config_path: Path | None = None, *, root: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_hardware_profiler.yaml"
        self.root = root or PATHS.project_root
        self._user_home = str(Path.home())

    def config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def handle(self, request: PinhoForgeHardwareProfilerRequest) -> PinhoForgeHardwareProfilerResult:
        blocked_reason = self._blocked_operation_reason(request.operation)
        if blocked_reason:
            return self._blocked(request, *blocked_reason)

        generated_at = datetime.now(timezone.utc).isoformat()
        tools = self._tool_items()
        readiness = self._build_readiness(tools)
        system_profile = self._system_profile(generated_at)
        hardware_profile = self._hardware_profile()
        report_markdown = None
        report_json = None
        if request.operation == "export_environment_report":
            report_markdown = self._render_markdown(generated_at, readiness, tools)
            report_json = {
                "generated_at": generated_at,
                "system_profile": system_profile,
                "hardware_profile": hardware_profile,
                "tool_availability": [item.model_dump() for item in tools],
                "readiness_summary": readiness.model_dump(),
                "redaction_applied": True,
            }

        tool_payload = tools if request.include_tools or request.operation == "get_tool_availability" else []
        return PinhoForgeHardwareProfilerResult(
            request_id=request.request_id,
            operation=request.operation,
            status="completed_with_warnings" if readiness.warnings else "completed",
            human_message=self._human_message(request.operation, readiness),
            generated_at=generated_at,
            system_profile=system_profile if request.include_hardware or request.operation == "get_environment_profile" else None,
            hardware_profile=hardware_profile if request.include_hardware or request.operation == "get_environment_profile" else None,
            tool_availability=tool_payload,
            readiness_summary=readiness,
            report_markdown=report_markdown,
            report_json=report_json,
            warnings=readiness.warnings,
            errors=[],
            redaction_applied=True,
            evidence_refs=self._evidence(request),
        )

    def _blocked_operation_reason(self, operation: str) -> tuple[str, str] | None:
        mapping = {
            "install_tool": ("pinhoforge_tool_install_not_allowed", "Instalacao de ferramenta bloqueada por policy."),
            "repair_environment": ("pinhoforge_environment_mutation_not_allowed", "Reparo de ambiente bloqueado por policy."),
            "modify_path": ("pinhoforge_path_modify_blocked", "Modificacao de PATH bloqueada por policy."),
            "run_diagnostic_command_arbitrary": ("pinhoforge_setup_command_blocked", "Comando arbitrario de diagnostico bloqueado por policy."),
            "execute_terminal": ("pinhoforge_environment_mutation_not_allowed", "Execucao de terminal bloqueada neste provider read-only."),
            "run_build": ("pinhoforge_environment_mutation_not_allowed", "Execucao de build nao faz parte do provider de hardware."),
        }
        return mapping.get(operation)

    def _tool_items(self) -> list[PinhoForgeToolAvailabilityItem]:
        provider = self.config().get("provider") or {}
        items = []
        for item in provider.get("tools") or []:
            tool_id = str(item.get("tool_id"))
            display_name = str(item.get("display_name") or tool_id)
            executable = shutil.which(str(item.get("command") or tool_id))
            status = "available" if executable else "missing"
            version = None
            if executable:
                version = self._redact(str(Path(executable).name))
            items.append(
                PinhoForgeToolAvailabilityItem(
                    tool_id=tool_id,
                    display_name=display_name,
                    status=status,
                    version=version,
                    executable_path_redacted=self._redact(executable) if executable else None,
                    used_by_capabilities=list(item.get("used_by_capabilities") or []),
                    readiness_impact="supports_capability" if executable else "capability_degraded",
                    warnings=[] if executable else [f"{tool_id} missing"],
                    errors=[],
                )
            )
        return items

    def _build_readiness(self, tools: list[PinhoForgeToolAvailabilityItem]) -> PinhoForgeReadinessSummary:
        tool_status = {item.tool_id: item.status for item in tools}

        def has(*tool_ids: str) -> bool:
            return any(tool_status.get(tool_id) == "available" for tool_id in tool_ids)

        conversion = "ready" if has("ffmpeg", "libreoffice", "pandoc", "calibre", "inkscape") else "degraded" if has("tesseract", "whisper") else "missing"
        android = "ready" if has("java", "gradle", "adb") and (os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")) else "degraded" if has("java", "adb") else "missing"
        media = "ready" if has("ffmpeg", "tesseract", "whisper") else "degraded" if has("ffmpeg", "tesseract", "whisper") else "missing"
        development = "ready" if has("java", "python", "git") else "degraded" if has("java", "python", "git", "node") else "missing"
        warnings = []
        blockers = []
        if conversion != "ready":
            warnings.append("conversion_readiness_not_full")
        if android != "ready":
            warnings.append("android_readiness_not_full")
        if tool_status.get("ffmpeg") != "available":
            blockers.append("FFmpeg nao detectado.")
        if not (os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")):
            blockers.append("Android SDK nao configurado.")
        if tool_status.get("adb") != "available":
            blockers.append("ADB nao detectado.")
        if tool_status.get("java") != "available":
            blockers.append("JDK nao detectado.")
        return PinhoForgeReadinessSummary(
            conversion_readiness=conversion,
            android_readiness=android,
            media_readiness=media,
            development_readiness=development,
            terminal_readiness="ready",
            blockers=blockers,
            warnings=warnings,
            recommended_next_steps=[f"Corrigir manualmente: {item}" for item in blockers],
        )

    def _system_profile(self, generated_at: str) -> dict[str, Any]:
        cwd = Path.cwd()
        return {
            "generated_at": generated_at,
            "os_name": os.name,
            "platform": os.getenv("OS") or os.name,
            "python_version": os.sys.version.split()[0],
            "user_home_redacted": self._redact(self._user_home),
            "working_directory_redacted": self._redact(str(cwd)),
        }

    def _hardware_profile(self) -> dict[str, Any]:
        cpu_count = os.cpu_count() or 0
        disk = shutil.disk_usage(Path(self.root.anchor or self.root.drive or "C:\\"))
        return {
            "cpu_cores": cpu_count,
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
            "disk_usable_gb": round(disk.free / (1024 ** 3), 2),
        }

    def _render_markdown(self, generated_at: str, readiness: PinhoForgeReadinessSummary, tools: list[PinhoForgeToolAvailabilityItem]) -> str:
        lines = [
            "# PinhoForge Hardware Profiler Report",
            "",
            f"Generated: {generated_at}",
            "Redaction applied: true",
            "",
            "## Readiness",
            f"- Conversion: {readiness.conversion_readiness}",
            f"- Android: {readiness.android_readiness}",
            f"- Media: {readiness.media_readiness}",
            f"- Development: {readiness.development_readiness}",
            f"- Terminal: {readiness.terminal_readiness}",
            "",
            "## Tools",
        ]
        lines.extend(f"- {item.tool_id}: {item.status}" for item in tools)
        if readiness.blockers:
            lines.extend(["", "## Blockers", *[f"- {item}" for item in readiness.blockers]])
        return "\n".join(lines) + "\n"

    def _human_message(self, operation: str, readiness: PinhoForgeReadinessSummary) -> str:
        if operation == "get_tool_availability":
            return "Disponibilidade de ferramentas locais consultada em modo read-only."
        if operation == "get_readiness_summary":
            return f"Readiness calculado: android={readiness.android_readiness}, conversion={readiness.conversion_readiness}."
        if operation == "export_environment_report":
            return "Relatorio de ambiente gerado em modo read-only."
        return "Perfil de ambiente consultado em modo read-only."

    def _blocked(self, request: PinhoForgeHardwareProfilerRequest, reason_code: str, message: str) -> PinhoForgeHardwareProfilerResult:
        return PinhoForgeHardwareProfilerResult(
            request_id=request.request_id,
            operation=request.operation,
            status="blocked",
            reason_code=reason_code,
            human_message=message,
            warnings=[message],
            redaction_applied=True,
            evidence_refs=self._evidence(request),
        )

    def _evidence(self, request: PinhoForgeHardwareProfilerRequest) -> list[str]:
        return workflow_evidence_refs(
            request.metadata,
            ["provider:pinhoforge_hardware_profiler", f"request:{request.request_id}"],
        )

    def _redact(self, value: str | None) -> str | None:
        if value is None:
            return None
        result = value.replace(self._user_home, "<USER_HOME>")
        result = re.sub(r"(?i)[a-z]:\\\\users\\\\[^\\\\/\\s]+", "<USER_HOME>", result)
        result = re.sub(r"/Users/[^/\\s]+", "<USER_HOME>", result)
        result = re.sub(r"/home/[^/\\s]+", "<USER_HOME>", result)
        result = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "<REDACTED_SECRET>", result)
        result = re.sub(r"\bAIza[A-Za-z0-9_-]{8,}\b", "<REDACTED_SECRET>", result)
        result = re.sub(r"\b(?!(?:10|127)\.)(?!(?:169\.254|192\.168)\.)(?!172\.(?:1[6-9]|2\d|3[01])\.)(?:\d{1,3}\.){3}\d{1,3}\b", "<REDACTED_PUBLIC_IP>", result)
        try:
            if result and result == socket.gethostbyname(socket.gethostname()):
                result = "<REDACTED_PUBLIC_IP>"
        except OSError:
            pass
        return result
