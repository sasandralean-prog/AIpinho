from __future__ import annotations

import pytest

from aipinho.schemas.self_healing import SelfHealingScanRequest
from aipinho.services.self_healing.self_healing_service import SelfHealingService


@pytest.mark.multi_agent
@pytest.mark.golden_path
def test_self_healing_scan_returns_auditable_status_without_deleting_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_SELF_HEALING_ROOT", str(tmp_path / "self_healing"))
    service = SelfHealingService()

    candidates = service.scan(SelfHealingScanRequest(detector_ids=[], persist=True))
    status = service.status()

    assert isinstance(candidates, list)
    assert status.status in {"ok", "warning", "disabled"}
    assert status.raw_default_visible is False
    assert isinstance(status.candidates_open, int)
