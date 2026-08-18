# H1C0.R2.13 — Perception Fact Projection Semantics, Provenance & Bounded Derivation

- Verdict: FIRETEST5_H1C0_R2_13_PERCEPTION_FACT_PROJECTION_READY
- FireTest 5: NOT_READY
- Root cause status: probable_with_evidence
- Public frontier localized: PERCEPTION_FACT_SOURCE_BINDING_STALLED
- Final task_run_id: task_run_a85129892a9d4ac29d3bfe0225de9883
- Operation: op_2a57a1734f5949a9ae9ef8926366e048

## Objective
R2.13 opened the generic fact projection boundary inside ContractDrivenPerceptionService without making music, paths, extensions, artifact names or FireTest fixtures production authorities. The wave separates observed, derived and candidate fact semantics and preserves provenance/evidence lineage.

## Before State
R2.12 left the public run blocked at PERCEPTION_FACT_PROJECTION_STALLED. The last observed checkpoint was before_fact_projection; after_fact_projection, payload assembly, metadata coverage, inventory sufficiency and evidence_phase1 were not reached.

## Changed Files
- src/aipinho/schemas/artifacts/contract_perception.py
- src/aipinho/services/artifacts/contract_driven_perception_service.py
- src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py
- src/aipinho/services/runtime/task_run_store.py
- src/aipinho/services/cvl/cognitive_validation_laboratory_service.py
- reports/runtime_consolidation/h1c0_r2_13_collect_public_rerun.py
- tests/unit/test_artifact_late_rejection_preserves_terminal_reason.py
- tests/unit/test_perception_fact_projection_stage_trace.py
- tests/unit/test_perception_fact_projection_provenance.py
- tests/unit/test_perception_fact_projection_observed_vs_derived.py
- tests/unit/test_perception_fact_projection_bounded_derivation.py
- tests/unit/test_perception_fact_projection_no_filesystem_observation.py
- tests/unit/test_perception_fact_projection_reason_mapping.py
- tests/unit/test_cvl_perception_fact_projection_frontier.py

## Real Call Graph
ContractDrivenPerceptionService.compile now exposes the fact projection path as:

1. attribute_observations
2. evidence_set
3. semantic_coverage
4. semantic_coverage_report
5. knowledge_records
6. semantic_assertions
7. semantic_self_review
8. semantic_coverage_2

## Fact Semantics
KnowledgeRecord and SemanticAssertion now carry explicit fact_kind, source_kind, provenance_refs, derivation_rule, validation_eligibility and truth-boundary fields. Observed facts keep evidence/provenance refs. Derived facts keep derivation provenance. Candidate facts remain non-truth-eligible unless evidence and confidence gates allow validation. Missing observation remains unknown/insufficient, not false.

## Bounded Derivation
Fact projection now emits bounded checkpoints for source binding, candidate projection, derivation, provenance binding, deduplication and validation projection. Generic configurable fact budgets can block with PERCEPTION_FACT_PROJECTION_BOUND_EXCEEDED or PERCEPTION_FACT_PROJECTION_COMPLEXITY_BUDGET_EXCEEDED without truncating silently.

## Public Rerun
- client_response_status: accepted_running
- result.status: blocked
- result reason observed: PERCEPTION_FACT_SOURCE_BINDING_STALLED
- finished_at: 2026-08-17T16:55:41.465956+00:00
- terminal_event_count: 1
- music_inventory_reached: True
- before_fact_projection_reached: True
- after_fact_projection_reached: False
- before_payload_assembly_reached: False
- last_completed_fact_stage: before_fact_source_binding
- metadata_coverage_reached: False
- inventory_sufficiency_reached: False
- evidence_phase1_reached: False
- queue_runtime: 200 in 164 ms

## Endpoint Health
All collected endpoints returned 200: summary, events, result, truth, artifacts, session, queue_hygiene and queue_runtime. No backend restart was required after terminal result.

## Phase 2–6
All phases 2 through 6 were skipped_due_to_prior_block with api_called=false and skip_reason=PERCEPTION_FACT_SOURCE_BINDING_STALLED.

## Tests
- Focused R2.13 tests: 13 passed.
- Regression set: 115 passed.
- py_compile: PASS.
- Anti-hardcode: PASS; only pre-existing CVL structural FireTest type names matched.
- Generic fixture validation: passed, 5 cases, production_logic_depends_on_firetest_fixture=false.

## Storage
- run.json bytes: 220188
- result.json bytes: 153657
- events.json bytes: 99207

## Divergence Note
The existing TaskRunResult projection still has top-level reason_code=null. The canonical observed reason is present in validation.reason_code and completion metadata, and the terminal event carries the same reason. The collector records this as result_reason_code=PERCEPTION_FACT_SOURCE_BINDING_STALLED.

## Why No False Success
The run remains blocked. SpeakerTruth.safe_to_report_success=false. Metadata coverage, inventory sufficiency and evidence_phase1 were not reached. No Phase 2 API call was made.

## Why No Fixture Hardcode
Production changes are generic schema/service/runtime/CVL changes. FireTest strings and local paths only appear in reports/tests/collector prompts, not in production decision logic.

## Next Frontier
The next frontier is fact source binding at scale: selected entities plus observation plan become AttributeObservation and EvidenceSet. The first non-completed stage is after_fact_source_binding.
