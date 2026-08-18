from __future__ import annotations

import json

from aipinho.adapters.llm_providers.base_provider import BaseModelProvider
from aipinho.schemas.models.model_request import ModelRequest
from aipinho.schemas.models.model_response import ModelResponse, ModelUsage


class StubProvider(BaseModelProvider):
    def status(self) -> dict[str, object]:
        return {"status": "ok", "provider": "stub.local", "real_inference": False, "network": False, "tools": False}

    def invoke(self, request: ModelRequest) -> ModelResponse:
        input_chars = sum(len(message.content) for message in request.messages)
        context_items = int(request.metadata.get("context_items", 0) or 0)
        evidence_items = int(request.metadata.get("evidence_items", 0) or 0)
        purpose = str(request.metadata.get("purpose", "chat"))
        contract_type = str((request.output_contract or {}).get("contract_type", request.metadata.get("output_contract_type", "plain_text")))
        if contract_type == "json_findings":
            structured = {"findings": [], "limitations": ["stub_provider_no_real_inference"]}
            content = json.dumps(structured, sort_keys=True)
        elif contract_type == "task_preview":
            structured = {"summary": "Stub task preview only.", "allowed_actions": [], "denied_actions": [], "approval_required_for": []}
            content = json.dumps(structured, sort_keys=True)
        elif contract_type == "markdown_report":
            structured = None
            evidence_lines = self._evidence_lines(request)
            evidence_block = "\n".join(evidence_lines) if evidence_lines else "- No external evidence references were provided to the stub."
            content = (
                "# Executive Summary\n"
                "Stub report generated from provided context only.\n"
                "# Findings\n"
                "No model-generated findings were added.\n"
                "# Recommendations\n"
                "Keep deterministic validation before execution.\n"
                "# Limitations\n"
                "stub_provider_no_real_inference.\n"
                "# Evidence\n"
                f"{evidence_block}"
            )
        elif contract_type == "artifact_preview":
            structured = None
            content = "# Summary\nArtifact preview only; no file was written.\n# Limitations\nstub_provider_no_real_inference"
        else:
            structured = None
            if purpose in {"project_report", "code_analysis"}:
                content = f"Stub response: received {context_items} context items and {evidence_items} evidence items. No real inference was performed."
            else:
                content = "Stub response: prompt assembled successfully. No real LLM was invoked."
        output_chars = len(content)
        return ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            status="completed",
            content=content,
            structured_output=structured,
            usage=ModelUsage(input_chars=input_chars, output_chars=output_chars, estimated_input_tokens=max(1, input_chars // 4), estimated_output_tokens=max(1, output_chars // 4)),
            finish_reason="stop",
            real_inference=False,
            warnings=["stub_model_used", "no_real_inference"],
            trace=[{"stage": "stub_provider", "status": "completed", "reason": "deterministic_stub_response"}],
        )

    def _evidence_lines(self, request: ModelRequest) -> list[str]:
        context = request.metadata.get("evidence_context", [])
        if not isinstance(context, list):
            return []
        lines: list[str] = []
        for index, item in enumerate(context[:20], start=1):
            if not isinstance(item, dict):
                continue
            ref = item.get("evidence_id") or item.get("id") or item.get("source_id") or item.get("path") or item.get("file") or item.get("source") or item.get("relative_path")
            if ref:
                lines.append(f"- Evidence {index}: {ref}")
        return lines
