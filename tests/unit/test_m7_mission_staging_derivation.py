from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from aipinho.schemas.runtime.mission_contract import MissionResourceScope
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.governance.intent_human_authority_service import IntentHumanAuthorityService
from aipinho.services.governance.intent_remote_repository_service import IntentRemoteRepositoryService
from aipinho.services.policy_kernel.mission_local_resource_scope_service import MissionLocalResourceScopeService
from aipinho.services.policy_kernel.mission_staging_policy_service import MissionStagingPolicyService
from aipinho.services.runtime.mission_contract_service import MissionContractService
from aipinho.services.runtime.mission_staging_resource_service import MissionStagingResourceService

REPO = "https://code.example.test/team/staging-app.git"


def _contract(*, authorized: bool = True):
    token = uuid4().hex
    prompt = (
        f"Use repository {REPO} branch main and git fetch. "
        + ("AUTORIZACAO: Autorizo git fetch nesta missao." if authorized else "")
    )
    human = IntentHumanAuthorityService().resolve(
        prompt=prompt,
        known_capabilities=["git_fetch"],
    )
    remote = IntentRemoteRepositoryService().resolve(prompt).resources
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id=f"session_m7_{token}",
        source_message_id=f"msg_m7_{token}",
        workspace=None,
        contract_type="shell",
        operation_type="git_fetch",
        runtime_profile="shell",
        capabilities_required=["git_fetch"],
        requested_actions=["run_command"],
        intent_map={
            "intent_type": "git_fetch",
            "raw_prompt": prompt,
            "requested_capabilities": ["git_fetch"],
            "authorized_capabilities": human.authorized_capabilities,
            "authority_evidence": human.evidence,
            "remote_resources": [item.model_dump(mode="json") for item in remote],
        },
    )
    return MissionContractService().compile_from_request(request)


def test_derives_deterministic_mission_staging_without_creating_directory() -> None:
    contract = _contract()
    remote = contract.remote_resources[0]
    service = MissionStagingResourceService()
    first = service.derive_resource(contract, remote_resource_id=remote.resource_id)
    second = service.derive_resource(contract, remote_resource_id=remote.resource_id)

    assert first.status == second.status == "allowed"
    assert first.resource is not None and second.resource is not None
    assert first.resource == second.resource
    assert first.resource.resource_type == "mission_staging"
    assert first.resource.role == "temp_staging"
    assert first.resource.derived_from == remote.resource_id
    assert first.resource.metadata["lifetime"] == "mission"
    assert first.resource.metadata["authority_inherited"] == []
    assert first.resource.metadata["authority_not_inherited"] == ["git_fetch"]
    assert Path(first.resource.locator or "").exists() is False
    MissionStagingPolicyService().validate_derived_resource(
        parent=contract,
        resource=first.resource,
    )


def test_derived_child_contract_is_valid_and_scope_matcher_sees_staging() -> None:
    contract = _contract()
    remote = contract.remote_resources[0]
    child, decision = MissionStagingResourceService().derive_child_contract(
        contract,
        remote_resource_id=remote.resource_id,
    )
    assert MissionContractService().verify(child)
    assert child.revision == contract.revision + 1
    assert child.parent_authority_sha256 == contract.authority_sha256
    assert decision.resource is not None
    staging = decision.resource
    assert staging in child.local_resources
    nested = str(Path(staging.locator or "") / "src" / "main.py")
    matched = MissionLocalResourceScopeService().scope_for_path(child.local_resources, nested)
    assert matched is not None
    assert matched.resource_id == staging.resource_id


def test_staging_requires_explicit_human_authority_for_remote() -> None:
    contract = _contract(authorized=False)
    remote = contract.remote_resources[0]

    decision = MissionStagingResourceService().derive_resource(
        contract,
        remote_resource_id=remote.resource_id,
    )

    assert decision.status == "denied"
    assert decision.reason_code == "mission_staging_source_remote_not_human_authorized"
def test_direct_prompt_cannot_declare_mission_staging() -> None:
    resource = MissionResourceScope(
        resource_id="forged_staging",
        resource_type="mission_staging",
        role="temp_staging",
        locator=str(Path.cwd() / "forged"),
    )
    request = TaskRunRequest(
        source_type="direct",
        source_channel="unit",
        session_id="session_forged",
        source_message_id="msg_forged",
        contract_type="shell",
        operation_type="run_command",
        runtime_profile="shell",
        intent_map={
            "intent_type": "run_command",
            "local_resources": [resource.model_dump(mode="json")],
        },
    )
    with pytest.raises(ValueError, match="mission_contract_resource_type_mismatch"):
        MissionContractService().compile_from_request(request)


def test_forged_staging_outside_safe_root_is_rejected() -> None:
    contract = _contract()
    remote = contract.remote_resources[0]
    service = MissionStagingResourceService()
    decision = service.derive_resource(contract, remote_resource_id=remote.resource_id)
    assert decision.resource is not None
    forged = decision.resource.model_copy(update={"locator": str(Path.cwd() / "outside_staging")})

    with pytest.raises(ValueError, match="mission_staging_outside_safe_root"):
        MissionStagingPolicyService().validate_derived_resource(
            parent=contract,
            resource=forged,
        )


def test_ordinary_new_local_resource_remains_forbidden_in_child() -> None:
    contract = _contract()
    extra = MissionResourceScope(
        resource_id="extra_local",
        resource_type="local_workspace",
        role="target_mutable",
        locator=str(Path.cwd() / "extra_local"),
        permissions=["read_file"],
    )
    with pytest.raises(ValueError, match="mission_contract_child_adds_local_resource"):
        MissionContractService().narrowed_child(
            contract,
            local_resources=[*contract.local_resources, extra],
        )
def test_staging_cannot_inherit_human_authority_by_metadata_tamper() -> None:
    contract = _contract()
    remote = contract.remote_resources[0]
    decision = MissionStagingResourceService().derive_resource(
        contract,
        remote_resource_id=remote.resource_id,
    )
    assert decision.resource is not None
    metadata = dict(decision.resource.metadata)
    metadata["authority_inherited"] = ["git_fetch"]
    forged = decision.resource.model_copy(update={"metadata": metadata})

    with pytest.raises(ValueError, match="mission_staging_human_authority_must_not_inherit"):
        MissionStagingPolicyService().validate_derived_resource(
            parent=contract,
            resource=forged,
        )
