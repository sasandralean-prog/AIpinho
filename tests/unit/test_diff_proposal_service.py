from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.services.patching.diff_proposal_service import DiffProposalService


def test_diff_proposal_service_generates_or_needs_review():
    service = DiffProposalService()
    empty = service.create("patch_plan_abcdef", "docs/a.md", "old", [])
    assert empty.status == "needs_review"
    diff = service.create("patch_plan_abcdef", "docs/a.md", "old", [PatchHunk(hunk_id="h", file_path="docs/a.md", original="old", replacement="new", evidence_ids=["e1"], confidence=0.7)])
    assert diff.status == "generated"
    assert "new" in diff.diff.diff_text
