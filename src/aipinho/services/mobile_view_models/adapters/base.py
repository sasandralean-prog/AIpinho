from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainSnapshot:
    domain: str
    status: str
    summary: str
    endpoints: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DomainStatusAdapter:
    def __init__(self, domain: str, endpoints: list[str], status: str = "unknown", summary: str | None = None) -> None:
        self.domain = domain
        self.endpoints = endpoints
        self.status = status
        self.summary = summary or f"{domain} disponivel como evidencia sanitizada quando o endpoint responder."

    def snapshot(self) -> DomainSnapshot:
        return DomainSnapshot(
            domain=self.domain,
            status=self.status,
            summary=self.summary,
            endpoints=self.endpoints,
        )

