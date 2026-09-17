from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.governance.intent_human_authority_service import IntentHumanAuthorityService
from aipinho.services.policy_kernel.authority_grant_service import AuthorityGrantService
from aipinho.services.runtime.mission_contract_service import MissionContractService


def _evidence(prompt: str, capabilities: list[str]):
    return IntentHumanAuthorityService().resolve(
        prompt=prompt,
        known_capabilities=capabilities,
    )


def _contract(tmp_path: Path, *, authorized: bool = True):
    target = tmp_path / "target"
    target.mkdir(exist_ok=True)
    prompt = (
        "AUTORIZACAO: Autorizo nesta missao edicao de codigo e criacao de arquivos."
        if authorized
        else "Edite o codigo e crie arquivos conforme necessario."
    )
    capabilities = ["modify_file", "create_file"]
    resolved = _evidence(prompt, capabilities)
    resource = MissionResourceScope(
        resource_id="resource_target",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(target),
        permissions=capabilities,
        provenance_refs=["test_prompt_scope"],
    )
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id="session_m4",
        source_message_id="msg_m4_authority",
        workspace=str(target),
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        runtime_profile="write_file",
        capabilities_required=["write_workspace"],
        requested_actions=["write_files"],
        intent_map={
            "intent_type": "workspace_fix_request",
            "raw_prompt": prompt,
            "requested_capabilities": capabilities,
            "authorized_capabilities": resolved.authorized_capabilities,
            "authority_evidence": resolved.evidence,
            "local_resources": [resource.model_dump(mode="json")],
        },
    )
    return target, MissionContractService().compile_from_request(request)


def test_requested_capability_is_not_explicit_authority() -> None:
    service = IntentHumanAuthorityService()
    requested = service.resolve(
        prompt="Faca git push quando a validacao terminar.",
        known_capabilities=["git_push"],
    )
    conditional = service.resolve(
        prompt="Se o git push falhar, preserve o commit local.",
        known_capabilities=["git_push"],
    )
    explicit = service.resolve(
        prompt="AUTORIZACAO: Autorizo git push nesta missao.",
        known_capabilities=["git_push"],
    )

    assert requested.requested_capabilities == ["git_push"]
    assert requested.authorized_capabilities == []
    assert conditional.authorized_capabilities == []
    assert explicit.authorized_capabilities == ["git_push"]
    assert explicit.evidence and explicit.evidence[0]["kind"] == "explicit_human_authorization"


def test_mission_contract_rejects_authority_without_prompt_evidence(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    prompt = "Autorizo edicao de codigo nesta missao."
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        workspace=str(target),
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        runtime_profile="write_file",
        intent_map={
            "raw_prompt": prompt,
            "requested_capabilities": ["modify_file"],
            "authorized_capabilities": ["modify_file"],
            "local_resources": [{
                "resource_id": "resource_target",
                "resource_type": "local_workspace",
                "role": "target_mutable",
                "locator": str(target),
                "permissions": ["modify_file"],
            }],
        },
    )
    with pytest.raises(ValueError, match="mission_contract_authority_evidence_missing"):
        MissionContractService().compile_from_request(request)


def test_mission_grant_binds_scope_and_revocation(tmp_path: Path) -> None:
    target, contract = _contract(tmp_path, authorized=True)
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    grant = grants.ensure_mission_grant(contract)
    assert grant is not None and grant.status == "approved"

    inside = grants.decision_for_contract(
        contract,
        action="modify_file",
        path=str(target / "a.py"),
        resource_id="resource_target",
    )
    outside = grants.decision_for_contract(
        contract,
        action="modify_file",
        path=str(tmp_path / "outside.py"),
        resource_id="resource_target",
    )
    assert inside is not None and inside.reason_code == "grant_effective"
    assert outside is not None and outside.reason_code == "grant_path_out_of_scope"

    revoked = grants.revoke(grant.grant_id)
    assert revoked.status == "revoked"
    after = grants.decision_for_contract(contract, action="modify_file", path=str(target / "a.py"))
    assert after is not None and after.reason_code.startswith("grant_not_approved:revoked")


def test_single_use_grant_consumes_use_limit(tmp_path: Path) -> None:
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    grant = grants.create_pending(
        session_id="session",
        workspace_id=None,
        workspace_path=None,
        actions=["modify_file"],
        scope="single_use",
        max_uses=1,
    )
    assert grants.approve(grant.grant_id).status == "approved"
    first = grants.consume(grant.grant_id, action="modify_file")
    second = grants.consume(grant.grant_id, action="modify_file")
    assert first.reason_code == "grant_consumed"
    assert first.grant.used_count == 1
    assert second.reason_code == "grant_not_approved:expired"


