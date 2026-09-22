from __future__ import annotations

from types import SimpleNamespace

import pytest

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.governance.lifecycle import CanonicalIntentDecision
from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.semantic_runtime.mission_completion_requirements import (
    MissionCompletionRequirementEvidence,
    MissionCompletionRequirementResolution,
)
from aipinho.services.models.model_router_service import ModelRouterService
from aipinho.services.orchestration.workspace_fix_discovery_service import (
    MissionCompletionRequirementIngressError,
    WorkspaceFixDiscoveryService,
)
from aipinho.services.roles.role_model_binding_service import (
    RoleModelBindingService,
)
from aipinho.services.roles.role_registry_service import RoleRegistryService
from aipinho.services.runtime.mission_contract_service import (
    MissionContractService,
)
from aipinho.services.semantic_runtime.mission_completion_requirement_ingress_service import (
    MissionCompletionRequirementIngressService,
)


class _FakeReasoner:
    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = []

    def propose_json(self, **kwargs):
        self.calls.append(kwargs)
        candidate = (
            self.candidate(kwargs)
            if callable(self.candidate)
            else self.candidate
        )
        return {
            "status": "candidate",
            "candidate": candidate,
            "model_id": "fake-model",
            "response_id": f"fake-response-{len(self.calls)}",
            "real_inference": False,
            "evaluation_status": "accepted",
            "retry_attempts": 0,
            "warnings": [],
        }


def test_requirement_ingress_accepts_only_prompt_grounded_explicit_criteria() -> None:
    prompt = (
        "CRITERIO FINAL: a missao so termina com mudança concreta de código "
        "e push confirmado no repositorio. "
        "Antes disso, exige regressão validada e build aprovado."
    )
    reasoner = _FakeReasoner(
        {
            "requirements": [
                {
                    "kind": "completion",
                    "requirement": "concrete_code_change",
                    "evidence_id": "segment_0_evidence_0",
                    "confidence": 0.97,
                    "rationale": "Explicit final state.",
                },
                {
                    "kind": "completion",
                    "requirement": "push_confirmed",
                    "evidence_id": "segment_0_evidence_0",
                    "confidence": 0.95,
                    "rationale": "Explicit final state.",
                },
                {
                    "kind": "validation",
                    "requirement": "validated_regression",
                    "evidence_id": "segment_0_evidence_1",
                    "confidence": 0.96,
                    "rationale": "Explicit validation.",
                },
                {
                    "kind": "validation",
                    "requirement": "build_approved",
                    "evidence_id": "segment_0_evidence_1",
                    "rationale": "Explicit validation.",
                },
            ]
        }
    )
    service = MissionCompletionRequirementIngressService(
        reasoner=reasoner,  # type: ignore[arg-type]
    )

    result = service.resolve(prompt=prompt, enabled=True)

    assert result.status == "resolved"
    assert result.reason_code == "MISSION_COMPLETION_REQUIREMENTS_RESOLVED"
    assert result.completion_requirements == [
        "concrete_code_change",
        "push_confirmed",
    ]
    assert result.validation_requirements == [
        "validated_regression",
        "build_approved",
    ]
    assert result.allow_limited_completion is False
    assert len(result.evidence) == 4
    payload = reasoner.calls[0]["payload"]
    assert "prompt_segment" not in payload
    assert payload["evidence_units"] == [
        {
            "evidence_id": "segment_0_evidence_0",
            "text": (
                "CRITERIO FINAL: a missao so termina com mudança concreta de "
                "código e push confirmado no repositorio."
            ),
        },
        {
            "evidence_id": "segment_0_evidence_1",
            "text": "Antes disso, exige regressão validada e build aprovado.",
        },
    ]
    assert all(item.evidence_excerpt in prompt for item in result.evidence)
    assert any(
        item.requirement == "build_approved" and item.confidence == 1.0
        for item in result.evidence
    )
    assert result.provenance["reasoner_calls"] == 1
    assert all(
        ref.startswith("mission_completion_requirement:")
        for ref in result.provenance["evidence_refs"]
    )


