# Sprint 19 ? Hardening, Regression, Security Gates e Speaker Truth

Veredito: **SPRINT19_HARDENING_READY_WITH_OPERATOR_UX_FIELD_WARNING**

## Fonte Prim?ria
O Sprint 19 leu primeiro o relat?rio do Sprint 18: `reports/sprint18_operator_firetest_20260623_113400.md`. O hardening foi guiado pelos gaps reais do Sprint 18, n?o por uma lista gen?rica.

## Corre??es / Fechamentos
1. **Token HTTP/operator path ? corrigido.**
   - Causa raiz: token local do backend estava com preview diferente do token oficial usado pelo operador/mobile.
   - A??o: realinhado o hash local sem imprimir plaintext.
   - Evid?ncia: endpoint protegido criou mudan?a tempor?ria, aprovou, aplicou e fez rollback; `temp_still_present=false`.

2. **ApprovalRequest extra fields ? fechado como n?o reproduzido no schema atual.**
   - O schema atual aceita os campos que apareciam como extras no log hist?rico.
   - Planos `copy_file` e `git_push` criaram `approval_id` normalmente ap?s restart.

## Regress?o Executada
- 16 testes focados passaram.
- py_compile passou nos m?dulos envolvidos.
- Android `compileDebugKotlin` passou.

## Security Gates
- Muta??o HTTP de config exige token: sim.
- Token plaintext em status: n?o.
- Workspace write/copy pede approval: sim.
- Git push pede approval: sim.
- Rotas duplicadas adicionadas: n?o.
- Execu??o perigosa livre observada: n?o.

## Avisos Restantes
- QA real de operador Mobile/Launcher ainda precisa ser rodado em campo.
- Speaker Truth em fluxo completo de task/approval/resume ainda precisa ser validado visualmente.

## Veredito Final
Kernel/backend e contratos est?o endurecidos para os gaps do Sprint 18. O Sprint 19 fica aprovado com warning de valida??o de campo UX/Speaker, n?o por falha de kernel.
