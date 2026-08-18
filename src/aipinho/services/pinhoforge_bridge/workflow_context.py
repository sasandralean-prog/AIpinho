from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PinhoForgeWorkflowContext:
    workflow_id: str | None = None
    workflow_run_id: str | None = None
    workflow_step_id: str | None = None
    checkpoint_id: str | None = None
    trace_id: str | None = None
    source_scope: str | None = None
    workspace_ref: str | None = None

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any] | None) -> "PinhoForgeWorkflowContext":
        data = metadata or {}

        def first(*keys: str) -> str | None:
            for key in keys:
                value = data.get(key)
                if value is not None and str(value).strip():
                    return str(value)
            return None

        return cls(
            workflow_id=first("workflow_id", "workflowId"),
            workflow_run_id=first("workflow_run_id", "workflowRunId", "run_id", "runId"),
            workflow_step_id=first("workflow_step_id", "workflowStepId", "step_id", "stepId"),
            checkpoint_id=first("checkpoint_id", "checkpointId", "workflow_checkpoint_id"),
            trace_id=first("trace_id", "traceId"),
            source_scope=first("source_scope", "sourceScope"),
            workspace_ref=first("workspace_ref", "workspaceRef"),
        )

    def evidence_refs(self) -> list[str]:
        refs: list[str] = []
        if self.workflow_id:
            refs.append(f"workflow:{self.workflow_id}")
        if self.workflow_run_id:
            refs.append(f"workflow_run:{self.workflow_run_id}")
        if self.workflow_step_id:
            refs.append(f"workflow_step:{self.workflow_step_id}")
        if self.checkpoint_id:
            refs.append(f"checkpoint:{self.checkpoint_id}")
        if self.trace_id:
            refs.append(f"trace:{self.trace_id}")
        return refs


def workflow_evidence_refs(metadata: dict[str, Any] | None, base_refs: list[str]) -> list[str]:
    refs: list[str] = []
    for ref in [*base_refs, *PinhoForgeWorkflowContext.from_metadata(metadata).evidence_refs()]:
        if ref and ref not in refs:
            refs.append(ref)
    return refs
