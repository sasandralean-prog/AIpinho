from aipinho.schemas.analysis.file_selection import FileSelectionCandidate
from aipinho.services.analysis.file_context_budget_service import FileContextBudgetService


def test_file_context_budget_omits_after_file_and_byte_limits():
    service = FileContextBudgetService()
    selected, omitted = service.fit(
        [
            FileSelectionCandidate(path="a.py", score=10, size_bytes=10),
            FileSelectionCandidate(path="b.py", score=9, size_bytes=10),
            FileSelectionCandidate(path="c.py", score=8, size_bytes=10),
        ],
        max_files=2,
        max_total_bytes=25,
    )

    assert [item.path for item in selected] == ["a.py", "b.py"]
    assert omitted[0].reason == "max_files_budget"
