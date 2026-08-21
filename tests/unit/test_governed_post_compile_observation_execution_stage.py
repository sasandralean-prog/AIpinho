from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Any

from aipinho.capabilities.media_metadata.descriptor import MEDIA_METADATA_EVIDENCE_KEYS
from aipinho.schemas.artifacts.contract_perception import (
    AttributeObservationRequirement,
    EvidenceRecord,
    EvidenceSet,
    ObservationCapability,
    ObservationPlan,
    ObservationStrategy,
    ObservationTask,
)
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry, ContractDrivenPerceptionService
from aipinho.services.artifacts.governed_observation_execution_stage_service import (
    GovernedObservationExecutionStageService,
    PostCompileObservationBudget,
)
from aipinho.services.artifacts.observation_evidence_checkpoint_service import (
    EvidenceCheckpointResolutionError,
    EvidenceCheckpointWriteError,
    RuntimeObservationEvidenceCheckpointStore,
)
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService
from aipinho.services.runtime.runtime_payload_ref_store import RuntimePayloadRefStore


class _Adapter:
    observer_id = "media_metadata_reader"
    version = "1"

    def __init__(self, *, delay_s: float = 0.0, keys: list[str] | None = None) -> None:
        self.delay_s = delay_s
        self.keys = keys or ["track_title", "artist"]
        self.calls: list[ObservationTask] = []
        self._lock = threading.Lock()
        self.active_calls = 0
        self.max_active_calls = 0

    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        with self._lock:
            self.calls.append(task)
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            if self.delay_s:
                time.sleep(self.delay_s)
            return {
                "raw_ref": task.inputs.get("file_path"),
                "observations": [
                    {
                        "entity_ref": task.entity_ref,
                        "attribute_name": key,
                        "canonical_key": key,
                        "normalized_value": f"{key}_value",
                        "confidence": 0.9,
                        "raw_ref": task.inputs.get("file_path"),
                    }
                    for key in self.keys
                ],
                "media_metadata_capability": {
                    "status": "partial",
                    "configured": True,
                    "available": True,
                    "execution_status": "partial",
                    "primary_backend": "mutagen",
                    "attempted_backends": ["mutagen"],
                    "successful_backends": ["mutagen"],
                    "fallback_backends_used": [],
                    "backend_error_counts": {},
                    "evidence_counts_by_canonical_key": {key: 1 for key in self.keys},
                    "evidence_counts_by_backend": {"mutagen": len(self.keys)},
                    "semantic_identity_evidence_counts": {
                        key: (1 if key in self.keys else 0)
                        for key in ["track_title", "artist", "album", "album_artist"]
                    },
                },
            }
        finally:
            with self._lock:
                self.active_calls -= 1

    def applicability_decision(
        self,
        *,
        capability: Any,
        entity: dict[str, Any],
        task: ObservationTask,
        canonical_key: str,
        raw_source_ref: str,
    ) -> dict[str, Any]:
        if str(getattr(capability, "capability_id", "")) != "media_metadata_reader":
            return {"status": "unknown", "reason_code": "TEST_CAPABILITY_APPLICABILITY_UNKNOWN"}
        source_root_role = str(entity.get("source_root_role") or task.entity_ref.get("source_root_role") or task.inputs.get("source_root_role") or "")
        if source_root_role and source_root_role not in {"library_root", "corpus_root"}:
            return {"status": "inapplicable", "reason_code": "MEDIA_CAPABILITY_ROOT_ROLE_INAPPLICABLE"}
        entity_role = str(entity.get("entity_role") or task.entity_ref.get("entity_role") or task.inputs.get("entity_role") or "")
        routing_hints = {
            str(item)
            for item in list(entity.get("routing_hints") or [])
            + list(task.entity_ref.get("routing_hints") or [])
            + list(task.inputs.get("routing_hints") or [])
            if str(item).strip()
        }
        if entity_role in {"media_asset_candidate", "audio_track_candidate"} or "media_metadata_observation" in routing_hints:
            return {"status": "applicable", "reason_code": "MEDIA_CAPABILITY_ROUTING_HINT_APPLICABLE"}
        supported = self._supported_extensions()
        extension = Path(str(raw_source_ref or "")).suffix.lower().lstrip(".")
        if extension and extension in supported:
            return {"status": "applicable", "reason_code": "MEDIA_CAPABILITY_EXTENSION_DECLARED_BY_BACKEND"}
        if extension and supported:
            return {"status": "inapplicable", "reason_code": "MEDIA_CAPABILITY_EXTENSION_NOT_DECLARED_BY_BACKENDS"}
        return {"status": "unknown", "reason_code": "MEDIA_CAPABILITY_APPLICABILITY_UNKNOWN"}

    def _supported_extensions(self) -> set[str]:
        capability = getattr(self, "capability", None)
        supported: set[str] = set()
        for backend in getattr(capability, "backends", {}).values():
            descriptor = backend.descriptor() if hasattr(backend, "descriptor") else None
            supported.update(str(item).lower().lstrip(".") for item in getattr(descriptor, "supported_extensions", []) or [])
        return supported


class _SupportedExtensionBackend:
    backend_id = "fake_backend"

    def __init__(self, extensions: list[str]) -> None:
        self.extensions = extensions

    def descriptor(self) -> Any:
        return type("Descriptor", (), {"supported_extensions": self.extensions})()


class _ApplicabilityCapability:
    def __init__(self, extensions: list[str]) -> None:
        self.backends = {"fake_backend": _SupportedExtensionBackend(extensions)}


class _UnsupportedAdapter(_Adapter):
    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        with self._lock:
            self.calls.append(task)
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            return {
                "raw_ref": task.inputs.get("file_path"),
                "observations": [],
                "media_metadata_capability": {
                    "status": "blocked",
                    "configured": True,
                    "available": True,
                    "execution_status": "blocked",
                    "primary_backend": "mutagen",
                    "attempted_backends": ["mutagen"],
                    "successful_backends": [],
                    "fallback_backends_used": [],
                    "backend_error_counts": {"MEDIA_BACKEND_UNSUPPORTED_FORMAT": 1},
                    "evidence_counts_by_canonical_key": {},
                    "evidence_counts_by_backend": {},
                    "semantic_identity_evidence_counts": {
                        "track_title": 0,
                        "artist": 0,
                        "album": 0,
                        "album_artist": 0,
                    },
                },
            }
        finally:
            with self._lock:
                self.active_calls -= 1


class _RuntimeFailureAdapter(_Adapter):
    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        with self._lock:
            self.calls.append(task)
        raise RuntimeError("observer exploded")


class _SilentNoEvidenceAdapter(_Adapter):
    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        with self._lock:
            self.calls.append(task)
        return {"raw_ref": task.inputs.get("file_path"), "observations": []}


class _RoleApplicabilityAdapter(_Adapter):
    def __init__(self, *, applicable_roles: set[str], keys: list[str] | None = None) -> None:
        super().__init__(keys=keys)
        self.applicable_roles = set(applicable_roles)

    def applicability_decision(
        self,
        *,
        capability: Any,
        entity: dict[str, Any],
        task: ObservationTask,
        canonical_key: str,
        raw_source_ref: str,
    ) -> dict[str, Any]:
        role = str(entity.get("entity_role") or task.entity_ref.get("entity_role") or task.inputs.get("entity_role") or "")
        if role in self.applicable_roles:
            return {"status": "applicable", "reason_code": "TEST_ROLE_APPLICABLE", "evidence": {"entity_role": role}}
        return {"status": "inapplicable", "reason_code": "TEST_ROLE_INAPPLICABLE", "evidence": {"entity_role": role}}


class _SequenceAdapter(_UnsupportedAdapter):
    def __init__(self, sequence: list[str]) -> None:
        super().__init__(keys=["artist"])
        self.sequence = list(sequence)

    def execute(self, task: ObservationTask, binding: Any) -> dict[str, Any]:
        outcome = self.sequence.pop(0) if self.sequence else "success"
        if outcome == "runtime":
            with self._lock:
                self.calls.append(task)
            raise RuntimeError("observer exploded")
        if outcome == "unsupported":
            return super().execute(task, binding)
        return _Adapter.execute(self, task, binding)


