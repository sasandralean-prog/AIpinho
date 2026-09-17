from __future__ import annotations

from aipinho.schemas.governance.lifecycle import (
    CanonicalOperationContract,
    CanonicalPermission,
    CanonicalPolicyFacet,
)
from aipinho.services.governance.policy.effective_policy_decision_service import (
    EffectivePolicyDecisionService,
)


def _contract(action: str = "modify_file") -> CanonicalOperationContract:
    return CanonicalOperationContract(
        intent_type="workspace_fix_request",
        operation_type="filesystem_modify_file",
        contract_type="filesystem_write",
        requires_task=True,
        workspace_mutation=True,
        requested_actions=[action],
        workspace_path="C:/work/app",
    )


def _facet(
    facet: str,
    permission: CanonicalPermission,
    *,
    capability: str = "modify_file",
    requires_human_authority: bool = False,
    reason_code: str = "test",
) -> CanonicalPolicyFacet:
    return CanonicalPolicyFacet(
        facet=facet,
        permission=permission,
        source=f"test:{facet}",
        reason_code=reason_code,
        capability=capability,
        requires_human_authority=requires_human_authority,
    )


def test_human_authority_satisfies_only_matching_consent_ask() -> None:
    service = EffectivePolicyDecisionService()
    decision = service.resolve_facets(
        _contract(),
        facets=[
            _facet(
                "resource_permission",
                CanonicalPermission.ASK,
                requires_human_authority=True,
            ),
            _facet("human_authority", CanonicalPermission.ALLOWED),
            _facet("global_policy", CanonicalPermission.ALLOWED),
        ],
        capability="modify_file",
        resource_id="workspace_app",
    )

    assert decision.permission == CanonicalPermission.ALLOWED
    assert decision.requires_approval is False
    assert decision.source == "effective_policy_decision"


def test_missing_human_authority_keeps_approval_required() -> None:
    decision = EffectivePolicyDecisionService().resolve_facets(
        _contract(),
        facets=[
            _facet(
                "resource_permission",
                CanonicalPermission.ASK,
                requires_human_authority=True,
            ),
            _facet("global_policy", CanonicalPermission.ALLOWED),
        ],
        capability="modify_file",
    )

    assert decision.permission == CanonicalPermission.ASK
    assert decision.requires_approval is True
    assert decision.ask_actions == ["modify_file"]


def test_authority_for_other_capability_does_not_satisfy_ask() -> None:
    decision = EffectivePolicyDecisionService().resolve_facets(
        _contract(),
        facets=[
            _facet(
                "resource_permission",
                CanonicalPermission.ASK,
                requires_human_authority=True,
            ),
            _facet("human_authority", CanonicalPermission.ALLOWED, capability="git_push"),
        ],
        capability="modify_file",
    )

    assert decision.permission == CanonicalPermission.ASK
    assert decision.requires_approval is True


def test_hard_deny_cannot_be_overridden_by_human_authority() -> None:
    decision = EffectivePolicyDecisionService().resolve_facets(
        _contract(),
        facets=[
            _facet("resource_permission", CanonicalPermission.ALLOWED),
            _facet("human_authority", CanonicalPermission.ALLOWED),
            _facet(
                "global_policy",
                CanonicalPermission.DENIED,
                reason_code="global_policy_denied",
            ),
        ],
        capability="modify_file",
    )

    assert decision.permission == CanonicalPermission.DENIED
    assert decision.denied_actions == ["modify_file"]
    assert decision.reason_code.value == "policy_denied"


def test_canonical_decision_preserves_facet_diagnostics() -> None:
    facets = [
        _facet("capability_demand", CanonicalPermission.ALLOWED),
        _facet("resource_permission", CanonicalPermission.ALLOWED),
        _facet("human_authority", CanonicalPermission.ALLOWED),
    ]
    decision = EffectivePolicyDecisionService().resolve_facets(
        _contract(),
        facets=facets,
        capability="modify_file",
        resource_id="workspace_app",
    )

    assert decision.permission == CanonicalPermission.ALLOWED
    assert decision.capability == "modify_file"
    assert decision.resource_id == "workspace_app"
    assert [item.facet for item in decision.facets] == [
        "capability_demand",
        "resource_permission",
        "human_authority",
    ]
    assert decision.trace[0]["stage"] == "canonical_policy_facets"
    assert decision.trace[0]["facets"][2]["source"] == "test:human_authority"
