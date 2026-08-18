from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.execution_plan import CandidatePlan, CanonicalExecutionStep
from aipinho.schemas.runtime.planner_v2 import ExecutionPlan, ExecutionPlanTrace, ExecutionStage
from aipinho.schemas.runtime.runtime_contracts_v2 import RuntimeContractBundle
from aipinho.services.runtime.execution_plan_promotion_service import ExecutionPlanPromotionService
from aipinho.services.runtime.runtime_contracts_v2_service import RuntimeContractValidator
from aipinho.utils.yaml_loader import load_yaml_file


class ExecutionStageBuilder:
    def build(self, bundle: RuntimeContractBundle) -> list[ExecutionStage]:
        stages: list[ExecutionStage] = [
            ExecutionStage(stage_id="stage_01_validate_contracts", stage_type="validate_contracts"),
        ]
        previous = stages[-1].stage_id
        if bundle.approval.approval_required:
            stages.append(ExecutionStage(stage_id="stage_02_wait_approval", stage_type="approval", depends_on=[previous], metadata={"permissions": bundle.approval.permissions_requested}))
            previous = stages[-1].stage_id
        stages.append(ExecutionStage(stage_id="stage_03_execute", stage_type=bundle.execution.operation_type, roles=bundle.role.required_roles, depends_on=[previous], metadata={"contract_type": bundle.execution.contract_type, "requested_actions": bundle.execution.requested_actions}))
        previous = stages[-1].stage_id
        if bundle.artifact.expected_outputs:
            stages.append(ExecutionStage(stage_id="stage_04_artifacts", stage_type="artifacts", depends_on=[previous], metadata={"expected_outputs": bundle.artifact.expected_outputs}))
            previous = stages[-1].stage_id
        stages.append(ExecutionStage(stage_id="stage_05_validation", stage_type="validation", depends_on=[previous], metadata={"checks": bundle.validation.required_checks}))
        return stages


class ExecutionPlanValidator:
    def __init__(self, contract_validator: RuntimeContractValidator | None = None) -> None:
        self.contract_validator = contract_validator or RuntimeContractValidator()

    def validate_contracts(self, bundle: RuntimeContractBundle) -> list[str]:
        return list(self.contract_validator.validate(bundle).errors)

    def validate_plan(self, plan: ExecutionPlan) -> list[str]:
        errors: list[str] = []
        if not plan.stages:
            errors.append("execution_plan_has_no_stages")
        stage_ids = {stage.stage_id for stage in plan.stages}
        for stage in plan.stages:
            for dep in stage.depends_on:
                if dep not in stage_ids:
                    errors.append(f"missing_dependency:{dep}")
        return errors


class ExecutionPlanBuilder:
    def __init__(self, stage_builder: ExecutionStageBuilder | None = None, validator: ExecutionPlanValidator | None = None) -> None:
        self.stage_builder = stage_builder or ExecutionStageBuilder()
        self.validator = validator or ExecutionPlanValidator()
        self.promotion = ExecutionPlanPromotionService()

    def build(self, bundle: RuntimeContractBundle) -> ExecutionPlan:
        contract_errors = self.validator.validate_contracts(bundle)
        if contract_errors:
            return ExecutionPlan(status="blocked", contract_bundle_id=bundle.bundle_id, blocked_reasons=contract_errors, trace=[ExecutionPlanTrace(stage="contract_validation", status="blocked")])
        plan = ExecutionPlan(
            contract_bundle_id=bundle.bundle_id,
            stages=self.stage_builder.build(bundle),
            approvals_required=bundle.approval.permissions_requested if bundle.approval.approval_required else [],
            artifacts_expected=list(bundle.artifact.expected_outputs),
            validations_required=list(bundle.validation.required_checks),
            trace=[ExecutionPlanTrace(stage="execution_plan_builder", status="planned")],
        )
        candidate = self._candidate_from_bundle(bundle, plan)
        promotion = self.promotion.promote(
            candidate,
            policy_snapshot={
                "approval_required_for": bundle.approval.permissions_requested if bundle.approval.approval_required else [],
                "denied_actions": [],
                "contract_bundle_id": bundle.bundle_id,
            },
        )
        plan.candidate_plan = candidate
        plan.canonical_execution_plan = promotion.execution_plan
        plan_errors = self.validator.validate_plan(plan)
        plan_errors.extend(promotion.reason_codes)
        if plan_errors:
            plan.status = "blocked"
            plan.blocked_reasons.extend(plan_errors)
        return plan

    def _candidate_from_bundle(self, bundle: RuntimeContractBundle, plan: ExecutionPlan) -> CandidatePlan:
        steps = [
            CanonicalExecutionStep(
                step_id=stage.stage_id,
                step_type=stage.stage_type,
                action=str(stage.metadata.get("requested_actions", [stage.stage_type])[0] if isinstance(stage.metadata.get("requested_actions"), list) and stage.metadata.get("requested_actions") else stage.stage_type),
                required=stage.required,
                side_effect=bool(set(stage.metadata.get("requested_actions", []) or []).intersection(ExecutionPlanPromotionService.SIDE_EFFECT_ACTIONS)),
                depends_on=list(stage.depends_on),
                expected_outputs=list(bundle.artifact.expected_outputs),
                required_capabilities=list(bundle.role.required_capabilities),
                metadata=dict(stage.metadata),
            )
            for stage in plan.stages
        ]
        return CandidatePlan(
            semantic_goal=str(bundle.execution.metadata.get("semantic_goal") or bundle.execution.operation_type),
            operation_kind=bundle.execution.operation_type,
            workspace={
                "workspace_refs": list(bundle.workspace.workspace_refs),
                "scope": bundle.workspace.scope,
            },
            targets=list(bundle.workspace.target_paths or bundle.workspace.workspace_refs),
            dependencies=[{"type": "contract_bundle", "id": bundle.bundle_id}],
            requested_actions=list(bundle.execution.requested_actions),
            required_capabilities=list(bundle.role.required_capabilities),
            execution_steps=steps,
            rollback_strategy={"required": bool(set(bundle.execution.requested_actions).intersection(ExecutionPlanPromotionService.SIDE_EFFECT_ACTIONS))},
            validation_requirements=list(bundle.validation.required_checks),
            artifact_expectations=list(bundle.artifact.expected_outputs),
            source_ref=bundle.bundle_id,
            metadata={"contract_type": bundle.execution.contract_type, "runtime_profile": bundle.execution.runtime_profile},
        )


class PlannerV2:
    def __init__(self, config_path: Path | None = None, builder: ExecutionPlanBuilder | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "planner_v2.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.builder = builder or ExecutionPlanBuilder()

    def enabled(self) -> bool:
        raw = self.config.get("planner_v2", {}) if isinstance(self.config.get("planner_v2", {}), dict) else {}
        return bool(raw.get("enabled", False))

    def plan(self, bundle: RuntimeContractBundle) -> ExecutionPlan:
        return self.builder.build(bundle)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "planner_v2", "enabled": self.enabled()}
