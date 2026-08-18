from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.repositories.skills.skill_repositories import (
    SkillAuditRepository,
    SkillCatalogRepository,
    SkillRegistryRepository,
    SkillTraceRepository,
)
from aipinho.schemas.events.contracts import EventPublishRequest
from aipinho.schemas.skills.contracts import (
    SkillAudit,
    SkillCompositionPlan,
    SkillCompositionResult,
    SkillContract,
    SkillDryRunRequest,
    SkillDryRunResult,
    SkillExecutionEnvelope,
    SkillExecutionResult,
    SkillInstallPreview,
    SkillInstallRequest,
    SkillInstallResult,
    SkillOutputValidationResult,
    SkillPreviewRequest,
    SkillPreviewResult,
    SkillRegistryEntry,
    SkillRouteCandidate,
    SkillRouteRequest,
    SkillRouteResult,
    SkillTrace,
    SkillTraceStep,
)
from aipinho.services.context.context_core import ContextBundleRepository
from aipinho.services.events.event_core import EventPublisherService
from aipinho.services.tools.tool_contract_core import (
    GovernedToolRegistryService,
    ToolPermissionService,
    ToolResultSanitizer,
)
from aipinho.utils.yaml_loader import load_yaml_file

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
ACTIVE_PREVIEW_STATUSES = {"enabled", "experimental"}
BLOCKED_AUTHORITY_FIELDS = {
    "policy_decision",
    "context_admission",
    "context_items",
    "selected_model",
    "model_id",
    "final_status",
    "approval_granted",
    "memory_write",
    "workspace_write",
}
SECURITY_SIGNALS = {"credential_required", "secret_required", "api_key_required"}


def _tokens(value: str | None) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", (value or "").lower()))


class SkillContractLoader:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "skills" / "skill_catalog.yaml"

    def load(self) -> dict[str, SkillContract]:
        data = load_yaml_file(self.path, root=PATHS.project_root)
        raw = data.get("skills", {})
        if not isinstance(raw, dict):
            raise ValueError("skill_catalog_skills_must_be_mapping")
        return {skill_id: SkillContract(skill_id=skill_id, **entry) for skill_id, entry in raw.items()}


class SkillContractValidator:
    REQUIRED_KEYS = {
        "skill_id", "namespace", "category", "display_name", "purpose", "when_to_use",
        "when_not_to_use", "input_contract", "output_contract", "required_context_purpose",
        "required_capabilities", "allowed_tools", "forbidden_tools", "risk_level",
        "approval_required", "validation", "fallback", "anti_triggers", "examples",
        "failure_modes", "events_emitted", "debugger_trace_policy",
    }

    def validate(self, payload: SkillContract | dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload, dict):
            missing = sorted(self.REQUIRED_KEYS - set(payload))
            if missing:
                return {"status": "rejected", "valid": False, "reasons": [f"missing:{item}" for item in missing]}
        try:
            contract = payload if isinstance(payload, SkillContract) else SkillContract(**payload)
        except Exception as exc:
            return {"status": "rejected", "valid": False, "reasons": [str(exc)]}
        reasons: list[str] = []
        if contract.status not in {"enabled", "disabled", "degraded", "experimental", "future_stub"}:
            reasons.append("invalid_status")
        if contract.risk_level not in RISK_ORDER:
            reasons.append("invalid_risk_level")
        if contract.supports_real_execution:
            reasons.append("real_execution_forbidden")
        return {
            "status": "accepted" if not reasons else "rejected",
            "valid": not reasons,
            "reasons": reasons,
            "skill_id": contract.skill_id,
        }


