from __future__ import annotations
class ArtifactServiceStatus:
    def status(self) -> dict[str, object]:
        return {"status": "ok", "enabled": True, "port": 9098, "mode": "artifact_metadata_and_links", "direct_workspace_serve_enabled": False}
