# HOTFIX — Gemini -> AIpinho Capability Negotiation

Data: 2026-06-23

## Veredito

GEMINI_AIPINHO_CAPABILITY_HOTFIX_READY_WITH_WARNINGS

## Objetivo

Corrigir a negociacao generica de capabilities na delegacao Gemini -> AIpinho para que pedidos operacionais amplos nao sejam bloqueados antes de child run quando a rota e o workspace permitem pelo menos uma fase inicial read-only governada.

## Causa raiz

O bloqueio vinha de uma divergencia entre:

- aliases usados pelos agentes e pelo Gemini Executor;
- capabilities declaradas no perfil da AIpinho;
- capabilities permitidas na rota Gemini -> AIpinho;
- classificacao de operation_type em pedidos compostos.

Pedidos com leitura + criacao de artifact + build/test podiam ser reduzidos a `artifact_request` ou bloqueados por `target_agent_missing_capability`, mesmo quando a execucao segura deveria iniciar por uma fase read-only e deferir fases posteriores para gates/approval.

## Correcoes aplicadas

1. Capability registry
   - Adicionadas capabilities canonicas `build` e `test`.
   - Adicionados aliases genericos para artifact/report/build/test/validation.
   - Mantida separacao entre shell livre e build/test governados.

2. Agent registry
   - AIpinho, Lucio e Gemini passaram a declarar `build` e `test` como capabilities governadas.

3. Delegation policy
   - Rotas para AIpinho aceitam `delegated_governed_execution` e `operational_task_request`.
   - Rotas para AIpinho aceitam `build` e `test` como fases governadas.

4. AgentDelegationPolicyService
   - Adicionada metadata estruturada de capability negotiation.
   - Adicionada negociacao por fase: capabilities futuras podem ser deferidas se a fase inicial read-only puder iniciar.
   - Bloqueios reais agora incluem `missing_capabilities`, aliases resolvidos, capabilities do target, capabilities da rota, workspace policy e `whether_execution_started=false`.

5. AgentDelegationService
   - `DelegationResult.metadata_sanitized` agora preserva o diagnostico estruturado de bloqueios.
   - Evento `delegation_blocked` inclui metadata sanitizada.

6. GeminiExecutorService
   - Pedidos compostos com build/test ou leitura+write+validation viram `delegated_governed_execution`.
   - Artifact simples continua `artifact_request`.
   - Criacao simples continua `workspace_operation`.
   - Mensagem do Gemini nao promete child-run quando a delegacao foi bloqueada ou nao iniciou execucao real.

## Arquivos alterados

- `C:\Dev\AIpinho\config\policies\capability_registry.yaml`
- `C:\Dev\AIpinho\config\agents\agent_registry.yaml`
- `C:\Dev\AIpinho\config\agents\delegation_policy.yaml`
- `C:\Dev\AIpinho\src\aipinho\schemas\agents\delegation.py`
- `C:\Dev\AIpinho\src\aipinho\services\agents\agent_delegation_policy_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\agents\agent_delegation_service.py`
- `C:\Dev\AIpinho\src\aipinho\services\gemini_executor\gemini_executor_service.py`
- `C:\Dev\AIpinho\tests\unit\test_agent_delegation_service.py`
- `C:\Dev\AIpinho\tests\unit\test_gemini_executor_service.py`

## Testes executados

- `python -m py_compile src\aipinho\services\agents\agent_delegation_policy_service.py src\aipinho\services\agents\agent_delegation_service.py src\aipinho\services\gemini_executor\gemini_executor_service.py src\aipinho\schemas\agents\delegation.py`
- `python -m pytest tests\unit\test_agent_delegation_service.py tests\unit\test_gemini_executor_service.py -q`

Resultado:

- 23 passed in 4.13s

## Smoke

Smoke direto da camada de delegacao Gemini -> AIpinho:

- status: `running`
- decision: `auto_approve`
- child_run_id: criado
- child_operation_type: `delegated_governed_execution`
- aliases confirmados:
  - `scan_workspace -> read_workspace`
  - `create_file -> write_workspace`
  - `workspace_write -> write_workspace`
  - `create_artifact -> artifact_write`
  - `run_shell_build -> build`
  - `run_tests -> test`

Smoke via Gemini Executor completo com `workspace_context` real ficou `blocked` antes da delegacao porque o workspace resolver do Gemini nao reconheceu o path real nesse harness. Isso foi classificado como warning externo ao hotfix de capability negotiation, pois a delegacao direta passou e nao houve falsa promessa de child-run.

## Hardcode / specific-case

Varredura focada nos arquivos alterados nao encontrou referencias a:

- SapoAndando
- PinhoForgeStudio
- nomes especificos de artifact
- frases especificas de prompt

As alteracoes foram feitas via registry/config, policy e services genericos.

## Riscos restantes

- O Gemini Executor completo ainda depende do workspace resolver/policy reconhecer caminhos reais antes de chegar na delegacao.
- `build` e `test` agora sao capabilities governadas declaradas; fluxos com side effect continuam sujeitos aos gates existentes.

## Conclusao

O bloqueio por negotiation de capabilities foi corrigido de forma generica. Gemini pode delegar para AIpinho tarefas operacionais compostas sem cair em `artifact_request` simples e sem bloquear antes do child-run quando as capabilities estao declaradas ou deferiveis por fase.
