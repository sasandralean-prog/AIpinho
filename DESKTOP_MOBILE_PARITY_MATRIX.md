# DESKTOP MOBILE PARITY MATRIX

| Feature | Mobile status | Desktop status | Endpoint usado | Gaps | Proximo passo |
| --- | --- | --- | --- | --- | --- |
| Chat normal | Validado com presentation renderer | Implementado via ChatPresentationMapper | `/api/v1/chat/sessions/*/timeline` | Depende do backend preencher timeline/presentation | Smoke com modelo real |
| Details | Cards e terminal colapsado | Modo Detalhes por combobox | Timeline + metadata sanitizada | Sem painel lateral dedicado ainda | Separar painel lateral em versao futura |
| Raw | Oculto por padrao | Raw sanitizado apenas no modo Raw/colapsado | Timeline/raw payload local | Raw por mensagem usa payload retornado | Plugar endpoint raw se necessario |
| Artifact download | Botao no chat com token no header | Botao no chat e aba Artifacts | `/api/v1/artifacts/{artifact_id}/download` | Sem lista global de artifacts se backend nao expor | Consumir lista oficial quando existir |
| Attachments | Suportado no mobile | Nao implementado nesta primeira versao | N/A | Falta client/upload UX desktop | Adicionar UploadButton governado |
| Pipeline | Cards, approvals e fila | Cards de task e botoes se `approval_id` real | `/api/v1/tasks/cards`, `/api/v1/approvals/*` | Formato de task card pode variar | Ajustar quando contrato v2 final estabilizar |
| Approval | Botao real quando ha approval | Approve/reject/cancel reais por approval_id | `/api/v1/approvals/{id}/approve|reject|cancel` | Sem confirm modal ainda | Adicionar confirmacao visual |
| Debugger | Debugger 2.0 sanitizado | Eventos filtraveis sanitizados | `/api/v1/events`, `/api/v1/debugger/status` | Sem busca por trace_id dedicada | Adicionar filtros por trace/session/task |
| Dashboard health | Status backend/mobile | Servicos + restart permitido | `/api/v1/monitor/*` | Depende de payload de services | Melhorar indicadores por porta |
| Service restart | 9088/9089/9098 permitidos, 9099 bloqueado | Mesmo contrato no client desktop | `/api/v1/monitor/services/{id}/restart` | 9099 mostra instrucao humana | Mecanismo externo se autorizado |
| Config/pairing | Host/token/perfis/ADB | Host/token persistidos e ADB exibido | `/api/v1/connection/*` | Sem QR se backend nao expor | Plugar QR quando houver endpoint |
| Copy sanitized | Validado nos cards | Botao Copiar por mensagem | Local presentation mapper | Sem feedback toast persistente | Adicionar toast/status bar |