class _SnapshotCapability:
    def __init__(self, *, status: str = "available") -> None:
        self.status = status
        self.calls = 0

    def backend_availability_snapshot(self) -> dict[str, dict[str, Any]]:
        self.calls += 1
        return {
            "mutagen": {
                "backend_id": "mutagen",
                "backend_type": "fake",
                "supported_attributes": ["artist", "track_title", "codec"],
                "status": self.status,
            }
        }


class _CountingCheckpointStore(RuntimeObservationEvidenceCheckpointStore):
    def __init__(self, *, payload_refs: RuntimePayloadRefStore, run_id: str) -> None:
        super().__init__(payload_refs=payload_refs, run_id=run_id)
        self.resolve_calls = 0
        self.max_records_resolved = 0

    def resolve_checkpoint(self, ref: dict[str, Any]) -> EvidenceSet:
        self.resolve_calls += 1
        resolved = super().resolve_checkpoint(ref)
        self.max_records_resolved = max(self.max_records_resolved, len(resolved.records))
        return resolved


def _capability(
    *,
    available: bool = True,
    status: str = "available",
    attributes: list[str] | None = None,
) -> ObservationCapability:
    attrs = attributes or list(MEDIA_METADATA_EVIDENCE_KEYS)
    return ObservationCapability(
        capability_id="media_metadata_reader",
        name="Media metadata reader",
        version="1",
        domain="media_metadata",
        observable_attributes=attrs,
        supported_attribute_names=attrs,
        compatible_entity_kinds=["file", "media_asset_candidate", "*"],
        evidence_types=["media_metadata_evidence"],
        supported_strategies=["execute_observer"],
        typical_confidence=0.9,
        observer_binding={
            "observer_id": "media_metadata_reader",
            "adapter_id": "media_metadata_reader",
            "input_schema": {"required": ["file_path"]},
        },
        available=available,
        status=status,
    )


def _generic_capability(
    capability_id: str,
    *,
    consumes: list[str],
    attributes: list[str] | None = None,
    applicability_entity_roles: list[str] | None = None,
) -> ObservationCapability:
    attrs = attributes or ["generic_signal"]
    observer_binding: dict[str, Any] = {
        "observer_id": capability_id,
        "adapter_id": capability_id,
        "input_schema": {"required": ["source_ref"]},
    }
    if applicability_entity_roles is not None:
        observer_binding["applicability"] = {"entity_roles": applicability_entity_roles}
    return ObservationCapability(
        capability_id=capability_id,
        name=capability_id,
        version="1",
        domain="generic",
        observable_attributes=attrs,
        supported_attribute_names=attrs,
        compatible_entity_kinds=["file", "*"],
        consumes=consumes,
        evidence_types=["generic_evidence"],
        supported_strategies=["execute_observer"],
        typical_confidence=0.9,
        observer_binding=observer_binding,
        available=True,
        status="available",
    )


def _evidence_record(
    *,
    evidence_id: str = "evidence_artist",
    entity_id: str = "entity_1",
    canonical_key: str = "artist",
    normalized_value: str = "Artist",
    backend_id: str = "mutagen",
    limitations: list[str] | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        entity_ref={"entity_id": entity_id},
        canonical_key=canonical_key,
        attribute_name=canonical_key,
        normalized_value=normalized_value,
        backend_id=backend_id,
        capability_id="media_metadata_reader",
        observer_id="media_metadata_reader",
        raw_ref=f"raw:{canonical_key}",
        confidence=0.9,
        provenance={"raw_tag_key": canonical_key.upper(), "raw_result_id": "raw_result_1"},
        limitations=limitations or [],
    )


def _task(attribute: str, *, entity_id: str = "entity_1", source_ref: str = "media://one") -> ObservationTask:
    return ObservationTask(
        goal_id=f"goal_{attribute}_{entity_id}_{source_ref}",
        strategy_id="strategy_media",
        capability_id="media_metadata_reader",
        entity_ref={"entity_ids": [entity_id]},
        attribute_name=attribute,
        canonical_key=attribute,
        inputs={"target_entity_ids": [entity_id], "source_ref": source_ref, "required_confidence": 0.7},
        expected_outputs=[attribute],
        expected_evidence=["media_metadata_evidence"],
        status="PLANNED",
        execution_disposition="deferred_by_compile_policy",
        pre_defer_status="READY_FOR_OBSERVER",
    )


def _generic_task(
    attribute: str,
    *,
    capability_id: str,
    entity_id: str = "entity_1",
    source_ref: str = "file://one",
) -> ObservationTask:
    return ObservationTask(
        goal_id=f"goal_{attribute}_{entity_id}_{source_ref}",
        strategy_id=f"strategy_{capability_id}",
        capability_id=capability_id,
        entity_ref={"entity_ids": [entity_id]},
        attribute_name=attribute,
        canonical_key=attribute,
        inputs={"target_entity_ids": [entity_id], "source_ref": source_ref},
        expected_outputs=[attribute],
        expected_evidence=["generic_evidence"],
        status="PLANNED",
        execution_disposition="deferred_by_compile_policy",
        pre_defer_status="READY_FOR_OBSERVER",
    )


def _plan(tasks: list[ObservationTask]) -> ObservationPlan:
    return ObservationPlan(
        observation_strategies=[
            ObservationStrategy(
                goal_id="goal",
                strategy_id="strategy_media",
                strategy_kind="execute_observer",
                attribute_name="track_title",
                required_capability_kind="media_metadata",
                rationale="unit test",
            )
        ],
        observation_tasks=tasks,
    )


def _generic_plan(tasks: list[ObservationTask]) -> ObservationPlan:
    strategies = [
        ObservationStrategy(
            goal_id=task.goal_id,
            strategy_id=str(task.strategy_id),
            strategy_kind="execute_observer",
            attribute_name=task.attribute_name,
            required_capability_kind=str(task.capability_id or ""),
            rationale="unit test",
        )
        for task in tasks
    ]
    return ObservationPlan(observation_strategies=strategies, observation_tasks=tasks)


def _plan_with_requirements(
    tasks: list[ObservationTask],
    requirements: list[AttributeObservationRequirement],
) -> ObservationPlan:
    plan = _plan(tasks)
    return plan.model_copy(update={"requirements": requirements})


def _requirement(attribute: str, *, required: bool = True, evidence_required: bool = True) -> AttributeObservationRequirement:
    return AttributeObservationRequirement(
        attribute_name=attribute,
        canonical_key=attribute,
        requiredness="required" if required else "optional",
        required=required,
        nullable=False,
        evidence_required=evidence_required,
    )


def _stage(adapter: _Adapter, *, budget: PostCompileObservationBudget | None = None) -> GovernedObservationExecutionStageService:
    return GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"media_metadata_reader": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[_capability()]),
        budget=budget or PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )


def _stage_with_capability(
    adapter: _Adapter,
    *,
    capability: ObservationCapability,
    budget: PostCompileObservationBudget | None = None,
) -> GovernedObservationExecutionStageService:
    return GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"media_metadata_reader": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[capability]),
        budget=budget or PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )


def _stage_without_registered_capability(
    adapter: _Adapter,
    *,
    budget: PostCompileObservationBudget | None = None,
) -> GovernedObservationExecutionStageService:
    return GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"media_metadata_reader": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[]),
        budget=budget or PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )


