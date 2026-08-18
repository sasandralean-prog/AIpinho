from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_security_validation import ModelSecurityValidation
from aipinho.utils.yaml_loader import load_yaml_file


class ModelSecurityValidator:
    def __init__(self) -> None:
        self.config = load_yaml_file(PATHS.config_root / "models" / "model_security_policy.yaml", critical=True, root=PATHS.config_root / "models")

    def validate(self, model: ModelDefinition) -> ModelSecurityValidation:
        path = model.model_path
        validation = ModelSecurityValidation(model_id=model.model_id, status="blocked", path=path)
        if not path:
            validation.blocked_reasons.append("model_path_required")
            return validation
        if self._is_network_path(path):
            validation.network_path = True
            validation.blocked_reasons.append("network_path_blocked")
            return validation
        candidate = Path(path)
        validation.traversal_detected = any(part == ".." for part in candidate.parts)
        if validation.traversal_detected and self.config.get("security", {}).get("block_path_traversal", True):
            validation.blocked_reasons.append("path_traversal_blocked")
        validation.extension_valid = candidate.suffix.lower() == ".gguf"
        if not validation.extension_valid:
            validation.blocked_reasons.append("invalid_extension")
        validation.allowed_root = self._under_any_root(candidate, [str(item) for item in self.config.get("security", {}).get("allowed_roots", []) or []])
        if not validation.allowed_root:
            validation.blocked_reasons.append("outside_allowed_model_roots")
        try:
            validation.symlink_detected = candidate.is_symlink()
        except OSError:
            validation.warnings.append("symlink_status_unavailable")
        if validation.symlink_detected and self.config.get("security", {}).get("block_symlinks", True):
            validation.blocked_reasons.append("symlink_blocked")
        validation.status = "passed" if not validation.blocked_reasons else "blocked"
        return validation

    def _is_network_path(self, path: str) -> bool:
        lowered = path.lower()
        return lowered.startswith("\\\\") or lowered.startswith("http://") or lowered.startswith("https://")

    def _under_any_root(self, path: Path, roots: list[str]) -> bool:
        text = self._norm(path)
        for root in roots:
            root_text = self._norm(Path(root))
            if text == root_text or text.startswith(root_text.rstrip("\\/") + "\\") or text.startswith(root_text.rstrip("\\/") + "/"):
                return True
        return False

    def _norm(self, path: Path) -> str:
        try:
            return str(path.resolve(strict=False)).lower()
        except OSError:
            return str(path).lower()
