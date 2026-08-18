from __future__ import annotations

from collections import Counter
from typing import Any


class LiveAlignmentConflictDetector:
    """Detects live governance alignment problems from explicit matrices.

    The detector is intentionally data-driven: callers can feed static audit
    inventories, runtime snapshots, or test fixtures without coupling this
    service to a single router or store implementation.
    """

    SIDE_EFFECT_ACTIONS = {
        "apply_patch",
        "create_directory",
        "create_file",
        "modify_file",
        "patch_apply",
        "run_command",
        "shell_build",
        "shell_command",
        "shell_test",
        "write_file",
        "write_files",
        "workspace_write",
    }

    CANONICAL_ROUTE_CLASSES = {"LIVE_CANONICAL", "LIVE_HELPER"}
    NONCANONICAL_WRITE_CLASSES = {"LIVE_LEGACY_BLOCKED", "DEAD_CONFIG", "UNKNOWN_OWNER"}

    def detect(self, matrix: dict[str, Any]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        self._detect_routes(matrix.get("routes", []), conflicts)
        self._detect_effective_configs(matrix.get("effective_configs", []), conflicts)
        self._detect_intent_contracts(matrix.get("intent_contracts", []), conflicts)
        self._detect_roles(matrix.get("roles", []), conflicts)
        self._detect_tools(matrix.get("tools", []), conflicts)
        self._detect_approvals(matrix.get("approvals", []), conflicts)
        self._detect_runtime(matrix.get("runtime", []), conflicts)
        self._detect_validation(matrix.get("validation", []), conflicts)
        self._detect_artifacts(matrix.get("artifacts", []), conflicts)
        self._detect_speaker_truth(matrix.get("speaker_truth", []), conflicts)
        self._detect_qa(matrix.get("qa", {}), conflicts)
        return conflicts

    def severity_counts(self, conflicts: list[dict[str, Any]]) -> dict[str, int]:
        counts = Counter(str(item.get("severity") or "UNKNOWN") for item in conflicts)
        return {key: counts.get(key, 0) for key in ("P0", "P1", "P2", "UNKNOWN")}

    def _detect_routes(self, routes: Any, conflicts: list[dict[str, Any]]) -> None:
        route_list = self._list(routes)
        endpoint_counts = Counter(
            self._route_key(route)
            for route in route_list
            if isinstance(route, dict)
        )
        for route in route_list:
            if not isinstance(route, dict):
                continue
            endpoint = str(route.get("endpoint") or "unknown_endpoint")
            route_key = self._route_key(route)
            owner = str(route.get("owner") or route.get("service_owner") or "")
            route_class = str(route.get("classification") or route.get("route_class") or "")
            actions = self._set(route.get("actions") or route.get("possible_actions"))
            side_effects = bool(route.get("side_effects_possible")) or bool(actions & self.SIDE_EFFECT_ACTIONS)
            if endpoint_counts[route_key] > 1 and not route.get("duplicate_allowed"):
                self._add(
                    conflicts,
                    "route_duplicate_owner",
                    "P1",
                    "route",
                    endpoint,
                    "Endpoint appears more than once without duplicate_allowed.",
                    "Multiple public owners can diverge response, policy, or approval behavior.",
                    "Route duplicate count is greater than one.",
                    "Consolidate ownership or mark intentional compatibility alias.",
                )
            if not owner or route_class == "UNKNOWN_OWNER":
                self._add(
                    conflicts,
                    "route_missing_owner",
                    "P1",
                    "route",
                    endpoint,
                    "Live route has no declared owner.",
                    "Operator cannot know which lifecycle owns the decision.",
                    f"owner={owner!r}, classification={route_class!r}",
                    "Declare a canonical owner or quarantine the route.",
                )
            if side_effects and route_class in self.NONCANONICAL_WRITE_CLASSES:
                self._add(
                    conflicts,
                    "side_effect_route_not_canonical",
                    "P0",
                    "route",
                    endpoint,
                    "Side-effect route is not canonical.",
                    "Write or shell could bypass the canonical governance lifecycle.",
                    f"classification={route_class}, actions={sorted(actions)}",
                    "Route side effects through GovernanceLifecycle/ToolGateway or block the route.",
                )
            if side_effects and route_class not in self.CANONICAL_ROUTE_CLASSES and route_class:
                self._add(
                    conflicts,
                    "side_effect_route_degraded",
                    "P1",
                    "route",
                    endpoint,
                    "Side-effect route is not explicitly LIVE_CANONICAL/LIVE_HELPER.",
                    "The route may be callable but not certifiable.",
                    f"classification={route_class}",
                    "Mark as canonical/helper only after lifecycle evidence exists.",
                )

    def _detect_effective_configs(self, configs: Any, conflicts: list[dict[str, Any]]) -> None:
        for config in self._list(configs):
            if not isinstance(config, dict):
                continue
            component = str(config.get("component") or "unknown_component")
            if config.get("conflicting_values"):
                self._add(
                    conflicts,
                    "effective_config_conflict",
                    str(config.get("severity") or "P1"),
                    "effective_config",
                    component,
                    "Effective config contains conflicting values.",
                    "Runtime may allow, ask, or deny differently per path.",
                    str(config.get("conflicting_values")),
                    "Choose one source of truth and document consumers.",
                )
            if config.get("loaded") and not config.get("consumers"):
                self._add(
                    conflicts,
                    "config_loaded_without_consumer",
                    "P2",
                    "effective_config",
                    component,
                    "Config is loaded or present but has no known consumer.",
                    "Dead config can mislead routing and operator expectations.",
                    str(config.get("config_files") or []),
                    "Connect the config or mark it as legacy/dead.",
                )

    def _detect_intent_contracts(self, contracts: Any, conflicts: list[dict[str, Any]]) -> None:
        for item in self._list(contracts):
            if not isinstance(item, dict):
                continue
            prompt_class = str(item.get("prompt_class") or item.get("intent_type") or "unknown_intent")
            if not item.get("operation_type"):
                self._add(
                    conflicts,
                    "intent_missing_operation_type",
                    "P1",
                    "intent_contract",
                    prompt_class,
                    "Intent has no operation_type.",
                    "Policy and runtime cannot align without operation_type.",
                    str(item),
                    "Map intent_type to an operation_type before permission evaluation.",
                )
            if item.get("requires_runtime") and not item.get("runtime_profile"):
                self._add(
                    conflicts,
                    "intent_missing_runtime_profile",
                    "P1",
                    "intent_contract",
                    prompt_class,
                    "Intent requires runtime but has no runtime_profile.",
                    "TaskRun may block late with missing profile or expected outcomes.",
                    str(item),
                    "Declare runtime_profile in the canonical intent-contract matrix.",
                )
            if item.get("read_only") and self._set(item.get("actions")) & self.SIDE_EFFECT_ACTIONS:
                self._add(
                    conflicts,
                    "readonly_intent_has_write_action",
                    "P0",
                    "intent_contract",
                    prompt_class,
                    "Read-only intent contains side-effect action.",
                    "Read-only prompts can become writes.",
                    str(item.get("actions")),
                    "Split planning/analysis from write contracts.",
                )

    def _detect_roles(self, roles: Any, conflicts: list[dict[str, Any]]) -> None:
        for role in self._list(roles):
            if not isinstance(role, dict):
                continue
            role_id = str(role.get("role_id") or role.get("name") or "unknown_role")
            if role.get("requires_real_model") and not role.get("model_configured"):
                self._add(
                    conflicts,
                    "role_model_missing",
                    "P1",
                    "role_model",
                    role_id,
                    "Role requires real model but no model is configured.",
                    "Role cannot honestly claim real inference.",
                    str(role),
                    "Configure a model or mark role degraded/missing.",
                )
            if role.get("health") == "healthy" and not role.get("real_inference") and role.get("requires_real_model"):
                self._add(
                    conflicts,
                    "role_health_claims_real_without_inference",
                    "P0",
                    "role_model",
                    role_id,
                    "Role health is healthy while real_inference is false.",
                    "Stub/fallback may be presented as real model output.",
                    str(role),
                    "Set DEGRADED/MISSING or provide real model evidence.",
                )
            if role.get("fallback_possible") and not role.get("fallback_disclosure_required"):
                self._add(
                    conflicts,
                    "fallback_without_disclosure",
                    "P0",
                    "role_model",
                    role_id,
                    "Fallback is possible without disclosure requirement.",
                    "Silent fallback violates model truth.",
                    str(role),
                    "Require fallback_used, fallback_reason, model_used, and real_inference fields.",
                )
            if role.get("stub_used") and role.get("claims_real"):
                self._add(
                    conflicts,
                    "stub_claims_real",
                    "P0",
                    "role_model",
                    role_id,
                    "Stub/mock result claims real inference.",
                    "Operator receives false evidence.",
                    str(role),
                    "Mark stub_used=true and real_inference=false in response/trace.",
                )

    def _detect_tools(self, tools: Any, conflicts: list[dict[str, Any]]) -> None:
        for tool in self._list(tools):
            if not isinstance(tool, dict):
                continue
            tool_id = str(tool.get("tool_id") or tool.get("name") or "unknown_tool")
            action = str(tool.get("action") or tool.get("policy_action") or "")
            side_effect = bool(tool.get("side_effect")) or action in self.SIDE_EFFECT_ACTIONS
            if not tool.get("policy_action"):
                self._add(
                    conflicts,
                    "tool_missing_policy_action",
                    "P1",
                    "tool_gateway",
                    tool_id,
                    "Tool has no policy action.",
                    "Capability may exist without a policy decision.",
                    str(tool),
                    "Map tool_id to a policy action.",
                )
            if tool.get("contract_action_missing"):
                self._add(
                    conflicts,
                    "tool_missing_contract_action",
                    "P1",
                    "tool_gateway",
                    tool_id,
                    "Tool has no matching contract action.",
                    "Contracts cannot predict or validate tool side effects.",
                    str(tool),
                    "Map tool to contract action and expected output.",
                )
            if side_effect and not tool.get("through_gateway", True):
                self._add(
                    conflicts,
                    "side_effect_tool_bypasses_gateway",
                    "P0",
                    "tool_gateway",
                    tool_id,
                    "Side-effect tool bypasses ToolGateway.",
                    "Write/shell can bypass approval and audit.",
                    str(tool),
                    "Route through ToolGateway or block it.",
                )
            if side_effect and tool.get("approval_policy") == "ask" and not tool.get("approval_scope"):
                self._add(
                    conflicts,
                    "tool_ask_missing_approval_scope",
                    "P1",
                    "tool_gateway",
                    tool_id,
                    "Tool policy is ask but approval_scope is missing.",
                    "Approval may be generic and unsafe.",
                    str(tool),
                    "Bind tool request to approval scope, paths, actions, and expected outputs.",
                )

    def _detect_approvals(self, approvals: Any, conflicts: list[dict[str, Any]]) -> None:
        for approval in self._list(approvals):
            if not isinstance(approval, dict):
                continue
            approval_id = str(approval.get("approval_id") or "unknown_approval")
            if approval.get("status") in {"pending", "approved"}:
                if not approval.get("draft_id"):
                    self._add(
                        conflicts,
                        "approval_missing_draft_id",
                        "P0",
                        "approval",
                        approval_id,
                        "Approval has no draft_id.",
                        "Approval may authorize a loose permission instead of an executable plan.",
                        str(approval),
                        "Require draft_id before creating executable approval.",
                    )
                if not approval.get("executable_plan_ref"):
                    self._add(
                        conflicts,
                        "approval_missing_executable_plan_ref",
                        "P0",
                        "approval",
                        approval_id,
                        "Approval has no executable_plan_ref.",
                        "Approval can resume into an empty TaskRun.",
                        str(approval),
                        "Require executable_plan_ref before approval creation.",
                    )

    def _detect_runtime(self, runtimes: Any, conflicts: list[dict[str, Any]]) -> None:
        for runtime in self._list(runtimes):
            if not isinstance(runtime, dict):
                continue
            runtime_id = str(runtime.get("run_id") or runtime.get("runtime_profile") or "unknown_runtime")
            if runtime.get("executable_source") == "task_run_sanitized":
                self._add(
                    conflicts,
                    "runtime_uses_sanitized_taskrun_source",
                    "P0",
                    "runtime",
                    runtime_id,
                    "Runtime uses sanitized TaskRun as executable source.",
                    "Sanitized placeholders can be written to workspace.",
                    str(runtime),
                    "Use TaskDraft/executable plan store as execution source.",
                )
            if runtime.get("omitted_placeholder_written"):
                self._add(
                    conflicts,
                    "omitted_placeholder_written",
                    "P0",
                    "runtime",
                    runtime_id,
                    "Sanitization placeholder was written to workspace.",
                    "Generated project contains display redaction instead of real content.",
                    str(runtime),
                    "Block placeholder content and load full approved plan.",
                )
            if runtime.get("requires_plan") and not runtime.get("executable_plan_ref"):
                self._add(
                    conflicts,
                    "taskrun_missing_executable_plan",
                    "P0",
                    "runtime",
                    runtime_id,
                    "TaskRun requires plan but has no executable_plan_ref.",
                    "Execution can block late or claim false success.",
                    str(runtime),
                    "Require executable_plan_ref before creating TaskRun.",
                )

    def _detect_validation(self, validations: Any, conflicts: list[dict[str, Any]]) -> None:
        for validation in self._list(validations):
            if not isinstance(validation, dict):
                continue
            validation_id = str(validation.get("validation_id") or "unknown_validation")
            missing = validation.get("missing_required_outputs") or validation.get("missing_outcomes") or []
            if validation.get("status") == "passed" and missing:
                self._add(
                    conflicts,
                    "validation_passed_with_missing_outputs",
                    "P0",
                    "validation",
                    validation_id,
                    "Validation passed with missing required outputs.",
                    "Speaker Truth can report success without evidence.",
                    str(missing),
                    "Set validation failed/incomplete when required outputs are missing.",
                )

    def _detect_artifacts(self, artifacts: Any, conflicts: list[dict[str, Any]]) -> None:
        for artifact in self._list(artifacts):
            if not isinstance(artifact, dict):
                continue
            artifact_id = str(artifact.get("artifact_id") or artifact.get("name") or "unknown_artifact")
            if artifact.get("required") and not artifact.get("registered"):
                self._add(
                    conflicts,
                    "artifact_required_not_registered",
                    "P1",
                    "artifact",
                    artifact_id,
                    "Artifact is required but not registered.",
                    "UI may show phantom artifacts or omit requested output.",
                    str(artifact),
                    "Register artifact or report degraded/missing artifact explicitly.",
                )

    def _detect_speaker_truth(self, entries: Any, conflicts: list[dict[str, Any]]) -> None:
        for item in self._list(entries):
            if not isinstance(item, dict):
                continue
            response_id = str(item.get("response_id") or "speaker_truth")
            if item.get("claims_success") and not item.get("evidence_refs"):
                self._add(
                    conflicts,
                    "speaker_success_without_evidence",
                    "P0",
                    "speaker_truth",
                    response_id,
                    "Speaker claims success without evidence refs.",
                    "User can receive false success.",
                    str(item),
                    "Require task result, validation, artifact, or file evidence before success wording.",
                )
            if item.get("claims_execution") and item.get("execution_status") in {"planned", "preview_only", "blocked"}:
                self._add(
                    conflicts,
                    "speaker_claims_execution_without_execution",
                    "P0",
                    "speaker_truth",
                    response_id,
                    "Speaker claims execution while execution status is not executed.",
                    "Planning can be misrepresented as completed work.",
                    str(item),
                    "Render planned/blocked/pending approval truthfully.",
                )

    def _detect_qa(self, qa: Any, conflicts: list[dict[str, Any]]) -> None:
        if not isinstance(qa, dict):
            return
        if qa.get("pipeline_status") in {None, "not_tested", "partial", "degraded"}:
            self._add(
                conflicts,
                "pipeline_path_not_fully_certified",
                "P1",
                "qa",
                "pipeline",
                "Pipeline path is not fully certified.",
                "Pipeline may diverge from chat/launcher/mobile behavior.",
                str(qa.get("pipeline_status")),
                "Declare degraded or run a pipeline field test.",
                blocking=False,
            )
        if qa.get("mobile_launcher_visual_status") in {None, "not_tested", "partial", "degraded"}:
            self._add(
                conflicts,
                "mobile_launcher_visual_qa_partial",
                "P1",
                "qa",
                "mobile_launcher",
                "Mobile/Launcher visual QA is partial or degraded.",
                "UX may not reflect runtime truth.",
                str(qa.get("mobile_launcher_visual_status")),
                "Run visual QA or disclose degraded status.",
                blocking=False,
            )

    def _add(
        self,
        conflicts: list[dict[str, Any]],
        conflict_id: str,
        severity: str,
        component: str,
        owner: str,
        symptom: str,
        impact: str,
        proof: str,
        recommended_patch: str,
        *,
        blocking: bool | None = None,
    ) -> None:
        conflicts.append(
            {
                "conflict_id": conflict_id,
                "severity": severity,
                "component": component,
                "owner": owner,
                "symptom": symptom,
                "proof": proof,
                "impact": impact,
                "recommended_patch": recommended_patch,
                "blocking": severity == "P0" if blocking is None else bool(blocking),
            }
        )

    def _list(self, value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    def _set(self, value: Any) -> set[str]:
        if isinstance(value, str):
            return {value}
        if isinstance(value, (list, tuple, set)):
            return {str(item) for item in value}
        return set()

    def _route_key(self, route: dict[str, Any]) -> str:
        method = str(route.get("method") or "*").upper()
        endpoint = str(route.get("endpoint") or "unknown_endpoint")
        return f"{method} {endpoint}"
