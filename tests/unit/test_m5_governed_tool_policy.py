from __future__ import annotations

from pathlib import Path

from aipinho.schemas.governance.lifecycle import CanonicalPermission
from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.governance.intent_human_authority_service import (
    IntentHumanAuthorityService,
)
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.tools.governed_tool_execution_service import (
    GovernedToolExecutionService,
)


class _Completed:
    returncode = 0
    stdout = "ok\n"
    stderr = ""


def _runner(_argv, **kwargs):
    assert kwargs["shell"] is False
    return _Completed()

def _contract(target: Path, *, authorized: bool):
    prompt = (
        "AUTORIZACAO: Autorizo nesta missao a execucao de testes."
        if authorized
        else "Execute os testes desta missao."
    )
    capabilities = ["shell_test"]
    resolved = IntentHumanAuthorityService().resolve(
        prompt=prompt,
        known_capabilities=capabilities,
    )
    resource = MissionResourceScope(
        resource_id="resource_dynamic_target",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(target),
        permissions=["read_file", "shell_test"],
        provenance_refs=["m5_c2_test"],
    )
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id="session_m5_c2",
        source_message_id="msg_m5_c2",
        workspace=str(target),
        contract_type="shell",
        operation_type="test_run",
        runtime_profile="shell",
        capabilities_required=capabilities,
        requested_actions=["run_command"],
        intent_map={
            "intent_type": "workspace_fix_request",
            "raw_prompt": prompt,
            "requested_capabilities": capabilities,
            "authorized_capabilities": resolved.authorized_capabilities,
            "authority_evidence": resolved.evidence,
            "local_resources": [resource.model_dump(mode="json")],
        },
    )
    return MissionContractService().compile_from_request(request)


def _service(tmp_path: Path, contract, *, run_id: str):
    target = Path(contract.local_resources[0].locator)
    store = TaskRunStore(root=tmp_path / "task_runs")
    run = TaskRun(
        run_id=run_id,
        source_type="test",
        workspace=str(target),
        contract_type="shell",
        plan=TaskRunPlan(
            plan_id=f"plan_{run_id}",
            contract_type="shell",
            steps=[],
        ),
        status="running",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    store.create_run(run)
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    service = GovernedToolExecutionService(
        runner=_runner,
        task_runs=store,
        authority_grants=grants,
    )
    return service, run, grants


def _test_request(target: Path, run: TaskRun) -> ToolExecutionRequest:
    return ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        task_run_id=run.run_id,
        input={
            "workspace": str(target),
            "argv": ["pytest", "-q"],
        },
    )


def test_mission_authority_allows_dynamic_test_shell_without_second_approval(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    target.mkdir()
    contract = _contract(target, authorized=True)
    service, run, grants = _service(tmp_path, contract, run_id="task_run_c2a2a2a2")
    request = _test_request(target, run)

    preview = service.preview_decision(request)
    result = service.execute(request)

    assert preview["canonical_policy"]["permission"] == "allowed"
    assert preview["capability"] == "shell_test"
    assert result.status == "executed_governed"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.permission == CanonicalPermission.ALLOWED
    grant = grants.ensure_mission_grant(contract)
    assert grant is not None
    assert grant.used_count == 1


def test_dynamic_test_shell_without_authority_remains_canonical_ask(tmp_path: Path) -> None:
    target = tmp_path / "dynamic_target"
    target.mkdir()
    contract = _contract(target, authorized=False)
    service, run, _grants = _service(tmp_path, contract, run_id="task_run_c2b2b2b2")
    request = _test_request(target, run)

    preview = service.preview_decision(request)
    approval = service.request_approval(request)

    assert preview["canonical_policy"]["permission"] == "ask"
    assert preview["capability"] == "shell_test"
    assert approval["status"] == "approval_required"
    assert approval["approval"].status == "pending"


def test_ambiguous_git_and_network_shell_are_canonical_denied(tmp_path: Path) -> None:
    service = GovernedToolExecutionService(runner=_runner)
    workspace = r"C:\Dev\AIpinho"
    git_request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={"workspace": workspace, "argv": ["git", "push", "origin", "main"]},
    )
    network_request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={"workspace": workspace, "argv": ["curl", "https://example.com"]},
    )

    git_preview = service.preview_decision(git_request)
    network_preview = service.preview_decision(network_request)

    assert git_preview["canonical_policy"]["permission"] == "denied"
    assert network_preview["canonical_policy"]["permission"] == "denied"
    git_reasons = {
        item["reason_code"] for item in git_preview["canonical_policy"]["facets"]
    }
    network_reasons = {
        item["reason_code"] for item in network_preview["canonical_policy"]["facets"]
    }
    assert "git_write_requires_granular_classification" in git_reasons
    assert "network_shell_requires_granular_classification" in network_reasons


class _WebResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return b"network-ok"


def test_structured_web_request_remains_governed_not_globally_denied(tmp_path: Path) -> None:
    def opener(request, timeout):
        assert request.full_url == "https://example.com/health"
        assert request.method == "GET"
        assert timeout > 0
        return _WebResponse()

    service = GovernedToolExecutionService(opener=opener)
    request = ToolExecutionRequest(
        tool_id="web.request",
        mode="governed",
        input={"url": "https://example.com/health", "method": "GET"},
    )
    preview = service.preview_decision(request)
    approval = service.request_approval(request)["approval"]
    service.approvals.approve(approval.approval_id)
    result = service.execute(
        request.model_copy(update={"approval_id": approval.approval_id})
    )

    assert preview["canonical_policy"]["permission"] == "ask"
    assert preview["capability"] == "network_download"
    assert result.status == "executed_governed"
    assert result.content == "network-ok"
    assert result.canonical_policy_decision is not None
    assert result.canonical_policy_decision.permission == CanonicalPermission.ALLOWED
