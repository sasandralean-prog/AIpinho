from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.runtime_contracts_v2 import RuntimeContractBundle
from aipinho.schemas.runtime.runtime_dispatcher_v2 import DispatchDecision, DispatchRoute, DispatchTrace
from aipinho.services.roles.role_contract_service import RoleContractService
from aipinho.services.runtime.runtime_contracts_v2_service import RuntimeContractValidator
from aipinho.utils.yaml_loader import load_yaml_file


class DispatchValidator:
    def __init__(self, contract_validator: RuntimeContractValidator | None = None) -> None:
        self.contract_validator = contract_validator or RuntimeContractValidator()

    def validate(self, bundle: RuntimeContractBundle) -> list[str]:
        result = self.contract_validator.validate(bundle)
        return list(result.errors)


class RoleSelectionResolver:
    def __init__(self, roles: RoleContractService | None = None) -> None:
        self.roles = roles or RoleContractService()

    def resolve(self, bundle: RuntimeContractBundle) -> tuple[list[str], list[str]]:
        selected: list[str] = []
        blocked: list[str] = []
        for role_id in bundle.role.required_roles:
            contract = self.roles.get_contract(role_id)
            if contract is None:
                blocked.append(f"role_contract_missing:{role_id}")
                continue
            if contract.lifecycle.status != "enabled":
                blocked.append(f"role_disabled:{role_id}")
                continue
            selected.append(role_id)
        return selected, blocked


class ExecutionRouteResolver:
    def resolve(self, bundle: RuntimeContractBundle, roles: list[str]) -> DispatchRoute:
        return DispatchRoute(
            operation_type=bundle.execution.operation_type,
            contract_type=bundle.execution.contract_type,
            roles=roles,
            approvals_required=bundle.approval.permissions_requested if bundle.approval.approval_required else [],
            artifacts_expected=list(bundle.artifact.expected_outputs),
            validations_required=list(bundle.validation.required_checks),
        )


class RuntimeDispatcherV2:
    def __init__(self, config_path: Path | None = None, validator: DispatchValidator | None = None, roles: RoleSelectionResolver | None = None, routes: ExecutionRouteResolver | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "runtime_dispatcher_v2.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.validator = validator or DispatchValidator()
        self.roles = roles or RoleSelectionResolver()
        self.routes = routes or ExecutionRouteResolver()

    def enabled(self) -> bool:
        raw = self.config.get("runtime_dispatcher_v2", {}) if isinstance(self.config.get("runtime_dispatcher_v2", {}), dict) else {}
        return bool(raw.get("enabled", False))

    def dispatch(self, bundle: RuntimeContractBundle) -> DispatchDecision:
        trace: list[DispatchTrace] = [DispatchTrace(stage="dispatch_start", status="ready")]
        errors = self.validator.validate(bundle)
        if errors:
            return DispatchDecision(status="blocked", blocked_reasons=errors, trace=[*trace, DispatchTrace(stage="contract_validation", status="blocked", reason=";".join(errors))])
        selected_roles, role_blocks = self.roles.resolve(bundle)
        if role_blocks:
            return DispatchDecision(status="blocked", blocked_reasons=role_blocks, trace=[*trace, DispatchTrace(stage="role_selection", status="blocked", reason=";".join(role_blocks))])
        route = self.routes.resolve(bundle, selected_roles)
        return DispatchDecision(status="ready", route=route, trace=[*trace, DispatchTrace(stage="route_resolved", status="ready", data=route.model_dump(mode="json"))])

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "runtime_dispatcher_v2", "enabled": self.enabled()}
