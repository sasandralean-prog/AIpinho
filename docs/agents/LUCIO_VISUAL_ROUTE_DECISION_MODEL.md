# Lúcio Visual Route Decision Model

## Prioridade de decisão

1. Segurança e privacidade.
2. Clareza do pedido.
3. Presença de evidência visual.
4. Capacidade do Lúcio de responder estrategicamente.
5. Necessidade de executor técnico.

## Exemplos de decisão

- Screenshot de erro + pedido de diagnóstico: `answer_directly` ou `delegate_to_codex`, conforme necessidade técnica.
- Imagem ambígua sem objetivo claro: `request_better_image`.
- Pedido de correção com evidência visual: `delegate_to_codex` com artifact refs e validação esperada.
- Pergunta conceitual sem side effect: `answer_directly`.

## Princípio

Artifacts visuais são `evidence_source`, não `target_skill`. A imagem não força visão/OCR se o usuário não pediu análise visual ou se a política não precisa disso.

