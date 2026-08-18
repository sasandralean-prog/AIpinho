from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_hardware_profile import ModelHardwareProfile
from aipinho.utils.yaml_loader import load_yaml_file


class ModelHardwareEstimator:
    def __init__(self) -> None:
        self.config = load_yaml_file(PATHS.config_root / "models" / "model_hardware_policy.yaml", critical=True, root=PATHS.config_root / "models")

    def estimate(self, model: ModelDefinition) -> ModelHardwareProfile:
        classes = self.config.get("classes", {}) if isinstance(self.config.get("classes", {}), dict) else {}
        hardware_class = model.hardware_class or self._class_from_parameter(model.parameter_class)
        details = classes.get(hardware_class, {}) if isinstance(classes.get(hardware_class, {}), dict) else {}
        manual_only = bool(model.manual_only or details.get("manual_only", False))
        return ModelHardwareProfile(
            model_id=model.model_id,
            hardware_class=hardware_class,
            parameter_class=model.parameter_class,
            cpu_only=True,
            fits_default_hardware=bool(details.get("fits_default_hardware", True)),
            manual_only=manual_only,
            warning=details.get("warning"),
        )

    def _class_from_parameter(self, parameter_class: str | None) -> str:
        if parameter_class == "14b":
            return "large_cpu_slow"
        if parameter_class in {"1_5b", "1_7b", "small"}:
            return "small_cpu"
        return "medium_cpu"
