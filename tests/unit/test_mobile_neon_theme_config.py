from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def _load_mobile_config(name: str) -> dict[str, object]:
    with (ROOT / "config" / "mobile" / name).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def test_neon_theme_policy_declares_required_palette() -> None:
    policy = _load_mobile_config("mobile_neon_theme_policy.yaml")
    palette = policy.get("colors", {})
    required = {
        "#020406",
        "#03070A",
        "#0A1014",
        "#16232D",
        "#0E1821",
        "#00E5FF",
        "#39FF14",
        "#FF2BD6",
        "#FF1493",
        "#FF4DA6",
        "#7DEBFF",
        "#60707A",
    }
    assert required.issubset(set(palette.values()))


def test_mobile_app_policy_enables_cyberpunk_polish_flags() -> None:
    policy = _load_mobile_config("mobile_app_policy.yaml")
    mobile_app = policy["mobile_app"]
    assert mobile_app["cyberpunk_neon_theme_enabled"] is True
    assert mobile_app["horizontal_tabs_enabled"] is True
    assert mobile_app["connection_autofill_enabled"] is True
    assert mobile_app["support_bundle_preview_enabled"] is True
