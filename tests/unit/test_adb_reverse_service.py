from aipinho.services.supervisor.adb_reverse_service import ADBReverseService


def test_adb_reverse_commands_include_all_ports_and_do_not_autorun():
    status = ADBReverseService().commands()
    assert status.auto_run_adb_allowed is False
    assert status.ports == [9080, 9088, 9089, 9098, 9099]
    assert "adb reverse tcp:9080 tcp:9080" in status.commands
    assert "adb reverse tcp:9099 tcp:9099" in status.commands
