import pytest
from pydantic import ValidationError
from aipinho.schemas.maintenance.contracts import MaintenanceRequest, MaintenanceStatus

def test_contracts_forbid_unknown_fields():
    with pytest.raises(ValidationError):
        MaintenanceRequest(unknown=True)

def test_status_contract_makes_blocked_mutations_explicit():
    status = MaintenanceStatus()
    assert status.autonomous_apply is False
    assert status.direct_shell_enabled is False
    assert status.direct_git_enabled is False
    assert status.direct_policy_write_enabled is False
    assert status.direct_memory_write_enabled is False
