from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_runtime_estimate import ModelRuntimeEstimate
from aipinho.utils.yaml_loader import load_yaml_file


class ModelRuntimeEstimator:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "inference_limits.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def estimate(self, *, model_size_bytes: int | None = None, ctx_size: int = 2048, n_predict: int = 256, quantization: str | None = None) -> ModelRuntimeEstimate:
        warnings: list[str] = []
        confidence = "low"
        estimated_ram_gb = 0.0
        if model_size_bytes and model_size_bytes > 0:
            overhead_gb = max(0.5, (ctx_size + n_predict) / 4096 * 0.75)
            estimated_ram_gb = round(model_size_bytes / (1024 ** 3) + overhead_gb, 2)
            confidence = "medium" if quantization else "low"
        else:
            warnings.append("model_size_unknown")
        memory_policy = self.config.get("memory", {}) if isinstance(self.config.get("memory", {}), dict) else {}
        warn_above = float(memory_policy.get("warn_if_estimated_ram_gb_above", 8) or 8)
        max_allowed = float(memory_policy.get("max_estimated_ram_gb", 16) or 16)
        blocking = False
        if estimated_ram_gb and estimated_ram_gb > warn_above:
            warnings.append("estimated_ram_above_warning_threshold")
        if estimated_ram_gb and estimated_ram_gb > max_allowed:
            blocking = True
            warnings.append("estimated_ram_above_max")
        if not model_size_bytes and memory_policy.get("block_if_estimate_unknown_when_real_inference", False):
            blocking = True
            warnings.append("unknown_estimate_blocked_by_policy")
        return ModelRuntimeEstimate(
            estimated_ram_gb=estimated_ram_gb,
            confidence=confidence,  # type: ignore[arg-type]
            warnings=warnings,
            blocking=blocking,
            model_size_bytes=model_size_bytes,
            ctx_size=ctx_size,
            n_predict=n_predict,
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "model_runtime_estimator"}
