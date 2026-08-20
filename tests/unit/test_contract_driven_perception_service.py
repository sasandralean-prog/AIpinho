from pathlib import Path
from typing import Any

from aipinho.schemas.artifacts.contract_perception import ObservationCapability
from aipinho.services.artifacts.contract_driven_perception_service import CapabilityRegistry, ContractDrivenPerceptionService
from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import ReadonlyAnalysisArtifactRuntimeService


def _observed_entity_service() -> ObservedEntityCompilationService:
    return ObservedEntityCompilationService(
        policy={
            "scan": {"max_entities": 50, "max_depth": 3},
            "root_role_policy": {
                "project_root_role": "project_root",
                "library_root_role": "library_root",
                "external_root_role": "external_root",
                "corpus_preferred_root_roles": ["library_root", "corpus_root"],
                "corpus_excluded_entity_roles": [
                    "project_source_file",
                    "build_output_file",
                    "cache_file",
                    "generated_file",
                ],
                "build_output_segments": ["build", "target", "out"],
                "cache_segments": [".gradle", ".git", "node_modules", "cache"],
                "source_segments": ["src"],
                "generated_segments": ["generated"],
            },
            "attribute_aliases": {
                "name": ["name", "nome"],
                "extension": ["extension", "extensao"],
                "size_bytes": ["size", "tamanho"],
                "relative_path": ["path"],
                "source_root_role": ["source_root_role"],
                "entity_role": ["entity_role"],
            },
            "display_labels": {"extension": "extensão"},
        }
    )


class _RecordingPerceptionService(ContractDrivenPerceptionService):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.seen_compile_policy: dict[str, Any] | None = None

    def compile(self, *, graph: dict[str, Any], declared_contract: dict[str, Any] | None = None, stage_observer=None):
        self.seen_compile_policy = dict((declared_contract or {}).get("perception_compile_policy") or {})
        return super().compile(graph=graph, declared_contract=declared_contract, stage_observer=stage_observer)


def test_contract_observation_selects_candidates_without_domain_rules(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "extensao", "tamanho", "unobserved_metric"],
            "expected_entities": [{"entity_role": "collection_item", "declared_label": "generic_item"}],
        },
    )

    assert result.contract_observation_plan.expected_attributes == [
        "name",
        "extension",
        "size_bytes",
        "unobserved_metric",
    ]
    assert result.candidate_entity_set.candidates
    assert result.candidate_entity_set.selected_entity_ids
    assert result.specialization_hypotheses
    assert result.specialization_hypotheses[0].hypothesized_kind == "generic_item"
    assert result.semantic_coverage.coverage_ratio == 0.75
    assert result.semantic_coverage.unsupported_fields == ["unobserved_metric"]


def test_observation_plan_explains_missing_attribute_as_capability_gap(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["nome", "unobserved_metric"]},
    )

    gaps = result.semantic_coverage.semantic_gaps
    assert any(item["gap_type"] == "ATTRIBUTE_NOT_OBSERVED:unobserved_metric" for item in gaps)
    assert any(item["reason_code"] == "NO_MATCHING_CAPABILITY" for item in gaps)
    assert any("OBSERVER_CAPABILITY_MISSING" in item["details"]["reason_chain"] for item in gaps)
    codec_requirement = [
        item for item in result.observation_plan.requirements if item.attribute_name == "unobserved_metric"
    ][0]
    assert codec_requirement.gap_reason == "NO_MATCHING_CAPABILITY"
    assert codec_requirement.observation_goal_id
    assert codec_requirement.strategy_ids
    assert codec_requirement.capability_match_ids
    codec_matches = [
        item for item in result.observation_plan.capability_matches if item.goal_id == codec_requirement.observation_goal_id
    ]
    assert codec_matches
    assert all(item.match_status == "NO_MATCHING_CAPABILITY" for item in codec_matches)
    assert all(item.capability_id is None for item in codec_matches)
    assert result.observation_plan.observation_goals
    assert result.observation_plan.observation_strategies
    assert result.observation_plan.capability_decisions
    assert result.semantic_coverage.coverage_by_domain["capability_matching"]["status"] == "partial"
    assert result.semantic_coverage.coverage_by_domain["capability_matching"]["goals_without_match"] == 1
    assert result.observation_plan.observation_tasks
    codec_task = [
        item for item in result.observation_plan.observation_tasks if item.attribute_name == "unobserved_metric"
    ][0]
    assert codec_task.status == "BLOCKED_NO_CAPABILITY"
    assert codec_task.expected_evidence == ["structured_attribute_evidence"]
    assert result.evidence_set.records
    assert "unobserved_metric" not in result.evidence_set.attribute_names
    assert result.semantic_coverage_report.attribute_coverage == 0.5
    assert result.semantic_coverage_report.capability_coverage < 1.0
    assert result.semantic_coverage_report.evidence_coverage == 0.5
    assert result.semantic_coverage_report.missing_attributes == ["unobserved_metric"]
    assert result.semantic_coverage_report.missing_capabilities == ["unobserved_metric"]
    assert result.semantic_coverage_report.is_semantically_complete is False