class SkillRegistryService:
    def __init__(self, loader: SkillContractLoader | None = None) -> None:
        self.loader = loader or SkillContractLoader()
        self.repository = SkillRegistryRepository()
        self._contracts: dict[str, SkillContract] | None = None

    @property
    def contracts(self) -> dict[str, SkillContract]:
        if self._contracts is None:
            self._contracts = self.loader.load()
            entries = [
                SkillRegistryEntry(
                    skill_id=skill.skill_id,
                    status=skill.status,
                    risk_level=skill.risk_level,
                    execution_mode=skill.execution_mode,
                ).model_dump()
                for skill in self._contracts.values()
            ]
            self.repository.save(entries)
        return self._contracts

    def get(self, skill_id: str) -> SkillContract | None:
        return self.contracts.get(skill_id)

    def list(self) -> list[SkillContract]:
        return sorted(self.contracts.values(), key=lambda item: item.skill_id)

    def status(self) -> dict[str, Any]:
        skills = self.list()
        return {
            "status": "ok" if skills else "degraded",
            "enabled": True,
            "skills_loaded": len(skills),
            "enabled_skills": len([skill for skill in skills if skill.status in ACTIVE_PREVIEW_STATUSES]),
            "real_execution_enabled": False,
            "preview_enabled": True,
            "dry_run_enabled": True,
            "install_real_enabled": False,
            "unknown_skill_blocked": True,
            "critical_skills_disabled": all(skill.status in {"disabled", "future_stub"} for skill in skills if skill.risk_level == "critical"),
            "external_connectors_disabled_by_default": all(
                not skill.default_enabled for skill in skills if skill.namespace not in {"aipinho"}
            ),
        }


class SkillCatalogService:
    def __init__(self, registry: SkillRegistryService | None = None) -> None:
        self.registry = registry or SkillRegistryService()
        self.repository = SkillCatalogRepository()

    def catalog(self) -> list[SkillContract]:
        skills = self.registry.list()
        self.repository.save([skill.model_dump() for skill in skills])
        return skills

    def filter(self, *, category: str | None = None, status: str | None = None) -> list[SkillContract]:
        values = self.catalog()
        if category:
            values = [skill for skill in values if skill.category == category]
        if status:
            values = [skill for skill in values if skill.status == status]
        return values


class SkillAntiTriggerService:
    def blocked_reasons(self, contract: SkillContract, signals: list[str]) -> list[str]:
        signal_set = set(signals)
        reasons = [item.reason for item in contract.anti_triggers if item.signal in signal_set]
        if signal_set & SECURITY_SIGNALS:
            reasons.append("credential_or_secret_request_blocked")
        return list(dict.fromkeys(reasons))


class SkillCapabilityResolver:
    def resolve(self, contract: SkillContract, granted_capabilities: list[str]) -> dict[str, Any]:
        granted = set(granted_capabilities)
        required = set(contract.required_capabilities)
        missing = sorted(required - granted)
        return {
            "status": "allowed" if not missing else "blocked",
            "required": sorted(required),
            "granted": sorted(granted),
            "missing": missing,
            "skill_cannot_expand_capabilities": True,
        }


class SkillContextRequirementService:
    def validate(self, contract: SkillContract, context_bundle_id: str | None) -> dict[str, Any]:
        if not context_bundle_id:
            return {"status": "blocked", "reasons": ["missing_context_bundle"]}
        bundle = ContextBundleRepository().get(context_bundle_id)
        if bundle is None:
            return {"status": "blocked", "reasons": ["context_bundle_not_found"]}
        reasons: list[str] = []
        if bundle.purpose != contract.required_context_purpose:
            reasons.append("context_purpose_mismatch")
        if not bundle.safe_for_prompt:
            reasons.append("context_bundle_not_safe")
        return {
            "status": "allowed" if not reasons else "blocked",
            "reasons": reasons,
            "bundle_id": bundle.bundle_id,
            "purpose": bundle.purpose,
            "context_owner": "context_kernel",
        }


class SkillToolPolicyService:
    def validate(self, contract: SkillContract, requested_tools: list[str]) -> dict[str, Any]:
        requested = set(requested_tools)
        not_allowed = sorted(requested - set(contract.allowed_tools))
        forbidden = sorted(requested & set(contract.forbidden_tools))
        reasons = [f"tool_not_allowed:{item}" for item in not_allowed] + [f"tool_forbidden:{item}" for item in forbidden]
        return {"status": "allowed" if not reasons else "blocked", "reasons": reasons}


