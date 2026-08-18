from __future__ import annotations

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.intent.intent_map import IntentMap


class ChatReportComposer:
    def compose(self, request: ChatRequest, intent_map: IntentMap) -> str:
        surface = request.context.surface if request.context else "unknown"
        return (
            "Resumo no chat:\n"
            "- Eu identifiquei um pedido de recapitulacao dentro da conversa.\n"
            "- Nao ha historico persistente de conversa nesta sprint, entao posso resumir apenas a mensagem e o contexto enviados agora.\n"
            f"- Canal de saida: {intent_map.output_intent.channel}.\n"
            f"- Superficie informada: {surface}.\n"
            "- Nenhum arquivo sera criado e nenhuma task sera aberta por este pedido."
        )