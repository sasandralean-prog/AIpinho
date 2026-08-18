# SR1 Capability Registry Report

## Summary

Implemented the first Semantic Runtime layer for governed capability-based model
selection.

## Added

- `CapabilityContract`
- `CapabilityModelBinding`
- `CapabilitySelection`
- `SemanticCapabilityRegistry`
- `CapabilityResolver`
- `ModelPolicyResolver`
- semantic capability registry config
- documentation for the capability registry

## Changed

- `RoleModelGateServiceV2` now selects models through `CapabilityResolver`
  instead of reading `primary_model` directly from the role binding.
- Capability alias matching was moved out of the role gate and into the
  semantic capability resolver.
- Role model gate decisions now expose `capability_id` and `selection_source`.
- `RolePipelineService` now resolves real runtime model selection through
  `CapabilityResolver` when a pipeline explicitly requests real inference.

## Compatibility

Existing role model bindings are merged into semantic capability bindings. The
default coder model remains `qwen2_5_coder_7b_q4_k_m`.

The default role pipeline request remains stub/deterministic compatible unless
the caller explicitly requests real inference.

## Tests

Passed:

- `python -m pytest tests\unit\test_semantic_capability_registry.py tests\unit\test_role_model_gate_service_v2.py -q`
- `python -m pytest tests\unit\test_semantic_capability_registry.py tests\unit\test_role_model_gate_service_v2.py tests\unit\test_role_model_binding_service_v2.py tests\unit\test_role_model_fallback_service_v2.py tests\unit\test_role_pipeline_service.py -q`
- `python -m pytest tests\unit\test_semantic_capability_registry.py tests\unit\test_role_model_gate_service_v2.py tests\unit\test_role_pipeline_service.py -q`
- `python -m pytest tests\e2e\test_role_model_binding_controlled_real_inference_flow.py tests\e2e\test_role_pipeline_model_gate_flow.py -q`

Observed external config drift:

- `python -m pytest tests\unit\test_model_registry_service.py tests\unit\test_role_model_gate_service.py tests\unit\test_role_model_gate_service_v2.py tests\unit\test_role_model_trace_service_v2.py tests\unit\test_role_model_run_store_v2.py tests\unit\test_semantic_capability_registry.py -q`
- One pre-existing expectation failed because `config/models/model_registry.yaml`
  currently has `runtime_defaults.chat_model_use_enabled=true` and
  `role_model_use_enabled=true`, while the older unit test expects both false.
  This file was not changed by SR1.

## Non-goals

Semantic Interpreter was not implemented in SR1.

## Veredito

SR1_CAPABILITY_REGISTRY_IMPLEMENTED