def test_one_entity_many_tasks_create_one_physical_probe_and_logical_fanout() -> None:
    adapter = _Adapter(keys=["track_title", "artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("track_title"), _task("artist"), _task("album_artist")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert len(adapter.calls) == 1
    assert len(result.observation_execution_results) == 1
    assert result.telemetry["physical_probe_count"] == 1
    assert result.telemetry["files_attempted"] == 1
    assert result.telemetry["files_succeeded"] == 1
    assert result.telemetry["goals_satisfied"] == 2
    assert result.telemetry["goals_unsatisfied"] == 1
    assert result.telemetry["evidence_records_created"] == 2
    assert adapter.calls[0].expected_outputs == ["album_artist", "artist", "track_title"]
    assert adapter.calls[0].inputs["requested_canonical_keys"] == ["album_artist", "artist", "track_title"]
    identity_group = adapter.calls[0].created_from["media_observation_demand"]["semantic_requirement_groups"][0]
    assert identity_group["satisfaction"] == "ANY_OF"
    assert set(identity_group["candidate_keys"]) == {"album_artist", "artist", "track_title"}


def test_media_execution_demand_preserves_required_non_identity_claims() -> None:
    adapter = _Adapter(keys=["artist", "codec"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan_with_requirements(
            [_task("artist"), _task("codec")],
            [_requirement("codec", required=True, evidence_required=True), _requirement("artist", required=False)],
        ),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    demand = adapter.calls[0].inputs["media_observation_demand"]
    assert result.telemetry["physical_probe_count"] == 1
    assert demand["blocking_required_claims"] == [
        {"canonical_key": "codec", "satisfaction": "REQUIRED", "evidence_required": True}
    ]
    assert demand["semantic_requirement_groups"][0]["satisfaction"] == "ANY_OF"
    assert demand["optional_enrichment_claims"] == []


def test_optional_non_identity_claim_remains_enrichment() -> None:
    adapter = _Adapter(keys=["artist", "codec"])
    stage = _stage(adapter)

    stage.execute(
        observation_plan=_plan_with_requirements(
            [_task("artist"), _task("codec")],
            [_requirement("codec", required=False), _requirement("artist", required=False)],
        ),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    demand = adapter.calls[0].inputs["media_observation_demand"]
    assert demand["blocking_required_claims"] == []
    assert demand["optional_enrichment_claims"] == ["codec"]


def test_computed_metadata_status_task_does_not_create_physical_media_demand() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("metadata_status")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert adapter.calls == []
    assert result.telemetry["dedup_group_count"] == 0
    assert result.telemetry["physical_probe_count"] == 0


def test_contract_scoped_media_applicability_preserves_sidecar_and_artwork_entities_without_probe() -> None:
    adapter = _Adapter(keys=["artist"])
    adapter.capability = _ApplicabilityCapability(["mp3", "m4a", "mp4"])
    stage = _stage(adapter)
    selected_entities = [
        {"entity_id": "track", "path": "library/song.m4a", "entity_kind": "file", "entity_role": "corpus_file", "source_root_role": "library_root"},
        {"entity_id": "sidecar", "path": "library/sidecar_text.lrc", "entity_kind": "file", "entity_role": "corpus_file", "source_root_role": "library_root"},
        {"entity_id": "art", "path": "library/cover_image.jpg", "entity_kind": "file", "entity_role": "corpus_file", "source_root_role": "library_root"},
    ]

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id="track", source_ref="library/song.m4a"),
            _task("artist", entity_id="sidecar", source_ref="library/sidecar_text.lrc"),
            _task("artist", entity_id="art", source_ref="library/cover_image.jpg"),
        ]),
        selected_entities=selected_entities,
    )

    assert [call.inputs["source_ref"] for call in adapter.calls] == ["library/song.m4a"]
    assert result.telemetry["capability_applicable_count"] == 1
    assert result.telemetry["capability_inapplicable_count"] == 2
    assert result.telemetry["capability_inapplicable_reasons"] == {
        "MEDIA_CAPABILITY_EXTENSION_NOT_DECLARED_BY_BACKENDS": 2
    }
    assert {entity["entity_id"] for entity in selected_entities} == {"track", "sidecar", "art"}


def test_media_routing_hint_remains_hint_without_container_truth() -> None:
    adapter = _Adapter(keys=["artist"])
    adapter.capability = _ApplicabilityCapability(["mp3", "m4a", "mp4"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="library/mislabeled.m4a")]),
        selected_entities=[{"entity_id": "entity_1", "path": "library/mislabeled.m4a", "entity_kind": "file", "entity_role": "corpus_file", "source_root_role": "library_root"}],
    )

    assert len(adapter.calls) == 1
    assert result.telemetry["physical_probe_count"] == 1
    keys = [record.canonical_key for record in result.observation_execution_results[0].evidence_set.records]
    assert keys == ["artist"]
    assert "container" not in keys


def test_unknown_applicability_is_not_silently_treated_as_inapplicable() -> None:
    adapter = _Adapter(keys=["artist"])
    adapter.capability = _ApplicabilityCapability(["mp3", "m4a"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="library/no_extension")]),
        selected_entities=[{"entity_id": "entity_1", "path": "library/no_extension", "entity_kind": "file", "entity_role": "corpus_file", "source_root_role": "library_root"}],
    )

    assert len(adapter.calls) == 1
    assert result.telemetry["capability_applicability_unknown_count"] == 1
    assert result.telemetry["physical_probe_count"] == 1


def test_generic_capability_applicability_is_contract_and_role_scoped() -> None:
    adapter_x = _Adapter(keys=["generic_signal"])
    adapter_y = _Adapter(keys=["generic_signal"])
    stage = GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"capability_x": adapter_x, "capability_y": adapter_y}),
        observer_registry=CapabilityRegistry(capabilities=[
            _generic_capability("capability_x", consumes=["file_path"], applicability_entity_roles=["x_candidate"]),
            _generic_capability("capability_y", consumes=["file_path"], applicability_entity_roles=["y_candidate"]),
        ]),
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )

    result = stage.execute(
        observation_plan=_generic_plan([
            _generic_task("generic_signal", capability_id="capability_x", entity_id="entity_x"),
            _generic_task("generic_signal", capability_id="capability_x", entity_id="entity_y"),
            _generic_task("generic_signal", capability_id="capability_y", entity_id="entity_y"),
        ]),
        selected_entities=[
            {"entity_id": "entity_x", "path": "file://x", "entity_kind": "file", "entity_role": "x_candidate"},
            {"entity_id": "entity_y", "path": "file://y", "entity_kind": "file", "entity_role": "y_candidate"},
        ],
    )

    assert len(adapter_x.calls) == 1
    assert len(adapter_y.calls) == 1
    assert adapter_x.calls[0].inputs["entity_id"] == "entity_x"
    assert adapter_y.calls[0].inputs["entity_id"] == "entity_y"
    assert result.telemetry["capability_applicable_count"] == 2
    assert result.telemetry["capability_inapplicable_count"] == 1


def test_consumes_is_not_interpreted_as_entity_role_applicability() -> None:
    adapter = _Adapter(keys=["generic_signal"])
    stage = GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"text_capability": adapter}),
        observer_registry=CapabilityRegistry(capabilities=[
            _generic_capability("text_capability", consumes=["file_path", "text_content"])
        ]),
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )

    result = stage.execute(
        observation_plan=_generic_plan([
            _generic_task("generic_signal", capability_id="text_capability", entity_id="entity_1")
        ]),
        selected_entities=[
            {"entity_id": "entity_1", "path": "file://one", "entity_kind": "file", "entity_role": "corpus_file"}
        ],
    )

    assert len(adapter.calls) == 1
    assert result.telemetry["capability_applicability_unknown_count"] == 1
    assert result.telemetry["capability_inapplicable_count"] == 0


def test_two_fake_capabilities_own_distinct_applicability_without_stage_branching() -> None:
    adapter_x = _RoleApplicabilityAdapter(applicable_roles={"x_candidate"}, keys=["generic_signal"])
    adapter_y = _RoleApplicabilityAdapter(applicable_roles={"y_candidate"}, keys=["generic_signal"])
    stage = GovernedObservationExecutionStageService(
        observation_boundary=ObservationExecutionBoundaryService(adapters={"capability_x": adapter_x, "capability_y": adapter_y}),
        observer_registry=CapabilityRegistry(capabilities=[
            _generic_capability("capability_x", consumes=["file_path"]),
            _generic_capability("capability_y", consumes=["file_path"]),
        ]),
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25),
    )

    result = stage.execute(
        observation_plan=_generic_plan([
            _generic_task("generic_signal", capability_id="capability_x", entity_id="entity_x"),
            _generic_task("generic_signal", capability_id="capability_y", entity_id="entity_x"),
            _generic_task("generic_signal", capability_id="capability_y", entity_id="entity_y"),
        ]),
        selected_entities=[
            {"entity_id": "entity_x", "path": "file://x", "entity_kind": "file", "entity_role": "x_candidate"},
            {"entity_id": "entity_y", "path": "file://y", "entity_kind": "file", "entity_role": "y_candidate"},
        ],
    )

    assert len(adapter_x.calls) == 1
    assert len(adapter_y.calls) == 1
    assert adapter_x.calls[0].inputs["entity_id"] == "entity_x"
    assert adapter_y.calls[0].inputs["entity_id"] == "entity_y"
    assert result.telemetry["capability_applicable_count"] == 2
    assert result.telemetry["capability_inapplicable_count"] == 1
    decision_source = GovernedObservationExecutionStageService._capability_applicability_decision
    source = Path(decision_source.__code__.co_filename).read_text(encoding="utf-8")
    method_source = source[
        source.index("    def _capability_applicability_decision("):
        source.index("    def _explicit_applicability_contract_decision(")
    ]
    assert "media_metadata_reader" not in method_source
    assert "MEDIA_CAPABILITY" not in method_source
    assert "supported_extensions" not in method_source
    assert ".consumes" not in method_source


