from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.smoke_test_status import SmokeTestStatus
from aipinho.services.models.llama_cpp_status_service import LlamaCppStatusService
from aipinho.services.models.manual_inference_profile_service import ManualInferenceProfileService
from aipinho.utils.yaml_loader import load_yaml_file


class ManualInferenceStatusService:
    def __init__(self, manual_gate_config: dict[str, Any] | None = None, smoke_policy: dict[str, Any] | None = None, profile_service: ManualInferenceProfileService | None = None, llama_status_service: LlamaCppStatusService | None = None) -> None:
        self.manual_gate_config = manual_gate_config or load_yaml_file(PATHS.config_root / "models" / "manual_inference_gate.yaml", critical=True, root=PATHS.config_root / "models")
        self.smoke_policy = smoke_policy or load_yaml_file(PATHS.config_root / "models" / "llama_smoke_test_policy.yaml", critical=True, root=PATHS.config_root / "models")
        self.real_gate_config = load_yaml_file(PATHS.config_root / "models" / "real_inference_gate.yaml", critical=True, root=PATHS.config_root / "models")
        self.profile_service = profile_service or ManualInferenceProfileService()
        self.llama_status_service = llama_status_service or LlamaCppStatusService()

    def status(self) -> SmokeTestStatus:
        manual = self.manual_gate_config.get("manual_inference", {}) if isinstance(self.manual_gate_config.get("manual_inference", {}), dict) else {}
        defaults = self.manual_gate_config.get("defaults", {}) if isinstance(self.manual_gate_config.get("defaults", {}), dict) else {}
        smoke = self.smoke_policy.get("smoke_test", {}) if isinstance(self.smoke_policy.get("smoke_test", {}), dict) else {}
        real = self.real_gate_config.get("real_inference", {}) if isinstance(self.real_gate_config.get("real_inference", {}), dict) else {}
        llama = self.llama_status_service.status().model_dump()
        manual_enabled = bool(manual.get("enabled", False))
        smoke_enabled = bool(smoke.get("enabled", False) and manual.get("allow_smoke_test", False))
        status = "disabled"
        warnings: list[str] = []
        if manual_enabled and smoke_enabled:
            status = "available" if llama.get("status") == "available" else "degraded"
        if not manual_enabled:
            warnings.append("manual_inference_disabled")
        if not smoke_enabled:
            warnings.append("smoke_test_disabled")
        return SmokeTestStatus(
            manual_inference_enabled=manual_enabled,
            smoke_test_enabled=smoke_enabled,
            real_inference_global_enabled=bool(real.get("enabled", False)),
            default_model=str(real.get("default_model", "stub.default")),
            chat_auto_real_inference=bool(defaults.get("chat_auto_use", False)),
            report_auto_real_inference=bool(defaults.get("report_auto_use", False)),
            analysis_auto_real_inference=bool(defaults.get("analysis_auto_use", False)),
            profiles=self.profile_service.list_profiles(),
            llama_cpp_status=llama,
            warnings=list(dict.fromkeys(warnings)),
            status=status,  # type: ignore[arg-type]
        )
