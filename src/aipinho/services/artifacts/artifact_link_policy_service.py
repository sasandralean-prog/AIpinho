from __future__ import annotations
class ArtifactLinkPolicyService:
    def policy(self) -> dict[str, object]:
        return {"status": "ok", "direct_workspace_serve_enabled": False, "links_require_manifest": True, "hash_manifest_required": True}
