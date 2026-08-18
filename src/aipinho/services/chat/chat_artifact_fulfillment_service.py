from __future__ import annotations

from typing import Any

from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactPathArchiveRequest, ArtifactUploadRequest, ArtifactZipRequest, TaskRunArtifactExportRequest
from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.schemas.chat.chat_response import ChatArtifactLink, ChatNextAction, ChatResponse
from aipinho.services.artifacts.artifact_path_archive_service import ArtifactPathArchiveService
from aipinho.services.artifacts.artifact_interaction_core import ArtifactUploadService, ArtifactZipService
from aipinho.services.artifacts.task_run_artifact_export_service import TaskRunArtifactExportService
from aipinho.services.chat.blocked_policy_response_service import BlockedPolicyResponseService
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


class ChatArtifactFulfillmentService:
    """Fulfills governed chat requests that ask for an operational result as an artifact."""

    def __init__(
        self,
        runtime: TaskRuntimeService | None = None,
        exporter: TaskRunArtifactExportService | None = None,
        uploader: ArtifactUploadService | None = None,
        zipper: ArtifactZipService | None = None,
        path_archiver: ArtifactPathArchiveService | None = None,
        blocked_responses: BlockedPolicyResponseService | None = None,
    ) -> None:
        self.runtime = runtime or TaskRuntimeService()
        self.exporter = exporter or TaskRunArtifactExportService()
        self.uploader = uploader or ArtifactUploadService()
        self.zipper = zipper or ArtifactZipService()
        self.path_archiver = path_archiver or ArtifactPathArchiveService()
        self.blocked_responses = blocked_responses or BlockedPolicyResponseService()

    def fulfill_response_artifact(
        self,
        *,
        session_id: str,
        decision: ChatOperationDecision,
        factual_response: ChatResponse | None,
    ) -> ChatResponse:
        if factual_response is None or factual_response.status != "ok" or not factual_response.message.strip():
            return self._degraded(
                session_id=session_id,
                decision=decision,
                message="Preciso de um conteudo final confiavel antes de gerar um artifact. Nenhum arquivo foi criado.",
                warnings=["artifact_source_content_missing"],
            )
        filenames = self._filenames(decision.metadata.get("requested_output"))
        text_filename = filenames.get("text") or self._default_filename("text_filename")
        package_filename = filenames.get("package") or self._default_filename("package_filename")
        upload = self.uploader.upload(
            ArtifactUploadRequest(
                filename=text_filename,
                content=factual_response.message.strip() + "\n",
                content_type="text/plain; charset=utf-8",
                metadata={
                    "source_type": "chat_response",
                    "source_response_id": factual_response.response_id,
                    "operation_id": decision.operation_id,
                },
            )
        )
        links: list[ChatArtifactLink] = [
            ChatArtifactLink(
                artifact_id=upload.artifact.artifact_id,
                filename=upload.artifact.filename,
                content_type=upload.artifact.content_type,
                size_bytes=upload.artifact.size_bytes,
                download_endpoint=upload.download_path,
                download_path=upload.download_path,
                label=f"Baixar {upload.artifact.filename}",
            )
        ]
        requested_output = decision.metadata.get("requested_output")
        package_requested = isinstance(requested_output, dict) and requested_output.get("package_format") == "zip"
        if package_requested:
            zipped = self.zipper.create(ArtifactZipRequest(artifact_ids=[upload.artifact.artifact_id], filename=package_filename))
            links.insert(
                0,
                ChatArtifactLink(
                    artifact_id=zipped.artifact.artifact_id,
                    filename=zipped.artifact.filename,
                    content_type=zipped.artifact.content_type,
                    size_bytes=zipped.artifact.size_bytes,
                    download_endpoint=zipped.download_path,
                    download_path=zipped.download_path,
                    label=f"Baixar {zipped.artifact.filename}",
                ),
            )
        message = (
            f"{factual_response.message.strip()}\n\n"
            f"Artifact pronto: {links[0].filename}\n"
            f"Link: {links[0].download_path}"
        )
        return factual_response.model_copy(update={
            "response_id": decision.operation_id,
            "session_id": session_id,
            "status": "ok",
            "message": message,
            "intent": {"intent_type": "artifact_request", "requires_task": False, "requires_workspace": False},
            "policy": {"approval_required_for": [], "workspace_write": False, "validation_status": "passed"},
            "artifact_id": links[0].artifact_id,
            "artifact_links": links,
            "evidence_refs": [{"type": "artifact", "ref_id": links[0].artifact_id}],
            "next_actions": [ChatNextAction(type="download_artifact", label=links[0].label, target_id=links[0].artifact_id)],
            "warnings": list(dict.fromkeys([*factual_response.warnings, "artifact_generated_from_chat_response"])),
            "message_type": "assistant_final_answer",
            "operation_type": self._routed_operation_type(decision),
            "operation_id": decision.operation_id,
            "requires_user_action": False,
            "is_final_answer": True,
            "grounded": True,
            "grounding_required": True,
        })

    def fulfill_filesystem_archive(
        self,
        *,
        session_id: str,
        decision: ChatOperationDecision,
    ) -> ChatResponse:
        requested_output = decision.metadata.get("requested_output")
        filenames = self._filenames(requested_output)
        source_paths = self._source_paths(decision.metadata)
        archive_filename = filenames.get("package") or self._default_archive_filename(source_paths)
        try:
            archive = self.path_archiver.create(
                ArtifactPathArchiveRequest(
                    source_paths=source_paths,
                    filename=archive_filename,
                    operation_id=decision.operation_id,
                    metadata={"source": "persistent_chat", "operation_type": decision.operation_type},
                )
            )
        except ValueError as exc:
            return self._blocked(
                session_id=session_id,
                decision=decision,
                block_reason_code="filesystem_archive_blocked",
                human_reason="A origem solicitada nao passou pela policy de leitura e empacotamento.",
                safe_alternatives=["Escolha um workspace registrado para leitura ou revise a policy aplicavel."],
                warnings=[str(exc)],
                requested_capability="read_workspace",
                requested_action="create_artifact_archive",
            )

        link = ChatArtifactLink(
            artifact_id=archive.artifact.artifact_id,
            filename=archive.artifact.filename,
            content_type=archive.artifact.content_type,
            size_bytes=archive.artifact.size_bytes,
            download_endpoint=archive.download_path,
            download_path=archive.download_path,
            label=f"Baixar {archive.artifact.filename}",
        )
        included_count = len(archive.included_paths)
        skipped_count = len(archive.skipped_paths)
        skipped_text = f" {skipped_count} item(ns) foram pulados por policy." if skipped_count else ""
        message = (
            f"Preparei o arquivo {archive.artifact.filename} com {included_count} item(ns) validado(s)."
            f"{skipped_text}\n\n"
            f"Download: {archive.download_path}"
        )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="ok",
            message=message,
            intent={
                "intent_type": "filesystem_archive_request",
                "requires_task": False,
                "requires_workspace": True,
                "requires_patch": False,
                "source_path_count": len(source_paths),
            },
            policy={"approval_required_for": [], "read_only": True, "workspace_write": False, "validation_status": "passed"},
            artifact_id=archive.artifact.artifact_id,
            artifact_links=[link],
            evidence_refs=[{"type": "artifact", "ref_id": archive.artifact.artifact_id}],
            next_actions=[ChatNextAction(type="download_artifact", label=link.label, target_id=link.artifact_id)],
            warnings=list(dict.fromkeys([*archive.warnings, "artifact_generated_from_filesystem_archive"])),
            message_type="assistant_final_answer",
            operation_type=self._routed_operation_type(decision),
            operation_id=decision.operation_id,
            requires_user_action=False,
            is_final_answer=True,
            grounded=True,
            grounding_required=True,
        )

    @staticmethod
    def _routed_operation_type(decision: ChatOperationDecision) -> str:
        return str(decision.metadata.get("router_operation_type") or decision.operation_type)

    def fulfill_readonly_analysis(
        self,
        *,
        session_id: str,
        prompt: str,
        decision: ChatOperationDecision,
    ) -> ChatResponse:
        from aipinho.services.chat.chat_service import ChatService

        analysis_prompt = prompt.strip() or (decision.primary_prompt or prompt)
        base = ChatService().respond(
            ChatRequest(
                message=analysis_prompt,
                mode="preview",
                include_trace=False,
                context=ChatContext(surface="mobile", active_workspace=decision.workspace),
            )
        )
        preview_id = base.preview_id or base.task_preview_id
        if not preview_id:
            return self._degraded(
                session_id=session_id,
                decision=decision,
                message="Nao consegui criar um preview read-only confiavel para gerar o artefato. Nenhum arquivo foi criado.",
                warnings=[*base.warnings, "task_preview_missing_for_artifact_fulfillment"],
            )

        run = self.runtime.create_from_preview(preview_id)
        if run.status == "waiting_input" and run.approval_id:
            return self._pending_approval(
                session_id=session_id,
                decision=decision,
                task_id=self._task_id_for_run(run),
                approval_id=run.approval_id,
            )
        if run.status == "blocked":
            return self._blocked_from_run(session_id=session_id, decision=decision, run=run)

        run, result = self.runtime.start(run.run_id)
        if run.status == "blocked":
            return self._blocked_from_run(session_id=session_id, decision=decision, run=run, result=result)
        if run.status not in {"completed", "partial"} or result is None:
            return self._degraded(
                session_id=session_id,
                decision=decision,
                message=f"A analise terminou com status {run.status}. Nao gerei link de download porque nao houve resultado validado.",
                task_id=self._task_id_for_run(run),
                warnings=[f"task_run_status:{run.status}", "artifact_not_created_without_validated_result"],
            )
        validation = result.validation if isinstance(result.validation, dict) else {}
        if validation.get("status") in {"failed", "rejected"}:
            event_id = self._emit_task_event(
                run.run_id,
                "validation_failed",
                "Validation failed before artifact export.",
                {"validation": validation},
            )
            return self.blocked_responses.build(
                session_id=session_id,
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                task_id=self._task_id_for_run(run),
                policy_name="validation_gate",
                block_reason_code="validation_failed",
                human_reason="A analise terminou, mas a validacao falhou antes da exportacao.",
                safe_alternatives=["Consulte os checks de validacao e corrija a causa indicada."],
                requested_capability="artifact_output",
                requested_action="export_artifact",
                evidence_refs=[{"type": "validation", "ref_id": str(validation.get("validation_id") or run.run_id)}],
                warnings=["validation_failed"],
                blocked_stage="validation_failed",
                validation_status=str(validation.get("status")),
                validation_id=validation.get("validation_id"),
                artifact_output_status="not_created",
                trace_id=f"task-runs/{run.run_id}/trace",
                event_id=event_id,
            )

        filenames = self._filenames(decision.metadata.get("requested_output"))
        try:
            export = self.exporter.export(
                run.run_id,
                TaskRunArtifactExportRequest(
                    summary_filename=filenames.get("text"),
                    zip_filename=filenames.get("package"),
                ),
            )
        except ValueError as exc:
            event_id = self._emit_task_event(
                run.run_id,
                "artifact_failed",
                "Artifact export was blocked.",
                {"reason": str(exc)},
            )
            return self.blocked_responses.build(
                session_id=session_id,
                operation_id=decision.operation_id,
                operation_type=decision.operation_type,
                task_id=self._task_id_for_run(run),
                policy_name="artifact_output_policy",
                block_reason_code="artifact_export_blocked",
                human_reason="A analise terminou, mas a exportacao do artefato foi bloqueada pela validacao.",
                safe_alternatives=["Consulte a validacao do TaskRun e solicite uma nova exportacao quando o resultado estiver elegivel."],
                warnings=["artifact_export_blocked", str(exc)],
                requested_capability="artifact_output",
                requested_action="export_artifact",
                blocked_stage="artifact_output_policy",
                artifact_output_status="not_created",
                validation_status=str(validation.get("status") or "unknown"),
                validation_id=validation.get("validation_id"),
                trace_id=f"task-runs/{run.run_id}/trace",
                event_id=event_id,
            )

        artifact_links = [
            ChatArtifactLink(
                artifact_id=export.zip_artifact.artifact_id,
                filename=export.zip_artifact.filename,
                content_type=export.zip_artifact.content_type,
                size_bytes=export.zip_artifact.size_bytes,
                download_endpoint=export.zip_download_path,
                download_path=export.zip_download_path,
                label=f"Baixar {export.zip_artifact.filename}",
            ),
            ChatArtifactLink(
                artifact_id=export.summary_artifact.artifact_id,
                filename=export.summary_artifact.filename,
                content_type=export.summary_artifact.content_type,
                size_bytes=export.summary_artifact.size_bytes,
                download_endpoint=export.summary_download_path,
                download_path=export.summary_download_path,
                label=f"Baixar {export.summary_artifact.filename}",
            ),
        ]
        message = (
            "Analise read-only concluida e artefato gerado.\n\n"
            f"Resumo: {result.summary}\n\n"
            f"Arquivo para download: {export.zip_artifact.filename}\n"
            f"Link: {export.zip_download_path}\n"
            "O workspace analisado permaneceu inalterado."
        )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="ok",
            message=message,
            intent={
                "intent_type": decision.operation_type,
                "requires_task": True,
                "requires_workspace": True,
                "requested_output": "artifact",
                "output_target": "artifact_store",
            },
            policy={
                "approval_required_for": [],
                "read_only": True,
                "workspace_write": False,
                "artifact_output": True,
                "artifact_store_separate_from_workspace": True,
            },
            task_id=self._task_id_for_run(run),
            result_ref_id=run.run_id,
            artifact_id=export.zip_artifact.artifact_id,
            artifact_links=artifact_links,
            evidence_refs=[
                {"type": "task_run", "ref_id": run.run_id},
                {"type": "artifact", "ref_id": export.zip_artifact.artifact_id},
            ],
            next_actions=[
                ChatNextAction(type="download_artifact", label=artifact_links[0].label, target_id=export.zip_artifact.artifact_id),
                ChatNextAction(type="view_task_run", label="Ver TaskRun", target_id=run.run_id),
            ],
            warnings=list(dict.fromkeys([*result.warnings, "artifact_generated_from_validated_task_run"])),
            message_type="assistant_final_answer",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            requires_user_action=False,
            is_final_answer=True,
            grounded=True,
            grounding_required=True,
        )

    def _filenames(self, requested_output: Any) -> dict[str, str]:
        if not isinstance(requested_output, dict):
            return {}
        filenames = requested_output.get("filenames")
        if not isinstance(filenames, dict):
            return {}
        return {str(key): str(value) for key, value in filenames.items() if str(value).strip()}

    def _source_paths(self, metadata: dict[str, Any]) -> list[str]:
        raw = metadata.get("source_paths")
        if not isinstance(raw, list):
            requested_output = metadata.get("requested_output")
            raw = requested_output.get("source_paths") if isinstance(requested_output, dict) else []
        return [str(item).strip() for item in raw or [] if str(item).strip()]

    def _default_archive_filename(self, source_paths: list[str]) -> str:
        if len(source_paths) == 1 and source_paths[0].strip():
            name = str(source_paths[0]).rstrip("\\/").split("\\")[-1].split("/")[-1].strip()
            if name:
                return f"{name}.zip"
        return self._default_filename("package_filename")

    def _default_filename(self, key: str) -> str:
        defaults = self.exporter.policy.get("defaults", {}) if isinstance(self.exporter.policy.get("defaults", {}), dict) else {}
        configured = str(defaults.get(key) or "").strip()
        if configured:
            return configured
        return "artifact.txt" if key == "text_filename" else "artifacts.zip"

    def _degraded(
        self,
        *,
        session_id: str,
        decision: ChatOperationDecision,
        message: str,
        warnings: list[str],
        task_id: str | None = None,
    ) -> ChatResponse:
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="degraded",
            message=message,
            intent={
                "intent_type": decision.operation_type,
                "requires_task": True,
                "requires_workspace": True,
                "output_target": "artifact_store",
            },
            policy={
                "approval_required_for": [],
                "read_only": True,
                "workspace_write": False,
                "artifact_output": True,
            },
            task_id=task_id,
            warnings=list(dict.fromkeys(warnings)),
            message_type="assistant_degraded_answer",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            requires_user_action=False,
            is_final_answer=False,
            grounded=False,
            grounding_required=True,
            grounding_missing_reason="artifact_fulfillment_incomplete",
        )

    def _pending_approval(
        self,
        *,
        session_id: str,
        decision: ChatOperationDecision,
        task_id: str,
        approval_id: str,
    ) -> ChatResponse:
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            task_id=task_id,
            approval_id=approval_id,
            status="pending_approval",
            message="A operacao esta pronta, mas precisa da sua aprovacao antes de continuar.",
            intent={"intent_type": decision.operation_type, "requires_task": True, "requires_workspace": True},
            policy={"status": "pending_approval", "approval_required": True, "approval_id": approval_id},
            next_actions=[ChatNextAction(type="review_approval", label="Revisar aprovacao", target_id=approval_id)],
            warnings=["approval_required"],
            message_type="task_status_update",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            requires_user_action=True,
            is_final_answer=False,
            grounded=True,
            grounding_required=True,
        )

    def _blocked_from_run(
        self,
        *,
        session_id: str,
        decision: ChatOperationDecision,
        run,
        result=None,
    ) -> ChatResponse:
        cause = getattr(run, "block_cause", None) or getattr(result, "block_cause", None)
        if cause is None:
            return self._blocked(
                session_id=session_id,
                decision=decision,
                task_id=self._task_id_for_run(run),
                block_reason_code=str((run.blocked_reasons or ["unknown_block_reason"])[0]),
                human_reason="A task foi bloqueada sem causa detalhada; consulte o trace para diagnostico.",
                safe_alternatives=["Abra o Debugger e consulte o trace da task."],
                warnings=list(run.blocked_reasons or ["unknown_block_reason"]),
                requested_capability="read_workspace",
                requested_action="analyze",
            )
        return self.blocked_responses.build(
            session_id=session_id,
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            task_id=self._task_id_for_run(run),
            policy_name=cause.policy_name or "task_runtime_policy",
            policy_decision_id=cause.policy_decision_id,
            block_reason_code=cause.block_reason_code,
            human_reason=cause.human_reason,
            safe_alternatives=cause.safe_alternatives,
            requested_capability=cause.capability_requested,
            requested_action="analyze",
            workspace_id=cause.workspace_id,
            workspace_role=cause.workspace_role,
            evidence_refs=cause.evidence_refs,
            warnings=list(run.blocked_reasons),
            blocked_stage=cause.blocked_stage,
            technical_reason_sanitized=cause.technical_reason_sanitized,
            source_read_status=cause.source_read_status,
            artifact_output_status=cause.artifact_output_status,
            approval_status=cause.approval_status,
            validation_status=cause.validation_status,
            validation_id=cause.validation_id,
            trace_id=cause.trace_id,
            event_id=cause.event_id,
        )

    @staticmethod
    def _task_id_for_run(run) -> str | None:
        return getattr(run, "task_id", None) or None

    def _blocked(
        self,
        *,
        session_id: str,
        decision: ChatOperationDecision,
        block_reason_code: str,
        human_reason: str,
        safe_alternatives: list[str],
        warnings: list[str],
        task_id: str | None = None,
        requested_capability: str | None = None,
        requested_action: str | None = None,
    ) -> ChatResponse:
        return self.blocked_responses.build(
            session_id=session_id,
            operation_id=decision.operation_id,
            operation_type=decision.operation_type,
            task_id=task_id,
            policy_name="artifact_and_workspace_policy",
            block_reason_code=block_reason_code,
            human_reason=human_reason,
            safe_alternatives=safe_alternatives,
            requested_capability=requested_capability,
            requested_action=requested_action,
            evidence_refs=[
                {
                    "type": "policy_decision",
                    "ref_id": block_reason_code,
                    "human_label": "Decisao de policy",
                }
            ],
            warnings=warnings,
        )

    def _emit_task_event(self, task_id: str, event_type: str, message: str, metadata: dict[str, Any]) -> str | None:
        try:
            event = self.runtime.events.create(task_id, event_type, "blocked", message, metadata=metadata)
            return event.event_id
        except Exception:
            return None
