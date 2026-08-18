from __future__ import annotations

import time
from pathlib import Path

from aipinho.schemas.sandbox import SandboxCleanupPreview, SandboxCleanupPreviewRequest
from aipinho.services.sandbox.sandbox_paths import ensure_sandbox_dirs
from aipinho.services.sandbox.sandbox_paths import is_within
from aipinho.services.sandbox.sandbox_policy_service import SandboxPolicyService
from aipinho.services.sandbox.sandbox_store_service import SandboxStoreService


class SandboxCleanupService:
    def __init__(self, *, store: SandboxStoreService | None = None, policy: SandboxPolicyService | None = None) -> None:
        self.store = store or SandboxStoreService()
        self.policy = policy or SandboxPolicyService()
        self.dirs = ensure_sandbox_dirs()

    def preview(self, request: SandboxCleanupPreviewRequest) -> SandboxCleanupPreview:
        candidates: list[dict[str, object]] = []
        cutoff = time.time() - max(1, request.max_age_hours) * 3600
        roots = []
        if request.include_tmp:
            roots.append(self.dirs["tmp"])
        if request.include_trash:
            roots.append(self.dirs["trash"])
        for root in roots:
            for path in root.rglob("*"):
                if path.is_file() and path.stat().st_mtime < cutoff:
                    candidates.append({"path_sanitized": str(path), "size": path.stat().st_size, "root": root.name})
        preview = SandboxCleanupPreview(candidates=candidates)
        self.store.save_cleanup_preview(preview)
        self.store.append_trace(None, {"type": "sandbox_cleanup_preview_created", "preview_id": preview.cleanup_preview_id, "candidate_count": len(candidates)})
        return preview

    def apply(self, preview_id: str) -> dict[str, object]:
        preview = self.store.get_cleanup_preview(preview_id)
        decision = self.policy.allow_cleanup_apply(has_preview_id=preview is not None)
        if not decision.allowed:
            return {"status": "blocked", "reason_code": decision.reason_code, "deleted": 0}
        deleted = 0
        allowed_roots = [self.dirs["tmp"].resolve(strict=False), self.dirs["trash"].resolve(strict=False)]
        for candidate in preview.candidates if preview else []:
            path = Path(str(candidate.get("path_sanitized", ""))).resolve(strict=False)
            if not any(is_within(path, root) for root in allowed_roots):
                continue
            try:
                if path.exists() and path.is_file():
                    path.unlink()
                    deleted += 1
            except OSError:
                continue
        self.store.append_trace(None, {"type": "sandbox_cleanup_applied", "preview_id": preview_id, "deleted": deleted})
        return {"status": "succeeded", "reason_code": "sandbox_cleanup_preview_allowed", "deleted": deleted}
