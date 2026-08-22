from __future__ import annotations

import re
from pathlib import Path
from typing import Any


LYRICS_EXTENSIONS = {"lrc"}


class FileContainerSignatureService:
    """Observes bounded file/container anatomy for routing diagnostics only."""

    def observe_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        extension = self._extension(entity)
        path = self._source_path(entity)
        sample = b""
        read_error = None
        if path is not None:
            try:
                with path.open("rb") as handle:
                    sample = handle.read(64)
            except OSError as exc:
                read_error = exc.__class__.__name__

        signature = self._signature(sample, extension=extension, read_error=read_error)
        observed_family = signature["observed_signature_family"]
        expected_families = self._expected_signature_families(extension)
        match = bool(expected_families and observed_family in expected_families)
        mismatch = bool(expected_families and observed_family not in {"unknown", "read_error"} and not match)
        reason = (
            "FILE_CONTAINER_SIGNATURE_READ_ERROR"
            if read_error
            else "FILE_CONTAINER_EXTENSION_MISMATCH"
            if mismatch
            else "FILE_CONTAINER_EXTENSION_MATCHED"
            if match
            else "FILE_CONTAINER_SIGNATURE_UNKNOWN"
            if observed_family == "unknown"
            else "FILE_CONTAINER_SIGNATURE_OBSERVED"
        )
        return {
            "observed_magic_bytes_sample": sample[:16].hex() if sample else "",
            "observed_signature_family": observed_family,
            "observed_container": signature["observed_container_candidate"],
            "observed_container_candidate": signature["observed_container_candidate"],
            "observed_mime_candidate": signature["observed_mime_candidate"],
            "container_confidence": signature["confidence"],
            "evidence_method": "bounded_magic_bytes",
            "byte_range": "0:64",
            "extension_container_match": match,
            "extension_container_mismatch": mismatch,
            "mismatch_reason_code": "FILE_CONTAINER_EXTENSION_MISMATCH" if mismatch else None,
            "routing_hint_only": True,
            "semantic_truth_claim": False,
            "capability_authority_bypassed": False,
            "backend_routing_implications": self._routing_implications(
                extension=extension,
                observed_family=observed_family,
                mismatch=mismatch,
            ),
            "file_anatomy_status": "observed" if sample else ("read_error" if read_error else "unknown"),
            "file_anatomy_reason_code": reason,
            "file_anatomy_limitations": "signature_is_routing_hint_not_semantic_identity",
        }

    def _signature(self, sample: bytes, *, extension: str, read_error: str | None) -> dict[str, Any]:
        if read_error:
            return {
                "observed_signature_family": "read_error",
                "observed_container_candidate": "read_error",
                "observed_mime_candidate": "application/octet-stream",
                "confidence": 0.0,
            }
        if len(sample) >= 8 and sample[4:8] == b"ftyp":
            return {
                "observed_signature_family": "iso_bmff",
                "observed_container_candidate": "mp4_or_m4a_candidate",
                "observed_mime_candidate": "audio/mp4_or_video/mp4",
                "confidence": 0.95,
            }
        if sample.startswith(bytes.fromhex("1a45dfa3")):
            return {
                "observed_signature_family": "ebml_candidate",
                "observed_container_candidate": "matroska_or_webm_candidate",
                "observed_mime_candidate": "video/webm_or_matroska",
                "confidence": 0.9,
            }
        if sample.startswith(b"ID3") or (len(sample) >= 2 and sample[0] == 0xFF and (sample[1] & 0xE0) == 0xE0):
            return {
                "observed_signature_family": "mp3_candidate",
                "observed_container_candidate": "mp3_candidate",
                "observed_mime_candidate": "audio/mpeg",
                "confidence": 0.85,
            }
        if sample.startswith(bytes.fromhex("ffd8ff")):
            return {
                "observed_signature_family": "jpeg",
                "observed_container_candidate": "jpeg",
                "observed_mime_candidate": "image/jpeg",
                "confidence": 0.95,
            }
        if sample.startswith(bytes.fromhex("89504e470d0a1a0a")):
            return {
                "observed_signature_family": "png",
                "observed_container_candidate": "png",
                "observed_mime_candidate": "image/png",
                "confidence": 0.95,
            }
        if extension in LYRICS_EXTENSIONS and self._looks_like_lrc_text(sample):
            return {
                "observed_signature_family": "text_lrc_candidate",
                "observed_container_candidate": "text_lrc_candidate",
                "observed_mime_candidate": "text/plain",
                "confidence": 0.65,
            }
        return {
            "observed_signature_family": "unknown",
            "observed_container_candidate": "unknown",
            "observed_mime_candidate": "application/octet-stream",
            "confidence": 0.0,
        }

    def _routing_implications(self, *, extension: str, observed_family: str, mismatch: bool) -> list[str]:
        if observed_family == "unknown":
            return ["container_signature_unknown"]
        if mismatch:
            return ["declared_extension_mismatch", "container_aware_backend_required"]
        if extension:
            return ["declared_extension_matched"]
        return ["routing_hint_requires_capability_authority"]

    def _looks_like_lrc_text(self, sample: bytes) -> bool:
        if not sample:
            return False
        try:
            text = sample.decode("utf-8", errors="ignore")
        except Exception:
            return False
        return bool(re.search(r"\[[0-9]{1,2}:[0-9]{2}(?:\.[0-9]{1,3})?\]", text)) or "\x00" not in text

    def _expected_signature_families(self, extension: str) -> set[str]:
        if extension in {"m4a", "mp4"}:
            return {"iso_bmff"}
        if extension == "mp3":
            return {"mp3_candidate"}
        if extension in {"jpg", "jpeg"}:
            return {"jpeg"}
        if extension == "png":
            return {"png"}
        if extension in LYRICS_EXTENSIONS:
            return {"text_lrc_candidate"}
        return set()

    def _source_path(self, entity: dict[str, Any]) -> Path | None:
        source_root = str(entity.get("source_root") or self._attribute_value(entity, "source_root") or "")
        relative_path = self._relative_path(entity)
        if not source_root or not relative_path:
            source = str(entity.get("source") or "")
            return Path(source) if source else None
        return Path(source_root) / relative_path

    def _extension(self, entity: dict[str, Any]) -> str:
        extension = str(entity.get("extension") or self._attribute_value(entity, "extension") or "")
        if not extension:
            filename = self._filename(entity)
            extension = Path(filename).suffix.lstrip(".") if filename else ""
        return extension.casefold().lstrip(".")

    def _filename(self, entity: dict[str, Any]) -> str:
        name = str(entity.get("filename") or entity.get("name") or self._attribute_value(entity, "name") or "")
        if name:
            return name
        relative_path = self._relative_path(entity)
        return Path(relative_path).name if relative_path else ""

    def _relative_path(self, entity: dict[str, Any]) -> str:
        return str(entity.get("relative_path") or self._attribute_value(entity, "relative_path") or "")

    def _attribute_value(self, entity: dict[str, Any], key: str) -> Any:
        for container_name in ("observed_attributes", "inferred_attributes"):
            container = entity.get(container_name)
            if not isinstance(container, dict):
                continue
            raw = container.get(key)
            if isinstance(raw, dict) and "value" in raw:
                return raw.get("value")
        return None
