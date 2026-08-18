from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.schemas.artifacts.artifact_interaction_contracts import UniversalArtifactCreateRequest
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService


class AgentTextArtifactService:
    def __init__(self, registry: UniversalArtifactRegistryService | None = None) -> None:
        self.registry = registry or UniversalArtifactRegistryService()

    def create(
        self,
        *,
        source_agent: str,
        content: str,
        session_id: str | None = None,
        filename: str | None = None,
        artifact_kind: str = "analysis",
        owner_task_id: str | None = None,
        bridge_task_id: str | None = None,
    ) -> dict:
        safe_kind = "".join(char for char in artifact_kind.lower() if char.isalnum() or char in {"-", "_"}) or "analysis"
        effective_filename = Path(filename).name if filename else f"{source_agent}_{safe_kind}_{uuid4().hex[:10]}.md"
        record = self.registry.create(
            UniversalArtifactCreateRequest(
                source_agent=source_agent,
                filename=effective_filename,
                content_type="text/markdown",
                content=content,
                session_id=session_id,
                owner_task_id=owner_task_id,
                bridge_task_id=bridge_task_id,
                validation_status="validated",
                provenance={
                    "executor_agent": source_agent,
                    "artifact_kind": safe_kind,
                    "local_execution": False,
                    "evidence_refs": [f"session:{session_id}"] if session_id else [],
                },
                metadata={"artifact_kind": safe_kind, "raw_default_visible": False},
                visible_to_agent_ids=[source_agent, "aipinho", "codex"],
            )
        )
        return self.registry.get(record.artifact_id) or record.model_dump()

