# AIpinho Engineering Evolution - Bloco K

Data: 2026-07-02

Veredito: BLOCK_K_CONTINUOUS_RUNTIME_READY

## Objetivo

Transformar o runtime em um ciclo governado: Objetivo -> Plano -> Execucao -> Observacao -> Correcao -> Continuacao -> Conclusao.

## Arquitetura Implementada

Novos contratos:

- `ContinuousRuntimeCheckpoint`
- `ContinuousRuntimeCycle`
- `ContinuousRuntimeResume`

Novo servico:

- `ContinuousRuntimeService`

## Integracao

- `TaskRuntimeService.evaluate_continuous_runtime()` avalia uma `TaskRun` existente.
- O ciclo continua somente quando a run pode continuar.
- O ciclo para em `completed`, `needs_approval`, `needs_user` ou `blocked`.
- Conclusao de run completed usa Evidence Engine antes de declarar `completed`.
- Waiting input com approval vira `needs_approval`.
- Bloqueio/falha/cancelamento vira `blocked` com reason code.

## Arquivos Alterados

- `src/aipinho/schemas/runtime/continuous_runtime.py`
- `src/aipinho/services/runtime/continuous_runtime_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `tests/unit/test_continuous_runtime_service.py`

## Testes Executados

Comando:

```powershell
python -m py_compile C:\Dev\AIpinho\src\aipinho\schemas\runtime\continuous_runtime.py C:\Dev\AIpinho\src\aipinho\services\runtime\continuous_runtime_service.py C:\Dev\AIpinho\src\aipinho\services\runtime\task_runtime_service.py C:\Dev\AIpinho\tests\unit\test_continuous_runtime_service.py
python -m pytest tests/unit/test_continuous_runtime_service.py tests/unit/test_evidence_engine_service.py tests/unit/test_worker_registry_service.py tests/unit/test_task_runtime_service.py tests/unit/test_hotfix_policy_kernel_approval_gate.py tests/governance/test_g21_readonly_analysis_intent.py tests/governance/test_lifecycle_core.py tests/governance/test_g24_preview_quality_gate.py -q
python -c "from aipinho.app_factory import create_app; app=create_app(); print(app.title); print(len(app.routes))"
```

Resultado:

```text
60 passed
AIpinho
942
```

## Smoke em Backend Vivo

Backend reiniciado pelo script canonico:

```text
C:\Dev\AIpinho\scripts\dev\stop_aipinho_9088.ps1
C:\Dev\AIpinho\scripts\dev\start_aipinho_9088.ps1
```

Resultado:

```text
AIpinho API started.
PID: 51296
Bind: 0.0.0.0:9088
Health: {"status":"ok","service":"AIpinho","version":"0.1.0","runtime":"local"}
```

Smoke criado:

```text
run_id: task_run_d5ea8f0ea35f43e8a535954d0fb7a588
cycle_status: continue
stage: continuation
next_action: continue_runtime
checkpoints: 3
reason_code: task_status:created
```

## Regression Candidates

- Run criada/queued/running/partial deve continuar.
- Run waiting_input com approval deve pedir approval.
- Run blocked/failed/cancelled deve parar com bloqueio real.
- Run completed so pode concluir com Evidence Engine aprovado.
- Ciclo deve sempre conter checkpoints auditaveis.

## Rollback

Rollback seguro:

1. Remover `ContinuousRuntimeService` do `TaskRuntimeService`.
2. Remover `src/aipinho/services/runtime/continuous_runtime_service.py`.
3. Remover `src/aipinho/schemas/runtime/continuous_runtime.py`.
4. Remover testes de continuous runtime.

Como o Bloco K e avaliativo e nao inicia background loop sozinho, rollback nao exige migracao de dados.

## Limitacoes

- Ainda nao ha scheduler continuo em background.
- O ciclo avalia o estado atual; execucao automatica multi-step sera papel do Bloco L.
- Nenhum endpoint publico dedicado foi criado neste bloco.

## Proximo Bloco

Bloco L pode iniciar agora, porque o Bloco K tem contratos, servico, integracao runtime, testes, smoke vivo e rollback documentado.