def test_expected_unsupported_outcomes_do_not_trigger_systemic_consecutive_failure_breaker() -> None:
    adapter = _UnsupportedAdapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25, max_consecutive_execution_failures=10),
    )

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id=f"entity_{index}", source_ref=f"library/{index}.m4a")
            for index in range(10)
        ]),
        selected_entities=[
            {"entity_id": f"entity_{index}", "path": f"library/{index}.m4a", "entity_role": "media_asset_candidate", "source_root_role": "library_root"}
            for index in range(10)
        ],
    )

    assert len(adapter.calls) == 10
    assert result.blocked_reason_code is None
    assert result.telemetry["expected_unsupported_count"] == 10
    assert result.telemetry["systemic_execution_failure_count"] == 0
    assert result.telemetry["current_consecutive_systemic_failures"] == 0
    assert result.telemetry["max_consecutive_systemic_failures_observed"] == 0


def test_unexplained_no_evidence_triggers_systemic_consecutive_failure_breaker() -> None:
    adapter = _SilentNoEvidenceAdapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25, max_consecutive_execution_failures=10),
    )

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id=f"entity_{index}", source_ref=f"library/{index}.m4a")
            for index in range(12)
        ]),
        selected_entities=[
            {"entity_id": f"entity_{index}", "path": f"library/{index}.m4a", "entity_role": "media_asset_candidate", "source_root_role": "library_root"}
            for index in range(12)
        ],
    )

    assert len(adapter.calls) == 10
    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_CONSECUTIVE_EXECUTION_FAILURES_EXCEEDED"
    assert result.telemetry["systemic_execution_failure_count"] == 10
    assert result.telemetry["expected_unsupported_count"] == 0
    assert result.telemetry["max_consecutive_systemic_failures_observed"] == 10


def test_actual_runtime_failures_trigger_systemic_consecutive_failure_breaker() -> None:
    adapter = _RuntimeFailureAdapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25, max_consecutive_execution_failures=10),
    )

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id=f"entity_{index}", source_ref=f"library/{index}.m4a")
            for index in range(12)
        ]),
        selected_entities=[
            {"entity_id": f"entity_{index}", "path": f"library/{index}.m4a", "entity_role": "media_asset_candidate", "source_root_role": "library_root"}
            for index in range(12)
        ],
    )

    assert len(adapter.calls) == 10
    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_CONSECUTIVE_EXECUTION_FAILURES_EXCEEDED"
    assert result.telemetry["systemic_execution_failure_count"] == 10
    assert result.telemetry["max_consecutive_systemic_failures_observed"] == 10


def test_expected_unsupported_and_success_reset_systemic_failure_streak() -> None:
    adapter = _SequenceAdapter(["runtime", "runtime", "unsupported", "runtime", "success", "runtime"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=25, max_consecutive_execution_failures=3),
    )

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id=f"entity_{index}", source_ref=f"library/{index}.m4a")
            for index in range(6)
        ]),
        selected_entities=[
            {"entity_id": f"entity_{index}", "path": f"library/{index}.m4a", "entity_role": "media_asset_candidate", "source_root_role": "library_root"}
            for index in range(6)
        ],
    )

    assert len(adapter.calls) == 6
    assert result.blocked_reason_code is None
    assert result.telemetry["systemic_execution_failure_count"] == 4
    assert result.telemetry["expected_unsupported_count"] == 1
    assert result.telemetry["max_consecutive_systemic_failures_observed"] == 2
    assert result.telemetry["current_consecutive_systemic_failures"] == 1


def test_physical_backend_and_key_telemetry_is_authoritative_and_bounded() -> None:
    adapter = _Adapter(keys=["track_title", "artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("track_title"), _task("artist")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert result.telemetry["attempted_backends"] == {"mutagen": 1}
    assert result.telemetry["successful_backends"] == {"mutagen": 1}
    assert result.telemetry["fallback_backends_used"] == {}
    assert result.telemetry["evidence_counts_by_canonical_key"] == {"track_title": 1, "artist": 1}
    assert result.telemetry["evidence_counts_by_backend"] == {"mutagen": 2}
    assert result.telemetry["semantic_identity_evidence_counts"] == {
        "track_title": 1,
        "artist": 1,
        "album": 0,
        "album_artist": 0,
    }
    assert result.telemetry["media_metadata_capability"]["status"] == "partial"


def test_source_ref_and_entity_id_are_part_of_physical_dedup_key() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id="entity_1", source_ref="media://one"),
            _task("artist", entity_id="entity_1", source_ref="media://two"),
            _task("artist", entity_id="entity_2", source_ref="media://one"),
        ]),
        selected_entities=[
            {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
            {"entity_id": "entity_2", "path": "media://one", "entity_role": "media_asset_candidate"},
        ],
    )

    assert len(adapter.calls) == 3
    assert [call.inputs["file_path"] for call in adapter.calls] == ["media://one", "media://two", "media://one"]
    assert result.telemetry["dedup_group_count"] == 3
    assert result.telemetry["physical_probe_count"] == 3


def test_arbitrary_planned_task_is_not_executed_without_defer_marker() -> None:
    adapter = _Adapter(keys=["artist"])
    task = _task("artist")
    task = task.model_copy(update={"execution_disposition": None, "pre_defer_status": None})

    result = _stage(adapter).execute(
        observation_plan=_plan([task]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one"}],
    )

    assert adapter.calls == []
    assert result.telemetry["dedup_group_count"] == 0
    assert result.telemetry["files_attempted"] == 0


def test_timeout_quarantines_late_result_and_fail_stops_before_next_probe() -> None:
    adapter = _Adapter(delay_s=0.2, keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=20, heartbeat_interval_ms=5, max_consecutive_execution_failures=1),
    )
    checkpoints: list[str] = []

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id="entity_1", source_ref="media://one"),
            _task("artist", entity_id="entity_2", source_ref="media://two"),
        ]),
        selected_entities=[
            {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
            {"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"},
        ],
        checkpoint=lambda stage, metrics: checkpoints.append(stage),
    )

    assert len(adapter.calls) == 1
    assert result.blocked_reason_code == "POST_COMPILE_PHYSICAL_PROBE_TIMEOUT"
    assert result.telemetry["physical_probe_count"] == 1
    assert result.observation_execution_results[0].status == "BLOCKED_TIMEOUT"
    assert result.observation_execution_results[0].evidence_set.records == []
    assert "physical_probe_checkpoint" in checkpoints
    time.sleep(0.25)
    stage.execute(observation_plan=_plan([]), selected_entities=[])


def test_cross_run_quarantine_bound_blocks_second_run_without_new_probe() -> None:
    adapter = _Adapter(delay_s=0.2, keys=["artist"])
    budget = PostCompileObservationBudget(max_probe_elapsed_ms=20, heartbeat_interval_ms=5, max_quarantined_workers=1)
    stage_a = _stage(adapter, budget=budget)
    stage_b = _stage(adapter, budget=budget)

    first = stage_a.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )
    second = stage_b.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_2", source_ref="media://two")]),
        selected_entities=[{"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"}],
    )

    assert first.blocked_reason_code == "POST_COMPILE_PHYSICAL_PROBE_TIMEOUT"
    assert second.blocked_reason_code == "POST_COMPILE_OBSERVATION_QUARANTINE_BOUND_OCCUPIED"
    assert len(adapter.calls) == 1
    assert second.telemetry["physical_probe_count"] == 0
    assert second.telemetry["files_attempted"] == 0
    time.sleep(0.25)
    stage_b.execute(observation_plan=_plan([]), selected_entities=[])


