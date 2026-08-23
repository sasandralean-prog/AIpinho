from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_METADATA_EVIDENCE_KEYS,
    MediaMetadataBackendDescriptor,
    MediaMetadataBackendError,
    RawMediaMetadataField,
    RawMediaMetadataResult,
)
from aipinho.capabilities.media_metadata.environment import discover_media_tool


class FFprobeMediaMetadataBackend:
    backend_id = "ffprobe"
    version = "1"

    def __init__(self, executable: str = "ffprobe", timeout_s: float = 10.0) -> None:
        self.executable = executable
        self.timeout_s = timeout_s

    def descriptor(self) -> MediaMetadataBackendDescriptor:
        discovery = discover_media_tool(self.executable, tool_id="ffprobe", timeout_s=min(self.timeout_s, 5.0))
        return MediaMetadataBackendDescriptor(
            backend_id=self.backend_id,
            backend_type="external_cli",
            version=self.version,
            supported_extensions=["mp3", "mp4", "m4a", "flac", "ogg", "opus", "wav"],
            supported_containers=["mp3", "mp4", "m4a", "flac", "ogg", "opus", "wav"],
            supported_attributes=list(MEDIA_METADATA_EVIDENCE_KEYS),
            requires_external_binary=True,
            dependency_name=self.executable,
            dependency_version=discovery.version,
            resolved_executable_path=discovery.resolved_executable_path,
            environment_reason_code=discovery.reason_code,
            environment_message=discovery.message,
            confidence_profile={"technical_metadata": 0.9, "descriptive_metadata": 0.75},
            limitations=[
                "Requires ffprobe CLI in PATH and JSON output support.",
                "ffmpeg is a media-environment dependency; ffprobe is required for this metadata backend.",
            ],
            status=discovery.status,
        )

    def probe(self, *, file_path: str, entity_ref: dict[str, Any] | None = None) -> RawMediaMetadataResult:
        discovery = discover_media_tool(self.executable, tool_id="ffprobe", timeout_s=min(self.timeout_s, 5.0))
        if not discovery.available or not discovery.resolved_executable_path:
            return self._error_result(
                file_path=file_path,
                entity_ref=entity_ref,
                code=discovery.reason_code or "FFPROBE_NOT_AVAILABLE",
                message=discovery.message or "ffprobe executable is not available in PATH.",
                discovery=discovery,
            )
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="MEDIA_BACKEND_UNSUPPORTED_FORMAT", message="Media file path does not exist or is not a file.", discovery=discovery)
        command = [
            discovery.resolved_executable_path,
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
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_TIMEOUT", message="ffprobe execution timed out.", discovery=discovery)
        except Exception as exc:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_RUNTIME_ERROR", message=str(exc) or exc.__class__.__name__, discovery=discovery)
        if completed.returncode != 0:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_RUNTIME_ERROR", message=(completed.stderr or "ffprobe failed").strip(), discovery=discovery)
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="FFPROBE_INVALID_JSON", message=str(exc), discovery=discovery)
        fields = self._fields(payload, str(path))
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version=self.version,
            file_ref=str(path),
            entity_ref=entity_ref or {},
            raw_fields=fields,
            confidence_by_field={item.canonical_key: item.confidence for item in fields},
            provenance={
                "backend": self.backend_id,
                "command": [discovery.resolved_executable_path, "-show_format", "-show_streams"],
                "shell": False,
                "file_path": str(path),
                "ffprobe_version": discovery.version,
                "ffprobe_version_first_line": discovery.version_first_line,
            },
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

    def _error_result(self, *, file_path: str, entity_ref: dict[str, Any] | None, code: str, message: str, discovery: Any | None = None) -> RawMediaMetadataResult:
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version=self.version,
            file_ref=file_path,
            entity_ref=entity_ref or {},
            errors=[MediaMetadataBackendError(code=code, message=message, backend_id=self.backend_id)],
            limitations_by_field={key: [message] for key in MEDIA_METADATA_EVIDENCE_KEYS},
            provenance={
                "backend": self.backend_id,
                "file_path": file_path,
                "resolved_executable_path": getattr(discovery, "resolved_executable_path", None),
                "ffprobe_status": getattr(discovery, "status", None),
                "ffprobe_version": getattr(discovery, "version", None),
            },
            raw_ref=file_path,
        )
