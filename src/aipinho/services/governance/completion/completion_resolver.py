from __future__ import annotations

from typing import Any

from aipinho.schemas.governance.lifecycle import CanonicalCompletionVerdict, GovernanceLifecycleReasonCode


class CanonicalCompletionResolver:
    def resolve(self, expected_outputs: list[str], outputs: dict[str, Any] | None, *, proposed_status: str = "completed") -> CanonicalCompletionVerdict:
        present = outputs or {}
        expected = list(dict.fromkeys(str(item) for item in expected_outputs if str(item).strip()))
        fulfilled = [item for item in expected if present.get(item) is not None]
        missing = [item for item in expected if item not in fulfilled]
        if proposed_status in {"failed", "blocked"}:
            status = proposed_status
        elif missing:
            status = "incomplete"
        elif proposed_status == "completed_with_warnings":
            status = "completed_with_warnings"
        else:
            status = "completed"
        return CanonicalCompletionVerdict(
            status=status,
            safe_to_report_success=status == "completed" and not missing,
            expected_outputs=expected,
            fulfilled_outputs=fulfilled,
            missing_outputs=missing,
            reason_code=GovernanceLifecycleReasonCode.COMPLETION_MISSING_OUTPUTS if missing else GovernanceLifecycleReasonCode.NONE,
        )