def test_early_quarantine_block_preserves_configured_available_capability_telemetry() -> None:
    slow_adapter = _Adapter(delay_s=0.2, keys=["artist"])
    budget = PostCompileObservationBudget(max_probe_elapsed_ms=20, heartbeat_interval_ms=5, max_quarantined_workers=1)
    first_stage = _stage(slow_adapter, budget=budget)

    first = first_stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )
    snapshot_capability = _SnapshotCapability(status="available")
    blocked_adapter = _Adapter(keys=["artist"])
    blocked_adapter.capability = snapshot_capability
    second_stage = _stage(blocked_adapter, budget=budget)

    second = second_stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_2", source_ref="media://two")]),
        selected_entities=[{"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"}],
    )

    media = second.telemetry["media_metadata_capability"]
    assert first.blocked_reason_code == "POST_COMPILE_PHYSICAL_PROBE_TIMEOUT"
    assert second.blocked_reason_code == "POST_COMPILE_OBSERVATION_QUARANTINE_BOUND_OCCUPIED"
    assert media["configured"] is True
    assert media["available"] is True
    assert media["execution_status"] == "blocked"
    assert second.telemetry["physical_probe_count"] == 0
    assert second.telemetry["files_attempted"] == 0
    time.sleep(0.25)
    second_stage.execute(observation_plan=_plan([]), selected_entities=[])


def test_absent_media_capability_does_not_project_configured_on_early_block() -> None:
    slow_adapter = _Adapter(delay_s=0.2, keys=["artist"])
    budget = PostCompileObservationBudget(max_probe_elapsed_ms=20, heartbeat_interval_ms=5, max_quarantined_workers=1)
    first_stage = _stage(slow_adapter, budget=budget)

    first_stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )
    blocked_adapter = _Adapter(keys=["artist"])
    blocked_adapter.capability = _SnapshotCapability(status="available")
    absent_stage = _stage_without_registered_capability(blocked_adapter, budget=budget)

    result = absent_stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_2", source_ref="media://two")]),
        selected_entities=[{"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"}],
    )

    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_QUARANTINE_BOUND_OCCUPIED"
    assert result.telemetry["media_metadata_capability"]["configured"] is False
    assert result.telemetry["physical_probe_count"] == 0
    time.sleep(0.25)
    absent_stage.execute(observation_plan=_plan([]), selected_entities=[])


def test_concurrent_runs_cannot_exceed_atomic_worker_bound() -> None:
    adapter = _Adapter(delay_s=0.15, keys=["artist"])
    budget = PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=5, max_quarantined_workers=1)
    stages = [_stage(adapter, budget=budget), _stage(adapter, budget=budget)]
    barrier = threading.Barrier(3)
    results: list[Any] = []

    def run(stage: GovernedObservationExecutionStageService, entity_id: str, source_ref: str) -> None:
        barrier.wait()
        results.append(
            stage.execute(
                observation_plan=_plan([_task("artist", entity_id=entity_id, source_ref=source_ref)]),
                selected_entities=[{"entity_id": entity_id, "path": source_ref, "entity_role": "media_asset_candidate"}],
            )
        )

    threads = [
        threading.Thread(target=run, args=(stages[0], "entity_1", "media://one")),
        threading.Thread(target=run, args=(stages[1], "entity_2", "media://two")),
    ]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert len(adapter.calls) == 1
    assert adapter.max_active_calls == 1
    assert sorted(result.blocked_reason_code or "" for result in results) == [
        "",
        "POST_COMPILE_OBSERVATION_WORKER_BOUND_OCCUPIED",
    ]
    blocked = next(result for result in results if result.blocked_reason_code)
    assert blocked.telemetry["physical_probe_count"] == 0
    assert blocked.telemetry["files_attempted"] == 0


def test_backend_availability_snapshot_is_stage_scoped() -> None:
    adapter = _Adapter(keys=["artist"])
    snapshot_capability = _SnapshotCapability(status="available")
    adapter.capability = snapshot_capability
    stage = _stage(adapter)

    stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id="entity_1", source_ref="media://one"),
            _task("artist", entity_id="entity_2", source_ref="media://two"),
        ]),
        selected_entities=[
            {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
            {"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"},
        ],
    )
    assert snapshot_capability.calls == 1

    snapshot_capability.status = "unavailable"
    stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_3", source_ref="media://three")]),
        selected_entities=[{"entity_id": "entity_3", "path": "media://three", "entity_role": "media_asset_candidate"}],
    )
    assert snapshot_capability.calls == 2


def test_total_observation_deadline_blocks_active_probe_before_probe_deadline() -> None:
    adapter = _Adapter(delay_s=0.1, keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, max_total_observation_elapsed_ms=20, heartbeat_interval_ms=5),
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_TOTAL_BUDGET_EXCEEDED"
    assert len(adapter.calls) == 1
    assert result.observation_execution_results[0].evidence_set.records == []
    time.sleep(0.12)
    stage.execute(observation_plan=_plan([]), selected_entities=[])


def test_materialized_observation_bytes_budget_blocks_before_materialization() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=10, max_materialized_observation_bytes=10),
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_MATERIALIZED_BYTES_BUDGET_EXCEEDED"
    assert result.observation_execution_results[0].status == "BLOCKED_POLICY"
    assert result.observation_execution_results[0].evidence_set.records == []
    assert result.telemetry["physical_probe_count"] == 1
    assert result.telemetry["files_succeeded"] == 1
    assert result.telemetry["files_failed"] == 0
    assert result.telemetry["results_rejected_by_policy"] == 1


