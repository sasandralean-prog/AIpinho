from datetime import datetime, timezone

from aipinho.schemas.patching.apply.patch_apply_file_result import PatchApplyFileResult
from aipinho.schemas.patching.apply.patch_apply_result import PatchApplyResult
from aipinho.schemas.patching.apply.post_apply_validation import PostApplyValidation
from aipinho.services.patching.apply.patch_apply_store import PatchApplyStore
from aipinho.services.rag.sources.patch_apply_result_retrieval_source import PatchApplyResultRetrievalSource
from tests.unit.retrieval_test_helpers import request


def test_patch_apply_result_source_returns_cited_result_without_file_content(tmp_path):
    store = PatchApplyStore(root=tmp_path)
    apply_run_id = "patch_apply_run_" + "c" * 32
    now = datetime.now(timezone.utc).isoformat()
    store.save_result(
        PatchApplyResult(
            apply_run_id=apply_run_id,
            plan_id="patch_plan_" + "d" * 32,
            status="completed",
            safe_to_report_success=True,
            files=[PatchApplyFileResult(file_path="src/example.py", status="applied", changed=True)],
            post_apply_validation=PostApplyValidation(status="passed", passed=True),
            created_at=now,
            updated_at=now,
        )
    )
    hits = PatchApplyResultRetrievalSource(store=store).retrieve(
        request(sources=["patch_apply_results"], apply_run_id=apply_run_id)
    )
    assert len(hits) == 1
    assert hits[0].citation.citation_type == "patch_apply_field"
    assert hits[0].metadata["changed_files"] == 1
    assert "src/example.py" not in hits[0].excerpt
