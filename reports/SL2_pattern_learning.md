# SL2 Semantic Pattern Learning

Status: SL2_SEMANTIC_PATTERN_LEARNING_READY

Implemented:

- `SemanticPatternEngine`
- `SemanticPatternRepository`
- `SemanticPatternScorer`
- `SemanticPatternNormalizer`
- `SemanticPatternValidator`
- `SemanticPatternMatch`
- `SemanticPatternRecognitionRequest`
- `SemanticPatternRecognitionResult`

Endpoints:

- `GET /api/v1/runtime/semantic-learning/patterns`
- `POST /api/v1/runtime/semantic-learning/patterns`

Guarantees:

- deterministic recognition;
- concept reuse from Semantic Knowledge Base;
- no prompt-literal learning;
- no runtime mutation;
- no Semantic Interpreter changes.

Verification:

- `python -m pytest tests\unit\test_semantic_learning_sl2.py -q` -> 5 passed
- `python -m compileall src\aipinho\schemas\semantic_learning.py src\aipinho\services\semantic_learning_service.py src\aipinho\api\routers\semantic_learning_router.py` -> passed
- `python -m pytest tests\unit\test_semantic_capability_registry.py tests\unit\test_semantic_interpreter_pipeline.py tests\unit\test_isr_schema.py tests\unit\test_semantic_normalizer.py tests\unit\test_contract_compiler.py tests\unit\test_semantic_learning_sl1.py tests\unit\test_semantic_learning_sl2.py -q` -> 36 passed
- Router registration check -> 133 routers, semantic-learning registered

Implementation note:

- Seeded semantic pattern IDs are deterministic (`semantic_pattern_<canonical_intent>`) to avoid unstable pattern recognition across service instances.
