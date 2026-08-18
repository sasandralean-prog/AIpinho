from __future__ import annotations

from pathlib import Path

from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_probe_result import ModelProbeResult


class ModelLoadProbeService:
    def metadata_probe(self, model: ModelDefinition, *, include_first_token_probe: bool = False, operator_confirmed: bool = False) -> ModelProbeResult:
        blocked: list[str] = []
        warnings: list[str] = []
        first_token = False
        if include_first_token_probe:
            if not operator_confirmed:
                blocked.append("first_token_probe_requires_operator_confirmation")
            else:
                blocked.append("first_token_probe_not_implemented")
                warnings.append("no_model_load_executed")
        path = Path(model.model_path) if model.model_path else None
        metadata: dict[str, object] = {
            "model_id": model.model_id,
            "model_path_configured": bool(model.model_path),
            "first_token_probe_requested": include_first_token_probe,
            "first_token_probe_executed": first_token,
        }
        if path and path.exists() and path.is_file():
            metadata["size_bytes"] = path.stat().st_size
        return ModelProbeResult(
            model_id=model.model_id,
            status="blocked" if blocked else "passed",
            probe_type="metadata",
            first_token_probe_executed=first_token,
            blocked_reasons=blocked,
            warnings=warnings,
            metadata=metadata,
        )
