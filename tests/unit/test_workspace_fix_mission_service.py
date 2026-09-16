from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.orchestration.workspace_fix_mission_service import (
    WorkspaceFixMissionService,
)


class _ContinuousRuntime:
    def evaluate(self, run, *, objective=None):
        return SimpleNamespace(status="continue", current_stage="continuation", objective=objective)


class _Runtime:
    def __init__(self) -> None:
        self.requests = []
        self.continuous_runtime = _ContinuousRuntime()

    def create_run(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            run_id="task_run_discovery",
            task_id="task_discovery",
            operation_id=request.operation_id or "op_discovery",
            runtime_profile=request.runtime_profile,
            status="queued",
            operation_type=request.operation_type,
            contract_type=request.contract_type,
        )


class _Missions:
    def __init__(self) -> None:
        self.created = []

    def create_mission(self, *, objective, session_id=None, workspace=None):
        mission = SimpleNamespace(
            mission_id="engineering_mission_discovery",
            objective=objective,
            session_id=session_id,
            workspace=workspace,
        )
        self.created.append(mission)
        return mission

    def attach_run(self, mission, run, cycle):
        return SimpleNamespace(
            mission_id=mission.mission_id,
            lifecycle=SimpleNamespace(status="running"),
        )


def test_workspace_fix_discovery_creates_readonly_autorun_and_defers_future_effects() -> None:
    runtime = _Runtime()
    missions = _Missions()
    service = WorkspaceFixMissionService(runtime=runtime, missions=missions)
    original_graph = {
        "observational_intent": True,
        "mutation_intent": True,
        "execution_intent": True,
        "state_effect": "workspace_mutation",
        "requested_effects": ["workspace_mutation", "runtime_execution"],
        "evidence": ["compound_fix_request"],
    }

    started = service.start_discovery(
        request=ChatRequest(
            message="Analise, corrija e depois execute o build.",
            session_id="session_fix",
        ),
        workspace=r"C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop",
        source_channel="mobile_chat",
        operation_id="op_fix",
        mission_semantic_intent_graph=original_graph,
        mission_evidence=["future_side_effect_intent_deferred_until_discovery"],
    )

    assert started.mission_id == "engineering_mission_discovery"
    assert started.run.status == "queued"
    assert len(runtime.requests) == 1

    request = runtime.requests[0]
    assert request.contract_type == "analysis_readonly"
    assert request.operation_type == "project_analysis"
    assert request.runtime_profile == "readonly_analysis"
    assert request.requested_actions == ["read_files"]
    assert request.capabilities_required == ["read_workspace"]
    assert request.mode == "read_only"
    assert request.start_immediately is True
    assert request.approval_id is None

    phase_graph = request.intent_map["semantic_intent_graph"]
    assert phase_graph["readonly_contract"] is True
    assert phase_graph["mutation_intent"] is False
    assert phase_graph["execution_intent"] is False
    assert phase_graph["knowledge_output"] is False
    assert phase_graph["planning_intent"] is False
    assert phase_graph["state_effect"] == "knowledge_only"
    assert phase_graph["workspace_effect"] == "knowledge_only"
    assert phase_graph["filesystem_effect"] == "prohibited"
    assert phase_graph["runtime_effect"] == "none"

    assert request.intent_map["mission_semantic_intent_graph"] == original_graph
    assert request.intent_map["deferred_effects"] == [
        "workspace_mutation",
        "runtime_execution",
    ]
    assert request.intent_map["mission_id"] == "engineering_mission_discovery"
    assert request.intent_map["mission_execution_strategy"]["mode"] == "end_to_end_governed"
    assert request.intent_map["mission_continuation_policy"]["auto_continue"] is True
    assert request.intent_map["workspace_scope_contract"]["primary_workspace"].endswith(
        "PinhoabacaxiMusicasDesktop"
    )
