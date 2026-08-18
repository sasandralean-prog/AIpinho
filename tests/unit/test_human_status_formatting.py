from apps.launcher.ui.utils.human_status import human_status


def test_human_status_labels() -> None:
    assert human_status("ok") == "Operacional"
    assert human_status("degraded") == "Degradado"
    assert human_status("blocked") == "Bloqueado"
