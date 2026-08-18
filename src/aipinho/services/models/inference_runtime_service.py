from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from aipinho.adapters.llm_providers.llama_cpp_provider import LlamaCppProvider
from aipinho.schemas.models.inference_runtime import InferenceRuntimeFingerprint, InferenceRuntimeTelemetry
from aipinho.schemas.models.inference_observability import (
    CanonicalInferenceInputArtifact,
    CanonicalInferenceOutputArtifact,
    ContextBudgetArtifact,
)
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.models.inference_input_doctor_service import InferenceInputDoctorService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService


class InferenceRuntimeService:
    """Canonical boundary for real model inference.

    Engine providers remain adapters underneath this service. Callers should not
    invoke llama.cpp directly when they need model output.
    """

    _hash_cache: dict[tuple[str, int, int], str] = {}

    def __init__(
        self,
        *,
        llama_cpp: LlamaCppProvider | None = None,
        model_registry: ModelRegistryService | None = None,
        provider_registry: ProviderRegistryService | None = None,
    ) -> None:
        self.llama_cpp = llama_cpp or LlamaCppProvider()
        self.model_registry = model_registry or getattr(self.llama_cpp, "model_registry", None) or ModelRegistryService()
        self.provider_registry = provider_registry or getattr(self.llama_cpp, "provider_registry", None) or ProviderRegistryService()
        self.input_doctor = InferenceInputDoctorService()

    def invoke(self, request: ModelRequest) -> ModelResponse:
        input_artifact = self._input_artifact(request)
        provider = self.provider_registry.get_provider(request.provider_id)
        if provider is None and request.provider_id == "llama_cpp.local":
            provider = self.provider_registry.get_provider("llama_cpp.local")
        provider_type = provider.type if provider is not None else request.provider_id
        if provider_type != "llama_cpp" and not provider_type.startswith("llama_cpp_"):
            response = ModelResponse(
                request_id=request.request_id,
                model_id=request.model_id,
                provider_id=request.provider_id,
                status="blocked",
                content="Inference Runtime blocked: provider is not a governed llama.cpp inference provider.",
                finish_reason="blocked",
                real_inference=False,
                warnings=["inference_provider_not_supported"],
                trace=[{"stage": "inference_runtime", "status": "blocked", "reason": "inference_provider_not_supported"}],
            )
            return self._attach_telemetry(response, request, input_artifact=input_artifact)
        response = self.llama_cpp.invoke(request)
        return self._attach_telemetry(response, request, input_artifact=input_artifact)

    def invoke_preview(self, request: ModelRequest) -> dict[str, object]:
        preview = self.llama_cpp.invoke_preview(request)
        preview["inference_runtime"] = self._telemetry(request).model_dump(mode="json")
        return preview

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "inference_runtime",
            "providers": self.provider_registry.status(),
            "models": self.model_registry.status(),
            "llama_cpp_adapter": self.llama_cpp.status(),
        }

    def _attach_telemetry(self, response: ModelResponse, request: ModelRequest, *, input_artifact: CanonicalInferenceInputArtifact) -> ModelResponse:
        telemetry = self._telemetry(request, response=response)
        input_artifact = input_artifact.model_copy(update={"fingerprint": telemetry.fingerprint.model_dump(mode="json")})
        output_artifact = self._output_artifact(response, input_artifact=input_artifact, telemetry=telemetry)
        input_doctor = self.input_doctor.analyze(input_artifact, output_artifact)
        response.metadata = {
            **response.metadata,
            "inference_runtime": telemetry.model_dump(mode="json"),
            "canonical_inference_input_artifact": input_artifact.model_dump(mode="json"),
            "canonical_inference_output_artifact": output_artifact.model_dump(mode="json"),
            "inference_input_doctor": input_doctor.model_dump(mode="json"),
        }
        response.trace.append(
            {
                "stage": "inference_runtime",
                "status": response.status,
                "reason": "canonical_inference_completed" if response.real_inference else response.finish_reason,
                "data": {
                    "provider_id": request.provider_id,
                    "model_id": request.model_id,
                    "executable_sha256": telemetry.fingerprint.executable_sha256,
                    "model_sha256": telemetry.fingerprint.model_sha256,
                    "cwd": telemetry.fingerprint.cwd,
                    "timed_out": telemetry.timed_out,
                },
            }
        )
        return response

    def _input_artifact(self, request: ModelRequest) -> CanonicalInferenceInputArtifact:
        prompt_final = self._prompt_final(request)
        role_context = request.metadata.get("role_context") if isinstance(request.metadata.get("role_context"), dict) else {}
        patch_candidate = request.metadata.get("patch_candidate") if isinstance(request.metadata.get("patch_candidate"), dict) else {}
        if not patch_candidate and isinstance(role_context, dict) and isinstance(role_context.get("patch_candidate"), dict):
            patch_candidate = role_context.get("patch_candidate") or {}
        current_content = request.metadata.get("current_content")
        if current_content is None and isinstance(role_context, dict):
            current_content = role_context.get("current_content")
        evidence = request.metadata.get("evidence")
        if evidence is None and isinstance(role_context, dict):
            evidence = role_context.get("evidence") or role_context.get("evidence_refs")
        diagnosis_id = str(patch_candidate.get("diagnosis_id") or request.metadata.get("diagnosis_id") or "")
        context_budget = self._context_budget(request, prompt_final)
        truncated_items = self._truncated_items(request, role_context)
        output_schema = request.output_contract if isinstance(request.output_contract, dict) else {}
        return CanonicalInferenceInputArtifact(
            role=str(request.metadata.get("role_id") or ""),
            operation_type=str(request.metadata.get("operation_type") or request.metadata.get("purpose") or ""),
            semantic_goal=str(request.metadata.get("semantic_goal") or request.metadata.get("prompt_original") or ""),
            prompt_original=str(request.metadata.get("prompt_original") or self._first_user_message(request)),
            prompt_final=prompt_final,
            system_prompt="\n\n".join(message.content for message in request.messages if message.role == "system"),
            output_schema=output_schema,
            artifacts_used=self._string_list(request.metadata.get("artifacts_used") or request.metadata.get("artifact_refs")),
            evidence_used=self._evidence_ids(evidence),
            diagnosis_ids=[diagnosis_id] if diagnosis_id else self._string_list(request.metadata.get("diagnosis_ids")),
            patch_candidate_id=str(patch_candidate.get("candidate_id") or request.metadata.get("patch_candidate_id") or "") or None,
            symbol_targets=self._string_list([patch_candidate.get("target_symbol")] if patch_candidate.get("target_symbol") else request.metadata.get("symbol_targets")),
            file_targets=self._string_list([patch_candidate.get("target_file")] if patch_candidate.get("target_file") else request.metadata.get("file_targets")),
            code_snippets=self._code_snippets(current_content, patch_candidate),
            estimated_tokens=max(1, len(prompt_final) // 4) if prompt_final else 0,
            prompt_chars=len(prompt_final),
            truncated_items=truncated_items,
            context_budget=context_budget,
            provider=request.provider_id,
            model=request.model_id,
            metadata={
                "observed_behavior": patch_candidate.get("observed_behavior") or request.metadata.get("observed_behavior"),
                "expected_behavior": patch_candidate.get("expected_behavior") or request.metadata.get("expected_behavior"),
                "omitted_artifacts": self._string_list(request.metadata.get("omitted_artifacts")),
                "omitted_snippets": self._string_list(request.metadata.get("omitted_snippets")),
                "omitted_symbols": self._string_list(request.metadata.get("omitted_symbols")),
            },
        )

    def _output_artifact(
        self,
        response: ModelResponse,
        *,
        input_artifact: CanonicalInferenceInputArtifact,
        telemetry: InferenceRuntimeTelemetry,
    ) -> CanonicalInferenceOutputArtifact:
        parsed, json_valid, diagnostics = self.input_doctor.parse_output(response.content)
        replacement_count, replacement_detected, replacement_diagnostics = self._replacement_state(parsed)
        diagnostics.extend(replacement_diagnostics)
        empty_output = not bool(response.content.strip()) or ("legacy_edits_empty" in diagnostics) or ("replacement_empty" in diagnostics)
        confidence = 0.0
        if isinstance(parsed, dict):
            try:
                confidence = float(parsed.get("confidence") or 0.0)
            except (TypeError, ValueError):
                confidence = 0.0
        return CanonicalInferenceOutputArtifact(
            input_artifact_id=input_artifact.artifact_id,
            raw_output=str(response.metadata.get("raw_output") or response.content),
            sanitized_output=response.content,
            parsed_output=parsed,
            parser=telemetry.parser,
            completion_chars=len(response.content),
            json_valid=json_valid,
            retry_count=telemetry.retry_count,
            finish_reason=response.finish_reason,
            confidence=confidence,
            replacement_detected=replacement_detected,
            replacement_count=replacement_count,
            empty_output=empty_output,
            diagnostics=list(dict.fromkeys(diagnostics)),
        )

    def _replacement_state(self, parsed: Any) -> tuple[int, bool, list[str]]:
        diagnostics: list[str] = []
        if parsed is None:
            return 0, False, diagnostics
        if isinstance(parsed, dict):
            if "edits" in parsed:
                edits = parsed.get("edits")
                if not isinstance(edits, list) or not edits:
                    return 0, False, ["legacy_edits_empty"]
                count = sum(1 for item in edits if isinstance(item, dict) and str(item.get("replacement") or "").strip())
                if count <= 0:
                    diagnostics.append("replacement_empty")
                return count, count > 0, diagnostics
            replacement = str(parsed.get("replacement") or parsed.get("patch_snippet") or "")
            if not replacement.strip():
                diagnostics.append("replacement_empty")
                return 0, False, diagnostics
            return 1, True, diagnostics
        return 0, False, ["parsed_output_not_patch_replacement"]

    def _prompt_final(self, request: ModelRequest) -> str:
        return "\n\n".join(f"{message.role}: {message.content}" for message in request.messages)

    def _first_user_message(self, request: ModelRequest) -> str:
        return next((message.content for message in request.messages if message.role == "user"), "")

    def _context_budget(self, request: ModelRequest, prompt_final: str) -> ContextBudgetArtifact:
        budget = request.metadata.get("context_budget") if isinstance(request.metadata.get("context_budget"), dict) else {}
        role_limit = budget.get("max_context_chars") if isinstance(budget, dict) else None
        provider_limit = request.metadata.get("ctx_size")
        try:
            provider_limit_chars = int(provider_limit) * 4 if provider_limit else None
        except (TypeError, ValueError):
            provider_limit_chars = None
        return ContextBudgetArtifact(
            role_limit_chars=int(role_limit) if role_limit is not None else None,
            provider_limit_chars=provider_limit_chars,
            actual_chars=len(prompt_final),
            estimated_tokens=max(1, len(prompt_final) // 4) if prompt_final else 0,
            discarded_items=self._string_list(request.metadata.get("discarded_context_items")),
            truncated_items=self._string_list(request.metadata.get("truncated_items")),
        )

    def _truncated_items(self, request: ModelRequest, role_context: dict[str, Any]) -> list[str]:
        items = self._string_list(request.metadata.get("truncated_items"))
        if "[truncated]" in self._prompt_final(request):
            items.append("prompt_final")
        for key, value in role_context.items() if isinstance(role_context, dict) else []:
            if isinstance(value, str) and "[truncated]" in value:
                items.append(str(key))
        return list(dict.fromkeys(items))

    def _string_list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        if isinstance(value, dict):
            return [str(key) for key in value if key]
        if isinstance(value, (list, tuple, set)):
            result: list[str] = []
            for item in value:
                if isinstance(item, dict):
                    candidate = item.get("artifact_id") or item.get("evidence_id") or item.get("logical_path") or item.get("source_path") or item.get("target_file") or item.get("target_symbol")
                    if candidate:
                        result.append(str(candidate))
                elif item:
                    result.append(str(item))
            return list(dict.fromkeys(result))
        return [str(value)]

    def _evidence_ids(self, value: Any) -> list[str]:
        return self._string_list(value)

    def _code_snippets(self, current_content: Any, patch_candidate: dict[str, Any]) -> list[dict[str, Any]]:
        content = str(current_content or "")
        if not content.strip():
            return []
        return [
            {
                "target_file": str(patch_candidate.get("target_file") or ""),
                "target_symbol": str(patch_candidate.get("target_symbol") or ""),
                "chars": len(content),
                "content": content,
            }
        ]

    def _telemetry(self, request: ModelRequest, *, response: ModelResponse | None = None) -> InferenceRuntimeTelemetry:
        model = self.model_registry.get_model(request.model_id)
        provider = self.provider_registry.get_provider(request.provider_id)
        executable_path = str(request.metadata.get("executable_path") or (provider.executable_path if provider else "") or "") or None
        model_path = str(request.metadata.get("model_path") or (model.model_path if model else "") or "") or None
        cwd = self._cwd_for(provider_config_path=executable_path, request=request)
        fingerprint = InferenceRuntimeFingerprint(
            executable_path=executable_path,
            executable_sha256=self._file_sha256(executable_path),
            model_path=model_path,
            model_sha256=self._file_sha256(model_path),
            model_size_bytes=self._file_size(model_path),
            model_mtime_ns=self._file_mtime_ns(model_path),
            cwd=cwd,
            path_sha256=self._text_sha256(os.environ.get("PATH", "")),
            env_sha256=self._env_sha256(),
            vulkan_sdk=os.environ.get("VULKAN_SDK"),
        )
        prompt_chars = sum(len(message.content) for message in request.messages)
        content = response.content if response is not None else ""
        raw_stdout_chars = int((response.metadata or {}).get("stdout_raw_chars") or len(content)) if response else 0
        stderr_chars = int((response.metadata or {}).get("stderr_chars") or 0) if response else 0
        parser = str((response.metadata or {}).get("parser") or "llama_cli_text") if response else None
        json_valid = self._json_valid(content) if request.output_contract.get("format") == "json" or request.output_contract.get("contract_type") == "json" else None
        return InferenceRuntimeTelemetry(
            provider_type=provider.type if provider else None,
            execution_mode=provider.execution_mode if provider else None,
            model_id=request.model_id,
            provider_id=request.provider_id,
            ctx_size=int((response.metadata or {}).get("ctx_size") or request.metadata.get("ctx_size") or 0) or None if response else None,
            max_output_tokens=request.generation_config.max_tokens,
            timeout_seconds=int(request.metadata.get("timeout_seconds") or 0) or None,
            prompt_chars=prompt_chars,
            completion_chars=len(content),
            prompt_tokens_estimated=max(1, prompt_chars // 4) if prompt_chars else 0,
            completion_tokens_estimated=max(1, len(content) // 4) if content else 0,
            parser=parser,
            json_valid=json_valid,
            retry_count=int(request.metadata.get("retry_count") or 0),
            timed_out=bool((response.metadata or {}).get("process_timed_out", False)) if response else False,
            stdout_raw_chars=raw_stdout_chars,
            stdout_sanitized_chars=len(content),
            stderr_chars=stderr_chars,
            fingerprint=fingerprint,
            warnings=list(response.warnings if response else []),
        )

    def _cwd_for(self, *, provider_config_path: str | None, request: ModelRequest) -> str | None:
        configured = request.metadata.get("working_directory")
        if configured:
            return str(configured)
        if provider_config_path:
            try:
                return str(Path(provider_config_path).resolve().parent)
            except OSError:
                return None
        return None

    def _file_sha256(self, path: str | None) -> str | None:
        if not path:
            return None
        try:
            file_path = Path(path)
            if not file_path.is_file():
                return None
            stat = file_path.stat()
            cache_key = (str(file_path.resolve()), stat.st_size, stat.st_mtime_ns)
            cached = self._hash_cache.get(cache_key)
            if cached:
                return cached
            digest = hashlib.sha256()
            with file_path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            value = digest.hexdigest()
            self._hash_cache[cache_key] = value
            return value
        except OSError:
            return None

    def _file_size(self, path: str | None) -> int | None:
        if not path:
            return None
        try:
            return Path(path).stat().st_size
        except OSError:
            return None

    def _file_mtime_ns(self, path: str | None) -> int | None:
        if not path:
            return None
        try:
            return Path(path).stat().st_mtime_ns
        except OSError:
            return None

    def _text_sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()

    def _env_sha256(self) -> str:
        redacted = {
            key: value
            for key, value in os.environ.items()
            if not any(secret in key.casefold() for secret in ("key", "token", "secret", "password"))
        }
        return self._text_sha256(json.dumps(redacted, sort_keys=True, ensure_ascii=True))

    def _json_valid(self, content: str) -> bool:
        try:
            json.loads(content)
            return True
        except (TypeError, ValueError):
            return False
