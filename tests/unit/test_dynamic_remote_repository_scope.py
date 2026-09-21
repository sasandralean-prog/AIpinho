from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.governance.intent_remote_repository_service import IntentRemoteRepositoryService
from aipinho.services.policy_kernel.remote_repository_identity_service import RemoteRepositoryIdentityService
from aipinho.services.policy_kernel.remote_repository_scope_service import RemoteRepositoryScopeService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService


REPO_A_HTTPS = "https://code.example.test/team/alpha-app.git"
REPO_A_SSH = "git@code.example.test:team/alpha-app.git"
REPO_B = "https://code.example.test/team/beta-app.git"


def _resolution_prompt() -> str:
    return (
        f"Investigue e corrija o workspace usando repository {REPO_A_HTTPS}. "
        "Branch main. Depois faca git fetch, git commit e git push. "
        f"Do not use repository {REPO_B}. "
        r"Nao inicialize um repositorio em C:\Temp\scratch."
    )


def test_equivalent_https_and_ssh_urls_normalize_to_same_identity() -> None:
    identities = RemoteRepositoryIdentityService()
    left = identities.normalize(REPO_A_HTTPS)
    right = identities.normalize(REPO_A_SSH)

    assert left.normalized_identity == right.normalized_identity
    assert left.normalized_locator == right.normalized_locator
    assert left.host == "code.example.test"


def test_semantic_ingress_compiles_positive_negative_repo_and_branch_scope() -> None:
    decision = SemanticIntentResolutionService().resolve(
        _resolution_prompt(), source_channel="unit"
    )

    assert len(decision.remote_resources) == 2
    allowed = next(item for item in decision.remote_resources if item.role == "remote_allowed")
    denied = next(item for item in decision.remote_resources if item.role == "remote_denied")
    assert allowed.allowed_branches == ["main"]
    assert {"git_fetch", "git_commit", "git_push"} <= set(allowed.permissions)
    assert denied.permissions == []
    assert any(item.kind == "git_init" and item.effect == "deny" for item in decision.mission_constraints)



def test_remote_scope_recognizes_clean_copy_fetch_and_fast_forward_language() -> None:
    prompt = (
        f"Use repository {REPO_A_HTTPS} branch main. "
        "Obtenha uma copia Git limpa. "
        "Atualize main com fetch + fast-forward seguro. "
        "Depois faca git commit e git push."
    )

    resources = IntentRemoteRepositoryService().resolve(prompt).resources
    allowed = next(item for item in resources if item.role == "remote_allowed")

    assert {
        "git_clone",
        "git_fetch",
        "git_pull_ff",
        "git_commit",
        "git_push",
    } <= set(allowed.permissions)



def test_authority_gap_preserves_only_ungranted_git_staging_operations() -> None:
    prompt = (
        "AUTORIZACAO: Autorizo nesta missao leitura, diagnostico, edicao de codigo, "
        "criacao/alteracao de testes, execucao de build/test, git commit e git push. "
        r"WORKSPACE ALVO: C:\Work\TargetApp. "
        "Investigue e corrija estruturalmente o codigo no workspace alvo. "
        f"REPOSITORIO CANONICO: {REPO_A_HTTPS} branch main. "
        "Para promocao final, obtenha uma copia Git limpa e atualize main com "
        "fetch + fast-forward seguro. Depois faca git commit e git push. "
        "Nao versione caches ou artefatos transitorios."
    )

    decision = SemanticIntentResolutionService().resolve(
        prompt,
        source_channel="unit",
        workspace_hint=r"C:\Work\TargetApp",
    )

    gap = set(decision.requested_capabilities) - set(
        decision.authorized_capabilities
    )
    assert gap == {
        "git_clone",
        "git_fetch",
        "git_pull_ff",
    }
    assert "artifact_create" not in decision.requested_capabilities
    assert "create_directory" not in decision.requested_capabilities
    assert "create_file" in decision.authorized_capabilities
    assert "shell_readonly" in decision.authorized_capabilities