def test_task_run_guard_accepts_explicit_mission_authority_without_second_approval(tmp_path: Path) -> None:
    from aipinho.services.runtime.task_run_guard import TaskRunGuard
    from tests.support.runtime_fixtures import runtime_run

    target, contract = _contract(tmp_path, authorized=True)
    run = runtime_run(
        action="write_files",
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        runtime_profile="write_file",
        workspace=str(target),
        policy={
            "status": "needs_approval",
            "allowed_actions": ["write_files"],
            "denied_actions": [],
            "approval_required_for": ["write_files"],
        },
    )
    run.mission_contract = contract
    run.mission_binding = contract.binding()
    guard = TaskRunGuard(
        authority_grants=AuthorityGrantService(store_dir=tmp_path / "grants")
    )

    decision = guard.check_run(run)

    assert decision.allowed is True
    assert "approval_required" not in decision.blocked_reasons


def test_task_run_guard_still_requires_approval_without_explicit_authority(tmp_path: Path) -> None:
    from aipinho.services.runtime.task_run_guard import TaskRunGuard
    from tests.support.runtime_fixtures import runtime_run

    target, contract = _contract(tmp_path, authorized=False)
    run = runtime_run(
        action="write_files",
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        runtime_profile="write_file",
        workspace=str(target),
        policy={
            "status": "needs_approval",
            "allowed_actions": ["write_files"],
            "denied_actions": [],
            "approval_required_for": ["write_files"],
        },
    )
    run.mission_contract = contract
    run.mission_binding = contract.binding()
    decision = TaskRunGuard(
        authority_grants=AuthorityGrantService(store_dir=tmp_path / "grants")
    ).check_run(run)

    assert decision.allowed is False
    assert "approval_required" in decision.blocked_reasons


def test_tool_gateway_consumes_mission_authority_at_final_gate(tmp_path: Path) -> None:
    from aipinho.schemas.runtime.task_run import TaskRun
    from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
    from aipinho.services.runtime.task_run_store import TaskRunStore
    from tests.unit.test_dynamic_local_resource_runtime import _dynamic_gateway

    target, contract = _contract(tmp_path, authorized=True)
    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = TaskRun(
        run_id="task_run_a4a4a4a4",
        source_type="test",
        workspace=str(target),
        contract_type="filesystem_write",
        plan=TaskRunPlan(
            plan_id="plan_m4_gateway",
            contract_type="filesystem_write",
            steps=[],
        ),
        status="running",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    gateway.authority_grants = grants

    from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest

    result = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "create_file",
        ToolInvocationCreateRequest(
            path_ref=str(target / "authorized.txt"),
            input={"content": "ok"},
        ),
        task_run_id=task_run.run_id,
    )

    assert result.status == "succeeded"
    assert (target / "authorized.txt").read_text(encoding="utf-8") == "ok"
    grant = grants.ensure_mission_grant(contract)
    assert grant is not None
    assert grant.used_count == 1


def test_explicit_authorization_does_not_leak_into_later_conditional_sentence() -> None:
    service = IntentHumanAuthorityService()
    resolution = service.resolve(
        prompt=(
            "AUTORIZACAO: Autorizo leitura nesta missao. "
            "Se o git push falhar, preserve o commit local."
        ),
        known_capabilities=["read_file", "git_push"],
    )

    assert resolution.requested_capabilities == ["git_push", "read_file"]
    assert resolution.authorized_capabilities == ["read_file"]


def test_mission_authority_cannot_override_source_readonly_resource(tmp_path: Path) -> None:
    from aipinho.schemas.runtime.task_run import TaskRun
    from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
    from aipinho.services.runtime.task_run_store import TaskRunStore
    from tests.unit.test_dynamic_local_resource_runtime import _dynamic_gateway
    from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest

    source = tmp_path / "source"
    source.mkdir()
    prompt = "AUTORIZACAO: Autorizo nesta missao criacao de arquivos."
    resolved = _evidence(prompt, ["create_file"])
    request = TaskRunRequest(
        source_type="direct", source_channel="unit", workspace=str(source),
        contract_type="filesystem_write", operation_type="filesystem_write_file",
        runtime_profile="write_file",
        intent_map={
            "raw_prompt": prompt,
            "requested_capabilities": ["create_file"],
            "authorized_capabilities": resolved.authorized_capabilities,
            "authority_evidence": resolved.evidence,
            "local_resources": [{
                "resource_id": "resource_source",
                "resource_type": "local_workspace",
                "role": "source_readonly",
                "locator": str(source),
                "permissions": ["read_file", "create_file"],
            }],
        },
    )
    contract = MissionContractService().compile_from_request(request)
    task_store = TaskRunStore(root=tmp_path / "task_runs")
    task_run = TaskRun(
        run_id="task_run_b4b4b4b4",
        source_type="test",
        workspace=str(source),
        contract_type="filesystem_write",
        plan=TaskRunPlan(
            plan_id="plan_m4_readonly",
            contract_type="filesystem_write",
            steps=[],
        ),
        status="running",
        mission_contract=contract,
        mission_binding=contract.binding(),
    )
    task_store.create_run(task_run)
    gateway, agent_run = _dynamic_gateway(tmp_path, task_store)
    gateway.authority_grants = AuthorityGrantService(store_dir=tmp_path / "grants")
    result = gateway.invoke(
        "aipinho",
        agent_run.run_id,
        "create_file",
        ToolInvocationCreateRequest(
            path_ref=str(source / "blocked.txt"),
            input={"content": "no"},
        ),
        task_run_id=task_run.run_id,
    )

    assert result.status == "blocked"
    assert not (source / "blocked.txt").exists()


