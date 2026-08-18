from __future__ import annotations

from aipinho.schemas.cognitive_governance import (
    CognitiveCapability,
    CognitiveEscalationHistory,
    CognitiveEscalationRequest,
    CognitiveEvaluationRequest,
    CognitiveGovernanceHistory,
    CognitiveGovernanceRequest,
    CognitivePolicy,
    CognitivePolicyDecision,
    CognitivePolicyList,
    CognitiveRisk,
    CognitiveRouteList,
    CognitiveRoutingRequest,
    EscalationDecision,
    EscalationPolicy,
    GovernanceAudit,
    GovernanceDecision,
    GovernanceEvidence,
    GovernanceSession,
    RoutingDecision,
)


RISK_ORDER: dict[CognitiveRisk, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


class CognitivePolicyRepository:
    def __init__(self, policies: list[CognitivePolicy] | None = None) -> None:
        self._policies = policies or self._seed_policies()

    def list(self) -> list[CognitivePolicy]:
        return sorted(self._policies, key=lambda item: item.policy_id)

    def get(self, policy_id: str) -> CognitivePolicy | None:
        for policy in self._policies:
            if policy.policy_id == policy_id:
                return policy
        return None

    def for_capability(self, capability: str, scope: str) -> CognitivePolicy | None:
        scoped = [policy for policy in self._policies if policy.capability == capability and policy.scope == scope]
        if scoped:
            return sorted(scoped, key=lambda item: item.policy_id)[0]
        generic = [policy for policy in self._policies if policy.capability == capability and policy.scope == "runtime"]
        return sorted(generic, key=lambda item: item.policy_id)[0] if generic else None

    def _seed_policies(self) -> list[CognitivePolicy]:
        return [
            CognitivePolicy(
                policy_id="cognitive_policy_language_runtime",
                name="Language runtime policy",
                scope="runtime",
                capability="language",
                allowed_models=["local-small", "governed-chat"],
                forbidden_models=["unregistered", "external-unsafe"],
                max_risk="medium",
                max_cost=0.25,
                max_latency_ms=30000,
                requires_approval=False,
            ),
            CognitivePolicy(
                policy_id="cognitive_policy_reasoning_runtime",
                name="Reasoning runtime policy",
                scope="runtime",
                capability="reasoning",
                allowed_models=["local-reasoner", "governed-reasoner"],
                forbidden_models=["unregistered"],
                max_risk="medium",
                max_cost=0.5,
                max_latency_ms=60000,
                requires_approval=True,
                requires_supervisor=True,
                requires_runtime_doctor=True,
            ),
            CognitivePolicy(
                policy_id="cognitive_policy_vision_runtime",
                name="Vision runtime policy",
                scope="runtime",
                capability="vision",
                allowed_models=["local-vision", "governed-vision"],
                forbidden_models=["external-unsafe"],
                max_risk="medium",
                max_cost=0.5,
                max_latency_ms=60000,
                requires_approval=True,
                requires_supervisor=False,
                requires_runtime_doctor=True,
            ),
            CognitivePolicy(
                policy_id="cognitive_policy_ocr_runtime",
                name="OCR runtime policy",
                scope="runtime",
                capability="ocr",
                allowed_models=["local-ocr", "governed-ocr"],
                forbidden_models=["external-unsafe"],
                max_risk="medium",
                max_cost=0.2,
                max_latency_ms=45000,
                requires_approval=False,
            ),
            CognitivePolicy(
                policy_id="cognitive_policy_planning_runtime",
                name="Planning runtime policy",
                scope="runtime",
                capability="planning",
                allowed_models=["local-reasoner", "governed-reasoner"],
                forbidden_models=["unregistered"],
                max_risk="medium",
                max_cost=0.5,
                max_latency_ms=60000,
                requires_approval=True,
                requires_supervisor=True,
                requires_runtime_doctor=True,
            ),
            CognitivePolicy(
                policy_id="cognitive_policy_code_generation_runtime",
                name="Code generation runtime policy",
                scope="runtime",
                capability="code_generation",
                allowed_models=["local-reasoner", "governed-reasoner"],
                forbidden_models=["unregistered", "external-unsafe"],
                max_risk="medium",
                max_cost=0.75,
                max_latency_ms=90000,
                requires_approval=True,
                requires_supervisor=True,
                requires_runtime_doctor=True,
            ),
            CognitivePolicy(
                policy_id="cognitive_policy_code_review_runtime",
                name="Code review runtime policy",
                scope="runtime",
                capability="code_review",
                allowed_models=["local-reasoner", "governed-reasoner"],
                forbidden_models=["unregistered"],
                max_risk="medium",
                max_cost=0.4,
                max_latency_ms=60000,
                requires_approval=False,
                requires_runtime_doctor=True,
            ),
        ]


class CognitivePolicyEngine:
    def __init__(self, repository: CognitivePolicyRepository | None = None) -> None:
        self.repository = repository or CognitivePolicyRepository()

    def list_policies(self) -> CognitivePolicyList:
        policies = self.repository.list()
        return CognitivePolicyList(count=len(policies), policies=policies, inference_executed=False)

    def get_policy(self, policy_id: str) -> CognitivePolicy | None:
        return self.repository.get(policy_id)

    def evaluate(self, request: CognitiveEvaluationRequest) -> CognitivePolicyDecision:
        policy = self.repository.for_capability(request.capability, request.scope)
        if policy is None:
            return CognitivePolicyDecision(status="blocked", policy_id="none", capability=request.capability, model=request.model, reason_codes=["cognitive_policy_missing"])
        reasons: list[str] = []
        if request.model and request.model in policy.forbidden_models:
            reasons.append("model_forbidden_by_policy")
        if request.model and policy.allowed_models and request.model not in policy.allowed_models:
            reasons.append("model_not_allowed_by_policy")
        if RISK_ORDER[request.risk] > RISK_ORDER[policy.max_risk]:
            reasons.append("risk_exceeds_policy")
        if request.estimated_cost is not None and policy.max_cost is not None and request.estimated_cost > policy.max_cost:
            reasons.append("cost_exceeds_policy")
        if request.estimated_latency_ms is not None and policy.max_latency_ms is not None and request.estimated_latency_ms > policy.max_latency_ms:
            reasons.append("latency_exceeds_policy")
        if policy.requires_approval and not request.operator_approved:
            reasons.append("approval_required")
        if policy.requires_supervisor and not request.supervisor_available:
            reasons.append("supervisor_required")
        if policy.requires_runtime_doctor and not request.runtime_doctor_available:
            reasons.append("runtime_doctor_required")
        blocking = [reason for reason in reasons if reason not in {"approval_required", "supervisor_required", "runtime_doctor_required"}]
        status = "blocked" if blocking else "requires_approval" if reasons else "allowed"
        return CognitivePolicyDecision(
            status=status,
            policy_id=policy.policy_id,
            capability=request.capability,
            model=request.model,
            allowed=status == "allowed",
            requires_approval=policy.requires_approval and not request.operator_approved,
            requires_supervisor=policy.requires_supervisor and not request.supervisor_available,
            requires_runtime_doctor=policy.requires_runtime_doctor and not request.runtime_doctor_available,
            reason_codes=reasons,
            deterministic=True,
            inference_executed=False,
        )

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "cognitive_policy_engine",
            "version": "1.0",
            "policies": len(self.repository.list()),
            "deterministic": True,
            "inference_executed": False,
        }


