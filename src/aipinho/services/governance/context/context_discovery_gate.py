from __future__ import annotations

import hashlib
import re
from typing import Any

from aipinho.schemas.governance.lifecycle import (
    CanonicalIntentDecision,
    CanonicalOperationContract,
    ContextGateDecision,
    GovernanceLifecycleReasonCode,
)


class ContextDiscoveryGate:
    """Blocks premature side-effect approval before the system knows what to do."""

    WRITE_OR_EXECUTE = {
        "write_files",
        "write_file",
        "create_file",
        "modify_file",
        "apply_patch",
        "project_generation",
        "create_directory",
        "run_command",
        "run_tests",
    }
    ANALYSIS_TERMS = ("analise", "analisar", "diagnostique", "diagnosticar", "auditoria", "problema", "bug", "ux")
    FIX_TERMS = ("corrija", "corrigir", "conserte", "implemente correcao", "implemente correção", "fix")

    def evaluate(
        self,
        *,
        user_text: str,
        intent: CanonicalIntentDecision,
        contract: CanonicalOperationContract,
        source_message_id: str | None = None,
        context_ref: str | None = None,
        discovery_ref: str | None = None,
        analysis_ref: str | None = None,
        executable_plan_ref: str | None = None,
        expected_outputs: list[str] | None = None,
        validation_plan: dict[str, Any] | list[Any] | None = None,
    ) -> ContextGateDecision:
        if not self._needs_write_or_execution(contract):
            return ContextGateDecision(
                status="not_required",
                can_create_write_approval=True,
                source_message_id=source_message_id,
                context_ref=context_ref,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
                trace=[{"stage": "context_discovery_gate", "mode": "readonly_or_conversation"}],
            )

        inferred_source = source_message_id or self._stable_ref("source_message", user_text or contract.operation_id)
        inferred_context = context_ref
        inferred_snapshot = discovery_ref or (
            self._stable_ref("workspace_snapshot", contract.workspace_path) if contract.workspace_path else None
        )
        targets = [path for path in contract.target_paths if str(path).strip()]
        outputs = [item for item in expected_outputs or [] if str(item).strip()]

        if not inferred_source or not user_text.strip():
            return self._blocked(
                GovernanceLifecycleReasonCode.APPROVAL_NOT_CREATED_PROMPT_CONTEXT_MISSING,
                "source_message_id",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
            )
        if not executable_plan_ref:
            return self._blocked(
                GovernanceLifecycleReasonCode.APPROVAL_NOT_CREATED_NO_EXECUTABLE_PLAN,
                "executable_plan_ref",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
                workspace_snapshot_ref=inferred_snapshot,
            )
        if not inferred_context:
            return self._blocked(
                GovernanceLifecycleReasonCode.PREVIEW_REJECTED_NO_CONTEXT_REF,
                "context_ref",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
            )
        if not contract.workspace_path:
            return self._blocked(
                GovernanceLifecycleReasonCode.APPROVAL_NOT_CREATED_WORKSPACE_NOT_RESOLVED,
                "workspace_path",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
            )
        if self._diagnostic_write(user_text, intent, contract) and not analysis_ref:
            reason = (
                GovernanceLifecycleReasonCode.WORKSPACE_DISCOVERY_REQUIRED
                if not discovery_ref
                else GovernanceLifecycleReasonCode.APPROVAL_NOT_CREATED_NO_ANALYSIS_REF
            )
            return self._blocked(
                reason,
                "analysis_ref",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
                workspace_snapshot_ref=inferred_snapshot,
            )
        if not targets:
            return self._blocked(
                GovernanceLifecycleReasonCode.APPROVAL_NOT_CREATED_NO_TARGET_FILES,
                "target_files",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
                workspace_snapshot_ref=inferred_snapshot,
            )
        if not outputs:
            return self._blocked(
                GovernanceLifecycleReasonCode.APPROVAL_NOT_CREATED_NO_EXPECTED_OUTPUTS,
                "expected_outputs",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
                workspace_snapshot_ref=inferred_snapshot,
            )
        if not validation_plan:
            return self._blocked(
                GovernanceLifecycleReasonCode.APPROVAL_NOT_CREATED_NO_VALIDATION_PLAN,
                "validation_plan",
                source_message_id=inferred_source,
                context_ref=inferred_context,
                discovery_ref=discovery_ref,
                analysis_ref=analysis_ref,
                workspace_snapshot_ref=inferred_snapshot,
            )
        return ContextGateDecision(
            status="ready",
            can_create_write_approval=True,
            source_message_id=inferred_source,
            context_ref=inferred_context,
            workspace_snapshot_ref=inferred_snapshot,
            discovery_ref=discovery_ref,
            analysis_ref=analysis_ref,
            trace=[
                {
                    "stage": "context_discovery_gate",
                    "mode": "ready",
                    "target_count": len(targets),
                    "expected_outputs": outputs,
                }
            ],
        )

    def _needs_write_or_execution(self, contract: CanonicalOperationContract) -> bool:
        return bool(set(contract.requested_actions).intersection(self.WRITE_OR_EXECUTE))

    def _diagnostic_write(
        self,
        user_text: str,
        intent: CanonicalIntentDecision,
        contract: CanonicalOperationContract,
    ) -> bool:
        text = (user_text or "").casefold()
        has_analysis = any(term in text for term in self.ANALYSIS_TERMS)
        has_fix = any(term in text for term in self.FIX_TERMS)
        return has_analysis and has_fix or intent.intent_type in {"workspace_fix_request", "diagnostic_fix_request"}

    def _blocked(
        self,
        reason_code: GovernanceLifecycleReasonCode,
        missing: str,
        *,
        source_message_id: str | None,
        context_ref: str | None,
        discovery_ref: str | None,
        analysis_ref: str | None,
        workspace_snapshot_ref: str | None = None,
    ) -> ContextGateDecision:
        return ContextGateDecision(
            status=reason_code.value,
            can_create_write_approval=False,
            reason_code=reason_code,
            source_message_id=source_message_id,
            context_ref=context_ref,
            workspace_snapshot_ref=workspace_snapshot_ref,
            discovery_ref=discovery_ref,
            analysis_ref=analysis_ref,
            missing_requirements=[missing],
            trace=[{"stage": "context_discovery_gate", "mode": "blocked", "reason_code": reason_code.value}],
        )

    def _stable_ref(self, prefix: str, value: str | None) -> str | None:
        if not value:
            return None
        digest = hashlib.sha256(str(value).encode("utf-8", errors="ignore")).hexdigest()[:16]
        safe_prefix = re.sub(r"[^a-z0-9_]+", "_", prefix.casefold()).strip("_") or "ref"
        return f"{safe_prefix}_{digest}"