class SkillRiskService:
    def evaluate(self, contract: SkillContract, approval_id: str | None = None) -> dict[str, Any]:
        approval_required = contract.approval_required or contract.risk_level in {"high", "critical"}
        if contract.risk_level == "critical":
            return {"status": "blocked", "approval_required": True, "reason": "critical_skill_disabled"}
        if approval_required and not approval_id:
            return {"status": "preview_only", "approval_required": True, "reason": "approval_required_for_risk"}
        return {"status": "preview_only", "approval_required": approval_required, "reason": "real_execution_disabled"}


class SkillFallbackService:
    def fallback(self, contract: SkillContract, reasons: list[str]) -> dict[str, Any]:
        return {
            "mode": contract.fallback.mode,
            "target_skill_id": contract.fallback.target_skill_id,
            "human_message": contract.fallback.human_message,
            "reasons": reasons,
            "execution_started": False,
        }


class SkillTraceService:
    def __init__(self, repository: SkillTraceRepository | None = None) -> None:
        self.repository = repository or SkillTraceRepository()

    def create(self, *, skill_id: str | None, operation: str, status: str, steps: list[SkillTraceStep]) -> SkillTrace:
        return self.repository.save(SkillTrace(skill_id=skill_id, operation=operation, status=status, steps=steps))

    def get(self, trace_id: str) -> dict[str, Any] | None:
        return self.repository.get(trace_id)


class SkillAuditService:
    def __init__(self, repository: SkillAuditRepository | None = None) -> None:
        self.repository = repository or SkillAuditRepository()

    def record(self, action: str, skill_id: str | None, allowed: bool, reasons: list[str]) -> SkillAudit:
        return self.repository.append(SkillAudit(action=action, skill_id=skill_id, allowed=allowed, reasons=reasons))


class SkillEventEmitter:
    ALLOWED = {
        "skill_registered", "skill_contract_validated", "skill_contract_rejected",
        "skill_route_requested", "skill_route_selected", "skill_route_blocked",
        "skill_preview_created", "skill_dry_run_started", "skill_dry_run_completed",
        "skill_dry_run_blocked", "skill_execution_blocked", "skill_output_validated",
        "skill_output_rejected", "skill_install_preview_created", "skill_install_blocked",
        "tool_permission_granted", "tool_permission_denied",
        "tool_invocation_preview_created", "tool_invocation_blocked",
    }

    def __init__(self, publisher: EventPublisherService | None = None) -> None:
        self.publisher = publisher or EventPublisherService()

    def emit(self, event_type: str, summary: str, payload: dict[str, Any], *, source_service: str = "skill_runtime") -> dict[str, Any]:
        if event_type not in self.ALLOWED:
            raise ValueError("unknown_skill_event")
        event = self.publisher.publish(EventPublishRequest(
            event_type=event_type,
            source_service=source_service,
            human_summary=summary,
            payload=payload,
        ))
        return event.model_dump()


class SkillRoutingPolicyService:
    def score(self, request: SkillRouteRequest, contract: SkillContract) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        if request.requested_skill_id == contract.skill_id:
            score += 1.0
            reasons.append("explicit_skill_id_match")
        if request.category and request.category == contract.category:
            score += 0.7
            reasons.append("category_match")
        if request.context_purpose and request.context_purpose == contract.required_context_purpose:
            score += 0.4
            reasons.append("context_purpose_match")
        purpose_tokens = _tokens(request.purpose)
        contract_tokens = _tokens(contract.purpose + " " + " ".join(contract.when_to_use))
        overlap = purpose_tokens & contract_tokens
        if overlap:
            score += min(0.5, len(overlap) * 0.1)
            reasons.append("purpose_evidence_match")
        return score, reasons


