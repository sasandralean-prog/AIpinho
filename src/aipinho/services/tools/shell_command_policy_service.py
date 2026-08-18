from __future__ import annotations

import hashlib
import shlex
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.tools.shell_command_policy import ShellCommandClassification
from aipinho.utils.yaml_loader import load_yaml_file


class ShellCommandPolicyService:
    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = policy_path or PATHS.config_root / "policies" / "governed_tool_execution_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, critical=True, root=self.policy_path.parent)

    def classify(self, *, argv: list[str] | None = None, command: str | None = None, working_dir: str | None = None) -> ShellCommandClassification:
        normalized = self._normalized(argv=argv, command=command)
        try:
            tokens = argv or shlex.split(command or "", posix=False) or [""]
        except ValueError:
            tokens = [""]
        executable = Path(tokens[0].strip('"')).name.lower() if normalized else ""
        category, reasons = self._category(normalized, executable)
        shell_policy = self.policy.get("shell", {}) if isinstance(self.policy, dict) else {}
        category_policy = shell_policy.get("category_policy", {}) if isinstance(shell_policy.get("category_policy"), dict) else {}
        blocked_categories = {str(item) for item in category_policy.get("blocked_categories", []) or []}
        approval_categories = {str(item) for item in category_policy.get("approval_required_categories", []) or []}
        decision = "blocked" if category in blocked_categories else ("approval_required" if category in approval_categories else "allowed")
        risk = self._risk(category)
        return ShellCommandClassification(
            command_id=self._command_id(normalized, working_dir),
            normalized_command=normalized,
            working_dir=working_dir,
            category=category,  # type: ignore[arg-type]
            policy_decision=decision,
            risk_score=risk,
            expected_side_effects=self._expected_side_effects(category),
            reasons=reasons or [f"category:{category}"],
            trace=[{
                "stage": "shell_command_policy",
                "decision": decision,
                "reason": f"category:{category}",
                "source": str(self.policy_path),
                "data": {"executable": executable, "category": category, "risk_score": risk},
            }],
        )

    def _category(self, normalized: str, executable: str) -> tuple[str, list[str]]:
        shell_policy = self.policy.get("shell", {}) if isinstance(self.policy, dict) else {}
        categories = shell_policy.get("categories", {}) if isinstance(shell_policy.get("categories"), dict) else {}
        lowered = normalized.lower()
        for category, rules in categories.items():
            if not isinstance(rules, dict):
                continue
            executables = {str(item).lower() for item in rules.get("executables", []) or []}
            tokens = [str(item).lower() for item in rules.get("tokens", []) or []]
            if executable and executable in executables:
                return str(category), [f"executable:{executable}"]
            if tokens and any(token in lowered for token in tokens):
                return str(category), [f"token:{token}" for token in tokens if token in lowered][:5]
        return "unknown_shell", ["no_shell_category_match"]

    def _normalized(self, *, argv: list[str] | None, command: str | None) -> str:
        if argv:
            return " ".join(str(item) for item in argv)
        return str(command or "").strip()

    def _risk(self, category: str) -> str:
        if category in {"readonly_shell", "git_read_shell"}:
            return "low"
        if category in {"test_shell", "build_shell", "package_shell", "network_shell", "process_control_shell"}:
            return "medium"
        if category in {"write_shell", "unknown_shell"}:
            return "high"
        return "critical"

    def _expected_side_effects(self, category: str) -> list[str]:
        if category in {"readonly_shell", "git_read_shell"}:
            return []
        return [category]

    def _command_id(self, normalized: str, working_dir: str | None) -> str:
        digest = hashlib.sha256(f"{working_dir or ''}\n{normalized}".encode("utf-8")).hexdigest()[:16]
        return f"cmd_{digest}"

    def status(self) -> dict[str, object]:
        shell_policy = self.policy.get("shell", {}) if isinstance(self.policy, dict) else {}
        return {
            "status": "ok",
            "service": "shell_command_policy",
            "categories": sorted((shell_policy.get("categories", {}) or {}).keys()),
        }
