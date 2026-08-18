from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.services.patching.unified_diff_builder import UnifiedDiffBuilder


class DiffProposalService:
    def __init__(self) -> None:
        self.builder = UnifiedDiffBuilder()

    def create(self, plan_id: str, file_path: str, original_content: str, hunks: list[PatchHunk]) -> DiffProposal:
        if not hunks:
            return DiffProposal(proposal_id=f"diff_proposal_{uuid4().hex}", plan_id=plan_id, status="needs_review", blocked_reasons=["no_safe_hunks"])
        diff = self.builder.from_hunks(file_path, original_content, hunks)
        if not diff.diff_text:
            return DiffProposal(proposal_id=f"diff_proposal_{uuid4().hex}", plan_id=plan_id, status="invalid", blocked_reasons=["empty_diff"])
        return DiffProposal(proposal_id=f"diff_proposal_{uuid4().hex}", plan_id=plan_id, status="generated", diff=diff)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "diff_proposal", "apply_enabled": False, "write_enabled": False}
