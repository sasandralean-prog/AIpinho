from __future__ import annotations

import json
import os
import re
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.continuous_runtime import ContinuousRuntimeCycle
from aipinho.schemas.runtime.engineering_autopilot import (
    DecisionLogEntry,
    EngineeringMission,
    MissionApproval,
    MissionCheckpoint,
    MissionDashboard,
    MissionReport,
    MissionResume,
    MissionReview,
)
from aipinho.schemas.runtime.task_run import TaskRun


class EngineeringAutopilotService:
    def __init__(self, root: Path | None = None) -> None:
        configured = os.getenv("AIPINHO_ENGINEERING_MISSION_ROOT")
        self.root = root or (Path(configured) if configured else PATHS.project_root / "data" / "runtime" / "engineering_missions")
        self.root.mkdir(parents=True, exist_ok=True)

    def create_mission(self, *, objective: str, session_id: str | None = None, workspace: str | None = None) -> EngineeringMission:
        mission = EngineeringMission(objective=objective, session_id=session_id, workspace=workspace)
        mission.lifecycle.checkpoints.append(
            MissionCheckpoint(
                stage="planning",
                status="planned",
                summary="Mission created under governed autopilot supervision.",
            )
        )
        mission.decision_log.append(
            DecisionLogEntry(
                reason="mission_created",
                evidence=[{"type": "mission", "ref_id": mission.mission_id}],
                alternatives=["manual_single_prompt", "governed_mission"],
                chosen_option="governed_mission",
                rejected_options=["manual_single_prompt"],
                impact="Mission state becomes auditable.",
                risk="low",
                rollback="archive_mission",
                worker="PlannerWorker",
                contracts=["EngineeringMission"],
                capabilities=["planning"],
                validation="mission_contract_created",
            )
        )
        mission.dashboard = self.dashboard(mission)
        self.save(mission)
        return mission

    def attach_run(self, mission: EngineeringMission, run: TaskRun, cycle: ContinuousRuntimeCycle) -> EngineeringMission:
        if run.run_id not in mission.run_ids:
            mission.run_ids.append(run.run_id)
        status = self._mission_status_from_cycle(cycle)
        mission.lifecycle.status = status
        mission.lifecycle.current_stage = cycle.current_stage
        mission.lifecycle.checkpoints.append(
            MissionCheckpoint(
                stage=cycle.current_stage,
                status=status,
                summary=f"Attached run {run.run_id}; continuous runtime status is {cycle.status}.",
                run_id=run.run_id,
                evidence_refs=[
                    {"type": "task_run", "ref_id": run.run_id},
                    {"type": "continuous_cycle", "ref_id": cycle.cycle_id},
                ],
            )
        )
        if cycle.status == "needs_approval":
            mission.approvals.append(
                MissionApproval(
                    approval_id=cycle.approval_id,
                    status="pending",
                    reason=cycle.reason_code,
                    required_for=[run.operation_type or run.contract_type or "runtime_execution"],
                )
            )
        mission.decision_log.append(self._decision_log_from_run(run, cycle))
        mission.reviews.append(self.review(mission))
        mission.reports.append(self.report(mission))
        mission.dashboard = self.dashboard(mission)
        self.save(mission)
        return mission

    def review(self, mission: EngineeringMission) -> MissionReview:
        if mission.lifecycle.status == "blocked":
            return MissionReview(status="failed", summary="Mission is blocked.", findings=["blocked_runtime"])
        if mission.lifecycle.status in {"waiting_approval", "waiting_user"}:
            return MissionReview(status="warning", summary="Mission requires operator input.", findings=[mission.lifecycle.status])
        if mission.lifecycle.status == "completed":
            return MissionReview(status="passed", summary="Mission completed with governed evidence.")
        return MissionReview(status="warning", summary="Mission can continue.", findings=["continue_runtime"])

    def resume(self, mission: EngineeringMission) -> MissionResume:
        next_action = {
            "planned": "create_or_attach_task_run",
            "running": "continue_runtime",
            "waiting_approval": "wait_for_approval",
            "waiting_user": "wait_for_user",
            "blocked": "surface_block_reason",
            "completed": "publish_report",
        }.get(mission.lifecycle.status, "inspect_mission")
        return MissionResume(
            mission_id=mission.mission_id,
            status=mission.lifecycle.status,
            current_stage=mission.lifecycle.current_stage,
            next_action=next_action,
            checkpoint_count=len(mission.lifecycle.checkpoints),
        )

    def report(self, mission: EngineeringMission) -> MissionReport:
        evidence_refs = [{"type": "mission_checkpoint", "ref_id": checkpoint.checkpoint_id} for checkpoint in mission.lifecycle.checkpoints]
        return MissionReport(
            mission_id=mission.mission_id,
            status=mission.lifecycle.status,
            summary=f"Mission {mission.mission_id} is {mission.lifecycle.status} at {mission.lifecycle.current_stage}.",
            run_ids=list(mission.run_ids),
            evidence_refs=evidence_refs,
        )

    def dashboard(self, mission: EngineeringMission) -> MissionDashboard:
        return MissionDashboard(
            mission_id=mission.mission_id,
            status=mission.lifecycle.status,
            current_stage=mission.lifecycle.current_stage,
            total_checkpoints=len(mission.lifecycle.checkpoints),
            run_count=len(mission.run_ids),
            pending_approval_count=sum(1 for approval in mission.approvals if approval.status == "pending"),
            blocked_count=1 if mission.lifecycle.status == "blocked" else 0,
            evidence_count=sum(len(entry.evidence) for entry in mission.decision_log),
        )

    def save(self, mission: EngineeringMission) -> None:
        path = self._path_for_mission(mission.mission_id)
        path.write_text(json.dumps(mission.model_dump(mode="json"), ensure_ascii=True, indent=2), encoding="utf-8")

    def get(self, mission_id: str) -> EngineeringMission | None:
        path = self._path_for_mission(mission_id)
        if not path.exists():
            return None
        return EngineeringMission.model_validate_json(path.read_text(encoding="utf-8"))

    def _decision_log_from_run(self, run: TaskRun, cycle: ContinuousRuntimeCycle) -> DecisionLogEntry:
        worker = None
        contracts: list[str] = []
        capabilities: list[str] = []
        if run.execution_graph and run.execution_graph.nodes:
            first_node = run.execution_graph.nodes[0]
            worker = first_node.worker
            contracts = list(first_node.contracts)
            capabilities = list(first_node.capabilities)
        return DecisionLogEntry(
            reason=cycle.reason_code or "continuous_runtime_evaluated",
            evidence=[
                {"type": "task_run", "ref_id": run.run_id},
                {"type": "continuous_cycle", "ref_id": cycle.cycle_id},
            ],
            alternatives=["continue", "request_approval", "request_user", "block", "complete"],
            chosen_option=cycle.status,
            rejected_options=[option for option in ["continue", "request_approval", "request_user", "block", "complete"] if option != cycle.status],
            impact=f"Mission lifecycle moved to {cycle.status}.",
            risk="medium" if cycle.status in {"continue", "needs_approval"} else "low",
            rollback="resume_from_last_checkpoint",
            worker=worker,
            contracts=contracts,
            capabilities=capabilities,
            validation=cycle.reason_code or cycle.status,
        )

    def _mission_status_from_cycle(self, cycle: ContinuousRuntimeCycle) -> str:
        return {
            "continue": "running",
            "completed": "completed",
            "needs_approval": "waiting_approval",
            "needs_user": "waiting_user",
            "blocked": "blocked",
        }[cycle.status]

    def _path_for_mission(self, mission_id: str) -> Path:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", mission_id)
        return self.root / f"{safe_id}.json"
