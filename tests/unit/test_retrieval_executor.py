from aipinho.services.rag.retrieval_executor import RetrievalExecutor
from tests.unit.retrieval_test_helpers import request


def test_retrieval_executor_combines_project_report_results_and_trace():
    hits, trace, warnings = RetrievalExecutor().execute(request(), ["project_reports"])
    assert hits
    assert trace[0].reason == "source_retrieved"
    assert warnings == []
