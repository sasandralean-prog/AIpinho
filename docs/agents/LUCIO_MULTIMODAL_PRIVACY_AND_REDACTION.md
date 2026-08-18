# Lúcio Multimodal Privacy and Redaction

## Política

- Tokens, secrets e credenciais não podem aparecer em resposta, evento, report ou raw visível.
- Raw visual não vai para memória curada automaticamente.
- Imagens com risco de segredo recebem `redaction_status=warning` ou equivalente.
- O modo normal do chat mostra apenas resposta humana e evidências sanitizadas.

## Fontes permitidas para resposta

- Metadados de artifact.
- Análise visual governada.
- Trace sanitizado.
- Contexto textual enviado pelo usuário.

## Fontes proibidas como primárias

- RAG legado.
- Memória de projeto contaminada.
- Raw log bruto.
- Raw image bytes em chat normal.

