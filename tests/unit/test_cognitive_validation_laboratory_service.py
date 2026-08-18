from pathlib import Path

from aipinho.schemas.cvl import FireTestProfile, SimulationRequest
from aipinho.services.cvl import (
    CVLReportWriter,
    CognitiveDependencyGraphService,
    CognitiveCoverageService,
    CognitiveGapPredictor,
    CognitiveSimulationEngine,
    CognitiveValidationLaboratoryService,
    FireTestLaboratoryService,
)


def _profile() -> FireTestProfile:
    return FireTestProfile(
        profile_id="profile_generic_capability",
        name="Generic capability validation",
        objective="Validate whether declared knowledge can satisfy a contract before execution.",
        domain="generic",
        expected_pipeline=[
            "intent",
            "contract",
            "perception",
            "capability_matching",
            "validation",
            "speaker_truth",
        ],
        involved_contracts=["semantic_artifact_contract"],
        involved_modules=["artifact_runtime", "contract_perception"],
        expected_capabilities=["structured_attribute_observation"],
        expected_artifacts=["reports/example.md"],
        success_contract={"validation": "pass", "speaker_truth": "safe"},
    )


def test_firetest_laboratory_registers_profiles_without_code_changes() -> None:
    profile = _profile()

    suite = FireTestLaboratoryService().suite([profile], name="generic_suite")

    assert suite.name == "generic_suite"
    assert suite.profiles[0].profile_id == "profile_generic_capability"
    assert FireTestLaboratoryService().get_profile(suite, "profile_generic_capability") == profile


def test_gap_predictor_predicts_missing_capability_without_runtime_execution() -> None:
    profile = _profile()
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=[])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "capability_matching"
    assert report.probable_capability == "structured_attribute_observation"
    assert report.reason_codes == ["PREDICTED_CAPABILITY_MISSING"]
    assert report.dependency_chain


