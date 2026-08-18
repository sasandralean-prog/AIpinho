from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.rag.sources.task_result_retrieval_source import TaskResultRetrievalSource
from aipinho.services.runtime.task_run_store import TaskRunStore
from tests.unit.retrieval_test_helpers import request


def test_task_result_source_requires_id_and_returns_cited_safe_summary(tmp_path):
    store = TaskRunStore(root=tmp_path)
    run_id = "task_run_" + "a" * 32
    store.save_result(
        run_id,
        TaskRunResult(
            run_id=run_id,
            status="completed",
            summary="Read-only analysis completed with cited findings.",
            safe_to_display=True,
            events_count=4,
        ),
    )
    source = TaskResultRetrievalSource(store=store)
    assert source.retrieve(request(sources=["task_results"])) == []
    hits = source.retrieve(request(sources=["task_results"], run_id=run_id))
    assert len(hits) == 1
    assert hits[0].citation.citation_type == "task_result_field"
    assert hits[0].metadata["status"] == "completed"