def test_mission_authority_cannot_override_globally_blocked_git_push(tmp_path: Path) -> None:
    from aipinho.services.runtime.task_run_guard import TaskRunGuard
    from tests.support.runtime_fixtures import runtime_run

    prompt = "AUTORIZACAO: Autorizo git push nesta missao."
    resolved = _evidence(prompt, ["git_push"])
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        contract_type="readonly_analysis",
        operation_type="project_analysis",
        runtime_profile="readonly_analysis",
        intent_map={
            "raw_prompt": prompt,
            "requested_capabilities": ["git_push"],
            "authorized_capabilities": resolved.authorized_capabilities,
            "authority_evidence": resolved.evidence,
            "remote_resources": [{
                "resource_id": "remote_example",
                "resource_type": "remote_repository",
                "role": "remote_allowed",
                "locator": "https://code.example.test/team/app.git",
                "provider": "code.example.test",
                "normalized_identity": "code.example.test/team/app",
                "allowed_branches": ["main"],
                "permissions": ["git_push"],
            }],
        },
    )
    contract = MissionContractService().compile_from_request(request)
    run = runtime_run(
        action="git_push",
        contract_type="in_chat_final_report",
        operation_type="project_analysis",
        runtime_profile="readonly_analysis",
        policy={
            "status": "needs_approval",
            "allowed_actions": ["git_push"],
            "denied_actions": [],
            "approval_required_for": ["git_push"],
        },
    )
    run.mission_contract = contract
    run.mission_binding = contract.binding()
    decision = TaskRunGuard(
        authority_grants=AuthorityGrantService(store_dir=tmp_path / "grants")
    ).check_run(run)

    assert decision.allowed is False
    assert "blocked_action:git_push" in decision.blocked_reasons


def test_mission_grant_enforces_remote_repository_and_branch_scope(tmp_path: Path) -> None:
    prompt = "AUTORIZACAO: Autorizo git push nesta missao."
    resolved = _evidence(prompt, ["git_push"])
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        contract_type="readonly_analysis",
        operation_type="workspace_fix_request",
        intent_map={
            "intent_type": "workspace_fix_request",
            "raw_prompt": prompt,
            "requested_capabilities": ["git_push"],
            "authorized_capabilities": resolved.authorized_capabilities,
            "authority_evidence": resolved.evidence,
            "remote_resources": [{
                "resource_id": "remote_allowed",
                "resource_type": "remote_repository",
                "role": "remote_allowed",
                "locator": "https://code.example.test/team/app.git",
                "provider": "code.example.test",
                "normalized_identity": "code.example.test/team/app",
                "allowed_branches": ["main"],
                "permissions": ["git_push"],
            }],
        },
    )
    contract = MissionContractService().compile_from_request(request)
    grants = AuthorityGrantService(store_dir=tmp_path / "grants")

    allowed = grants.decision_for_contract(
        contract,
        action="git_push",
        resource_id="remote_allowed",
        repository_identity="code.example.test/team/app",
        branch="main",
    )
    wrong_branch = grants.decision_for_contract(
        contract,
        action="git_push",
        resource_id="remote_allowed",
        repository_identity="code.example.test/team/app",
        branch="dev",
    )
    wrong_repo = grants.decision_for_contract(
        contract,
        action="git_push",
        resource_id="remote_allowed",
        repository_identity="code.example.test/team/other",
        branch="main",
    )

    assert allowed is not None and allowed.reason_code == "grant_effective"
    assert wrong_branch is not None and wrong_branch.reason_code == "grant_branch_out_of_scope"
    assert wrong_repo is not None and wrong_repo.reason_code == "grant_repository_out_of_scope"
