from __future__ import annotations

from time import perf_counter

from aipinho.schemas.models.manual_inference_request import ManualInferenceRequest
from aipinho.schemas.models.manual_inference_result import ExpectedOutputCheck, ManualInferenceResult
from aipinho.services.models.llama_cpp_provider import LlamaCppProvider
from aipinho.services.models.inference_runtime_service import InferenceRuntimeService
from aipinho.services.models.llama_smoke_prompt_service import LlamaSmokePromptService
from aipinho.services.models.manual_inference_gate_service import ManualInferenceGateService
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService
from aipinho.services.models.model_output_sanitizer import ModelOutputSanitizer
from aipinho.services.models.real_inference_run_store import RealInferenceRunStore
from aipinho.services.models.smoke_test_audit_service import SmokeTestAuditService


class LlamaSmokeTestService:
    def __init__(
        self,
        profile_service: ManualInferenceProfileService | None = None,
        gate_service: ManualInferenceGateService | None = None,
        prompt_service: LlamaSmokePromptService | None = None,
        provider: LlamaCppProvider | None = None,
        inference_runtime: InferenceRuntimeService | None = None,
        audit_service: SmokeTestAuditService | None = None,
        run_store: RealInferenceRunStore | None = None,
        sanitizer: ModelOutputSanitizer | None = None,
    ) -> None:
        self.profile_service = profile_service or ManualInferenceProfileService()
        self.gate_service = gate_service or ManualInferenceGateService(profile_service=self.profile_service)
        self.prompt_service = prompt_service or LlamaSmokePromptService()
        if inference_runtime is not None:
            self.inference_runtime = inference_runtime
        elif provider is not None:
            self.inference_runtime = InferenceRuntimeService(llama_cpp=provider)
        else:
            self.inference_runtime = InferenceRuntimeService()
        self.audit_service = audit_service or SmokeTestAuditService()
        self.run_store = run_store or RealInferenceRunStore()
        self.sanitizer = sanitizer or ModelOutputSanitizer()

    def validate(self, request: ManualInferenceRequest) -> dict[str, object]:
        profile = self.profile_service.get_profile(request.profile_id)
        decision = self.gate_service.decide(request, profile)
        return {"status": "allowed" if decision.allowed else "blocked", "gate_decision": decision.model_dump(), "process_started": False}

    def preview(self, request: ManualInferenceRequest) -> dict[str, object]:
        profile = self.profile_service.get_profile(request.profile_id)
        decision = self.gate_service.decide(request, profile)
        prompt_summary = self.prompt_service.prompt_summary(request.prompt_id or (profile.prompt_id if profile else None))
        command_preview = None
        runtime_estimate: dict[str, object] = {}
        warnings: list[str] = []
        if decision.allowed and profile is not None:
            try:
                model_request = self.prompt_service.build_smoke_prompt(request, profile)
                preview = self.inference_runtime.invoke_preview(model_request)
                command_preview = preview.get("command_preview")
                runtime_estimate = preview.get("runtime_estimate", {}) if isinstance(preview.get("runtime_estimate", {}), dict) else {}
                warnings.extend([str(item) for item in preview.get("warnings", []) or []])
            except Exception as exc:
                warnings.append(str(exc))
        return {
            "status": "ok",
            "process_started": False,
            "gate_decision": decision.model_dump(),
            "prompt_summary": prompt_summary,
            "command_preview": command_preview,
            "runtime_estimate": runtime_estimate,
            "warnings": list(dict.fromkeys(warnings)),
        }

    def smoke_test(self, request: ManualInferenceRequest) -> ManualInferenceResult:
        started = perf_counter()
        profile = self.profile_service.get_profile(request.profile_id)
        decision = self.gate_service.decide(request, profile)
        if profile is None or not decision.allowed:
            result = ManualInferenceResult(
                status="blocked",
                profile_id=request.profile_id,
                model_id=request.model_id,
                provider_id=request.provider_id,
                real_inference=False,
                process_started=False,
                duration_ms=self._duration_ms(started),
                gate_decision=decision.model_dump(),
                warnings=decision.warnings,
                violations=decision.blocked_reasons,
                trace=decision.trace if request.include_trace else [],
            )
            return self._persist(result)
        try:
            model_request = self.prompt_service.build_smoke_prompt(request, profile)
            response = self.inference_runtime.invoke(model_request)
        except Exception as exc:
            result = ManualInferenceResult(
                status="failed",
                profile_id=profile.profile_id,
                model_id=profile.model_id,
                provider_id=profile.provider_id,
                real_inference=False,
                process_started=False,
                duration_ms=self._duration_ms(started),
                gate_decision=decision.model_dump(),
                warnings=[str(exc)],
                violations=["smoke_test_exception"],
                trace=decision.trace if request.include_trace else [],
            )
            return self._persist(result)
        output_preview = self.sanitizer.sanitize(response.content, max_chars=500)
        expected = self.prompt_service.validate_expected_output(output_preview, request.prompt_id or profile.prompt_id)
        process_started = bool(response.real_inference)
        status = "completed" if response.status == "completed" else "failed"
        if response.finish_reason == "timeout":
            status = "timeout"
        elif response.status == "blocked":
            status = "blocked"
        elif response.status == "completed" and not expected.get("passed", False):
            status = "completed_with_warning"
        result = ManualInferenceResult(
            status=status,  # type: ignore[arg-type]
            profile_id=profile.profile_id,
            model_id=response.model_id,
            provider_id=response.provider_id,
            real_inference=response.real_inference,
            process_started=process_started,
            duration_ms=self._duration_ms(started),
            output_preview=output_preview,
            expected_output_check=ExpectedOutputCheck.model_validate(expected),
            model_response=response.model_dump(exclude={"content"}),
            gate_decision=decision.model_dump(),
            warnings=list(dict.fromkeys([*response.warnings, *decision.warnings])),
            violations=[] if response.status != "blocked" else response.warnings,
            trace=[*decision.trace, *response.trace] if request.include_trace else [],
        )
        return self._persist(result)

    def _persist(self, result: ManualInferenceResult) -> ManualInferenceResult:
        event = self.audit_service.record(result)
        result.audit_event_id = event.audit_event_id
        self.run_store.save_run(result)
        self.run_store.append_event(result.run_id, event.model_dump())
        return result

    def _duration_ms(self, started: float) -> int:
        return int((perf_counter() - started) * 1000)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "llama_smoke_test"}
