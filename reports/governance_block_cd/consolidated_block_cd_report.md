# Relatorio Consolidado dos Blocos C e D

Status: CONSOLIDATED_BLOCK_CD_REPORT_READY

Data: 2026-06-28

## 1. Resumo executivo

- Veredito C: GOVERNANCE_BLOCK_C_LEGACY_DELETION_READY.
- Veredito D: GOVERNANCE_UNIFIED_SYSTEM_READY.
- Fluxo unico de governanca: ativo para rotas publicas criticas cobertas pelos testes.
- Legacy/deprecated ativo como autoridade publica: nao encontrado nas evidencias C/D.
- P0 aberto: nenhum P0 comprovado nos reports C/D.
- Criacao de apps/projetos: APP_CREATION_ALLOWED_WITH_CAUTION.

Conclusao objetiva:

O Bloco C removeu/bloqueou os caminhos publicos legacy de verdade para chat/Continue. O Bloco D provou o lifecycle unificado em comportamento essencial: read-only nao vira escrita, fix request passa por discovery antes de approval, capability truth nao cai no ChatService generico e Continue/persistent/direct chat carregam GovernanceLifecycleSnapshot. Ainda falta firetest de campo com Mobile/Launcher reais, clique de approval por botao, TaskRun completa de app e artifact real.

## 2. Bloco C - Legacy / Deprecated

Status: GOVERNANCE_BLOCK_C_LEGACY_DELETION_READY.

Checkpoints concluidos:

- G14_RESIDUAL_ENDPOINT_OWNERSHIP_MAP_READY.
- G15_RESIDUAL_ENDPOINT_MIGRATION_READY.
- G16_LEGACY_CHAT_SERVICES_FOLDED_READY.
- G17_LEGACY_QUARANTINE_COMPLETED_READY.
- G18_LEGACY_DELETION_PREFLIGHT_READY.
- G19_LEGACY_DELETION_REGRESSION_READY.

Removido/quarentenado:

- `src/aipinho/api/routers/chat_router.py` foi movido para quarentena.
- `src/aipinho/api/routers/continue_integration_router.py` foi movido para quarentena.
- `config/runtime/runtime_profiles.yaml` antigo foi deletado da quarentena apos preflight.

Rotas migradas para ownership canonico:

- Chat direct/preview/approval command/session/timeline/raw/copy/feedback.
- `/v1/models`.
- `/v1/chat/completions`.
- `/v1/integrations/continue/chat`.
- `/v1/integrations/vscode/actions/preview`.
- `/v1/integrations/vscode/actions/execute`.
- Chat status/diagnostics/model-status/manual-inference.

Mantidos:

- `ChatService`: mantido como content provider para conversa comum.
- `ChatOperationRouterService`: mantido porque `ChatService` ainda importa internamente.
- `ChatPermissionGrantService`: mantido para semantica interna de grants, mas nao como autoridade final de rotas publicas.

Classificacao:

- Legacy removido: `config/runtime/runtime_profiles.yaml` antigo.
- Legacy bloqueado/quarentenado: `chat_router.py`, `continue_integration_router.py`.
- Legacy ainda ativo como autoridade publica: nao evidenciado.
- Legacy suspeito: helpers internos do `ChatService`, P1/P2, nao P0.
- Configs deprecated restantes: nenhuma evidenciada nos reports C/D.

Eventos/perguntas do Lucio:

- `legacy_path_called`: nao reportado como ocorrido nos summaries C/D.
- `legacy_path_blocked`: nao reportado como ocorrido nos summaries C/D.
- `deprecated_config_loaded`: nao reportado como ocorrido nos summaries C/D.
- `legacy_import_detected`: active import scan do G17 nao encontrou referencias ativas em `src/aipinho` para `chat_router`, `continue_integration_router` ou `config/runtime/runtime_profiles.yaml`.

Evidencia C:

- Focused regression: 35 passed in 84.18s.
- Reports em `C:\Dev\AIpinho\reports\governance_block_c`.

## 3. Bloco D - Firetest / comportamento

Status: GOVERNANCE_UNIFIED_SYSTEM_READY.

Checkpoints concluidos:

