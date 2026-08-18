from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from aipinho.schemas.pinhoforge_bridge import PinhoForgeBridgeManifest, PinhoForgeProviderStatus
from aipinho.services.events.event_core import redact_payload


class PinhoForgeManifestReader:
    def read(self, path: Path) -> PinhoForgeBridgeManifest:
        if not path.exists():
            raise FileNotFoundError("pinhoforge_manifest_not_found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        sanitized = redact_payload(payload)
        try:
            return PinhoForgeBridgeManifest.model_validate(sanitized)
        except ValidationError as exc:
            raise ValueError("pinhoforge_manifest_invalid") from exc

    def status(self, path: Path | None, *, provider_id: str = "pinhoforge_studio") -> PinhoForgeProviderStatus:
        if path is None:
            return PinhoForgeProviderStatus(
                provider_id=provider_id,
                status="missing_manifest_path",
                manifest_loaded=False,
                execution_enabled=False,
                errors=["pinhoforge_manifest_path_not_configured"],
            )
        try:
            manifest = self.read(path)
        except FileNotFoundError:
            return PinhoForgeProviderStatus(
                provider_id=provider_id,
                status="manifest_not_found",
                manifest_loaded=False,
                manifest_path_sanitized=self._sanitize_path(path),
                execution_enabled=False,
                errors=["pinhoforge_manifest_not_found"],
            )
        except (json.JSONDecodeError, ValueError):
            return PinhoForgeProviderStatus(
                provider_id=provider_id,
                status="invalid_manifest",
                manifest_loaded=False,
                manifest_path_sanitized=self._sanitize_path(path),
                execution_enabled=False,
                errors=["pinhoforge_manifest_invalid"],
            )
        return PinhoForgeProviderStatus(
            provider_id=manifest.provider_id,
            status="ready_for_discovery",
            mode=manifest.bridge_mode,
            execution_enabled=False,
            manifest_loaded=True,
            manifest_path_sanitized=self._sanitize_path(path),
            capability_count=len(manifest.capabilities),
            module_count=len(manifest.modules),
            allowed_operations=["handshake", "health", "manifest", "readiness"],
            blocked_operations=["execute"],
            warnings=manifest.warnings,
        )

    def _sanitize_path(self, path: Path) -> str:
        text = str(path)
        home = os.path.expanduser("~")
        if home and text.lower().startswith(home.lower()):
            return "%USER_HOME%" + text[len(home):]
        return str(redact_payload(text))
