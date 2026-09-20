from __future__ import annotations

import hashlib
import os
import re
from typing import Any
from uuid import uuid4
from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.mission_continuation import (
    MissionContinuationCandidate,
    MissionContinuationPlanningResult,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.phase_semantic_demand_compiler import (
    PhaseSemanticDemandCompiler,
)
from aipinho.services.runtime.task_run_trace_service import TaskRunTraceService
from aipinho.services.runtime.runtime_profile_service import RuntimeProfileService
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)
from aipinho.services.runtime.execution_plan_promotion_service import ExecutionPlanPromotionService
from aipinho.services.runtime.phase_identity_service import PhaseIdentityService
from aipinho.services.config_governance.workspace_permission_matrix_service import (
    WorkspacePermissionMatrixService,
)
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.utils.yaml_loader import load_yaml_file

class TaskRunPlanner:
    def __init__(
        self,
        *,
        semantic_reasoner: ContractBoundSemanticReasoner | None = None,
        phase_demands: PhaseSemanticDemandCompiler | None = None,
        permission_matrix: WorkspacePermissionMatrixService | None = None,
        phases: PhaseIdentityService | None = None,
    ) -> None:
        self.runtime = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_policy.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.steps = load_yaml_file(PATHS.config_root / "runtime" / "governed_task_steps.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.profiles = RuntimeProfileService().load()
        self.actions = ActionRegistryService().load()
        self.limits = load_yaml_file(PATHS.config_root / "runtime" / "task_runtime_limits.yaml", critical=True, root=PATHS.config_root / "runtime")
        self.trace = TaskRunTraceService()
        self.execution_plans = ExecutionPlanPromotionService()
        self.semantic_reasoner = semantic_reasoner
        self.phase_demands = phase_demands or PhaseSemanticDemandCompiler()
        self.permission_matrix = permission_matrix or WorkspacePermissionMatrixService()
        self.phases = phases or PhaseIdentityService()

    def plan(self, request: TaskRunRequest) -> TaskRunPlan:
        allowed_contracts = set(self.runtime.get("allowed_contract_types", []) or [])
        allowed_actions = set(self.runtime.get("allowed_actions", []) or [])
        blocked_actions = set(self.runtime.get("blocked_actions", []) or [])
        reasons: list[str] = []
        if request.contract_type not in allowed_contracts: reasons.append("unsupported_contract_type")
        normalized_actions = [
            self.actions.normalize_action(action) if self.actions.action_exists(action) else action
            for action in request.requested_actions
        ]
        for action in normalized_actions:
            if action in blocked_actions: reasons.append(f"blocked_action:{action}")
            elif action not in allowed_actions: reasons.append(f"unknown_runtime_action:{action}")
        profile = self.profiles.resolve(
            operation_type=request.operation_type,
            contract_type=request.contract_type,
            requested_profile=request.runtime_profile,
        )
        if profile is None:
            reasons.append("runtime_profile_missing")
            profile = {}
        step_ids = list(profile.get("steps", []) or []) if not reasons else []
        max_steps = int(self.limits.get("limits", {}).get("max_steps_per_run", 20))
        if not step_ids: reasons.append("runtime_pipeline_missing")
        if len(step_ids) > max_steps: reasons.append("runtime_step_limit_exceeded")
        built: list[TaskRunStep] = []
        definitions = self.steps.get("step_types", {}) if isinstance(self.steps.get("step_types", {}), dict) else {}
        profile_actions = {
            str((definitions.get(step_id) or {}).get("action"))
            for step_id in step_ids
            if isinstance(definitions.get(step_id), dict)
        }
        profile_actions.update(str(action) for action in profile.get("allowed_actions", []) or [])
        for action in normalized_actions:
            if profile_actions and action not in profile_actions:
                reasons.append(f"action_not_allowed_by_profile:{action}")
        for index, step_type in enumerate(step_ids):
            definition = definitions.get(step_type)
            if not isinstance(definition, dict) or not definition.get("enabled", False):
                reasons.append(f"unknown_or_disabled_step:{step_type}")
                continue
            action = str(definition.get("action", ""))
            side_effect = bool(definition.get("side_effect", False))
            if action not in allowed_actions:
                reasons.append(f"action_not_allowed:{action}")
                continue
            if side_effect and not profile.get("allowed_side_effects"):
                reasons.append(f"profile_side_effect_not_allowed:{step_type}")
                continue
            built.append(TaskRunStep(step_id=f"step_{index+1:02d}_{step_type}", step_type=step_type, action=action, required=bool(definition.get("required", True)), side_effect=side_effect))
        status = "blocked" if reasons else "ready"
        task_plan = TaskRunPlan(
            plan_id=f"task_run_plan_{uuid4().hex}",
            contract_type=request.contract_type,
            status=status,
            steps=built,
            blocked_reasons=list(dict.fromkeys(reasons)),
            trace=[self.trace.item("task_run_planner", status, "plan_built_from_runtime_profile", source=f"config/runtime/profiles/{profile.get('id', 'missing')}.yaml", data={"steps": len(built), "profile": profile.get("id")})],
            metadata={
                "runtime_profile": profile.get("id"),
                "required_capabilities": list(profile.get("required_capabilities", []) or []),
                "approval_scope": profile.get("approval_scope"),
                "output_validation_required": bool(profile.get("output_validation_required", False)),
                "artifact_registration_required": bool(profile.get("artifact_registration_required", False)),
                "normalized_actions": normalized_actions,
                "workspace_requirements": dict(profile.get("workspace_requirements", {}) or {}),
            },
        )
        candidate = self.execution_plans.candidate_from_task_run_plan(
            request=request,
            plan=task_plan,
            workspace_context={"workspace_path": request.workspace} if request.workspace else {},
        )
        promotion = self.execution_plans.promote(
            candidate,
            policy_snapshot=request.policy_decision,
            task_id=request.task_id,
            taskrun_id=request.task_run_id,
            approval_id=request.approval_id,
        )
        task_plan.candidate_plan = candidate
        task_plan.canonical_execution_plan = promotion.execution_plan
        task_plan.metadata["candidate_plan_id"] = candidate.candidate_plan_id
        if promotion.execution_plan is not None:
            task_plan.metadata["execution_id"] = promotion.execution_plan.execution_id
            task_plan.metadata["canonical_execution_plan"] = promotion.execution_plan.model_dump(mode="json")
        if promotion.reason_codes:
            task_plan.status = "blocked"
            task_plan.blocked_reasons = list(dict.fromkeys([*task_plan.blocked_reasons, *promotion.reason_codes]))
        task_plan.trace.append(
            self.trace.item(
                "execution_plan_promotion",
                promotion.status,
                "candidate_plan_promoted_by_effective_policy",
                source="services/runtime/execution_plan_promotion_service.py",
                data={
                    "candidate_plan_id": candidate.candidate_plan_id,
                    "execution_id": promotion.execution_plan.execution_id if promotion.execution_plan else None,
                    "reason_codes": promotion.reason_codes,
                },
            )
        )
        return task_plan

    def plan_continuation(
        self,
        *,
        run: Any,
        phase_outcome: Any | None = None,
    ) -> MissionContinuationPlanningResult:
        contract = getattr(run, "mission_contract", None)
        if contract is None:
            return self._continuation_result(
                "blocked",
                "MISSION_CONTINUATION_MISSION_CONTRACT_REQUIRED",
            )
        if str(contract.strategy) != "end_to_end_governed":
            return self._continuation_result(
                "not_applicable",
                "MISSION_CONTINUATION_STRATEGY_BOUNDARY",
            )

        continuation = (
            run.intent_map.get("mission_continuation")
            if isinstance(getattr(run, "intent_map", None), dict)
            and isinstance(run.intent_map.get("mission_continuation"), dict)
            else {}
        )
        depth = self._non_negative_int(continuation.get("depth"))
        max_depth = int(
            (self.limits.get("limits", {}) or {}).get(
                "max_mission_continuation_depth",
                12,
            )
        )
        if depth >= max_depth:
            return self._continuation_result(
                "blocked",
                "MISSION_CONTINUATION_DEPTH_LIMIT_REACHED",
                provenance={"depth": depth, "max_depth": max_depth},
            )

        semantic_context = dict(getattr(contract, "semantic_context", {}) or {})
        semantic_graph = (
            dict(semantic_context.get("semantic_intent_graph") or {})
            if isinstance(semantic_context.get("semantic_intent_graph"), dict)
            else dict(run.intent_map.get("semantic_intent_graph") or {})
            if isinstance(getattr(run, "intent_map", None), dict)
            and isinstance(run.intent_map.get("semantic_intent_graph"), dict)
            else {}
        )
        if (
            not semantic_graph
            and not contract.completion.completion_requirements
            and not contract.completion.validation_requirements
        ):
            return self._continuation_result(
                "blocked",
                "MISSION_CONTINUATION_STRUCTURED_SEMANTICS_REQUIRED",
                provenance={"depth": depth, "max_depth": max_depth},
            )
        current_phase = self.phases.from_run(run) or ""
        phase_lineage = self._unique(
            [
                *list(continuation.get("phase_lineage") or []),
                *([current_phase] if current_phase else []),
            ]
        )
        unsatisfied_effects = self._unsatisfied_requested_effects(
            run=run,
            semantic_graph=semantic_graph,
            continuation=continuation,
            semantic_context=semantic_context,
        )
        reasoner = self.semantic_reasoner or ContractBoundSemanticReasoner()
        continuation_options = self._continuation_option_catalog(run)
        continuation_option_map = {
            str(item["option_id"]): item
            for item in continuation_options
        }
        continuation_goal = (
            "Select the next bounded mission work unit, or declare the mission "
            "complete only when the frozen mission semantics and terminal evidence "
            "support completion."
        )
        continuation_payload = {
            "mission": {
                "mission_id": contract.mission_id,
                "strategy": contract.strategy,
                "source_prompt_sha256": contract.source_prompt_sha256,
                "semantic_context": {
                    key: value
                    for key, value in semantic_context.items()
                    if key != "semantic_intent_graph"
                },
                "requested_capabilities": list(
                    contract.authority.requested_capabilities
                ),
                "authorized_capabilities": list(
                    contract.authority.authorized_capabilities
                ),
                "completion_requirements": list(
                    contract.completion.completion_requirements
                ),
                "validation_requirements": list(
                    contract.completion.validation_requirements
                ),
            },
            "current": {
                "phase_id": current_phase,
                "operation_type": getattr(run, "operation_type", None),
                "contract_type": getattr(run, "contract_type", None),
                "runtime_profile": getattr(run, "runtime_profile", None),
                "requested_actions": list(
                    getattr(run, "requested_actions", []) or []
                ),
                "depth": depth,
                "phase_lineage": phase_lineage,
            },
            "terminal_outcome": self._continuation_outcome_payload(
                phase_outcome
            ),
            "semantic_intent_graph": semantic_graph,
            "unsatisfied_requested_effects": unsatisfied_effects,
            "continuation_options": continuation_options,
            "allowed_contract_types": list(
                self.runtime.get(
                    "allowed_contract_types",
                    [],
                )
                or []
            ),
            "rules": [
                "Select exactly one option_id from continuation_options; runtime_profile and operation_type are materialized by the runtime.",
                "requested_actions must be a subset of the selected continuation option allowed_actions.",
                "Use contract_type from the selected option default_contract_types when that list is non-empty; otherwise use allowed_contract_types.",
                "Do not expand capabilities, resources or authority.",
                "Phase identity is assigned deterministically by the runtime; do not infer or authorize it.",
                "Do not use raw prompt text or infer permissions.",
                "Return complete only when unsatisfied_requested_effects is empty.",
                "Candidate is descriptive only; policy and execution authority are external.",
            ],
            "output_schema": {
                "action": "continue|complete",
                "candidate": {
                    "option_id": "continuation_option_id",
                    "contract_type": "runtime_contract_type",
                    "requested_actions": ["option_allowed_action"],
                },
                "confidence": "number_between_0_and_1",
                "rationale": "non_empty_string",
            },
        }
        candidate_retry_limit = max(
            0,
            int(
                (self.limits.get("limits", {}) or {}).get(
                    "max_mission_continuation_candidate_retries",
                    0,
                )
                or 0
            ),
        )
        candidate_retries = 0
        candidate_rejections: list[str] = []
        correction: dict[str, Any] | None = None

        while True:
            proposal_payload = dict(continuation_payload)
            if correction is not None:
                proposal_payload["candidate_correction"] = correction
            proposal = reasoner.propose_json(
                semantic_goal=continuation_goal,
                payload=proposal_payload,
                allowed_fields=[
                    "action",
                    "candidate",
                    "confidence",
                    "rationale",
                ],
                required_fields=[
                    "action",
                    "candidate",
                    "confidence",
                    "rationale",
                ],
                role_id="semantic_interpreter",
                max_tokens=650,
            )
            provenance = {
                "model_id": proposal.get("model_id"),
                "response_id": proposal.get("response_id"),
                "real_inference": proposal.get("real_inference"),
                "evaluation_status": proposal.get("evaluation_status"),
                "warnings": list(proposal.get("warnings") or []),
                "depth": depth,
                "max_depth": max_depth,
                "candidate_retries": candidate_retries,
                "candidate_rejections": list(candidate_rejections),
            }
            if proposal.get("status") != "candidate":
                return self._continuation_result(
                    "blocked",
                    str(
                        proposal.get("reason_code")
                        or "MISSION_CONTINUATION_PLANNER_MODEL_UNAVAILABLE"
                    ),
                    provenance=provenance,
                )

            model_output = dict(proposal.get("candidate") or {})
            action = str(
                model_output.get("action") or ""
            ).strip().casefold()
            candidate_payload = (
                dict(model_output.get("candidate") or {})
                if isinstance(
                    model_output.get("candidate"),
                    dict,
                )
                else {}
            )
            try:
                confidence = float(
                    model_output.get("confidence", 0.0)
                )
            except (TypeError, ValueError):
                confidence = 0.0
            rationale = str(
                model_output.get("rationale") or ""
            ).strip()
            if confidence < 0.65 or not rationale:
                return self._continuation_result(
                    "blocked",
                    "MISSION_CONTINUATION_PLANNER_CONFIDENCE_INSUFFICIENT",
                    provenance={
                        **provenance,
                        "confidence": confidence,
                    },
                )
            if action == "complete":
                if unsatisfied_effects:
                    return self._continuation_result(
                        "blocked",
                        "MISSION_CONTINUATION_PREMATURE_COMPLETE",
                        provenance={
                            **provenance,
                            "confidence": confidence,
                            "unsatisfied_requested_effects": (
                                unsatisfied_effects
                            ),
                        },
                    )
                return self._continuation_result(
                    "not_applicable",
                    "MISSION_CONTINUATION_PLANNER_COMPLETE",
                    provenance={
                        **provenance,
                        "confidence": confidence,
                    },
                )
            if action != "continue":
                return self._continuation_result(
                    "blocked",
                    "MISSION_CONTINUATION_PLANNER_ACTION_INVALID",
                    provenance={
                        **provenance,
                        "confidence": confidence,
                    },
                )

            (
                materialized_candidate,
                option_reason,
            ) = self._materialize_continuation_option(
                candidate_payload=candidate_payload,
                option_map=continuation_option_map,
            )
            if materialized_candidate is None:
                validated = None
                reason = option_reason
            else:
                candidate_payload = materialized_candidate
                candidate_payload["phase_id"] = (
                    self._continuation_phase_id(
                        depth=depth,
                        runtime_profile=str(
                            candidate_payload.get(
                                "runtime_profile",
                                "",
                            )
                        ),
                        operation_type=str(
                            candidate_payload.get(
                                "operation_type",
                                "",
                            )
                        ),
                    )
                )
                validated, reason = (
                    self._validate_continuation_candidate_payload(
                        run=run,
                        candidate_payload=candidate_payload,
                        phase_lineage=phase_lineage,
                    )
                )
            if validated is not None:
                break
            rejection_reason = (
                reason
                or "MISSION_CONTINUATION_CANDIDATE_INVALID"
            )
            candidate_rejections.append(rejection_reason)
            if candidate_retries >= candidate_retry_limit:
                return self._continuation_result(
                    "blocked",
                    rejection_reason,
                    provenance={
                        **provenance,
                        "confidence": confidence,
                        "candidate_rejections": list(
                            candidate_rejections
                        ),
                    },
                )
            candidate_retries += 1
            correction = {
                "attempt": candidate_retries,
                "reason_code": rejection_reason,
                "rejected_candidate": candidate_payload,
                "instruction": (
                    "Produce a new candidate that satisfies all supplied "
                    "catalogs, lineage constraints, capability boundaries "
                    "and deterministic rules. Do not repeat the rejected "
                    "candidate."
                ),
            }

        demand = self.phase_demands.compile_for_run(
            run=run,
            consumer_phase_id=validated["phase_id"],
            consumer_operation_type=validated["operation_type"],
        )
        if demand.status != "compiled" or demand.requirements is None:
            return self._continuation_result(
                "blocked",
                (
                    demand.reason_codes[0]
                    if demand.reason_codes
                    else "MISSION_CONTINUATION_DEPENDENCY_REQUIREMENTS_UNAVAILABLE"
                ),
                provenance={
                    **provenance,
                    "confidence": confidence,
                    "semantic_demand": demand.model_dump(mode="json"),
                },
            )

        local_ids = [item.resource_id for item in contract.local_resources]
        remote_ids = [item.resource_id for item in contract.remote_resources]
        workspace_resource_id = self._workspace_resource_id(run, contract)
        planner_ref = (
            f"task_run_planner_continuation:{run.plan.plan_id}:"
            f"{proposal.get('response_id') or validated['phase_id']}"
        )
        candidate = MissionContinuationCandidate(
            planner_ref=planner_ref,
            dependency_id=f"dependency_{run.run_id}_{validated['phase_id']}",
            phase_id=validated["phase_id"],
            operation_type=validated["operation_type"],
            contract_type=validated["contract_type"],
            runtime_profile=validated["runtime_profile"],
            requested_actions=validated["requested_actions"],
            required_capabilities=validated["required_capabilities"],
            runtime_capabilities_required=validated[
                "runtime_capabilities_required"
            ],
            local_resource_ids=local_ids,
            remote_resource_ids=remote_ids,
            workspace_resource_id=workspace_resource_id,
            mode=(
                "governed"
                if any(
                    self.actions.is_side_effect(item)
                    for item in validated["requested_actions"]
                )
                else "read_only"
            ),
            requirements=demand.requirements,
            metadata={
                "planner": "TaskRunPlanner.plan_continuation",
                "confidence": confidence,
                "rationale": rationale,
                "source_plan_id": run.plan.plan_id,
                "source_execution_id": demand.source_execution_id,
                "source_semantics_sha256": demand.source_semantics_sha256,
                "continuation_option_id": validated.get(
                    "continuation_option_id"
                ),
            },
        )
        return self._continuation_result(
            "planned",
            "MISSION_CONTINUATION_CANDIDATE_PLANNED",
            candidate=candidate,
            provenance={**provenance, "confidence": confidence},
        )

    def _materialize_continuation_option(
        self,
        *,
        candidate_payload: dict[str, Any],
        option_map: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, str | None]:
        option_id = str(
            candidate_payload.get("option_id") or ""
        ).strip()
        if not option_id:
            return (
                None,
                "MISSION_CONTINUATION_OPTION_ID_REQUIRED",
            )
        option = option_map.get(option_id)
        if option is None:
            return (
                None,
                "MISSION_CONTINUATION_OPTION_UNKNOWN",
            )

        contract_type = str(
            candidate_payload.get("contract_type") or ""
        ).strip()
        default_contract_types = {
            str(item)
            for item in list(
                option.get("default_contract_types", []) or []
            )
            if str(item)
        }
        if (
            default_contract_types
            and contract_type not in default_contract_types
        ):
            return (
                None,
                "MISSION_CONTINUATION_CONTRACT_OPTION_MISMATCH",
            )

        raw_actions = candidate_payload.get(
            "requested_actions"
        )
        if not isinstance(raw_actions, list):
            return (
                None,
                "MISSION_CONTINUATION_ACTIONS_INVALID",
            )
        try:
            requested_actions = self._unique(
                [
                    self.actions.normalize_action(str(item))
                    for item in raw_actions
                ]
            )
        except Exception:
            return (
                None,
                "MISSION_CONTINUATION_ACTION_UNKNOWN",
            )
        option_actions = {
            str(item)
            for item in list(
                option.get("allowed_actions", []) or []
            )
            if str(item)
        }
        if any(
            action not in option_actions
            for action in requested_actions
        ):
            return (
                None,
                "MISSION_CONTINUATION_ACTION_NOT_OPTION_ALLOWED",
            )

        return (
            {
                **dict(candidate_payload),
                "option_id": option_id,
                "runtime_profile": str(
                    option.get("runtime_profile") or ""
                ),
                "operation_type": str(
                    option.get("operation_type") or ""
                ),
                "requested_actions": requested_actions,
            },
            None,
        )

    @staticmethod
    def _continuation_option_id(
        *,
        runtime_profile: str,
        operation_type: str,
    ) -> str:
        raw = (
            f"{str(runtime_profile).strip()}|"
            f"{str(operation_type).strip()}"
        )
        stem = re.sub(
            r"[^a-z0-9_]+",
            "_",
            raw.casefold(),
        ).strip("_")
        if not stem:
            stem = "work"
        digest = hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:8]
        return f"option_{stem[:44]}_{digest}"

    def _continuation_phase_id(
        self,
        *,
        depth: int,
        runtime_profile: str,
        operation_type: str,
    ) -> str:
        raw_stem = (
            str(runtime_profile or "").strip()
            or str(operation_type or "").strip()
            or "work"
        )
        stem = re.sub(
            r"[^a-z0-9_]+",
            "_",
            raw_stem.casefold(),
        ).strip("_")
        if not stem:
            stem = "work"
        prefix = f"phase_{max(0, int(depth)) + 1:03d}_"
        max_stem = max(1, 63 - len(prefix))
        return f"{prefix}{stem[:max_stem]}"

    def _validate_continuation_candidate_payload(
        self,
        *,
        run: Any,
        candidate_payload: dict[str, Any],
        phase_lineage: list[str],
    ) -> tuple[dict[str, Any] | None, str | None]:
        phase_id = str(candidate_payload.get("phase_id") or "").strip()
        operation_type = str(candidate_payload.get("operation_type") or "").strip()
        contract_type = str(candidate_payload.get("contract_type") or "").strip()
        runtime_profile = str(candidate_payload.get("runtime_profile") or "").strip()
        if re.fullmatch(r"[a-z][a-z0-9_]{1,63}", phase_id) is None:
            return None, "MISSION_CONTINUATION_PHASE_ID_INVALID"
        if phase_id in set(phase_lineage):
            return None, "MISSION_CONTINUATION_PHASE_CYCLE_DETECTED"
        if contract_type not in set(self.runtime.get("allowed_contract_types", []) or []):
            return None, "MISSION_CONTINUATION_CONTRACT_TYPE_UNSUPPORTED"
        profile = self.profiles.get(runtime_profile)
        if profile is None:
            return None, "MISSION_CONTINUATION_RUNTIME_PROFILE_UNKNOWN"
        if operation_type not in set(profile.get("operation_types", []) or []):
            return None, "MISSION_CONTINUATION_OPERATION_PROFILE_MISMATCH"

        raw_actions = candidate_payload.get("requested_actions")
        if not isinstance(raw_actions, list):
            return None, "MISSION_CONTINUATION_ACTIONS_INVALID"
        try:
            requested_actions = self._unique(
                [self.actions.normalize_action(str(item)) for item in raw_actions]
            )
        except Exception:
            return None, "MISSION_CONTINUATION_ACTION_UNKNOWN"

        runtime_allowed = set(self.runtime.get("allowed_actions", []) or [])
        runtime_blocked = set(self.runtime.get("blocked_actions", []) or [])
        if any(
            action in runtime_blocked or action not in runtime_allowed
            for action in requested_actions
        ):
            return None, "MISSION_CONTINUATION_ACTION_NOT_RUNTIME_ALLOWED"

        definitions = (
            self.steps.get("step_types", {})
            if isinstance(self.steps.get("step_types"), dict)
            else {}
        )
        profile_actions = {
            str(action)
            for action in list(profile.get("allowed_actions", []) or [])
            if str(action)
        }
        for step_id in list(profile.get("steps", []) or []):
            definition = definitions.get(step_id)
            if isinstance(definition, dict) and definition.get("action"):
                profile_actions.add(str(definition["action"]))
        if any(action not in profile_actions for action in requested_actions):
            return None, "MISSION_CONTINUATION_ACTION_NOT_PROFILE_ALLOWED"

        runtime_capabilities = self._unique(
            [
                *list(profile.get("required_capabilities", []) or []),
                *[
                    capability
                    for action in requested_actions
                    for capability in [self.actions.capability_for(action)]
                    if capability
                ],
            ]
        )
        authority_permissions = self._unique(
            [
                self.permission_matrix.permission_for_action(action)
                for action in requested_actions
            ]
        )
        mission = getattr(run, "mission_contract", None)
        if mission is None:
            return None, "MISSION_CONTINUATION_MISSION_CONTRACT_REQUIRED"
        requested_authority = set(mission.authority.requested_capabilities)
        authorized_authority = set(mission.authority.authorized_capabilities)
        if not set(authority_permissions).issubset(requested_authority):
            return None, "MISSION_CONTINUATION_CAPABILITY_NOT_REQUESTED"
        if not set(authority_permissions).issubset(authorized_authority):
            return None, "MISSION_CONTINUATION_CAPABILITY_NOT_AUTHORIZED"

        return (
            {
                "phase_id": phase_id,
                "operation_type": operation_type,
                "contract_type": contract_type,
                "runtime_profile": runtime_profile,
                "requested_actions": requested_actions,
                "required_capabilities": authority_permissions,
                "runtime_capabilities_required": runtime_capabilities,
                "continuation_option_id": str(
                    candidate_payload.get("option_id") or ""
                ),
            },
            None,
        )

    def _unsatisfied_requested_effects(
        self,
        *,
        run: Any,
        semantic_graph: dict[str, Any],
        continuation: dict[str, Any],
        semantic_context: dict[str, Any],
    ) -> list[str]:
        actions: list[str] = []
        for entry in list(continuation.get("history") or []):
            if not isinstance(entry, dict):
                continue
            actions.extend(
                str(item)
                for item in list(entry.get("requested_actions") or [])
                if str(item)
            )
        actions.extend(
            str(item)
            for item in list(getattr(run, "requested_actions", []) or [])
            if str(item)
        )
        normalized_actions = [
            self.actions.normalize_action(item)
            for item in actions
            if self.actions.action_exists(item)
        ]
        categories = {
            self.actions.get_action(action).category
            for action in normalized_actions
        }
        side_effect_seen = any(
            self.actions.is_side_effect(action) for action in normalized_actions
        )
        workspace_mutation_seen = bool(
            categories.intersection({"filesystem_write", "patch", "project_write"})
        )
        runtime_execution_seen = bool(
            categories.intersection({"shell", "validation"})
        )
        requested_effects = self._unique(
            list(semantic_graph.get("requested_effects") or [])
        )
        unsatisfied: list[str] = []
        for effect in requested_effects:
            if effect == "workspace_mutation" and not workspace_mutation_seen:
                unsatisfied.append(effect)
            elif effect in {"build_execution", "runtime_execution"} and not runtime_execution_seen:
                unsatisfied.append(effect)
        if (
            bool(
                semantic_context.get(
                    "future_side_effect_intent",
                    getattr(run, "intent_map", {}).get(
                        "future_side_effect_intent",
                        False,
                    ),
                )
            )
            and not side_effect_seen
            and "workspace_mutation" not in unsatisfied
        ):
            unsatisfied.append("governed_side_effect")
        if (
            bool(semantic_graph.get("execution_intent"))
            and not runtime_execution_seen
            and not any(
                effect in {"build_execution", "runtime_execution"}
                for effect in unsatisfied
            )
        ):
            unsatisfied.append("runtime_execution")
        return self._unique(unsatisfied)

    def _continuation_option_catalog(
        self,
        run: Any,
    ) -> list[dict[str, Any]]:
        mission = getattr(run, "mission_contract", None)
        requested_authority = set(
            getattr(
                getattr(mission, "authority", None),
                "requested_capabilities",
                [],
            )
            or []
        )
        authorized_authority = set(
            getattr(
                getattr(mission, "authority", None),
                "authorized_capabilities",
                [],
            )
            or []
        )
        runtime_allowed = set(
            self.runtime.get("allowed_actions", []) or []
        )
        runtime_blocked = set(
            self.runtime.get("blocked_actions", []) or []
        )
        allowed_contracts = set(
            self.runtime.get("allowed_contract_types", []) or []
        )
        options: list[dict[str, Any]] = []
        for profile in self.profiles.catalog():
            profile_id = str(profile.get("id") or "")
            if not profile_id:
                continue
            allowed_actions: list[str] = []
            for raw_action in list(
                profile.get("allowed_actions", []) or []
            ):
                action = str(raw_action)
                if not action or not self.actions.action_exists(action):
                    continue
                normalized = self.actions.normalize_action(action)
                if (
                    normalized in runtime_blocked
                    or normalized not in runtime_allowed
                ):
                    continue
                permission = self.permission_matrix.permission_for_action(
                    normalized
                )
                if permission not in requested_authority:
                    continue
                if permission not in authorized_authority:
                    continue
                allowed_actions.append(normalized)
            default_contract_types = [
                contract_type
                for contract_type, default_profile in (
                    RuntimeProfileService.CONTRACT_DEFAULTS.items()
                )
                if default_profile == profile_id
                and contract_type in allowed_contracts
            ]
            for operation_type in list(
                profile.get("operation_types", []) or []
            ):
                if not str(operation_type):
                    continue
                operation = str(operation_type)
                options.append(
                    {
                        "option_id": self._continuation_option_id(
                            runtime_profile=profile_id,
                            operation_type=operation,
                        ),
                        "runtime_profile": profile_id,
                        "operation_type": operation,
                        "allowed_actions": self._unique(
                            allowed_actions
                        ),
                        "default_contract_types": (
                            default_contract_types
                        ),
                    }
                )
        return options

    def _continuation_action_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "action": action,
                "category": definition.category,
                "capability": definition.capability,
                "side_effect": definition.side_effect,
                "requires_approval": definition.requires_approval,
            }
            for action, definition in sorted(self.actions.list_actions().items())
            if action in set(self.runtime.get("allowed_actions", []) or [])
            and action not in set(self.runtime.get("blocked_actions", []) or [])
        ]

    def _continuation_outcome_payload(self, outcome: Any | None) -> dict[str, Any]:
        if outcome is None:
            return {}
        return {
            "phase_id": getattr(outcome, "phase_id", None),
            "result_status": getattr(outcome, "result_status", None),
            "limitations": list(getattr(outcome, "limitations", []) or []),
            "required_disclosures": list(
                getattr(outcome, "required_disclosures", []) or []
            ),
            "missing_truth": list(getattr(outcome, "missing_truth", []) or []),
            "risk_constraints": list(
                getattr(outcome, "risk_constraints", []) or []
            ),
            "phase_dependency": dict(
                getattr(outcome, "phase_dependency", {}) or {}
            ),
            "use_safety": dict(getattr(outcome, "use_safety", {}) or {}),
            "semantic_properties": dict(
                getattr(outcome, "semantic_properties", {}) or {}
            ),
            "evidence_refs": list(getattr(outcome, "evidence_refs", []) or []),
        }

    def _workspace_resource_id(self, run: Any, contract: Any) -> str | None:
        workspace = str(getattr(run, "workspace", "") or "").strip()
        if workspace:
            normalized = os.path.normcase(os.path.abspath(workspace))
            for resource in contract.local_resources:
                if not resource.locator:
                    continue
                if os.path.normcase(os.path.abspath(resource.locator)) == normalized:
                    return resource.resource_id
        for resource in contract.local_resources:
            if resource.role in {"target_mutable", "system_mutable"}:
                return resource.resource_id
        return (
            contract.local_resources[0].resource_id
            if len(contract.local_resources) == 1
            else None
        )

    def _continuation_result(
        self,
        status: str,
        reason_code: str,
        *,
        candidate: MissionContinuationCandidate | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> MissionContinuationPlanningResult:
        return MissionContinuationPlanningResult(
            status=status,
            reason_code=reason_code,
            candidate=candidate,
            provenance=dict(provenance or {}),
            trace=[
                {
                    "stage": "task_run_planner_continuation",
                    "status": status,
                    "reason_code": reason_code,
                }
            ],
        )

    @staticmethod
    def _non_negative_int(value: Any) -> int:
        try:
            return max(0, int(value or 0))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _unique(values: list[Any]) -> list[str]:
        return list(
            dict.fromkeys(
                str(item).strip()
                for item in values
                if str(item).strip()
            )
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_planner", "profiles": self.profiles.status()}
