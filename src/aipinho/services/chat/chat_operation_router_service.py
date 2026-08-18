from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.services.prompt_intelligence.path_extraction_service import PathExtractionService
from aipinho.services.prompt_intelligence.canonical_operation_service import CanonicalOperationService
from aipinho.services.semantic_runtime.semantic_intent_resolution_service import SemanticIntentResolutionService
from aipinho.utils.yaml_loader import load_yaml_file


@dataclass(frozen=True)
class ChatOperationDecision:
    operation_id: str
    operation_type: str
    message_type: str
    confidence: float
    reasons: list[str] = field(default_factory=list)
    workspace: str | None = None
    primary_prompt: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ChatOperationRouterService:
    """Classifies persistent-chat requests before they are saved as final answers."""

    def __init__(
        self,
        policy: dict[str, Any] | None = None,
        path_extractor: PathExtractionService | None = None,
        semantic_intent: SemanticIntentResolutionService | None = None,
    ) -> None:
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "chat" / "chat_operation_routing_policy.yaml",
            critical=True,
            root=PATHS.config_root / "chat",
        )
        self.path_extractor = path_extractor or PathExtractionService()
        self.canonical_operations = CanonicalOperationService()
        self.semantic_intent = semantic_intent or SemanticIntentResolutionService()

    def route(self, prompt: str, workspace_hint: str | None = None) -> ChatOperationDecision:
        text = prompt.strip()
        lowered = self._normalize_text(text)
        workspace = self._extract_workspace(text) or workspace_hint
        source_paths = self._extract_paths(text)
        semantic = self.semantic_intent.resolve(text, source_channel="chat_operation_router")
        semantic_decision = self._semantic_precedence_decision(semantic, text, lowered, workspace)
        if semantic_decision is not None:
            return semantic_decision
        planning_readonly = self._product_planning_readonly_metadata(lowered)
        if planning_readonly is not None:
            return self._decision(
                "product_planning_readonly",
                "assistant_final_answer",
                0.94,
                ["product_planning_readonly_detected", "safe_readonly_intent_override"],
                workspace=None,
                primary_prompt=text,
                metadata=planning_readonly,
            )
        phase_resume = self._phase_resume_metadata(text, lowered, workspace, source_paths)
        if phase_resume is not None:
            return self._decision(
                "governed_project_rebuild",
                "task_preview",
                0.89,
                ["phase_resume_detected", "existing_report_used_as_evidence", "implementation_plan_next"],
                workspace=str(phase_resume.get("workspace") or workspace),
                primary_prompt=text,
                metadata=phase_resume,
            )
        if self._matches_session_execution_report(lowered, has_workspace=bool(workspace)):
            return self._decision(
                "session_execution_report",
                "assistant_final_answer",
                0.86,
                ["session_execution_report_requested", "read_only_session_records_report"],
                workspace=None,
            )
        readonly_audit = self._workspace_readonly_audit_metadata(text, lowered, workspace)
        if readonly_audit is not None:
            return self._decision(
                "workspace_readonly_audit_report",
                "task_status_update",
                0.88,
                ["workspace_readonly_audit_detected", "report_output_requested", "session_diagnostic_bypassed"],
                workspace=workspace,
                primary_prompt=text,
                metadata=readonly_audit,
            )
        project_bootstrap = self._project_bootstrap_metadata(text, lowered, workspace)
        if project_bootstrap is not None:
            return self._decision(
                "project_bootstrap",
                "task_preview",
                0.91,
                ["project_bootstrap_detected", "operational_prompt_precedence_over_session_diagnostic", "preview_approval_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata=project_bootstrap,
            )
        if self._matches_session_diagnostic(lowered):
            return self._decision("session_diagnostic", "system_diagnostic_result", 0.82, ["session_diagnostic_terms_detected"], workspace=workspace)
        if self._matches_workspace_permission_list(lowered):
            return self._decision(
                "workspace_permission_list",
                "assistant_final_answer",
                0.88,
                ["workspace_permission_list_detected", "workspace_registry_query_requested"],
                workspace=None,
                primary_prompt=text,
                metadata={
                    "requested_operation": "workspace_permission_list",
                    "read_only": True,
                    "requires_task": False,
                    "requires_workspace": False,
                    "workspace_write": False,
                    "source": "workspace_registry_permission_query",
                },
            )
        if self._matches_permission_status(lowered):
            return self._decision(
                "permission_status",
                "assistant_final_answer",
                0.84,
                ["permission_status_terms_detected", "workspace_policy_status_requested"],
                workspace=None,
            )
        workspace_metadata = self._workspace_metadata_query_metadata(text, lowered, workspace)
        if workspace_metadata is not None:
            return self._decision(
                "workspace_metadata_query",
                "assistant_final_answer",
                0.9,
                ["workspace_metadata_query_detected", "explicit_no_write_constraint", "chat_only_response_requested"],
                workspace=workspace,
                primary_prompt=text,
                metadata=workspace_metadata,
            )
        config_targets = self._configuration_change_targets(lowered)
        if config_targets:
            return self._decision(
                "governed_configuration_change",
                "task_preview",
                0.86,
                ["governed_configuration_change_detected", "preview_approval_validation_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "configuration_targets": config_targets,
                    "requires_preview": True,
                    "requires_approval": True,
                    "requires_validation": True,
                    "direct_mutation_allowed": False,
                },
            )
        if self._matches_dangerous_operation(lowered, bool(workspace)):
            return self._decision(
                "dangerous_operation_blocked",
                "blocked_policy_message",
                0.92,
                ["dangerous_operation_detected", "policy_block_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"policy_name": "dangerous_operation_policy", "requested_action": "dangerous_side_effect"},
            )
        if self._matches_brainstorming_conversation(lowered):
            return self._decision(
                "simple_conversation",
                "assistant_final_answer",
                0.78,
                ["brainstorming_deferred_creation_detected", "conversation_not_task"],
                workspace=None,
                primary_prompt=text,
                metadata={"conversation_kind": "brainstorming"},
            )
        if self._matches_attachment_required_missing(lowered):
            return self._decision(
                "attachment_required_missing",
                "blocked_policy_message",
                0.86,
                ["attachment_required_terms_detected", "attachment_context_missing"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"required_input": "attachment"},
            )
        if self._matches_local_file_append(text, lowered, workspace):
            return self._decision(
                "filesystem_append_file",
                "task_status_update",
                0.88,
                ["local_file_append_detected", "filesystem_append_scope_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"requested_operation": "append_file", "workspace_write": True},
            )
        if self._matches_local_file_read(text, lowered, workspace):
            return self._decision(
                "filesystem_read_file",
                "assistant_final_answer",
                0.9,
                ["local_file_read_detected", "private_rag_not_required", "web_search_not_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"requested_operation": "read_file", "workspace_write": False},
            )
        if self._matches_contextual_file_append(lowered):
            return self._decision(
                "filesystem_append_file",
                "task_status_update",
                0.82,
                ["contextual_file_append_detected", "requires_recent_file_context"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"requested_operation": "append_file", "requires_context_path": not bool(workspace)},
            )
        if self._matches_governed_shell_request(lowered):
            shell_policy = ((self.policy.get("operations", {}) or {}).get("governed_shell_request", {}) or {})
            approval_scope = str(shell_policy.get("approval_scope") or "governed_shell")
            return self._decision(
                "governed_shell_request",
                "task_status_update",
                0.88,
                ["governed_shell_request_detected", "shell_requires_preview_approval_validation"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_operation": "run_command",
                    "requested_actions": ["run_command"],
                    "approval_scope": approval_scope,
                    "requires_tool_gateway": True,
                    "requires_validation": True,
                    "command_text": text,
                },
            )
        if self._matches_sandbox_capability_test(lowered):
            return self._decision(
                "sandbox_capability_test",
                "assistant_final_answer",
                0.84,
                ["sandbox_capability_test_requested", "ephemeral_probe_allowed"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"requested_operation": "capability_probe", "workspace_write": True},
            )
        artifact_requested = self._matches_artifact_request(lowered)
        if self._matches_sandbox_batch_artifact_request(text, lowered, workspace, artifact_requested):
            return self._decision(
                "sandbox_batch_artifact_request",
                "task_status_update",
                0.9,
                ["sandbox_path_detected_from_prompt", "sandbox_batch_artifact_request_detected", "sandbox_path_allowed"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_operation": "create_files_and_archive",
                    "requested_actions": ["create_directory", "write_files", "create_archive", "validate_artifact"],
                    "workspace_write": True,
                    "requires_validation": True,
                    "approval_scope": "sandbox_batch_artifact",
                    "requested_output": self._artifact_output_request(text, lowered),
                    "source_scope": "sandbox",
                    "reason_code": "sandbox_path_detected_from_prompt",
                },
        )
        evidence_bundle = self._workspace_evidence_bundle_metadata(text, lowered, workspace, artifact_requested)
        if evidence_bundle is not None:
            return self._decision(
                "workspace_evidence_bundle",
                "task_status_update",
                0.91,
                ["workspace_evidence_bundle_detected", "summary_and_archive_outputs_detected", "tool_gateway_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata=evidence_bundle,
            )
        reachability_report = self._workspace_static_reachability_report_metadata(text, lowered, workspace)
        if reachability_report is not None:
            return self._decision(
                "workspace_static_reachability_report",
                "task_status_update",
                0.89,
                ["static_reachability_qa_detected", "expected_text_and_report_output_detected", "tool_gateway_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata=reachability_report,
            )
        if self._matches_governed_change_plan(lowered, bool(workspace)):
            return self._decision(
                "governed_change_plan",
                "task_preview",
                0.9,
                ["governed_change_plan_detected", "referenced_files_are_evidence", "no_write_before_approval"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_actions": ["patch_preview"],
                    "output_target": "target_workspace",
                    "workspace_write": False,
                    "requires_patch_preview": True,
                    "requires_approval": True,
                    "referenced_files_role": "evidence_source",
                },
            )
        if (
            bool(workspace)
            and self._matches_implementation_execution_request(lowered)
            and not self._matches_inferred_ui_text_update(lowered)
            and not self._matches_narrow_explicit_file_edit(text, lowered)
        ):
            return self._decision(
                "governed_project_rebuild",
                "task_preview",
                0.88,
                ["governed_implementation_request_detected", "target_workspace_execution_requires_preview_approval_validation"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"output_target": "target_workspace", "requires_patch_preview": True, "requires_approval": True},
            )
        if self._matches_governed_file_write(text, lowered):
            requested_operation = self._governed_file_write_operation(text, lowered)
            target_resolution = "infer_ui_source" if self._matches_inferred_ui_text_update(lowered) and not self._requested_filenames(text) else None
            metadata = {
                "requested_operation": requested_operation,
                "workspace_write": True,
                "requires_tool_gateway": True,
                "requires_validation": True,
            }
            if target_resolution:
                metadata["target_resolution"] = target_resolution
            return self._decision(
                "governed_file_write",
                "task_status_update",
                0.88,
                ["governed_file_write_detected", "tool_gateway_write_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata=metadata,
            )
        if self._matches_governed_project_rebuild(lowered, bool(workspace)):
            return self._decision(
                "governed_project_rebuild",
                "task_preview",
                0.84,
                ["governed_project_rebuild_detected", "target_workspace_execution_requires_preview_approval_validation"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"output_target": "target_workspace", "requires_patch_preview": True, "requires_approval": True},
            )
        if artifact_requested and workspace and self._matches_explicit_workspace_output(lowered):
            requested_output = self._artifact_output_request(text, lowered)
            return self._decision(
                "workspace_artifact_write_request",
                "artifact_preview",
                0.88,
                ["explicit_workspace_output_detected", "workspace_write_requires_governed_envelope"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_output": requested_output,
                    "output_target": "workspace",
                    "workspace_write": True,
                    "artifact_generation": True,
                },
            )
        filesystem_archive_requested = self._matches_filesystem_archive_request(lowered, source_paths, artifact_requested)
        if filesystem_archive_requested:
            requested_output = self._artifact_output_request(text, lowered)
            requested_output["source_paths"] = source_paths
            return self._decision(
                "filesystem_archive_request",
                "assistant_final_answer",
                0.88,
                ["filesystem_archive_request_detected", "explicit_path_source_detected"],
                workspace=workspace,
                primary_prompt=text,
                metadata={"requested_output": requested_output, "source_paths": source_paths},
            )
        readonly_requested = self._matches_readonly_project_analysis(lowered, workspace)
        if readonly_requested:
            metadata: dict[str, Any] = {}
            reasons = ["readonly_project_analysis_detected"]
            message_type = "task_preview"
            primary_prompt = None
            confidence = 0.8
            if artifact_requested:
                metadata["requested_output"] = self._artifact_output_request(text, lowered)
                metadata["output_target"] = "artifact_store"
                metadata["workspace_write"] = False
                metadata["artifact_generation"] = True
                reasons.append("artifact_output_requested")
                reasons.append("artifact_output_separated_from_workspace_write")
                message_type = "assistant_final_answer"
                primary_prompt = self._strip_artifact_terms(text)
                confidence = 0.86
            return self._decision(
                "readonly_analysis_with_artifact_output" if artifact_requested else "readonly_project_analysis",
                message_type,
                confidence,
                reasons,
                workspace=workspace,
                primary_prompt=primary_prompt,
                metadata=metadata,
            )
        if self._matches_public_fact_query(lowered):
            return self._decision(
                "public_fact_query",
                "assistant_degraded_answer",
                0.82,
                ["public_fact_query_detected", "web_search_required_or_capability_missing"],
                workspace=None,
                primary_prompt=text,
                metadata={"requires_web_search": True, "private_rag_required": False},
            )
        specific_operation = self._specific_operational_decision(text, lowered, workspace)
        if specific_operation is not None:
            return specific_operation
        operational_task = self._matches_operational_task_request(lowered)
        if operational_task:
            requested_actions = self._operational_task_actions(lowered)
            return self._decision(
                "operational_task_request",
                "task_preview",
                0.82,
                ["operational_task_request_detected", "task_contract_preview_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_actions": requested_actions,
                    "requires_task": True,
                    "requires_policy": True,
                    "requires_capability_resolution": True,
                },
            )
        if artifact_requested:
            return self._decision(
                "artifact_request",
                "artifact_offer",
                0.78,
                ["artifact_request_terms_detected"],
                workspace=workspace,
                primary_prompt=self._strip_artifact_terms(text),
                metadata={"requested_output": self._artifact_output_request(text, lowered)},
            )
        if self._matches_followup(lowered, bool(workspace)):
            recall_kind = self._followup_recall_kind(lowered)
            return self._decision(
                "followup_result_recall",
                "assistant_final_answer",
                0.7,
                ["followup_result_recall_detected", f"recall_kind_{recall_kind}"],
                workspace=workspace,
                metadata={"recall_kind": recall_kind},
            )
        if self._matches_followup_review(lowered, bool(workspace)):
            return self._decision(
                "followup_result_review",
                "assistant_final_answer",
                0.76,
                ["followup_result_review_detected", "grounded_previous_result_review_required"],
                workspace=workspace,
                metadata={"recall_kind": "summary", "review_scope": "previous_result"},
            )
        return self._decision("simple_conversation", "assistant_final_answer", 0.55, ["default_conversation_route"], workspace=workspace)

    def _semantic_precedence_decision(
        self,
        semantic,
        text: str,
        lowered: str,
        workspace: str | None,
    ) -> ChatOperationDecision | None:
        if semantic.intent_type == "product_planning_readonly":
            metadata = self._product_planning_readonly_metadata(lowered)
            if metadata is None:
                return None
            metadata["semantic_intent"] = semantic.model_dump(mode="json")
            return self._decision(
                "product_planning_readonly",
                "assistant_final_answer",
                0.94,
                ["semantic_intent_resolution", *semantic.evidence],
                workspace=None,
                primary_prompt=text,
                metadata=metadata,
            )
        if semantic.intent_type == "workspace_permission_list":
            return self._decision(
                "workspace_permission_list",
                "assistant_final_answer",
                0.88,
                ["semantic_intent_resolution", *semantic.evidence],
                workspace=None,
                primary_prompt=text,
                metadata={
                    "requested_operation": "workspace_permission_list",
                    "read_only": True,
                    "requires_task": False,
                    "requires_workspace": False,
                    "workspace_write": False,
                    "source": "workspace_registry_permission_query",
                    "semantic_intent": semantic.model_dump(mode="json"),
                },
            )
        if semantic.intent_type == "governed_shell_request" and self._matches_governed_shell_request(lowered):
            shell_policy = ((self.policy.get("operations", {}) or {}).get("governed_shell_request", {}) or {})
            approval_scope = str(shell_policy.get("approval_scope") or "governed_shell")
            return self._decision(
                "governed_shell_request",
                "task_status_update",
                0.88,
                ["semantic_intent_resolution", *semantic.evidence],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_operation": "run_command",
                    "requested_actions": ["run_command"],
                    "approval_scope": approval_scope,
                    "requires_tool_gateway": True,
                    "requires_validation": True,
                    "command_text": text,
                    "semantic_intent": semantic.model_dump(mode="json"),
                },
            )
        return None

    def _decision(
        self,
        operation_type: str,
        message_type: str,
        confidence: float,
        reasons: list[str],
        *,
        workspace: str | None = None,
        primary_prompt: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatOperationDecision:
        payload = metadata or {}
        canonical_operation = self.canonical_operations.from_router(operation_type, payload)
        return ChatOperationDecision(
            operation_id=f"chatop_{uuid4().hex}",
            operation_type=canonical_operation,
            message_type=message_type,
            confidence=confidence,
            reasons=reasons,
            workspace=workspace,
            primary_prompt=primary_prompt,
            metadata={**payload, "router_operation_type": operation_type, "canonical_operation_type": canonical_operation},
        )

    def _operation_terms(self, operation: str, key: str) -> list[str]:
        data = (self.policy.get("operations", {}) or {}).get(operation, {}) or {}
        return [self._normalize_text(str(item)) for item in data.get(key, []) or []]

    def _extract_workspace(self, prompt: str) -> str | None:
        extracted = self.path_extractor.extract_first(prompt)
        return extracted.value if extracted else None

    def _extract_paths(self, prompt: str) -> list[str]:
        return [item.value for item in self.path_extractor.extract(prompt)]

    def _has_any(self, lowered: str, terms: list[str]) -> bool:
        return any(term and term in lowered for term in terms)

    def _has_any_bounded(self, lowered: str, terms: list[str]) -> bool:
        return any(
            term
            and re.search(
                rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])",
                lowered,
            )
            for term in terms
        )

    def _has_any_non_negated_bounded(self, lowered: str, terms: list[str]) -> bool:
        negation_terms = ("nao", "não", "sem", "nunca", "no", "without", "do not", "dont", "don't")
        for term in terms:
            if not term:
                continue
            for match in re.finditer(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])", lowered):
                prefix = lowered[max(0, match.start() - 28): match.start()]
                if any(re.search(rf"(?<![a-z0-9_]){re.escape(negation)}\s+$", prefix) for negation in negation_terms):
                    continue
                return True
        return False

    def _count_matches(self, lowered: str, terms: list[str]) -> int:
        return sum(1 for term in terms if term and term in lowered)

    def _configuration_change_targets(self, lowered: str) -> list[str]:
        operation = ((self.policy.get("operations", {}) or {}).get("governed_configuration_change", {}) or {})
        if not isinstance(operation, dict):
            return []
        action_terms = self._operation_terms("governed_configuration_change", "action_terms")
        target_groups = operation.get("target_terms", {})
        if not isinstance(target_groups, dict) or not self._has_any_non_negated_bounded(lowered, action_terms):
            return []
        targets: list[str] = []
        for target_name, terms in target_groups.items():
            normalized_terms = [self._normalize_text(str(item)) for item in terms or []]
            if self._has_any(lowered, normalized_terms):
                targets.append(str(target_name))
        return list(dict.fromkeys(targets))

    def _matches_session_diagnostic(self, lowered: str) -> bool:
        if self._matches_project_bootstrap_terms(lowered):
            return False
        operation = ((self.policy.get("operations", {}) or {}).get("session_diagnostic", {}) or {})
        explicit_terms = [
            "diagnostique esta sessao",
            "diagnosticar esta sessao",
            "diagnostico da conversa",
            "diagnostico do chat",
            "verifique o estado da sessao",
            "estado da sessao",
            "por que essa conversa falhou",
            "por que esta conversa falhou",
            "listar estado do chat",
            "debug da sessao",
            "debug do chat",
            "session diagnostic",
        ]
        if self._has_any(lowered, explicit_terms):
            return True
        terms = self._operation_terms("session_diagnostic", "terms")
        anchor_terms = self._operation_terms("session_diagnostic", "anchor_terms")
        minimum = int(operation.get("min_matches", 2))
        diagnostic_verbs = ["diagnostique", "diagnosticar", "debug", "verifique", "verificar", "investigue", "investigar"]
        session_anchors = ["sessao", "session", "conversa", "chat", "timeline", "mensagem", "resposta"]
        return (
            self._count_matches(lowered, terms) >= minimum
            and self._has_any_bounded(lowered, diagnostic_verbs)
            and self._has_any(lowered, anchor_terms)
            and self._has_any(lowered, session_anchors)
        )

    def _project_bootstrap_metadata(self, text: str, lowered: str, workspace: str | None) -> dict[str, Any] | None:
        if not self._matches_project_bootstrap_terms(lowered):
            return None
        negative_constraints = self._operation_terms("project_bootstrap", "negative_constraints")
        requested_actions = [
            "read_workspace_metadata",
            "inspect_workspace",
            "create_task_preview",
            "create_approval_request",
            "write_files",
        ]
        if self._has_any(lowered, ["apply_patch", "aplicar patch", "aplique patch", "patch"]):
            requested_actions.append("apply_patch")
        if self._has_any(lowered, ["criar arquivo", "crie arquivo", "create_file", "modify_file", "modificar arquivo"]):
            requested_actions.extend(["create_file", "modify_file"])
        return {
            "requested_operation": "project_bootstrap",
            "requested_actions": list(dict.fromkeys(requested_actions)),
            "negative_constraints": list(dict.fromkeys(negative_constraints)),
            "requires_task": True,
            "requires_policy": True,
            "requires_workspace": True,
            "requires_patch_preview": True,
            "requires_approval": True,
            "requires_validation": True,
            "workspace_write": True,
            "output_target": "target_workspace",
            "source_channel": "chat",
            "approval_scope": "project_write",
            "do_not_reuse_old_approval": self._has_any(lowered, ["nao reutilize approvals antigos", "não reutilize approvals antigos", "no_reuse_old_approval"]),
            "safety_check_as_internal_step": self._has_any(lowered, ["safety check", "safety check do hotfix"]),
            "bootstrap_title": self._project_bootstrap_title(text),
            "workspace_exists_required": False,
            "project_generation_phase": "bootstrap",
            "pre_approval_expected_outcomes": ["discovery_result", "blueprint_result", "task_preview_result", "approval_request_result"],
        }

    def _matches_project_bootstrap_terms(self, lowered: str) -> bool:
        operation = ((self.policy.get("operations", {}) or {}).get("project_bootstrap", {}) or {})
        action_terms = self._operation_terms("project_bootstrap", "action_terms")
        context_terms = self._operation_terms("project_bootstrap", "context_terms")
        min_action = int(operation.get("min_action_matches", 1))
        min_context = int(operation.get("min_context_matches", 1))
        if self._count_matches(lowered, action_terms) >= min_action and self._count_matches(lowered, context_terms) >= min_context:
            return True
        starts_operational = re.search(r"^\s*(?:aipinho\s*[—\-:]\s*)?(?:iniciar|inicie|criar|crie|implementar|implemente)\s+(?:projeto|sprint|mvp|blueprint)", lowered)
        return bool(starts_operational and self._has_any(lowered, context_terms))

    def _project_bootstrap_title(self, text: str) -> str | None:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        if not first_line:
            return None
        return re.sub(r"\s+", " ", first_line).strip(" .:-")[:160]

    def _matches_session_execution_report(self, lowered: str, *, has_workspace: bool = False) -> bool:
        if has_workspace:
            return False
        operation = ((self.policy.get("operations", {}) or {}).get("session_execution_report", {}) or {})
        report_terms = self._operation_terms("session_execution_report", "report_terms")
        execution_terms = self._operation_terms("session_execution_report", "execution_terms")
        min_report = int(operation.get("min_report_matches", 1))
        min_execution = int(operation.get("min_execution_matches", 1))
        return self._count_matches(lowered, report_terms) >= min_report and self._count_matches(lowered, execution_terms) >= min_execution

    def _product_planning_readonly_metadata(self, lowered: str) -> dict[str, Any] | None:
        operation = ((self.policy.get("operations", {}) or {}).get("product_planning_readonly", {}) or {})
        explicit_terms = self._operation_terms("product_planning_readonly", "explicit_intent_terms")
        planning_terms = self._operation_terms("product_planning_readonly", "planning_terms")
        safety_terms = self._operation_terms("product_planning_readonly", "safety_terms")
        explicit = self._has_any(lowered, explicit_terms)
        signal_count = self._count_matches(lowered, [*planning_terms, *safety_terms])
        minimum = int(operation.get("min_signal_matches", 2))
        if not explicit and signal_count < minimum:
            return None
        if not explicit and not (self._has_any(lowered, planning_terms) and self._has_any(lowered, safety_terms)):
            return None
        return {
            "requested_operation": "product_planning_readonly",
            "intent_type": "product_planning_readonly",
            "requires_task": False,
            "requires_workspace": False,
            "requires_patch": False,
            "approval_required": False,
            "side_effect": False,
            "write_allowed": False,
            "shell_allowed": False,
            "read_only": True,
            "workspace_write": False,
            "explicit_safe_intent_override": explicit,
            "planning_signal_count": signal_count,
            "router_operation_type": "product_planning_readonly",
        }

    def _matches_workspace_permission_list(self, lowered: str) -> bool:
        operation = ((self.policy.get("operations", {}) or {}).get("workspace_permission_list", {}) or {})
        action_terms = self._operation_terms("workspace_permission_list", "action_terms")
        target_terms = self._operation_terms("workspace_permission_list", "target_terms")
        minimum = int(operation.get("min_signal_matches", 2))
        signals = self._count_matches(lowered, [*action_terms, *target_terms])
        return signals >= minimum and self._has_any(lowered, target_terms)

    def _matches_permission_status(self, lowered: str) -> bool:
        operation = ((self.policy.get("operations", {}) or {}).get("permission_status", {}) or {})
        action_terms = self._operation_terms("permission_status", "action_terms")
        permission_terms = self._operation_terms("permission_status", "permission_terms")
        target_terms = self._operation_terms("permission_status", "target_terms")
        minimum = int(operation.get("min_matches", 2))
        total = self._count_matches(lowered, [*action_terms, *permission_terms, *target_terms])
        action_match = self._has_any_bounded(lowered, action_terms)
        target_match = self._has_any(lowered, target_terms) or self._has_fuzzy_token_match(
            lowered,
            target_terms,
            threshold=float(operation.get("fuzzy_target_threshold", 0.78)),
        )
        return total >= minimum and action_match and self._has_any(lowered, permission_terms) and target_match

    def _matches_dangerous_operation(self, lowered: str, has_workspace: bool) -> bool:
        destructive_terms = self._operation_terms("dangerous_operation", "destructive_terms")
        git_terms = self._operation_terms("dangerous_operation", "git_write_terms")
        target_terms = self._operation_terms("dangerous_operation", "target_terms")
        if self._has_any_non_negated_bounded(lowered, git_terms):
            return True
        if not self._has_any_non_negated_bounded(lowered, destructive_terms):
            return False
        return has_workspace or self._has_any(lowered, target_terms)

    def _matches_brainstorming_conversation(self, lowered: str) -> bool:
        action_terms = self._operation_terms("brainstorming_conversation", "action_terms")
        defer_terms = self._operation_terms("brainstorming_conversation", "defer_terms")
        return self._has_any(lowered, action_terms) and self._has_any(lowered, defer_terms)

    def _matches_attachment_required_missing(self, lowered: str) -> bool:
        terms = self._operation_terms("attachment_required_missing", "requirement_terms")
        return self._has_any(lowered, terms)

    def _matches_local_file_read(self, prompt: str, lowered: str, workspace: str | None) -> bool:
        if not workspace or not re.search(r"\.[A-Za-z0-9]{1,12}$", workspace):
            return False
        if self._phase_resume_metadata(prompt, lowered, workspace, self._extract_paths(prompt)) is not None:
            return False
        action_terms = self._operation_terms("local_file_read", "action_terms")
        content_terms = self._operation_terms("local_file_read", "content_terms")
        return self._has_any(lowered, action_terms) and self._has_any(lowered, content_terms)

    def _phase_resume_metadata(self, prompt: str, lowered: str, workspace: str | None, source_paths: list[str]) -> dict[str, Any] | None:
        operation = ((self.policy.get("operations", {}) or {}).get("phase_resume_implementation", {}) or {})
        if not isinstance(operation, dict):
            return None
        action_terms = self._operation_terms("phase_resume_implementation", "action_terms")
        evidence_terms = self._operation_terms("phase_resume_implementation", "evidence_terms")
        if not self._has_any(lowered, action_terms) or not self._has_any(lowered, evidence_terms):
            return None
        evidence_path = self._phase_resume_evidence_path(source_paths, workspace, operation)
        if evidence_path is None:
            return None
        evidence = Path(evidence_path)
        inferred_workspace = workspace
        if evidence.suffix.casefold() in {".md", ".txt", ".json"} and evidence.parent.name.casefold() in {"reports", "report", "relatorios", "relatorios"}:
            inferred_workspace = str(evidence.parent.parent)
        if not inferred_workspace:
            return None
        return {
            "requested_operation": "continue_from_existing_report",
            "output_target": "target_workspace",
            "requires_patch_preview": True,
            "requires_approval": True,
            "workspace_write": True,
            "phase_resume": {
                "completed_phase": "preflight",
                "next_phase": str(operation.get("next_phase") or "implementation_plan"),
                "evidence_report_path": evidence_path,
                "evidence_exists": Path(evidence_path).exists(),
            },
            "referenced_files_role": "evidence_source",
            "evidence_report_path": evidence_path,
            "workspace": inferred_workspace,
        }

    def _phase_resume_evidence_path(self, source_paths: list[str], workspace: str | None, operation: dict[str, Any]) -> str | None:
        for value in source_paths:
            try:
                path = Path(value)
            except (OSError, ValueError):
                continue
            if path.suffix.casefold() not in {".md", ".txt", ".json"}:
                continue
            if path.parent.name.casefold() in {"reports", "report", "relatorios", "relatorios"}:
                return value
        if workspace:
            try:
                root = Path(workspace)
            except (OSError, ValueError):
                root = None
            if root is not None and root.exists() and root.is_dir():
                globs = [str(item) for item in operation.get("evidence_globs", []) or []]
                for pattern in globs:
                    for candidate in sorted(root.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True):
                        if candidate.is_file():
                            return str(candidate)
        return None

    def _matches_local_file_append(self, prompt: str, lowered: str, workspace: str | None) -> bool:
        if not workspace or not re.search(r"\.[A-Za-z0-9]{1,12}$", workspace):
            return False
        action_terms = self._operation_terms("contextual_file_append", "action_terms")
        return self._has_any(lowered, action_terms)

    def _workspace_metadata_query_metadata(self, prompt: str, lowered: str, workspace: str | None) -> dict[str, Any] | None:
        if not workspace:
            return None
        operation = ((self.policy.get("operations", {}) or {}).get("workspace_metadata_query", {}) or {})
        action_terms = self._operation_terms("workspace_metadata_query", "action_terms")
        metadata_terms = self._operation_terms("workspace_metadata_query", "metadata_terms")
        no_write_terms = self._operation_terms("workspace_metadata_query", "no_write_terms")
        chat_only_terms = self._operation_terms("workspace_metadata_query", "chat_only_terms")
        has_inspection_action = self._has_any_non_negated_bounded(lowered, action_terms) or self._has_any(lowered, chat_only_terms)
        if not has_inspection_action:
            return None
        signal_count = self._count_matches(lowered, [*action_terms, *metadata_terms, *chat_only_terms])
        if signal_count < int(operation.get("min_signal_matches", 2)):
            return None
        if not self._has_any(lowered, no_write_terms):
            return None
        requested_files = self._metadata_query_requested_files(prompt)
        return {
            "requested_operation": "inspect_workspace_metadata",
            "workspace_write": False,
            "requires_task": False,
            "requires_patch": False,
            "requires_artifact": False,
            "read_only": True,
            "chat_only": self._has_any(lowered, chat_only_terms),
            "requested_files": requested_files,
            "entrypoint_patterns": [str(item) for item in operation.get("entrypoint_patterns", []) or []],
        }

    def _metadata_query_requested_files(self, prompt: str) -> list[str]:
        candidates: list[str] = []
        for match in re.finditer(
            r"(?<![A-Za-z0-9._-])([A-Za-z0-9][A-Za-z0-9._-]{0,119}\.[A-Za-z0-9]{1,12})(?!(?:[A-Za-z0-9_-]|\.[A-Za-z0-9]))",
            prompt,
            flags=re.IGNORECASE,
        ):
            name = match.group(1).strip(" .,:;")
            if name and name not in candidates:
                candidates.append(name)
        return candidates

    def _matches_contextual_file_append(self, lowered: str) -> bool:
        action_terms = self._operation_terms("contextual_file_append", "action_terms")
        reference_terms = self._operation_terms("contextual_file_append", "reference_terms")
        return self._has_any(lowered, action_terms) and self._has_any(lowered, reference_terms)

    def _matches_sandbox_capability_test(self, lowered: str) -> bool:
        action_terms = self._operation_terms("sandbox_capability_test", "action_terms")
        capability_terms = self._operation_terms("sandbox_capability_test", "capability_terms")
        write_terms = self._operation_terms("sandbox_capability_test", "write_terms")
        return self._has_any_bounded(lowered, action_terms) and self._has_any_bounded(lowered, capability_terms) and self._has_any_bounded(lowered, write_terms)

    def _matches_sandbox_batch_artifact_request(self, prompt: str, lowered: str, workspace: str | None, artifact_requested: bool) -> bool:
        if not artifact_requested or not workspace or not self._is_sandbox_path(workspace):
            return False
        action_terms = self._operation_terms("sandbox_batch_artifact_request", "action_terms")
        directory_terms = self._operation_terms("sandbox_batch_artifact_request", "directory_terms")
        file_terms = self._operation_terms("sandbox_batch_artifact_request", "file_terms")
        package_terms = self._operation_terms("sandbox_batch_artifact_request", "package_terms")
        has_action = self._has_any(lowered, action_terms)
        has_directory = self._has_any(lowered, directory_terms)
        has_files = self._has_any(lowered, file_terms) or bool(self._requested_filenames(prompt))
        has_package = self._has_any(lowered, package_terms)
        return has_action and has_directory and has_files and has_package

    def _matches_governed_file_write(self, prompt: str, lowered: str) -> bool:
        extracted = self._extract_workspace(prompt)
        if extracted and re.search(r"\.[A-Za-z0-9]{1,12}$", extracted):
            return False
        if self._matches_artifact_request(lowered) and self._matches_readonly_project_analysis(lowered, self._extract_workspace(prompt)):
            return False
        operation = ((self.policy.get("operations", {}) or {}).get("governed_file_write", {}) or {})
        action_terms = [
            *self._operation_terms("governed_file_write", "action_terms"),
            *self._operation_terms("governed_file_write", "modify_action_terms"),
        ]
        file_terms = self._operation_terms("governed_file_write", "file_terms")
        min_action = int(operation.get("min_action_matches", 1))
        has_action = self._count_matches(lowered, action_terms) >= min_action
        if has_action and self._matches_inferred_ui_text_update(lowered):
            return True
        has_file_term = self._has_any_bounded(lowered, file_terms)
        requested_filenames = self._requested_filenames(prompt)
        has_filename = bool(requested_filenames) or bool(
            re.search(
                r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12})(?![A-Za-z0-9_.-])",
                prompt,
            )
        )
        local_output_markers = (
            "workspace",
            "pasta",
            "diretorio",
            "diretório",
            "dentro de",
            "dentro do",
            "dentro da",
            "nesse diret",
            "neste diret",
            "nessa pasta",
            "nesta pasta",
        )
        has_workspace_context = bool(self._extract_workspace(prompt)) or any(marker in lowered for marker in local_output_markers)
        has_relative_output_target = bool(
            re.search(
                r"(?:em|para|at|to)\s*[:=]?\s*[`\"']?[A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12}",
                prompt,
                flags=re.IGNORECASE,
            )
        )
        if has_action and has_filename and self._additive_term_targets_existing_file(prompt, lowered):
            return True
        if not has_workspace_context and not has_relative_output_target:
            return False
        return has_action and has_filename and has_file_term

    def _matches_governed_shell_request(self, lowered: str) -> bool:
        operation = ((self.policy.get("operations", {}) or {}).get("governed_shell_request", {}) or {})
        action_terms = self._operation_terms("governed_shell_request", "action_terms")
        command_terms = self._operation_terms("governed_shell_request", "command_terms")
        min_action = int(operation.get("min_action_matches", 1))
        min_command = int(operation.get("min_command_matches", 1))
        return (
            self._count_matches(lowered, action_terms) >= min_action
            and self._count_matches(lowered, command_terms) >= min_command
        )

    def _matches_governed_change_plan(self, lowered: str, has_workspace: bool) -> bool:
        if not has_workspace:
            return False
        operation = ((self.policy.get("operations", {}) or {}).get("governed_change_plan", {}) or {})
        action_terms = self._operation_terms("governed_change_plan", "action_terms")
        preview_terms = self._operation_terms("governed_change_plan", "preview_terms")
        defer_terms = self._operation_terms("governed_change_plan", "defer_terms")
        return (
            self._count_matches(lowered, action_terms) >= int(operation.get("min_action_matches", 1))
            and self._count_matches(lowered, preview_terms) >= int(operation.get("min_preview_matches", 1))
            and self._count_matches(lowered, defer_terms) >= int(operation.get("min_defer_matches", 1))
        )

    def _governed_file_write_operation(self, prompt: str, lowered: str) -> str:
        modify_terms = self._operation_terms("governed_file_write", "modify_action_terms")
        if self._matches_inferred_ui_text_update(lowered):
            return "modify_file"
        additive_terms = {"adicione", "adicionar", "inclua", "incluir"}
        strict_modify_terms = [term for term in modify_terms if term not in additive_terms]
        if self._has_any_non_negated_bounded(lowered, strict_modify_terms):
            return "modify_file"
        if self._additive_term_targets_existing_file(prompt, lowered):
            return "modify_file"
        return "create_file"

    def _directory_target_path(self, prompt: str, workspace: str | None) -> str | None:
        if not workspace:
            return None
        match = re.search(
            r"(?:pasta|diretorio|diret[oó]rio|folder|directory)\s+(?:chamada|chamado|nomeada|nomeado|called)?\s*[`\"]?(?P<name>[A-Za-z0-9_. -]{2,80})[`\"]?",
            prompt,
            re.IGNORECASE,
        )
        if not match:
            return workspace
        name = match.group("name").strip().strip(". ,;:`\"")
        for marker in (" dentro de ", " em ", " no workspace", " na pasta"):
            if marker in name.casefold():
                name = re.split(marker, name, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if not name or re.search(r"[\\/:*?\"<>|]", name):
            return workspace
        return str(Path(workspace) / name).replace("/", "\\")

    def _additive_term_targets_existing_file(self, prompt: str, lowered: str) -> bool:
        additive_terms = ("adicione", "adicionar", "inclua", "incluir", "append")
        if not self._has_any_non_negated_bounded(lowered, list(additive_terms)):
            return False
        return bool(
            re.search(
                r"(?:ao|no|na|nesse|neste|nessa|nesta)\s+(?:arquivo|ficheiro|file)?\s*[`\"']?[A-Za-z0-9_. \-/\\]+\.[A-Za-z0-9]{1,12}",
                prompt,
                flags=re.IGNORECASE,
            )
        )

    def _matches_inferred_ui_text_update(self, lowered: str) -> bool:
        visible_text_terms = self._operation_terms("governed_file_write", "ui_visible_text_terms")
        ui_surface_terms = self._operation_terms("governed_file_write", "ui_surface_terms")
        if not visible_text_terms or not ui_surface_terms:
            return False
        return self._has_any(lowered, visible_text_terms) and self._has_any(lowered, ui_surface_terms)

    def _matches_governed_project_rebuild(self, lowered: str, has_workspace: bool) -> bool:
        if not has_workspace:
            return False
        operation = ((self.policy.get("operations", {}) or {}).get("governed_project_rebuild", {}) or {})
        action_terms = self._operation_terms("governed_project_rebuild", "action_terms")
        context_terms = self._operation_terms("governed_project_rebuild", "context_terms")
        min_action = int(operation.get("min_action_matches", 1))
        min_context = int(operation.get("min_context_matches", 1))
        return self._count_matches(lowered, action_terms) >= min_action and self._count_matches(lowered, context_terms) >= min_context

    def _matches_implementation_execution_request(self, lowered: str) -> bool:
        action_terms = self._operation_terms("governed_project_rebuild", "implementation_action_terms")
        context_terms = self._operation_terms("governed_project_rebuild", "implementation_context_terms")
        return self._has_any_non_negated_bounded(lowered, action_terms) and self._has_any(lowered, context_terms)

    def _matches_narrow_explicit_file_edit(self, prompt: str, lowered: str) -> bool:
        if not self._requested_filenames(prompt):
            return False
        if self._governed_file_write_operation(prompt, lowered) != "modify_file":
            return False
        file_terms = self._operation_terms("governed_file_write", "file_terms")
        execution_terms = self._operation_terms("governed_project_rebuild", "implementation_execution_terms")
        return self._has_any_bounded(lowered, file_terms) and not self._has_any_bounded(lowered, execution_terms)

    def _has_fuzzy_token_match(self, text: str, terms: list[str], *, threshold: float) -> bool:
        tokens = set(re.findall(r"[a-z0-9_]+", text))
        candidates = {term for term in terms if " " not in term and len(term) >= 5}
        return any(SequenceMatcher(None, token, candidate).ratio() >= threshold for token in tokens for candidate in candidates)

    def _matches_artifact_request(self, lowered: str) -> bool:
        create_terms = self._operation_terms("artifact_request", "create_terms")
        package_terms = self._operation_terms("artifact_request", "package_terms")
        return self._has_any(lowered, create_terms) and self._has_any(lowered, package_terms)

    def _workspace_evidence_bundle_metadata(
        self,
        text: str,
        lowered: str,
        workspace: str | None,
        artifact_requested: bool,
    ) -> dict[str, Any] | None:
        if not workspace or not artifact_requested:
            return None
        operation = ((self.policy.get("operations", {}) or {}).get("workspace_evidence_bundle", {}) or {})
        if not self._has_any(lowered, [str(item) for item in operation.get("action_terms", []) or []]):
            return None
        if not self._has_any(lowered, [str(item) for item in operation.get("bundle_terms", []) or []]):
            return None
        if not self._has_any(lowered, [str(item) for item in operation.get("include_terms", []) or []]):
            return None
        paths = self._requested_relative_paths(text)
        archives = [item for item in paths if Path(item).suffix.casefold() == ".zip"]
        summaries = [
            item for item in paths
            if Path(item).suffix.casefold() in {".md", ".txt"}
            and any(marker in Path(item).stem.casefold() for marker in ("summary", "resumo", "report", "relatorio"))
        ]
        if not archives or not summaries:
            return None
        archive_path = archives[0]
        summary_path = next((item for item in summaries if "summary" in Path(item).stem.casefold() or "resumo" in Path(item).stem.casefold()), summaries[0])
        source_paths = [item for item in paths if item not in {archive_path, summary_path}]
        return {
            "requested_operation": "create_summary_and_archive",
            "workspace_write": True,
            "requires_tool_gateway": True,
            "requires_validation": True,
            "summary_relative_path": summary_path,
            "archive_relative_path": archive_path,
            "source_relative_paths": source_paths,
            "include_globs": self._requested_bundle_globs(lowered),
            "title": self._requested_report_title(text) or "Evidence Bundle Summary",
        }

    def _requested_relative_paths(self, text: str) -> list[str]:
        paths: list[str] = []
        embedded_pattern = r"(?<![A-Za-z]:)(?:[A-Za-z0-9_.-]+[\\/])+[A-Za-z0-9_.-]+\.[A-Za-z0-9]{1,12}"
        for match in re.finditer(embedded_pattern, text):
            normalized = self._normalize_relative_request_path(match.group(0))
            if normalized and normalized not in paths:
                paths.append(normalized)
        for line in text.splitlines():
            candidate = line.strip().strip("*- `\"'")
            normalized = self._normalize_relative_request_path(candidate)
            if normalized and normalized not in paths:
                paths.append(normalized)
        for filename in self._requested_filenames(text).values():
            normalized = self._normalize_relative_request_path(filename)
            if normalized and normalized not in paths:
                paths.append(normalized)
        return paths

    def _normalize_relative_request_path(self, value: str) -> str | None:
        candidate = value.strip().strip("*- `\"'.,;:()[]{}")
        if not candidate or ":" in candidate or candidate.startswith(("/", "\\")):
            return None
        candidate = candidate.replace("\\", "/")
        if "/" in candidate and re.search(r"\s+(?:e|and)\s+", candidate, flags=re.IGNORECASE):
            return None
        if not re.fullmatch(r"[A-Za-z0-9_. -]+(?:/[A-Za-z0-9_. -]+)*\.[A-Za-z0-9]{1,12}", candidate):
            return None
        path = Path(candidate)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            return None
        return path.as_posix()

    def _requested_bundle_globs(self, lowered: str) -> list[str]:
        globs: list[str] = []
        pattern = r"(?:qualquer|todos?\s+os?)\s+(?:relatorio|arquivo)s?\s+([a-z0-9_.-]+)\s+(?:presente[s]?\s+)?em\s+([a-z0-9_./\\-]+)"
        for match in re.finditer(pattern, lowered):
            token = match.group(1).strip(" ._-")
            directory = match.group(2).strip(" ./\\")
            if token and directory and ".." not in Path(directory).parts:
                globs.append(f"{directory}/*{token}*")
        return list(dict.fromkeys(globs))

    def _requested_report_title(self, text: str) -> str | None:
        match = re.search(r"(?:titulo|title)\s*:\s*([^\n*]{3,160})", text, flags=re.IGNORECASE)
        if not match:
            return None
        title = re.sub(r"\s+", " ", match.group(1)).strip(" .:-")
        return title or None

    def _workspace_static_reachability_report_metadata(
        self,
        text: str,
        lowered: str,
        workspace: str | None,
    ) -> dict[str, Any] | None:
        if not workspace:
            return None
        if not self._has_any(lowered, ["qa visual", "screenshot", "renderizacao", "renderização", "static reachability", "texto esperado"]):
            return None
        expected = self._expected_text_from_prompt(text)
        if not expected:
            return None
        reports = self._requested_report_output_paths(text)
        if not reports:
            return None
        return {
            "requested_operation": "static_reachability_report",
            "workspace_write": True,
            "requires_tool_gateway": True,
            "requires_validation": True,
            "expected_text": expected,
            "report_relative_path": reports[0],
            "router_operation_type": "workspace_static_reachability_report",
        }

    def _workspace_readonly_audit_metadata(
        self,
        text: str,
        lowered: str,
        workspace: str | None,
    ) -> dict[str, Any] | None:
        if not workspace:
            return None
        operation = ((self.policy.get("operations", {}) or {}).get("workspace_readonly_audit_report", {}) or {})
        action_terms = self._operation_terms("workspace_readonly_audit_report", "action_terms")
        target_terms = self._operation_terms("workspace_readonly_audit_report", "target_terms")
        output_terms = self._operation_terms("workspace_readonly_audit_report", "output_terms")
        min_action = int(operation.get("min_action_matches", 1))
        min_target = int(operation.get("min_target_matches", 1))
        min_output = int(operation.get("min_output_matches", 1))
        if self._count_matches(lowered, action_terms) < min_action:
            return None
        if self._count_matches(lowered, target_terms) < min_target:
            return None
        if self._count_matches(lowered, output_terms) < min_output:
            return None
        reports = self._requested_report_output_paths(text)
        if not reports:
            return None
        return {
            "requested_operation": "workspace_readonly_audit_report",
            "workspace_write": True,
            "workspace_write_scope": "requested_report_only",
            "requires_tool_gateway": True,
            "requires_validation": True,
            "report_relative_path": reports[0],
            "search_terms": self._audit_search_terms(text),
            "router_operation_type": "workspace_readonly_audit_report",
        }

    def _requested_report_output_paths(self, text: str) -> list[str]:
        report_paths = [
            item for item in self._requested_relative_paths(text)
            if item.startswith("reports/") and Path(item).suffix.casefold() in {".md", ".txt"}
        ]
        if len(report_paths) <= 1:
            return report_paths

        normalized_text = text.replace("\\", "/")
        output_context_terms = (
            "gere",
            "gerar",
            "salve",
            "salvar",
            "escreva",
            "crie",
            "criar",
            "retorne",
            "retornar",
            "grave",
            "output",
            "write",
            "save",
            "create",
            "generate",
        )
        source_context_terms = (
            "baseie-se",
            "baseado",
            "fonte",
            "fontes",
            "source",
            "sources",
            "relatorios:",
            "relatórios:",
        )

        def score(path: str) -> tuple[int, int]:
            idx = normalized_text.find(path)
            if idx < 0:
                return (0, 0)
            before = normalized_text[max(0, idx - 180):idx].casefold()
            line_before = normalized_text[max(0, normalized_text.rfind("\n", 0, idx) + 1):idx].casefold()
            window_after = normalized_text[idx:min(len(normalized_text), idx + 80)].casefold()
            value = 0
            if any(term in before for term in output_context_terms):
                value += 4
            if any(term in line_before for term in output_context_terms):
                value += 3
            if re.search(r"(?:em|para|to|at)\s*:?[\s\r\n]*$", line_before, flags=re.IGNORECASE):
                value += 3
            if any(term in before for term in source_context_terms):
                value -= 4
            if any(term in line_before for term in source_context_terms):
                value -= 3
            if re.search(r"^reports/(?:preflight|diagnosis|diagnostico|runtime)", path, flags=re.IGNORECASE):
                value -= 1
            if "correction" in path.casefold() or "correcao" in path.casefold() or "correção" in path.casefold():
                value += 1
            if re.search(r"\b(?:inclua|include|contenha|must contain)\b", window_after, flags=re.IGNORECASE):
                value += 1
            return (value, -idx)

        return sorted(report_paths, key=score, reverse=True)

    def _audit_search_terms(self, text: str) -> list[str]:
        terms: list[str] = []
        for match in re.finditer(r"`([^`]{3,80})`|['\"]([^'\"]{3,80})['\"]", text):
            value = (match.group(1) or match.group(2) or "").strip()
            if value and value not in terms:
                terms.append(value)
        for token in re.findall(r"[A-Za-z0-9_./\\:-]{3,80}", text):
            normalized = token.strip(".,;:()[]{}")
            if (
                normalized
                and (
                    "_" in normalized
                    or "." in normalized
                    or "\\" in normalized
                    or "/" in normalized
                    or normalized[:1].isupper()
                )
                and normalized not in terms
            ):
                terms.append(normalized)
        return terms[:24]

    def _expected_text_from_prompt(self, text: str) -> str | None:
        match = re.search(r"(?:texto esperado|expected text)\s*:\s*([^\n]{3,240})", text, flags=re.IGNORECASE)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip(" .:-") or None
        return None

    def _matches_explicit_workspace_output(self, lowered: str) -> bool:
        action_terms = self._operation_terms("workspace_artifact_write_request", "action_terms")
        destination_terms = self._operation_terms("workspace_artifact_write_request", "destination_terms")
        return self._has_any(lowered, action_terms) and self._has_any(lowered, destination_terms)

    def _matches_filesystem_archive_request(self, lowered: str, source_paths: list[str], artifact_requested: bool) -> bool:
        if not artifact_requested or not source_paths:
            return False
        source_terms = self._operation_terms("filesystem_archive_request", "source_terms")
        return self._has_any(lowered, source_terms)

    def _matches_operational_task_request(self, lowered: str) -> bool:
        if self._matches_artifact_request(lowered):
            return False
        operation = ((self.policy.get("operations", {}) or {}).get("operational_task_request", {}) or {})
        action_terms = self._operation_terms("operational_task_request", "action_terms")
        target_terms = self._operation_terms("operational_task_request", "target_terms")
        min_action = int(operation.get("min_action_matches", 1))
        min_target = int(operation.get("min_target_matches", 1))
        return self._count_matches(lowered, action_terms) >= min_action and self._count_matches(lowered, target_terms) >= min_target

    def _specific_operational_decision(self, text: str, lowered: str, workspace: str | None) -> ChatOperationDecision | None:
        if self._matches_artifact_request(lowered) and not workspace:
            return None
        source_paths = self._extract_paths(text)
        action_terms = self._operation_terms("operational_task_request", "action_terms")
        target_terms = self._operation_terms("operational_task_request", "target_terms")
        if not self._has_any(lowered, action_terms):
            return None
        if not (workspace or self._has_any(lowered, target_terms)):
            return None

        if self._has_any(lowered, self._operation_terms("operational_task_request", "build_terms")):
            requested_actions = ["run_build", "create_artifact"]
            if self._has_any(lowered, ["projeto", "app", "aplicativo", "android", "kotlin", "jogo", "game"]):
                requested_actions = ["create_project", "write_files", *requested_actions]
            return self._decision(
                "android_apk_build" if "apk" in lowered else "artifact_build_request",
                "task_preview",
                0.86,
                ["build_operation_detected", "capability_check_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_actions": list(dict.fromkeys(requested_actions)),
                    "approval_scope": "android_build" if "apk" in lowered else "artifact_generate",
                    "requires_task": True,
                    "requires_policy": True,
                    "requires_capability_resolution": True,
                },
            )

        if self._has_any(lowered, ["android", "kotlin"]) and self._has_any(lowered, ["projeto", "app", "aplicativo", "jogo", "game"]):
            return self._decision(
                "android_project_create",
                "task_preview",
                0.86,
                ["android_project_generation_detected", "project_write_preview_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_actions": ["create_project", "write_files"],
                    "approval_scope": "project_write",
                    "requires_task": True,
                    "requires_policy": True,
                },
            )

        if workspace and re.search(r"\.[A-Za-z0-9]{1,12}$", workspace):
            requested_operation = self._governed_file_write_operation(text, lowered)
            operation_type = "filesystem_modify_file" if requested_operation == "modify_file" else "filesystem_write_file"
            return self._decision(
                operation_type,
                "task_status_update",
                0.9,
                ["filesystem_file_operation_detected", "filesystem_write_scope_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_operation": requested_operation,
                    "requested_actions": [requested_operation],
                    "approval_scope": "file_modify" if requested_operation == "modify_file" else "filesystem_write",
                    "workspace_write": True,
                    "requires_validation": True,
                },
            )

        if workspace and self._has_any(lowered, ["pasta", "diretorio", "diretório", "folder", "directory"]):
            target_path = self._directory_target_path(text, workspace)
            return self._decision(
                "filesystem_create_directory",
                "task_status_update",
                0.86,
                ["filesystem_directory_operation_detected", "filesystem_write_scope_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_operation": "create_directory",
                    "requested_actions": ["create_directory"],
                    "approval_scope": "filesystem_create_directory",
                    "workspace_write": True,
                    "requires_validation": True,
                    "target_path": target_path,
                    "target_paths": [target_path] if target_path else [workspace],
                },
            )

        creation_terms = ["crie", "criar", "gere", "gerar", "implemente", "implementar", "construa", "construir"]
        if self._has_any(lowered, creation_terms) and self._has_any(lowered, ["projeto", "app", "aplicativo", "jogo", "game"]):
            return self._decision(
                "project_create",
                "task_preview",
                0.82,
                ["project_generation_detected", "project_write_preview_required"],
                workspace=workspace,
                primary_prompt=text,
                metadata={
                    "requested_actions": ["create_project", "write_files"],
                    "approval_scope": "project_write",
                    "requires_task": True,
                    "requires_policy": True,
                },
            )
        return None

    def _is_sandbox_path(self, path_ref: str) -> bool:
        try:
            sandbox_root = (PATHS.project_root / "sandboxes").resolve(strict=False)
            path = Path(path_ref).resolve(strict=False)
            return path == sandbox_root or sandbox_root in path.parents
        except Exception:
            return False

    def _operational_task_actions(self, lowered: str) -> list[str]:
        operation = ((self.policy.get("operations", {}) or {}).get("operational_task_request", {}) or {})
        hints = operation.get("capability_hints", {}) or {}
        actions: list[str] = []
        if isinstance(hints, dict):
            for config in hints.values():
                if not isinstance(config, dict):
                    continue
                terms = [self._normalize_text(str(item)) for item in config.get("terms", []) or []]
                if self._has_any(lowered, terms):
                    actions.extend(str(item) for item in config.get("actions", []) or [])
        return list(dict.fromkeys(actions or ["plan_task"]))

    def _matches_public_fact_query(self, lowered: str) -> bool:
        operation = ((self.policy.get("operations", {}) or {}).get("public_fact_query", {}) or {})
        search_terms = self._operation_terms("public_fact_query", "search_terms")
        fact_terms = self._operation_terms("public_fact_query", "fact_terms")
        question_terms = self._operation_terms("public_fact_query", "question_terms")
        list_terms = self._operation_terms("public_fact_query", "list_terms")
        knowledge_terms = self._operation_terms("public_fact_query", "knowledge_terms")
        has_search = self._has_any(lowered, search_terms)
        has_fact = self._has_any(lowered, fact_terms)
        has_listable_public_knowledge = self._has_any_bounded(lowered, list_terms) and (
            self._has_any(lowered, knowledge_terms) or has_fact
        )
        asks_question = "?" in lowered or self._has_any_bounded(lowered, question_terms)
        return has_search or (has_fact and asks_question) or has_listable_public_knowledge

    def _matches_readonly_project_analysis(self, lowered: str, workspace: str | None) -> bool:
        analysis_terms = self._operation_terms("readonly_project_analysis", "analysis_terms")
        project_terms = self._operation_terms("readonly_project_analysis", "project_terms")
        readonly_terms = self._operation_terms("readonly_project_analysis", "readonly_terms")
        has_target = bool(workspace) or self._has_any(lowered, project_terms)
        return has_target and self._has_any(lowered, analysis_terms) and (self._has_any(lowered, readonly_terms) or bool(workspace))

    def _matches_followup(self, lowered: str, has_workspace: bool) -> bool:
        if has_workspace:
            return False
        terms = self._operation_terms("followup_result_recall", "terms")
        minimum = int(((self.policy.get("operations", {}) or {}).get("followup_result_recall", {}) or {}).get("min_matches", 1))
        return self._count_matches(lowered, terms) >= minimum

    def _matches_followup_review(self, lowered: str, has_workspace: bool) -> bool:
        if has_workspace:
            return False
        operation = ((self.policy.get("operations", {}) or {}).get("followup_result_review", {}) or {})
        action_terms = self._operation_terms("followup_result_review", "action_terms")
        reference_terms = self._operation_terms("followup_result_review", "reference_terms")
        min_action = int(operation.get("min_action_matches", 1))
        min_reference = int(operation.get("min_reference_matches", 1))
        return self._count_matches(lowered, action_terms) >= min_action and self._count_matches(lowered, reference_terms) >= min_reference

    def _followup_recall_kind(self, lowered: str) -> str:
        operation = ((self.policy.get("operations", {}) or {}).get("followup_result_recall", {}) or {})
        recall_kinds = operation.get("recall_kinds", {}) or {}
        for recall_kind, config in recall_kinds.items():
            terms = [str(item).lower() for item in (config or {}).get("terms", []) or []]
            if self._has_any(lowered, terms):
                return str(recall_kind)
        return "answer"

    def _strip_artifact_terms(self, prompt: str) -> str:
        terms = [
            *self._operation_terms("artifact_request", "create_terms"),
            *self._operation_terms("artifact_request", "package_terms"),
        ]
        cleaned = prompt
        for term in sorted(terms, key=len, reverse=True):
            if term:
                cleaned = re.sub(re.escape(term), " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-")
        return cleaned or prompt

    def _artifact_output_request(self, prompt: str, lowered: str) -> dict[str, Any]:
        filenames = self._requested_filenames(prompt)
        package_terms = self._operation_terms("artifact_request", "package_terms")
        create_terms = self._operation_terms("artifact_request", "create_terms")
        return {
            "artifact_requested": True,
            "package_format": "zip" if "zip" in lowered else None,
            "download_requested": self._has_any(lowered, [*package_terms, *create_terms]),
            "filenames": filenames,
        }

    def _requested_filenames(self, prompt: str) -> dict[str, str]:
        relative_path_pattern = (
            r"(?<![A-Za-z0-9._:-])"
            r"([A-Za-z0-9][A-Za-z0-9._-]*(?:[/\\][A-Za-z0-9][A-Za-z0-9._ -]*)+\.(?:txt|md|zip))"
            r"(?!(?:[A-Za-z0-9_-]|\.[A-Za-z0-9]))"
        )
        basename_pattern = r"(?<![A-Za-z0-9._-])([A-Za-z0-9][A-Za-z0-9._-]{0,119}\.(?:txt|md|zip))(?!(?:[A-Za-z0-9_-]|\.[A-Za-z0-9]))"
        candidates = [
            (match.start(), match.group(1))
            for pattern in (relative_path_pattern, basename_pattern)
            for match in re.finditer(pattern, prompt, flags=re.IGNORECASE)
        ]
        matches = [value for _, value in sorted(candidates, key=lambda item: item[0])]
        filenames: dict[str, str] = {}
        for match in matches:
            name = match.strip(" .,:;")
            lowered = name.lower()
            if lowered.endswith(".zip") and "package" not in filenames:
                filenames["package"] = name
            elif lowered.endswith((".txt", ".md")) and "text" not in filenames:
                filenames["text"] = name
        return filenames

    def _normalize_text(self, value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value)
        ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
        return ascii_text.lower()
