from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_connection_autofill_uses_read_only_api_v1_suggestions() -> None:
    with (ROOT / "config" / "mobile" / "mobile_connection_policy.yaml").open("r", encoding="utf-8") as handle:
        policy = yaml.safe_load(handle) or {}
    autofill = policy.get("autofill", {})
    assert autofill["endpoint"] == "/api/v1/connection/suggestions"
    assert autofill["aggressive_network_scan_allowed"] is False


def test_copy_actions_keep_raw_hidden_by_default() -> None:
    with (ROOT / "config" / "mobile" / "mobile_copy_actions_policy.yaml").open("r", encoding="utf-8") as handle:
        policy = yaml.safe_load(handle) or {}
    assert policy["raw_copy_requires_explicit_action"] is True
    assert policy["token_redaction_required"] is True
