from __future__ import annotations

from pathlib import Path

from aipinho.schemas.vision.contracts import ImageInput, ImageInputValidation
from aipinho.services.vision.image_input_policy_service import ImageInputPolicyService
from aipinho.services.vision.image_sensitivity_scanner import ImageSensitivityScanner


class ImageInputValidator:
    def __init__(self, policy: ImageInputPolicyService | None = None, sensitivity: ImageSensitivityScanner | None = None) -> None:
        self.policy = policy or ImageInputPolicyService()
        self.sensitivity = sensitivity or ImageSensitivityScanner()

    def validate(self, image: ImageInput | None) -> ImageInputValidation:
        blocked: list[str] = []
        warnings: list[str] = []
        if image is None:
            return ImageInputValidation(status="blocked", allowed=False, blocked_reasons=["image_input_required"])
        source_ref = image.source_ref
        if source_ref is None:
            blocked.append("missing_source_ref")
        path_text = image.file_path or (source_ref.path if source_ref else None)
        file_name = image.file_name or (source_ref.file_name if source_ref else None) or path_text or ""
        suffix = Path(file_name).suffix.lower()
        if suffix and suffix not in self.policy.allowed_extensions():
            blocked.append("extension_not_allowed")
        if suffix in {".exe", ".zip", ".bat", ".cmd", ".ps1"}:
            blocked.append("executable_or_archive_file_blocked")
        if ".." in str(path_text or ""):
            blocked.append("path_traversal_blocked")
        lowered = str(path_text or "").lower()
        if lowered.startswith("c:\\pinhoabacaxiai"):
            blocked.append("forbidden_root")
        if path_text:
            path = Path(path_text)
            if path.exists() and path.is_file():
                size = path.stat().st_size
                limit = int(self.policy.limits().get("max_file_bytes", 20000000))
                if size > limit:
                    blocked.append("file_too_large")
        mime = (image.mime_type or (source_ref.mime_type if source_ref else "") or "").lower()
        if mime and mime not in self.policy.allowed_mime_types():
            blocked.append("mime_type_not_allowed")
        sensitivity = self.sensitivity.scan_text(" ".join(str(value) for value in [image.file_name, path_text, image.metadata]))
        blocked.extend([str(item) for item in sensitivity.get("blocked_reasons", [])])
        status = "ok" if not blocked else "blocked"
        return ImageInputValidation(status=status, allowed=not blocked, input=image, warnings=warnings, blocked_reasons=list(dict.fromkeys(blocked)))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "image_input_validator", "requires_source_ref": True}
