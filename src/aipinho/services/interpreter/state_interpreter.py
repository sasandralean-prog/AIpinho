from __future__ import annotations


class StateInterpreter:
    STATUS_MESSAGES = {
        "allowed": "permitido pela Policy Kernel",
        "needs_approval": "exige aprovacao antes de executar",
        "needs_clarification": "precisa de esclarecimento",
        "denied": "bloqueado por politica",
        "degraded": "funcionando com dependencia ausente",
    }

    def explain_policy_status(self, status: str) -> str:
        return self.STATUS_MESSAGES.get(status, "estado de policy desconhecido")