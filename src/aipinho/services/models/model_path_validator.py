from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.models.model_path_validation import ModelPathValidation
from aipinho.services.models.local_model_path_service import LocalModelPathService


class ModelPathValidator:
    def __init__(self, path_service: LocalModelPathService | None = None, config: dict[str, Any] | None = None) -> None:
        self.path_service = path_service or LocalModelPathService(config=config)

    def validate_model_path(self, path: str | None, *, model_enabled: bool = False) -> ModelPathValidation:
        validation = ModelPathValidation(kind="model", path=path, configured=bool(path))
        policy = self.path_service.validation_policy()
        if not path:
            if model_enabled:
                validation.status = "blocked"
                validation.blocked_reasons.append("model_path_required")
            else:
                validation.status = "disabled"
                validation.warnings.append("model_path_missing_for_disabled_model")
            return validation
        if self._is_network_path(path):
            validation.network_path = True
            validation.status = "blocked"
            validation.blocked_reasons.append("network_path_blocked")
            return validation
        candidate = Path(path)
        validation.forbidden_root = self._under_any_root(candidate, self.path_service.blocked_roots())
        if validation.forbidden_root and policy.get("block_forbidden_roots", True):
            validation.status = "blocked"
            validation.blocked_reasons.append("forbidden_root")
        validation.allowed_root = self._under_any_root(candidate, self.path_service.allowed_roots())
        if not validation.allowed_root:
            validation.blocked_reasons.append("outside_allowed_model_roots")
        validation.extension_valid = candidate.suffix.lower() == ".gguf"
        if policy.get("require_gguf_extension", True) and not validation.extension_valid:
            validation.blocked_reasons.append("invalid_extension")
        validation.exists = candidate.exists()
        validation.is_file = candidate.is_file()
        if validation.exists and validation.is_file:
            try:
                validation.size_bytes = candidate.stat().st_size
            except OSError:
                validation.warnings.append("size_unavailable")
        elif policy.get("require_existing_file", True):
            validation.blocked_reasons.append("file_not_found")
        validation.valid = not validation.blocked_reasons and validation.exists and validation.is_file and validation.extension_valid and validation.allowed_root
        if validation.valid:
            validation.status = "valid"
        elif validation.status != "blocked":
            validation.status = "blocked" if validation.blocked_reasons else "unavailable"
        return validation

    def validate_executable_path(self, path: str | None, *, provider_enabled: bool = False) -> ModelPathValidation:
        validation = ModelPathValidation(kind="executable", path=path, configured=bool(path))
        if not path:
            if provider_enabled:
                validation.status = "blocked"
                validation.blocked_reasons.append("executable_path_required")
            else:
                validation.status = "disabled"
                validation.warnings.append("executable_path_missing_for_disabled_provider")
            return validation
        if self._is_network_path(path):
            validation.network_path = True
            validation.status = "blocked"
            validation.blocked_reasons.append("network_path_blocked")
            return validation
        candidate = Path(path)
        validation.forbidden_root = self._under_any_root(candidate, self.path_service.blocked_roots())
        if validation.forbidden_root:
            validation.blocked_reasons.append("forbidden_root")
        suffix = candidate.suffix.lower()
        validation.extension_valid = suffix in {".exe", ".cmd", ".bat"}
        if not validation.extension_valid:
            validation.blocked_reasons.append("invalid_executable_extension")
        validation.exists = candidate.exists()
        validation.is_file = candidate.is_file()
        if validation.exists and validation.is_file:
            try:
                validation.size_bytes = candidate.stat().st_size
            except OSError:
                validation.warnings.append("size_unavailable")
        else:
            validation.blocked_reasons.append("file_not_found")
        validation.allowed_root = not validation.forbidden_root
        validation.valid = not validation.blocked_reasons and validation.exists and validation.is_file and validation.extension_valid
        validation.status = "valid" if validation.valid else "blocked"
        return validation

    def _is_network_path(self, path: str) -> bool:
        lowered = path.lower()
        return lowered.startswith("\\\\") or lowered.startswith("http://") or lowered.startswith("https://")

    def _under_any_root(self, path: Path, roots: list[str]) -> bool:
        if not roots:
            return False
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
