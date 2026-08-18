from aipinho.services.supervisor.connection_profile_service import ConnectionProfileService


def test_connection_profiles_and_selected_persistence(tmp_path):
    service = ConnectionProfileService(selected_path=tmp_path / "selected.json")
    ids = {profile.profile_id for profile in service.list_profiles()}
    assert {"adb_reverse", "wifi_lan", "tailscale", "manual"}.issubset(ids)
    assert service.get("adb_reverse").urls["core_backend"] == "http://127.0.0.1:9088"
    service.select("wifi_lan")
    assert service.selected() == "wifi_lan"
