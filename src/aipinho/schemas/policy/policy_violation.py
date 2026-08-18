from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.policy.policy_trace import Severity


class PolicyViolation(AIpinhoModel):
    code: str
    reason: str
    severity: Severity = "error"
    source: str