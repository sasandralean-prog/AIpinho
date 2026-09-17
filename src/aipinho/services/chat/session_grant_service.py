from __future__ import annotations

from aipinho.services.policy_kernel.authority_grant_service import (
    AuthorityGrantService,
    _utc_now,
)


class SessionGrantService(AuthorityGrantService):
    """Backward-compatible chat facade over the canonical authority-grant store."""


__all__ = ["SessionGrantService", "_utc_now"]
