# Lúcio Multimodal Mobile Guide

## Uso

Na aba Lúcio, o usuário pode anexar imagens, logs e arquivos permitidos. O app envia o arquivo como artifact governado para o backend e referencia o artifact na mensagem.

## MIME types iniciais

- `image/png`
- `image/jpeg`
- `image/webp`
- `text/plain`
- `text/markdown`
- `application/json`
- `application/pdf`

## Renderização

- Modo normal: resposta humana, badges e ações seguras.
- Detalhes: artifact refs, rota, delegação e trace sanitizado.
- Raw/debug: apenas sob ação explícita.

## Segurança

O Android não recebe secrets de provider. O app não decide policy e não executa side effects. Ele apenas envia artifacts, mostra status e solicita ações governadas.

