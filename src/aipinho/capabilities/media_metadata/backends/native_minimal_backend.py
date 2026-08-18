from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_METADATA_CANONICAL_KEYS,
    MediaMetadataBackendDescriptor,
    MediaMetadataBackendError,
    RawMediaMetadataField,
    RawMediaMetadataResult,
)


class NativeMinimalMediaProbeBackend:
    backend_id = "native_minimal"
    version = "1"

    def descriptor(self) -> MediaMetadataBackendDescriptor:
        return MediaMetadataBackendDescriptor(
            backend_id=self.backend_id,
            backend_type="native_minimal",
            version=self.version,
            supported_extensions=["mp3", "mp4", "m4a"],
            supported_containers=["mp3", "mp4", "m4a"],
            supported_attributes=["container", "codec", "bitrate", "sample_rate", "channels", "duration"],
            requires_external_binary=False,
            requires_python_dependency=False,
            confidence_profile={"container": 0.8, "codec": 0.7, "duration": 0.65, "bitrate": 0.6},
            limitations=[
                "Minimal header/box probe only.",
                "Does not decode audio.",
                "Does not implement full MP4 atom, ID3, artwork, or editorial metadata parsing.",
            ],
            status="available",
        )

    def probe(self, *, file_path: str, entity_ref: dict[str, Any] | None = None) -> RawMediaMetadataResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="MEDIA_BACKEND_UNSUPPORTED_FORMAT", message="Media file path does not exist or is not a file.")
        try:
            data = path.read_bytes()[:1024 * 1024]
        except Exception as exc:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="MEDIA_BACKEND_RUNTIME_ERROR", message=str(exc) or exc.__class__.__name__)
        if len(data) < 12:
            return self._error_result(file_path=file_path, entity_ref=entity_ref, code="MEDIA_BACKEND_NO_EVIDENCE", message="File is too small for native media probing.")
        if data[4:8] == b"ftyp":
            return self._probe_mp4(data=data, path=path, entity_ref=entity_ref)
        if data.startswith(b"ID3") or self._looks_like_mpeg_frame(data):
            return self._probe_mp3(data=data, path=path, entity_ref=entity_ref)
        return self._error_result(file_path=file_path, entity_ref=entity_ref, code="MEDIA_BACKEND_UNSUPPORTED_FORMAT", message="Native minimal backend did not recognize a supported media signature.")

    def _probe_mp4(self, *, data: bytes, path: Path, entity_ref: dict[str, Any] | None) -> RawMediaMetadataResult:
        fields: list[RawMediaMetadataField] = []
        brand = data[8:12].decode("ascii", errors="ignore").strip("\x00 ") if len(data) >= 12 else ""
        brand_key = brand.casefold()
        container = "m4a" if brand_key in {"m4a", "m4b", "m4p"} else "mp4"
        fields.append(self._field("container", container, 0.8, str(path), limitations=["container inferred from ftyp brand/header"]))
        boxes = self._mp4_boxes(data)
        stsd_type = self._find_stsd_codec(data)
        if stsd_type:
            fields.append(self._field("codec", stsd_type, 0.7, str(path), limitations=["codec read from simple stsd sample entry"]))
        else:
            fields.append(self._field("codec", None, 0.0, str(path), limitations=["stsd sample entry not found by native minimal backend"]))
        duration = self._find_mp4_duration_seconds(data)
        if duration is not None:
            fields.append(self._field("duration", duration, 0.65, str(path), limitations=["duration derived from simple mvhd/mdhd timescale"]))
        warnings = []
        if "moov" not in boxes:
            warnings.append("moov box not found in scanned prefix")
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version=self.version,
            file_ref=str(path),
            entity_ref=entity_ref or {},
            container=container,
            codec=stsd_type,
            duration=duration,
            raw_fields=[item for item in fields if item.normalized_value not in (None, "")],
            confidence_by_field={item.canonical_key: item.confidence for item in fields if item.normalized_value not in (None, "")},
            limitations_by_field={item.canonical_key: item.limitations for item in fields if item.limitations},
            warnings=warnings,
            provenance={"backend": self.backend_id, "probe": "mp4_minimal", "file_path": str(path)},
            raw_ref=str(path),
        )

    def _probe_mp3(self, *, data: bytes, path: Path, entity_ref: dict[str, Any] | None) -> RawMediaMetadataResult:
        offset = self._mp3_frame_offset(data)
        fields = [self._field("container", "mp3", 0.85, str(path), limitations=["container detected from ID3/MPEG header"])]
        if offset is not None:
            frame = self._parse_mp3_frame(data[offset:offset + 4])
            if frame:
                fields.append(self._field("codec", "mp3", 0.8, str(path), limitations=["codec detected from MPEG audio frame header"]))
                if frame.get("bitrate"):
                    fields.append(self._field("bitrate", frame["bitrate"], 0.65, str(path), limitations=["bitrate estimated from first MPEG frame"]))
                if frame.get("sample_rate"):
                    fields.append(self._field("sample_rate", frame["sample_rate"], 0.7, str(path), limitations=["sample rate read from first MPEG frame"]))
                if frame.get("channels"):
                    fields.append(self._field("channels", frame["channels"], 0.65, str(path), limitations=["channels read from first MPEG frame"]))
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version=self.version,
            file_ref=str(path),
            entity_ref=entity_ref or {},
            container="mp3",
            codec="mp3" if any(item.canonical_key == "codec" for item in fields) else None,
            bitrate=next((item.normalized_value for item in fields if item.canonical_key == "bitrate"), None),
            sample_rate=next((item.normalized_value for item in fields if item.canonical_key == "sample_rate"), None),
            channels=next((item.normalized_value for item in fields if item.canonical_key == "channels"), None),
            raw_fields=fields,
            confidence_by_field={item.canonical_key: item.confidence for item in fields},
            limitations_by_field={item.canonical_key: item.limitations for item in fields if item.limitations},
            provenance={"backend": self.backend_id, "probe": "mp3_minimal", "file_path": str(path)},
            raw_ref=str(path),
        )

    def _mp4_boxes(self, data: bytes) -> list[str]:
        boxes: list[str] = []
        offset = 0
        limit = min(len(data), 1024 * 1024)
        while offset + 8 <= limit:
            size = int.from_bytes(data[offset:offset + 4], "big")
            box_type = data[offset + 4:offset + 8].decode("ascii", errors="ignore")
            if size < 8:
                break
            boxes.append(box_type)
            offset += size
        return boxes

    def _find_stsd_codec(self, data: bytes) -> str | None:
        idx = data.find(b"stsd")
        if idx < 0:
            return None
        start = idx + 16
        if start + 4 > len(data):
            return None
        codec = data[start:start + 4].decode("ascii", errors="ignore").strip("\x00 ")
        return codec.lower() if codec else None

    def _find_mp4_duration_seconds(self, data: bytes) -> float | None:
        for box in (b"mvhd", b"mdhd"):
            idx = data.find(box)
            if idx < 0 or idx + 24 > len(data):
                continue
            version = data[idx + 4]
            if version == 0 and idx + 24 <= len(data):
                timescale = int.from_bytes(data[idx + 16:idx + 20], "big")
                duration = int.from_bytes(data[idx + 20:idx + 24], "big")
            elif version == 1 and idx + 36 <= len(data):
                timescale = int.from_bytes(data[idx + 28:idx + 32], "big")
                duration = int.from_bytes(data[idx + 32:idx + 40], "big")
            else:
                continue
            if timescale > 0 and duration >= 0:
                return round(duration / timescale, 6)
        return None

    def _looks_like_mpeg_frame(self, data: bytes) -> bool:
        offset = self._mp3_frame_offset(data)
        return offset is not None

    def _mp3_frame_offset(self, data: bytes) -> int | None:
        start = 0
        if data.startswith(b"ID3") and len(data) >= 10:
            size = 0
            for b in data[6:10]:
                size = (size << 7) | (b & 0x7F)
            start = 10 + size
        for offset in range(start, min(len(data) - 1, start + 4096)):
            if data[offset] == 0xFF and (data[offset + 1] & 0xE0) == 0xE0:
                return offset
        return None

    def _parse_mp3_frame(self, header: bytes) -> dict[str, int] | None:
        if len(header) < 4:
            return None
        value = struct.unpack(">I", header)[0]
        version_bits = (value >> 19) & 0b11
        layer_bits = (value >> 17) & 0b11
        bitrate_index = (value >> 12) & 0b1111
        sample_index = (value >> 10) & 0b11
        channel_mode = (value >> 6) & 0b11
        if version_bits == 0b01 or layer_bits == 0 or bitrate_index in {0, 15} or sample_index == 3:
            return None
        sample_rates = {
            0b11: [44100, 48000, 32000],
            0b10: [22050, 24000, 16000],
            0b00: [11025, 12000, 8000],
        }
        # MPEG Layer III tables in bps; enough for a conservative first-frame probe.
        bitrates_mpeg1_l3 = [0, 32000, 40000, 48000, 56000, 64000, 80000, 96000, 112000, 128000, 160000, 192000, 224000, 256000, 320000]
        bitrates_mpeg2_l3 = [0, 8000, 16000, 24000, 32000, 40000, 48000, 56000, 64000, 80000, 96000, 112000, 128000, 144000, 160000]
        bitrate_table = bitrates_mpeg1_l3 if version_bits == 0b11 else bitrates_mpeg2_l3
        return {
            "bitrate": bitrate_table[bitrate_index],
            "sample_rate": sample_rates[version_bits][sample_index],
            "channels": 1 if channel_mode == 0b11 else 2,
        }

    def _field(self, key: str, value: Any, confidence: float, raw_ref: str, *, limitations: list[str] | None = None) -> RawMediaMetadataField:
        return RawMediaMetadataField(
            canonical_key=key,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            semantic_type="technical_metadata",
            source_backend_id=self.backend_id,
            raw_ref=raw_ref,
            limitations=limitations or [],
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