def test_attribute_identity_normalizes_mojibake_without_losing_raw_label(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["extens?o", "dura??o"],
        },
    )

    descriptors = result.contract_observation_plan.attribute_contracts
    by_raw = {item.raw_label: item for item in descriptors}
    assert by_raw["extens?o"].canonical_key == "extension"
    assert "?" not in by_raw["extens?o"].canonical_key
    assert by_raw["extens?o"].display_label == "extensão"
    assert by_raw["extens?o"].raw_label == "extens?o"
    assert "?" not in by_raw["dura??o"].canonical_key
    assert result.contract_observation_plan.expected_attributes[0] == "extension"


def test_capability_matching_and_arbitration_are_contract_driven(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    registry = CapabilityRegistry(
        capabilities=[
            ObservationCapability(
                capability_id="generic_metric_reader",
                name="Generic metric reader",
                domain="generic",
                observable_attributes=["unobserved_metric"],
                compatible_entity_kinds=["file"],
                supported_strategies=["execute_observer"],
                typical_confidence=0.9,
                estimated_cost=0.2,
                latency_ms=10,
            )
        ]
    )
    service = ContractDrivenPerceptionService(observed_entities=observed, observer_registry=registry)

    result = service.compile(
        graph=graph,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["unobserved_metric"]},
    )

    requirement = result.observation_plan.requirements[0]
    assert requirement.attribute_name == "unobserved_metric"
    assert requirement.observer_capability_ids == ["generic_metric_reader"]
    assert requirement.capability_match_ids
    assert requirement.gap_reason == "ATTRIBUTE_VALUE_NOT_OBSERVED"
    decision = result.observation_plan.capability_decisions[0]
    assert decision.status == "selected"
    assert decision.decision_status == "SELECTED"
    assert decision.selected_capability_id == "generic_metric_reader"
    positive_match = next(item for item in result.observation_plan.capability_matches if item.capability_id == "generic_metric_reader")
    assert positive_match.match_status == "MATCHED"
    assert positive_match.missing_preconditions == []
    assert result.observation_plan.observation_tasks[0].status == "READY_FOR_OBSERVER"
    assert result.semantic_coverage_report.capability_coverage == 1.0
    assert result.semantic_coverage.coverage_by_domain["capability_arbitration"]["selected"] == 1


def test_capability_arbitration_reports_ties_without_executing_observer(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    registry = CapabilityRegistry(
        capabilities=[
            ObservationCapability(
                capability_id="generic_probe_a",
                name="Generic probe A",
                observable_attributes=["generic_signal"],
                compatible_entity_kinds=["file"],
                supported_strategies=["execute_observer"],
                typical_confidence=0.8,
            ),
            ObservationCapability(
                capability_id="generic_probe_b",
                name="Generic probe B",
                observable_attributes=["generic_signal"],
                compatible_entity_kinds=["file"],
                supported_strategies=["execute_observer"],
                typical_confidence=0.8,
            ),
        ]
    )
    service = ContractDrivenPerceptionService(observed_entities=observed, observer_registry=registry)

    result = service.compile(
        graph=graph,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["generic_signal"]},
    )

    decision = result.observation_plan.capability_decisions[0]
    assert decision.status == "multiple_capabilities_available"
    assert decision.decision_status == "BLOCKED_AMBIGUOUS"
    assert decision.reason_code == "MULTIPLE_CAPABILITIES_AVAILABLE"
    assert result.observation_plan.requirements[0].gap_reason == "MULTIPLE_CAPABILITIES_AVAILABLE"


