from __future__ import annotations

from typing import Any

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.intent.intent_map import IntentMap
from aipinho.schemas.policy.policy_decision import PolicyDecision
from aipinho.services.artifacts.chat_report_composer import ChatReportComposer
from aipinho.services.interpreter.interpreter_service import InterpreterService
from aipinho.services.speaker.response_composer import ResponseComposer
from aipinho.services.speaker.speaker_policy_service import SpeakerPolicyService


class SpeakerService:
    def __init__(
        self,
        policy: SpeakerPolicyService | None = None,
        composer: ResponseComposer | None = None,
        interpreter: InterpreterService | None = None,
        report_composer: ChatReportComposer | None = None,
    ) -> None:
        self.policy = policy or SpeakerPolicyService().load()
        self.composer = composer or ResponseComposer()
        self.interpreter = interpreter or InterpreterService()
        self.report_composer = report_composer or ChatReportComposer()

    def compose_response(
        self,
        *,
        request: ChatRequest,
        intent_map: IntentMap,
        policy_decision: PolicyDecision,
        contract_preview: dict[str, Any],
        status: str,
    ) -> str:
        if status == "needs_clarification":
            return self.compose_clarification(intent_map)
        if status == "blocked":
            return self.compose_blocked(intent_map, policy_decision)
        if intent_map.intent_type == "self_analysis":
            return self.compose_self_analysis_answer()
        if intent_map.intent_type == "capability_explanation":
            return self.compose_capability_answer()
        if intent_map.intent_type == "in_chat_final_report":
            return self.compose_chat_report(request, intent_map)
        if status == "preview":
            return self.compose_preview(intent_map, policy_decision, contract_preview)
        return self.compose_conversation(intent_map)

    def compose_conversation(self, intent_map: IntentMap) -> str:
        if intent_map.operation == "explain":
            return "Posso responder de forma conceitual no chat. Nesta sprint eu nao crio task nem executo acoes para perguntas de conversa."
        return "Tudo certo por aqui. Posso conversar e tambem preparar previews seguros de contrato quando o pedido for operacional."

    def compose_self_analysis_answer(self) -> str:
        state = self.composer.product_state()
        product = state.get("product", {}) if isinstance(state, dict) else {}
        stage = product.get("stage", "foundation") if isinstance(product, dict) else "foundation"
        capabilities = [str(item) for item in product.get("ready_capabilities", [])] if isinstance(product, dict) else []
        limits = [str(item) for item in product.get("known_limitations", [])] if isinstance(product, dict) else []
        ok_sources, missing_sources = self.composer.source_status()
        message = [
            f"AIpinho esta no estagio: {stage}.",
            "Capacidades ja implementadas nesta base:",
            self.composer.bullet_list(capabilities or ["Foundation, Policy Kernel e Prompt Intelligence basicos."]),
            "Limitacoes atuais:",
            self.composer.bullet_list(limits or ["Execucao real ainda nao esta implementada."]),
            "Fontes usadas:",
            self.composer.bullet_list(ok_sources or ["config/app/product.yaml"]),
        ]
        if missing_sources:
            message.extend(["Fontes ausentes ou vazias:", self.composer.bullet_list(missing_sources)])
        return "\n".join(part for part in message if part)

    def compose_capability_answer(self) -> str:
        state = self.composer.product_state()
        product = state.get("product", {}) if isinstance(state, dict) else {}
        capabilities = [str(item) for item in product.get("ready_capabilities", [])] if isinstance(product, dict) else []
        limits = [str(item) for item in product.get("known_limitations", [])] if isinstance(product, dict) else []
        return (
            "Hoje eu consigo:\n"
            f"{self.composer.bullet_list(capabilities)}\n\n"
            "Ainda nao consigo nesta base:\n"
            f"{self.composer.bullet_list(limits)}"
        )

    def compose_chat_report(self, request: ChatRequest, intent_map: IntentMap) -> str:
        return self.report_composer.compose(request, intent_map)

    def compose_clarification(self, intent_map: IntentMap) -> str:
        if intent_map.requires_workspace and not intent_map.workspace.declared:
            return "Preciso de esclarecimento antes de continuar: qual workspace ou projeto devo considerar, e qual resultado voce espera? Nao vou criar task nem executar nada enquanto isso estiver ambiguo."
        return "Preciso de esclarecimento antes de continuar. Diga qual objetivo, escopo e nivel de risco voce quer assumir. Nenhuma acao sera executada agora."

    def compose_blocked(self, intent_map: IntentMap, policy_decision: PolicyDecision) -> str:
        reason = self.interpreter.explain_policy_status(policy_decision.status)
        if policy_decision.denied_actions and policy_decision.status in {"allowed", "needs_approval"}:
            reason = "bloqueado pela Policy Kernel"
        if intent_map.workspace.protected:
            return "Bloqueado por politica: o workspace informado esta protegido. Nao vou ler, escrever, criar task ou preparar execucao para essa raiz."
        denied = ", ".join(policy_decision.denied_actions) or "acao solicitada"
        return f"Pedido bloqueado: {reason}. Acoes negadas: {denied}. Nenhuma execucao foi iniciada."

    def compose_preview(self, intent_map: IntentMap, policy_decision: PolicyDecision, contract_preview: dict[str, Any]) -> str:
        status_text = self.interpreter.explain_policy_status(policy_decision.status)
        actions = ", ".join(intent_map.requested_actions) or "nenhuma acao operacional"
        approvals = ", ".join(policy_decision.approval_required_for) or "nenhuma aprovacao pendente neste preview"
        return (
            f"Entendi isso como {intent_map.intent_type}.\n"
            "Vou ficar apenas no preview de contrato; nenhuma tool, LLM, RAG, memoria, shell ou patch sera executado.\n"
            f"Status de policy: {status_text}.\n"
            f"Acoes solicitadas: {actions}.\n"
            f"Aprovacao exigida para: {approvals}.\n"
            f"Preview seguro: {contract_preview.get('safe_to_preview', False)}; execucao segura agora: {contract_preview.get('safe_to_execute', False)}."
        )

    def status(self) -> dict[str, object]:
        policy_status = self.policy.status()
        return {
            "status": policy_status.get("status", "degraded"),
            "service": "speaker",
            "execution_enabled": False,
            "raw_context_enabled": False,
            "governed_context_only": True,
            "citation_bypass_enabled": False,
            "policy": policy_status,
        }
