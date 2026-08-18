from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_METADATA_CANONICAL_KEYS,
    MediaMetadataBackendDescriptor,
    MediaMetadataBackendError,
    RawMediaMetadataField,
    RawMediaMetadataResult,
)


class FFprobeMediaMetadataBackend:
    backend_id = "ffprobe"
    version = "1"

    def __init__(self, executable: str = "ffprobe", timeout_s: float = 10.0) -> None:
        self.executable = executable
        self.timeout_s = timeout_s

    def descriptor(self) -> MediaMetadataBackendDescriptor:
        available = shutil.which(self.executable) is not None
        return MediaMetadataBackendDescriptor(
            backend_id=self.backend_id,
            backend_type="external_cli",
            version=self.version,
            supported_extensions=["mp3", "mp4", "m4a", "flac", "ogg", "opus", "wav"],
            supported_containers=["mp3", "mp4", "m4a", "flac", "ogg", "opus", "wav"],
            supported_attributes=list(MEDIA_METADATA_CANONICAL_KEYS),
            requires_external_binary=True,
            dependency_name=self.executable,
            confidence_profile={"technical_metadata": 0.9, "descriptive_metadata": 0.75},
            limitations=["Requires ffprobe CLI in PATH and JSON output support."],
            status="available" if available else "unavailable",
        )

    def probe(self, *, file_path: str, entity_ref: dict[str, Any] | None = None) -> RawMediaMetadataResult:
        if shutil.which(self.executable) is None:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_NOT_AVAILABLE", message="ffprobe executable is not available in PATH.")
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="MEDIA_BACKEND_UNSUPPORTED_FORMAT", message="Media file path does not exist or is not a file.")
        command = [
            self.executable,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout_s, check=False)
        except subprocess.TimeoutExpired:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_TIMEOUT", message="ffprobe execution timed out.")
        except Exception as exc:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_RUNTIME_ERROR", message=str(exc) or exc.__class__.__name__)
        if completed.returncode != 0:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_RUNTIME_ERROR", message=(completed.stderr or "ffprobe failed").strip())
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_INVALID_JSON", message=str(exc))
        fields = self._fields(payload, str(path))
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version=self.version,
            file_ref=str(path),
            entity_ref=entity_ref or {},
            raw_fields=fields,
            confidence_by_field={item.canonical_key: item.confidence for item in fields},
            provenance={"backend": self.backend_id, "command": [self.executable, "-show_format", "-show_streams"], "file_path": str(path)},
            raw_ref=str(path),
        )

    def _fields(self, payload: dict[str, Any], raw_ref: str) -> list[RawMediaMetadataField]:
        rows: list[RawMediaMetadataField] = []
        fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
        streams = payload.get("streams") if isinstance(payload.get("streams"), list) else []
        audio = next((item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"), None)
        if fmt.get("format_name"):
            rows.append(self._field("container", str(fmt["format_name"]).split(",")[0], 0.9, raw_ref))
        if audio and audio.get("codec_name"):
            rows.append(self._field("codec", str(audio["codec_name"]), 0.9, raw_ref))
        if audio and audio.get("sample_rate"):
            rows.append(self._field("sample_rate", audio["sample_rate"], 0.9, raw_ref))
        if audio and audio.get("channels"):
            rows.append(self._field("channels", audio["channels"], 0.9, raw_ref))
        bitrate = audio.get("bit_rate") if audio else None
        if not bitrate:
            bitrate = fmt.get("bit_rate")
        if bitrate:
            rows.append(self._field("bitrate", bitrate, 0.85, raw_ref))
        duration = fmt.get("duration") or (audio.get("duration") if audio else None)
        if duration:
            rows.append(self._field("duration", duration, 0.85, raw_ref))
        tags = fmt.get("tags") if isinstance(fmt.get("tags"), dict) else {}
        if tags:
            rows.append(self._field("metadata", tags, 0.75, raw_ref, semantic_type="descriptive_metadata"))
        return rows

    def _field(self, key: str, value: Any, confidence: float, raw_ref: str, *, semantic_type: str = "technical_metadata") -> RawMediaMetadataField:
        return RawMediaMetadataField(
            canonical_key=key,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            semantic_type=semantic_type,
            source_backend_id=self.backend_id,
            raw_ref=raw_ref,
        )

    def _error_result(self, *, file_path: str, entity_ref: dict[str, Any] | None, code: str, message: str) -> RawMediaMetadataResult:
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version=self.version,
            file_ref=file_path,
            entity_ref=entity_ref or {},
            errors=[MediaMetadataBackendError(code=code, message=message, backend_id=self.backend_id)],
            limitations_by_field={key: [message] for key in MEDIA_METADATA_CANONICAL_KEYS},
            provenance={"backend": self.backend_id, "file_path": file_path},
            raw_ref=file_path,
        )