def test_remote_scope_gate_allows_declared_push_after_identity_reobservation() -> None:
    resources = IntentRemoteRepositoryService().resolve(_resolution_prompt()).resources
    decision = RemoteRepositoryScopeService().decide(
        remote_resources=resources,
        repository_locator=REPO_A_HTTPS,
        branch="main",
        operation="git_push",
        observed_repository_locator=REPO_A_SSH,
    )

    assert decision.status == "allowed"
    assert decision.reason_code == "remote_scope_allows_operation"


def test_remote_scope_gate_requires_reobservation_before_push() -> None:
    resources = IntentRemoteRepositoryService().resolve(_resolution_prompt()).resources
    decision = RemoteRepositoryScopeService().decide(
        remote_resources=resources,
        repository_locator=REPO_A_HTTPS,
        branch="main",
        operation="git_push",
    )

    assert decision.status == "needs_clarification"
    assert decision.reason_code == "remote_identity_reobservation_required"


def test_remote_scope_gate_rejects_different_repo_wrong_branch_and_negative_repo() -> None:
    resources = IntentRemoteRepositoryService().resolve(_resolution_prompt()).resources
    gate = RemoteRepositoryScopeService()

    different = gate.decide(
        remote_resources=resources,
        repository_locator="https://code.example.test/team/gamma-app.git",
        branch="main",
        operation="git_fetch",
    )
    wrong_branch = gate.decide(
        remote_resources=resources,
        repository_locator=REPO_A_HTTPS,
        branch="dev",
        operation="git_fetch",
    )
    negative = gate.decide(
        remote_resources=resources,
        repository_locator=REPO_B,
        branch="main",
        operation="git_fetch",
    )

    assert different.reason_code == "remote_repository_not_declared"
    assert wrong_branch.reason_code == "remote_branch_not_allowed"
    assert negative.reason_code == "remote_repository_explicitly_denied"


def test_global_network_policy_and_secret_material_override_prompt_scope() -> None:
    service = IntentRemoteRepositoryService()
    denied_host_resources = service.resolve(
        "Use repository https://169.254.169.254/team/app.git branch main and git fetch."
    ).resources
    secret_resources = service.resolve(
        "Use repository https://TOKEN_VALUE@github.com/example/app.git branch main and git fetch."
    ).resources
    gate = RemoteRepositoryScopeService()

    host = gate.decide(
        remote_resources=denied_host_resources,
        repository_locator="https://169.254.169.254/team/app.git",
        branch="main",
        operation="git_fetch",
    )
    secret = gate.decide(
        remote_resources=secret_resources,
        repository_locator="https://github.com/example/app.git",
        branch="main",
        operation="git_fetch",
    )

    assert host.reason_code == "remote_repository_host_denied"
    assert secret.reason_code == "remote_repository_secret_material_detected"
    assert all("TOKEN_VALUE" not in (item.locator or "") for item in secret_resources)


def _mission_contract_from_prompt(prompt: str):
    decision = SemanticIntentResolutionService().resolve(prompt, source_channel="unit")
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        workspace=str(Path.cwd()),
        contract_type="analysis_readonly",
        operation_type="project_analysis",
        runtime_profile="readonly_analysis",
        capabilities_required=["read_workspace"],
        intent_map={
            "intent_type": decision.intent_type,
            "raw_prompt": prompt,
            "mission_execution_strategy": {"mode": decision.mission_execution_mode},
            "local_resources": [item.model_dump(mode="json") for item in decision.local_resources],
            "remote_resources": [item.model_dump(mode="json") for item in decision.remote_resources],
            "negative_constraints": [item.model_dump(mode="json") for item in decision.mission_constraints],
        },
    )
    return MissionContractService().compile_from_request(request)


def test_remote_scope_is_frozen_into_mission_contract() -> None:
    contract = _mission_contract_from_prompt(_resolution_prompt())
    allowed = next(item for item in contract.remote_resources if item.role == "remote_allowed")

    assert allowed.normalized_identity == "code.example.test/team/alpha-app"
    assert allowed.allowed_branches == ["main"]
    assert any(item.kind == "git_init" for item in contract.negative_constraints)
    assert MissionContractService().verify(contract) is True


