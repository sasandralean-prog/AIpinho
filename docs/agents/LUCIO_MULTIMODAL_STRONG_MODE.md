# Lúcio Multimodal Strong Mode

## Objetivo

O modo multimodal do Lúcio permite analisar mensagens com texto, imagens, screenshots, logs e arquivos como evidência estratégica. Lúcio continua sendo agente de análise, decisão e delegação: ele não executa side effects locais diretamente.

## Fluxo

1. O usuário envia texto e referências de artifact.
2. O backend monta uma `LucioMultimodalMessage`.
3. Artifacts visuais são convertidos em `LucioVisualArtifact` com metadados sanitizados.
4. A política de rota gera `LucioRouteDecision`.
5. Lúcio responde diretamente, pede esclarecimento, cria plano ou delega para Codex/AIpinho.
6. Delegações carregam contexto visual sanitizado, artifact refs e expectativa de validação.

## Garantias

- Raw visual fica oculto por padrão.
- Memória automática de imagem fica desabilitada.
- RAG não é usado como fonte primária para screenshots.
- Secrets detectados em artefatos geram warning/redaction.
- Codex/AIpinho recebem contexto visual como evidência, não como permissão automática para executar.

