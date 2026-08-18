from __future__ import annotations

import difflib

from aipinho.schemas.patching.diff_preview import DiffPreview
from aipinho.schemas.patching.patch_hunk import PatchHunk


class UnifiedDiffBuilder:
    def build(self, file_path: str, original_content: str, replacement_content: str, *, max_chars: int = 50000) -> DiffPreview:
        diff = "\n".join(difflib.unified_diff(original_content.splitlines(), replacement_content.splitlines(), fromfile=f"a/{file_path}", tofile=f"b/{file_path}", lineterm=""))
        added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
        return DiffPreview(diff_text=diff[:max_chars], truncated=len(diff) > max_chars, chars=min(len(diff), max_chars), added_lines=added, removed_lines=removed)

    def from_hunks(self, file_path: str, original_content: str, hunks: list[PatchHunk]) -> DiffPreview:
        replacement = original_content
        for hunk in hunks:
            replacement = replacement.replace(hunk.original, hunk.replacement, 1)
        return self.build(file_path, original_content, replacement)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "unified_diff_builder", "apply_enabled": False}
