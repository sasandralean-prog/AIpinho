# Multi-Agent Dashboard

O Dashboard multiagente e a visao operacional agregada de AIpinho, Lucio, Codex e Gemini.

Fonte oficial:

- `GET /api/v1/dashboard/multi-agent`
- `GET /api/v1/dashboard/health`
- `GET /api/v1/dashboard/state-consistency`

O dashboard consolida:

- estado do backend e portas;
- agentes registrados;
- sessoes e runs;
- delegacoes;
- approvals pendentes;
- auto-approvals;
- blocos e falhas;
- validacoes;
- artifacts;
- policy kernel;
- tool gateway;
- event bus;
- self-healing governado.

Regras:

- raw nao aparece por padrao;
- tokens e secrets sao redigidos;
- UI nao decide policy, safety ou status final;
- safe actions apontam para endpoints backend;
- inconsistencias aparecem como warnings, nao como sucesso.
