
from pathlib import Path

from aipinho.services.legacy_rag.legacy_core import LegacyReviewService


def test_legacy_rag_commit_requires_manifest(tmp_path):
    result = LegacyReviewService().commit(tmp_path / "missing_approval.json")
    assert result.status == "blocked"
    assert "approval_manifest_missing" in result.warnings
