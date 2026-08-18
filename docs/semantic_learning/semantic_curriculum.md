# Semantic Curriculum

The Semantic Curriculum organizes accumulated semantic knowledge into versioned, governable competencies.

It does not modify Semantic Runtime, contracts, models, rules, or behavior automatically.

## Components

- `SemanticCurriculum`
- `SemanticCurriculumEntry`
- `SemanticCapability`
- `SemanticCompetency`
- `SemanticEvolution`
- `SemanticMilestone`
- `SemanticPromotionCandidate`
- `SemanticCurriculumRepository`
- `SemanticCurriculumSerializer`

## Maturity Levels

- `UNKNOWN`
- `EXPERIMENTAL`
- `LEARNING`
- `STABLE`
- `CANONICAL`
- `DEPRECATED`
- `REMOVED`

## Promotion

Semantic promotion creates a `SemanticPromotionCandidate`.

Promotion candidates include:

- competency;
- reason;
- knowledge used;
- patterns used;
- evidence;
- related regressions;
- expected impact;
- risks;
- rollback;
- approval requirement.

No promotion is automatic. Every candidate requires human approval and explicit future versioning.

## Reports

The service returns:

- `semantic_curriculum_report.md` as markdown text;
- `semantic_curriculum.json` as the curriculum payload;
- `semantic_evolution_history.json` as structured history.

## Endpoints

- `GET /api/v1/runtime/semantic-learning/curriculum`
- `GET /api/v1/runtime/semantic-learning/curriculum/{id}`
- `POST /api/v1/runtime/semantic-learning/curriculum/promote`
- `POST /api/v1/runtime/semantic-learning/curriculum/review`
