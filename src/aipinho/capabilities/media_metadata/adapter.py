from __future__ import annotations

from pathlib import PurePath
from typing import Any

from aipinho.capabilities.media_metadata.policy import MediaMetadataCapability
from aipinho.schemas.artifacts.contract_perception import ObservationTask, ObserverBinding


class MediaMetadataObserverAdapter:
    observer_id = "media_metadata_reader"
    version = "1"

    def __init__(self, capability: MediaMetadataCapability | None = None) -> None:
        self.capability = capability or MediaMetadataCapability()
        self._supported_extensions_cache: tuple[set[str], list[dict[str, str]]] | None = None

    def execute(self, task: ObservationTask, binding: ObserverBinding) -> dict[str, Any]:
        self._ensure_eligible(task)
        file_path = str(task.inputs.get("file_path") or "")
        requested_keys = task.inputs.get("requested_canonical_keys")
        if not isinstance(requested_keys, list):
            requested_keys = (task.created_from or {}).get("requested_canonical_keys")
        if not isinstance(requested_keys, list):
            requested_keys = list(task.expected_outputs or [])
        availability_snapshot = task.inputs.get("media_metadata_backend_availability_snapshot")
        media_observation_demand = task.inputs.get("media_observation_demand")
        if not isinstance(media_observation_demand, dict):
            media_observation_demand = (task.created_from or {}).get("media_observation_demand")
        return self.capability.payload_for_boundary(
            file_path=file_path,
            entity_ref=task.entity_ref,
            requested_keys=[str(item) for item in requested_keys or []],
            backend_availability_snapshot=availability_snapshot if isinstance(availability_snapshot, dict) else None,
            media_observation_demand=media_observation_demand if isinstance(media_observation_demand, dict) else None,
        )

    def applicability_decision(
        self,
        *,
        capability: Any,
        entity: dict[str, Any],
        task: ObservationTask,
        canonical_key: str,
        raw_source_ref: str,
    ) -> dict[str, Any]:
        return self.applicability_admission_decision(
            capability=capability,
            entity=entity,
            task=task,
            canonical_key=canonical_key,
            raw_source_ref=raw_source_ref,
        )

    def applicability_admission_decision(
        self,
        *,
        capability: Any,
        entity: dict[str, Any],
        task: ObservationTask,
        canonical_key: str,
        raw_source_ref: str,
    ) -> dict[str, Any]:
        """Cheap capability-owned source routing decision.

        Extension/source-role checks are routing eligibility only. They do not
        assert codec/container/title/artist Truth.
        """
        source_root_role = str(
            self._entity_value(entity, "source_root_role")
            or task.entity_ref.get("source_root_role")
            or task.inputs.get("source_root_role")
            or ""
        )
        if source_root_role and source_root_role not in {"library_root", "corpus_root"}:
            return {
                "status": "inapplicable",
                "reason_code": "MEDIA_CAPABILITY_ROOT_ROLE_INAPPLICABLE",
                "evidence": {"source_root_role": source_root_role},
            }
        source_ref = str(raw_source_ref or task.inputs.get("file_path") or task.inputs.get("source_ref") or "")
        if not source_ref:
            return {"status": "unknown", "reason_code": "MEDIA_CAPABILITY_SOURCE_REF_UNKNOWN"}
        entity_role = str(
            self._entity_value(entity, "entity_role")
            or task.entity_ref.get("entity_role")
            or task.inputs.get("entity_role")
            or ""
        )
        routing_hints = {
            str(item)
            for item in self._entity_list_value(entity, "routing_hints")
            + list(task.entity_ref.get("routing_hints") or [])
            + list(task.inputs.get("routing_hints") or [])
            if str(item).strip()
        }
        if entity_role in {"media_asset_candidate", "audio_track_candidate"} or "media_metadata_observation" in routing_hints:
            return {
                "status": "applicable",
                "reason_code": "MEDIA_CAPABILITY_ROUTING_HINT_APPLICABLE",
                "evidence": {"entity_role": entity_role, "routing_hints": sorted(routing_hints)},
            }
        extension = self._source_extension(entity=entity, source_ref=source_ref)
        supported_extensions, descriptor_failures = self._supported_extensions()
        if extension and extension in supported_extensions:
            return {
                "status": "applicable",
                "reason_code": "MEDIA_CAPABILITY_EXTENSION_DECLARED_BY_BACKEND",
                "evidence": {
                    "extension": extension,
                    "supported_extensions": sorted(supported_extensions),
                    "descriptor_failures": descriptor_failures,
                },
            }
        if descriptor_failures:
            raise RuntimeError("MEDIA_CAPABILITY_BACKEND_DESCRIPTOR_FAILED")
        if extension and supported_extensions:
            return {
                "status": "inapplicable",
                "reason_code": "MEDIA_CAPABILITY_EXTENSION_NOT_DECLARED_BY_BACKENDS",
                "evidence": {"extension": extension, "supported_extensions": sorted(supported_extensions)},
            }
        return {"status": "unknown", "reason_code": "MEDIA_CAPABILITY_APPLICABILITY_UNKNOWN"}

    def _ensure_eligible(self, task: ObservationTask) -> None:
        entity_role = str(task.inputs.get("entity_role") or task.entity_ref.get("entity_role") or "")
        source_root_role = str(task.inputs.get("source_root_role") or task.entity_ref.get("source_root_role") or "")
        file_path = str(task.inputs.get("file_path") or "")
        if entity_role not in {"media_asset_candidate", "audio_track_candidate"}:
            raise ValueError("MEDIA_CAPABILITY_ENTITY_ROLE_REJECTED")
        if source_root_role not in {"library_root", "corpus_root"}:
            raise ValueError("MEDIA_CAPABILITY_ROOT_ROLE_REJECTED")
        if not file_path:
            raise ValueError("MEDIA_CAPABILITY_FILE_PATH_MISSING")

    def _supported_extensions(self) -> tuple[set[str], list[dict[str, str]]]:
        if self._supported_extensions_cache is not None:
            supported, failures = self._supported_extensions_cache
            return set(supported), [dict(item) for item in failures]
        supported: set[str] = set()
        failures: list[dict[str, str]] = []
        for backend_id, backend in getattr(self.capability, "backends", {}).items():
            try:
                descriptor = backend.descriptor() if hasattr(backend, "descriptor") else None
            except Exception as exc:
                failures.append({
                    "backend_id": str(backend_id),
                    "exception_class": type(exc).__name__,
                    "exception_reason": str(exc)[:200],
                })
                continue
            if isinstance(descriptor, dict):
                extensions = descriptor.get("supported_extensions") or []
            else:
                extensions = getattr(descriptor, "supported_extensions", []) or []
            supported.update(str(item).lower().lstrip(".") for item in extensions if str(item).strip())
        self._supported_extensions_cache = (set(supported), [dict(item) for item in failures])
        return supported, failures

    def _source_extension(self, *, entity: dict[str, Any], source_ref: str) -> str:
        value = self._entity_value(entity, "extension")
        if value:
            return str(value).lower().lstrip(".")
        suffix = PurePath(source_ref).suffix
        return suffix.lower().lstrip(".")

    def _entity_value(self, entity: dict[str, Any], key: str) -> Any | None:
        if key in entity and entity.get(key) not in (None, ""):
            return entity.get(key)
        attributes = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
        value = attributes.get(key)
        if isinstance(value, dict):
            return value.get("value")
        if value not in (None, ""):
            return value
        observed = entity.get("observed_attributes") if isinstance(entity.get("observed_attributes"), dict) else {}
        value = observed.get(key)
        if isinstance(value, dict):
            return value.get("value")
        return value if value not in (None, "") else None

    def _entity_list_value(self, entity: dict[str, Any], key: str) -> list[Any]:
        value = self._entity_value(entity, key)
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if value in (None, ""):
            return []
        return [value]