def test_contract_aware_renderer_publishes_perception_summary(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    runtime = ReadonlyAnalysisArtifactRuntimeService(
        observed_entities=observed,
        perception=ContractDrivenPerceptionService(observed_entities=observed),
    )
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")

    render = runtime._contract_tabular_collection_content(
        expected_schema=["nome", "extensao", "codec"],
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "extensao", "codec"],
        },
    )

    assert render.content.splitlines()[0] == "nome,extensão,codec"
    assert "alpha.dat,dat," in render.content
    assert render.schema_coverage["status"] == "partial"
    assert render.schema_coverage["semantic_coverage"]["unsupported_fields"] == ["codec"]
    assert render.schema_coverage["semantic_coverage_report"]["missing_capabilities"] == ["codec"]
    assert render.entity_summary["perception"]["candidate_entity_set"]["selected_entity_ids"]
    assert render.entity_summary["perception"]["observation_plan"]["observation_goals"]
    assert render.entity_summary["perception"]["evidence_set"]["records"]
    assert render.entity_summary["perception"]["semantic_coverage_report"]["is_semantically_complete"] is False
    assert any(item["reason_code"] == "CAPABILITY_REJECTED" for item in render.semantic_gaps)


def test_readonly_runtime_compile_only_invariants_override_hostile_contract_policy(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    perception = _RecordingPerceptionService(observed_entities=observed)
    runtime = ReadonlyAnalysisArtifactRuntimeService(observed_entities=observed, perception=perception)
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")

    runtime._contract_tabular_collection_content(
        expected_schema=["nome"],
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome"],
            "perception_compile_policy": {
                "mode": "execute",
                "execute_observers": True,
                "execute_relationship_detection": True,
                "max_observer_executions": 99,
                "max_materialized_payload_bytes": 123,
            },
        },
    )

    assert perception.seen_compile_policy is not None
    assert perception.seen_compile_policy["mode"] == "compile_only"
    assert perception.seen_compile_policy["execute_observers"] is False
    assert perception.seen_compile_policy["execute_relationship_detection"] is False
    assert perception.seen_compile_policy["max_observer_executions"] == 0
    assert perception.seen_compile_policy["max_materialized_payload_bytes"] == 123


def test_workspace_root_roles_are_preserved_and_corpus_selection_excludes_project_files(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    (project / "src").mkdir(parents=True)
    (project / "build").mkdir()
    (project / ".gradle").mkdir()
    library.mkdir()
    (project / "src" / "Main.kt").write_text("fun main() {}", encoding="utf-8")
    (project / "build" / "Generated.class").write_bytes(b"class")
    (project / ".gradle" / "cache.lock").write_text("lock", encoding="utf-8")
    (library / "Alpha.any").write_text("content", encoding="utf-8")

    observed = _observed_entity_service()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "tamanho", "extens?o"],
            "workspace_context": {"project_root": str(project), "library_roots": [str(library)]},
        },
    )

    assert graph["roots_scanned_by_role"]["project_root"] == [str(project.resolve())]
    assert graph["roots_scanned_by_role"]["library_root"] == [str(library.resolve())]
    selected = set(result.candidate_entity_set.selected_entity_ids)
    selected_entities = [item for item in graph["entities"] if item["entity_id"] in selected]
    assert selected_entities
    assert {item["source_root_role"] for item in selected_entities} == {"library_root"}
    assert all(item["entity_role"] == "corpus_file" for item in selected_entities)
    rejected = [item for item in result.candidate_entity_set.candidates if item.status == "rejected"]
    assert rejected
    assert any("ROOT_ROLE_NOT_ALLOWED" in item.policy_rejection_reasons for item in rejected)
    assert any("ENTITY_ROLE_MISMATCH" in item.policy_rejection_reasons for item in rejected)
    descriptor = next(item for item in result.contract_observation_plan.attribute_contracts if item.raw_label == "extens?o")
    assert descriptor.canonical_key == "extension"
    assert descriptor.display_label == "extensão"


def test_library_root_media_metadata_attempt_uses_media_asset_hypothesis_not_audio_truth(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    (library / "related_asset.bin").write_text("not parsed media", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "codec"],
            "workspace_context": {"project_root": str(project), "library_roots": [str(library)]},
        },
    )

    selected_id = result.candidate_entity_set.selected_entity_ids[0]
    selected_entity = next(item for item in graph["entities"] if item["entity_id"] == selected_id)
    assert selected_entity["entity_role"] == "corpus_file"
    assert any(item.capability_id == "media_metadata_reader" for item in result.observation_plan.observation_tasks)
    execution_ref = service._execution_entity_ref(entity=selected_entity, capability_id="media_metadata_reader")
    assert execution_ref["entity_role"] == "media_asset_candidate"
    assert execution_ref["original_entity_role"] == "corpus_file"
    assert execution_ref["observation_hypothesis"] == "media_asset_candidate_for_contract_required_metadata"