class CapabilityResolver:
    def resolve(self, request: CognitiveRoutingRequest) -> CognitiveCapability:
        if request.capability:
            return request.capability
        intent = str(request.isr.get("intent") or request.contracts.get("operation_type") or "").lower()
        if "patch" in intent or "code" in intent:
            return "code_generation"
        if "review" in intent:
            return "code_review"
        if "plan" in intent:
            return "planning"
        if "vision" in intent or "image" in intent:
            return "vision"
        if "ocr" in intent:
            return "ocr"
        if "reason" in intent or "debug" in intent:
            return "reasoning"
        return "language"


class ModelSelector:
    def select(self, policy: CognitivePolicy, role: str) -> str | None:
        if not policy.allowed_models:
            return None
        role_preferred = {
            "semantic_interpreter": ["local-small", "governed-chat"],
            "planner": ["local-reasoner", "governed-reasoner"],
            "patch_planner": ["local-reasoner", "governed-reasoner"],
            "vision": ["local-vision", "governed-vision"],
            "ocr": ["local-ocr", "governed-ocr"],
        }
        for candidate in role_preferred.get(role, []):
            if candidate in policy.allowed_models:
                return candidate
        return policy.allowed_models[0]


class EscalationResolver:
    def escalation_models(self, policy: CognitivePolicy, decision: CognitivePolicyDecision) -> list[str]:
        if decision.status == "allowed":
            return []
        return [model for model in policy.allowed_models[1:] if model not in policy.forbidden_models]

    def can_escalate(self, policy: CognitivePolicy, decision: CognitivePolicyDecision) -> bool:
        return bool(self.escalation_models(policy, decision)) and "risk_exceeds_policy" not in decision.reason_codes


