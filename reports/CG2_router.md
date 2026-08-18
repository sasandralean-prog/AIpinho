# CG2 Cognitive Router

Status: CG2_COGNITIVE_ROUTER_READY

Implemented:

- `CognitiveRouter`
- `CapabilityResolver`
- `ModelSelector`
- `EscalationResolver`
- `RoleBindingResolver`
- `RoutingDecision`
- `CognitiveRoutingRequest`
- `CognitiveRouteList`

Endpoints:

- `POST /api/v1/runtime/cognitive/router`
- `GET /api/v1/runtime/cognitive/routes`

Guarantees:

- deterministic routing;
- no model execution;
- no prompt interpretation;
- compatible with Semantic Runtime and Cognitive Policy Engine.

Verification:

- `python -m pytest tests\unit\test_cognitive_router_cg2.py -q` -> 6 passed
- `python -m compileall src\aipinho\schemas\cognitive_governance.py src\aipinho\services\cognitive_policy_engine_service.py src\aipinho\api\routers\cognitive_governance_router.py` -> passed
- `python -m pytest tests\unit\test_cognitive_policy_engine_cg1.py tests\unit\test_cognitive_router_cg2.py tests\unit\test_semantic_capability_registry.py tests\unit\test_isr_schema.py -q` -> 22 passed
- Router registration check -> 134 routers, cognitive governance registered
