# H1B6 ? Public Runtime Response Boundary + Debt Closure

## Veredito

`FIRETEST5_H1B6_PUBLIC_RUNTIME_RESPONSE_BOUNDARY_READY_WITH_ENDPOINT_WINDOW_FINDING`

A H1B6 implementou o boundary p?blico governado: `/api/v1/chat` n?o ficou preso por minutos e retornou `accepted_running` com `task_run_id` persistido. A run p?blica limpa terminalizou de forma coerente com `result.json`, `finished_at`, fila limpa e um ?nico evento terminal.

H? um finding residual: durante uma janela de renderiza??o ativa, `summary`/`artifacts` ainda podem oscilar acima do or?amento curto de polling. Ap?s a primeira janela, e no estado final, endpoints ficam leves e coerentes.

## Escopo

- `accepted_running` e `timeout_blocked` como estados p?blicos n?o-sucesso.
- `PublicRuntimeResponsePolicy` configur?vel.
- `result finalization` coerente para terminalidade governada.
- Terminaliza??o idempotente preservada.
- Corre??o do falso `phase_dependency_artifacts_missing` por men??o textual a Fase 0/Fase 1.
- Proje??o/compacta??o formal de storage para impedir `run.json` gigantes.
- Proje??o leve de artifacts para evitar varredura global no caminho p?blico.

## Arquivos Alterados

- `src/aipinho/schemas/chat/chat_response.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/runtime/task_run_store.py`
- `src/aipinho/services/runtime/task_queue_service.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/runtime_storage_compaction_service.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `src/aipinho/services/cvl/cognitive_readiness_service.py`
- `config/runtime/task_run_event_policy.yaml`
- `tests/unit/test_public_runtime_response_boundary.py`
- `tests/unit/test_public_chat_phase_dependency_boundary.py`
- `tests/unit/test_public_runtime_result_finalization.py`
- `tests/unit/test_task_run_store.py`
- `tests/unit/test_artifact_runtime_service.py`

## Run P?blica Limpa

- `session_id`: `chat_h1b6_public_endpoint_light_20260813060155`
- `task_run_id`: `task_run_ad519431dd5146bea4043f4beeab011d`
- `client_response_status`: `accepted_running`
- `client_response_time_ms`: `5991`
- `server_final_status`: `completed`
- `result.status`: `completed`
- `finished_at`: `2026-08-13T06:05:20.881042+00:00`
- `terminal_event_count`: `1`
- `artifact_creation_started_count`: `3`
- `artifact_created_count`: `3`
- `queue_after`: `active=0 queued=0 pending=0`
- `run_json_bytes`: `88666`

## Endpoint Timings

M?ximos observados na run limpa:

- `artifacts`: `8009 ms`
- `events`: `463 ms`
- `result`: `8000 ms`
- `summary`: `8037 ms`
- `truth`: `5316 ms`

Finding residual:

- `summary`/`artifacts` tiveram timeouts transit?rios em janela ativa de renderiza??o.
- `truth` ativo ficou leve ap?s patch de proje??o (`RuntimeTruthEngine` sem timeline pesada quando `result` ainda n?o existe).
- Estado final respondeu de forma coerente: `summary=46ms`, `truth=5316ms`, `events=22ms`, `artifacts=89ms`, `result=13ms`.

## Storage Projection / Compaction

A descoberta dos `run.json` gigantes foi canonizada como d?vida acoplada da H1B6.

- Servi?o criado: `RuntimeStorageCompactionService`.
- `run_index.json` ? escrito em `create_run/update_run/save_result` via `TaskRunStore`.
- `queue.reconcile()` usa `list_queue_runs()` e n?o parseia hist?rico terminal gigante.
- Payloads grandes s?o preservados em `payload_refs`, com hash/ref, sem apagar evid?ncia.
- Compacta??o emergencial anterior: `10` arquivos, `1528561957` bytes salvos.
- Compacta??o formal: `5` arquivos, `4674813` bytes salvos.
- Projection health final: `ok`, `large_run_count=0`, `missing_index_count=0`.

## Result / Terminality

- `accepted_running` n?o ? sucesso.
- `timeout_blocked` n?o ? sucesso.
- `safe_to_report_success` permanece `false` em estados n?o terminais.
- Run p?blica final teve exatamente um evento terminal.
- Nenhum `artifact_created` p?s-terminal foi observado.
- `result.json` foi preservado e coerente.

## Testes

- `py_compile`: PASS.
- Integrado H1B6/H1B5/R1/storage/artifact projection:

```text
74 passed in 93.77s
```

## Gaps Restantes

- `summary`/`artifacts` ainda podem ter janela transit?ria lenta enquanto artifact render est? em se??o ativa. Recomendo repair slice focado em endpoint projection/cache para estado `artifact_creation_started` sem artifact index pronto.
- `truth` final ainda leva cerca de 5s porque monta timeline completa; aceit?vel para diagn?stico, mas ainda melhor?vel como endpoint leve final.
- N?o buscar `FIRETEST5_READY` ainda; pr?xima rodada deve ser diagn?stico p?blico completo com relationship flow observ?vel.

## Por Que N?o Houve Bypass

- Runtime continuou criando TaskRun real.
- Artifacts continuaram passando pelo Artifact Runtime/registry existente.
- Storage projection n?o cria lifecycle, n?o cria terminalidade, n?o cria artifact, n?o decide Validation/Completion/Speaker Truth.
- Nenhum timeout global foi aumentado como solu??o.
- N?o houve hardcode de FireTest/projeto/path/artifact espec?fico como condi??o de sucesso.

## Recomenda??o

Antes de H1B7, executar um FireTest 5 diagn?stico completo com Fase 0/CVL, ProjectAnalysis partial, artifact runtime e H1B5 relationship flow observ?vel. Se a janela lenta de endpoint voltar a ser dominante, criar repair slice espec?fico de lightweight endpoint projection durante artifact render ativo.