class RoleBindingResolver:
    def role_can_use(self, role: str, capability: CognitiveCapability) -> bool:
        bindings: dict[str, set[str]] = {
            "semantic_interpreter": {"language", "reasoning", "planning"},
            "planner": {"planning", "reasoning", "language"},
            "patch_planner": {"code_generation", "code_review", "reasoning", "planning"},
            "vision": {"vision"},
            "ocr": {"ocr"},
            "reviewer": {"code_review", "reasoning", "language"},
        }
        return capability in bindings.get(role, {capability})


class CognitiveRouter:
    _routes: list[RoutingDecision] = []

    def __init__(
        self,
        policy_engine: CognitivePolicyEngine | None = None,
        capability_resolver: CapabilityResolver | None = None,
        model_selector: ModelSelector | None = None,
        escalation_resolver: EscalationResolver | None = None,
        role_binding: RoleBindingResolver | None = None,
    ) -> None:
        self.policy_engine = policy_engine or CognitivePolicyEngine()
        self.capability_resolver = capability_resolver or CapabilityResolver()
        self.model_selector = model_selector or ModelSelector()
        self.escalation_resolver = escalation_resolver or EscalationResolver()
        self.role_binding = role_binding or RoleBindingResolver()

    def route(self, request: CognitiveRoutingRequest) -> RoutingDecision:
        capability = self.capability_resolver.resolve(request)
        policy = self.policy_engine.repository.for_capability(capability, request.scope)
        if policy is None:
            decision = RoutingDecision(status="blocked", role=request.role, capability=capability, policy_id="none", reason_codes=["cognitive_policy_missing"])
            self._routes.append(decision)
            return decision
        model = self.model_selector.select(policy, request.role)
        evaluation = self.policy_engine.evaluate(
            CognitiveEvaluationRequest(
                capability=capability,
                model=model,
                risk=request.risk,
                estimated_cost=request.estimated_cost,
                estimated_latency_ms=request.estimated_latency_ms,
                scope=request.scope,
                operator_approved=request.operator_approved,
                supervisor_available=request.supervisor_available,
                runtime_doctor_available=request.runtime_doctor_available,
            )
        )
        reasons = list(evaluation.reason_codes)
        if not self.role_binding.role_can_use(request.role, capability):
            reasons.append("role_not_bound_to_capability")
        status = "blocked" if "role_not_bound_to_capability" in reasons else evaluation.status
        decision = RoutingDecision(
            status=status,
            role=request.role,
            capability=capability,
            model=model,
            policy_id=policy.policy_id,
            requires_supervisor=evaluation.requires_supervisor,
            requires_approval=evaluation.requires_approval,
            can_escalate=self.escalation_resolver.can_escalate(policy, evaluation),
            escalation_models=self.escalation_resolver.escalation_models(policy, evaluation),
            reason_codes=reasons,
            deterministic=True,
            inference_executed=False,
            prompt_interpreted=False,
        )
        self._routes.append(decision)
        return decision

    def routes(self) -> CognitiveRouteList:
        return CognitiveRouteList(count=len(self._routes), routes=list(self._routes), inference_executed=False)


