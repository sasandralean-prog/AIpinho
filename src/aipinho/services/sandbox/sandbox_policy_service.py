from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.sandbox import SandboxPolicyDecision
from aipinho.services.sandbox.sandbox_paths import is_relative_path_safe, is_within, sandbox_root
from aipinho.utils.yaml_loader import load_yaml_file


class SandboxPolicyService:
    SECRET_PATTERN = re.compile(
        r"(Bearer\s+[A-Za-z0-9._~+/-]{12,}|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,})",
        re.IGNORECASE,
    )
    def __init__(self, *, policy_path: Path | None = None) -> None:
        self.policy_path = policy_path or PATHS.config_root / "sandbox" / "sandbox_policy.yaml"

    def policy(self) -> dict[str, Any]:
        data = load_yaml_file(self.policy_path, critical=False, root=PATHS.config_root)
        return data if data else self._default_policy()

    def status(self) -> dict[str, Any]:
        policy = self.policy()
        return {
            "status": "ok" if policy.get("enabled", True) else "disabled",
            "version": str(policy.get("version", 1)),
            "root_path_sanitized": str(sandbox_root()),
            "allowed_shell_categories": policy.get("allowed_shell_categories", []),
            "blocked_shell_patterns": policy.get("blocked_shell_patterns", []),
            "cleanup_requires_preview": bool(policy.get("cleanup", {}).get("requires_preview", True)),
        }

    def allow_path(self, *, workspace_root: Path, relative_path: str, operation: str) -> SandboxPolicyDecision:
        if not self.policy().get("enabled", True):
            return self._decision(False, "sandbox_disabled", "Sandbox governado esta desabilitado.")
        if not is_relative_path_safe(relative_path):
            return self._decision(False, "sandbox_path_traversal_blocked", "O caminho solicitado tenta sair da caixa de areia.")
        root = sandbox_root()
        candidate = (workspace_root / relative_path).resolve(strict=False)
        if not is_within(candidate, root):
            reason = "sandbox_escape_blocked" if operation.startswith("read") else "sandbox_outside_write_blocked"
            return self._decision(False, reason, "A operacao foi bloqueada porque sairia do sandbox governado.")
        if not is_within(candidate, workspace_root):
            return self._decision(False, "sandbox_escape_blocked", "A operacao foi bloqueada porque sairia do workspace sandbox.")
        if candidate.exists() and candidate.is_symlink():
            try:
                target = candidate.resolve(strict=True)
            except OSError:
                return self._decision(False, "sandbox_symlink_escape_blocked", "Symlink invalido bloqueado no sandbox.")
            if not is_within(target, root):
                return self._decision(False, "sandbox_symlink_escape_blocked", "Symlink/junction para fora do sandbox bloqueado.")
        if operation == "delete-safe" and relative_path.strip() in {"", "."}:
            return self._decision(False, "sandbox_destructive_command_blocked", "Delete do root do workspace sandbox foi bloqueado.")
        return self._decision(True, "sandbox_allowed_low_risk", "Operacao permitida dentro do sandbox governado.")

    def allow_shell(self, *, workspace_root: Path, cwd_relative: str, command: str, category: str | None) -> SandboxPolicyDecision:
        path_decision = self.allow_path(workspace_root=workspace_root, relative_path=cwd_relative or ".", operation="shell")
        if not path_decision.allowed:
            return path_decision
        policy = self.policy()
        normalized = command.casefold()
        for pattern in policy.get("blocked_shell_patterns", []):
            if re.search(str(pattern), normalized):
                pattern_text = str(pattern).casefold()
                reason = "sandbox_network_blocked" if any(token in pattern_text for token in ("curl", "wget", "invoke-webrequest", "irm", "iwr")) else "sandbox_destructive_command_blocked"
                return self._decision(False, reason, "Comando bloqueado pela policy de shell do sandbox.")
        allowed = set(str(item) for item in policy.get("allowed_shell_categories", []))
        shell_category = category or self.classify_shell(command)
        if shell_category not in allowed:
            return self._decision(False, "sandbox_destructive_command_blocked", "Categoria de shell nao permitida no sandbox.")
        return self._decision(True, "sandbox_shell_allowed", "Shell seguro permitido dentro do sandbox.")

    def classify_shell(self, command: str) -> str:
        lowered = command.casefold().strip()
        if any(token in lowered for token in ["pytest", "python -m pytest", "gradlew", "npm test", "cargo test"]):
            return "test_shell"
        if any(token in lowered for token in ["python -m py_compile", "tsc", "npm run build", "gradlew assemble"]):
            return "build_shell"
        if lowered.startswith(("dir", "ls", "pwd", "type ", "get-content", "python --version", "node --version")):
            return "readonly_shell"
        return "unknown_shell"

    def allow_artifact(self, *, estimated_size: int) -> SandboxPolicyDecision:
        max_size = int(self.policy().get("artifact", {}).get("max_bytes", 200_000_000))
        if estimated_size > max_size:
            return self._decision(False, "sandbox_artifact_too_large", "Artifact excede o tamanho permitido pela policy do sandbox.")
        return self._decision(True, "sandbox_artifact_export_allowed", "Exportacao de artifact permitida para conteudo do sandbox.")

    def allow_content(self, content: str) -> SandboxPolicyDecision:
        if self.SECRET_PATTERN.search(content):
            return self._decision(False, "sandbox_secret_access_blocked", "Conteudo com risco de segredo foi bloqueado no sandbox.")
        return self._decision(True, "sandbox_allowed_low_risk", "Conteudo permitido pela policy do sandbox.")

    def allow_cleanup_apply(self, *, has_preview_id: bool) -> SandboxPolicyDecision:
        if self.policy().get("cleanup", {}).get("requires_preview", True) and not has_preview_id:
            return self._decision(False, "sandbox_cleanup_requires_preview", "Limpeza do sandbox exige preview antes de aplicar.")
        return self._decision(True, "sandbox_cleanup_preview_allowed", "Limpeza governada permitida apos preview.")

    def _decision(self, allowed: bool, reason_code: str, human_reason: str) -> SandboxPolicyDecision:
        return SandboxPolicyDecision(
            allowed=allowed,
            reason_code=reason_code,
            human_reason=human_reason,
            risk_level="low" if allowed else "medium",
            safe_alternative=None if allowed else "Use um caminho relativo dentro do sandbox ou reduza o risco da operacao.",
            evidence_refs=[f"sandbox_policy:{reason_code}"],
        )

    def _default_policy(self) -> dict[str, Any]:
        return {
            "version": 1,
            "enabled": True,
            "allowed_shell_categories": ["readonly_shell", "test_shell", "build_shell", "package_shell"],
            "blocked_shell_patterns": [
                r"\bdel\b|\brm\b|\bformat\b|\bshutdown\b|\brestart-computer\b",
                r"\bgit\s+push\b|\bgit\s+commit\b",
                r"\bcurl\b|\bwget\b|\binvoke-webrequest\b|\birm\b|\biwr\b",
            ],
            "artifact": {"max_bytes": 200_000_000},
            "cleanup": {"requires_preview": True},
        }