def test_evidence_record_budget_replaces_over_budget_result_before_materialization() -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=10, max_evidence_records=1),
    )
    selected_entities = [
        {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
        {"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"},
    ]
    perception = service.compile(
        graph={"entities": selected_entities},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["artist"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    execution = stage.execute(observation_plan=perception.observation_plan, selected_entities=selected_entities)
    materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=execution.observation_execution_results,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["artist"]},
    )

    assert execution.blocked_reason_code == "POST_COMPILE_OBSERVATION_EVIDENCE_RECORD_BUDGET_EXCEEDED"
    assert [len(result.evidence_set.records) for result in execution.observation_execution_results] == [1, 0]
    observed_entity_ids = {
        item.entity_id
        for item in materialized.attribute_observations
        if item.canonical_key == "artist" and item.observation_state == "observed"
    }
    assert observed_entity_ids == {"entity_1"}


def test_zero_consecutive_failure_limit_does_not_block_success() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(max_probe_elapsed_ms=500, heartbeat_interval_ms=10, max_consecutive_execution_failures=0),
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert result.blocked_reason_code is None
    assert result.telemetry["files_succeeded"] == 1


def test_unavailable_capability_is_revalidated_before_physical_execution() -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage_with_capability(adapter, capability=_capability(available=False, status="unavailable"))

    result = stage.execute(
        observation_plan=_plan([_task("artist", entity_id="entity_1", source_ref="media://one")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    assert adapter.calls == []
    assert result.telemetry["dedup_group_count"] == 0
    assert result.telemetry["physical_probe_count"] == 0


def test_post_execution_materialization_updates_evidence_and_attribute_observations() -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    adapter = _Adapter(keys=["artist"])
    stage = _stage(adapter)
    selected_entities = [{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}]
    perception = service.compile(
        graph={"entities": selected_entities},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["artist"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    execution = stage.execute(observation_plan=perception.observation_plan, selected_entities=selected_entities)
    materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=execution.observation_execution_results,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["artist"]},
    )

    assert perception.observation_execution_results == []
    assert materialized.observation_execution_results
    assert any(record.canonical_key == "artist" for record in materialized.evidence_set.records)
    assert any(item.canonical_key == "artist" and item.observation_state == "observed" for item in materialized.attribute_observations)
    physical_tasks = {
        item.canonical_key: item
        for item in materialized.observation_plan.observation_tasks
        if item.execution_disposition == "executed_by_post_compile_stage"
    }
    assert physical_tasks["artist"].status == "EXECUTED"
    assert physical_tasks["artist"].created_from["logical_claim_satisfaction_not_inferred"] is True


def test_contract_aware_filter_drops_unrequested_generic_metadata_but_preserves_identity() -> None:
    adapter = _Adapter(keys=["metadata", "track_title", "artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("track_title"), _task("artist")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    execution = result.observation_execution_results[0]
    assert [record.canonical_key for record in execution.evidence_set.records] == ["track_title", "artist"]
    assert result.telemetry["evidence_records_produced"] == 3
    assert result.telemetry["evidence_records_accepted"] == 2
    assert result.telemetry["evidence_records_rejected"] == 1
    assert execution.provenance["contract_aware_evidence_filter"]["discarded_record_count"] == 1


def test_contract_aware_filter_retains_generic_metadata_when_contract_requests_it() -> None:
    adapter = _Adapter(keys=["metadata", "artist"])
    stage = _stage(adapter)

    result = stage.execute(
        observation_plan=_plan([_task("metadata"), _task("artist")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
    )

    keys = [record.canonical_key for record in result.observation_execution_results[0].evidence_set.records]
    assert keys == ["metadata", "artist"]
    assert result.telemetry["evidence_records_rejected"] == 0


def test_checkpoint_receipt_retains_lightweight_result_and_resolves_records(tmp_path) -> None:
    adapter = _Adapter(keys=["artist", "track_title"])
    stage = _stage(adapter)
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist"), _task("track_title")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
        evidence_checkpoint_sink=checkpoint_store,
    )

    execution = result.observation_execution_results[0]
    assert execution.evidence_inline is False
    assert execution.evidence_set.records == []
    assert execution.evidence_record_count == 2
    assert execution.evidence_canonical_keys == ["artist", "track_title"]
    assert result.telemetry["checkpoint_count"] == 1
    assert result.telemetry["checkpoint_bytes"] > 0
    resolved = checkpoint_store.resolve_checkpoint(execution.evidence_checkpoint_ref)
    assert [record.canonical_key for record in resolved.records] == ["artist", "track_title"]
    assert len(resolved.entity_refs) == 1
    assert all(record.entity_ref["entity_id"] == "entity_1" for record in resolved.records)


def test_checkpoint_rejects_cross_entity_records_without_rewriting(tmp_path) -> None:
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )
    evidence = EvidenceSet(records=[
        _evidence_record(evidence_id="evidence_1", entity_id="entity_1"),
        _evidence_record(evidence_id="evidence_2", entity_id="entity_2"),
    ])

    try:
        checkpoint_store.write_checkpoint(
            physical_probe_key=("entity_1", "media_metadata_reader", "media://one"),
            entity_ref={"entity_id": "entity_1"},
            evidence_set=evidence,
        )
    except EvidenceCheckpointWriteError as exc:
        assert exc.reason_code == "POST_COMPILE_EVIDENCE_CHECKPOINT_ENTITY_MISMATCH"
    else:
        raise AssertionError("cross-entity checkpoint was accepted")
    assert list((tmp_path / "task_run_checkpoint" / "payload_refs").glob("*.json")) == []


def test_checkpoint_round_trip_preserves_semantic_fields_for_same_entity_records(tmp_path) -> None:
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )
    original = [
        _evidence_record(evidence_id="evidence_title", canonical_key="track_title", normalized_value="Song", limitations=["limited"]),
        _evidence_record(evidence_id="evidence_artist", canonical_key="artist", normalized_value="Artist"),
    ]
    evidence = EvidenceSet(records=original)

    ref = checkpoint_store.write_checkpoint(
        physical_probe_key=("entity_1", "media_metadata_reader", "media://one"),
        entity_ref={"entity_id": "entity_1"},
        evidence_set=evidence,
    )
    resolved = checkpoint_store.resolve_checkpoint(ref)

    for before, after in zip(original, resolved.records, strict=True):
        assert after.evidence_id == before.evidence_id
        assert after.entity_ref["entity_id"] == before.entity_ref["entity_id"]
        assert after.canonical_key == before.canonical_key
        assert after.normalized_value == before.normalized_value
        assert after.backend_id == before.backend_id
        assert after.raw_ref == before.raw_ref
        assert after.provenance == before.provenance
        assert after.confidence == before.confidence
        assert after.limitations == before.limitations


def test_checkpoint_digest_mismatch_blocks_resolution(tmp_path) -> None:
    evidence = EvidenceSet(records=[_evidence_record()])
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )
    ref = checkpoint_store.write_checkpoint(
        physical_probe_key=("entity_1", "media_metadata_reader", "media://one"),
        entity_ref={"entity_id": "entity_1"},
        evidence_set=evidence,
    )
    bad_ref = {**ref, "sha256": "0" * 64}

    try:
        checkpoint_store.resolve_checkpoint(bad_ref)
    except EvidenceCheckpointResolutionError as exc:
        assert exc.reason_code == "POST_COMPILE_EVIDENCE_CHECKPOINT_INTEGRITY_FAILED"
    else:
        raise AssertionError("checkpoint digest mismatch did not block")


def test_missing_checkpoint_ref_blocks_resolution(tmp_path) -> None:
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )

    try:
        checkpoint_store.resolve_checkpoint({"content_ref": "task_run_checkpoint/payload_refs/missing.json"})
    except EvidenceCheckpointResolutionError as exc:
        assert exc.reason_code == "POST_COMPILE_EVIDENCE_CHECKPOINT_UNRESOLVABLE"
    else:
        raise AssertionError("missing checkpoint ref did not block")


def test_malformed_checkpoint_payload_blocks_resolution(tmp_path) -> None:
    payload_refs = RuntimePayloadRefStore(root=tmp_path)
    ref = payload_refs.write_payload_ref(
        run_id="task_run_checkpoint",
        key="evidence_checkpoint",
        path="post_compile_observation/malformed",
        value={"schema_version": "wrong", "records": []},
    )
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=payload_refs,
        run_id="task_run_checkpoint",
    )

    try:
        checkpoint_store.resolve_checkpoint(ref)
    except EvidenceCheckpointResolutionError as exc:
        assert exc.reason_code == "POST_COMPILE_EVIDENCE_CHECKPOINT_INTEGRITY_FAILED"
    else:
        raise AssertionError("malformed checkpoint payload did not block")


def test_checkpointed_execution_materializes_attribute_observations_without_hydrating_final_evidence_set(tmp_path) -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    adapter = _Adapter(keys=["artist"])
    stage = _stage(adapter)
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )
    selected_entities = [{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}]
    perception = service.compile(
        graph={"entities": selected_entities},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["artist"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )

    execution = stage.execute(
        observation_plan=perception.observation_plan,
        selected_entities=selected_entities,
        evidence_checkpoint_sink=checkpoint_store,
    )
    materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=execution.observation_execution_results,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["artist"]},
        evidence_checkpoint_resolver=checkpoint_store,
    )

    observed = [item for item in materialized.attribute_observations if item.canonical_key == "artist"]
    assert len(observed) == 1
    assert observed[0].observation_state == "observed"
    assert observed[0].evidence_refs
    assert materialized.evidence_set.records == []
    assert materialized.evidence_set.checkpoint_refs
    assert materialized.evidence_set.record_count == 1


def test_retention_policy_rejection_preserves_physical_backend_telemetry(tmp_path) -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(
            max_probe_elapsed_ms=500,
            heartbeat_interval_ms=10,
            max_checkpointed_observation_bytes=1,
            max_single_checkpoint_bytes=1,
        ),
    )
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
        evidence_checkpoint_sink=checkpoint_store,
    )

    assert result.blocked_reason_code == "POST_COMPILE_EVIDENCE_CHECKPOINT_SINGLE_BYTES_EXCEEDED"
    assert result.telemetry["physical_probe_count"] == 1
    assert result.telemetry["physical_backend_attempts"] == {"mutagen": 1}
    assert result.telemetry["physical_backend_successes"] == {"mutagen": 1}
    assert result.telemetry["evidence_records_produced"] == 1
    assert result.telemetry["evidence_records_accepted"] == 0
    assert result.telemetry["evidence_records_rejected"] == 1
    assert result.telemetry["results_physically_succeeded"] == 1
    assert result.telemetry["results_accepted"] == 0
    assert result.telemetry["results_rejected_by_policy"] == 1


