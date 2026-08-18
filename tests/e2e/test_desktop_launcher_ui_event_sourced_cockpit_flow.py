from pathlib import Path


def test_desktop_launcher_ui_structure_and_reports_ready() -> None:
    required = [
        "apps/launcher/ui/launcher_ui_main.py",
        "apps/launcher/ui/tabs/dashboard_tab.py",
        "apps/launcher/ui/tabs/chat_tab.py",
        "apps/launcher/ui/tabs/pipeline_tab.py",
        "apps/launcher/ui/tabs/debugger_tab.py",
        "apps/launcher/ui/tabs/settings_tab.py",
        "config/launcher/desktop_ui_policy.yaml",
    ]
    for item in required:
        assert Path(item).exists(), item
