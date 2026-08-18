from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.patching.patch_hunk import PatchHunk


class PatchHunkBuilder:
    def build(self, file_path: str, original_content: str, replacement_hint: str, evidence_ids: list[str]) -> PatchHunk | None:
        original = original_content.splitlines()[0] if original_content.splitlines() else ""
        if not replacement_hint:
            return None
        reason = "Preview hunk from explicit evidence/request."
        if original == "":
            reason = "Create text file from explicit evidence/request."
        return PatchHunk(hunk_id=f"patch_hunk_{uuid4().hex}", file_path=file_path, original=original, replacement=replacement_hint, reason=reason, evidence_ids=evidence_ids, confidence=0.6)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_hunk_builder"}