class SkillRouterService:
    def __init__(self, registry: SkillRegistryService | None = None) -> None:
        self.registry = registry or SkillRegistryService()
        self.policy = SkillRoutingPolicyService()
        self.anti_trigger = SkillAntiTriggerService()
        self.capabilities = SkillCapabilityResolver()
        self.trace = SkillTraceService()
        self.audit = SkillAuditService()
        self.events = SkillEventEmitter()

    def route(self, request: SkillRouteRequest) -> SkillRouteResult:
        self.events.emit("skill_route_requested", "Roteamento de skill solicitado.", request.model_dump(), source_service="skill_router")
        candidates: list[SkillRouteCandidate] = []
        blocked: list[str] = []
        for contract in self.registry.list():
            if contract.status not in ACTIVE_PREVIEW_STATUSES:
                continue
            if RISK_ORDER.get(contract.risk_level, 99) > RISK_ORDER.get(request.risk_ceiling, 3):
                continue
            anti = self.anti_trigger.blocked_reasons(contract, request.signals)
            if anti:
                if request.requested_skill_id == contract.skill_id:
                    blocked.extend(anti)
                continue
            capability = self.capabilities.resolve(contract, request.granted_capabilities)
            if capability["missing"]:
                if request.requested_skill_id == contract.skill_id:
                    blocked.extend([f"missing_capability:{item}" for item in capability["missing"]])
                continue
            score, reasons = self.policy.score(request, contract)
            if score > 0:
                candidates.append(SkillRouteCandidate(
                    skill_id=contract.skill_id,
                    score=round(score, 3),
                    reasons=reasons,
                    approval_required=contract.approval_required,
                    execution_mode=contract.execution_mode,
                ))
        candidates.sort(key=lambda item: (-item.score, item.skill_id))
        status = "selected" if candidates else "blocked"
        trace = self.trace.create(
            skill_id=candidates[0].skill_id if candidates else request.requested_skill_id,
            operation="route",
            status=status,
            steps=[SkillTraceStep(stage="skill_router", decision=status, reason="candidate_scoring_completed", details={"candidate_count": len(candidates), "blocked": blocked})],
        )
        event_type = "skill_route_selected" if candidates else "skill_route_blocked"
        self.events.emit(event_type, "Skill candidata selecionada." if candidates else "Roteamento de skill bloqueado.", {"trace_id": trace.trace_id, "candidates": [item.model_dump() for item in candidates], "blocked": blocked}, source_service="skill_router")
        self.audit.record("route", candidates[0].skill_id if candidates else request.requested_skill_id, bool(candidates), blocked)
        return SkillRouteResult(status=status, candidates=candidates, blocked_reasons=list(dict.fromkeys(blocked or ([] if candidates else ["no_eligible_skill"]))), trace_id=trace.trace_id)


class SkillExecutionEnvelopeBuilder:
    def build(self, contract: SkillContract, request: SkillPreviewRequest, allowed_tools: list[str], denied_tools: list[str]) -> SkillExecutionEnvelope:
        return SkillExecutionEnvelope(
            skill_id=contract.skill_id,
            context_bundle_id=str(request.context_bundle_id),
            granted_capabilities=sorted(set(request.granted_capabilities)),
            allowed_tools=allowed_tools,
            denied_tools=denied_tools,
            approval_required=contract.approval_required,
            side_effects_allowed=False,
            real_execution_allowed=False,
            task_contract_snapshot=request.task_contract,
        )


