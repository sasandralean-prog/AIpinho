from __future__ import annotations

from aipinho.schemas.pinhoforge_bridge import PinhoForgeBridgePolicyDecision


class PinhoForgeBridgePolicyService:
    def __init__(
        self,
        *,
        allowed_operations: tuple[str, ...] = ("handshake", "health", "manifest", "readiness"),
        blocked_operations: tuple[str, ...] = ("execute",),
        execution_enabled: bool = False,
    ) -> None:
        self.allowed_operations = {operation.strip().lower() for operation in allowed_operations}
        self.blocked_operations = {operation.strip().lower() for operation in blocked_operations}
        self.execution_enabled = execution_enabled

    def evaluate(self, operation: str) -> PinhoForgeBridgePolicyDecision:
        normalized = operation.strip().lower()
        if normalized in self.blocked_operations or normalized == "execute" or not self.execution_enabled and normalized not in self.allowed_operations:
            return PinhoForgeBridgePolicyDecision(
                operation=normalized,
                decision="deny",
                reason_code="pinhoforge_bridge_execution_disabled",
                human_reason="A bridge PinhoForge esta em modo discovery/protocol-only; execucao real permanece bloqueada.",
                execution_enabled=False,
            )
        if normalized not in self.allowed_operations:
            return PinhoForgeBridgePolicyDecision(
                operation=normalized,
                decision="deny",
                reason_code="pinhoforge_bridge_operation_not_allowed",
                human_reason="Operacao fora do contrato permitido da bridge PinhoForge.",
                execution_enabled=False,
            )
        return PinhoForgeBridgePolicyDecision(
            operation=normalized,
            decision="allow",
            reason_code="pinhoforge_bridge_readonly_operation_allowed",
            human_reason="Operacao read-only permitida pela bridge PinhoForge.",
            execution_enabled=False,
        )