class EscalationPolicyRepository:
    def __init__(self, policies: list[EscalationPolicy] | None = None) -> None:
        self._policies = policies or [
            EscalationPolicy(policy_id="cognitive_escalation_policy_runtime_default", name="Runtime cognitive escalation policy", scope="runtime")
        ]

    def for_scope_and_capability(self, scope: str, capability: CognitiveCapability) -> EscalationPolicy:
        scoped = [policy for policy in self._policies if policy.scope == scope and policy.capability == capability]
        if scoped:
            return sorted(scoped, key=lambda item: item.policy_id)[0]
        generic = [policy for policy in self._policies if policy.scope == scope and policy.capability is None]
        if generic:
            return sorted(generic, key=lambda item: item.policy_id)[0]
        return sorted(self._policies, key=lambda item: item.policy_id)[0]


class ConfidenceEvaluator:
    def evaluate(self, request: CognitiveEscalationRequest) -> float:
        if request.confidence is not None:
            return self._clamp(request.confidence)
        for source in (request.isr, request.contracts):
            value = source.get("confidence")
            if isinstance(value, int | float):
                return self._clamp(float(value))
        return 0.5

    def _clamp(self, value: float) -> float:
        return max(0.0, min(1.0, value))


class ComplexityEstimator:
    def estimate(self, request: CognitiveEscalationRequest) -> float:
        score = 0.0
        score += min(len(self._sequence(request.isr.get("entities"))) * 0.08, 0.24)
        score += min(len(self._sequence(request.isr.get("constraints"))) * 0.1, 0.2)
        score += min(len(self._sequence(request.isr.get("expected_outputs"))) * 0.1, 0.2)
        score += min(len(self._sequence(request.contracts.get("requested_actions"))) * 0.12, 0.24)
        if self._truthy_nested(request.contracts, "approval_required", "requires_approval"):
            score += 0.18
        if self._truthy_nested(request.contracts, "validation_required", "requires_validation"):
            score += 0.16
        if self._truthy_nested(request.contracts, "artifact_generation", "requires_artifacts"):
            score += 0.1
        return max(0.0, min(1.0, score))

    def _sequence(self, value: object) -> list[object]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple | set):
            return list(value)
        if isinstance(value, dict):
            return list(value.values())
        return [value]

    def _truthy_nested(self, source: dict[str, object], *keys: str) -> bool:
        pending: list[object] = [source]
        while pending:
            current = pending.pop()
            if isinstance(current, dict):
                for key, value in current.items():
                    if key in keys and bool(value):
                        return True
                    pending.append(value)
            elif isinstance(current, list):
                pending.extend(current)
        return False


class CognitiveEscalationEngine:
    _history: list[EscalationDecision] = []

    def __init__(
        self,
        policy_repository: EscalationPolicyRepository | None = None,
        confidence_evaluator: ConfidenceEvaluator | None = None,
        complexity_estimator: ComplexityEstimator | None = None,
    ) -> None:
        self.policy_repository = policy_repository or EscalationPolicyRepository()
        self.confidence_evaluator = confidence_evaluator or ConfidenceEvaluator()
        self.complexity_estimator = complexity_estimator or ComplexityEstimator()

    def escalate(self, request: CognitiveEscalationRequest) -> EscalationDecision:
        route = request.routing_decision
        policy = self.policy_repository.for_scope_and_capability(request.scope, route.capability)
        confidence = self.confidence_evaluator.evaluate(request)
        complexity = self.complexity_estimator.estimate(request)
        reasons: list[str] = []
        action = "remain"
        target_model: str | None = None
        requires_human_validation = False
        blocked = False

        if route.status == "blocked":
            action = "block"
            blocked = True
            reasons.append("routing_decision_blocked")
        elif RISK_ORDER[request.risk] > RISK_ORDER[policy.max_risk_without_block]:
            action = "block"
            blocked = True
            reasons.append("risk_exceeds_escalation_policy")
        elif request.risk in {"high", "critical"} and policy.requires_human_for_high_risk:
            action = "request_human_validation"
            requires_human_validation = True
            reasons.append("human_validation_required_for_risk")
        elif confidence < policy.low_confidence_threshold and complexity >= policy.high_complexity_threshold and route.escalation_models:
            action = "escalate"
            target_model = route.escalation_models[0]
            reasons.extend(["low_confidence", "high_complexity", "escalation_model_available"])
        elif confidence < policy.human_validation_confidence_threshold:
            action = "request_human_validation"
            requires_human_validation = True
            reasons.append("confidence_below_human_validation_threshold")
        elif complexity >= policy.high_complexity_threshold and route.can_escalate and route.escalation_models:
            action = "escalate"
            target_model = route.escalation_models[0]
            reasons.extend(["high_complexity", "escalation_model_available"])
        else:
            reasons.append("current_route_sufficient")

        decision = EscalationDecision(
            action=action,
            capability=route.capability,
            role=route.role,
            routing_decision_id=route.route_id,
            current_model=route.model,
            target_model=target_model,
            confidence=confidence,
            complexity=complexity,
            risk=request.risk,
            policy_id=policy.policy_id,
            requires_human_validation=requires_human_validation,
            blocked=blocked,
            reason_codes=reasons,
            trace=[
                {"step": "confidence_evaluated", "value": confidence},
                {"step": "complexity_estimated", "value": complexity},
                {"step": "risk_evaluated", "value": request.risk},
                {"step": "decision_selected", "value": action},
            ],
            deterministic=True,
            inference_executed=False,
        )
        self._history.append(decision)
        return decision

    def history(self) -> CognitiveEscalationHistory:
        return CognitiveEscalationHistory(count=len(self._history), decisions=list(self._history), inference_executed=False)


