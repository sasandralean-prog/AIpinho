# SL4 Semantic Curriculum

Status: SL4_SEMANTIC_CURRICULUM_READY

Implemented:

- `SemanticCurriculum`
- `SemanticCurriculumEntry`
- `SemanticCapability`
- `SemanticCompetency`
- `SemanticEvolution`
- `SemanticMilestone`
- `SemanticPromotionCandidate`
- `SemanticCurriculumRepository`
- `SemanticCurriculumSerializer`
- `SemanticCurriculumService`

Endpoints:

- `GET /api/v1/runtime/semantic-learning/curriculum`
- `GET /api/v1/runtime/semantic-learning/curriculum/{id}`
- `POST /api/v1/runtime/semantic-learning/curriculum/promote`
- `POST /api/v1/runtime/semantic-learning/curriculum/review`

Guarantees:

- organizes acquired semantic knowledge;
- separates learning/stable maturity states;
- records evolution history;
- proposes competency promotion candidates;
- keeps full traceability;
- never auto-promotes;
- never modifies Semantic Runtime automatically;
- every future incorporation remains governed by human approval and explicit versioning.

Verification:

- `python -m pytest tests\unit\test_semantic_learning_sl3.py tests\unit\test_semantic_learning_sl4.py -q` -> 9 passed
- `python -m compileall src\aipinho\schemas\semantic_learning.py src\aipinho\services\semantic_learning_service.py src\aipinho\api\routers\semantic_learning_router.py` -> passed
- Semantic Learning SL1-SL4 + SR regression slice -> 45 passed
- Router registration check -> 133 routers, semantic-learning registered