def test_child_contract_may_narrow_remote_branch_but_not_expand_it() -> None:
    service = MissionContractService()
    parent = _mission_contract_from_prompt(
        "Use repository https://code.example.test/team/app.git branch main and branch release. Git fetch and git push."
    )
    resource = next(item for item in parent.remote_resources if item.role == "remote_allowed")
    narrowed = resource.model_copy(update={"allowed_branches": ["main"]})
    child = service.narrowed_child(parent, remote_resources=[narrowed])

    assert child.remote_resources[0].allowed_branches == ["main"]

    expanded = resource.model_copy(update={"allowed_branches": ["main", "release", "dev"]})
    try:
        service.narrowed_child(parent, remote_resources=[expanded])
    except ValueError as exc:
        assert str(exc) == "mission_contract_child_expands_resource_branches"
    else:
        raise AssertionError("branch expansion must be rejected")


def test_workspace_fix_discovery_freezes_remote_resources_into_first_taskrun(tmp_path: Path) -> None:
    from types import SimpleNamespace
    from aipinho.schemas.chat.chat_request import ChatRequest
    from aipinho.schemas.governance.lifecycle import CanonicalOperationContract, GovernanceLifecycleSnapshot
    from aipinho.services.orchestration.workspace_fix_discovery_service import WorkspaceFixDiscoveryService

    prompt = _resolution_prompt()
    intent = SemanticIntentResolutionService().resolve(
        prompt, source_channel="unit", workspace_hint=str(tmp_path)
    )
    snapshot = GovernanceLifecycleSnapshot(
        intent=intent,
        operation_contract=CanonicalOperationContract(operation_id="op_remote_discovery"),
    )

    class FakeRuntime:
        def __init__(self):
            self.request = None
            self.run = SimpleNamespace(run_id="task_run_aabbccdd")

        def create_run(self, request):
            self.request = request
            return self.run

        def start(self, _run_id):
            return self.run, SimpleNamespace(status="completed")

    runtime = FakeRuntime()
    WorkspaceFixDiscoveryService(runtime=runtime).execute(
        request=ChatRequest(message=prompt, session_id="remote_discovery"),
        snapshot=snapshot,
        workspace=str(tmp_path),
        source_channel="unit",
    )

    assert runtime.request is not None
    assert (
        runtime.request.intent_map["requested_capabilities"]
        == intent.requested_capabilities
    )
    frozen = runtime.request.intent_map["remote_resources"]
    assert len(frozen) == 2
    allowed = next(item for item in frozen if item["role"] == "remote_allowed")
    assert allowed["normalized_identity"] == "code.example.test/team/alpha-app"
    assert allowed["allowed_branches"] == ["main"]
    assert runtime.request.intent_map["negative_constraints"]


def test_multi_repository_scope_does_not_cross_grant_branch_or_operation() -> None:
    prompt = (
        f"Git fetch de {REPO_A_HTTPS} branch main. "
        f"Git push para {REPO_B} branch release."
    )
    resources = IntentRemoteRepositoryService().resolve(prompt).resources
    allowed = {item.normalized_identity: item for item in resources if item.role == "remote_allowed"}

    repo_a = allowed["code.example.test/team/alpha-app"]
    repo_b = allowed["code.example.test/team/beta-app"]
    assert repo_a.allowed_branches == ["main"]
    assert repo_a.permissions == ["git_fetch"]
    assert repo_b.allowed_branches == ["release"]
    assert repo_b.permissions == ["git_push"]


def test_remote_scope_requires_branch_scope_and_runtime_branch() -> None:
    no_branch = IntentRemoteRepositoryService().resolve(
        f"Use repository {REPO_A_HTTPS} e faca git fetch."
    ).resources
    scoped = IntentRemoteRepositoryService().resolve(
        f"Use repository {REPO_A_HTTPS} branch main e faca git fetch."
    ).resources
    gate = RemoteRepositoryScopeService()
    missing_scope = gate.decide(
        remote_resources=no_branch,
        repository_locator=REPO_A_HTTPS,
        branch="main",
        operation="git_fetch",
    )
    missing_runtime_branch = gate.decide(
        remote_resources=scoped,
        repository_locator=REPO_A_HTTPS,
        branch=None,
        operation="git_fetch",
    )

    assert missing_scope.status == "needs_clarification"
    assert missing_scope.reason_code == "remote_branch_scope_missing"
    assert missing_runtime_branch.status == "needs_clarification"
    assert missing_runtime_branch.reason_code == "remote_branch_required"