class SkillPreviewService:
    def __init__(self, registry: SkillRegistryService | None = None) -> None:
        self.registry = registry or SkillRegistryService()
        self.validator = SkillContractValidator()
        self.context = SkillContextRequirementService()
        self.capabilities = SkillCapabilityResolver()
        self.tools = SkillToolPolicyService()
        self.tool_permissions = ToolPermissionService()
        self.risk = SkillRiskService()
        self.anti_trigger = SkillAntiTriggerService()
        self.trace = SkillTraceService()
        self.audit = SkillAuditService()
        self.events = SkillEventEmitter()

    def preview(self, request: SkillPreviewRequest) -> SkillPreviewResult:
        contract = self.registry.get(request.skill_id)
        blocked: list[str] = []
        warnings: list[str] = []
        if contract is None:
            blocked.append("unknown_skill")
            return self._finish(request, None, blocked, warnings)
        validation = self.validator.validate(contract)
        if not validation["valid"]:
            blocked.extend(validation["reasons"])
        if contract.status not in ACTIVE_PREVIEW_STATUSES:
            blocked.append("skill_disabled")
        blocked.extend(self.anti_trigger.blocked_reasons(contract, request.signals))
        context = self.context.validate(contract, request.context_bundle_id)
        blocked.extend(context.get("reasons", []))
        capability = self.capabilities.resolve(contract, request.granted_capabilities)
        blocked.extend([f"missing_capability:{item}" for item in capability["missing"]])
        allowed_by_task = set(request.task_contract.get("allowed_capabilities", request.granted_capabilities))
        expansion = sorted(set(contract.required_capabilities) - allowed_by_task)
        blocked.extend([f"contract_expansion_blocked:{item}" for item in expansion])
        authority_fields = sorted(BLOCKED_AUTHORITY_FIELDS & set(request.task_contract))
        blocked.extend([f"skill_authority_field_forbidden:{item}" for item in authority_fields])
        requested_tools = request.requested_tools or list(contract.allowed_tools)
        tool_policy = self.tools.validate(contract, requested_tools)
        blocked.extend(tool_policy["reasons"])
        permission = self.tool_permissions.preview(
            skill_id=contract.skill_id,
            requested_tools=requested_tools,
            contract_allowed_tools=contract.allowed_tools,
            contract_forbidden_tools=contract.forbidden_tools,
            granted_capabilities=request.granted_capabilities,
            approval_id=request.approval_id,
        )
        blocked.extend([f"tool_permission_denied:{item}:{permission.reasons.get(item, 'denied')}" for item in permission.denied_tools])
        risk = self.risk.evaluate(contract, request.approval_id)
        if risk["status"] == "blocked":
            blocked.append(str(risk["reason"]))
        elif risk["approval_required"] and not request.approval_id:
            warnings.append("approval_required_preview_only")
        envelope = SkillExecutionEnvelopeBuilder().build(contract, request, permission.allowed_tools, permission.denied_tools)
        return self._finish(request, contract, blocked, warnings, envelope=envelope, approval_required=bool(risk["approval_required"]))

    def _finish(
        self,
        request: SkillPreviewRequest,
        contract: SkillContract | None,
        blocked: list[str],
        warnings: list[str],
        *,
        envelope: SkillExecutionEnvelope | None = None,
        approval_required: bool = False,
    ) -> SkillPreviewResult:
        blocked = list(dict.fromkeys(blocked))
        status = "blocked" if blocked else "preview"
        steps = []
        if contract and not blocked:
            steps = [
                {"stage": "contract_validation", "mode": "read_only"},
                {"stage": "context_bundle_reference", "owner": "context_kernel"},
                {"stage": "tool_permission_preview", "tools": envelope.allowed_tools if envelope else []},
                {"stage": "output_validation", "owner": "skill_output_validator"},
            ]
        trace = self.trace.create(
            skill_id=request.skill_id,
            operation="preview",
            status=status,
            steps=[SkillTraceStep(stage="skill_preview", decision=status, reason="preview_contract_evaluated", details={"blocked_reasons": blocked, "warnings": warnings})],
        )
        result = SkillPreviewResult(
            status=status,
            skill_id=request.skill_id,
            envelope=envelope,
            planned_steps=steps,
            blocked_reasons=blocked,
            warnings=warnings,
            approval_required=approval_required,
            safe_to_execute=False,
            side_effects_performed=False,
            trace_id=trace.trace_id,
        )
        event_type = "skill_preview_created" if not blocked else "skill_execution_blocked"
        self.events.emit(event_type, "Preview de skill criado sem efeitos colaterais." if not blocked else "Preview de skill bloqueado.", result.model_dump())
        self.audit.record("preview", request.skill_id, not blocked, blocked)
        return result


