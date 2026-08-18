from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MOBILE_SRC = ROOT / "apps" / "mobile" / "android" / "app" / "src" / "main" / "java" / "br" / "com" / "aipinho" / "mobile"


def _source(relative: str) -> str:
    return (MOBILE_SRC / relative).read_text(encoding="utf-8")


def test_mobile_main_flow_exposes_required_tabs_and_read_only_surfaces() -> None:
    main = _source("MainActivity.kt")
    nav = _source("ui/navigation/MainNavigationState.kt")
    assert "AipinhoScrollableTabBar" in main
    for tab in ("Dashboard", "Chat", "Pipeline", "Approvers", "Debugger 2.0", "Config"):
        assert tab in nav
    assert "PairingScreen" in main


def test_mobile_feature_parity_screens_use_neon_components() -> None:
    screens = {
        "ui/screens/DashboardScreen.kt": ("NeonCyberCard", "HumanizedViewModelTerminal", "Reiniciar backend"),
        "ui/screens/ChatScreen.kt": ("NeonRawCopyButton", "NeonUploadCard", "NeonConfirmDialog"),
        "ui/screens/PipelineScreen.kt": ("Fila de tasks", "HumanizedViewModelTerminal", "Sessao universal"),
        "ui/screens/DebuggerScreen.kt": ("NeonCyberCard", "NeonSearchField", "Debugger 2.0"),
        "ui/screens/SettingsScreen.kt": ("NeonConnectionAutoFillPanel", "NeonConnectionProfileCard"),
        "ui/screens/UniversalApproversScreen.kt": ("Universal Approvers", "universalApprovers"),
    }
    for relative, expected in screens.items():
        text = _source(relative)
        for symbol in expected:
            assert symbol in text
