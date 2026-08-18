# Semantic Evolution History

The Semantic Curriculum exposes structured evolution history through:

- `SemanticCurriculum.evolutions`
- `SemanticCurriculumResult.evolution_history`

Initial history:

- curriculum initialized from Semantic Knowledge Base;
- promotion candidates are recorded as future-version candidates only;
- recommendation reviews are recorded as evidence, not runtime changes.

Verification:

- `test_semantic_learning_sl4.py` validates curriculum history, promotion candidate metadata, rollback metadata, version serialization, and endpoint access.
