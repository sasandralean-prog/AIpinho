from __future__ import annotations

import hashlib
import re

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_content import ArtifactContentValidation
from aipinho.services.artifacts.artifact_format_validator import ArtifactFormatValidator
from aipinho.services.artifacts.artifact_secret_scanner import ArtifactSecretScanner
from aipinho.services.artifacts.artifact_trace_service import ArtifactTraceService
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactContentValidator:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_content_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        self.format_validator = ArtifactFormatValidator()
        self.secret_scanner = ArtifactSecretScanner()
        self.trace = ArtifactTraceService()

    def validate(self, content: str | bytes | None, *, fmt: str = "markdown", artifact_type: str = "report") -> ArtifactContentValidation:
        blocked: list[str] = []
        warnings: list[str] = []
        traces = []
        settings = self.policy.get("content", {}) if isinstance(self.policy.get("content"), dict) else {}
        text = ""
        binary_free = True
        if isinstance(content, bytes):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
                binary_free = False
        elif content is None:
            text = ""
        else:
            text = str(content)
            binary_free = "\x00" not in text
        if not binary_free:
            blocked.append("binary_content")
        if not text.strip() and not bool(settings.get("allow_empty", False)):
            blocked.append("empty_content")
        max_chars = int(settings.get("max_chars", 80000))
        max_bytes = int(settings.get("max_bytes", 200000))
        encoded = text.encode("utf-8", errors="replace")
        if len(text) > max_chars or len(encoded) > max_bytes:
            blocked.append("content_too_large")
        secret_free = not self.secret_scanner.has_secret(text)
        if not secret_free and bool(settings.get("reject_secret_content", True)):
            blocked.append("secret_content")
        executable_free = not self._has_pattern(text, self.policy.get("executable_patterns", []) or [])
        if not executable_free and bool(settings.get("reject_executable_payload", True)):
            blocked.append("executable_content")
        patch_detected = self._has_pattern(text, self.policy.get("patch_patterns", []) or [])
        patch_allowed = not patch_detected or (artifact_type == "report" and bool(settings.get("allow_patch_text_in_report", False)))
        if patch_detected and not patch_allowed and bool(settings.get("reject_patch_payload_by_default", True)):
            blocked.append("patch_payload")
        format_valid, format_warnings = self.format_validator.validate(text, fmt)
        warnings.extend(format_warnings)
        if not format_valid:
            blocked.append("invalid_format")
        pretty = self.format_validator.pretty_preview(self.secret_scanner.redact(text), fmt)
        digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        traces.append(self.trace.item("artifact_content_validation", "checked", "content_policy_applied", source="config/artifacts/artifact_content_policy.yaml", data={"format": fmt, "blocked": blocked}))
        return ArtifactContentValidation(
            valid=not blocked,
            format=fmt,  # type: ignore[arg-type]
            size_valid="content_too_large" not in blocked,
            secret_free=secret_free,
            binary_free=binary_free,
            executable_free=executable_free,
            patch_payload_allowed=patch_allowed,
            format_valid=format_valid,
            blocked_reasons=list(dict.fromkeys(blocked)),
            warnings=list(dict.fromkeys(warnings)),
            redacted_preview=pretty,
            content_hash=digest,
            trace=traces,
        )

    def _has_pattern(self, content: str, patterns: list[object]) -> bool:
        return any(re.search(str(pattern), content, flags=re.MULTILINE) for pattern in patterns)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_content_validator"}