- G20_CONTEXT_DISCOVERY_GATE_READY.
- G21_READONLY_ANALYSIS_INTENT_READY.
- G22_FIX_REQUEST_TWO_PHASE_READY.
- G23_CAPABILITY_TRUTH_READY.
- G24_APPROVAL_PREVIEW_QUALITY_GATE_READY.
- G25_BEHAVIORAL_REGRESSION_READY.
- G26_MULTICHANNEL_GOVERNANCE_FIRETEST_READY.

Resultado de testes solicitados:

| Teste | Resultado | Evidencia |
| --- | --- | --- |
| conversa simples | passou | G26 direct chat |
| planning read-only | passou | `workspace_analysis_readonly`, sem approval |
| criacao de app/projeto | degradado/com cautela | lifecycle/gates testados; app real completo nao foi criado no D |
| criacao de pasta | passou | VSCode action preview com `create_directory` e pending approval |
| criacao de approval pending | passou | `pending_approval` quando preview contem plano valido |
| listar approvals pendentes | coberto anteriormente por rotas/approval command; nao foi destaque do G26 | exige firetest de campo se necessario |
| aprovar approval | parcial | VSCode execute registra approval decision; nao executa shell/write diretamente |
| TaskRun executavel | parcial | gate impede TaskRun sem plano; execucao real completa nao foi exercitada no D |
| artifact real | nao coberto no D | nao inventado |
| Speaker Truth | passou | sem falso sucesso antes de completion/validation |
| Mobile Chat | parcial | service path/persistent chat coberto; QA visual/mobile real nao clicado |
| Launcher Chat | parcial | persistent/service path coberto; QA visual Launcher real nao clicado |
| Continue/VSCode | passou | `/v1/chat/completions` e VSCode preview/execute canonicos |
| Pipeline | parcial/nao evidenciado no D | precisa firetest de campo |
| Model Gate | parcial | status/model routes canonicas existem; gate de modelo operacional nao foi foco do G26 |

Comportamentos comprovados:

- Nenhum approval de escrita antes de discovery/context em fix request.
- Nenhum approval sem `executable_plan_ref`, target files, expected outputs e validation plan.
- Pedido de relatorio/plano nao vira `write_files`.
- Pergunta de capacidade usa `CapabilityTruthService`, nao provider generico.
- Direct chat, persistent chat e Continue retornam lifecycle equivalente para classes cobertas.

Evidencia D:

- G20-G26: 15 passed in 52.60s.
- Matriz ampliada B/C/D + integracao chat: 46 passed in 132.13s.
- `py_compile`: passed.
- Reports em `C:\Dev\AIpinho\reports\governance_block_d`.

## 4. P0 / P1 / P2 ainda abertos

P0 abertos:

- Nenhum P0 comprovado nos reports C/D.

P1:

- QA visual/mobile real para approval button ainda nao executado.
- Criacao completa de app/projeto com TaskRun real, execucao, validation e artifact real ainda nao foi provada pelo Bloco D.
- Pipeline nao teve firetest dedicado no D.

P2:

- `ChatService` permanece como content provider e ainda contem imports/helpers internos legados, embora nao seja autoridade publica do lifecycle.
- Discovery real de workspace ainda e inicial/metadata/read-only; analise profunda incremental pode ser proximo sprint.
- Historicos/reports antigos ainda podem citar nomes legacy.

## 5. Estado do fluxo unico

- Chat direct: sim.
- Chat persistente / Mobile service path: sim para lifecycle; QA visual mobile real parcial.
- Launcher service path: parcial, por analogia com persistent chat; QA visual launcher real pendente.
- Continue/VSCode: sim para `/v1/chat/completions`, `/v1/integrations/continue/chat`, preview/execute.
- Pipeline: parcial/nao comprovado nos reports C/D.

Fontes canonicas:

- Policy: `CanonicalPolicyService` + configs `config/governance/policy.yaml`.
- Approval: `CanonicalApprovalService` para gate + `ApprovalService` para persistencia/decisao.
- TaskRun/runtime: `CanonicalRuntimeService` + runtime governado existente.
- Speaker Truth: `CanonicalSpeakerTruthService`.
- Artifact registry: nao foi alterado por C/D; usar registry existente, ainda precisa firetest de artifact real no proximo bloco.

