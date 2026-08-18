from __future__ import annotations

from aipinho.schemas.patching.apply.hunk_apply_result import HunkApplyResult
from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.services.patching.apply.patch_apply_hashing import sha256_text


class HunkApplyEngine:
    def apply(self, content: str, hunk: PatchHunk) -> tuple[str, HunkApplyResult]:
        before_hash = sha256_text(content)
        if hunk.original == "":
            updated = hunk.replacement
            after_hash = sha256_text(updated)
            return updated, HunkApplyResult(hunk_id=hunk.hunk_id, file_path=hunk.file_path, status="applied", applied=True, reason="new_file_content_created", before_hash=before_hash, after_hash=after_hash)
        if hunk.original not in content:
            return content, HunkApplyResult(hunk_id=hunk.hunk_id, file_path=hunk.file_path, status="failed", applied=False, reason="removed_lines_or_context_mismatch", before_hash=before_hash, after_hash=before_hash)
        updated = content.replace(hunk.original, hunk.replacement, 1)
        after_hash = sha256_text(updated)
        return updated, HunkApplyResult(hunk_id=hunk.hunk_id, file_path=hunk.file_path, status="applied", applied=True, reason="exact_context_match", before_hash=before_hash, after_hash=after_hash)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "hunk_apply_engine", "fuzzy_apply": False}
