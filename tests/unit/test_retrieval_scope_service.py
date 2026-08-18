from aipinho.schemas.rag.retrieval_request import RetrievalScope
from aipinho.services.rag.retrieval_scope_service import RetrievalScopeService
from tests.unit.retrieval_test_helpers import request


def test_retrieval_scope_allows_official_workspace_and_blocks_forbidden_root():
    service = RetrievalScopeService()
    allowed = request(sources=["project_files"], workspace=r"C:\Dev\AIpinho", scope=RetrievalScope(scope_type="workspace", workspace=r"C:\Dev\AIpinho"))
    blocked = request(sources=["project_files"], workspace=r"C:\PinhoabacaxiAI", scope=RetrievalScope(scope_type="workspace", workspace=r"C:\PinhoabacaxiAI"))
    assert service.validate(allowed).valid is True
    assert "forbidden_root" in service.validate(blocked).blocked_reasons


def test_retrieval_scope_requires_workspace_for_files_and_explicit_memory():
    service = RetrievalScopeService()
    assert "workspace_required" in service.validate(request(sources=["project_files"])).blocked_reasons
    assert "explicit_memory_scope_required" in service.validate(request(sources=["curated_memory"], explicit=False)).blocked_reasons
