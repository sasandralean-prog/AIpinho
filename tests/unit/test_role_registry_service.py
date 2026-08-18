from aipinho.services.roles.role_registry_service import RoleRegistryService


def test_role_registry_loads_roles_and_safety_flags():
    service = RoleRegistryService()
    roles = service.list_roles()
    assert "speaker" in roles
    assert "analyst" in roles
    assert all(role.can_call_tools is False for role in roles.values())
    assert all(role.can_write is False for role in roles.values())
    assert all(role.can_patch is False for role in roles.values())


def test_role_registry_disabled_role_is_present_but_not_runnable():
    role = RoleRegistryService().get_role("executor")
    assert role is not None
    assert role.enabled is False


def test_role_registry_output_contracts_exist():
    for role in RoleRegistryService().list_roles().values():
        assert role.output_contract
