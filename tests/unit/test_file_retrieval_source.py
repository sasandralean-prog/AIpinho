from aipinho.schemas.rag.retrieval_request import RetrievalScope
from aipinho.services.rag.sources.file_retrieval_source import FileRetrievalSource
from tests.unit.retrieval_test_helpers import request


def test_file_retrieval_source_reads_allowed_file_via_readonly_service():
    req = request(query="AIpinho", sources=["project_files"], workspace=r"C:\Dev\AIpinho", paths=["README.md"], scope=RetrievalScope(scope_type="workspace", workspace=r"C:\Dev\AIpinho"))
    hits = FileRetrievalSource().retrieve(req)
    assert hits
    assert hits[0].citation.citation_type == "file_line_range"


def test_file_retrieval_source_does_not_leak_secret_file():
    req = request(query="secret", sources=["project_files"], workspace=r"C:\Dev\AIpinho", paths=[".env"], scope=RetrievalScope(scope_type="workspace", workspace=r"C:\Dev\AIpinho"))
    assert FileRetrievalSource().retrieve(req) == []
