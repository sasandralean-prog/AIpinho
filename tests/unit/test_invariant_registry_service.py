from aipinho.services.maintenance.invariant_registry_service import InvariantRegistryService

def test_registry_exposes_fifteen_general_invariants():
    values = InvariantRegistryService().list()
    assert len(values) == 15
    assert any(item.invariant_id == "patch_never_with_read_only" for item in values)
