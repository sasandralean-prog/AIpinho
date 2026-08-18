from __future__ import annotations

import hashlib
from pathlib import Path

from aipinho.schemas.governance.discovery import WorkspaceDiscoverySnapshot


class WorkspaceDiscoveryService:
    """Metadata-only discovery helper for governance decisions."""

    def snapshot_ref_for(self, workspace_path: str | None) -> str | None:
        if not workspace_path:
            return None
        digest = hashlib.sha256(workspace_path.encode("utf-8", errors="ignore")).hexdigest()[:16]
        return f"workspace_snapshot_{digest}"

    def metadata_snapshot(self, workspace_path: str) -> WorkspaceDiscoverySnapshot:
        path = Path(workspace_path)
        sample: list[str] = []
        if path.exists() and path.is_dir():
            for child in list(path.iterdir())[:20]:
                sample.append(str(child))
        ref = self.snapshot_ref_for(workspace_path) or "workspace_snapshot_unknown"
        return WorkspaceDiscoverySnapshot(snapshot_ref=ref, workspace_path=workspace_path, files_sampled=sample)
