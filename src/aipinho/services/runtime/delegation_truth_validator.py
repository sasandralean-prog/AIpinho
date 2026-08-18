from __future__ import annotations

import hashlib
import re

from aipinho.schemas.runtime.delegation_contract import DelegationTruthValidation


class DelegationTruthValidator:
    CLAIM_RE = re.compile(
        r"\b("
        r"deleguei|delegado|delegada|"
        r"consultei|"
        r"aipinho\s+(respondeu|informou|retornou|executou)|"
        r"executor\s+retornou|"
        r"polling|"
        r"child_run|"
        r"delegation_id"
        r")\b",
        re.IGNORECASE,
    )

    def validate(self, text: str, *, delegation_id: str | None = None) -> DelegationTruthValidation:
        claimed = bool(self.CLAIM_RE.search(str(text or "")))
        if claimed and not delegation_id:
            return DelegationTruthValidation(
                status="violation",
                delegation_claimed=True,
                delegation_id=None,
                violations=["delegation_claim_without_runtime_contract"],
                reason_code="delegation_id_required_for_delegation_claim",
                required_evidence=["delegation_id", "child_run_id", "runtime_evidence", "polling", "completion_event"],
            )
        return DelegationTruthValidation(
            status="ok",
            delegation_claimed=claimed,
            delegation_id=delegation_id,
            reason_code="ok",
        )

    @staticmethod
    def truth_hash(text: str, delegation_id: str | None) -> str:
        digest = hashlib.sha256()
        digest.update(str(text or "").encode("utf-8", errors="ignore"))
        digest.update(b"|")
        digest.update(str(delegation_id or "").encode("utf-8", errors="ignore"))
        return digest.hexdigest()
