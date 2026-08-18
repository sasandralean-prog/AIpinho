from pathlib import Path


MOBILE_ROOT = Path("apps/mobile/android/app/src/main/java/br/com/aipinho/mobile")


def test_agent_artifact_panel_uses_universal_registry_contract():
    api = (MOBILE_ROOT / "network" / "AgentApiClient.kt").read_text(encoding="utf-8")
    panel = (MOBILE_ROOT / "ui" / "components" / "AgentArtifactPanel.kt").read_text(encoding="utf-8")
    screen = (MOBILE_ROOT / "ui" / "screens" / "AgentTabScreen.kt").read_text(encoding="utf-8")

    assert "/api/v1/artifacts/by-agent/" in api
    assert "session_id" in api

    assert "source_agent" in panel
    assert "owner_task_id" in panel
    assert "bridge_task_id" in panel
    assert "validation_status" in panel
    assert "local_path" in panel
    assert "Copiar ID" in panel
    assert "Copiar caminho" in panel
    assert "artifactClient.download" in panel
    assert "missing" in panel
    assert "stale" in panel

    assert "renderImportantEvents" in screen
    assert "isImportantTimelineEvent" in screen
    assert "artifact" in screen
    assert "delegation" in screen
