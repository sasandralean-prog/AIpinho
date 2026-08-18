from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_doctor_check import ModelDoctorCheck
from aipinho.schemas.models.model_doctor_request import ModelDoctorRequest
from aipinho.schemas.models.model_doctor_result import ModelDoctorResult
from aipinho.services.models.model_capability_service import ModelCapabilityService
from aipinho.services.models.model_hardware_estimator import ModelHardwareEstimator
from aipinho.services.models.model_latency_estimator import ModelLatencyEstimator
from aipinho.services.models.model_load_probe_service import ModelLoadProbeService
from aipinho.services.models.model_path_validator import ModelPathValidator
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.model_security_validator import ModelSecurityValidator
from aipinho.services.models.model_trace_service import ModelTraceService
from aipinho.services.models.provider_registry_service import ProviderRegistryService


class ModelDoctorService:
    def __init__(
        self,
        registry: ModelRegistryService | None = None,
        providers: ProviderRegistryService | None = None,
        store_dir: Path | None = None,
    ) -> None:
        self.registry = registry or ModelRegistryService()
        self.providers = providers or ProviderRegistryService()
        self.path_validator = ModelPathValidator()
        self.security_validator = ModelSecurityValidator()
        self.capability = ModelCapabilityService()
        self.hardware = ModelHardwareEstimator()
        self.latency = ModelLatencyEstimator()
        self.probe = ModelLoadProbeService()
        self.trace = ModelTraceService()
        self.store_dir = store_dir or PATHS.project_root / "data" / "runtime" / "model_doctor"

    def run_for_model(self, model_id: str, request: ModelDoctorRequest | None = None) -> ModelDoctorResult | None:
        request = request or ModelDoctorRequest()
        model = self.registry.get_runtime_model(model_id)
        if model is None:
            return None
        trace_id = self.trace.create_model_trace(model_id=model.model_id, summary=f"Model Doctor started for {model.model_id}") if request.include_trace else None
        result = self._build_result(model, request, trace_id=trace_id)
        self._save(result)
        if trace_id:
            self.trace.record(trace_id, event_type="model_doctor_complete", status=result.status, summary=f"Model Doctor completed with {result.status}", model_id=model.model_id, data=result.model_dump())
        return result

    def run_all(self, request: ModelDoctorRequest | None = None) -> list[ModelDoctorResult]:
        request = request or ModelDoctorRequest()
        results = []
        for model in self.registry.runtime_models():
            if model.manual_only and not request.include_manual_only:
                continue
            result = self.run_for_model(model.model_id, request)
            if result is not None:
                results.append(result)
        return results

    def latest_report(self) -> dict[str, object]:
        results = []
        if self.store_dir.exists():
            for path in sorted(self.store_dir.glob("doctor_*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
                try:
                    results.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    continue
        return {"status": "ok", "results": results, "count": len(results)}

    def get_result(self, doctor_run_id: str) -> dict[str, object] | None:
        path = self.store_dir / f"{doctor_run_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_result(self, model: ModelDefinition, request: ModelDoctorRequest, *, trace_id: str | None) -> ModelDoctorResult:
        checks = [
            self._provider_check(model),
            self._path_check(model),
            self._security_check(model),
            self._mmproj_check(model),
            self._capability_check(model),
            self._hardware_check(model),
            self._latency_check(model),
            self._probe_check(model, request),
        ]
        blocked = []
        warnings = list(model.warnings)
        if model.manual_only:
            warnings.append("manual_only_model_requires_operator_confirmation_for_future_use")
        if model.experimental_until_doctor_passed:
            warnings.append("experimental_until_doctor_passed")
        for check in checks:
            blocked.extend(check.blocked_reasons)
            warnings.extend(check.warnings)
        blocked = list(dict.fromkeys(blocked))
        warnings = list(dict.fromkeys(warnings))
        status = "blocked" if blocked else ("degraded" if warnings else "healthy")
        return ModelDoctorResult(
            doctor_run_id=f"doctor_{uuid4().hex}_{model.model_id}",
            model_id=model.model_id,
            status=status,
            checks=checks,
            blocked_reasons=blocked,
            warnings=warnings,
            trace_id=trace_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _provider_check(self, model: ModelDefinition) -> ModelDoctorCheck:
        provider = self.providers.get_provider(model.provider_id)
        blocked = [] if provider else ["provider_not_registered"]
        warnings = [] if not provider or provider.enabled else ["provider_disabled"]
        return ModelDoctorCheck(name="provider_registered", status="passed" if not blocked else "blocked", summary="Provider registry lookup", blocked_reasons=blocked, warnings=warnings, evidence={"provider_id": model.provider_id})

    def _path_check(self, model: ModelDefinition) -> ModelDoctorCheck:
        validation = self.path_validator.validate_model_path(model.model_path, model_enabled=True)
        return ModelDoctorCheck(name="model_path", status="passed" if validation.valid else "blocked", summary="Model GGUF path validation", blocked_reasons=list(validation.blocked_reasons), warnings=list(validation.warnings), evidence=validation.model_dump())

    def _security_check(self, model: ModelDefinition) -> ModelDoctorCheck:
        validation = self.security_validator.validate(model)
        return ModelDoctorCheck(name="model_security", status=validation.status, summary="Model path security validation", blocked_reasons=list(validation.blocked_reasons), warnings=list(validation.warnings), evidence=validation.model_dump())

    def _mmproj_check(self, model: ModelDefinition) -> ModelDoctorCheck:
        blocked: list[str] = []
        warnings: list[str] = []
        evidence = {"requires_mmproj": model.requires_mmproj, "mmproj_path": model.mmproj_path}
        if model.requires_mmproj:
            validation = self.path_validator.validate_model_path(model.mmproj_path, model_enabled=True)
            evidence["validation"] = validation.model_dump()
            if not validation.valid:
                blocked.extend(validation.blocked_reasons or ["mmproj_invalid"])
            warnings.extend(validation.warnings)
        return ModelDoctorCheck(name="mmproj_path", status="passed" if not blocked else "blocked", summary="Vision mmproj validation", blocked_reasons=blocked, warnings=warnings, evidence=evidence)

    def _capability_check(self, model: ModelDefinition) -> ModelDoctorCheck:
        provider = self.providers.get_provider(model.provider_id)
        decision = self.capability.validate_provider_match(model, provider)
        return ModelDoctorCheck(name="capability_provider_match", status=str(decision["status"]), summary="Capability/provider compatibility", blocked_reasons=list(decision["blocked_reasons"]), warnings=list(decision["warnings"]), evidence={"capabilities": model.capabilities, "provider_id": model.provider_id})

    def _hardware_check(self, model: ModelDefinition) -> ModelDoctorCheck:
        estimate = self.hardware.estimate(model)
        warnings = [estimate.warning] if estimate.warning else []
        return ModelDoctorCheck(name="hardware_estimate", status="passed", summary="CPU-only hardware estimate", warnings=warnings, evidence=estimate.model_dump())

    def _latency_check(self, model: ModelDefinition) -> ModelDoctorCheck:
        estimate = self.latency.estimate(model)
        warnings = [estimate.expected] if estimate.requires_warning else []
        return ModelDoctorCheck(name="latency_estimate", status="passed", summary="CPU-only latency estimate", warnings=warnings, evidence=estimate.model_dump())

    def _probe_check(self, model: ModelDefinition, request: ModelDoctorRequest) -> ModelDoctorCheck:
        probe = self.probe.metadata_probe(model, include_first_token_probe=request.include_first_token_probe, operator_confirmed=request.operator_confirmed)
        return ModelDoctorCheck(name="load_probe", status=probe.status, summary="Metadata-only load probe", blocked_reasons=list(probe.blocked_reasons), warnings=list(probe.warnings), evidence=probe.model_dump())

    def _save(self, result: ModelDoctorResult) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        path = self.store_dir / f"{result.doctor_run_id}.json"
        path.write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "model_doctor", "runtime_models": len(self.registry.runtime_models()), "store_dir": str(self.store_dir)}
