from __future__ import annotations

import hashlib

from aipinho.schemas.runtime.mission_contract import MissionContract, MissionResourceScope
from aipinho.schemas.runtime.mission_staging import MissionStagingDerivationDecision
from aipinho.services.policy_kernel.mission_staging_policy_service import MissionStagingPolicyService
from aipinho.services.runtime.mission_contract_service import MissionContractService


class MissionStagingResourceService:
    """Derives mission-scoped local staging authority from a frozen remote scope."""

    def __init__(
        self,
        *,
        policy: MissionStagingPolicyService | None = None,
        missions: MissionContractService | None = None,
    ) -> None:
        self.policy = policy or MissionStagingPolicyService()
        self.missions = missions or MissionContractService(staging_policy=self.policy)

    def derive_resource(
        self,
        contract: MissionContract,
        *,
        remote_resource_id: str,
    ) -> MissionStagingDerivationDecision:
        if not self.missions.verify(contract):
            return self._denied("mission_contract_authority_hash_invalid", remote_resource_id)
        remote = next(
            (item for item in contract.remote_resources if item.resource_id == remote_resource_id),
            None,
        )
        if remote is None or remote.resource_type != "remote_repository":
            return self._denied("mission_staging_source_remote_missing", remote_resource_id)
        if remote.role != "remote_allowed" or not remote.normalized_identity:
            return self._denied("mission_staging_source_remote_not_allowed", remote_resource_id)
        if not remote.allowed_branches:
            return self._denied("mission_staging_source_branch_scope_missing", remote_resource_id)

        authorized = sorted(
            set(contract.authority.authorized_capabilities).intersection(remote.permissions)
        )
        if not authorized:
            return self._denied("mission_staging_source_remote_not_human_authorized", remote_resource_id)

        safe_root = self.policy.safe_root()
        resource_id = self._resource_id(contract, remote)
        mission_segment = hashlib.sha256(contract.mission_id.encode("utf-8")).hexdigest()[:20]
        locator = safe_root / mission_segment / resource_id
        creation_evidence = [
            f"mission:{contract.mission_id}",
            f"remote_resource:{remote.resource_id}",
            "mission_staging_policy:v1",
        ]
        resource = MissionResourceScope(
            resource_id=resource_id,
            resource_type="mission_staging",
            role="temp_staging",
            locator=str(locator),
            permissions=self.policy.allowed_permissions(),
            derived_from=remote.resource_id,
            provenance_refs=[
                *remote.provenance_refs,
                *creation_evidence,
            ],
            metadata={
                "lifetime": str(self.policy.config.get("lifetime") or "mission"),
                "source_remote_resource_id": remote.resource_id,
                "source_remote_identity": remote.normalized_identity,
                "source_allowed_branches": list(remote.allowed_branches),
                "authority_inherited": [],
                "authority_not_inherited": authorized,
                "creation_evidence": creation_evidence,
            },
        )
        self.policy.validate_derived_resource(parent=contract, resource=resource)
        return MissionStagingDerivationDecision(
            status="allowed",
            reason_code="mission_staging_resource_derived",
            resource=resource,
            safe_root=str(safe_root),
            source_remote_resource_id=remote.resource_id,
            authority_inherited=[],
            authority_not_inherited=authorized,
            evidence_refs=creation_evidence,
        )

    def derive_child_contract(
        self,
        contract: MissionContract,
        *,
        remote_resource_id: str,
    ) -> tuple[MissionContract, MissionStagingDerivationDecision]:
        decision = self.derive_resource(contract, remote_resource_id=remote_resource_id)
        if decision.status != "allowed" or decision.resource is None:
            raise ValueError(decision.reason_code)
        child = self.missions.narrowed_child(
            contract,
            local_resources=[*contract.local_resources, decision.resource],
        )
        return child, decision

    @staticmethod
    def _resource_id(contract: MissionContract, remote: MissionResourceScope) -> str:
        seed = "|".join(
            [
                contract.mission_id,
                remote.resource_id,
                str(remote.normalized_identity or ""),
                ",".join(remote.allowed_branches),
            ]
        )
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20]
        return f"mission_staging_{digest}"

    @staticmethod
    def _denied(reason_code: str, remote_resource_id: str) -> MissionStagingDerivationDecision:
        return MissionStagingDerivationDecision(
            status="denied",
            reason_code=reason_code,
            source_remote_resource_id=remote_resource_id,
        )