class SkillOutputValidator:
    def __init__(self, registry: SkillRegistryService | None = None) -> None:
        self.registry = registry or SkillRegistryService()
        self.sanitizer = ToolResultSanitizer()
        self.events = SkillEventEmitter()

    def validate(self, skill_id: str, output: dict[str, Any]) -> SkillOutputValidationResult:
        contract = self.registry.get(skill_id)
        if contract is None:
            return SkillOutputValidationResult(status="rejected", skill_id=skill_id, accepted=False, violations=["unknown_skill"])
        sanitized = self.sanitizer.sanitize(output)
        required = contract.output_contract.required
        missing = [field for field in required if field not in sanitized]
        authority = sorted(BLOCKED_AUTHORITY_FIELDS & set(sanitized))
        violations = [f"skill_output_authority_forbidden:{field}" for field in authority]
        accepted = not missing and not violations
        result = SkillOutputValidationResult(
            status="accepted" if accepted else "rejected",
            skill_id=skill_id,
            accepted=accepted,
            missing_fields=missing,
            violations=violations,
            sanitized_output=sanitized,
        )
        self.events.emit("skill_output_validated" if accepted else "skill_output_rejected", "Saida de skill validada." if accepted else "Saida de skill rejeitada.", result.model_dump())
        return result


class SkillDryRunService:
    def __init__(self, preview_service: SkillPreviewService | None = None) -> None:
        self.preview_service = preview_service or SkillPreviewService()
        self.output_validator = SkillOutputValidator(self.preview_service.registry)
        self.trace = SkillTraceService()
        self.events = SkillEventEmitter()

    def dry_run(self, request: SkillDryRunRequest) -> SkillDryRunResult:
        self.events.emit("skill_dry_run_started", "Dry-run de skill iniciado.", {"skill_id": request.skill_id})
        if request.side_effects_allowed:
            blocked = ["side_effects_must_be_false"]
            preview = None
        else:
            preview = self.preview_service.preview(SkillPreviewRequest(**request.model_dump(exclude={"side_effects_allowed"})))
            blocked = list(preview.blocked_reasons)
        if blocked:
            trace = self.trace.create(
                skill_id=request.skill_id,
                operation="dry_run",
                status="blocked",
                steps=[SkillTraceStep(stage="skill_dry_run", decision="blocked", reason="dry_run_preconditions_failed", details={"blocked_reasons": blocked})],
            )
            result = SkillDryRunResult(status="blocked", skill_id=request.skill_id, preview_id=preview.preview_id if preview else None, blocked_reasons=blocked, trace_id=trace.trace_id)
            self._persist(result)
            self.events.emit("skill_dry_run_blocked", "Dry-run de skill bloqueado.", result.model_dump())
            return result
        simulated_output = {"summary": f"Dry-run concluido para {request.skill_id}; nenhuma acao real foi executada.", "mode": "dry_run"}
        validation = self.output_validator.validate(request.skill_id, simulated_output)
        trace = self.trace.create(
            skill_id=request.skill_id,
            operation="dry_run",
            status="completed" if validation.accepted else "blocked",
            steps=[SkillTraceStep(stage="skill_dry_run", decision="simulated", reason="all_steps_simulated_without_tool_execution", details={"output_valid": validation.accepted})],
        )
        result = SkillDryRunResult(
            status="completed" if validation.accepted else "blocked",
            skill_id=request.skill_id,
            preview_id=preview.preview_id,
            simulated_tool_calls=[{"tool_id": tool_id, "status": "not_executed"} for tool_id in (preview.envelope.allowed_tools if preview.envelope else [])],
            simulated_output=validation.sanitized_output,
            output_valid=validation.accepted,
            blocked_reasons=validation.violations,
            side_effects_performed=False,
            safe_to_execute=False,
            trace_id=trace.trace_id,
        )
        self._persist(result)
        self.events.emit("skill_dry_run_completed", "Dry-run de skill concluido sem efeitos colaterais.", result.model_dump())
        return result

    def _persist(self, result: SkillDryRunResult) -> None:
        path = PATHS.project_root / "data" / "runtime" / "skills" / "dry_runs" / f"{result.dry_run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=True), encoding="utf-8")