def test_attribute_identity_normalization_trace_is_auditable_for_degraded_labels(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["extens?o", "dura??o"],
        },
    )

    descriptors = {item.raw_label: item for item in result.contract_observation_plan.attribute_contracts}
    trace = descriptors["extens?o"].normalization_trace
    assert trace is not None
    assert trace.raw_label == "extens?o"
    assert trace.canonical_key == "extension"
    assert trace.mojibake_detected is True
    assert trace.accepted is True
    assert trace.reason_code in {"MOJIBAKE_REPAIR_MATCH", "LOSS_TOLERANT_ALIAS_MATCH"}


def test_renderer_uses_only_contract_eligible_entities_for_corpus_inventory(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    (project / "build.gradle.kts").write_text("plugins {}", encoding="utf-8")
    (library / "Alpha.track").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    runtime = ReadonlyAnalysisArtifactRuntimeService(
        observed_entities=observed,
        perception=ContractDrivenPerceptionService(observed_entities=observed),
    )

    render = runtime._contract_tabular_collection_content(
        expected_schema=["nome", "extens?o", "codec"],
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "extens?o", "codec"],
            "workspace_context": {"project_root": str(project), "library_roots": [str(library)]},
        },
    )

    assert render.content.splitlines()[0] == "nome,extensão,codec"
    assert "Alpha.track,track," in render.content
    assert "build.gradle.kts" not in render.content
    candidates = render.entity_summary["perception"]["candidate_entity_set"]["candidates"]
    assert any(item["status"] == "rejected" for item in candidates)
    assert render.schema_coverage["semantic_coverage_report"]["missing_attributes"] == ["codec"]
    assert render.schema_coverage["semantic_coverage_report"]["missing_capabilities"] == []
    assert render.entity_summary["perception"]["media_metadata_capability"]["status"] == "blocked"
    assert render.entity_summary["perception"]["media_metadata_capability"]["execution_status"] == "blocked"
    assert render.entity_summary["perception"]["media_metadata_capability"]["files_attempted"] == 1
    assert "files_planned" not in render.entity_summary["perception"]["media_metadata_capability"]
    assert render.entity_summary["perception"]["compile_policy"]["mode"] == "compile_only"
    assert render.entity_summary["perception"]["payload_metrics"]["bound_status"] == "within_bounds"


def test_media_metadata_summary_uses_registry_configuration_not_absent_results() -> None:
    service = ContractDrivenPerceptionService(observer_registry=CapabilityRegistry(capabilities=[]))

    summary = service._media_metadata_capability_summary([])

    assert summary["status"] == "not_configured"
    assert summary["configured"] is False
    assert summary["available"] is False
    assert summary["execution_status"] == "not_started"
    assert summary["files_attempted"] == 0
    assert "files_planned" not in summary


def test_tabular_collection_with_corpus_roots_blocks_when_selection_policy_is_not_bound(tmp_path: Path) -> None:
    project = tmp_path / "app"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()
    (project / "build.gradle.kts").write_text("plugins {}", encoding="utf-8")
    (library / "Alpha.track").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(library)]},
    ).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "extensão", "codec"],
        },
    )

    assert graph["roots_scanned_by_role"]["library_root"]
    assert result.contract_observation_plan.entity_selection_contract["selection_mode"] == "generic_collection"
    assert result.candidate_entity_set.selected_entity_ids == []
    assert any(
        item.get("reason_code") == "ENTITY_SELECTION_POLICY_NOT_APPLIED"
        for item in result.candidate_entity_set.semantic_gaps
    )


def test_renderer_blocks_when_contract_corpus_root_has_no_eligible_entities(tmp_path: Path) -> None:
    project = tmp_path / "app"
    project.mkdir()
    (project / "settings.gradle.kts").write_text("pluginManagement {}", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(
        workspace=str(project),
        workspace_context={"project_root": str(project), "library_roots": [str(tmp_path / "missing_library")]},
    ).model_dump(mode="json")
    runtime = ReadonlyAnalysisArtifactRuntimeService(
        observed_entities=observed,
        perception=ContractDrivenPerceptionService(observed_entities=observed),
    )

    render = runtime._contract_tabular_collection_content(
        expected_schema=["nome", "tamanho"],
        analysis_payload={"observed_entity_graph": graph},
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "tamanho"],
            "workspace_context": {"project_root": str(project), "library_roots": [str(tmp_path / "missing_library")]},
        },
    )

    assert "settings.gradle.kts" not in render.content
    assert any(item["gap_type"] == "ENTITY_SELECTION_EMPTY_FOR_CONTRACT" for item in render.semantic_gaps)
    assert any(item.get("reason_code") in {"WORKSPACE_ROLE_MISMATCH", "ENTITY_INELIGIBLE_FOR_CONTRACT"} for item in render.semantic_gaps)