## 6. App creation status

APP_CREATION_ALLOWED_WITH_CAUTION

Motivo:

O sistema ja pode voltar a trabalhar em criacao de apps pequenos sob supervisao, desde que o primeiro ciclo seja tratado como field trial controlado. O lifecycle agora impede approval prematuro e protege contra `write_files` generico. Ainda nao ha evidencia C/D de criacao completa de app com TaskRun real, validacao e artifact real. Portanto, nao e APP_CREATION_ALLOWED pleno.

Condicao recomendada para retomar:

- Comecar com app pequeno.
- Passar por discovery -> plano -> preview completo -> approval -> TaskRun -> validation -> artifact/report.
- Registrar tudo em report de campo.

## 7. Recomendacao para Bloco E

Recomendacao: Bloco E - App Creation Recovery & Canonical Project Bootstrap.

Foco sugerido:

- E0: field preflight para app pequeno.
- E1: project bootstrap canonico com discovery real.
- E2: TaskPreview executavel para app.
- E3: approval por botao e por comando.
- E4: TaskRun real de criacao de arquivos.
- E5: validation + artifact/report real.
- E6: Mobile/Launcher visual QA.

Nao ha P0 de governanca comprovado bloqueando o inicio do Bloco E, mas ele deve ser um field trial controlado, nao feature nova ampla.

## 8. Relatorios / artifacts reais

Bloco C:

- `C:\Dev\AIpinho\reports\governance_block_c\block_c_summary.md`
- `C:\Dev\AIpinho\reports\governance_block_c\G14_residual_endpoint_ownership_map.md`
- `C:\Dev\AIpinho\reports\governance_block_c\G14_residual_endpoint_ownership_map.json`
- `C:\Dev\AIpinho\reports\governance_block_c\G15_residual_endpoint_migration.md`
- `C:\Dev\AIpinho\reports\governance_block_c\G16_legacy_chat_services_folded.md`
- `C:\Dev\AIpinho\reports\governance_block_c\G17_legacy_quarantine_completed.md`
- `C:\Dev\AIpinho\reports\governance_block_c\G17_legacy_quarantine_manifest.json`
- `C:\Dev\AIpinho\reports\governance_block_c\G18_legacy_deletion_preflight.md`
- `C:\Dev\AIpinho\reports\governance_block_c\G18_legacy_deletion_manifest.json`
- `C:\Dev\AIpinho\reports\governance_block_c\G19_legacy_deletion_regression.md`

Bloco D:

- `C:\Dev\AIpinho\reports\governance_block_d\block_d_summary.md`
- `C:\Dev\AIpinho\reports\governance_block_d\G20_context_discovery_gate.md`
- `C:\Dev\AIpinho\reports\governance_block_d\G21_readonly_analysis_intent.md`
- `C:\Dev\AIpinho\reports\governance_block_d\G22_fix_request_two_phase.md`
- `C:\Dev\AIpinho\reports\governance_block_d\G23_capability_truth.md`
- `C:\Dev\AIpinho\reports\governance_block_d\G24_preview_quality_gate.md`
- `C:\Dev\AIpinho\reports\governance_block_d\G25_behavioral_regression.md`
- `C:\Dev\AIpinho\reports\governance_block_d\G26_multichannel_firetest.md`

Consolidado:

- `C:\Dev\AIpinho\reports\governance_block_cd\consolidated_block_cd_report.md`
- `C:\Dev\AIpinho\reports\governance_block_cd\consolidated_block_cd_report.json`

Artifacts reais:

- Nenhum artifact zip/binario novo foi gerado por este consolidado.

## Formato final

CONSOLIDATED_BLOCK_CD_REPORT_READY

- veredito C: GOVERNANCE_BLOCK_C_LEGACY_DELETION_READY
- veredito D: GOVERNANCE_UNIFIED_SYSTEM_READY
- P0 abertos: nenhum comprovado nos reports C/D
- legacy restante: somente helpers internos/content provider, sem autoridade publica evidenciada
- app creation status: APP_CREATION_ALLOWED_WITH_CAUTION
- recomendacao Bloco E: App Creation Recovery & Canonical Project Bootstrap