class SkillComposerService:
    def __init__(self, registry: SkillRegistryService | None = None) -> None:
        self.registry = registry or SkillRegistryService()

    def compose(self, skill_ids: list[str]) -> SkillCompositionResult:
        blocked: list[str] = []
        contracts: list[SkillContract] = []
        for skill_id in skill_ids:
            contract = self.registry.get(skill_id)
            if contract is None:
                blocked.append(f"unknown_skill:{skill_id}")
            elif contract.status not in ACTIVE_PREVIEW_STATUSES:
                blocked.append(f"skill_disabled:{skill_id}")
            elif contract.risk_level == "critical":
                blocked.append(f"critical_skill_disabled:{skill_id}")
            else:
                contracts.append(contract)
        plan = SkillCompositionPlan(
            status="blocked" if blocked else "preview",
            skill_ids=[contract.skill_id for contract in contracts],
            steps=[{"index": index, "skill_id": contract.skill_id, "mode": "preview_only"} for index, contract in enumerate(contracts, 1)],
            approval_required=any(contract.approval_required for contract in contracts),
            real_execution_allowed=False,
            blocked_reasons=blocked,
        )
        return SkillCompositionResult(status=plan.status, plan=plan, execution_started=False)


class SkillRuntimeService:
    def __init__(self) -> None:
        self.registry = SkillRegistryService()
        self.preview_service = SkillPreviewService(self.registry)
        self.dry_run_service = SkillDryRunService(self.preview_service)

    def status(self) -> dict[str, Any]:
        return self.registry.status() | {
            "policy_owner": "policy_kernel",
            "context_owner": "context_kernel",
            "tool_permission_owner": "tool_policy",
            "output_validation_owner": "skill_output_validator",
            "model_selection_owner": "role_model_gate",
            "final_status_owner": "task_runtime",
        }

    def execute(self, skill_id: str) -> SkillExecutionResult:
        SkillEventEmitter().emit("skill_execution_blocked", "Execucao real de skill esta desabilitada.", {"skill_id": skill_id})
        return SkillExecutionResult(skill_id=skill_id)


class SkillManifestValidator:
    def validate(self, request: SkillInstallRequest) -> dict[str, Any]:
        reasons: list[str] = []
        if not request.manifest:
            reasons.append("manifest_required")
        if request.dependencies:
            reasons.append("dependency_install_blocked")
        if request.source_uri:
            reasons.append("external_download_blocked")
        validation = SkillContractValidator().validate(request.contract)
        reasons.extend(validation.get("reasons", []))
        return {"status": "accepted" if not reasons else "blocked", "valid": not reasons, "reasons": reasons, "skill_id": request.contract.get("skill_id")}


class SkillDependencyPolicyService:
    def evaluate(self, dependencies: list[str]) -> dict[str, Any]:
        return {"status": "allowed" if not dependencies else "blocked", "dependencies": dependencies, "install_performed": False}


class SkillInstallPreviewService:
    def __init__(self) -> None:
        self.validator = SkillManifestValidator()
        self.events = SkillEventEmitter()

    def preview(self, request: SkillInstallRequest) -> SkillInstallPreview:
        validation = self.validator.validate(request)
        preview = SkillInstallPreview(
            status="preview" if validation["valid"] else "blocked",
            skill_id=validation.get("skill_id"),
            contract_valid=bool(validation["valid"]),
            approval_required=True,
            files_written=False,
            dependencies_installed=False,
            blocked_reasons=validation["reasons"],
        )
        path = PATHS.project_root / "data" / "runtime" / "skills" / "install_previews" / f"{preview.install_preview_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(preview.model_dump(), indent=2, ensure_ascii=True), encoding="utf-8")
        self.events.emit("skill_install_preview_created" if validation["valid"] else "skill_install_blocked", "Preview de instalacao criado; nenhum arquivo instalado." if validation["valid"] else "Preview de instalacao bloqueado.", preview.model_dump(), source_service="skill_installer")
        return preview


class SkillInstallerService:
    def preview(self, request: SkillInstallRequest) -> SkillInstallResult:
        return SkillInstallResult(preview=SkillInstallPreviewService().preview(request), installed=False)


class SkillCreatorService:
    def create_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "draft", "contract": payload, "persisted": False, "installed": False, "requires_validation": True}
