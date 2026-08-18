from __future__ import annotations

from dataclasses import dataclass

from aipinho.schemas.agents.contracts import AgentProfile, AgentRun
from aipinho.schemas.agents.delegation import DelegationRequest, DelegationResult


@dataclass(frozen=True)
class AgentAdapterDecision:
    accepted: bool
    reason_code: str = "adapter_accepts_delegation"
    human_reason: str = "Agente pode receber a delegacao."


class AgentAdapter:
    agent_id = "unknown"

    def can_accept_delegation(self, profile: AgentProfile, request: DelegationRequest) -> AgentAdapterDecision:
        if not profile.enabled:
            return AgentAdapterDecision(False, "target_agent_disabled", "Agente destino esta desabilitado.")
        return AgentAdapterDecision(True)

    def summarize_result(self, request: DelegationRequest, child_run: AgentRun | None) -> DelegationResult:
        status = child_run.status if child_run else request.status
        evidence = [f"delegation:{request.delegation_id}"]
        if child_run:
            evidence.append(f"run:{child_run.run_id}")
        return DelegationResult(
            delegation_id=request.delegation_id,
            parent_run_id=request.parent_run_id,
            child_run_id=child_run.run_id if child_run else request.child_run_id,
            parent_agent_id=request.parent_agent_id,
            target_agent_id=request.target_agent_id,
            status=status,
            summary="Delegacao registrada. A execucao real deve ocorrer no child run do agente destino.",
            evidence_refs=evidence,
            next_steps=["Acompanhar eventos do child run.", "Executar ferramentas pelo Tool Gateway quando a tarefa exigir side effects."],
        )


class AIpinhoAgentAdapter(AgentAdapter):
    agent_id = "aipinho"


class CodexAgentAdapter(AgentAdapter):
    agent_id = "codex"


class GeminiAgentAdapter(AgentAdapter):
    agent_id = "gemini"


class LucioAgentAdapter(AgentAdapter):
    agent_id = "lucio"


class AgentAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, AgentAdapter] = {
            "aipinho": AIpinhoAgentAdapter(),
            "codex": CodexAgentAdapter(),
            "gemini": GeminiAgentAdapter(),
            "lucio": LucioAgentAdapter(),
        }

    def get(self, agent_id: str) -> AgentAdapter:
        return self._adapters.get(agent_id, AgentAdapter())
