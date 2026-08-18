from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.manual_inference_profile import ManualInferenceProfile
from aipinho.utils.yaml_loader import load_yaml_file


class ManualInferenceProfileService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "manual_inference_profiles.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def load_profiles(self) -> list[ManualInferenceProfile]:
        raw = self.config.get("profiles", {}) if isinstance(self.config.get("profiles", {}), dict) else {}
        profiles: list[ManualInferenceProfile] = []
        for profile_id, value in raw.items():
            if isinstance(value, dict):
                profile = ManualInferenceProfile(profile_id=str(profile_id), **value)
                profile.warnings.extend(self.validate_profile(profile))
                profiles.append(profile)
        return sorted(profiles, key=lambda item: item.profile_id)

    def get_profile(self, profile_id: str) -> ManualInferenceProfile | None:
        for profile in self.load_profiles():
            if profile.profile_id == profile_id:
                return profile
        return None

    def validate_profile(self, profile: ManualInferenceProfile) -> list[str]:
        warnings: list[str] = []
        if not profile.manual_only:
            warnings.append("profile_must_be_manual_only")
        if profile.allow_chat_auto_use:
            warnings.append("chat_auto_use_forbidden")
        if profile.allow_report_auto_use:
            warnings.append("report_auto_use_forbidden")
        if profile.allow_analysis_auto_use:
            warnings.append("analysis_auto_use_forbidden")
        if profile.timeout_seconds <= 0:
            warnings.append("timeout_required")
        if profile.max_input_chars <= 0:
            warnings.append("max_input_chars_required")
        if profile.max_output_tokens <= 0:
            warnings.append("max_output_tokens_required")
        return list(dict.fromkeys(warnings))

    def list_profiles(self) -> list[dict[str, object]]:
        return [profile.model_dump(exclude={"warnings"}) | {"warnings": profile.warnings} for profile in self.load_profiles()]

    def status(self) -> dict[str, object]:
        profiles = self.load_profiles()
        warnings = [warning for profile in profiles for warning in profile.warnings]
        return {
            "status": "ok" if not warnings else "degraded",
            "service": "manual_inference_profile",
            "profiles": [profile.model_dump() for profile in profiles],
            "warnings": list(dict.fromkeys(warnings)),
        }