def test_capability_descriptor_v2_fields_drive_matching_without_domain_rules(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    registry = CapabilityRegistry(
        capabilities=[
            {
                "capability_id": "generic_declared_attribute_probe",
                "name": "Generic declared attribute probe",
                "version": "2",
                "domain": "generic",
                "produces": ["generic_signal"],
                "consumes": ["entity_ref"],
                "supported_entity_types": ["file"],
                "evidence_types": ["structured_attribute_evidence"],
                "preconditions": ["observer_binding_available"],
                "supported_strategies": ["execute_observer"],
                "confidence_profile": {"typical": 0.8},
                "cost_profile": {"estimated": 0.1},
                "latency_profile": {"estimated_ms": 20},
                "determinism": "deterministic",
                "risk_level": "low",
                "requires_approval": False,
                "observer_binding": {"binding_type": "future_observer"},
                "status": "available",
                "typical_confidence": 0.8,
            }
        ]
    )
    service = ContractDrivenPerceptionService(observed_entities=observed, observer_registry=registry)

    result = service.compile(
        graph=graph,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["generic_signal"]},
    )

    match = next(item for item in result.observation_plan.capability_matches if item.capability_id == "generic_declared_attribute_probe")
    assert match.capability_id == "generic_declared_attribute_probe"
    assert match.attributes_covered == ["generic_signal"]
    assert match.missing_preconditions
    assert match.match_status == "PRECONDITION_FAILED"
    assert all(
        not (item.match_status == "MATCHED" and item.missing_preconditions)
        for item in result.observation_plan.capability_matches
    )
    assert result.observation_plan.capability_decisions[0].decision_status == "BLOCKED_PRECONDITION"


def test_semantic_knowledge_layer_only_promotes_evidence_backed_attributes(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={"expected_kind": "tabular_collection", "expected_schema": ["nome", "codec"]},
    )

    assert result.evidence_set.records
    knowledge_keys = {item.canonical_key for item in result.knowledge_records}
    assert "name" in knowledge_keys
    assert "codec" not in knowledge_keys

    assertions = {item.canonical_key: item for item in result.semantic_assertions}
    assert assertions["name"].state in {"OBSERVED", "VERIFIED"}
    assert assertions["name"].truth_eligible is True
    assert assertions["name"].evidence_ids
    assert assertions["codec"].state == "INSUFFICIENT_EVIDENCE"
    assert assertions["codec"].truth_eligible is False
    assert assertions["codec"].blocking_reasons == ["CAPABILITY_REJECTED"]

    assert result.semantic_self_review.can_speaker_claim is False
    assert result.semantic_self_review.truth_readiness == "blocked"
    assert any(item.code == "EVIDENCE_PRESENT" and item.canonical_key == "codec" and item.status == "fail" for item in result.semantic_self_review.questions)
    assert result.semantic_coverage_2.knowledge_coverage == 0.5
    assert result.semantic_coverage_2.truth_coverage == 0.5
    assert result.semantic_coverage_2.is_truth_ready is False
    assert "CAPABILITY_REJECTED" in result.semantic_coverage_2.blocking_reasons


def test_optional_missing_attribute_is_reviewed_without_truth_promotion(tmp_path: Path) -> None:
    (tmp_path / "alpha.dat").write_text("content", encoding="utf-8")
    observed = _observed_entity_service()
    graph = observed.compile(workspace=str(tmp_path)).model_dump(mode="json")
    service = ContractDrivenPerceptionService(observed_entities=observed)

    result = service.compile(
        graph=graph,
        declared_contract={
            "expected_kind": "tabular_collection",
            "expected_schema": ["nome", "diagnostic_note"],
            "attribute_contracts": [
                {"canonical_key": "name", "display_label": "nome", "raw_label": "nome"},
                {
                    "canonical_key": "diagnostic_note",
                    "display_label": "diagnostic_note",
                    "raw_label": "diagnostic_note",
                    "requiredness": "optional",
                    "evidence_required": False,
                },
            ],
        },
    )

    assertions = {item.canonical_key: item for item in result.semantic_assertions}
    assert assertions["diagnostic_note"].state == "UNKNOWN"
    assert assertions["diagnostic_note"].truth_eligible is False
    assert "diagnostic_note" not in result.semantic_coverage_report.missing_attributes
    assert all(
        item.status != "fail"
        for item in result.semantic_self_review.questions
        if item.canonical_key == "diagnostic_note"
    )
