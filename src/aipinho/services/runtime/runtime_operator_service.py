from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.runtime_operator import RuntimeObservation, RuntimeSnapshot
from aipinho.services.roles.role_contract_service import RoleContractService
from aipinho.services.runtime.planner_v2_service import PlannerV2
from aipinho.services.runtime.runtime_contracts_v2_service import RuntimeContractsV2Service
from aipinho.services.runtime.runtime_dispatcher_v2_service import RuntimeDispatcherV2
from aipinho.services.runtime.runtime_timeline_service import RuntimeTimelineService
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine
from aipinho.services.runtime.task_run_store import TaskRunStore


class RuntimeOperatorService:
    """Read-only runtime introspection facade for governed clients."""

    def __init__(self, store: TaskRunStore | None = None) -> None:
        self.store = store or TaskRunStore()

    def snapshot(self, *, task_run_id: str | None = None, runtime_data: dict[str, Any] | None = None) -> RuntimeSnapshot:
        data = self._normalize_public_runtime_data(dict(runtime_data or {}))
        data = self._hydrate_task_run(task_run_id, data)
        snapshot = RuntimeSnapshot(
            task_id=self._scalar(data, "task_id"),
            task_run_id=task_run_id or self._scalar(data, "task_run_id"),
            operation_id=self._scalar(data, "operation_id"),
            session_id=self._scalar(data, "session_id"),
            current_intent=self._observation(data, "intent", aliases=("current_intent", "intent", "intent_type")),
            current_lifecycle=self._observation(data, "lifecycle", aliases=("current_lifecycle", "lifecycle", "status", "phase")),
            current_contracts=self._observation(data, "contracts", aliases=("current_contracts", "runtime_contracts", "contract_bundle")),
            current_roles=self._observation(data, "roles", aliases=("current_roles", "selected_roles", "role_selection")),
            current_workspace=self._observation(data, "workspace", aliases=("current_workspace", "workspace_context", "workspace")),
            current_validation=self._observation(data, "validation", aliases=("current_validation", "validation_state", "validation")),
            current_completion=self._observation(data, "completion", aliases=("current_completion", "completion_state", "completion")),
            current_speaker_truth=self._observation(data, "speaker_truth", aliases=("current_speaker_truth", "speaker_truth")),
            current_artifacts=self._observation(data, "artifacts", aliases=("current_artifacts", "artifact_state", "artifacts")),
            semantic_ir=self._observation(data, "semantic_ir", aliases=("semantic_ir", "isr")),
            execution_plan=self._observation(data, "execution_plan", aliases=("execution_plan", "plan")),
            approval=self._observation(data, "approval", aliases=("approval", "approval_state")),
            dispatcher=self._observation(data, "dispatcher", aliases=("dispatcher", "dispatch")),
            timeline=self._observation(data, "timeline", aliases=("timeline", "events")),
            executor=self._observation(data, "executor", aliases=("executor", "execution", "executor_state")),
            models=self._observation(data, "models", aliases=("models", "model_state", "model_route")),
            tools=self._observation(data, "tools", aliases=("tools", "tool_state", "tool_invocations")),
            skills=self._observation(data, "skills", aliases=("skills", "skill_state", "skill_invocations")),
            source_refs=list(data.get("source_refs", [])) if isinstance(data.get("source_refs", []), list) else [],
            read_only=True,
            side_effects=False,
        )
        snapshot.source_refs = list(dict.fromkeys([*snapshot.source_refs, *self._service_refs()]))
        return snapshot

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "runtime_operator",
            "capability": "RuntimeOperator",
            "read_only": True,
            "side_effects": False,
            "can_execute_tools": False,
            "can_create_tasks": False,
            "can_approve": False,
            "can_patch": False,
        }

    def _observation(self, data: dict[str, Any], name: str, *, aliases: tuple[str, ...]) -> RuntimeObservation:
        for key in aliases:
            if key in data:
                return RuntimeObservation(name=name, status="observed", value=data[key], source=f"runtime_data.{key}")
        return RuntimeObservation(name=name, status="missing", source="runtime_data", warnings=[f"{name}_not_present"])

    def _normalize_public_runtime_data(self, data: dict[str, Any]) -> dict[str, Any]:
        chat = data.get("chat_response")
        if not isinstance(chat, dict):
            chat = data.get("chat")
        if not isinstance(chat, dict):
            if "governance_lifecycle" in data or "artifact_links" in data:
                chat = data
            else:
                return data
        lifecycle = chat.get("governance_lifecycle") if isinstance(chat.get("governance_lifecycle"), dict) else {}
        for key in ("task_id", "operation_id", "session_id"):
            if chat.get(key) is not None:
                data.setdefault(key, chat.get(key))
        if chat.get("result_ref_id") is not None:
            data.setdefault("task_run_id", chat.get("result_ref_id"))
        if chat.get("intent") is not None:
            data.setdefault("intent", chat.get("intent"))
        if lifecycle:
            lifecycle_value = dict(lifecycle)
            if "status" not in lifecycle_value and lifecycle_value.get("state") is not None:
                lifecycle_value["status"] = lifecycle_value.get("state")
            data.setdefault("lifecycle", lifecycle_value)
            for source_key, target_key in (
                ("operation_contract", "runtime_contracts"),
                ("execution_plan", "execution_plan"),
                ("validation", "validation"),
                ("completion", "completion"),
                ("speaker_truth", "speaker_truth"),
            ):
                if isinstance(lifecycle.get(source_key), dict):
                    value = dict(lifecycle[source_key])
                    if source_key == "speaker_truth" and "safe_to_report_success" not in value and "can_claim_success" in value:
                        value["safe_to_report_success"] = value.get("can_claim_success")
                    data.setdefault(target_key, value)
            workspace = lifecycle.get("workspace")
            if isinstance(workspace, dict):
                data.setdefault("workspace_context", workspace)
            elif lifecycle.get("workspace_path"):
                data.setdefault("workspace_context", {"project_root": lifecycle.get("workspace_path")})
            else:
                operation_contract = lifecycle.get("operation_contract")
                if isinstance(operation_contract, dict) and operation_contract.get("workspace_path"):
                    data.setdefault("workspace_context", {"project_root": operation_contract.get("workspace_path")})
            approval_gate = lifecycle.get("approval_gate")
            if isinstance(approval_gate, dict):
                approval_value = dict(approval_gate)
                if "approval_created" not in approval_value:
                    approval_value["approval_created"] = bool(approval_value.get("approval_id"))
                policy = chat.get("policy")
                if isinstance(policy, dict):
                    approval_value.setdefault("policy", dict(policy))
                    if "approval_required_for" not in approval_value and isinstance(policy.get("approval_required_for"), list):
                        approval_value["approval_required_for"] = list(policy["approval_required_for"])
                    if "permission" not in approval_value and policy.get("permission") is not None:
                        approval_value["permission"] = policy.get("permission")
                data["approval"] = approval_value
        if chat.get("policy") is not None:
            data.setdefault("approval", chat.get("policy"))
        artifacts = chat.get("artifact_links") or chat.get("artifacts")
        if artifacts:
            data.setdefault("artifacts", self._normalize_public_artifacts(artifacts))
        return data

    def _normalize_public_artifacts(self, artifacts: Any) -> Any:
        if not isinstance(artifacts, list):
            return artifacts
        normalized: list[Any] = []
        for item in artifacts:
            if not isinstance(item, dict):
                normalized.append(item)
                continue
            record = dict(item)
            if not record.get("logical_path") and record.get("label"):
                record["logical_path"] = record.get("label")
            normalized.append(record)
        return normalized

    def _scalar(self, data: dict[str, Any], key: str) -> str | None:
        value = data.get(key)
        if value is None:
            return None
        return str(value)

    def _hydrate_task_run(self, task_run_id: str | None, data: dict[str, Any]) -> dict[str, Any]:
        if not task_run_id:
            return data
        run = self.store.get_run(task_run_id)
        if run is None:
            data.setdefault("task_run_id", task_run_id)
            data.setdefault("source_refs", []).append("task_run_store:not_found")
            return data
        result = self.store.get_result(run.run_id)
        timeline = RuntimeTimelineService(store=self.store).build(run.run_id)
        truth = RuntimeTruthEngine().evaluate(run, result=result, timeline=timeline)
        workspace_context = run.workspace_context.model_dump(mode="json") if run.workspace_context else run.workspace_snapshot
        contracts = {
            "contract_type": run.contract_type,
            "operation_type": run.operation_type,
            "runtime_profile": run.runtime_profile,
            "requested_actions": list(run.requested_actions),
            "capabilities_required": list(run.capabilities_required),
        }
        validation = result.validation if result and isinstance(result.validation, dict) else (
            timeline.validations[-1].result if timeline and timeline.validations else None
        )
        completion = result.completion.model_dump(mode="json") if result and result.completion else (
            timeline.completion.model_dump(mode="json") if timeline else None
        )
        source_refs = list(data.get("source_refs", [])) if isinstance(data.get("source_refs"), list) else []
        hydrated = {
            "task_id": run.task_id,
            "task_run_id": run.run_id,
            "operation_id": run.operation_id,
            "session_id": run.session_id,
            "intent_type": run.intent_map.get("intent_type") or run.operation_type,
            "status": run.status,
            "runtime_contracts": contracts,
            "workspace_context": workspace_context,
            "validation": validation,
            "completion": completion,
            "speaker_truth": truth.model_dump(mode="json"),
            "artifacts": [dict(item) for item in run.produced_artifacts],
            "timeline": timeline.model_dump(mode="json") if timeline else None,
            "executor": {
                "status": run.status,
                "mode": run.mode,
                "safe_to_report_success": bool(run.canonical_state.safe_to_report_success) if run.canonical_state else None,
            },
            "source_refs": source_refs
            + [
                "task_run_store:observed",
                "runtime_timeline_service:observed" if timeline else "runtime_timeline_service:missing",
                "runtime_truth_engine:observed",
            ],
        }
        hydrated.update(data)
        hydrated["source_refs"] = source_refs + [
            "task_run_store:observed",
            "runtime_timeline_service:observed" if timeline else "runtime_timeline_service:missing",
            "runtime_truth_engine:observed",
        ]
        return hydrated

    def _service_refs(self) -> list[str]:
        refs: list[str] = []
        for service in (RuntimeContractsV2Service(), RoleContractService(), RuntimeDispatcherV2(), PlannerV2()):
            try:
                status = service.status()
            except Exception as exc:  # pragma: no cover - defensive introspection only
                refs.append(f"{service.__class__.__name__}:unavailable:{exc.__class__.__name__}")
                continue
            refs.append(f"{status.get('service', service.__class__.__name__)}:{status.get('status', 'unknown')}")
        return refs