def test_terminal_success_criterion_suppresses_procedural_false_positives() -> None:
    prompt = (
        "Rode git diff --check; faça commit e git push origin main. "
        "CRITÉRIO DE SUCESSO: a missão termina somente com mudança concreta "
        "de código, regressão validada e push confirmado."
    )

    def candidate(kwargs):
        units = kwargs["payload"]["evidence_units"]
        assert len(units) == 1
        assert "CRITÉRIO DE SUCESSO" in units[0]["text"]
        evidence_id = units[0]["evidence_id"]
        return {
            "requirements": [
                {"kind": "completion", "requirement": "code_changed", "evidence_id": evidence_id},
                {"kind": "validation", "requirement": "regression_validated", "evidence_id": evidence_id},
                {"kind": "completion", "requirement": "push_confirmed", "evidence_id": evidence_id},
            ]
        }

    reasoner = _FakeReasoner(candidate)
    result = MissionCompletionRequirementIngressService(
        reasoner=reasoner,  # type: ignore[arg-type]
    ).resolve(prompt=prompt, enabled=True)

    assert result.status == "resolved"
    assert result.completion_requirements == ["code_changed", "push_confirmed"]
    assert result.validation_requirements == ["regression_validated"]
    assert len(reasoner.calls) == 1
    assert all("git diff --check" not in item.evidence_excerpt for item in result.evidence)


def test_terminal_success_criterion_fails_closed_if_not_decomposed() -> None:
    result = MissionCompletionRequirementIngressService(
        reasoner=_FakeReasoner({"requirements": []}),  # type: ignore[arg-type]
    ).resolve(
        prompt="CRITÉRIO DE SUCESSO: a missão só termina com build validado.",
        enabled=True,
    )

    assert result.status == "invalid"
    assert result.reason_code == "MISSION_COMPLETION_TERMINAL_CRITERION_NOT_DECOMPOSED"


def test_requirement_ingress_rejects_model_evidence_not_present_in_prompt() -> None:
    reasoner = _FakeReasoner(
        {
            "requirements": [
                {
                    "kind": "completion",
                    "requirement": "invented_success",
                    "evidence_id": "segment_0_evidence_999",
                    "confidence": 0.99,
                    "rationale": "Invented.",
                }
            ]
        }
    )
    service = MissionCompletionRequirementIngressService(
        reasoner=reasoner,  # type: ignore[arg-type]
    )

    result = service.resolve(
        prompt="A missao exige um build validado.",
        enabled=True,
    )

    assert result.status == "invalid"
    assert (
        result.reason_code
        == "MISSION_COMPLETION_REQUIREMENT_EVIDENCE_NOT_IN_PROMPT"
    )


def test_requirement_ingress_distinguishes_no_requirements_from_unavailable() -> None:
    empty_reasoner = _FakeReasoner({"requirements": []})
    empty = MissionCompletionRequirementIngressService(
        reasoner=empty_reasoner,  # type: ignore[arg-type]
    ).resolve(
        prompt="Execute a tarefa end-to-end conforme a autoridade existente.",
        enabled=True,
    )
    assert empty.status == "resolved"
    assert (
        empty.reason_code
        == "MISSION_COMPLETION_REQUIREMENTS_NONE_EXPLICIT"
    )
    assert empty.completion_requirements == []
    assert empty.validation_requirements == []

    limited_reasoner = _FakeReasoner({"requirements": []})
    unavailable = MissionCompletionRequirementIngressService(
        reasoner=limited_reasoner,  # type: ignore[arg-type]
        max_segment_chars=1200,
        segment_overlap_chars=100,
        max_reasoner_calls=1,
    ).resolve(
        prompt=("criterio de missao " * 300),
        enabled=True,
    )
    assert unavailable.status == "unavailable"
    assert (
        unavailable.reason_code
        == "MISSION_COMPLETION_REQUIREMENT_CALL_LIMIT_EXCEEDED"
    )
    assert limited_reasoner.calls == []


def test_requirement_extractor_role_is_subordinate_and_routes_to_low_latency_model() -> None:
    role = RoleRegistryService().require_role(
        "mission_completion_requirement_extractor"
    )
    binding = RoleModelBindingService().get_binding(
        "mission_completion_requirement_extractor"
    )
    route = ModelRouterService().select_model(
        purpose="chat",
        role_id="mission_completion_requirement_extractor",
    )

    assert role.can_call_model is True
    assert role.can_call_tools is False
    assert role.can_execute_tools is False
    assert role.can_write is False
    assert role.can_patch is False
    assert role.can_approve is False
    assert binding is not None
    assert binding.primary_model == "qwen3_1_7b_q6_k"
    assert binding.max_latency_class == "low"
    assert binding.metadata["truth_authority"] is False
    assert route.status == "ok"
    assert route.model is not None
    assert route.model.model_id == "qwen3_1_7b_q6_k"