class CognitiveGovernanceController:
    _history: list[GovernanceDecision] = []

    def __init__(
        self,
        policy_engine: CognitivePolicyEngine | None = None,
        router: CognitiveRouter | None = None,
        escalation_engine: CognitiveEscalationEngine | None = None,
    ) -> None:
        self.policy_engine = policy_engine or CognitivePolicyEngine()
        self.router = router or CognitiveRouter(policy_engine=self.policy_engine)
        self.escalation_engine = escalation_engine or CognitiveEscalationEngine()

    def evaluate(self, request: CognitiveGovernanceRequest) -> GovernanceDecision:
        route = self.router.route(
            CognitiveRoutingRequest(
                isr=request.isr,
                contracts=request.contracts,
                role=request.role,
                capability=request.capability,
                scope=request.scope,
                risk=request.risk,
                estimated_cost=request.estimated_cost,
                estimated_latency_ms=request.estimated_latency_ms,
                operator_approved=request.operator_approved,
                supervisor_available=request.supervisor_available,
                runtime_doctor_available=request.runtime_doctor_available,
            )
        )
        policy_decision = self.policy_engine.evaluate(
            CognitiveEvaluationRequest(
                capability=route.capability,
                model=route.model,
                risk=request.risk,
                estimated_cost=request.estimated_cost,
                estimated_latency_ms=request.estimated_latency_ms,
                scope=request.scope,
                operator_approved=request.operator_approved,
                supervisor_available=request.supervisor_available,
                runtime_doctor_available=request.runtime_doctor_available,
            )
        )
        escalation = self.escalation_engine.escalate(
            CognitiveEscalationRequest(
                isr=request.isr,
                contracts=request.contracts,
                routing_decision=route,
                confidence=request.confidence,
                risk=request.risk,
                scope=request.scope,
            )
        )
        final_model = escalation.target_model if escalation.action == "escalate" else route.model
        target_policy_decision = policy_decision
        if final_model != route.model:
            target_policy_decision = self.policy_engine.evaluate(
                CognitiveEvaluationRequest(
                    capability=route.capability,
                    model=final_model,
                    risk=request.risk,
                    estimated_cost=request.estimated_cost,
                    estimated_latency_ms=request.estimated_latency_ms,
                    scope=request.scope,
                    operator_approved=request.operator_approved,
                    supervisor_available=request.supervisor_available,
                    runtime_doctor_available=request.runtime_doctor_available,
                )
            )

        reasons = self._reason_codes(route, policy_decision, target_policy_decision, escalation)
        requires_approval = route.requires_approval or policy_decision.requires_approval or target_policy_decision.requires_approval
        requires_supervisor = route.requires_supervisor or policy_decision.requires_supervisor or target_policy_decision.requires_supervisor
        requires_runtime_doctor = policy_decision.requires_runtime_doctor or target_policy_decision.requires_runtime_doctor
        requires_human_validation = escalation.requires_human_validation
        blocked = route.status == "blocked" or policy_decision.status == "blocked" or target_policy_decision.status == "blocked" or escalation.blocked
        pending_gate = requires_approval or requires_supervisor or requires_runtime_doctor or requires_human_validation
        status = "blocked" if blocked else "requires_approval" if pending_gate else "allowed"
        evidence = self._evidence(request, route, policy_decision, target_policy_decision, escalation)
        session = GovernanceSession(role=route.role, capability=route.capability, scope=request.scope)
        audit = GovernanceAudit(
            governance_session_id=session.governance_session_id,
            route_id=route.route_id,
            policy_decision_id=target_policy_decision.decision_id,
            escalation_id=escalation.escalation_id,
            status=status,
            evidence_ids=[item.evidence_id for item in evidence],
            trace=[
                {"step": "semantic_runtime_input_received", "isr_present": bool(request.isr)},
                {"step": "policy_engine_evaluated", "status": policy_decision.status},
                {"step": "router_resolved", "route_id": route.route_id},
                {"step": "escalation_evaluated", "action": escalation.action},
                {"step": "governance_decision_finalized", "status": status},
            ],
            inference_executed=False,
        )
        decision = GovernanceDecision(
            status=status,
            allowed=status == "allowed",
            role=route.role,
            capability=route.capability,
            model=final_model,
            requires_approval=requires_approval,
            requires_supervisor=requires_supervisor,
            requires_runtime_doctor=requires_runtime_doctor,
            requires_human_validation=requires_human_validation,
            route=route,
            policy_decision=target_policy_decision,
            escalation=escalation,
            session=session,
            evidence=evidence,
            audit=audit,
            reason_codes=reasons,
            inference_executed=False,
        )
        self._history.append(decision)
        return decision

    def history(self) -> CognitiveGovernanceHistory:
        return CognitiveGovernanceHistory(count=len(self._history), decisions=list(self._history), inference_executed=False)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "cognitive_governance_controller",
            "version": "1.0",
            "decisions": len(self._history),
            "deterministic": True,
            "inference_executed": False,
        }

    def _reason_codes(
        self,
        route: RoutingDecision,
        policy_decision: CognitivePolicyDecision,
        target_policy_decision: CognitivePolicyDecision,
        escalation: EscalationDecision,
    ) -> list[str]:
        reasons = list(dict.fromkeys(route.reason_codes + policy_decision.reason_codes + target_policy_decision.reason_codes + escalation.reason_codes))
        if not reasons:
            reasons.append("cognitive_governance_allowed")
        return reasons

    def _evidence(
        self,
        request: CognitiveGovernanceRequest,
        route: RoutingDecision,
        policy_decision: CognitivePolicyDecision,
        target_policy_decision: CognitivePolicyDecision,
        escalation: EscalationDecision,
    ) -> list[GovernanceEvidence]:
        return [
            GovernanceEvidence(
                source="semantic_runtime",
                summary="Canonical semantic inputs received by governance controller.",
                data={"isr_keys": sorted(request.isr.keys()), "contract_keys": sorted(request.contracts.keys())},
            ),
            GovernanceEvidence(
                source="policy_engine",
                summary="Cognitive policy evaluated without model inference.",
                refs=[policy_decision.decision_id, target_policy_decision.decision_id],
                data={"initial_status": policy_decision.status, "target_status": target_policy_decision.status},
            ),
            GovernanceEvidence(
                source="router",
                summary="Role, capability, and model route resolved.",
                refs=[route.route_id],
                data={"role": route.role, "capability": route.capability, "model": route.model, "status": route.status},
            ),
            GovernanceEvidence(
                source="escalation",
                summary="Cognitive escalation evaluated without inference.",
                refs=[escalation.escalation_id],
                data={"action": escalation.action, "target_model": escalation.target_model, "blocked": escalation.blocked},
            ),
        ]
