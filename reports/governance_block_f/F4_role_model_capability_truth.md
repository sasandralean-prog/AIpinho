# F4 Role Model Capability Truth

Checkpoint: F4_ROLE_MODEL_CAPABILITY_TRUTH_READY_WITH_CAUTION
Generated: 2026-06-28T15:44:57.208267+00:00

Roles mapped: speaker, planner, router, coder, tool_executor, validator, summarizer, capability_truth, embedding, vision, ocr, artifact_writer.

Truth rule:
- real model use must be declared with model_used/provider;
- fallback must expose fallback_used and fallback_reason;
- stubs cannot claim real inference.

Caution:
F9 used deterministic governed patch content and did not require external model inference. This is reported as degraded/static firetest evidence, not as real role inference.
