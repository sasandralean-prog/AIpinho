from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from aipinho.services.codex_agent.codex_agent_config_service import CodexAgentRuntimeConfig
from aipinho.services.security.secret_guard_service import SecretGuardService


@dataclass(frozen=True)
class CodexCliResult:
    status: str
    text: str
    cli_status: str
    error_code: str | None = None
    latency_ms: int | None = None
    event_count: int = 0


@dataclass(frozen=True)
class CodexCliProposalResult:
    result: CodexCliResult
    payload: dict[str, object] | None = None


class FakeCodexCliAdapter:
    def run_prompt(self, *, prompt: str, config: CodexAgentRuntimeConfig, workdir: str | None = None) -> CodexCliResult:
        return CodexCliResult(status="completed", text=f"Codex Agent fake respondeu em modo governado: {prompt[:240]}", cli_status="fake_adapter")

    def run_governed_proposal(
        self,
        *,
        prompt: str,
        config: CodexAgentRuntimeConfig,
        workdir: str,
        output_schema_path: Path,
    ) -> CodexCliProposalResult:
        payload = {"objective": prompt, "actions": []}
        return CodexCliProposalResult(
            result=CodexCliResult(
                status="completed",
                text=json.dumps(payload, ensure_ascii=False),
                cli_status="fake_adapter",
            ),
            payload=payload,
        )


class CodexCliAdapter:
    def __init__(self, cli_status: str, secret_guard: SecretGuardService | None = None) -> None:
        self.cli_status = cli_status
        self.secret_guard = secret_guard or SecretGuardService()

    def run_prompt(self, *, prompt: str, config: CodexAgentRuntimeConfig, workdir: str | None = None) -> CodexCliResult:
        return self._run_prompt(prompt=prompt, config=config, workdir=workdir)

    def run_governed_proposal(
        self,
        *,
        prompt: str,
        config: CodexAgentRuntimeConfig,
        workdir: str,
        output_schema_path: Path,
    ) -> CodexCliProposalResult:
        result = self._run_prompt(
            prompt=(
                "Proponha apenas acoes governadas para cumprir o pedido. "
                "Nao execute shell, nao altere arquivos e nao omita efeitos colaterais. "
                "Use paths dentro do workspace informado. Para shell, forneca argv sem "
                "metacaracteres; para arquivos, forneca conteudo final completo.\n\n"
                f"PEDIDO:\n{prompt}"
            ),
            config=config,
            workdir=workdir,
            output_schema_path=output_schema_path,
        )
        if result.status != "completed":
            return CodexCliProposalResult(result=result)
        try:
            payload = json.loads(result.text)
        except json.JSONDecodeError:
            failed = CodexCliResult(
                status="failed",
                text="Codex CLI retornou uma proposta que nao e JSON valido.",
                cli_status="cli_invalid_structured_output",
                error_code="codex_cli_invalid_structured_output",
                latency_ms=result.latency_ms,
                event_count=result.event_count,
            )
            return CodexCliProposalResult(result=failed)
        if not isinstance(payload, dict):
            failed = CodexCliResult(
                status="failed",
                text="Codex CLI retornou uma proposta estruturada invalida.",
                cli_status="cli_invalid_structured_output",
                error_code="codex_cli_invalid_structured_output",
                latency_ms=result.latency_ms,
                event_count=result.event_count,
            )
            return CodexCliProposalResult(result=failed)
        return CodexCliProposalResult(result=result, payload=payload)

    def _run_prompt(
        self,
        *,
        prompt: str,
        config: CodexAgentRuntimeConfig,
        workdir: str | None = None,
        output_schema_path: Path | None = None,
    ) -> CodexCliResult:
        if not config.enabled:
            return CodexCliResult(status="blocked", text="Codex Agent esta desabilitado por configuracao.", cli_status=self.cli_status, error_code="codex_agent_disabled")
        if self.cli_status in {"missing_cli", "cli_inaccessible", "cli_timeout", "cli_probe_failed", "cli_present_but_unhealthy"}:
            return CodexCliResult(status="failed", text="Codex CLI nao esta disponivel/autenticado para execucao neste ambiente.", cli_status=self.cli_status, error_code=self.cli_status)
        cwd = Path(workdir or config.default_workdir).expanduser().resolve()
        command = [
            config.cli_path,
            "--ask-for-approval",
            "never",
            "exec",
            "--json",
        ]
        if output_schema_path is not None:
            command.extend(["--output-schema", str(output_schema_path)])
        command.extend([
            "--sandbox",
            "read-only",
            "--cd",
            str(cwd),
        ])
        if not _is_git_worktree(cwd):
            command.append("--skip-git-repo-check")
        command.append(prompt)
        started = time.monotonic()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=config.timeout_seconds,
                check=False,
                creationflags=creationflags,
            )
        except subprocess.TimeoutExpired:
            return CodexCliResult(
                status="failed",
                text="Codex CLI excedeu o tempo limite configurado.",
                cli_status="cli_runtime_timeout",
                error_code="codex_cli_timeout",
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        except PermissionError:
            return CodexCliResult(status="failed", text="Codex CLI nao pode ser executada neste ambiente.", cli_status="cli_inaccessible", error_code="permission_denied")
        except OSError:
            return CodexCliResult(status="failed", text="Codex CLI falhou ao iniciar.", cli_status="cli_start_failed", error_code="codex_cli_start_failed")

        latency_ms = int((time.monotonic() - started) * 1000)
        final_text = ""
        event_count = 0
        terminal_error = ""
        for line in completed.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_count += 1
            item = event.get("item") if isinstance(event, dict) else None
            if isinstance(item, dict) and item.get("type") == "agent_message":
                final_text = str(item.get("text") or final_text)
            if event.get("type") in {"turn.failed", "error"}:
                terminal_error = str(event.get("message") or event.get("error") or "codex_cli_turn_failed")

        if completed.returncode != 0:
            stderr_summary = self._sanitize_error(completed.stderr)
            return CodexCliResult(
                status="failed",
                text=terminal_error or stderr_summary or "Codex CLI encerrou sem concluir a resposta.",
                cli_status="cli_runtime_failed",
                error_code=f"codex_cli_exit_{completed.returncode}",
                latency_ms=latency_ms,
                event_count=event_count,
            )
        if not final_text.strip():
            return CodexCliResult(
                status="failed",
                text="Codex CLI concluiu sem mensagem final utilizavel.",
                cli_status="cli_missing_final_message",
                error_code="codex_cli_missing_final_message",
                latency_ms=latency_ms,
                event_count=event_count,
            )
        return CodexCliResult(
            status="completed",
            text=final_text,
            cli_status="ready",
            latency_ms=latency_ms,
            event_count=event_count,
        )

    def _sanitize_error(self, stderr: str) -> str:
        redacted, _ = self.secret_guard.redact(stderr or "")
        meaningful_lines = [line.strip() for line in redacted.splitlines() if line.strip()]
        return " ".join(meaningful_lines)[-1000:]


def _is_git_worktree(path: Path) -> bool:
    return any((candidate / ".git").exists() for candidate in (path, *path.parents))
