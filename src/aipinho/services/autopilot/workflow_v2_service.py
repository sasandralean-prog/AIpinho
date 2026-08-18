from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest, ToolInvocationCreateRequest
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.memory.learning import LearningExtractionRequest
from aipinho.schemas.sandbox_autopilot import SandboxAutopilotRequest
from aipinho.schemas.skills.skill_packs import SkillPackSelectionRequest
from aipinho.schemas.workflows import (
    WorkflowApproval,
    WorkflowCancelRequest,
    WorkflowCheckpoint,
    WorkflowFinalReport,
    WorkflowPhase,
    WorkflowPlan,
    WorkflowPlanCreateRequest,
    WorkflowReplayRecord,
    WorkflowRecoveryPlan,
    WorkflowResumeRequest,
    WorkflowRun,
    WorkflowRunCreateRequest,
    WorkflowStep,
    WorkflowStepResult,
    WorkflowWorkspaceContext,
)
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.events.event_core import redact_payload
from aipinho.services.memory.learning_memory_service import LearningMemoryService
from aipinho.services.pinhoforge_bridge.pinhoforge_workflow_provider_registry import PinhoForgeWorkflowProviderRegistry
from aipinho.services.sandbox.sandbox_autopilot_service import SandboxAutopilotService
from aipinho.services.skills.skill_pack_registry_service import SkillPackRegistry
from aipinho.utils.yaml_loader import load_yaml_file


TERMINAL_STATUSES = {"completed", "completed_with_warnings", "blocked", "validation_failed", "failed", "cancelled", "timed_out"}


def _dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


class WorkflowStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.environ.get("AIPINHO_WORKFLOW_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "workflows")
        self.root.mkdir(parents=True, exist_ok=True)
        self.plans_path = self.root / "plans.json"
        self.runs_path = self.root / "runs.json"
        self.checkpoints_path = self.root / "checkpoints.json"
        self.recoveries_path = self.root / "recoveries.json"
        self.approvals_path = self.root / "approvals.json"
        self.step_results_path = self.root / "step_results.json"
        self.replays_path = self.root / "replays.json"
        self.reports_path = self.root / "reports.json"

    def save_plan(self, plan: WorkflowPlan) -> WorkflowPlan:
        rows = [item for item in self.list_plans() if item.workflow_plan_id != plan.workflow_plan_id]
        rows.append(plan)
        _write_json(self.plans_path, {"plans": [_dump(item) for item in rows]})
        return plan

    def get_plan(self, workflow_plan_id: str) -> WorkflowPlan | None:
        return next((item for item in self.list_plans() if item.workflow_plan_id == workflow_plan_id), None)

    def list_plans(self) -> list[WorkflowPlan]:
        return [WorkflowPlan(**item) for item in _read_json(self.plans_path, {"plans": []}).get("plans", [])]

    def save_run(self, run: WorkflowRun) -> WorkflowRun:
        rows = [item for item in self.list_runs(include_all=True) if item.workflow_run_id != run.workflow_run_id]
        rows.append(run)
        _write_json(self.runs_path, {"runs": [_dump(item) for item in rows]})
        return run

    def get_run(self, workflow_run_id: str) -> WorkflowRun | None:
        return next((item for item in self.list_runs(include_all=True) if item.workflow_run_id == workflow_run_id), None)

    def list_runs(self, *, include_all: bool = False) -> list[WorkflowRun]:
        rows = [WorkflowRun(**item) for item in _read_json(self.runs_path, {"runs": []}).get("runs", [])]
        return rows if include_all else [item for item in rows if item.status not in TERMINAL_STATUSES]

    def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> WorkflowCheckpoint:
        rows = [item for item in self.list_checkpoints() if item.checkpoint_id != checkpoint.checkpoint_id]
        rows.append(checkpoint)
        _write_json(self.checkpoints_path, {"checkpoints": [_dump(item) for item in rows]})
        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> WorkflowCheckpoint | None:
        return next((item for item in self.list_checkpoints() if item.checkpoint_id == checkpoint_id), None)

    def list_checkpoints(self, *, workflow_run_id: str | None = None) -> list[WorkflowCheckpoint]:
        rows = [WorkflowCheckpoint(**item) for item in _read_json(self.checkpoints_path, {"checkpoints": []}).get("checkpoints", [])]
        return [item for item in rows if item.workflow_run_id == workflow_run_id] if workflow_run_id else rows

    def save_recovery(self, recovery: WorkflowRecoveryPlan) -> WorkflowRecoveryPlan:
        rows = [item for item in self.list_recoveries() if item.recovery_plan_id != recovery.recovery_plan_id]
        rows.append(recovery)
        _write_json(self.recoveries_path, {"recoveries": [_dump(item) for item in rows]})
        return recovery

    def get_recovery(self, recovery_plan_id: str) -> WorkflowRecoveryPlan | None:
        return next((item for item in self.list_recoveries() if item.recovery_plan_id == recovery_plan_id), None)

    def list_recoveries(self, *, workflow_run_id: str | None = None) -> list[WorkflowRecoveryPlan]:
        rows = [WorkflowRecoveryPlan(**item) for item in _read_json(self.recoveries_path, {"recoveries": []}).get("recoveries", [])]
        return [item for item in rows if item.workflow_run_id == workflow_run_id] if workflow_run_id else rows

    def save_approval(self, approval: WorkflowApproval) -> WorkflowApproval:
        rows = [item for item in self.list_approvals() if item.approval_id != approval.approval_id]
        rows.append(approval)
        _write_json(self.approvals_path, {"approvals": [_dump(item) for item in rows]})
        return approval

    def get_approval(self, approval_id: str) -> WorkflowApproval | None:
        return next((item for item in self.list_approvals() if item.approval_id == approval_id), None)

    def list_approvals(self, *, workflow_run_id: str | None = None, status: str | None = None) -> list[WorkflowApproval]:
        rows = [WorkflowApproval(**item) for item in _read_json(self.approvals_path, {"approvals": []}).get("approvals", [])]
        if workflow_run_id:
            rows = [item for item in rows if item.workflow_run_id == workflow_run_id]
        if status:
            rows = [item for item in rows if item.status == status]
        return rows

    def save_step_result(self, result: WorkflowStepResult) -> WorkflowStepResult:
        rows = [item for item in self.list_step_results() if item.step_result_id != result.step_result_id]
        rows.append(result)
        _write_json(self.step_results_path, {"step_results": [_dump(item) for item in rows]})
        return result

    def get_step_result(self, step_result_id: str) -> WorkflowStepResult | None:
        return next((item for item in self.list_step_results() if item.step_result_id == step_result_id), None)

    def list_step_results(self, *, workflow_run_id: str | None = None, step_id: str | None = None) -> list[WorkflowStepResult]:
        rows = [WorkflowStepResult(**item) for item in _read_json(self.step_results_path, {"step_results": []}).get("step_results", [])]
        if workflow_run_id:
            rows = [item for item in rows if item.workflow_run_id == workflow_run_id]
        if step_id:
            rows = [item for item in rows if item.step_id == step_id]
        return rows

    def save_replay(self, replay: WorkflowReplayRecord) -> WorkflowReplayRecord:
        rows = [item for item in self.list_replays() if item.replay_id != replay.replay_id]
        rows.append(replay)
        _write_json(self.replays_path, {"replays": [_dump(item) for item in rows]})
        return replay

    def list_replays(self, *, workflow_run_id: str | None = None) -> list[WorkflowReplayRecord]:
        rows = [WorkflowReplayRecord(**item) for item in _read_json(self.replays_path, {"replays": []}).get("replays", [])]
        return [item for item in rows if item.workflow_run_id == workflow_run_id] if workflow_run_id else rows

    def save_report(self, report: WorkflowFinalReport) -> WorkflowFinalReport:
        rows = [item for item in self.list_reports() if item.workflow_run_id != report.workflow_run_id]
        rows.append(report)
        _write_json(self.reports_path, {"reports": [_dump(item) for item in rows]})
        return report

    def list_reports(self) -> list[WorkflowFinalReport]:
        return [WorkflowFinalReport(**item) for item in _read_json(self.reports_path, {"reports": []}).get("reports", [])]


class WorkflowStateMachine:
    allowed: dict[str, set[str]] = {
        "created": {"planning", "blocked", "failed", "cancelled"},
        "planning": {"waiting_for_approval", "running", "blocked", "failed", "cancelled"},
        "waiting_for_approval": {"running", "blocked", "cancelled"},
        "running": {"paused", "validating", "reporting", "recovering", "blocked", "failed", "cancelled", "timed_out"},
        "paused": {"resuming", "cancelled", "reporting"},
        "resuming": {"running", "failed", "cancelled"},
        "validating": {"running", "recovering", "reporting", "validation_failed", "failed", "cancelled"},
        "recovering": {"running", "reporting", "failed", "cancelled"},
        "reporting": {"completed", "completed_with_warnings", "validation_failed", "blocked", "failed", "cancelled"},
    }

    def transition(self, run: WorkflowRun, next_status: str) -> WorkflowRun:
        if run.status in TERMINAL_STATUSES:
            raise ValueError(f"terminal_workflow_cannot_transition:{run.status}")
        if next_status not in self.allowed.get(run.status, set()):
            raise ValueError(f"invalid_workflow_transition:{run.status}->{next_status}")
        return run.model_copy(update={"status": next_status})


class WorkflowCheckpointManager:
    def __init__(self, store: WorkflowStore) -> None:
        self.store = store

    def create(
        self,
        run: WorkflowRun,
        *,
        checkpoint_type: str,
        phase_id: str | None = None,
        step_id: str | None = None,
        metadata_sanitized: dict[str, Any] | None = None,
    ) -> WorkflowCheckpoint:
        checkpoint = WorkflowCheckpoint(
            workflow_run_id=run.workflow_run_id,
            phase_id=phase_id,
            step_id=step_id,
            checkpoint_type=checkpoint_type,  # type: ignore[arg-type]
            status="created",
            state_snapshot_ref=f"workflow_run:{run.workflow_run_id}:{checkpoint_type}",
            artifacts_snapshot=run.artifact_ids,
            memory_snapshot=run.memory_candidate_ids,
            policy_state={"policy_decision_ids": run.policy_decision_ids},
            validation_state={"validation_ids": run.validation_ids},
            evidence_refs=[*run.evidence_refs, f"workflow:{run.workflow_run_id}"],
            metadata_sanitized=redact_payload(metadata_sanitized or {}),
        )
        return self.store.save_checkpoint(checkpoint)


class WorkflowRecoveryManager:
    def __init__(self, store: WorkflowStore) -> None:
        self.store = store

    def create_plan(self, run: WorkflowRun, *, failure_source: str, failure_reason: str) -> WorkflowRecoveryPlan:
        recovery = WorkflowRecoveryPlan(
            workflow_run_id=run.workflow_run_id,
            failure_source=failure_source,
            failure_reason=failure_reason,
            proposed_recovery="Criar relatorio parcial, preservar evidencias e permitir retomar de checkpoint quando seguro.",
            risk_level="low",
            requires_approval=False,
            steps=["preserve_evidence", "generate_partial_report", "resume_from_checkpoint_or_stop_safely"],
            evidence_refs=[*run.evidence_refs, f"workflow:{run.workflow_run_id}"],
        )
        return self.store.save_recovery(recovery)


class WorkflowPlanner:
    def __init__(
        self,
        *,
        store: WorkflowStore | None = None,
        skill_packs: SkillPackRegistry | None = None,
        sandbox_autopilot: SandboxAutopilotService | None = None,
        bridge_registry: PinhoForgeWorkflowProviderRegistry | None = None,
    ) -> None:
        self.store = store or WorkflowStore()
        self.skill_packs = skill_packs or SkillPackRegistry()
        self.sandbox_autopilot = sandbox_autopilot or SandboxAutopilotService()
        self.bridge_registry = bridge_registry or PinhoForgeWorkflowProviderRegistry()
        self.policy = load_yaml_file(PATHS.config_root / "autopilot" / "workflow_policy.yaml", critical=False, root=PATHS.config_root)

    def create_plan(self, request: WorkflowPlanCreateRequest) -> WorkflowPlan:
        route = self.sandbox_autopilot.route(
            SandboxAutopilotRequest(
                session_id=request.session_id,
                requesting_agent_id=request.requesting_agent_id,
                user_goal=request.user_goal,
                sandbox_workspace_id=request.sandbox_workspace_id,
                dry_run=True,
                metadata_sanitized=request.metadata_sanitized,
            )
        )
        workflow_type = request.workflow_type or self._workflow_type(request.user_goal, route.route_type)
        selected_packs = self._select_packs(request, workflow_type)
        workspace = WorkflowWorkspaceContext(
            source_workspace_id=request.source_workspace_id,
            target_workspace_id=request.target_workspace_id,
            sandbox_workspace_id=request.sandbox_workspace_id,
            external_path_detected=route.route_type == "external_path_onboarding_required",
            onboarding_required=route.route_type == "external_path_onboarding_required",
            write_allowed=bool(request.target_workspace_id) and workflow_type != "external_workspace_onboarding",
            reasons=[*route.reasons],
        )
        risk = self._risk_for(workflow_type, route.risk_level)
        bridge_bundle: dict[str, Any] | None = None
        if workflow_type == "bridge_provider_workflow":
            bridge_bundle = self.bridge_registry.select_recipes(
                user_goal=request.user_goal,
                requested_capabilities=request.requested_capabilities,
                workspace_ref=request.metadata_sanitized.get("workspace_ref") or request.metadata_sanitized.get("project_path"),
                source_scope=str(request.metadata_sanitized.get("source_scope") or self.bridge_registry.default_source_scope()),
                metadata=request.metadata_sanitized,
            )
        phases = self._phases_for(workflow_type, selected_packs, route.recommended_skills, risk, bridge_bundle=bridge_bundle)
        approval_strategy = []
        if risk in {"medium", "high"} and workflow_type != "bridge_provider_workflow":
            approval_strategy.append(f"approval_required_for_{risk}_risk")
        if workflow_type == "promotion_workflow":
            approval_strategy.append("approval_required_for_promotion_apply")
        plan = WorkflowPlan(
            session_id=request.session_id,
            requesting_agent_id=request.requesting_agent_id,
            user_goal=request.user_goal,
            workflow_type=workflow_type,
            project_profile_id=request.project_profile_id,
            workspace_context=workspace,
            sandbox_context={"route_decision": route.model_dump()},
            workspace_ref=request.metadata_sanitized.get("workspace_ref") or request.metadata_sanitized.get("project_path"),
            source_scope=str(request.metadata_sanitized.get("source_scope") or ("registered_workspace" if request.source_workspace_id else self.bridge_registry.default_source_scope())),
            target_workspace_id=request.target_workspace_id,
            source_workspace_id=request.source_workspace_id,
            selected_skill_packs=selected_packs,
            selected_skills=route.recommended_skills,
            phases=phases,
            expected_artifacts=["workflow_plan.md", "workflow_final_report.md", "workflow_step_results.json"] if workflow_type == "bridge_provider_workflow" else ["workflow_plan.md", "workflow_final_report.md"],
            expected_outputs=self._bridge_expected_outputs(bridge_bundle) if bridge_bundle else [],
            expected_memory_candidates=["run_learning_summary", "workflow_lesson"],
            validation_strategy=["event_trace_exists", "evidence_refs_present", "artifact_library_indexed", "no_source_readonly_write"],
            approval_strategy=approval_strategy,
            recovery_strategy=["retry_low_risk_step", "skip_optional_step", "partial_report", "resume_from_checkpoint"],
            risk_assessment={
                "risk_level": risk,
                "route_risk": route.risk_level,
                "workflow_type": workflow_type,
                "provider_readiness": bridge_bundle.get("provider_readiness", {}) if bridge_bundle else {},
                "selected_tools": bridge_bundle.get("selected_tools", []) if bridge_bundle else [],
            },
            limits=dict(self.policy.get("limits", {})) if isinstance(self.policy, dict) else {},
            assumptions=["WorkflowPlan nao executa por si so.", "Side effects usam Tool Gateway ou servicos governados existentes."],
            constraints=["source_readonly_write_denied", "token_not_in_url", "raw_hidden_by_default"],
            evidence_refs=[*route.evidence_refs, "workflow_planner:v2", *(bridge_bundle.get("selected_tools", []) if bridge_bundle else [])],
            metadata_sanitized={"route_type": route.route_type, "bridge_bundle": bridge_bundle or {}, **request.metadata_sanitized},
        )
        return self.store.save_plan(plan)

    def _workflow_type(self, goal: str, route_type: str) -> str:
        lowered = goal.casefold()
        if route_type == "external_path_onboarding_required":
            return "external_workspace_onboarding"
        if any(term in lowered for term in ("pinhoforge", "android workbench", "gradle", "adb", "logcat", "terminal governado", "command catalog", "conversao", "image lab", "3d lab")):
            return "bridge_provider_workflow"
        if any(term in lowered for term in ("promova", "promover", "promotion", "target_mutable")):
            return "promotion_workflow"
        if any(term in lowered for term in ("audite ux", "ux mobile", "interface mobile", "experiencia")):
            return "mobile_ux_audit"
        if any(term in lowered for term in ("debug", "erro", "falha", "corrija", "bug")):
            return "project_debugging"
        if any(term in lowered for term in ("document", "relatorio", "documentacao", "docs")):
            return "docs_generation"
        if any(term in lowered for term in ("crie", "gerar", "construa", "ferramenta", "app", "api", "cli")):
            return "sandbox_creation"
        return "project_analysis"

    def _select_packs(self, request: WorkflowPlanCreateRequest, workflow_type: str) -> list[str]:
        selection = self.skill_packs.select(
            SkillPackSelectionRequest(
                user_goal=request.user_goal,
                agent_id="autopilot",
                project_stack=request.project_stack or "mixed",
                requested_capabilities=[*request.requested_capabilities, workflow_type],
                execution_mode="sandbox_autopilot" if workflow_type == "sandbox_creation" else "assisted_execution",
            )
        )
        return [candidate.skill_pack_id for candidate in selection.candidates[:3]]

    def _risk_for(self, workflow_type: str, route_risk: str) -> str:
        if workflow_type == "external_workspace_onboarding":
            return "low"
        if workflow_type in {"promotion_workflow", "project_improvement", "project_debugging"}:
            return "medium"
        if workflow_type in {"project_analysis", "docs_generation", "mobile_ux_audit", "artifact_recovery", "sandbox_creation"}:
            return "high" if route_risk == "critical" else "low"
        return route_risk if route_risk in {"low", "medium", "high", "critical"} else "low"

    def _phases_for(self, workflow_type: str, selected_packs: list[str], selected_skills: list[str], risk: str, *, bridge_bundle: dict[str, Any] | None = None) -> list[WorkflowPhase]:
        if workflow_type == "bridge_provider_workflow":
            return self._bridge_phases_for(bridge_bundle or {}, risk)
        definitions = [
            ("intake", "Registrar objetivo, restricoes e evidencias iniciais.", [("route_decision", "Classificar workflow e rota tecnica.", "route_decision", False)]),
            ("planning", "Criar plano tecnico auditavel.", [("skill_pack_execute", "Selecionar skill packs e skills governadas.", "skill_pack_execute", False)]),
            ("execution", "Executar a parte tecnica governada.", [("sandbox_task_create", "Executar em sandbox ou preparar workspace governado.", "sandbox_task_create", workflow_type in {"sandbox_creation", "project_debugging", "project_improvement"})]),
            ("validation", "Validar resultado e evidencias.", [("validate", "Executar validacao obrigatoria do workflow.", "validate", False)]),
            ("artifact_generation", "Gerar artifacts e relatorio.", [("artifact_export", "Indexar artifacts do workflow.", "artifact_export", True)]),
            ("learning", "Criar candidatos de memoria com evidencia.", [("memory_extract", "Extrair aprendizado operacional como candidate.", "memory_extract", False)]),
            ("reporting", "Gerar resposta final verdadeira.", [("report_generate", "Gerar relatorio final do workflow.", "report_generate", True)]),
        ]
        if workflow_type == "external_workspace_onboarding":
            definitions = [
                ("intake", "Detectar caminho externo e escopo.", [("route_decision", "Identificar onboarding necessario.", "route_decision", False)]),
                ("context_resolution", "Pausar para registro/importacao governada.", [("workspace_onboarding", "Solicitar onboarding antes de ler/escrever.", "workspace_onboarding", False)]),
                ("reporting", "Explicar proximo passo seguro.", [("report_generate", "Gerar relatorio parcial.", "report_generate", True)]),
            ]
        phases: list[WorkflowPhase] = []
        for phase_index, (name, objective, step_defs) in enumerate(definitions, start=1):
            phase = WorkflowPhase(index=phase_index, name=name, objective=objective)
            steps = [
                WorkflowStep(
                    phase_id=phase.phase_id,
                    index=step_index,
                    name=step_name,
                    objective=step_objective,
                    action_type=action_type,  # type: ignore[arg-type]
                    source_scope="sandbox" if action_type == "sandbox_task_create" else "artifact_workspace",
                    skill_pack_id=selected_packs[0] if action_type == "skill_pack_execute" and selected_packs else None,
                    skill_id=selected_skills[0] if action_type == "skill_pack_execute" and selected_skills else None,
                    risk_level=risk if side_effect else "low",
                    approval_required=side_effect and risk in {"medium", "high"},
                    side_effects_expected=side_effect,
                    evidence_refs=[f"skill_pack:{pack}" for pack in selected_packs[:3]] if action_type == "skill_pack_execute" else [],
                )
                for step_index, (step_name, step_objective, action_type, side_effect) in enumerate(step_defs, start=1)
            ]
            phases.append(phase.model_copy(update={"steps": steps}))
        return phases

    def _bridge_phases_for(self, bridge_bundle: dict[str, Any], risk: str) -> list[WorkflowPhase]:
        phases: list[WorkflowPhase] = []
        intake = WorkflowPhase(index=1, name="intake", objective="Registrar objetivo, providers e readiness bridge.")
        intake_steps = [
            WorkflowStep(
                phase_id=intake.phase_id,
                index=1,
                name="route_decision",
                title="Route decision",
                objective="Consolidar objetivo e trilha governada do workflow bridge.",
                action_type="route_decision",
                source_scope="artifact_workspace",
                expected_outputs=["workflow_route_summary"],
                evidence_refs=["workflow:bridge_intake"],
            )
        ]
        phases.append(intake.model_copy(update={"steps": intake_steps}))

        execution = WorkflowPhase(index=2, name="bridge_execution", objective="Executar providers PinhoForge via Tool Gateway e Policy Kernel.")
        execution_steps: list[WorkflowStep] = []
        for step_index, recipe in enumerate(bridge_bundle.get("recipes", []), start=1):
            execution_steps.append(
                WorkflowStep(
                    phase_id=execution.phase_id,
                    index=step_index,
                    name=recipe["tool_name"],
                    title=recipe["recipe_id"],
                    objective=f"Executar {recipe['provider_id']}::{recipe['operation']} de forma governada.",
                    action_type="tool_invoke",
                    provider_id=recipe["provider_id"],
                    capability_id=recipe["capability_id"],
                    operation=recipe["operation"],
                    input_sanitized=recipe["input"],
                    tool_name=recipe["tool_name"],
                    source_scope=recipe["source_scope"],
                    expected_outputs=list(recipe.get("expected_outputs", [])),
                    risk_level=recipe["risk_level"],
                    requires_preview=bool(recipe.get("requires_preview", False)),
                    requires_approval=bool(recipe.get("requires_approval", False)),
                    approval_required=bool(recipe.get("requires_approval", False)),
                    side_effects_expected=bool(recipe.get("side_effects_expected", False)),
                    evidence_refs=[f"provider:{recipe['provider_id']}", f"capability:{recipe['capability_id']}"],
                )
            )
        phases.append(execution.model_copy(update={"steps": execution_steps}))

        validation = WorkflowPhase(index=3, name="validation", objective="Validar resultados, artifacts e rastreabilidade.")
        validation_steps = [
            WorkflowStep(
                phase_id=validation.phase_id,
                index=1,
                name="validate",
                objective="Consolidar evidencias e validar os outputs do workflow bridge.",
                action_type="validate",
                source_scope="artifact_workspace",
                expected_outputs=["workflow_validation"],
                evidence_refs=["workflow:bridge_validation"],
            )
        ]
        phases.append(validation.model_copy(update={"steps": validation_steps}))

        artifact_generation = WorkflowPhase(index=4, name="artifact_generation", objective="Exportar replay, step results e relatorio.")
        artifact_steps = [
            WorkflowStep(
                phase_id=artifact_generation.phase_id,
                index=1,
                name="artifact_export",
                objective="Registrar artifacts consolidados do workflow.",
                action_type="artifact_export",
                source_scope="artifact_workspace",
                expected_outputs=["workflow_step_results_artifact", "workflow_replay_artifact"],
                risk_level=risk,
                side_effects_expected=True,
                evidence_refs=["workflow:bridge_artifact_generation"],
            ),
            WorkflowStep(
                phase_id=artifact_generation.phase_id,
                index=2,
                name="memory_extract",
                objective="Gerar memory candidates com evidencias do workflow bridge.",
                action_type="memory_extract",
                source_scope="artifact_workspace",
                expected_outputs=["memory_candidates"],
                evidence_refs=["workflow:bridge_memory_extract"],
            ),
            WorkflowStep(
                phase_id=artifact_generation.phase_id,
                index=3,
                name="report_generate",
                objective="Preparar relatorio final do workflow bridge.",
                action_type="report_generate",
                source_scope="artifact_workspace",
                expected_outputs=["workflow_final_report"],
                risk_level=risk,
                side_effects_expected=True,
                evidence_refs=["workflow:bridge_report"],
            ),
        ]
        phases.append(artifact_generation.model_copy(update={"steps": artifact_steps}))
        return phases

    def _bridge_expected_outputs(self, bridge_bundle: dict[str, Any] | None) -> list[str]:
        if not bridge_bundle:
            return []
        outputs: list[str] = []
        for recipe in bridge_bundle.get("recipes", []):
            for output in recipe.get("expected_outputs", []):
                if output not in outputs:
                    outputs.append(output)
        outputs.extend([item for item in ["workflow_validation", "workflow_replay", "workflow_final_report"] if item not in outputs])
        return outputs


class WorkflowExecutor:
    def __init__(
        self,
        *,
        store: WorkflowStore | None = None,
        state_machine: WorkflowStateMachine | None = None,
        sandbox_autopilot: SandboxAutopilotService | None = None,
        tool_gateway: AgentToolGatewayService | None = None,
        learning: LearningMemoryService | None = None,
        kernel: AgentSessionKernelService | None = None,
        bridge_registry: PinhoForgeWorkflowProviderRegistry | None = None,
    ) -> None:
        self.store = store or WorkflowStore()
        self.state_machine = state_machine or WorkflowStateMachine()
        self.checkpoints = WorkflowCheckpointManager(self.store)
        self.recovery = WorkflowRecoveryManager(self.store)
        self.sandbox_autopilot = sandbox_autopilot or SandboxAutopilotService()
        self.tool_gateway = tool_gateway or AgentToolGatewayService()
        self.learning = learning or LearningMemoryService()
        self.kernel = kernel or AgentSessionKernelService()
        self.bridge_registry = bridge_registry or PinhoForgeWorkflowProviderRegistry()

    def create_run(self, request: WorkflowRunCreateRequest) -> WorkflowRun:
        plan = self.store.get_plan(request.workflow_plan_id)
        if plan is None:
            raise FileNotFoundError(request.workflow_plan_id)
        run = WorkflowRun(
            workflow_plan_id=plan.workflow_plan_id,
            workflow_id=plan.workflow_id,
            session_id=plan.session_id,
            initiating_agent_id=request.initiating_agent_id,
            status="created",
            workflow_type=plan.workflow_type,
            mode=plan.mode,
            project_profile_id=plan.project_profile_id,
            target_workspace_id=plan.target_workspace_id,
            source_workspace_id=plan.source_workspace_id,
            evidence_refs=[*plan.evidence_refs, f"workflow_plan:{plan.workflow_plan_id}"],
            metadata_sanitized=redact_payload({"workflow_title": plan.title, **request.metadata_sanitized}),
        )
        run = self._ensure_gateway_run(run, plan)
        run = self.store.save_run(run)
        if request.autorun:
            run = self.execute(run.workflow_run_id)
        return run

    def execute(self, workflow_run_id: str) -> WorkflowRun:
        run = self._require_run(workflow_run_id)
        plan = self._require_plan(run.workflow_plan_id)
        try:
            run = self.state_machine.transition(run, "planning")
            self.store.save_run(run)
            plan_artifact = self._write_artifact(run, "workflow_plan.md", self._plan_markdown(plan), origin="autopilot")
            run = run.model_copy(update={"artifact_ids": self._append_unique(run.artifact_ids, plan_artifact["artifact_id"])})
            run = self.state_machine.transition(run, "running")
            self.store.save_run(run)
            if plan.approval_strategy:
                approval = self._create_approval(run, plan)
                run = run.model_copy(update={"status": "waiting_for_approval", "warnings": self._append_unique(run.warnings, "approval_required"), "metadata_sanitized": {**run.metadata_sanitized, "pending_approval_id": approval.approval_id}})
                self.store.save_run(run)
                return run
            return self._run_without_pending_approval(run, plan)
        except Exception as exc:
            recovery = self.recovery.create_plan(run, failure_source="workflow_executor", failure_reason=type(exc).__name__)
            run = run.model_copy(update={
                "status": "failed",
                "errors": self._append_unique(run.errors, type(exc).__name__),
                "recovery_plan_ids": self._append_unique(run.recovery_plan_ids, recovery.recovery_plan_id),
                "completed_at": utc_now_iso(),
            })
            return self.store.save_run(run)

    def approve(self, workflow_run_id: str, approval_id: str, *, approved_by: str = "user") -> WorkflowRun:
        run = self._require_run(workflow_run_id)
        approval = self.store.get_approval(approval_id)
        if approval is None or approval.workflow_run_id != workflow_run_id:
            raise FileNotFoundError(approval_id)
        approval = approval.model_copy(update={"status": "approved", "decided_at": utc_now_iso(), "metadata_sanitized": {**approval.metadata_sanitized, "approved_by": approved_by}})
        self.store.save_approval(approval)
        pending_meta = dict(run.metadata_sanitized)
        pending_meta.pop("pending_approval_id", None)
        pending_meta.pop("pending_step_id", None)
        run = run.model_copy(update={"status": "running", "policy_decision_ids": self._append_unique(run.policy_decision_ids, f"approval:{approval.approval_id}"), "metadata_sanitized": pending_meta})
        self.store.save_run(run)
        return self._run_without_pending_approval(run, self._require_plan(run.workflow_plan_id))

    def reject(self, workflow_run_id: str, approval_id: str, *, rejected_by: str = "user") -> WorkflowRun:
        run = self._require_run(workflow_run_id)
        approval = self.store.get_approval(approval_id)
        if approval is None or approval.workflow_run_id != workflow_run_id:
            raise FileNotFoundError(approval_id)
        approval = approval.model_copy(update={"status": "rejected", "decided_at": utc_now_iso(), "metadata_sanitized": {**approval.metadata_sanitized, "rejected_by": rejected_by}})
        self.store.save_approval(approval)
        if approval.step_id:
            step_result = self._latest_step_result(workflow_run_id, approval.step_id)
            if step_result is not None:
                self.store.save_step_result(
                    step_result.model_copy(
                        update={
                            "status": "blocked",
                            "approval_id": approval.approval_id,
                            "completed_at": utc_now_iso(),
                            "errors": self._append_unique(step_result.errors, "approval_rejected"),
                            "output_summary": "Step bloqueado porque o approval foi rejeitado.",
                        }
                    )
                )
        report = self._final_report(run.model_copy(update={"status": "cancelled", "warnings": self._append_unique(run.warnings, "approval_rejected")}), "Workflow cancelado porque a aprovacao foi rejeitada.")
        return self.store.save_run(run.model_copy(update={"status": "cancelled", "artifact_ids": self._extend_unique(run.artifact_ids, report.artifact_ids), "completed_at": utc_now_iso(), "warnings": self._append_unique(run.warnings, "approval_rejected")}))

    def pause(self, workflow_run_id: str) -> WorkflowRun:
        run = self._require_run(workflow_run_id)
        if run.status != "running":
            return run
        run = self.state_machine.transition(run, "paused")
        return self.store.save_run(run)

    def resume(self, workflow_run_id: str, request: WorkflowResumeRequest) -> WorkflowRun:
        run = self._require_run(workflow_run_id)
        if run.status != "paused":
            return run
        run = self.state_machine.transition(run, "resuming")
        run = run.model_copy(update={"metadata_sanitized": {**run.metadata_sanitized, "resume_reason": request.reason, "resume_checkpoint_id": request.checkpoint_id}})
        self.store.save_run(run)
        run = self.state_machine.transition(run, "running")
        self.store.save_run(run)
        return self._run_without_pending_approval(run, self._require_plan(run.workflow_plan_id))

    def cancel(self, workflow_run_id: str, request: WorkflowCancelRequest) -> WorkflowRun:
        run = self._require_run(workflow_run_id)
        if request.generate_partial_report:
            report = self._final_report(run.model_copy(update={"status": "cancelled"}), f"Workflow cancelado: {request.reason}")
            run = run.model_copy(update={"artifact_ids": self._extend_unique(run.artifact_ids, report.artifact_ids)})
        run = run.model_copy(update={"status": "cancelled", "completed_at": utc_now_iso(), "warnings": self._append_unique(run.warnings, "partial_report_generated" if request.generate_partial_report else "cancelled_without_report")})
        final_checkpoint = self.checkpoints.create(run, checkpoint_type="final", metadata_sanitized={"cancel_reason": request.reason})
        return self.store.save_run(run.model_copy(update={"checkpoint_ids": self._append_unique(run.checkpoint_ids, final_checkpoint.checkpoint_id)}))

    def recover(self, workflow_run_id: str) -> WorkflowRecoveryPlan:
        run = self._require_run(workflow_run_id)
        recovery = self.recovery.create_plan(run, failure_source="manual_recovery_request", failure_reason="user_requested_recovery")
        run = run.model_copy(update={"status": "recovering" if run.status not in TERMINAL_STATUSES else run.status, "recovery_plan_ids": self._append_unique(run.recovery_plan_ids, recovery.recovery_plan_id)})
        self.store.save_run(run)
        return recovery

    def report(self, workflow_run_id: str) -> WorkflowFinalReport:
        return self._final_report(self._require_run(workflow_run_id), "Relatorio final solicitado.")

    def trace(self, workflow_run_id: str) -> dict[str, Any]:
        run = self._require_run(workflow_run_id)
        plan = self._require_plan(run.workflow_plan_id)
        return {
            "status": "ok",
            "workflow_run": run.model_dump(),
            "workflow_plan": plan.model_dump(),
            "step_results": [item.model_dump() for item in self.store.list_step_results(workflow_run_id=workflow_run_id)],
            "checkpoints": [item.model_dump() for item in self.store.list_checkpoints(workflow_run_id=workflow_run_id)],
            "recoveries": [item.model_dump() for item in self.store.list_recoveries(workflow_run_id=workflow_run_id)],
            "approvals": [item.model_dump() for item in self.store.list_approvals(workflow_run_id=workflow_run_id)],
            "replays": [item.model_dump() for item in self.store.list_replays(workflow_run_id=workflow_run_id)],
            "tool_invocations": [item.model_dump() for item in self.tool_gateway.list_invocations(run_id=run.gateway_run_id)] if run.gateway_run_id else [],
            "reports": [item.model_dump() for item in self.store.list_reports() if item.workflow_run_id == workflow_run_id],
        }

    def mobile_view_model(self) -> dict[str, Any]:
        runs = self.store.list_runs(include_all=True)[-20:]
        active = [run for run in runs if run.status not in TERMINAL_STATUSES]
        selected = active[-1] if active else runs[-1] if runs else None
        return {
            "state": {
                "screen": "workflows",
                "status": "ok" if selected else "empty",
                "raw_default_visible": False,
                "human_summary": "Workflows Autopilot v2 com plano, checkpoints e evidencias.",
            },
            "active_workflow": selected.model_dump() if selected else None,
            "runs": [run.model_dump() for run in runs],
            "active_step_results": [item.model_dump() for item in self.store.list_step_results(workflow_run_id=selected.workflow_run_id)] if selected else [],
            "pending_approvals": [approval.model_dump() for approval in self.store.list_approvals(status="pending")],
            "actions": [
                {"label": "Pausar", "endpoint": "/api/v1/workflows/runs/{workflow_run_id}/pause"},
                {"label": "Retomar", "endpoint": "/api/v1/workflows/runs/{workflow_run_id}/resume"},
                {"label": "Cancelar", "endpoint": "/api/v1/workflows/runs/{workflow_run_id}/cancel"},
                {"label": "Ver plano", "endpoint": "/api/v1/workflows/plans/{workflow_plan_id}"},
                {"label": "Ver step results", "endpoint": "/api/v1/workflows/runs/{workflow_run_id}/step-results"},
                {"label": "Ver replay", "endpoint": "/api/v1/workflows/runs/{workflow_run_id}/replay"},
                {"label": "Ver checkpoints", "endpoint": "/api/v1/workflows/runs/{workflow_run_id}/checkpoints"},
                {"label": "Abrir Debugger", "endpoint": "/api/v1/workflows/runs/{workflow_run_id}/trace"},
            ],
        }

    def _run_without_pending_approval(self, run: WorkflowRun, plan: WorkflowPlan) -> WorkflowRun:
        run = self._execute_phases(run, plan)
        if run.status in {"failed", "blocked", "validation_failed", "cancelled", "timed_out", "waiting_for_approval"}:
            return run
        run = self.state_machine.transition(run, "reporting")
        self.store.save_run(run)
        replay_artifact = self._write_artifact(
            run,
            "workflow_step_results.json",
            json.dumps([item.model_dump() for item in self.store.list_step_results(workflow_run_id=run.workflow_run_id)], indent=2, ensure_ascii=True),
            origin="workflow_step_results",
        )
        report = self._final_report(run, "Workflow concluido com evidencias preservadas.")
        replay = self.store.save_replay(
            WorkflowReplayRecord(
                workflow_run_id=run.workflow_run_id,
                workflow_id=run.workflow_id,
                summary="Replay governado disponivel para depuracao read-only do workflow.",
                step_result_ids=run.step_result_ids,
                artifact_ids=self._extend_unique(run.artifact_ids, [replay_artifact["artifact_id"], *report.artifact_ids]),
                evidence_refs=[*run.evidence_refs, f"workflow:{run.workflow_run_id}", f"artifact:{replay_artifact['artifact_id']}"],
            )
        )
        warnings = run.warnings
        final_status = "completed_with_warnings" if warnings else "completed"
        if not report.evidence_refs:
            final_status = "failed"
        run = run.model_copy(update={
            "status": final_status,
            "artifact_ids": self._extend_unique(run.artifact_ids, [replay_artifact["artifact_id"], *report.artifact_ids]),
            "memory_candidate_ids": self._extend_unique(run.memory_candidate_ids, report.memory_candidate_ids),
            "evidence_refs": self._extend_unique(run.evidence_refs, [*report.evidence_refs, f"replay:{replay.replay_id}"]),
            "completed_at": utc_now_iso(),
        })
        return self.store.save_run(run)

    def _execute_phases(self, run: WorkflowRun, plan: WorkflowPlan) -> WorkflowRun:
        for phase in plan.phases:
            before = self.checkpoints.create(run, checkpoint_type="after_phase", phase_id=phase.phase_id, metadata_sanitized={"before_phase": phase.name})
            run = run.model_copy(update={"current_phase_id": phase.phase_id, "checkpoint_ids": self._append_unique(run.checkpoint_ids, before.checkpoint_id)})
            self.store.save_run(run)
            for step in phase.steps:
                latest = self._latest_step_result(run.workflow_run_id, step.step_id)
                if latest and latest.status in {"completed", "completed_with_warnings", "skipped"}:
                    run = run.model_copy(update={"current_step_id": step.step_id, "current_step_result_id": latest.step_result_id})
                    self.store.save_run(run)
                    continue
                if latest and latest.status == "waiting_for_approval" and self._approved_step_approval(run.workflow_run_id, step.step_id) is None:
                    return self.store.save_run(run.model_copy(update={"status": "waiting_for_approval", "current_step_id": step.step_id, "current_step_result_id": latest.step_result_id}))
                run = run.model_copy(update={"current_step_id": step.step_id})
                self.store.save_run(run)
                if step.side_effects_expected:
                    checkpoint = self.checkpoints.create(run, checkpoint_type="before_side_effect", phase_id=phase.phase_id, step_id=step.step_id)
                    run = run.model_copy(update={"checkpoint_ids": self._append_unique(run.checkpoint_ids, checkpoint.checkpoint_id), "policy_decision_ids": self._append_unique(run.policy_decision_ids, f"policy:{step.step_id}")})
                    self.store.save_run(run)
                run = self._execute_step(run, plan, step)
                if run.status in {"failed", "blocked", "validation_failed"}:
                    recovery = self.recovery.create_plan(run, failure_source=step.action_type, failure_reason=run.errors[-1] if run.errors else "workflow_step_failed")
                    return self.store.save_run(run.model_copy(update={"recovery_plan_ids": self._append_unique(run.recovery_plan_ids, recovery.recovery_plan_id)}))
                if run.status == "waiting_for_approval":
                    return run
            after = self.checkpoints.create(run, checkpoint_type="after_phase", phase_id=phase.phase_id, metadata_sanitized={"after_phase": phase.name})
            run = run.model_copy(update={"checkpoint_ids": self._append_unique(run.checkpoint_ids, after.checkpoint_id), "evidence_refs": self._append_unique(run.evidence_refs, f"phase:{phase.name}")})
            self.store.save_run(run)
        validation_checkpoint = self.checkpoints.create(run, checkpoint_type="after_validation", metadata_sanitized={"validation": "workflow_evidence_present"})
        run = run.model_copy(update={
            "status": "validating",
            "checkpoint_ids": self._append_unique(run.checkpoint_ids, validation_checkpoint.checkpoint_id),
            "validation_ids": self._append_unique(run.validation_ids, f"workflow_validation_{run.workflow_run_id}"),
            "evidence_refs": self._append_unique(run.evidence_refs, f"validation:workflow_validation_{run.workflow_run_id}"),
        })
        self.store.save_run(run)
        if not run.evidence_refs:
            return self.store.save_run(run.model_copy(update={"status": "validation_failed", "errors": self._append_unique(run.errors, "missing_evidence_refs")}))
        if plan.workflow_type == "bridge_provider_workflow" and not self.store.list_step_results(workflow_run_id=run.workflow_run_id):
            return self.store.save_run(run.model_copy(update={"status": "validation_failed", "errors": self._append_unique(run.errors, "missing_step_results")}))
        return self.store.save_run(run.model_copy(update={"status": "running"}))

    def _execute_step(self, run: WorkflowRun, plan: WorkflowPlan, step: WorkflowStep) -> WorkflowRun:
        step_result = self.store.save_step_result(
            WorkflowStepResult(
                workflow_run_id=run.workflow_run_id,
                step_id=step.step_id,
                provider_id=step.provider_id,
                capability_id=step.capability_id,
                tool_name=step.tool_name,
                operation=step.operation or step.action_type,
                source_scope=step.source_scope,
                status="running",
                input_summary=json.dumps(redact_payload(step.input_sanitized), ensure_ascii=True)[:400],
                evidence_refs=[*step.evidence_refs, f"workflow:{run.workflow_run_id}", f"step:{step.step_id}"],
                started_at=utc_now_iso(),
                metadata_sanitized={"phase_id": step.phase_id, "tool_name": step.tool_name, "source_scope": step.source_scope},
            )
        )
        run = run.model_copy(update={"current_step_result_id": step_result.step_result_id, "step_result_ids": self._append_unique(run.step_result_ids, step_result.step_result_id)})
        self.store.save_run(run)
        if step.source_scope == "unknown":
            blocked = step_result.model_copy(
                update={
                    "status": "blocked",
                    "errors": self._append_unique(step_result.errors, "workflow_step_source_scope_unknown"),
                    "completed_at": utc_now_iso(),
                    "output_summary": "Step bloqueado porque source_scope=unknown.",
                }
            )
            self.store.save_step_result(blocked)
            return self.store.save_run(run.model_copy(update={"status": "blocked", "errors": self._append_unique(run.errors, "workflow_step_source_scope_unknown")}))
        if step.requires_approval and self._approved_step_approval(run.workflow_run_id, step.step_id) is None and step.action_type == "tool_invoke":
            approval = self._create_step_approval(run, plan, step, reason="Step exige approval antes da invocacao governada.")
            waiting = step_result.model_copy(
                update={
                    "status": "waiting_for_approval",
                    "approval_id": approval.approval_id,
                    "warnings": self._append_unique(step_result.warnings, "approval_required"),
                    "completed_at": utc_now_iso(),
                    "output_summary": "Aguardando approval do step governado.",
                }
            )
            self.store.save_step_result(waiting)
            return self.store.save_run(
                run.model_copy(
                    update={
                        "status": "waiting_for_approval",
                        "warnings": self._append_unique(run.warnings, "approval_required"),
                        "metadata_sanitized": {**run.metadata_sanitized, "pending_approval_id": approval.approval_id, "pending_step_id": step.step_id},
                    }
                )
            )
        if step.action_type == "sandbox_task_create" and plan.workflow_type == "sandbox_creation":
            result = self.sandbox_autopilot.run(
                SandboxAutopilotRequest(
                    session_id=plan.session_id,
                    requesting_agent_id=run.initiating_agent_id,
                    user_goal=plan.user_goal,
                    sandbox_workspace_id=plan.workspace_context.sandbox_workspace_id or "sandbox_ws_default",
                    dry_run=False,
                    metadata_sanitized={"workflow_run_id": run.workflow_run_id, "workflow_plan_id": plan.workflow_plan_id},
                )
            )
            if result.status in {"failed", "validation_failed", "artifact_failed", "blocked"}:
                self.store.save_step_result(
                    step_result.model_copy(
                        update={
                            "status": "failed" if result.status in {"failed", "artifact_failed"} else "blocked",
                            "errors": self._extend_unique(step_result.errors, result.errors or [result.status]),
                            "completed_at": utc_now_iso(),
                            "output_summary": "Sandbox Autopilot falhou ou foi bloqueado.",
                        }
                    )
                )
                return self.store.save_run(run.model_copy(update={"status": "validation_failed" if result.status == "validation_failed" else "blocked", "errors": self._extend_unique(run.errors, result.errors or [result.status])}))
            self.store.save_step_result(
                step_result.model_copy(
                    update={
                        "status": "completed",
                        "artifacts": list(result.artifact_ids),
                        "completed_at": utc_now_iso(),
                        "output_summary": "Sandbox Autopilot executado com sucesso.",
                        "evidence_refs": self._extend_unique(step_result.evidence_refs, result.evidence_refs),
                    }
                )
            )
            return self.store.save_run(run.model_copy(update={
                "sandbox_task_ids": self._append_unique(run.sandbox_task_ids, str(result.metadata_sanitized.get("sandbox_task_id") or result.autopilot_run_id)),
                "artifact_ids": self._extend_unique(run.artifact_ids, result.artifact_ids),
                "validation_ids": self._append_unique(run.validation_ids, str(result.validation_status or "sandbox_validation")),
                "evidence_refs": self._extend_unique(run.evidence_refs, result.evidence_refs),
                "warnings": self._extend_unique(run.warnings, result.warnings),
                "errors": self._extend_unique(run.errors, result.errors),
            }))
        if step.action_type == "workspace_onboarding":
            self.store.save_step_result(
                step_result.model_copy(
                    update={
                        "status": "blocked",
                        "warnings": self._append_unique(step_result.warnings, "external_workspace_onboarding_required"),
                        "completed_at": utc_now_iso(),
                        "output_summary": "Workspace externo precisa de onboarding governado.",
                    }
                )
            )
            return self.store.save_run(run.model_copy(update={"status": "blocked", "warnings": self._append_unique(run.warnings, "external_workspace_onboarding_required"), "evidence_refs": self._append_unique(run.evidence_refs, "workflow:onboarding_required")}))
        if step.action_type == "tool_invoke" and step.tool_name:
            approved = self._approved_step_approval(run.workflow_run_id, step.step_id)
            tool_request = self._tool_request_for_step(run, plan, step, approval_id=approved.approval_id if approved else None)
            result = self.tool_gateway.invoke("aipinho", run.gateway_run_id or "", step.tool_name, tool_request)
            updated = step_result.model_copy(
                update={
                    "status": "waiting_for_approval" if result.status == "approval_required" else ("completed" if result.status == "succeeded" else result.status),
                    "policy_decision_id": result.policy_decision.policy_decision_id if result.policy_decision else None,
                    "approval_id": approved.approval_id if approved else None,
                    "output_summary": result.tool_invocation.output_summary_sanitized,
                    "artifacts": [artifact.artifact_id for artifact in result.artifacts],
                    "warnings": self._extend_unique(step_result.warnings, result.output.get("warnings", []) if isinstance(result.output, dict) else []),
                    "errors": self._extend_unique(step_result.errors, result.output.get("errors", []) if isinstance(result.output, dict) else []),
                    "evidence_refs": self._extend_unique(step_result.evidence_refs, result.tool_invocation.evidence_refs + result.events_emitted + (result.output.get("evidence_refs", []) if isinstance(result.output, dict) else [])),
                    "logs": result.events_emitted,
                    "completed_at": utc_now_iso(),
                    "metadata_sanitized": {
                        **step_result.metadata_sanitized,
                        "tool_invocation_id": result.tool_invocation.tool_invocation_id,
                        "tool_status": result.tool_invocation.status,
                    },
                }
            )
            self.store.save_step_result(updated)
            if result.status == "approval_required":
                approval = self._create_step_approval(
                    run,
                    plan,
                    step,
                    reason=result.policy_decision.human_reason if result.policy_decision else "Approval requerido pelo Tool Gateway.",
                    preview_id=result.output.get("preview_id") if isinstance(result.output, dict) else None,
                )
                self.store.save_step_result(updated.model_copy(update={"approval_id": approval.approval_id}))
                return self.store.save_run(
                    run.model_copy(
                        update={
                            "status": "waiting_for_approval",
                            "warnings": self._append_unique(run.warnings, "approval_required"),
                            "metadata_sanitized": {**run.metadata_sanitized, "pending_approval_id": approval.approval_id, "pending_step_id": step.step_id},
                            "policy_decision_ids": self._append_unique(run.policy_decision_ids, result.policy_decision.policy_decision_id if result.policy_decision else ""),
                        }
                    )
                )
            if result.status == "blocked":
                return self.store.save_run(
                    run.model_copy(
                        update={
                            "status": "blocked",
                            "artifact_ids": self._extend_unique(run.artifact_ids, [artifact.artifact_id for artifact in result.artifacts]),
                            "policy_decision_ids": self._append_unique(run.policy_decision_ids, result.policy_decision.policy_decision_id if result.policy_decision else ""),
                            "evidence_refs": self._extend_unique(run.evidence_refs, result.tool_invocation.evidence_refs + result.events_emitted),
                            "errors": self._append_unique(run.errors, result.tool_invocation.block_reason_code or "workflow_tool_blocked"),
                        }
                    )
                )
            if result.status == "failed":
                return self.store.save_run(
                    run.model_copy(
                        update={
                            "status": "failed",
                            "artifact_ids": self._extend_unique(run.artifact_ids, [artifact.artifact_id for artifact in result.artifacts]),
                            "policy_decision_ids": self._append_unique(run.policy_decision_ids, result.policy_decision.policy_decision_id if result.policy_decision else ""),
                            "evidence_refs": self._extend_unique(run.evidence_refs, result.tool_invocation.evidence_refs + result.events_emitted),
                            "errors": self._append_unique(run.errors, result.tool_invocation.error_code or "workflow_tool_failed"),
                        }
                    )
                )
            validation_ids = [result.validation_result.validation_id] if result.validation_result else []
            return self.store.save_run(
                run.model_copy(
                    update={
                        "artifact_ids": self._extend_unique(run.artifact_ids, [artifact.artifact_id for artifact in result.artifacts]),
                        "tool_invocation_ids": self._append_unique(run.tool_invocation_ids, result.tool_invocation.tool_invocation_id),
                        "policy_decision_ids": self._append_unique(run.policy_decision_ids, result.policy_decision.policy_decision_id if result.policy_decision else ""),
                        "validation_ids": self._extend_unique(run.validation_ids, validation_ids),
                        "evidence_refs": self._extend_unique(run.evidence_refs, result.tool_invocation.evidence_refs + result.events_emitted + (result.output.get("evidence_refs", []) if isinstance(result.output, dict) else [])),
                        "warnings": self._extend_unique(run.warnings, updated.warnings),
                        "errors": self._extend_unique(run.errors, updated.errors),
                    }
                )
            )
        if step.action_type == "validate":
            status = "completed" if run.evidence_refs and (plan.workflow_type != "bridge_provider_workflow" or self.store.list_step_results(workflow_run_id=run.workflow_run_id)) else "failed"
            self.store.save_step_result(
                step_result.model_copy(
                    update={
                        "status": status,
                        "completed_at": utc_now_iso(),
                        "output_summary": "Validacao do workflow consolidada." if status == "completed" else "Validacao falhou por falta de evidencias.",
                        "errors": [] if status == "completed" else ["workflow_validation_missing_evidence"],
                    }
                )
            )
            if status != "completed":
                return self.store.save_run(run.model_copy(update={"status": "validation_failed", "errors": self._append_unique(run.errors, "workflow_validation_missing_evidence")}))
            return self.store.save_run(run.model_copy(update={"validation_ids": self._append_unique(run.validation_ids, f"workflow_validation_{run.workflow_run_id}"), "evidence_refs": self._append_unique(run.evidence_refs, f"validation:workflow_validation_{run.workflow_run_id}")}))
        if step.action_type == "artifact_export":
            artifact = self._write_artifact(
                run,
                "workflow_step_results_snapshot.json",
                json.dumps([item.model_dump() for item in self.store.list_step_results(workflow_run_id=run.workflow_run_id)], indent=2, ensure_ascii=True),
                origin="workflow_artifact_export",
            )
            self.store.save_step_result(
                step_result.model_copy(
                    update={
                        "status": "completed",
                        "artifacts": [artifact["artifact_id"]],
                        "completed_at": utc_now_iso(),
                        "output_summary": "Artifacts consolidados do workflow registrados.",
                        "evidence_refs": self._append_unique(step_result.evidence_refs, f"artifact:{artifact['artifact_id']}"),
                    }
                )
            )
            return self.store.save_run(run.model_copy(update={"artifact_ids": self._append_unique(run.artifact_ids, artifact["artifact_id"]), "evidence_refs": self._append_unique(run.evidence_refs, f"artifact:{artifact['artifact_id']}")}))
        if step.action_type == "memory_extract":
            extraction = self.learning.extract(
                LearningExtractionRequest(
                    source_type="workflow_run",
                    source_id=run.workflow_run_id,
                    agent_id=run.initiating_agent_id,
                    session_id=run.session_id,
                    run_id=run.workflow_run_id,
                    project_id=run.project_profile_id,
                    skill_pack_id=plan.selected_skill_packs[0] if plan.selected_skill_packs else None,
                    outcome=run.status,
                    reusable_lessons=[{"type": "workflow_lesson", "title": "Workflow v2 executado com checkpoints", "summary": "Autopilot v2 preservou plano, checkpoints, evidencias e relatorio final.", "reusable_when": ["autopilot_v2", "workflow_execution"]}],
                    evidence_refs=[*run.evidence_refs, f"workflow:{run.workflow_run_id}"],
                )
            )
            self.store.save_step_result(
                step_result.model_copy(
                    update={
                        "status": "completed",
                        "completed_at": utc_now_iso(),
                        "output_summary": "Memory candidates gerados a partir do workflow.",
                        "evidence_refs": self._extend_unique(step_result.evidence_refs, extraction.trace_refs),
                    }
                )
            )
            return self.store.save_run(run.model_copy(update={"memory_candidate_ids": self._extend_unique(run.memory_candidate_ids, [candidate.candidate_id for candidate in extraction.candidates]), "evidence_refs": self._extend_unique(run.evidence_refs, extraction.trace_refs)}))
        self.store.save_step_result(
            step_result.model_copy(
                update={
                    "status": "completed",
                    "completed_at": utc_now_iso(),
                    "output_summary": f"Step {step.action_type} concluido sem side effect.",
                    "evidence_refs": self._append_unique(step_result.evidence_refs, f"step:{step.action_type}:{step.step_id}"),
                }
            )
        )
        return self.store.save_run(run.model_copy(update={"evidence_refs": self._append_unique(run.evidence_refs, f"step:{step.action_type}:{step.step_id}")}))

    def _create_approval(self, run: WorkflowRun, plan: WorkflowPlan) -> WorkflowApproval:
        approval = WorkflowApproval(
            workflow_run_id=run.workflow_run_id,
            workflow_id=run.workflow_id,
            reason="Workflow exige aprovacao antes de side effects de risco medio/alto.",
            risk_level=str(plan.risk_assessment.get("risk_level") or "medium"),
            evidence_refs=[*run.evidence_refs, f"workflow_plan:{plan.workflow_plan_id}"],
            metadata_sanitized={"approval_strategy": plan.approval_strategy},
        )
        return self.store.save_approval(approval)

    def _create_step_approval(self, run: WorkflowRun, plan: WorkflowPlan, step: WorkflowStep, *, reason: str, preview_id: str | None = None) -> WorkflowApproval:
        approval = WorkflowApproval(
            workflow_run_id=run.workflow_run_id,
            workflow_id=run.workflow_id,
            step_id=step.step_id,
            reason=reason,
            risk_level=step.risk_level,
            preview_id=preview_id,
            expected_side_effects=step.expected_outputs,
            validation_plan=plan.validation_strategy,
            rollback_plan=plan.recovery_strategy,
            evidence_refs=[*run.evidence_refs, *step.evidence_refs, f"workflow_step:{step.step_id}"],
            metadata_sanitized={"tool_name": step.tool_name, "provider_id": step.provider_id, "capability_id": step.capability_id},
        )
        return self.store.save_approval(approval)

    def _write_artifact(self, run: WorkflowRun, filename: str, content: str, *, origin: str) -> dict[str, Any]:
        session_id = run.gateway_session_id or run.session_id
        if not session_id:
            session = self.kernel.create_session("aipinho", AgentSessionCreateRequest(title=f"Workflow {run.workflow_run_id}"))
            session_id = session.session_id
        artifact = self.tool_gateway.upload_artifact(
            "aipinho",
            session_id,
            ArtifactUploadRequest(
                run_id=run.gateway_run_id,
                filename=filename,
                content=content,
                content_type="text/markdown" if filename.endswith(".md") else "application/json",
                encoding="text",
                origin=origin,
                metadata_sanitized={
                    "workflow_run_id": run.workflow_run_id,
                    "workflow_id": run.workflow_id,
                    "workflow_plan_id": run.workflow_plan_id,
                    "origin_type": "autopilot",
                    "evidence_refs": [*run.evidence_refs, f"workflow:{run.workflow_run_id}"],
                },
            ),
        )
        return {"artifact_id": artifact.artifact_id, "download_endpoint": artifact.download_endpoint}

    def _final_report(self, run: WorkflowRun, summary: str) -> WorkflowFinalReport:
        step_results = self.store.list_step_results(workflow_run_id=run.workflow_run_id)
        report = WorkflowFinalReport(
            workflow_run_id=run.workflow_run_id,
            workflow_id=run.workflow_id,
            status=run.status,
            summary=summary,
            step_result_ids=[item.step_result_id for item in step_results],
            artifact_ids=run.artifact_ids,
            validation_ids=run.validation_ids,
            memory_candidate_ids=run.memory_candidate_ids,
            warnings=run.warnings,
            errors=run.errors,
            evidence_refs=[*run.evidence_refs, f"workflow:{run.workflow_run_id}"],
        )
        artifact = self._write_artifact(run, "workflow_final_report.md", self._report_markdown(report), origin="autopilot")
        report = report.model_copy(update={"artifact_ids": self._append_unique(report.artifact_ids, artifact["artifact_id"]), "evidence_refs": self._append_unique(report.evidence_refs, f"artifact:{artifact['artifact_id']}")})
        return self.store.save_report(report)

    def _ensure_gateway_run(self, run: WorkflowRun, plan: WorkflowPlan) -> WorkflowRun:
        gateway_session_id = run.gateway_session_id
        if not gateway_session_id:
            session = self.kernel.create_session(
                "aipinho",
                AgentSessionCreateRequest(
                    title=plan.title or f"Workflow {run.workflow_run_id}",
                    project_profile_id=plan.project_profile_id,
                    metadata_sanitized={"workflow_run_id": run.workflow_run_id, "workflow_plan_id": plan.workflow_plan_id},
                ),
            )
            gateway_session_id = session.session_id
        gateway_run_id = run.gateway_run_id
        if not gateway_run_id:
            gateway_run = self.kernel.create_run(
                "aipinho",
                gateway_session_id,
                AgentRunCreateRequest(
                    operation_type=f"workflow:{plan.workflow_type}",
                    status="running",
                    workspace_id=plan.target_workspace_id or plan.source_workspace_id,
                    project_profile_id=plan.project_profile_id,
                    capabilities_requested=[step.capability_id for phase in plan.phases for step in phase.steps if step.capability_id],
                    metadata_sanitized={
                        "workflow_run_id": run.workflow_run_id,
                        "workflow_plan_id": plan.workflow_plan_id,
                        "workflow_id": plan.workflow_id,
                    },
                ),
            )
            gateway_run_id = gateway_run.run_id
        return run.model_copy(update={"gateway_session_id": gateway_session_id, "gateway_run_id": gateway_run_id})

    def _latest_step_result(self, workflow_run_id: str, step_id: str) -> WorkflowStepResult | None:
        items = self.store.list_step_results(workflow_run_id=workflow_run_id, step_id=step_id)
        return items[-1] if items else None

    def _approved_step_approval(self, workflow_run_id: str, step_id: str) -> WorkflowApproval | None:
        approvals = [item for item in self.store.list_approvals(workflow_run_id=workflow_run_id) if item.step_id == step_id and item.status == "approved"]
        return approvals[-1] if approvals else None

    def _tool_request_for_step(self, run: WorkflowRun, plan: WorkflowPlan, step: WorkflowStep, *, approval_id: str | None) -> ToolInvocationCreateRequest:
        metadata = dict(step.input_sanitized.get("metadata") or {})
        metadata.update(
            {
                "workflow_id": run.workflow_id or plan.workflow_id or plan.workflow_plan_id,
                "workflow_run_id": run.workflow_run_id,
                "workflow_step_id": step.step_id,
                "workflow_phase_id": step.phase_id,
                "workflow_checkpoint_id": run.checkpoint_ids[-1] if run.checkpoint_ids else "",
                "source_scope": step.source_scope,
            }
        )
        payload = dict(step.input_sanitized)
        trace_id = f"workflow_trace_{run.workflow_run_id}_{step.step_id}"
        if step.tool_name and step.tool_name.startswith("pinhoforge_android_"):
            payload.update(
                {
                    "session_id": run.gateway_session_id,
                    "run_id": run.gateway_run_id,
                    "trace_id": trace_id,
                    "caller_agent_id": run.initiating_agent_id,
                    "source_scope": step.source_scope,
                    "workspace_ref": plan.workspace_ref,
                    "metadata": metadata,
                }
            )
        elif step.tool_name and step.tool_name.startswith("pinhoforge_terminal_"):
            payload.update(
                {
                    "session_id": run.gateway_session_id,
                    "source_scope": step.source_scope,
                    "metadata": metadata,
                }
            )
            if approval_id and "approval_id" not in payload:
                payload["approval_id"] = approval_id
        elif step.tool_name and step.tool_name.startswith("pinhoforge_conversion_"):
            payload.update({"source_scope": step.source_scope, "metadata": metadata})
        elif (step.tool_name and step.tool_name.startswith("pinhoforge_hardware_")) or step.tool_name in {"pinhoforge_tool_availability_get", "pinhoforge_readiness_summary_get", "pinhoforge_environment_report_export"}:
            payload.update(
                {
                    "session_id": run.gateway_session_id,
                    "run_id": run.gateway_run_id,
                    "trace_id": trace_id,
                    "caller_agent_id": run.initiating_agent_id,
                    "metadata": metadata,
                }
            )
        elif step.tool_name and step.tool_name.startswith("pinhoforge_media_"):
            payload.update(
                {
                    "session_id": run.gateway_session_id,
                    "run_id": run.gateway_run_id,
                    "trace_id": trace_id,
                    "caller_agent_id": run.initiating_agent_id,
                    "source_scope": step.source_scope,
                    "metadata": metadata,
                }
            )
        return ToolInvocationCreateRequest(
            operation_type=step.operation or step.action_type,
            workspace_id=plan.target_workspace_id or plan.source_workspace_id,
            project_profile_id=plan.project_profile_id,
            requesting_agent_id=run.initiating_agent_id,
            approval_id=approval_id,
            input=payload,
            metadata_sanitized={
                "workflow_id": run.workflow_id,
                "workflow_run_id": run.workflow_run_id,
                "workflow_step_id": step.step_id,
                "provider_id": step.provider_id,
                "tool_name": step.tool_name,
            },
        )

    def _plan_markdown(self, plan: WorkflowPlan) -> str:
        return "\n".join([
            f"# WorkflowPlan {plan.workflow_plan_id}",
            f"- Tipo: {plan.workflow_type}",
            f"- Modo: {plan.mode}",
            f"- Objetivo: {plan.user_goal}",
            f"- Source scope: {plan.source_scope}",
            f"- Workspace ref: {plan.workspace_ref or 'nenhum'}",
            f"- Skill packs: {', '.join(plan.selected_skill_packs) or 'nenhum'}",
            f"- Outputs esperados: {', '.join(plan.expected_outputs) or 'nenhum'}",
            f"- Approvals: {', '.join(plan.approval_strategy) or 'nenhum'}",
            f"- Risco: {plan.risk_assessment.get('risk_level', 'unknown')}",
            "## Fases",
            *[f"- {phase.index}. {phase.name}: {phase.objective}" for phase in plan.phases],
        ])

    def _report_markdown(self, report: WorkflowFinalReport) -> str:
        return "\n".join([
            f"# Workflow Final Report {report.workflow_run_id}",
            f"- Status: {report.status}",
            f"- Resumo: {report.summary}",
            f"- Step results: {', '.join(report.step_result_ids) or 'nenhum'}",
            f"- Artifacts: {', '.join(report.artifact_ids) or 'nenhum'}",
            f"- Validations: {', '.join(report.validation_ids) or 'nenhuma'}",
            f"- Memory candidates: {', '.join(report.memory_candidate_ids) or 'nenhum'}",
            f"- Warnings: {', '.join(report.warnings) or 'nenhum'}",
            f"- Errors: {', '.join(report.errors) or 'nenhum'}",
            f"- Evidence: {', '.join(report.evidence_refs) or 'nenhuma'}",
        ])

    def _require_run(self, workflow_run_id: str) -> WorkflowRun:
        run = self.store.get_run(workflow_run_id)
        if run is None:
            raise FileNotFoundError(workflow_run_id)
        return run

    def _require_plan(self, workflow_plan_id: str) -> WorkflowPlan:
        plan = self.store.get_plan(workflow_plan_id)
        if plan is None:
            raise FileNotFoundError(workflow_plan_id)
        return plan

    def _append_unique(self, values: list[str], value: str) -> list[str]:
        return values if not value or value in values else [*values, value]

    def _extend_unique(self, values: list[str], additions: list[str]) -> list[str]:
        result = list(values)
        for value in additions:
            if value and value not in result:
                result.append(value)
        return result
