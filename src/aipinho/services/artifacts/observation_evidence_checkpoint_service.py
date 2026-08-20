from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from aipinho.schemas.artifacts.contract_perception import EvidenceRecord, EvidenceSet
from aipinho.services.runtime.runtime_payload_ref_store import RuntimePayloadRefStore


class EvidenceCheckpointResolutionError(RuntimeError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class ObservationEvidenceCheckpointSink(Protocol):
    def write_checkpoint(
        self,
        *,
        physical_probe_key: tuple[str, str, str],
        entity_ref: dict[str, Any],
        evidence_set: EvidenceSet,
    ) -> dict[str, Any]:
        ...

    def resolve_checkpoint(self, ref: dict[str, Any]) -> EvidenceSet:
        ...


@dataclass
class RuntimeObservationEvidenceCheckpointStore:
    """Adapter from artifact execution to the existing run-scoped payload-ref store."""

    payload_refs: RuntimePayloadRefStore
    run_id: str

    def write_checkpoint(
        self,
        *,
        physical_probe_key: tuple[str, str, str],
        entity_ref: dict[str, Any],
        evidence_set: EvidenceSet,
    ) -> dict[str, Any]:
        compact_records = []
        for record in evidence_set.records:
            payload = record.model_dump(mode="json")
            payload.pop("entity_ref", None)
            compact_records.append(payload)
        checkpoint = {
            "schema_version": "post_compile_observation_evidence_checkpoint.v1",
            "checkpoint_kind": "post_compile_observation_evidence",
            "physical_probe_key": list(physical_probe_key),
            "entity_ref": entity_ref,
            "records": compact_records,
            "counts": {
                "record_count": len(compact_records),
                "canonical_keys": sorted({str(record.canonical_key or record.attribute_name or "") for record in evidence_set.records if record.canonical_key or record.attribute_name}),
            },
        }
        ref = self.payload_refs.write_payload_ref(
            run_id=self.run_id,
            key="evidence_checkpoint",
            path=f"post_compile_observation/{'/'.join(str(item) for item in physical_probe_key)}",
            value=checkpoint,
        )
        return {
            "content_ref": ref.get("content_ref"),
            "hash": ref.get("hash"),
            "sha256": ref.get("sha256") or ref.get("hash"),
            "size_bytes": ref.get("size_bytes"),
            "record_count": len(compact_records),
            "canonical_keys": checkpoint["counts"]["canonical_keys"],
            "reason_code": "POST_COMPILE_EVIDENCE_CHECKPOINTED",
            "storage_scope": "task_run_payload_refs",
            "schema_version": checkpoint["schema_version"],
        }

    def resolve_checkpoint(self, ref: dict[str, Any]) -> EvidenceSet:
        content_ref = ref.get("content_ref")
        expected = str(ref.get("sha256") or ref.get("hash") or "")
        try:
            payload = self.payload_refs.read_payload_ref(content_ref, run_id=self.run_id, expected_sha256=expected or None)
        except ValueError as exc:
            if str(exc) == "payload_ref_integrity_failed":
                raise EvidenceCheckpointResolutionError("POST_COMPILE_EVIDENCE_CHECKPOINT_INTEGRITY_FAILED") from exc
            raise
        except Exception as exc:
            raise EvidenceCheckpointResolutionError("POST_COMPILE_EVIDENCE_CHECKPOINT_UNRESOLVABLE") from exc
        if not isinstance(payload, dict):
            raise EvidenceCheckpointResolutionError("POST_COMPILE_EVIDENCE_CHECKPOINT_UNRESOLVABLE")
        if payload.get("schema_version") != "post_compile_observation_evidence_checkpoint.v1":
            raise EvidenceCheckpointResolutionError("POST_COMPILE_EVIDENCE_CHECKPOINT_INTEGRITY_FAILED")
        entity_ref = payload.get("entity_ref") if isinstance(payload.get("entity_ref"), dict) else {}
        records: list[EvidenceRecord] = []
        for item in payload.get("records") or []:
            if not isinstance(item, dict):
                raise EvidenceCheckpointResolutionError("POST_COMPILE_EVIDENCE_CHECKPOINT_INTEGRITY_FAILED")
            records.append(EvidenceRecord(**{**item, "entity_ref": entity_ref}))
        entity_refs = _unique_entity_refs([record.entity_ref for record in records if record.entity_ref])
        confidence_values = [record.confidence for record in records]
        return EvidenceSet(
            records=records,
            entity_refs=entity_refs,
            attribute_names=sorted({str(record.attribute_name) for record in records if record.attribute_name}),
            canonical_keys=sorted({str(record.canonical_key) for record in records if record.canonical_key}),
            checkpoint_refs=[ref],
            record_count=len(records),
            coverage_summary={
                "observed_record_count": len(records),
                "observed_attribute_count": len({record.attribute_name for record in records if record.attribute_name}),
                "observed_canonical_key_count": len({record.canonical_key for record in records if record.canonical_key}),
            },
            confidence_summary={
                "average_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
                "minimum_confidence": min(confidence_values) if confidence_values else 0.0,
                "maximum_confidence": max(confidence_values) if confidence_values else 0.0,
            },
        )


def _unique_entity_refs(entity_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for ref in entity_refs:
        key = str(ref.get("entity_id") or ref)
        rows.setdefault(key, ref)
    return [rows[key] for key in sorted(rows)]
