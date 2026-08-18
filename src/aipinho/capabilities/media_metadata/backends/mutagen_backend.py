from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.capabilities.media_metadata.descriptor import (
    MEDIA_METADATA_CANONICAL_KEYS,
    MediaMetadataBackendDescriptor,
    MediaMetadataBackendError,
    RawMediaMetadataField,
    RawMediaMetadataResult,
)


class MutagenMediaMetadataBackend:
    backend_id = "mutagen"
    version = "1"

    def descriptor(self) -> MediaMetadataBackendDescriptor:
        try:
            import mutagen  # type: ignore

            dependency_version = getattr(mutagen, "version_string", None) or getattr(mutagen, "__version__", None)
            status = "available"
        except Exception:
            dependency_version = None
            status = "unavailable"
        return MediaMetadataBackendDescriptor(
            backend_id=self.backend_id,
            backend_type="python_library",
            version=self.version,
            supported_extensions=["mp3", "mp4", "m4a", "flac", "ogg", "opus", "wav"],
            supported_containers=["mp3", "mp4", "m4a", "flac", "ogg", "opus", "wav"],
            supported_attributes=list(MEDIA_METADATA_CANONICAL_KEYS),
            requires_python_dependency=True,
            dependency_name="mutagen",
            dependency_version=dependency_version,
            confidence_profile={"technical_metadata": 0.9, "descriptive_metadata": 0.85, "artwork": 0.8},
            limitations=["Coverage depends on Mutagen support for the concrete container and tags."],
            status=status,
        )

    def probe(self, *, file_path: str, entity_ref: dict[str, Any] | None = None) -> RawMediaMetadataResult:
        descriptor = self.descriptor()
        if descriptor.status != "available":
            return self._error_result(
                file_path=file_path,
                entity_ref=entity_ref,
                code="MUTAGEN_NOT_IMPORTABLE",
                message="Python dependency mutagen is not available.",
            )
        try:
            from mutagen import File as MutagenFile  # type: ignore
        except Exception:
            return self._error_result(
                file_path=file_path,
                entity_ref=entity_ref,
                code="MUTAGEN_NOT_IMPORTABLE",
                message="Python dependency mutagen is not importable.",
            )
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return self._error_result(
                file_path=file_path,
                entity_ref=entity_ref,
                code="MEDIA_BACKEND_UNSUPPORTED_FORMAT",
                message="Media file path does not exist or is not a file.",
            )
        try:
            media = MutagenFile(str(path))
        except Exception as exc:
            return self._error_result(
                file_path=file_path,
                entity_ref=entity_ref,
                code="MEDIA_BACKEND_RUNTIME_ERROR",
                message=str(exc) or exc.__class__.__name__,
            )
        if media is None:
            return self._error_result(
                file_path=file_path,
                entity_ref=entity_ref,
                code="MEDIA_BACKEND_UNSUPPORTED_FORMAT",
                message="Mutagen did not recognize the file format.",
            )
        info = getattr(media, "info", None)
        tags = getattr(media, "tags", None)
        fields: list[RawMediaMetadataField] = []
        container = self._container_from_info(info)
        if container:
            fields.append(self._field("container", container, 0.85, "mutagen_info", str(path)))
        codec = self._codec_from_info(info, container)
        if codec:
            fields.append(self._field("codec", codec, 0.8, "mutagen_info", str(path)))
        for key, attr, confidence in [
            ("duration", "length", 0.9),
            ("bitrate", "bitrate", 0.85),
            ("sample_rate", "sample_rate", 0.85),
            ("channels", "channels", 0.8),
        ]:
            value = getattr(info, attr, None)
            if value not in (None, ""):
                fields.append(self._field(key, value, confidence, "mutagen_info", str(path)))
        metadata = self._tags_to_dict(tags)
        if metadata:
            fields.append(self._field("metadata", metadata, 0.75, "mutagen_tags", str(path), semantic_type="descriptive_metadata"))
        artwork_present = self._artwork_present(tags)
        if artwork_present is not None:
            fields.append(self._field("artwork", artwork_present, 0.75, "mutagen_tags", str(path), semantic_type="embedded_assets"))
        return RawMediaMetadataResult(
            backend_id=self.backend_id,
            backend_version=self.version,
            file_ref=str(path),
            entity_ref=entity_ref or {},
            container=container,
            codec=codec,
            bitrate=getattr(info, "bitrate", None),
            sample_rate=getattr(info, "sample_rate", None),
            channels=getattr(info, "channels", None),
            duration=getattr(info, "length", None),
            artwork=artwork_present,
            metadata=metadata or None,
            raw_fields=fields,
            confidence_by_field={item.canonical_key: item.confidence for item in fields},
            limitations_by_field={},
            provenance={"backend": self.backend_id, "dependency": "mutagen", "file_path": str(path)},
            raw_ref=str(path),
        )

    def _field(self, key: str, value: Any, confidence: float, source: str, raw_ref: str, *, semantic_type: str = "technical_metadata") -> RawMediaMetadataField:
        return RawMediaMetadataField(
            canonical_key=key,
            raw_value=value,
            normalized_value=value,
            confidence=confidence,
            semantic_type=semantic_type,
            source_backend_id=self.backend_id,
            raw_ref=raw_ref,
            limitations=[],
        )

    def _container_from_info(self, info: Any) -> str | None:
        mime = getattr(info, "mime", None)
        if isinstance(mime, list) and mime:
            value = str(mime[0]).split("/")[-1].lower()
            return value or None
        return None

    def _codec_from_info(self, info: Any, container: str | None) -> str | None:
        mime = getattr(info, "mime", None)
        if isinstance(mime, list) and mime:
            return str(mime[0]).split("/")[-1].lower()
        codec = getattr(info, "codec", None)
        if codec:
            return str(codec).lower()
        return None

    def _tags_to_dict(self, tags: Any) -> dict[str, Any]:
        if not tags:
            return {}
        rows: dict[str, Any] = {}
        for key in list(tags.keys())[:200]:
            value = tags.get(key)
            if key in {"APIC:", "covr"}:
                continue
            try:
                rows[str(key)] = str(value)
            except Exception:
                rows[str(key)] = repr(value)
        return rows

    def _artwork_present(self, tags: Any) -> str | None:
        if not tags:
            return None
        keys = {str(key).casefold() for key in tags.keys()}
        if any(key.startswith("apic") or key == "covr" for key in keys):
            return "embedded_present"
        return "unknown"

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
