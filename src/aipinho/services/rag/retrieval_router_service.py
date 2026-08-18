from __future__ import annotations

from typing import Any

from aipinho.services.rag.sources.curated_memory_retrieval_source import CuratedMemoryRetrievalSource
from aipinho.services.rag.sources.file_retrieval_source import FileRetrievalSource
from aipinho.services.rag.sources.patch_apply_result_retrieval_source import PatchApplyResultRetrievalSource
from aipinho.services.rag.sources.project_report_retrieval_source import ProjectReportRetrievalSource
from aipinho.services.rag.sources.task_result_retrieval_source import TaskResultRetrievalSource
from aipinho.services.rag.sources.validation_result_retrieval_source import ValidationResultRetrievalSource


class RetrievalRouterService:
    def __init__(self, adapters: dict[str, Any] | None = None) -> None:
        self.adapters = adapters or {
            "file_retrieval_source": FileRetrievalSource(),
            "project_report_retrieval_source": ProjectReportRetrievalSource(),
            "task_result_retrieval_source": TaskResultRetrievalSource(),
            "validation_result_retrieval_source": ValidationResultRetrievalSource(),
            "patch_apply_result_retrieval_source": PatchApplyResultRetrievalSource(),
            "curated_memory_retrieval_source": CuratedMemoryRetrievalSource(),
        }

    def adapter_for(self, adapter_id: str):
        return self.adapters.get(adapter_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_router", "adapters": sorted(self.adapters)}