def test_single_checkpoint_budget_blocks_before_durable_write(tmp_path) -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(
            max_probe_elapsed_ms=500,
            heartbeat_interval_ms=10,
            max_single_checkpoint_bytes=1,
            max_checkpointed_observation_bytes=64_000_000,
        ),
    )
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )

    result = stage.execute(
        observation_plan=_plan([_task("artist")]),
        selected_entities=[{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}],
        evidence_checkpoint_sink=checkpoint_store,
    )

    assert result.blocked_reason_code == "POST_COMPILE_EVIDENCE_CHECKPOINT_SINGLE_BYTES_EXCEEDED"
    assert result.telemetry["checkpoint_count"] == 0
    assert result.telemetry["checkpoint_bytes"] == 0
    assert list((tmp_path / "task_run_checkpoint" / "payload_refs").glob("*.json")) == []


def test_cumulative_checkpoint_budget_blocks_before_crossing_write_and_preserves_prior_refs(tmp_path) -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(
            max_probe_elapsed_ms=500,
            heartbeat_interval_ms=10,
            max_single_checkpoint_bytes=512_000,
            max_checkpointed_observation_bytes=2400,
        ),
    )
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_checkpoint",
    )

    result = stage.execute(
        observation_plan=_plan([
            _task("artist", entity_id="entity_1", source_ref="media://one"),
            _task("artist", entity_id="entity_2", source_ref="media://two"),
            _task("artist", entity_id="entity_3", source_ref="media://three"),
        ]),
        selected_entities=[
            {"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"},
            {"entity_id": "entity_2", "path": "media://two", "entity_role": "media_asset_candidate"},
            {"entity_id": "entity_3", "path": "media://three", "entity_role": "media_asset_candidate"},
        ],
        evidence_checkpoint_sink=checkpoint_store,
    )

    committed = list((tmp_path / "task_run_checkpoint" / "payload_refs").glob("*.json"))
    assert result.blocked_reason_code == "POST_COMPILE_OBSERVATION_CHECKPOINT_BYTES_BUDGET_EXCEEDED"
    assert result.telemetry["checkpoint_count"] == len(committed)
    assert result.telemetry["checkpoint_bytes"] <= 2400
    assert result.telemetry["results_rejected_by_policy"] == 1
    assert result.telemetry["evidence_records_rejected"] == 1


def test_checkpointed_stage_scales_without_accumulating_hydrated_evidence_sets(tmp_path) -> None:
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(
            max_probe_elapsed_ms=500,
            heartbeat_interval_ms=10,
            max_total_observation_elapsed_ms=120000,
            max_materialized_observation_bytes=8_000_000,
            max_checkpointed_observation_bytes=64_000_000,
        ),
    )
    checkpoint_store = RuntimeObservationEvidenceCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_scale",
    )
    entity_count = 1000
    tasks = [
        _task("artist", entity_id=f"entity_{index}", source_ref=f"media://{index}")
        for index in range(entity_count)
    ]
    entities = [
        {"entity_id": f"entity_{index}", "path": f"media://{index}", "entity_role": "media_asset_candidate"}
        for index in range(entity_count)
    ]

    result = stage.execute(
        observation_plan=_plan(tasks),
        selected_entities=entities,
        evidence_checkpoint_sink=checkpoint_store,
    )

    assert result.blocked_reason_code is None
    assert result.telemetry["physical_probe_count"] == entity_count
    assert result.telemetry["checkpoint_count"] == entity_count
    assert result.telemetry["inline_materialized_bytes"] < 8_000_000
    assert all(execution.evidence_set.records == [] for execution in result.observation_execution_results)
    assert all(execution.evidence_checkpoint_ref for execution in result.observation_execution_results)


def test_checkpointed_post_execution_materialization_scales_with_bounded_resolution(tmp_path) -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    adapter = _Adapter(keys=["artist"])
    stage = _stage(
        adapter,
        budget=PostCompileObservationBudget(
            max_probe_elapsed_ms=500,
            heartbeat_interval_ms=10,
            max_total_observation_elapsed_ms=120000,
            max_materialized_observation_bytes=8_000_000,
            max_checkpointed_observation_bytes=64_000_000,
        ),
    )
    checkpoint_store = _CountingCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_scale",
    )
    entity_count = 2250
    selected_entities = [
        {"entity_id": f"entity_{index}", "path": f"media://{index}", "entity_role": "media_asset_candidate"}
        for index in range(entity_count)
    ]
    perception = service.compile(
        graph={"entities": selected_entities},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["artist"],
            "perception_compile_policy": {"mode": "compile_only"},
        },
    )
    execution = stage.execute(
        observation_plan=perception.observation_plan,
        selected_entities=selected_entities,
        evidence_checkpoint_sink=checkpoint_store,
    )

    materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=execution.observation_execution_results,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["artist"]},
        evidence_checkpoint_resolver=checkpoint_store,
    )

    observed = [
        item
        for item in materialized.attribute_observations
        if item.canonical_key == "artist" and item.observation_state == "observed"
    ]
    assert execution.blocked_reason_code is None
    assert execution.telemetry["checkpoint_count"] == entity_count
    assert checkpoint_store.resolve_calls == entity_count
    assert checkpoint_store.max_records_resolved == 1
    assert len(observed) == entity_count
    assert materialized.evidence_set.records == []
    assert len(materialized.evidence_set.checkpoint_refs) == entity_count
    assert materialized.evidence_set.record_count == entity_count
    assert materialized.media_metadata_capability["evidence_records_created"] == entity_count
    assert materialized.media_metadata_capability["semantic_identity_evidence_counts"]["artist"] == entity_count


def test_checkpointed_materialization_is_semantically_equivalent_to_inline_path(tmp_path) -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    selected_entities = [{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}]
    declared_contract = {
        "expected_kind": "tabular_collection",
        "expected_schema": ["artist", "track_title"],
        "perception_compile_policy": {"mode": "compile_only"},
    }
    perception = service.compile(graph={"entities": selected_entities}, declared_contract=declared_contract)
    stage = _stage(_Adapter(keys=["artist", "track_title"]))
    inline_execution = stage.execute(
        observation_plan=perception.observation_plan,
        selected_entities=selected_entities,
    )
    checkpoint_store = _CountingCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_equivalence",
    )
    original_result = inline_execution.observation_execution_results[0]
    checkpoint_ref = checkpoint_store.write_checkpoint(
        physical_probe_key=tuple(original_result.provenance["physical_probe_key"]),
        entity_ref=original_result.evidence_set.records[0].entity_ref,
        evidence_set=original_result.evidence_set,
    )
    checkpoint_result = stage._checkpoint_receipt_result(original_result, checkpoint_ref=checkpoint_ref)

    inline_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=inline_execution.observation_execution_results,
        declared_contract=declared_contract,
    )
    checkpoint_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=[checkpoint_result],
        declared_contract=declared_contract,
        evidence_checkpoint_resolver=checkpoint_store,
    )

    def observed_rows(result):
        return sorted(
            (
                item.entity_id,
                item.canonical_key,
                item.observed_value,
                tuple(item.evidence_refs),
                item.observation_state,
            )
            for item in result.attribute_observations
            if item.observation_state == "observed"
        )

    assert observed_rows(inline_materialized) == observed_rows(checkpoint_materialized)
    assert _knowledge_signature(inline_materialized) == _knowledge_signature(checkpoint_materialized)
    assert _assertion_signature(inline_materialized) == _assertion_signature(checkpoint_materialized)
    assert _self_review_signature(inline_materialized) == _self_review_signature(checkpoint_materialized)
    assert _coverage2_signature(inline_materialized) == _coverage2_signature(checkpoint_materialized)
    assert checkpoint_materialized.evidence_set.records == []
    assert checkpoint_materialized.evidence_set.record_count == inline_materialized.evidence_set.record_count
    assert checkpoint_store.resolve_calls == 1


