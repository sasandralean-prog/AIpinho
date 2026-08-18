# H1C0.R2.14 Deep Diagnostic

Baseline R2.13 reached `before_fact_source_binding` and terminalized with `PERCEPTION_FACT_SOURCE_BINDING_STALLED`. The root cause is proven at the diagnostic level: source binding was still a monolithic region inside `ContractDrivenPerceptionService.compile()`, covering `attribute_observations`, `evidence_set`, `semantic_coverage`, and `semantic_coverage_report` without internal public checkpoints.

The patch plan is generic: index source-binding inputs, split AttributeObservation projection from EvidenceSet materialization, emit bounded checkpoints, add generic source-binding budget reasons, and make `TaskRunResult.reason_code` canonical across result/session/summary projections.

No production decision in this plan depends on FireTest, the corpus name, artifact path, extension, task id, operation id, or row count.
