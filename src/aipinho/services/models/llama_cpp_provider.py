from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse, ModelUsage
from aipinho.services.models.llama_cpp_command_builder import LlamaCppCommandBuilder
from aipinho.services.models.llama_cpp_status_service import LlamaCppStatusService
from aipinho.services.models.local_model_path_service import LocalModelPathService
from aipinho.services.models.model_invocation_audit_service import ModelInvocationAuditService
from aipinho.services.models.model_output_sanitizer import ModelOutputSanitizer
from aipinho.services.models.model_path_validator import ModelPathValidator
from aipinho.services.models.model_process_runner import ModelProcessRunner
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.model_runtime_estimator import ModelRuntimeEstimator
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.services.models.real_inference_gate_service import RealInferenceGateService
from aipinho.services.prompts.output_contract_builder import OutputContractBuilder


class LlamaCppProvider:
    def __init__(
        self,
        model_registry: ModelRegistryService | None = None,
        provider_registry: ProviderRegistryService | None = None,
        path_service: LocalModelPathService | None = None,
        validator: ModelPathValidator | None = None,
        gate: RealInferenceGateService | None = None,
        command_builder: LlamaCppCommandBuilder | None = None,
        runner: ModelProcessRunner | None = None,
        sanitizer: ModelOutputSanitizer | None = None,
        estimator: ModelRuntimeEstimator | None = None,
        output_contract_builder: OutputContractBuilder | None = None,
        audit: ModelInvocationAuditService | None = None,
    ) -> None:
        self.model_registry = model_registry or ModelRegistryService()
        self.provider_registry = provider_registry or ProviderRegistryService()
        self.path_service = path_service or LocalModelPathService()
        self.validator = validator or ModelPathValidator(self.path_service)
        self.gate = gate or RealInferenceGateService()
        self.command_builder = command_builder or LlamaCppCommandBuilder()
        self.runner = runner or ModelProcessRunner()
        self.sanitizer = sanitizer or ModelOutputSanitizer()
        self.estimator = estimator or ModelRuntimeEstimator()
        self.output_contract_builder = output_contract_builder or OutputContractBuilder()
        self.audit = audit or ModelInvocationAuditService()

    def status(self) -> dict[str, object]:
        return LlamaCppStatusService().status().model_dump()

    def validate_environment(self, *, executable_path: str | None = None, model_path: str | None = None, provider_enabled: bool | None = None, model_enabled: bool | None = None) -> dict[str, object]:
        provider = self.provider_registry.get_provider("llama_cpp.local")
        model = self.model_registry.get_model("llama.local.placeholder")
        executable = executable_path if executable_path is not None else (provider.executable_path if provider else None)
        local_entry = self.path_service.get_by_model_id("llama.local.placeholder")
        resolved_model_path = model_path if model_path is not None else (model.model_path if model and model.model_path else (local_entry.path if local_entry else None))
        executable_validation = self.validator.validate_executable_path(executable, provider_enabled=bool(provider_enabled if provider_enabled is not None else provider and provider.enabled))
        model_validation = self.validator.validate_model_path(resolved_model_path, model_enabled=bool(model_enabled if model_enabled is not None else model and model.enabled))
        return {
            "status": "blocked" if executable_validation.status == "blocked" or model_validation.status == "blocked" else "degraded",
            "provider_id": "llama_cpp.local",
            "model_id": "llama.local.placeholder",
            "executable": executable_validation.model_dump(),
            "model": model_validation.model_dump(),
        }

    def estimate(self, request: ModelRequest | None = None, *, model_path: str | None = None, ctx_size: int = 2048, n_predict: int = 256) -> dict[str, object]:
        size_bytes = None
        if model_path:
            validation = self.validator.validate_model_path(model_path, model_enabled=False)
            size_bytes = validation.size_bytes
        estimate = self.estimator.estimate(model_size_bytes=size_bytes, ctx_size=ctx_size, n_predict=n_predict)
        return estimate.model_dump()

    def invoke_preview(self, request: ModelRequest) -> dict[str, object]:
        prepared = self._prepare(request)
        gate_decision = prepared["gate_decision"]
        command_preview = None
        warnings = []
        if gate_decision.allowed:
            try:
                prompt = self._request_prompt(request)
                command = self.command_builder.build(
                    executable_path=str(prepared["executable_path"]),
                    model_path=str(prepared["model_path"]),
                    prompt=prompt,
                    ctx_size=int(request.metadata.get("ctx_size", 2048) or 2048),
                    n_predict=request.generation_config.max_tokens,
                    temperature=request.generation_config.temperature,
                    top_p=request.generation_config.top_p,
                )
                command_preview = {"argv_length": len(command.argv), "sanitized": command.sanitized, "warnings": command.warnings}
            except Exception as exc:  # preview should degrade, not execute/fail hard
                warnings.append(str(exc))
        estimate = self.estimator.estimate(
            model_size_bytes=prepared["model_validation"].size_bytes,
            ctx_size=int(request.metadata.get("ctx_size", 2048) or 2048),
            n_predict=request.generation_config.max_tokens,
        )
        return {
            "status": "ok",
            "invokes_model": False,
            "process_started": False,
            "gate_decision": gate_decision.model_dump(),
            "command_preview": command_preview,
            "runtime_estimate": estimate.model_dump(),
            "warnings": warnings,
        }

    def invoke(self, request: ModelRequest) -> ModelResponse:
        prepared = self._prepare(request)
        gate_decision = prepared["gate_decision"]
        trace = [*gate_decision.trace]
        if not gate_decision.allowed:
            return ModelResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                provider_id=gate_decision.provider_id,
                status="blocked",
                content="Llama.cpp invocation blocked: " + ", ".join(gate_decision.blocked_reasons),
                usage=ModelUsage(input_chars=sum(len(message.content) for message in request.messages)),
                finish_reason="blocked",
                real_inference=False,
                warnings=list(dict.fromkeys([*gate_decision.blocked_reasons, *gate_decision.warnings])),
                trace=trace,
            )
        provider = prepared["provider"]
        if provider is not None and provider.execution_mode in {"server_embedding", "server_rerank"}:
            reason = "specialized_llama_server_adapter_required"
            return ModelResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                provider_id=gate_decision.provider_id,
                status="blocked",
                content=f"Llama.cpp invocation blocked: {reason}",
                usage=ModelUsage(input_chars=sum(len(message.content) for message in request.messages)),
                finish_reason="blocked",
                real_inference=False,
                warnings=[reason, provider.execution_mode],
                trace=[*trace, self.audit.build_trace(stage="provider_adapter", status="blocked", reason=reason, data={"execution_mode": provider.execution_mode})],
            )
        if provider is not None and provider.execution_mode == "multimodal_cli":
            has_multimodal_input = any(
                bool(request.metadata.get(key))
                for key in ("image_path", "image_paths", "audio_path", "attachment_paths", "multimodal_inputs")
            )
            reason = "multimodal_input_required" if not has_multimodal_input else "multimodal_cli_adapter_required"
            return ModelResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                provider_id=gate_decision.provider_id,
                status="blocked",
                content=f"Llama.cpp invocation blocked: {reason}",
                usage=ModelUsage(input_chars=sum(len(message.content) for message in request.messages)),
                finish_reason="blocked",
                real_inference=False,
                warnings=[reason, provider.execution_mode],
                trace=[*trace, self.audit.build_trace(stage="provider_adapter", status="blocked", reason=reason, data={"execution_mode": provider.execution_mode})],
            )
        prompt = self._request_prompt(request)
        try:
            ctx_size = self._ctx_size_for_request(request, prompt)
            command = self.command_builder.build(
                executable_path=str(prepared["executable_path"]),
                model_path=str(prepared["model_path"]),
                prompt=prompt,
                ctx_size=ctx_size,
                n_predict=request.generation_config.max_tokens,
                temperature=request.generation_config.temperature,
                top_p=request.generation_config.top_p,
            )
        except Exception as exc:
            return ModelResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                provider_id=gate_decision.provider_id,
                status="blocked",
                content=f"Llama.cpp command blocked: {exc}",
                finish_reason="blocked",
                real_inference=False,
                warnings=[str(exc)],
                trace=[*trace, self.audit.build_trace(stage="command_builder", status="blocked", reason=str(exc))],
            )
        limits = prepared["limits"]
        process = self.runner.run(
            command.argv,
            timeout_seconds=int(limits["timeout_seconds"]),
            max_stdout_chars=int(limits["max_stdout_chars"]),
            max_stderr_chars=int(limits["max_stderr_chars"]),
            cwd=self._working_directory(str(prepared["executable_path"])),
            env=self._process_environment(),
        )
        raw_stdout_chars = len(process.stdout or "")
        stderr_raw_chars = len(process.stderr or "")
        completion = self.sanitizer.extract_llama_cli_completion(process.stdout, prompt=prompt)
        reasoning_content_stripped = self.sanitizer.has_reasoning_content(completion)
        completion = self.sanitizer.strip_reasoning_content(completion)
        stdout = self.sanitizer.sanitize(completion, max_chars=int(limits["max_stdout_chars"]))
        stderr = self.sanitizer.sanitize(process.stderr, max_chars=int(limits["max_stderr_chars"]))
        stdout_error = self.sanitizer.has_llama_cli_error(process.stdout)
        response_status = "completed" if process.status == "completed" and not stdout_error else "error"
        finish_reason = "timeout" if process.timed_out else "error" if stdout_error else "stop" if process.status == "completed" else "error"
        warnings = [] if process.status == "completed" else [process.status]
        if stdout_error:
            warnings.append("llama_cli_error")
        if reasoning_content_stripped:
            warnings.append("reasoning_content_stripped")
        if stderr:
            warnings.append("stderr_captured")
        response = ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=gate_decision.provider_id,
            status=response_status,  # type: ignore[arg-type]
            content=stdout,
            usage=ModelUsage(input_chars=len(prompt), output_chars=len(stdout), estimated_input_tokens=max(1, len(prompt) // 4) if prompt else 0, estimated_output_tokens=max(1, len(stdout) // 4) if stdout else 0),
            finish_reason=finish_reason,  # type: ignore[arg-type]
            real_inference=True,
            warnings=warnings,
            trace=[
                *trace,
                self.audit.build_trace(
                    stage="command_builder",
                    status="ok",
                    reason="argv_built",
                    data={"sanitized_command": command.sanitized, "ctx_size": ctx_size},
                ),
                self.audit.build_trace(stage="process", status=process.status, reason="process_runner_finished", data={"returncode": process.returncode, "timed_out": process.timed_out, "killed": process.killed, "latency_ms": process.latency_ms, "stderr": stderr}),
            ],
            metadata={
                "latency_ms": process.latency_ms,
                "process_status": process.status,
                "process_returncode": process.returncode,
                "process_timed_out": process.timed_out,
                "ctx_size": ctx_size,
                "stdout_raw_chars": raw_stdout_chars,
                "stderr_chars": stderr_raw_chars,
                "parser": "llama_cli_completion",
                "process_cwd": self._working_directory(str(prepared["executable_path"])),
            },
        )
        validation = self.output_contract_builder.validate_model_response_against_contract(response.content, request.output_contract)
        if not validation.get("valid", False):
            response.status = "degraded"
            response.warnings = [*response.warnings, str(validation.get("error", "output_contract_validation_failed"))]
            response.trace.append(self.audit.build_trace(stage="output_contract", status="degraded", reason=str(validation.get("error"))))
        return response

    def _prepare(self, request: ModelRequest) -> dict[str, Any]:
        model = self.model_registry.get_model(request.model_id)
        provider_id = request.provider_id or (model.provider_id if model else "llama_cpp.local")
        provider = self.provider_registry.get_provider(provider_id)
        local_entry = self.path_service.get_by_model_id(request.model_id)
        executable_path = request.metadata.get("executable_path") or (provider.executable_path if provider else None)
        model_path = request.metadata.get("model_path") or (model.model_path if model and model.model_path else (local_entry.path if local_entry else None))
        executable_validation = self.validator.validate_executable_path(str(executable_path) if executable_path else None, provider_enabled=bool(provider and provider.enabled))
        model_validation = self.validator.validate_model_path(str(model_path) if model_path else None, model_enabled=bool(model and model.enabled))
        gate_decision = self.gate.evaluate(
            request=request,
            model=model,
            provider=provider,
            model_path_validation=model_validation,
            executable_validation=executable_validation,
        )
        limits = {
            "timeout_seconds": request.metadata.get("timeout_seconds") or 60,
            "max_stdout_chars": request.metadata.get("max_stdout_chars") or 20000,
            "max_stderr_chars": request.metadata.get("max_stderr_chars") or 8000,
        }
        return {
            "model": model,
            "provider": provider,
            "model_path": model_path,
            "executable_path": executable_path,
            "model_validation": model_validation,
            "executable_validation": executable_validation,
            "gate_decision": gate_decision,
            "limits": limits,
        }

    def _request_prompt(self, request: ModelRequest) -> str:
        return "\n\n".join(f"{message.role}: {message.content}" for message in request.messages)

    def _ctx_size_for_request(self, request: ModelRequest, prompt: str) -> int:
        requested = request.metadata.get("ctx_size")
        if requested:
            return int(requested)
        runtime = self.command_builder.config.get("runtime", {})
        runtime = runtime if isinstance(runtime, dict) else {}
        default_ctx = int(runtime.get("default_ctx_size", 2048) or 2048)
        max_ctx = int(runtime.get("max_ctx_size", 4096) or 4096)
        estimated_prompt_tokens = max(1, len(prompt) // 4)
        output_tokens = max(0, int(request.generation_config.max_tokens or 0))
        margin_tokens = max(256, min(1024, output_tokens // 2 if output_tokens else 256))
        required = estimated_prompt_tokens + output_tokens + margin_tokens
        return min(max_ctx, max(default_ctx, required))

    def _working_directory(self, executable_path: str) -> str | None:
        llama = self.command_builder.config.get("llama_cpp", {}) if isinstance(self.command_builder.config.get("llama_cpp", {}), dict) else {}
        configured = llama.get("working_directory")
        if configured:
            return str(configured)
        try:
            return str(Path(executable_path).resolve().parent)
        except OSError:
            return None

    def _process_environment(self) -> dict[str, str] | None:
        runner_config = getattr(self.runner, "config", {})
        process_policy = runner_config.get("process", {}) if isinstance(runner_config, dict) and isinstance(runner_config.get("process", {}), dict) else {}
        if not bool(process_policy.get("sanitize_environment", True)):
            return None
        return dict(os.environ)