class _FakeCompletionIngress:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        return self.resolution


class _FakeRuntime:
    def __init__(self):
        self.request = None
        self.run = SimpleNamespace(run_id="task_run_a30")

    def create_run(self, request):
        self.request = request
        return self.run

    def start(self, run_id):
        assert run_id == self.run.run_id
        return self.run, SimpleNamespace(status="completed")


def _snapshot(tmp_path):
    target = tmp_path / "Target"
    target.mkdir()
    resource = MissionResourceScope(
        resource_id="workspace_target",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(target),
        permissions=["read_file", "modify_file"],
    )
    intent = CanonicalIntentDecision(
        intent_type="workspace_fix_request",
        operation_type="workspace_fix_request",
        requires_task=True,
        readonly=True,
        local_resources=[resource],
        mission_execution_mode="end_to_end_governed",
    )
    return (
        SimpleNamespace(
            intent=intent,
            operation_contract=SimpleNamespace(operation_id="op_a30"),
        ),
        target,
    )


def test_workspace_fix_ingress_freezes_resolved_requirements_into_mission_contract(
    tmp_path,
) -> None:
    snapshot, target = _snapshot(tmp_path)
    resolution = MissionCompletionRequirementResolution(
        status="resolved",
        reason_code="MISSION_COMPLETION_REQUIREMENTS_RESOLVED",
        completion_requirements=[
            "concrete_code_change",
            "push_confirmed",
        ],
        validation_requirements=["regression_validated"],
        evidence=[
            MissionCompletionRequirementEvidence(
                kind="completion",
                requirement="concrete_code_change",
                evidence_excerpt="mudança concreta de código",
                confidence=0.95,
                rationale="Explicit criterion.",
                segment_index=0,
            )
        ],
        provenance={
            "evidence_refs": [
                "mission_completion_requirement:abc123"
            ]
        },
    )
    runtime = _FakeRuntime()
    ingress = _FakeCompletionIngress(resolution)
    service = WorkspaceFixDiscoveryService(
        runtime=runtime,  # type: ignore[arg-type]
        completion_ingress=ingress,  # type: ignore[arg-type]
    )

    service.execute(
        request=ChatRequest(
            message=(
                "A missao exige mudança concreta de código, "
                "regressao validada e push confirmado."
            ),
            session_id="session_a30",
        ),
        snapshot=snapshot,  # type: ignore[arg-type]
        workspace=str(target),
        source_channel="unit",
    )

    assert runtime.request is not None
    intent_map = runtime.request.intent_map
    assert intent_map["completion_requirements"] == [
        "concrete_code_change",
        "push_confirmed",
    ]
    assert intent_map["validation_requirements"] == [
        "regression_validated"
    ]
    assert intent_map["allow_limited_completion"] is False
    contract = MissionContractService().compile_from_request(
        runtime.request
    )
    assert contract.completion.completion_requirements == [
        "concrete_code_change",
        "push_confirmed",
    ]
    assert contract.completion.validation_requirements == [
        "regression_validated"
    ]
    assert contract.semantic_context[
        "mission_completion_requirement_evidence"
    ][0]["requirement"] == "concrete_code_change"
    assert (
        "mission_completion_requirement:abc123"
        in contract.provenance_refs
    )


def test_workspace_fix_ingress_fails_closed_when_requirement_resolution_unavailable(
    tmp_path,
) -> None:
    snapshot, target = _snapshot(tmp_path)
    runtime = _FakeRuntime()
    ingress = _FakeCompletionIngress(
        MissionCompletionRequirementResolution(
            status="unavailable",
            reason_code="SEMANTIC_REASONER_MODEL_UNAVAILABLE",
        )
    )
    service = WorkspaceFixDiscoveryService(
        runtime=runtime,  # type: ignore[arg-type]
        completion_ingress=ingress,  # type: ignore[arg-type]
    )

    with pytest.raises(
        MissionCompletionRequirementIngressError
    ) as exc:
        service.execute(
            request=ChatRequest(
                message="Execute a missao end-to-end.",
                session_id="session_a30",
            ),
            snapshot=snapshot,  # type: ignore[arg-type]
            workspace=str(target),
            source_channel="unit",
        )

    assert exc.value.reason_code == "SEMANTIC_REASONER_MODEL_UNAVAILABLE"
    assert runtime.request is None