def test_gap_predictor_recognizes_media_corpus_project_analysis_handoff_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_project_analysis_media_corpus_handoff",
        name="ProjectAnalysis media corpus handoff frontier",
        objective="Predict source-reading versus corpus-inventory handoff before runtime execution.",
        domain="generic",
        expected_pipeline=["project_analysis", "corpus_handoff", "artifact_runtime"],
        involved_contracts=["media_corpus_inventory_artifact"],
        expected_capabilities=[],
        metadata={
            "project_analysis_cognition": {
                "reason_code": "MEDIA_CORPUS_ROOT_HANDOFF_READY",
                "component": "ProjectAnalysisService",
                "confidence": 0.86,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=[])

    assert report.predicted_status == "partial"
    assert report.probable_component == "ProjectAnalysisService"
    assert report.reason_codes == ["MEDIA_CORPUS_ROOT_HANDOFF_READY"]


def test_gap_predictor_prioritizes_semantic_ingress_before_capability_matching() -> None:
    profile = FireTestProfile(
        profile_id="profile_semantic_ingress",
        name="Semantic ingress validation",
        objective="Validate early text-to-contract observability before downstream capability matching.",
        domain="generic",
        expected_pipeline=[
            "text_ingress",
            "encoding",
            "semantic_normalization",
            "state_effects",
            "intent_resolution",
            "operation_contract_selection",
            "capability_matching",
        ],
        involved_contracts=["operation_contract"],
        expected_capabilities=["structured_attribute_observation"],
        metadata={"semantic_ingress": {"encoding_status": "degraded", "confidence": 0.88}},
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=[])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "encoding"
    assert report.reason_codes == ["PREDICTED_ENCODING_DEGRADATION"]
    assert report.confidence == 0.88


def test_gap_predictor_prioritizes_workspace_role_boundary_before_capability_matching() -> None:
    profile = FireTestProfile(
        profile_id="profile_workspace_role_boundary",
        name="Workspace role boundary validation",
        objective="Validate root-role-aware entity selection before downstream capability matching.",
        domain="generic",
        expected_pipeline=[
            "text_ingress",
            "operation_contract_selection",
            "observed_entity_compilation",
            "entity_selection_policy",
            "capability_matching",
        ],
        involved_contracts=["artifact_entity_selection_contract"],
        expected_capabilities=["structured_attribute_observation"],
        metadata={
            "semantic_ingress": {
                "encoding_status": "ok",
                "semantic_normalization_status": "ok",
                "state_effect_status": "resolved",
                "intent_status": "resolved",
                "operation_contract_status": "selected",
            },
            "workspace_role_boundary": {
                "root_role_status": "not_applied",
                "confidence": 0.91,
            },
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=[])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "entity_selection_policy"
    assert report.reason_codes == ["PREDICTED_WORKSPACE_ROLE_BOUNDARY"]
    assert report.confidence == 0.91


def test_gap_predictor_recognizes_relationship_cognition_frontier_without_runtime_execution() -> None:
    profile = FireTestProfile(
        profile_id="profile_relationship_cognition",
        name="Relationship cognition validation",
        objective="Validate relationship candidate readiness before execution.",
        domain="generic",
        expected_pipeline=[
            "contract",
            "relationship_evidence",
            "relationship_validation",
            "speaker_truth",
        ],
        involved_contracts=["relationship_candidate_contract"],
        expected_capabilities=["media_relationship_candidate_detector"],
        metadata={
            "relationship_cognition": {
                "capability_id": "media_relationship_candidate_detector",
                "capability_status": "registered",
                "evidence_status": "insufficient",
                "confidence": 0.79,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_relationship_candidate_detector"],
    )
    coverage = CognitiveCoverageService().report(
        profile,
        available_capabilities=["media_relationship_candidate_detector"],
    )

    assert report.predicted_status == "blocked"
    assert report.probable_component == "relationship_evidence"
    assert report.probable_capability == "media_relationship_candidate_detector"
    assert report.reason_codes == ["RELATIONSHIP_EVIDENCE_INSUFFICIENT"]
    assert any(metric.domain == "relationship_evidence" and metric.coverage == 0.0 for metric in coverage.metrics)


def test_gap_predictor_recognizes_project_analysis_read_cooperation_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_project_analysis_read_budget",
        name="ProjectAnalysis read cooperation validation",
        objective="Validate project analysis file read budget cooperation before execution.",
        domain="generic",
        expected_pipeline=[
            "intent",
            "project_analysis",
            "project_analysis_file_read",
            "artifact_runtime",
        ],
        involved_contracts=["analysis_readonly"],
        expected_capabilities=["read_workspace"],
        metadata={
            "project_analysis_cognition": {
                "component": "ProjectAnalysisService",
                "reason_code": "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED",
                "file_read_status": "single_file_budget_exceeded",
                "partial_context_status": "unknown",
                "cooperation_status": "unknown",
                "confidence": 0.83,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["read_workspace"])
    coverage = CognitiveCoverageService().report(profile, available_capabilities=["read_workspace"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "ProjectAnalysisService"
    assert report.reason_codes == ["PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED"]
    assert report.confidence == 0.83
    assert any(metric.domain == "project_analysis_file_read" and metric.coverage == 0.0 for metric in coverage.metrics)


def test_gap_predictor_recognizes_public_response_boundary_from_profile_metadata() -> None:
    profile = FireTestProfile(
        profile_id="profile_public_response_boundary",
        name="Public response boundary validation",
        objective="Validate governed public response behavior before long runtime execution.",
        domain="generic",
        expected_pipeline=[
            "intent",
            "public_response_boundary",
            "accepted_running",
            "timeout_blocked",
            "public_endpoint_summary",
        ],
        involved_contracts=["analysis_readonly", "public_runtime_response"],
        expected_capabilities=["read_workspace"],
        metadata={
            "public_response_boundary": {
                "response_mode": "synchronous",
                "accepted_running_status": "missing",
                "timeout_blocked_status": "missing",
                "confidence": 0.82,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["read_workspace"])
    coverage = CognitiveCoverageService().report(profile, available_capabilities=["read_workspace"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "PublicRuntimeResponsePolicy"
    assert report.reason_codes == ["PUBLIC_CHAT_RESPONSE_BOUNDARY"]
    assert report.confidence == 0.82
    assert any(metric.domain == "public_response_boundary" and metric.coverage == 0.0 for metric in coverage.metrics)


def test_gap_predictor_recognizes_public_preacceptance_frontier_from_profile_metadata() -> None:
    profile = FireTestProfile(
        profile_id="profile_public_preacceptance_boundary",
        name="Public pre-acceptance boundary validation",
        objective="Validate that heavy work does not run before TaskRun bootstrap.",
        domain="generic",
        expected_pipeline=[
            "intent",
            "public_preacceptance",
            "taskrun_bootstrap",
            "phase_progression",
        ],
        involved_contracts=["analysis_readonly", "public_runtime_response"],
        expected_capabilities=["read_workspace"],
        metadata={
            "public_response_boundary": {
                "preacceptance_status": "heavy_work_detected",
                "taskrun_bootstrap_status": "not_reached",
                "phase_progression_status": "stop_condition_required",
                "confidence": 0.81,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["read_workspace"])
    coverage = CognitiveCoverageService().report(profile, available_capabilities=["read_workspace"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "PublicPreAcceptancePolicy"
    assert report.reason_codes == ["PUBLIC_RUNTIME_PREACCEPTANCE_HEAVY_WORK_DETECTED"]
    assert report.confidence == 0.81
    assert any(metric.domain == "public_preacceptance" and metric.coverage == 0.0 for metric in coverage.metrics)


def test_gap_predictor_recognizes_terminal_result_missing_frontier() -> None:
    profile = FireTestProfile(
        profile_id="profile_terminal_result_missing",
        name="Terminal result finalization boundary",
        objective="Predict terminal result persistence gaps after partial artifact binding.",
        domain="generic",
        expected_pipeline=[
            "artifact_runtime",
            "result_finalization",
            "public_response",
        ],
        involved_contracts=["analysis_readonly", "public_runtime_response"],
        expected_capabilities=["read_workspace"],
        metadata={
            "public_response_boundary": {
                "terminal_result_status": "missing",
                "partial_artifact_result_finalization": "missing",
                "confidence": 0.83,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(profile, graph=graph, available_capabilities=["read_workspace"])

    assert report.predicted_status == "blocked"
    assert report.probable_component == "PublicRunFinalizationGuard"
    assert report.reason_codes == ["TERMINAL_RESULT_MISSING"]
    assert report.confidence == 0.83


def test_gap_predictor_prioritizes_relationship_provenance_before_validation() -> None:
    profile = FireTestProfile(
        profile_id="profile_relationship_provenance",
        name="Relationship provenance validation",
        objective="Validate relationship provenance maturity before final validation.",
        domain="generic",
        expected_pipeline=["relationship_evidence", "relationship_provenance", "relationship_validation"],
        involved_contracts=["relationship_candidate_contract"],
        expected_capabilities=["media_relationship_candidate_detector"],
        metadata={
            "relationship_cognition": {
                "capability_id": "media_relationship_candidate_detector",
                "capability_status": "registered",
                "evidence_status": "sufficient",
                "provenance_status": "missing",
                "validation_status": "required",
                "confidence": 0.81,
            }
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_relationship_candidate_detector"],
    )

    assert report.probable_component == "relationship_provenance"
    assert report.reason_codes == ["RELATIONSHIP_PROVENANCE_MISSING"]
    assert report.confidence == 0.81


def test_gap_predictor_predicts_semantic_maturity_after_entity_selection() -> None:
    profile = FireTestProfile(
        profile_id="profile_semantic_maturity",
        name="Semantic maturity validation",
        objective="Validate evidence to knowledge to truth readiness before runtime execution.",
        domain="generic",
        expected_pipeline=[
            "text_ingress",
            "operation_contract_selection",
            "observed_entity_compilation",
            "entity_selection_policy",
            "evidence_availability",
            "knowledge_availability",
            "semantic_completion",
            "truth_readiness",
        ],
        involved_contracts=["semantic_artifact_contract"],
        expected_capabilities=["structured_attribute_observation"],
        metadata={
            "semantic_ingress": {
                "encoding_status": "ok",
                "semantic_normalization_status": "ok",
                "state_effect_status": "resolved",
                "intent_status": "resolved",
                "operation_contract_status": "selected",
            },
            "workspace_role_boundary": {
                "root_role_status": "ready",
                "entity_selection_policy_status": "ready",
                "corpus_observation_status": "ready",
            },
            "semantic_maturity": {
                "evidence_availability": "insufficient",
                "knowledge_availability": "unknown",
                "truth_readiness": "not_ready",
                "probable_capability": "structured_attribute_observation",
                "confidence": 0.87,
            },
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["structured_attribute_observation"],
    )

    assert report.predicted_status == "blocked"
    assert report.probable_component == "evidence_recording"
    assert report.probable_capability == "structured_attribute_observation"
    assert report.reason_codes == ["PREDICTED_EVIDENCE_AVAILABILITY_GAP"]
    assert report.confidence == 0.87


def test_gap_predictor_distinguishes_backend_not_configured_before_evidence_recording() -> None:
    profile = FireTestProfile(
        profile_id="profile_media_backend",
        name="Media metadata backend frontier",
        objective="Predict observer/backend frontier before generic evidence recording.",
        domain="generic",
        expected_pipeline=[
            "observed_entity_compilation",
            "entity_selection_policy",
            "backend_configuration",
            "observer_execution",
            "evidence_recording",
        ],
        involved_contracts=["semantic_artifact_contract"],
        expected_capabilities=["media_metadata_reader"],
        metadata={
            "workspace_role_boundary": {
                "root_role_status": "ready",
                "entity_selection_policy_status": "ready",
                "corpus_observation_status": "ready",
            },
            "media_metadata_capability": {
                "capability_id": "media_metadata_reader",
                "capability_status": "registered",
                "backend_status": "not_configured",
                "confidence": 0.88,
            },
            "semantic_maturity": {
                "evidence_availability": "insufficient",
                "probable_capability": "media_metadata_reader",
            },
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_metadata_reader"],
    )

    assert report.predicted_status == "blocked"
    assert report.probable_component == "backend_not_configured"
    assert report.probable_capability == "media_metadata_reader"
    assert report.reason_codes == ["BACKEND_NOT_CONFIGURED"]
    assert report.confidence == 0.88


def test_gap_predictor_distinguishes_partial_backend_from_evidence_coverage_gap() -> None:
    profile = FireTestProfile(
        profile_id="profile_media_backend_partial",
        name="Media metadata partial evidence frontier",
        objective="Predict evidence coverage after backend execution produces partial evidence.",
        domain="generic",
        expected_pipeline=[
            "observed_entity_compilation",
            "entity_selection_policy",
            "backend_configuration",
            "observer_execution",
            "evidence_recording",
            "evidence_coverage",
        ],
        involved_contracts=["semantic_artifact_contract"],
        expected_capabilities=["media_metadata_reader"],
        metadata={
            "workspace_role_boundary": {
                "root_role_status": "ready",
                "entity_selection_policy_status": "ready",
                "corpus_observation_status": "ready",
            },
            "media_metadata_capability": {
                "capability_id": "media_metadata_reader",
                "capability_status": "registered",
                "backend_status": "partial",
                "evidence_coverage_status": "partial",
                "confidence": 0.86,
            },
        },
    )
    graph = CognitiveDependencyGraphService().build(profile)

    report = CognitiveGapPredictor().predict(
        profile,
        graph=graph,
        available_capabilities=["media_metadata_reader"],
    )

    assert report.predicted_status == "blocked"
    assert report.probable_component == "evidence_coverage"
    assert report.probable_capability == "media_metadata_reader"
    assert report.reason_codes == ["EVIDENCE_COVERAGE_INSUFFICIENT"]
    assert report.confidence == 0.86


def test_cognitive_coverage_reports_semantic_maturity_dimensions() -> None:
    profile = FireTestProfile(
        profile_id="profile_semantic_coverage",
        name="Semantic coverage validation",
        objective="Validate semantic coverage dimensions without executing runtime.",
        expected_pipeline=["evidence_availability", "knowledge_availability", "truth_readiness"],
        involved_contracts=["semantic_artifact_contract"],
        expected_capabilities=[],
        expected_artifacts=["reports/example.md"],
        success_contract={"speaker_truth": "safe"},
        metadata={
            "semantic_maturity": {
                "evidence_availability": "available",
                "knowledge_availability": "insufficient",
                "semantic_completion": "partial",
                "truth_readiness": "not_ready",
                "validation_probability": "low",
            }
        },
    )

    report = CognitiveCoverageService().report(profile, available_capabilities=[])
    metrics = {item.domain: item for item in report.metrics}

    assert metrics["evidence_availability"].health == "ready"
    assert metrics["knowledge_availability"].health == "blocked"
    assert metrics["semantic_completion"].gaps == ["partial"]
    assert metrics["truth_readiness"].gaps == ["not_ready"]
    assert metrics["validation_probability"].gaps == ["low"]


def test_dependency_graph_explains_contract_and_capability_impact() -> None:
    profile = _profile()
    service = CognitiveDependencyGraphService()
    graph = service.build(profile)

    capability_node = "capability:structured_attribute_observation"
    impact = service.impact(graph, capability_node)

    assert capability_node in {node.node_id for node in graph.nodes}
    assert impact.direct_dependents
    assert "pipeline:capability_matching" in impact.impacted_node_ids


def test_simulation_engine_blocks_before_execution_when_capability_is_missing() -> None:
    profile = _profile()

    result = CognitiveSimulationEngine().simulate(SimulationRequest(profile=profile, available_capabilities=[]))

    assert result.status == "blocked"
    assert result.predicted_failures
    assert result.predicted_failures[0].reason_code == "PREDICTED_CAPABILITY_MISSING"
    assert any(step.status == "predicted_blocked" for step in result.steps)
    assert all("task_run" not in step.explanation.casefold() for step in result.steps)


def test_cvl_generates_reports_as_readonly_analysis_artifacts(tmp_path: Path) -> None:
    profile = _profile()
    writer = CVLReportWriter(root=tmp_path / "cvl")
    service = CognitiveValidationLaboratoryService(writer=writer)

    result = service.analyze([profile], available_capabilities=[], write_reports=True)

    assert result.status == "blocked"
    assert set(result.report_paths) == {
        "firetest_lab",
        "prediction_report",
        "dependency_graph",
        "coverage_report",
        "simulation_report",
        "laboratory_summary",
    }
    for path in result.report_paths.values():
        assert Path(path).exists()
        assert Path(path).read_text(encoding="utf-8").strip()


def test_cvl_predicts_ready_when_contract_capabilities_are_available(tmp_path: Path) -> None:
    profile = _profile()
    service = CognitiveValidationLaboratoryService(writer=CVLReportWriter(root=tmp_path / "cvl"))

    result = service.analyze(
        [profile],
        available_capabilities=["structured_attribute_observation"],
        write_reports=False,
    )

    assert result.status == "ready"
    assert result.prediction_reports[0].predicted_status == "ready"
    assert result.simulation_results[0].status == "ready"
    assert result.coverage_reports[0].overall_status in {"ready", "partial"}
