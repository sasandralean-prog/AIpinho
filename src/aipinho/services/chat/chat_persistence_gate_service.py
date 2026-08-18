from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision


class ChatPersistenceGateService:
    FINAL_TYPES = {"assistant_final_answer", "assistant_degraded_answer", "system_diagnostic_result"}
    FINAL_STATUSES = {"ok", "ready"}

    def decorate(self, response: ChatResponse, decision: ChatOperationDecision) -> ChatResponse:
        message_type = response.message_type
        final_grounded_ready = bool(
            response.status in self.FINAL_STATUSES
            and response.grounded
            and (response.artifact_links or response.citation_map or response.evidence_refs)
        )
        if message_type == "assistant_final_answer" and decision.message_type != "assistant_final_answer" and not final_grounded_ready:
            message_type = decision.message_type  # type: ignore[assignment]
        is_final = message_type in self.FINAL_TYPES and response.status in self.FINAL_STATUSES
        if message_type in {"task_preview", "artifact_offer", "artifact_preview"}:
            is_final = False
        updates: dict[str, Any] = {
            "operation_id": response.operation_id or decision.operation_id,
            "operation_type": response.operation_type or decision.operation_type,
            "message_type": message_type,
            "is_final_answer": bool(response.is_final_answer and is_final),
            "requires_user_action": bool(response.requires_user_action or message_type in {"task_preview", "artifact_offer", "artifact_preview", "clarification_request"}),
        }
        if response.task_preview_id is None and response.preview_id is not None and message_type == "task_preview":
            updates["task_preview_id"] = response.preview_id
        if response.artifact_preview_id is None and response.preview_id is not None and message_type in {"artifact_offer", "artifact_preview"}:
            updates["artifact_preview_id"] = response.preview_id
        if message_type in {"task_preview", "artifact_offer", "artifact_preview"}:
            updates["grounded"] = bool(response.grounded and response.evidence_refs)
            updates["grounding_required"] = True
            updates["grounding_missing_reason"] = response.grounding_missing_reason or "operation_preview_not_final_result"
        return response.model_copy(update=updates)

    def assistant_task_id(self, response: ChatResponse) -> str | None:
        return response.task_id

    def metadata(self, response: ChatResponse, decision: ChatOperationDecision) -> dict[str, str]:
        approval_required = bool(response.policy.get("approval_required_for", [])) or bool(response.approval_id)
        rag_used = bool(response.citation_map)
        memory_used = bool(response.intent.get("memory_used", False))
        data = {
            "source": "chat_service",
            "chat_response_id": response.response_id,
            "chat_response_status": response.status,
            "status": response.status,
            "operational_session_id": response.session_id or "",
            "intent_type": str(response.intent.get("intent_type", "unknown")),
            "requires_task": str(bool(response.intent.get("requires_task", False))),
            "approval_required": str(approval_required),
            "rag_used": str(rag_used),
            "memory_used": str(memory_used),
            "fallback_used": str(bool(response.fallback_used)),
            "real_inference": str(bool(response.real_inference)),
            "message_type": str(response.message_type),
            "operation_type": str(response.operation_type or decision.operation_type),
            "operation_id": str(response.operation_id or decision.operation_id),
            "requires_user_action": str(bool(response.requires_user_action)),
            "is_final_answer": str(bool(response.is_final_answer)),
            "grounded": str(bool(response.grounded)),
            "grounding_required": str(bool(response.grounding_required)),
            "raw_available": "False",
        }
        optional = {
            "task_preview_id": response.task_preview_id,
            "task_draft_id": response.task_draft_id,
            "preview_id": response.preview_id,
            "task_id": response.task_id,
            "approval_id": response.approval_id,
            "artifact_id": response.artifact_id,
            "artifact_preview_id": response.artifact_preview_id,
            "result_ref_id": response.result_ref_id,
            "grounding_missing_reason": response.grounding_missing_reason,
        }
        for key, value in optional.items():
            if value:
                data[key] = str(value)
        for key in ("workspace_id", "workspace_role", "workspace_ref", "workspace_path", "file_path"):
            value = response.policy.get(key)
            if value:
                data[key] = str(value)
        if response.artifact_links:
            primary = response.artifact_links[0]
            data["artifact_id"] = primary.artifact_id
            data["artifact_filename"] = primary.filename
            data["artifact_content_type"] = primary.content_type
            data["artifact_size_bytes"] = str(primary.size_bytes or "")
            data["artifact_download_endpoint"] = primary.download_endpoint
            data["artifact_download_path"] = primary.download_path
            data["artifact_link_count"] = str(len(response.artifact_links))
            data["artifact_links_json"] = json.dumps(
                [
                    {
                        "artifact_id": link.artifact_id,
                        "filename": link.filename,
                        "content_type": link.content_type,
                        "size_bytes": link.size_bytes,
                        "download_endpoint": link.download_endpoint,
                        "download_path": link.download_path,
                        "label": link.label,
                        "requires_token": link.requires_token,
                    }
                    for link in response.artifact_links
                    if link.artifact_id
                ],
                ensure_ascii=True,
                separators=(",", ":"),
            )
        if response.policy_block is not None:
            block = response.policy_block
            data.update(
                {
                    "policy_block_id": block.block_id,
                    "policy_block_reason_code": block.block_reason_code,
                    "policy_block_human_reason": block.human_reason,
                    "policy_block_name": block.policy_name,
                    "policy_block_trace_id": block.trace_id or "",
                    "policy_block_event_id": block.event_id or "",
                    "policy_block_requires_user_action": str(block.requires_user_action),
                    "blocked_stage": block.blocked_stage or "",
                    "source_read_status": block.source_read_status or "",
                    "artifact_output_status": block.artifact_output_status or "",
                    "approval_status": block.approval_status or "",
                    "validation_status": block.validation_status or "",
                    "validation_id": block.validation_id or "",
                    "policy_block_safe_alternatives_json": json.dumps(block.safe_alternatives, ensure_ascii=True),
                }
            )
        attached_artifact_ids = response.intent.get("attached_artifact_ids")
        if isinstance(attached_artifact_ids, list) and attached_artifact_ids:
            data["attached_artifact_ids"] = ",".join(str(item) for item in attached_artifact_ids)
            data["attached_artifact_count"] = str(len(attached_artifact_ids))
        return data
