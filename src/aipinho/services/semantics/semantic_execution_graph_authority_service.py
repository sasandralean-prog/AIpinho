from __future__ import annotations

import hashlib
import json
from typing import Any

from aipinho.schemas.semantics.semantic_execution_graph import (
    SemanticDependencyEdge,
    SemanticExecutionGraph,
    SemanticWorkUnitContract,
)
from aipinho.schemas.semantics.task_semantic_vocabulary import (
    TaskSemanticVocabularyBinding,
)


class SemanticExecutionGraphAuthorityService:
    """Computes and verifies canonical semantic graph authority hashes."""

    def stable_sha256(self, payload: Any) -> str:
        rendered = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def authority_payload(
        self,
        *,
        task_run_id: str,
        task_id: str | None,
        source_plan_id: str,
        source_execution_id: str,
        source_semantics_sha256: str,
        vocabulary_binding: TaskSemanticVocabularyBinding,
        work_units: list[SemanticWorkUnitContract],
        edges: list[SemanticDependencyEdge],
        status: str,
        reason_codes: list[str],
        schema_version: str,
    ) -> dict[str, Any]:
        return {
            "task_run_id": task_run_id,
            "task_id": task_id,
            "source_plan_id": source_plan_id,
            "source_execution_id": source_execution_id,
            "source_semantics_sha256": source_semantics_sha256,
            "vocabulary_binding": vocabulary_binding.model_dump(mode="json"),
            "work_units": [
                item.model_dump(mode="json") for item in work_units
            ],
            "edges": [item.model_dump(mode="json") for item in edges],
            "status": status,
            "reason_codes": list(reason_codes),
            "schema_version": schema_version,
        }

    def compute_authority_sha256(
        self,
        **kwargs: Any,
    ) -> str:
        return self.stable_sha256(self.authority_payload(**kwargs))

    def verify(self, graph: SemanticExecutionGraph) -> bool:
        expected = self.compute_authority_sha256(
            task_run_id=graph.task_run_id,
            task_id=graph.task_id,
            source_plan_id=graph.source_plan_id,
            source_execution_id=graph.source_execution_id,
            source_semantics_sha256=graph.source_semantics_sha256,
            vocabulary_binding=graph.vocabulary_binding,
            work_units=graph.work_units,
            edges=graph.edges,
            status=graph.status,
            reason_codes=graph.reason_codes,
            schema_version=graph.schema_version,
        )
        return expected == graph.authority_sha256
