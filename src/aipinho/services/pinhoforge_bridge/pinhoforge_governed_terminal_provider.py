from __future__ import annotations

import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.pinhoforge_bridge.governed_terminal import (
    PinhoForgeTerminalCancelRequest,
    PinhoForgeTerminalExecuteRequest,
    PinhoForgeTerminalExecuteResult,
    PinhoForgeTerminalPreviewRequest,
    PinhoForgeTerminalPreviewResult,
    PinhoForgeTerminalSessionStatus,
)
from aipinho.utils.yaml_loader import load_yaml_file


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TerminalRunner(Protocol):
    def run(self, command_line: str, cwd: str, timeout_seconds: int, cancellation: threading.Event) -> dict[str, Any]:
        ...


class SubprocessTerminalRunner:
    def run(self, command_line: str, cwd: str, timeout_seconds: int, cancellation: threading.Event) -> dict[str, Any]:
        started = time.monotonic()
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-Command", command_line],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        while True:
            if cancellation.is_set():
                process.kill()
                stdout, stderr = process.communicate(timeout=2)
                return {
                    "status": "cancelled",
                    "reason_code": "terminal_cancelled",
                    "exit_code": None,
                    "stdout": stdout or "",
                    "stderr": stderr or "",
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
            try:
                stdout, stderr = process.communicate(timeout=0.2)
                return {
                    "status": "completed" if process.returncode == 0 else "failed",
                    "reason_code": None,
                    "exit_code": process.returncode,
                    "stdout": stdout or "",
                    "stderr": stderr or "",
                    "duration_ms": int((time.monotonic() - started) * 1000),
                }
            except subprocess.TimeoutExpired:
                if time.monotonic() - started >= timeout_seconds:
                    process.kill()
                    stdout, stderr = process.communicate(timeout=2)
                    return {
                        "status": "timed_out",
                        "reason_code": "terminal_timeout",
                        "exit_code": None,
                        "stdout": stdout or "",
                        "stderr": stderr or "",
                        "duration_ms": int((time.monotonic() - started) * 1000),
                    }


_PREVIEW_STORE: dict[str, dict[str, Any]] = {}
_SESSION_STATUS_STORE: dict[str, PinhoForgeTerminalSessionStatus] = {}
_CANCELLATION_STORE: dict[str, threading.Event] = {}


class PinhoForgeGovernedTerminalProvider:
    def __init__(self, config_path: Path | None = None, *, root: Path | None = None, runner: TerminalRunner | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "providers" / "pinhoforge_governed_terminal.yaml"
        self.root = root or PATHS.project_root
        self.runner = runner or SubprocessTerminalRunner()

    def config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        return load_yaml_file(self.config_path, root=self.root)

    def preview(self, request: PinhoForgeTerminalPreviewRequest) -> PinhoForgeTerminalPreviewResult:
        session_id = request.session_id or f"terminal_session_{uuid4().hex}"
        cwd = Path(str(request.cwd)).expanduser() if request.cwd else None
        blocked_reason: tuple[str, str] | None = self._precheck(request, cwd)
        if blocked_reason is not None:
            return self._blocked_preview(request, session_id, *blocked_reason)
        rendered = str(request.command_line or self._catalog().get(request.command_id or "", {}).get("command_line") or "").strip()
        category = request.shell_category or self._classify_category(rendered)
        risk_level, risk_reason = self._classify_risk(rendered, category)
        blocked_reasons: list[str] = []
        warnings: list[str] = []
        if request.command_source != "catalog":
            warnings.append("manual_or_generated_command_requires_review")
        if request.source_scope == "registered_workspace_readonly" and category in {"write_shell", "destructive_shell"}:
            blocked_reasons.append("source_readonly_write_blocked")
        if risk_level == "high" and category in {"destructive_shell", "process_control_shell", "unknown_shell"}:
            blocked_reasons.append("terminal_dangerous_command_blocked")
        requires_approval = (
            risk_level in {"medium", "high"}
            or request.command_source != "catalog"
            or category in {"write_shell", "network_shell", "git_write_shell", "process_control_shell"}
        )
        autoapprove = risk_level == "low" and request.command_source == "catalog"
        status = "blocked" if blocked_reasons else "previewed"
        reason_code = blocked_reasons[0] if blocked_reasons else None
        preview = PinhoForgeTerminalPreviewResult(
            request_id=request.request_id,
            session_id=session_id,
            status=status,
            reason_code=reason_code,
            preview_id=f"preview_{uuid4().hex}",
            rendered_command=self._redact_output(rendered),
            cwd_redacted=self._redact_path(cwd) if cwd else None,
            source_scope=request.source_scope,
            shell_category=category,
            risk_level=risk_level,
            risk_score=self._risk_score(risk_level),
            risk_reasons=[risk_reason],
            requires_approval=requires_approval,
            autoapprove_eligible=autoapprove,
            blocked_reasons=blocked_reasons,
            warnings=warnings,
            errors=[risk_reason] if blocked_reasons else [],
            execution_enabled=not blocked_reasons,
            policy_notes=["preview_required", "cwd_validated", f"shell_category:{category}"],
            evidence_refs=["provider:pinhoforge_governed_terminal", f"preview:{request.request_id}"],
        )
        _PREVIEW_STORE[preview.preview_id] = {
            "preview": preview,
            "command_line": rendered,
            "cwd": str(cwd),
            "timeout_seconds": request.timeout_seconds,
            "output_limit_chars": request.output_limit_kb * 1024,
        }
        _SESSION_STATUS_STORE[session_id] = PinhoForgeTerminalSessionStatus(
            request_id=request.request_id,
            session_id=session_id,
            status=status,
            reason_code=reason_code,
            cwd_redacted=preview.cwd_redacted,
            risk_level=preview.risk_level,
            warnings=preview.warnings,
            errors=preview.errors,
            evidence_refs=preview.evidence_refs,
        )
        return preview

    def execute(self, request: PinhoForgeTerminalExecuteRequest) -> PinhoForgeTerminalExecuteResult:
        context = _PREVIEW_STORE.get(request.preview_id)
        if context is None:
            return PinhoForgeTerminalExecuteResult(
                request_id=request.request_id,
                preview_id=request.preview_id,
                session_id="unknown",
                execution_id="exec_missing_preview",
                status="blocked",
                reason_code="terminal_no_preview_blocked",
                errors=["Preview obrigatorio antes da execucao."],
            )
        preview: PinhoForgeTerminalPreviewResult = context["preview"]
        if not preview.execution_enabled:
            return PinhoForgeTerminalExecuteResult(
                request_id=request.request_id,
                preview_id=request.preview_id,
                session_id=preview.session_id,
                execution_id="exec_preview_blocked",
                status="blocked",
                reason_code=preview.reason_code or "terminal_preview_blocked",
                warnings=preview.warnings,
                errors=preview.errors,
            )
        if preview.requires_approval and not request.approval_id and not request.confirmed:
            return PinhoForgeTerminalExecuteResult(
                request_id=request.request_id,
                preview_id=request.preview_id,
                session_id=preview.session_id,
                execution_id="exec_approval_required",
                status="blocked",
                reason_code="terminal_approval_required",
                errors=["Execucao requer approval ou confirmacao explicita."],
                evidence_refs=preview.evidence_refs,
            )
        execution_id = f"terminal_exec_{uuid4().hex}"
        cancellation = threading.Event()
        _CANCELLATION_STORE[execution_id] = cancellation
        _CANCELLATION_STORE[preview.session_id] = cancellation
        started_at = _utc_now_iso()
        _SESSION_STATUS_STORE[preview.session_id] = PinhoForgeTerminalSessionStatus(
            request_id=request.request_id,
            session_id=preview.session_id,
            execution_id=execution_id,
            status="running",
            cwd_redacted=preview.cwd_redacted,
            risk_level=preview.risk_level,
            started_at=started_at,
            evidence_refs=preview.evidence_refs,
        )
        raw = self.runner.run(
            command_line=str(context["command_line"]),
            cwd=str(context["cwd"]),
            timeout_seconds=request.timeout_seconds or int(context["timeout_seconds"]),
            cancellation=cancellation,
        )
        completed_at = _utc_now_iso()
        stdout, stdout_truncated = self._limit_text(self._redact_output(str(raw.get("stdout") or "")), request.output_limit_kb or int(context["output_limit_chars"]) // 1024)
        stderr, stderr_truncated = self._limit_text(self._redact_output(str(raw.get("stderr") or "")), request.output_limit_kb or int(context["output_limit_chars"]) // 1024)
        report_json = {
            "status": raw.get("status"),
            "exit_code": raw.get("exit_code"),
            "shell_category": preview.shell_category,
            "risk_level": preview.risk_level,
            "duration_ms": raw.get("duration_ms", 0),
        }
        report_markdown = "\n".join(
            [
                "# Bridge Governed Terminal Execution",
                f"Command: {preview.rendered_command or ''}",
                f"CWD: {preview.cwd_redacted or ''}",
                f"Status: {raw.get('status')}",
                f"Exit code: {raw.get('exit_code')}",
                "## Stdout",
                stdout,
                "## Stderr",
                stderr,
            ]
        )
        output_artifacts = self._expected_outputs(Path(str(context["cwd"])), request.expected_outputs)
        result = PinhoForgeTerminalExecuteResult(
            request_id=request.request_id,
            preview_id=request.preview_id,
            session_id=preview.session_id,
            execution_id=execution_id,
            status=str(raw.get("status") or "failed"),
            reason_code=raw.get("reason_code"),
            exit_code=raw.get("exit_code"),
            stdout=stdout,
            stderr=stderr,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated,
            duration_ms=int(raw.get("duration_ms") or 0),
            output_artifacts=output_artifacts,
            report_markdown=report_markdown,
            report_json=report_json,
            warnings=["approval_consumed"] if request.approval_id else [],
            errors=[] if str(raw.get("status")) in {"completed", "cancelled"} else [str(raw.get("reason_code") or "terminal_execution_failed")],
            evidence_refs=preview.evidence_refs + [f"execution:{execution_id}"],
            started_at=started_at,
            completed_at=completed_at,
        )
        _SESSION_STATUS_STORE[preview.session_id] = PinhoForgeTerminalSessionStatus(
            request_id=request.request_id,
            session_id=preview.session_id,
            execution_id=execution_id,
            status=result.status,
            reason_code=result.reason_code,
            cwd_redacted=preview.cwd_redacted,
            risk_level=preview.risk_level,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=result.duration_ms,
            warnings=result.warnings,
            errors=result.errors,
            evidence_refs=result.evidence_refs,
        )
        _CANCELLATION_STORE.pop(execution_id, None)
        _CANCELLATION_STORE.pop(preview.session_id, None)
        return result

    def cancel_execution(self, request: PinhoForgeTerminalCancelRequest) -> PinhoForgeTerminalSessionStatus:
        key = request.execution_id or request.session_id
        if not key:
            return PinhoForgeTerminalSessionStatus(
                request_id=request.request_id,
                session_id="unknown",
                status="blocked",
                reason_code="terminal_cancel_target_missing",
                errors=["execution_id ou session_id obrigatorio."],
            )
        cancellation = _CANCELLATION_STORE.get(key)
        existing = _SESSION_STATUS_STORE.get(request.session_id or key)
        if cancellation is None or existing is None:
            return PinhoForgeTerminalSessionStatus(
                request_id=request.request_id,
                session_id=request.session_id or key,
                execution_id=request.execution_id,
                status="blocked",
                reason_code="terminal_session_not_found",
                errors=["Sessao de terminal nao encontrada."],
            )
        cancellation.set()
        updated = existing.model_copy(update={"status": "cancelling", "reason_code": "terminal_cancel_requested"})
        _SESSION_STATUS_STORE[updated.session_id] = updated
        return updated

    def session_status(self, request_id: str, session_id: str) -> PinhoForgeTerminalSessionStatus:
        return _SESSION_STATUS_STORE.get(session_id) or PinhoForgeTerminalSessionStatus(
            request_id=request_id,
            session_id=session_id,
            status="blocked",
            reason_code="terminal_session_not_found",
            errors=["Sessao de terminal nao encontrada."],
        )

    def _precheck(self, request: PinhoForgeTerminalPreviewRequest, cwd: Path | None) -> tuple[str, str] | None:
        allowed_scopes = set(str(item) for item in (self.config().get("provider") or {}).get("allowed_source_scopes") or [])
        if request.source_scope not in allowed_scopes:
            return "terminal_unknown_scope_blocked", "Escopo de origem nao autorizado para terminal governado."
        if cwd is None:
            return "terminal_missing_cwd", "CWD obrigatorio."
        if not cwd.exists() or not cwd.is_dir():
            return "terminal_invalid_cwd", "CWD inexistente ou invalido."
        command_line = str(request.command_line or self._catalog().get(request.command_id or "", {}).get("command_line") or "").strip()
        if not command_line:
            return "terminal_command_not_found", "Comando nao encontrado ou invalido."
        if self._contains_secret(command_line):
            return "terminal_secret_in_command_blocked", "Comando contem token, segredo ou credencial."
        return None

    def _classify_category(self, command_line: str) -> str:
        lowered = command_line.lower()
        if any(token in lowered for token in ("remove-item", "del ", "format ", "stop-process", "kill ")):
            return "destructive_shell"
        if any(token in lowered for token in ("git push", "git commit", "git reset", "git clean")):
            return "git_write_shell"
        if any(token in lowered for token in ("invoke-webrequest", "curl ", "wget ", "http://", "https://")):
            return "network_shell"
        if any(token in lowered for token in ("set-content", "out-file", "copy-item", "move-item", "mkdir", "new-item", "compress-archive")):
            return "write_shell"
        if any(token in lowered for token in ("pytest", "gradle", "build", "test", "python -m")):
            return "test_shell"
        if any(token in lowered for token in ("get-childitem", "test-path", "measure-object", "sort-object", "select-object")):
            return "readonly_shell"
        return "unknown_shell"

    def _classify_risk(self, command_line: str, category: str) -> tuple[str, str]:
        if category in {"destructive_shell", "process_control_shell", "git_write_shell"}:
            return "high", "Comando perigoso ou irreversivel."
        if category in {"write_shell", "network_shell", "unknown_shell"}:
            return "medium", "Comando requer revisao ou approval governado."
        if category in {"test_shell", "build_shell", "readonly_shell"}:
            return "low", "Comando classificado como seguro para execucao governada."
        return "medium", "Categoria de shell exige validacao."

    def _risk_score(self, risk_level: str) -> int:
        return {"low": 10, "medium": 45, "high": 85}.get(risk_level, 50)

    def _blocked_preview(self, request: PinhoForgeTerminalPreviewRequest, session_id: str, reason_code: str, message: str) -> PinhoForgeTerminalPreviewResult:
        result = PinhoForgeTerminalPreviewResult(
            request_id=request.request_id,
            session_id=session_id,
            status="blocked",
            reason_code=reason_code,
            preview_id=f"preview_{uuid4().hex}",
            source_scope=request.source_scope,
            shell_category=request.shell_category or "unknown_shell",
            risk_level="high",
            risk_score=95,
            blocked_reasons=[reason_code],
            errors=[message],
            execution_enabled=False,
            evidence_refs=["provider:pinhoforge_governed_terminal", f"preview:{request.request_id}"],
        )
        _SESSION_STATUS_STORE[session_id] = PinhoForgeTerminalSessionStatus(
            request_id=request.request_id,
            session_id=session_id,
            status="blocked",
            reason_code=reason_code,
            errors=[message],
            evidence_refs=result.evidence_refs,
        )
        return result

    def _catalog(self) -> dict[str, dict[str, str]]:
        provider = self.config().get("provider") or {}
        return {str(item.get("command_id")): dict(item) for item in provider.get("catalog_commands") or []}

    def _expected_outputs(self, cwd: Path, expected_outputs: list[str]) -> list[dict[str, Any]]:
        artifacts: list[dict[str, Any]] = []
        for item in expected_outputs:
            candidate = (cwd / item).resolve()
            if not str(candidate).startswith(str(cwd.resolve())):
                continue
            if candidate.exists() and candidate.is_file():
                artifacts.append(
                    {
                        "filename": candidate.name,
                        "path": str(candidate),
                        "path_redacted": self._redact_path(candidate),
                        "size_bytes": candidate.stat().st_size,
                        "content_type": "text/plain",
                        "status": "ready",
                        "requires_token": True,
                    }
                )
        return artifacts

    def _limit_text(self, text: str, output_limit_kb: int) -> tuple[str, bool]:
        max_chars = max(1024, output_limit_kb * 1024)
        if len(text) <= max_chars:
            return text, False
        return text[:max_chars] + "\n[truncated]", True

    def _contains_secret(self, command_line: str) -> bool:
        return bool(re.search(r"(?i)(bearer\s+[a-z0-9._~+/-]+|sk-[a-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}|token=|api_key=)", command_line))

    def _redact_output(self, text: str) -> str:
        text = re.sub(r"(?i)(bearer\s+[a-z0-9._~+/-]+|sk-[a-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}|token=|api_key=)", "<redacted>", text)
        return re.sub(r"(?i)c:\\users\\[^\\]+", lambda _: "C:\\Users\\<user>", text)

    def _redact_path(self, path: Path) -> str:
        return self._redact_output(str(path))