def test_required_codec_claim_remains_evidence_sufficient_when_checkpointed(tmp_path) -> None:
    service = ContractDrivenPerceptionService(
        observer_registry=CapabilityRegistry(capabilities=[_capability(attributes=["codec"])])
    )
    selected_entities = [{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}]
    declared_contract = {
        "expected_kind": "tabular_collection",
        "expected_schema": ["codec"],
        "perception_compile_policy": {"mode": "compile_only"},
    }
    perception = service.compile(graph={"entities": selected_entities}, declared_contract=declared_contract)
    stage = _stage_with_capability(_Adapter(keys=["codec"]), capability=_capability(attributes=["codec"]))
    inline_execution = stage.execute(observation_plan=perception.observation_plan, selected_entities=selected_entities)
    checkpoint_store = _CountingCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_required_codec",
    )
    original_result = inline_execution.observation_execution_results[0]
    checkpoint_ref = checkpoint_store.write_checkpoint(
        physical_probe_key=tuple(original_result.provenance["physical_probe_key"]),
        entity_ref=original_result.evidence_set.records[0].entity_ref,
        evidence_set=original_result.evidence_set,
    )
    checkpoint_result = stage._checkpoint_receipt_result(original_result, checkpoint_ref=checkpoint_ref)

    inline_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=inline_execution.observation_execution_results,
        declared_contract=declared_contract,
    )
    checkpoint_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=[checkpoint_result],
        declared_contract=declared_contract,
        evidence_checkpoint_resolver=checkpoint_store,
    )

    inline_assertion = _assertion_by_key(inline_materialized, "codec")
    checkpoint_assertion = _assertion_by_key(checkpoint_materialized, "codec")
    assert inline_assertion["state"] == "OBSERVED"
    assert checkpoint_assertion == inline_assertion
    assert "INSUFFICIENT_EVIDENCE" not in checkpoint_assertion["blocking_reasons"]
    assert _knowledge_signature(inline_materialized) == _knowledge_signature(checkpoint_materialized)


def test_checkpointed_media_identity_preserves_knowledge_and_assertion_semantics(tmp_path) -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    selected_entities = [{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}]
    declared_contract = {
        "expected_kind": "tabular_collection",
        "expected_schema": ["artist"],
        "perception_compile_policy": {"mode": "compile_only"},
    }
    perception = service.compile(graph={"entities": selected_entities}, declared_contract=declared_contract)
    stage = _stage(_Adapter(keys=["artist"]))
    inline_execution = stage.execute(observation_plan=perception.observation_plan, selected_entities=selected_entities)
    checkpoint_store = _CountingCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_identity_equivalence",
    )
    original_result = inline_execution.observation_execution_results[0]
    checkpoint_ref = checkpoint_store.write_checkpoint(
        physical_probe_key=tuple(original_result.provenance["physical_probe_key"]),
        entity_ref=original_result.evidence_set.records[0].entity_ref,
        evidence_set=original_result.evidence_set,
    )
    checkpoint_result = stage._checkpoint_receipt_result(original_result, checkpoint_ref=checkpoint_ref)

    inline_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=inline_execution.observation_execution_results,
        declared_contract=declared_contract,
    )
    checkpoint_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=[checkpoint_result],
        declared_contract=declared_contract,
        evidence_checkpoint_resolver=checkpoint_store,
    )

    assert _knowledge_signature(inline_materialized) == _knowledge_signature(checkpoint_materialized)
    assert _assertion_signature(inline_materialized) == _assertion_signature(checkpoint_materialized)
    assert _self_review_signature(inline_materialized) == _self_review_signature(checkpoint_materialized)
    assert _coverage2_signature(inline_materialized) == _coverage2_signature(checkpoint_materialized)


def test_checkpointed_conflicting_evidence_does_not_become_truth_eligible(tmp_path) -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[_capability()]))
    selected_entities = [{"entity_id": "entity_1", "path": "media://one", "entity_role": "media_asset_candidate"}]
    declared_contract = {
        "expected_kind": "tabular_collection",
        "expected_schema": ["artist"],
        "perception_compile_policy": {"mode": "compile_only"},
    }
    perception = service.compile(graph={"entities": selected_entities}, declared_contract=declared_contract)
    stage = _stage(_Adapter(keys=["artist"]))
    inline_execution = stage.execute(observation_plan=perception.observation_plan, selected_entities=selected_entities)
    original_result = inline_execution.observation_execution_results[0]
    conflicted_record = original_result.evidence_set.records[0].model_copy(
        update={
            "contradictions": [{"code": "CONFLICTING_ARTIST", "other_value": "Other"}],
            "truth_eligible": True,
        }
    )
    conflicted_result = original_result.model_copy(
        update={
            "evidence_set": original_result.evidence_set.model_copy(update={"records": [conflicted_record], "record_count": 1})
        }
    )
    checkpoint_store = _CountingCheckpointStore(
        payload_refs=RuntimePayloadRefStore(root=tmp_path),
        run_id="task_run_conflict_equivalence",
    )
    checkpoint_ref = checkpoint_store.write_checkpoint(
        physical_probe_key=tuple(conflicted_result.provenance["physical_probe_key"]),
        entity_ref=conflicted_record.entity_ref,
        evidence_set=conflicted_result.evidence_set,
    )
    checkpoint_result = stage._checkpoint_receipt_result(conflicted_result, checkpoint_ref=checkpoint_ref)

    inline_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=[conflicted_result],
        declared_contract=declared_contract,
    )
    checkpoint_materialized = service.materialize_execution_results(
        perception_result=perception,
        selected_entities=selected_entities,
        execution_results=[checkpoint_result],
        declared_contract=declared_contract,
        evidence_checkpoint_resolver=checkpoint_store,
    )

    assert _knowledge_signature(inline_materialized) == _knowledge_signature(checkpoint_materialized)
    assert _assertion_signature(inline_materialized) == _assertion_signature(checkpoint_materialized)
    assertion = _assertion_by_key(checkpoint_materialized, "artist")
    assert assertion["state"] == "CONFLICTED"
    assert assertion["truth_eligible"] is False
    assert assertion["blocking_reasons"] == ("EVIDENCE_CONFLICT",)


def _knowledge_signature(result):
    return sorted(
        (
            item.canonical_key,
            (item.entity_ref or {}).get("entity_id"),
            item.value,
            item.state,
            item.fact_kind,
            item.source_kind,
            tuple(item.evidence_ids),
            tuple(item.provenance_refs),
            item.validation_eligibility,
            item.truth_eligibility,
            round(float(item.confidence or 0.0), 4),
        )
        for item in result.knowledge_records
    )


def _assertion_signature(result):
    return sorted(
        (
            item.canonical_key,
            item.state,
            tuple(item.evidence_ids),
            len(item.knowledge_ids),
            round(float(item.confidence or 0.0), 4),
            item.truth_eligible,
            tuple(item.blocking_reasons),
        )
        for item in result.semantic_assertions
    )


def _assertion_by_key(result, key: str) -> dict[str, Any]:
    for item in result.semantic_assertions:
        if item.canonical_key == key:
            return {
                "state": item.state,
                "evidence_ids": tuple(item.evidence_ids),
                "knowledge_ids_count": len(item.knowledge_ids),
                "confidence": round(float(item.confidence or 0.0), 4),
                "truth_eligible": item.truth_eligible,
                "blocking_reasons": tuple(item.blocking_reasons),
            }
    raise AssertionError(f"missing assertion for {key}")


def _self_review_signature(result):
    review = result.semantic_self_review
    question_states = sorted(
        (item.code, item.canonical_key, item.status, tuple(item.evidence_ids), item.reason_code)
        for item in review.questions
    )
    return (
        question_states,
        review.evidence_count,
        review.truth_readiness,
        review.can_promote_to_validation,
        review.can_speaker_claim,
    )


def _coverage2_signature(result):
    coverage = result.semantic_coverage_2
    return (
        coverage.knowledge_coverage,
        coverage.truth_coverage,
        coverage.is_truth_ready,
        tuple(coverage.blocking_reasons),
    )
