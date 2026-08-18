# SR3 ISR Report

## Summary

Created the official canonical Intermediate Semantic Representation (ISR)
schema and migrated the Semantic Interpreter output to that ISR.

## Added

- `IntermediateSemanticRepresentation`
- `ISREntity`
- `ISRMetadata`
- `ISRValidator`
- `ISRSerializer`
- `ISRVersioning`

## Updated

- `SemanticInterpreterOutput` is now an alias of the canonical ISR.
- `SemanticInterpreterPipeline` now returns versioned ISR fields:
  - `version`
  - `permissions_requested`
  - `expected_outputs`
  - `ambiguity`
  - `semantic_trace`
  - `metadata`

## Compatibility

SR2 property names remain available as compatibility properties:

- `requested_outputs`
- `ambiguity_score`
- `trace`
- `capability_id`
- `model_selection`
- no-side-effect flags

## Non-goals

SR3 does not create operation contracts, tasks, approvals, tool calls, skills,
patches, or Runtime executions.

## Tests

Passed:

- `python -m pytest tests\unit\test_isr_schema.py tests\unit\test_semantic_interpreter_pipeline.py tests\unit\test_semantic_capability_registry.py -q`
- `python -m pytest tests\unit\test_role_model_gate_service_v2.py tests\unit\test_role_pipeline_service.py tests\e2e\test_role_model_binding_controlled_real_inference_flow.py tests\e2e\test_role_pipeline_model_gate_flow.py -q`
- `python -m compileall -q src\aipinho\schemas\semantic_runtime src\aipinho\services\semantic_runtime`

Results:

- ISR/Semantic Runtime focused tests: 15 passed.
- Runtime compatibility tests: 10 passed.

## Veredito

SR3_ISR_READY
