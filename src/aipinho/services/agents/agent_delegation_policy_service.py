from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentProfile
from aipinho.schemas.agents.delegation import DelegationPolicyDecision, DelegationRequest
from aipinho.services.policy_kernel.capability_gate_service import CapabilityRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


RISK_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}

DEFAULT_START_CAPABILITIES = {
    "read_workspace",
    "scan_workspace",
    "search_workspace",
    "report_generate",
    "validation",
}

DEFAULT_FUTURE_CAPABILITIES = {
    "workspace_write",
    "write_workspace",
    "create_file",
    "modify_file",
    "create_directory",
    "shell",
    "run_approved_shell",
    "run_shell_build",
    "run_shell_test",
    "build",
    "test",
    "run_tests",
    "artifact_create",
    "create_artifact",
    "report_generate",
    "patch_preview",
    "patch_apply",
}


class AgentDelegationPolicyService:
    def __init__(self, path: Path | None = None, *, root: Path | None = None) -> None:
        self.root = root or PATHS.config_root
        self.path = path or self.root / "agents" / "delegation_policy.yaml"
        self.capability_registry = self._capability_registry()

    def evaluate(
        self,
        request: DelegationRequest,
        *,
        parent_profile: AgentProfile | None,
        target_profile: AgentProfile | None,
        cycle_detected: bool = False,
        depth: int = 0,
        child_count: int = 0,
    ) -> DelegationPolicyDecision:
        config = self._config()
        defaults = config.get("defaults", {})
        max_depth = int(defaults.get("max_depth", 3))
        max_children = int(defaults.get("max_child_runs_per_parent", 10))

        if parent_profile is None:
            return self._decision(request, "deny", "parent_agent_not_allowed", "Agente origem nao encontrado ou nao autorizado.")
        if target_profile is None:
            return self._decision(request, "deny", "target_agent_not_found", "Agente destino nao encontrado.")
        if not target_profile.enabled:
            return self._decision(request, "deny", "target_agent_disabled", "Agente destino esta desabilitado.")
        if cycle_detected and bool(defaults.get("enable_cycle_detection", True)):
            return self._decision(request, "deny", "delegation_cycle_detected", "Delegacao circular detectada.")
        if depth >= max_depth:
            return self._decision(request, "deny", "delegation_depth_exceeded", "Profundidade maxima de delegacao excedida.")
        if child_count >= max_children:
            return self._decision(request, "deny", "delegation_depth_exceeded", "Limite de child runs por parent excedido.")

        route = self._route(config, request.parent_agent_id, request.target_agent_id)
        if route is None or not bool(route.get("enabled", False)):
            return self._decision(request, "deny", "parent_agent_not_allowed", "Esta rota de delegacao nao esta habilitada pela policy.")

        allowed_modes = set(route.get("execution_modes", defaults.get("execution_modes", [])))
        if allowed_modes and request.execution_mode not in allowed_modes:
            return self._decision(request, "deny", "delegation_policy_denied", "Modo de execucao nao permitido para esta delegacao.")

        operations = set(str(item) for item in route.get("operations", []))
        if operations and request.requested_operation not in operations and request.operation_type not in operations:
            return self._decision(request, "deny", "target_agent_missing_capability", "Agente destino nao declara esta operacao delegada.")

        allowed_caps = self._canonical_capabilities(route.get("capabilities", []))
        target_caps = self._canonical_capabilities(target_profile.capabilities)
        requested_caps = self._canonical_capabilities(request.capabilities_requested)
        capability_metadata = self._capability_metadata(
            request=request,
            route=route,
            target_profile=target_profile,
            allowed_caps=allowed_caps,
            target_caps=target_caps,
            requested_caps=requested_caps,
        )
        missing = [cap for cap in requested_caps if cap not in allowed_caps and cap not in target_caps]
        if missing:
            phase_decision = self._phase_negotiation(requested_caps=requested_caps, missing=set(missing), defaults=defaults)
            capability_metadata["missing_capabilities"] = missing
            capability_metadata["phase_negotiation"] = phase_decision
            if not bool(phase_decision.get("can_start_initial_phase")):
                capability_metadata.update(
                    {
                        "whether_execution_started": False,
                        "files_changed": False,
                        "artifacts_created": [],
                    }
                )
                return self._decision(
                    request,
                    "deny",
                    "target_agent_missing_capability",
                    "Agente destino nao possui capability solicitada.",
                    capability_metadata,
                )
            capability_metadata["deferred_capabilities"] = missing

        if request.workspace_id and route.get("workspace_policy") == "deny":
            return self._decision(request, "deny", "delegation_workspace_denied", "Workspace nao permitido para esta rota de delegacao.", capability_metadata)

        risk = request.risk_level or "low"
        if RISK_ORDER.get(risk, 4) >= RISK_ORDER["critical"]:
            return self._decision(request, "deny", "delegation_risk_too_high", "Risco critico bloqueado pela policy.", capability_metadata)
        if RISK_ORDER.get(risk, 4) >= RISK_ORDER["high"]:
            return self._decision(request, "require_approval", "approval_required", "Delegacao de alto risco exige aprovacao humana.", capability_metadata)

        if bool(route.get("autoapprove", True)) and request.execution_mode in {"governed_autorun", "power_user"}:
            return self._decision(request, "auto_approve", "delegation_auto_approved", "Delegacao segura autoaprovada pela policy.", capability_metadata)
        return self._decision(request, "allow", "delegation_allowed", "Delegacao permitida pela policy.", capability_metadata)

    def timeout_seconds(self, requested: int | None) -> int:
        defaults = self._config().get("defaults", {})
        default_timeout = int(defaults.get("default_timeout_seconds", 900))
        max_timeout = int(defaults.get("max_timeout_seconds", 1800))
        value = requested if requested is not None else default_timeout
        return max(1, min(int(value), max_timeout))

    def _config(self) -> dict[str, Any]:
        data = load_yaml_file(self.path, critical=False, root=self.root)
        if not data:
            return {
                "defaults": {
                    "max_depth": 3,
                    "max_child_runs_per_parent": 10,
                    "default_timeout_seconds": 900,
                    "max_timeout_seconds": 1800,
                    "enable_cycle_detection": True,
                    "execution_modes": ["safe_chat", "assisted_execution", "governed_autorun", "power_user"],
                },
                "routes": [],
            }
        return data

    def _capability_registry(self) -> CapabilityRegistryService | None:
        path = self.root / "policies" / "capability_registry.yaml"
        if not path.exists():
            return None
        try:
            return CapabilityRegistryService(path).load()
        except Exception:
            return None

    def _canonical_capabilities(self, capabilities: Any) -> set[str]:
        values = [str(item) for item in (capabilities or [])]
        if self.capability_registry is None:
            return {item for item in values if item}
        return set(self.capability_registry.canonicalize_all(values))

    def _canonical_capability_map(self, capabilities: Any) -> dict[str, str]:
        values = [str(item) for item in (capabilities or []) if str(item).strip()]
        if self.capability_registry is None:
            return {item: item for item in values}
        return {item: self.capability_registry.canonicalize(item) for item in values}

    def _capability_metadata(
        self,
        *,
        request: DelegationRequest,
        route: dict[str, Any],
        target_profile: AgentProfile,
        allowed_caps: set[str],
        target_caps: set[str],
        requested_caps: set[str],
    ) -> dict[str, Any]:
        requested_map = self._canonical_capability_map(request.capabilities_requested)
        target_map = self._canonical_capability_map(target_profile.capabilities)
        route_map = self._canonical_capability_map(route.get("capabilities", []))
        return {
            "requested_capabilities": list(request.capabilities_requested),
            "requested_capabilities_canonical": sorted(requested_caps),
            "target_agent_declared_capabilities": list(target_profile.capabilities),
            "target_agent_declared_capabilities_canonical": sorted(target_caps),
            "route_allowed_capabilities": list(route.get("capabilities", [])),
            "route_allowed_capabilities_canonical": sorted(allowed_caps),
            "matched_aliases": {
                raw: canonical
                for raw, canonical in requested_map.items()
                if raw != canonical or canonical in target_caps or canonical in allowed_caps
            },
            "target_matched_aliases": {raw: canonical for raw, canonical in target_map.items() if raw != canonical},
            "route_matched_aliases": {raw: canonical for raw, canonical in route_map.items() if raw != canonical},
            "workspace_policy_decision": route.get("workspace_policy", "unknown"),
        }

    def _phase_negotiation(self, *, requested_caps: set[str], missing: set[str], defaults: dict[str, Any]) -> dict[str, Any]:
        config = defaults.get("phase_capability_negotiation", {})
        enabled = bool(config.get("enabled", True))
        start_capabilities = self._canonical_capabilities(config.get("start_capabilities", DEFAULT_START_CAPABILITIES))
        future_capabilities = self._canonical_capabilities(config.get("future_capabilities", DEFAULT_FUTURE_CAPABILITIES))
        start_caps_present = sorted(requested_caps & start_capabilities)
        future_missing = sorted(missing & future_capabilities)
        blocking_missing = sorted(missing - future_capabilities)
        can_start = enabled and bool(start_caps_present) and not blocking_missing
        return {
            "enabled": enabled,
            "can_start_initial_phase": can_start,
            "initial_phase_capabilities": start_caps_present,
            "future_phase_missing_capabilities": future_missing,
            "blocking_missing_capabilities": blocking_missing,
        }

    def _route(self, config: dict[str, Any], parent: str, target: str) -> dict[str, Any] | None:
        for route in config.get("routes", []):
            if not isinstance(route, dict):
                continue
            if route.get("parent_agent_id") == parent and route.get("target_agent_id") == target:
                return route
        return None

    def _decision(self, request: DelegationRequest, decision: str, reason_code: str, human_reason: str, extra: dict[str, Any] | None = None) -> DelegationPolicyDecision:
        auto_id = f"auto_approval_{uuid4().hex}" if decision == "auto_approve" else None
        return DelegationPolicyDecision(
            delegation_id=request.delegation_id,
            parent_agent_id=request.parent_agent_id,
            target_agent_id=request.target_agent_id,
            requested_operation=request.requested_operation,
            capabilities_requested=request.capabilities_requested,
            workspace_id=request.workspace_id,
            risk_level=request.risk_level,
            execution_mode=request.execution_mode,
            decision=decision,  # type: ignore[arg-type]
            reason_code=reason_code,
            human_reason=human_reason,
            technical_reason_sanitized=reason_code,
            auto_approval_id=auto_id,
            approval_required=decision == "require_approval",
            safe_alternative="Retornar ao agente pai com resumo e pedir decisao do usuario." if decision == "deny" else None,
            evidence_refs=[f"delegation:{request.delegation_id}", f"policy:{reason_code}", *(f"{key}:{value}" for key, value in (extra or {}).items())],
            metadata_sanitized=extra or {},
        )
