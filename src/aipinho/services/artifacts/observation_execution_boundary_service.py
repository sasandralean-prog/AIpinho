from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Protocol

from aipinho.schemas.artifacts.contract_perception import (
    EvidenceRecord,
    EvidenceSet,
    ObservationCapability,
    ObservationExecutionError,
    ObservationExecutionPolicy,
    ObservationExecutionResult,
    ObservationExecutionTimelineEvent,
    ObservationTask,
    ObserverBinding,
)


class ObserverAdapter(Protocol):
    """Adapter contract for observational capabilities.

    Adapters do not decide truth, write artifacts, or update completion. They
    only return raw/normalized observations that the boundary can turn into
    EvidenceRecord objects.
    """

    observer_id: str
    version: str

    def execute(self, task: ObservationTask, binding: ObserverBinding) -> dict[str, Any]:
        ...


class ObservationExecutionBoundaryService:
    """Governed boundary for executing ObservationTask units.

    The boundary is intentionally generic. It knows about contracts, bindings,
    policy, errors, and evidence provenance; it does not know media, CSV,
    FireTest, or renderer behavior.
    """

    def __init__(self, adapters: dict[str, ObserverAdapter] | None = None) -> None:
        self.adapters = adapters or {}

    def execute(
        self,
        *,
        task: ObservationTask,
        capability: ObservationCapability | None,
        policy: ObservationExecutionPolicy | None = None,
    ) -> ObservationExecutionResult:
        started = self._now()
        events = [
            self._event(
                "observation_execution_started",
                task=task,
                capability_id=capability.capability_id if capability else task.capability_id,
                status="EXECUTING",
                message="Observation execution boundary entered.",
            )
        ]
        policy = policy or ObservationExecutionPolicy()
        if task.status == "BLOCKED_NO_CAPABILITY" or capability is None:
            error = self._error(
                "OBSERVER_NOT_BOUND",
                "No capability is available for this observation task.",
                task=task,
                capability=capability,
            )
            return self._blocked_result(
                task=task,
                capability=capability,
                status="BLOCKED_NO_CAPABILITY",
                started_at=started,
                events=events,
                errors=[error],
            )
        if task.status != "READY_FOR_OBSERVER":
            error = self._error(
                "OBSERVER_INPUT_SCHEMA_INVALID",
                "ObservationTask is not ready for observer execution.",
                task=task,
                capability=capability,
                details={"task_status": task.status},
            )
            return self._blocked_result(
                task=task,
                capability=capability,
                status="BLOCKED_PRECONDITION",
                started_at=started,
                events=events,
                errors=[error],
            )

        binding = self._binding_for(capability)
        if binding is None:
            error = self._error(
                "OBSERVER_NOT_BOUND",
                "Capability has no observer binding.",
                task=task,
                capability=capability,
            )
            return self._blocked_result(
                task=task,
                capability=capability,
                status="BLOCKED_OBSERVER_ERROR",
                started_at=started,
                events=events,
                errors=[error],
            )

        policy_error = self._policy_error(task=task, capability=capability, policy=policy)
        if policy_error is not None:
            return self._blocked_result(
                task=task,
                capability=capability,
                binding=binding,
                status="BLOCKED_POLICY",
                started_at=started,
                events=events,
                errors=[policy_error],
            )

        input_error = self._input_error(task=task, capability=capability, binding=binding)
        if input_error is not None:
            return self._blocked_result(
                task=task,
                capability=capability,
                binding=binding,
                status="BLOCKED_PRECONDITION",
                started_at=started,
                events=events,
                errors=[input_error],
            )

        adapter = self.adapters.get(binding.adapter_id or binding.observer_id)
        if adapter is None:
            error = self._error(
                "OBSERVER_NOT_BOUND",
                "No adapter is registered for the observer binding.",
                task=task,
                capability=capability,
                observer_id=binding.observer_id,
                details={"adapter_id": binding.adapter_id},
            )
            return self._blocked_result(
                task=task,
                capability=capability,
                binding=binding,
                status="BLOCKED_OBSERVER_ERROR",
                started_at=started,
                events=events,
                errors=[error],
            )

        started_monotonic = time.monotonic()
        try:
            raw = adapter.execute(task, binding)
        except Exception as exc:  # pragma: no cover - exact exception type belongs to adapter
            code = self._adapter_error_code(exc)
            error = self._error(
                code,
                str(exc) or exc.__class__.__name__,
                task=task,
                capability=capability,
                observer_id=binding.observer_id,
            )
            return self._blocked_result(
                task=task,
                capability=capability,
                binding=binding,
                status="BLOCKED_OBSERVER_ERROR",
                started_at=started,
                events=events,
                errors=[error],
            )
        duration_ms = int((time.monotonic() - started_monotonic) * 1000)
        timeout_ms = binding.timeout_ms or policy.timeout_ms
        if timeout_ms and duration_ms > timeout_ms:
            error = self._error(
                "OBSERVER_TIMEOUT",
                "Observer execution exceeded the configured timeout.",
                task=task,
                capability=capability,
                observer_id=binding.observer_id,
                retryable=True,
                details={"duration_ms": duration_ms, "timeout_ms": timeout_ms},
            )
            return self._blocked_result(
                task=task,
                capability=capability,
                binding=binding,
                status="BLOCKED_TIMEOUT",
                started_at=started,
                events=events,
                errors=[error],
                duration_ms=duration_ms,
            )

        observer_payload = self._observer_payload(raw)
        evidence, output_errors = self._evidence_from_raw(
            raw=raw,
            task=task,
            capability=capability,
            binding=binding,
            observer_id=binding.observer_id,
            observer_version=getattr(adapter, "version", None) or binding.observer_version,
        )
        if output_errors:
            return self._blocked_result(
                task=task,
                capability=capability,
                binding=binding,
                status="FAILED",
                started_at=started,
                events=events,
                errors=output_errors,
                duration_ms=duration_ms,
                observer_payload=observer_payload,
            )
        confidence_error = self._confidence_error(task=task, policy=policy, evidence=evidence, capability=capability, binding=binding)
        if confidence_error is not None:
            return self._blocked_result(
                task=task,
                capability=capability,
                binding=binding,
                status="FAILED",
                started_at=started,
                events=events,
                errors=[confidence_error],
                duration_ms=duration_ms,
                observer_payload=observer_payload,
            )

        finished = self._now()
        events.append(
            self._event(
                "observation_execution_finished",
                task=task,
                capability_id=capability.capability_id,
                observer_id=binding.observer_id,
                status="EXECUTED",
                message="Observer returned valid evidence.",
                details={"evidence_records": len(evidence.records)},
            )
        )
        return ObservationExecutionResult(
            observation_task_id=task.observation_task_id,
            goal_id=task.goal_id,
            strategy_id=task.strategy_id,
            capability_id=capability.capability_id,
            observer_id=binding.observer_id,
            status="EXECUTED",
            started_at=started,
            finished_at=finished,
            duration_ms=duration_ms,
            raw_ref=str(raw.get("raw_ref") or "") or None,
            evidence_set=evidence,
            errors=[],
            timeline_events=events,
            confidence=evidence.confidence_summary.get("minimum_confidence", 0.0),
            limitations=[item for record in evidence.records for item in record.limitations],
            provenance={
                "boundary": "ObservationExecutionBoundaryService",
                "policy_id": policy.policy_id,
                "observer_payload": observer_payload,
            },
        )

    def _binding_for(self, capability: ObservationCapability) -> ObserverBinding | None:
        data = capability.observer_binding or {}
        observer_id = data.get("observer_id") or data.get("adapter_id") or data.get("id")
        if not observer_id:
            return None
        return ObserverBinding(
            capability_id=capability.capability_id,
            observer_id=str(observer_id),
            adapter_id=str(data.get("adapter_id") or observer_id),
            observer_version=data.get("observer_version") or data.get("version") or capability.version,
            input_schema=data.get("input_schema") or {},
            output_schema=data.get("output_schema") or {},
            acquisition_method=str(data.get("acquisition_method") or "execute_observer"),
            timeout_ms=data.get("timeout_ms"),
            limitations=[str(item) for item in data.get("limitations") or []],
            provenance={"capability_descriptor": capability.capability_id},
        )

    def _policy_error(
        self,
        *,
        task: ObservationTask,
        capability: ObservationCapability,
        policy: ObservationExecutionPolicy,
    ) -> ObservationExecutionError | None:
        if not policy.allow_execution:
            return self._error(
                "OBSERVER_POLICY_BLOCKED",
                policy.reason or "Observation execution is blocked by policy.",
                task=task,
                capability=capability,
            )
        if (policy.requires_approval or capability.requires_approval) and not policy.approved:
            return self._error(
                "OBSERVER_POLICY_BLOCKED",
                "Observation execution requires approval.",
                task=task,
                capability=capability,
                details={"requires_approval": True},
            )
        return None

    def _input_error(
        self,
        *,
        task: ObservationTask,
        capability: ObservationCapability,
        binding: ObserverBinding,
    ) -> ObservationExecutionError | None:
        required = list(binding.input_schema.get("required") or [])
        missing = [item for item in required if item not in task.inputs]
        if missing:
            return self._error(
                "OBSERVER_INPUT_SCHEMA_INVALID",
                "ObservationTask inputs do not satisfy the observer binding schema.",
                task=task,
                capability=capability,
                observer_id=binding.observer_id,
                details={"missing_inputs": missing},
            )
        return None

    def _evidence_from_raw(
        self,
        *,
        raw: Any,
        task: ObservationTask,
        capability: ObservationCapability,
        binding: ObserverBinding,
        observer_id: str,
        observer_version: str | None,
    ) -> tuple[EvidenceSet, list[ObservationExecutionError]]:
        if not isinstance(raw, dict):
            return EvidenceSet(), [
                self._error(
                    "OBSERVER_OUTPUT_SCHEMA_INVALID",
                    "Observer output must be a dictionary.",
                    task=task,
                    capability=capability,
                    observer_id=observer_id,
                )
            ]
        raw_records = raw.get("records")
        raw_observations = raw.get("observations")
        if raw_records is None and raw_observations is None:
            return EvidenceSet(), [
                self._error(
                    "OBSERVER_OUTPUT_SCHEMA_INVALID",
                    "Observer output must contain records or observations.",
                    task=task,
                    capability=capability,
                    observer_id=observer_id,
                )
            ]
        records: list[EvidenceRecord] = []
        for item in raw_records or []:
            if isinstance(item, EvidenceRecord):
                record = item
            elif isinstance(item, dict):
                record = EvidenceRecord(**self._record_payload(item, task=task, capability=capability, binding=binding, observer_id=observer_id))
            else:
                continue
            records.append(record)
        for item in raw_observations or []:
            if not isinstance(item, dict):
                continue
            records.append(EvidenceRecord(**self._record_payload(item, task=task, capability=capability, binding=binding, observer_id=observer_id)))
        if not records:
            return EvidenceSet(), [
                self._error(
                    "OBSERVER_PRODUCED_NO_EVIDENCE",
                    "Observer executed but did not produce valid evidence records.",
                    task=task,
                    capability=capability,
                    observer_id=observer_id,
                )
            ]
        for record in records:
            record.observer_id = record.observer_id or observer_id
            record.capability_id = record.capability_id or capability.capability_id
            record.provenance.setdefault("observer_version", observer_version)
            record.provenance.setdefault("boundary", "ObservationExecutionBoundaryService")
        confidence_values = [item.confidence for item in records]
        return EvidenceSet(
            records=records,
            entity_refs=[item.entity_ref for item in records if item.entity_ref],
            attribute_names=sorted({str(item.attribute_name) for item in records if item.attribute_name}),
            canonical_keys=sorted({str(item.canonical_key) for item in records if item.canonical_key}),
            coverage_summary={
                "observed_record_count": len(records),
                "observed_attribute_count": len({item.attribute_name for item in records if item.attribute_name}),
                "observed_canonical_key_count": len({item.canonical_key for item in records if item.canonical_key}),
            },
            confidence_summary={
                "average_confidence": round(sum(confidence_values) / len(confidence_values), 4),
                "minimum_confidence": min(confidence_values),
                "maximum_confidence": max(confidence_values),
            },
        ), []

    def _observer_payload(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return {}
        payload: dict[str, Any] = {}
        media_summary = raw.get("media_metadata_capability")
        if isinstance(media_summary, dict):
            payload["media_metadata_capability"] = media_summary
        return payload

    def _record_payload(
        self,
        item: dict[str, Any],
        *,
        task: ObservationTask,
        capability: ObservationCapability,
        binding: ObserverBinding,
        observer_id: str,
    ) -> dict[str, Any]:
        attribute = item.get("attribute_name") or task.attribute_name
        canonical_key = item.get("canonical_key") or task.canonical_key or attribute
        return {
            "source": item.get("source") or "observer_execution",
            "acquisition_method": item.get("acquisition_method") or binding.acquisition_method,
            "observer_id": item.get("observer_id") or observer_id,
            "capability_id": item.get("capability_id") or capability.capability_id,
            "backend_id": item.get("backend_id"),
            "entity_ref": item.get("entity_ref") or task.entity_ref,
            "attribute_name": attribute,
            "canonical_key": canonical_key,
            "raw_ref": item.get("raw_ref"),
            "normalized_value": item.get("normalized_value", item.get("value")),
            "semantic_type": item.get("semantic_type"),
            "confidence": float(item.get("confidence", capability.typical_confidence or 0.0)),
            "provenance": item.get("provenance") or {"observation_task_id": task.observation_task_id},
            "timestamp": item.get("timestamp") or self._now(),
            "ambiguity": float(item.get("ambiguity", 0.0)),
            "contradictions": item.get("contradictions") or [],
            "limitations": item.get("limitations") or [],
        }

    def _confidence_error(
        self,
        *,
        task: ObservationTask,
        policy: ObservationExecutionPolicy,
        evidence: EvidenceSet,
        capability: ObservationCapability,
        binding: ObserverBinding,
    ) -> ObservationExecutionError | None:
        required = max(float(task.inputs.get("required_confidence") or 0.0), policy.min_confidence)
        minimum = float(evidence.confidence_summary.get("minimum_confidence") or 0.0)
        if required and minimum < required:
            return self._error(
                "OBSERVER_CONFIDENCE_TOO_LOW",
                "Observer evidence confidence is below the required threshold.",
                task=task,
                capability=capability,
                observer_id=binding.observer_id,
                details={"required_confidence": required, "observed_confidence": minimum},
            )
        return None

    def _blocked_result(
        self,
        *,
        task: ObservationTask,
        capability: ObservationCapability | None,
        status: str,
        started_at: str,
        events: list[ObservationExecutionTimelineEvent],
        errors: list[ObservationExecutionError],
        binding: ObserverBinding | None = None,
        duration_ms: int | None = None,
        observer_payload: dict[str, Any] | None = None,
    ) -> ObservationExecutionResult:
        finished = self._now()
        events.append(
            self._event(
                "observation_execution_blocked",
                task=task,
                capability_id=capability.capability_id if capability else task.capability_id,
                observer_id=binding.observer_id if binding else None,
                status=status,
                reason_code=errors[0].code if errors else None,
                message=errors[0].message if errors else None,
            )
        )
        return ObservationExecutionResult(
            observation_task_id=task.observation_task_id,
            goal_id=task.goal_id,
            strategy_id=task.strategy_id,
            capability_id=capability.capability_id if capability else task.capability_id,
            observer_id=binding.observer_id if binding else None,
            status=status,
            started_at=started_at,
            finished_at=finished,
            duration_ms=duration_ms,
            evidence_set=EvidenceSet(),
            errors=errors,
            timeline_events=events,
            confidence=0.0,
            limitations=self._payload_limitations(observer_payload),
            provenance={
                "boundary": "ObservationExecutionBoundaryService",
                "observer_payload": observer_payload or {},
            },
        )

    def _payload_limitations(self, observer_payload: dict[str, Any] | None) -> list[str]:
        payload = observer_payload or {}
        media_summary = payload.get("media_metadata_capability") if isinstance(payload.get("media_metadata_capability"), dict) else {}
        return [str(item) for item in media_summary.get("limitations") or [] if item]

    def _error(
        self,
        code: str,
        message: str,
        *,
        task: ObservationTask,
        capability: ObservationCapability | None = None,
        observer_id: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> ObservationExecutionError:
        return ObservationExecutionError(
            code=code,
            message=message,
            capability_id=capability.capability_id if capability else task.capability_id,
            observer_id=observer_id,
            retryable=retryable,
            details=details or {},
        )

    def _event(
        self,
        event_type: str,
        *,
        task: ObservationTask,
        capability_id: str | None,
        observer_id: str | None = None,
        status: str | None = None,
        reason_code: str | None = None,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> ObservationExecutionTimelineEvent:
        return ObservationExecutionTimelineEvent(
            event_type=event_type,
            observation_task_id=task.observation_task_id,
            capability_id=capability_id,
            observer_id=observer_id,
            status=status,
            reason_code=reason_code,
            message=message,
            timestamp=self._now(),
            details=details or {},
        )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _adapter_error_code(self, exc: Exception) -> str:
        message = str(exc or "")
        known = {
            "MEDIA_CAPABILITY_ENTITY_ROLE_REJECTED": "MEDIA_CAPABILITY_ENTITY_ROLE_REJECTED",
            "MEDIA_CAPABILITY_ROOT_ROLE_REJECTED": "MEDIA_CAPABILITY_ROOT_ROLE_REJECTED",
            "MEDIA_CAPABILITY_FILE_PATH_MISSING": "MEDIA_CAPABILITY_FILE_PATH_MISSING",
            "MEDIA_METADATA_OBSERVER_BINDING_MISSING": "MEDIA_METADATA_OBSERVER_BINDING_MISSING",
        }
        return known.get(message, message if message.startswith(("MEDIA_", "MUTAGEN_", "FFPROBE_")) else "OBSERVER_RUNTIME_ERROR")
