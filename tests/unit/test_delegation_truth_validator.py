from __future__ import annotations

from aipinho.services.runtime.delegation_truth_validator import DelegationTruthValidator


def test_delegation_claim_without_runtime_contract_is_violation():
    result = DelegationTruthValidator().validate("Deleguei para AIpinho e o executor retornou resposta.")

    assert result.status == "violation"
    assert result.reason_code == "delegation_id_required_for_delegation_claim"
    assert "delegation_claim_without_runtime_contract" in result.violations


def test_delegation_claim_with_runtime_contract_is_allowed():
    result = DelegationTruthValidator().validate(
        "Deleguei para AIpinho e acompanhei polling.",
        delegation_id="delegation_abc",
    )

    assert result.status == "ok"
    assert result.delegation_claimed is True
    assert result.delegation_id == "delegation_abc"
