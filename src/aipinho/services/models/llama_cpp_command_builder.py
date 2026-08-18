from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class LlamaCppCommand:
    argv: list[str]
    sanitized: str
    warnings: list[str] = field(default_factory=list)


class LlamaCppCommandBuilder:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "llama_cpp_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def build(
        self,
        *,
        executable_path: str,
        model_path: str,
        prompt: str,
        ctx_size: int | None = None,
        n_predict: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        threads: int | None = None,
        custom_args: list[str] | None = None,
    ) -> LlamaCppCommand:
        llama = self.config.get("llama_cpp", {}) if isinstance(self.config.get("llama_cpp", {}), dict) else {}
        runtime = self.config.get("runtime", {}) if isinstance(self.config.get("runtime", {}), dict) else {}
        if llama.get("use_shell", False):
            raise ValueError("shell_execution_blocked")
        default_args = [str(arg) for arg in runtime.get("default_args", []) or []]
        if custom_args and not llama.get("allow_custom_args", False):
            raise ValueError("custom_args_blocked")
        blocked_args = set(llama.get("blocked_args", []) or [])
        allowed_args = set(llama.get("allowed_args", []) or [])
        extra_args = [*default_args, *(custom_args or [])]
        if any(arg in blocked_args for arg in extra_args):
            raise ValueError("blocked_llama_arg")
        if allowed_args and any(arg.startswith("-") and arg not in allowed_args for arg in extra_args):
            raise ValueError("llama_arg_not_allowed")
        resolved_ctx = min(int(ctx_size or runtime.get("default_ctx_size", 2048)), int(runtime.get("max_ctx_size", 4096)))
        resolved_predict = min(int(n_predict or runtime.get("default_n_predict", 256)), int(runtime.get("max_n_predict", 1024)))
        argv = [
            executable_path,
            "--model",
            model_path,
            "--prompt",
            prompt,
            "--ctx-size",
            str(resolved_ctx),
            "--n-predict",
            str(resolved_predict),
            "--temp",
            str(temperature if temperature is not None else runtime.get("default_temperature", 0.2)),
            "--top-p",
            str(top_p if top_p is not None else runtime.get("default_top_p", 0.9)),
        ]
        if threads or runtime.get("default_threads"):
            argv.extend(["--threads", str(threads or runtime.get("default_threads"))])
        if extra_args:
            argv.extend(extra_args)
        sanitized = " ".join([executable_path, "--model", model_path, "--prompt", f"<prompt chars={len(prompt)}>", "--ctx-size", str(resolved_ctx), "--n-predict", str(resolved_predict), *extra_args])
        return LlamaCppCommand(argv=argv, sanitized=sanitized, warnings=[])

    def status(self) -> dict[str, object]:
        llama = self.config.get("llama_cpp", {}) if isinstance(self.config.get("llama_cpp", {}), dict) else {}
        return {"status": "ok", "service": "llama_cpp_command_builder", "use_shell": bool(llama.get("use_shell", False)), "allow_custom_args": bool(llama.get("allow_custom_args", False))}
