# Sprint 18 ? End-to-End Operator Firetest

Veredito: **CONFIG_GOVERNANCE_OPERATOR_REQUIRES_PATCH**

## Resumo
O backend, o contrato de workspace-flow e os servi?os de governan?a passaram nos testes focados. O endpoint can?nico `/api/v1/workspace-flows/plan` agora aceita o payload estruturado usado pela UX (`source`/`target` com `workspace_id`) sem criar rota duplicada.

O fluxo de configura??o foi executado por bypass autorizado na camada HTTP/token, mas ainda usando `ConfigGovernanceService`, preview, approval, apply, backup e rollback. A muta??o HTTP direta continuou bloqueada por `local_token_required`, ent?o o operador real via Mobile/Launcher ainda n?o pode ser declarado pronto.

## Readiness
- BACKEND_READY: True
- MOBILE_UX_READY: build_ready_not_operator_verified
- LAUNCHER_UX_READY: py_compile_ready_not_operator_verified
- OPERATOR_FLOW_READY: partial_service_bypass_only
- SPEAKER_TRUTH_READY: not_exercised_in_full_operator_flow

## Corre??es Aplicadas
1. Workspace Flow Contract: `source/target` estruturados com `workspace_id` agora resolvem paths relativos pelo registry.
2. Settings UX: Mobile e Launcher ganharam controles de criar workspace, aprovar, aplicar e rollback usando endpoints can?nicos j? existentes.

## Evid?ncias
- Health backend 9088: ok.
- Testes Python focados: 13 passed.
- Kotlin compileDebugKotlin: BUILD SUCCESSFUL.
- Workspace `rafael_downloads`: criado por fluxo governado com approval e backup.
- Workspace `sprint_file_sync`: criado por fluxo governado com approval e backup.
- Rollback probe: aplicado e revertido; workspace tempor?rio n?o ficou presente.
- Copy flow Downloads -> Sprint File Sync: `pending_approval` para `create_file` e `copy_to`.
- Git push flow: `pending_approval`, sem execu??o livre.

## Gaps / Riscos
- P0: token HTTP/local pairing rejeitou a muta??o por endpoint protegido (`local_token_required`).
- P1: Mobile/Launcher foram compilados, mas n?o certificados por operador real nesta execu??o.
- P1: Speaker Truth n?o foi exercitado em fluxo completo de task/approval/resume.
- P1: log hist?rico pr?-restart continha `ApprovalRequest` com extra fields; sem recorr?ncia fresca, mas deve ser auditado no Sprint 19.

## Pr?ximo Passo Obrigat?rio
Sprint 19 deve ler este relat?rio e fechar os gaps acima, principalmente o alinhamento token/pairing/HTTP operator path e a valida??o de Speaker Truth.
