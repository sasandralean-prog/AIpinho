from __future__ import annotations

import json

from aipinho.schemas.agents.hybrid_execution import CanonicalPromptRequest, CanonicalPromptResult
from aipinho.services.events.event_core import redact_payload


class CanonicalPromptBuilderService:
    def build(self, request: CanonicalPromptRequest) -> CanonicalPromptResult:
        constraints = redact_payload(request.constraints)
        outputs = [str(redact_payload(item)) for item in request.desired_outputs]
        workspace = str(redact_payload(request.workspace)) if request.workspace else "not_provided"
        sections = [
            "Delegated governed execution request",
            f"Source agent: {request.source_agent}",
            f"Target agent: aipinho",
            f"Workspace: {workspace}",
            f"Intent: {request.intent}",
            "Objective:",
            str(redact_payload(request.user_message)),
            "Constraints:",
            json.dumps(constraints, ensure_ascii=True, sort_keys=True),
            "Expected outputs:",
            json.dumps(outputs, ensure_ascii=True),
            "Validation:",
            "Required. Return evidence references and the real validation status." if request.validation_required else "Use the operation contract validation policy.",
            "Truth contract:",
            "Do not declare success before execution evidence and validation confirm the requested result.",
        ]
        risk_notes = []
        if request.risk_level in {"high", "critical"}:
            risk_notes.append("Human confirmation may be required by policy before side effects.")
        return CanonicalPromptResult(
            canonical_prompt="\n".join(sections),
            requires_confirmation=bool(risk_notes),
            risk_notes=risk_notes,
        )

