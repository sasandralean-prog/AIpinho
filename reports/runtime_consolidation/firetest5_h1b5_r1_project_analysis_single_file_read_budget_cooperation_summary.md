# H1B5.R1 - ProjectAnalysis Single-File Read Budget Cooperation

## Veredito

`FIRETEST5_H1B5_R1_PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_COOPERATION_READY`

READY com findings publicos residuais. A fronteira `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED` foi superada no caminho publico: ProjectAnalysis retornou `partial`, `safe_to_continue=true` e o artifact runtime foi alcancado. O FireTest 5 completo ainda nao deve ser declarado READY porque a resposta publica sincrona estourou no cliente, a run precisou de cleanup governado e nao houve `result.json` final nem Truth completo.

## Objetivo

Fazer ProjectAnalysis cooperar com orcamento por arquivo, preservar estado parcial e permitir handoff para artifact runtime quando houver contexto parcial suficiente, sem aumentar timeout global e sem mascarar bloqueios.

## Escopo E Nao-Goals

Implementado apenas o repair slice de leitura/selecao bounded de ProjectAnalysis e a consciencia CVL associada. Nao houve H1B6, nao houve alteracao de `/api/v1/chat` para `accepted_running`, nao houve nova relationship capability, nao houve bypass de artifact runtime, nao houve relaxamento de Validation/Completion/Speaker Truth.

## Causa Observada Antes

A run limpa anterior bloqueava em `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`, com `last_checkpoint=project_analysis_single_file_read_budget_exceeded`, `blocking_operation=file_read`, `files_read=3`, `bytes_read=17214`, sem alcancar `artifact_creation_started`.

## Arquivos Alterados

- `src/aipinho/services/analysis/file_context_builder.py`
- `src/aipinho/services/analysis/project_analysis_service.py`
- `src/aipinho/schemas/analysis/project_analysis_cooperation.py`
- `src/aipinho/schemas/analysis/project_analysis_result.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `src/aipinho/services/cvl/cognitive_readiness_service.py`
- `config/runtime/task_run_event_policy.yaml`
- `tests/unit/test_project_analysis_single_file_read_budget_cooperation.py`
- `tests/unit/test_cognitive_validation_laboratory_service.py`

## Arquitetura Antes/Depois

Antes, `FileContextBuilder` podia perceber estouro somente depois de uma leitura individual cara e emitir `project_analysis_single_file_budget_exceeded`, derrubando ProjectAnalysis inteira. Depois, cada candidato recebe uma decisao pre-leitura `read|partial_read|skip`, com custo estimado, bytes solicitados, orcamento restante, reason code e provenance.

## Read Budget Policy

A politica usa sinais generalistas: `max_single_file_read_ms`, `max_file_bytes`, `max_total_bytes`, orcamento restante de contexto, tamanho do arquivo e amostra minima segura. Nao ha regra por linguagem, extensao, arquivo, projeto ou caminho local.

## Selection/Read Cooperation

Arquivos caros podem virar `partial_read` bounded. Arquivos que nao cabem mais em uma amostra minima viram `skip` governado. `FileReadPlan` e `ProjectAnalysisResult` preservam `files_partial_read`, `files_skipped`, `bytes_skipped_estimated` e `read_decisions`.

## ProjectAnalysisResult E safe_to_continue

`ProjectAnalysisResult` agora carrega decisoes de leitura e contadores de partial/skip. `safe_to_continue=true` continua condicionado a `partial_readiness`, nao apenas ao fato de haver algum conteudo. Se o contexto parcial e suficiente, runtime pode seguir com limitation; se nao e, bloqueia.

## Runtime/Summary

O summary leve expoe amostra de `read_decisions`, contadores de `files_partial_read/files_skipped` e `bytes_skipped_estimated`. O payload detalhado fica no resultado/diagnostico, nao inline gigante.

## CVL/Fase 0

CVL passou a reconhecer fronteiras generalistas de ProjectAnalysis/read cooperation:

- `PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED`
- `PROJECT_ANALYSIS_FILE_SKIPPED_BY_SINGLE_FILE_BUDGET`
- `PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE`
- `PROJECT_ANALYSIS_PARTIAL_CONTEXT_INSUFFICIENT`
- `PROJECT_ANALYSIS_SELECTION_READ_COOPERATION_MISSING`

A previsao vem de `frontier_context`/metadata/coverage de ProjectAnalysis, nao de string de FireTest, path, Kotlin ou arquivo especifico.

## Testes Executados

```text
python -m pytest tests/unit/test_project_analysis_single_file_read_budget_cooperation.py -q
3 passed

python -m pytest tests/unit/test_project_analysis_single_file_read_budget_cooperation.py tests/unit/test_cognitive_validation_laboratory_service.py -q
18 passed

python -m pytest tests/unit/test_project_analysis_single_file_read_budget_cooperation.py tests/unit/test_universal_task_session_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_relationship_stack_integration_audit.py tests/unit/test_project_analysis_service.py tests/unit/test_project_analysis_public_boundary.py -q
54 passed in 86.37s
```

`py_compile` passou para os arquivos alterados.

## Anti-Hardcode

Busca nos arquivos alterados nao encontrou regra nova baseada em `Pinhoabacaxi`, `music_inventory`, `C:\Dev`, Kotlin, arquivo especifico, extensoes especificas ou relacoes finais. Achados com `FireTest` foram referencias estruturais antigas de CVL (`FireTestProfile/FireTestLaboratoryService`) e titulos de relatorios, nao logica nova de decisao.

## FireTest Publico Controlado

Run publica canonica relevante:

```text
task_run_id = task_run_6b571a6d279647ba842a8ae25a1243dc
workspace = C:\Users\rafae\Documents\PinhoabacaxiMusicasDesktop
library_roots = D:\rafa\pinho music
client_response_status = timeout
client_response_time_ms = 360026
final_run_status = blocked apos cleanup/idempotency
finished_at = 2026-08-13T02:29:02.187349+00:00
```

Run auxiliar anterior em `C:\Dev\AIpinho` tambem confirmou a recuperacao de ProjectAnalysis, mas nao e a evidencia principal do FireTest canonico.

A primeira tentativa publica foi bloqueada antes de TaskRun por `phase_dependency_artifacts_missing` porque o texto mencionava Fase 1 e Fase 0, fazendo o runtime interpretar `phase_0` como artifact operacional predecessor. As tentativas validas mantiveram a referencia de Fase 0 no `ChatContext`, sem transforma-la em dependencia textual operacional.

## Resultado Publico Observado

ProjectAnalysis atravessou como partial governado:

```text
analysis_status = partial
reason_code = PROJECT_ANALYSIS_COMPLETED
safe_to_continue = true
partial_readiness.reason_codes = [PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE]
duration_ms = 34093
files_discovered = 76
files_scan_attempted = 127
files_scanned = 78
files_selected = 12
files_read = 12
bytes_read = 34564
last_checkpoint = after_result_serialization
```

Artifact runtime foi alcancado:

```text
artifact_creation_started_count = 3
artifact_created_count = 2
reports/firetest5/phase1_discovery.md = created
reports/firetest5/project_inventory.md = created
reports/firetest5/music_inventory.csv = artifact_creation_started; late artifact rejected after terminal cleanup
```

Isso satisfaz o criterio H1B5.R1 de melhora real: `artifact_creation_started_count > 0` apos ProjectAnalysis parcial seguro.

## Findings Publicos Residuais

A resposta `/api/v1/chat` ainda e sincrona e estourou no cliente. A run nao gerou `result.json` antes do cleanup completo, e os endpoints podem ficar lentos durante coleta. Apos o cleanup, o runtime registrou `artifact_late_rejected` para o artifact tardio e `terminalization_already_applied` para tentativas posteriores, indicando que a politica late artifact reject e a idempotencia terminal da H1B4.3.3 continuaram preservadas.

## Calibracao Phase0 vs Phase1

A calibracao canonica pos-execucao ficou `mismatch` de proposito util: a Fase 0 previu `PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE`, mas a fronteira real observada foi `ARTIFACT_RENDER_TERMINALITY` com `ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED`. Isso e bom sinal para H1B5.R1: ProjectAnalysis deixou de ser a fronteira dominante e a proxima fronteira voltou para artifact/public response boundary.

## Gaps Restantes

- `/api/v1/chat` continua preso ao boundary sincrono para runs longas.
- Summary/truth/artifacts endpoints podem ficar lentos quando a run nao tem result final coerente.
- A selecao ProjectAnalysis publica consumiu cerca de 40s em `project_analysis_selection_checkpoint`, novo ponto a observar em wave futura se necessario.
- A run canonica usou o workspace correto e registrou `library_roots = D:\rafa\pinho music`, mas o flow publico ainda nao finalizou result/truth sem cleanup.

## Proxima Recomendacao

Se o objetivo imediato for estabilizar o caminho publico: `H1B6 - Public Runtime Response Boundary accepted_running / timeout_blocked`.

Se o objetivo for repetir FireTest 5 sobre o workspace/corpus correto depois do H1B5.R1: fazer uma run diagnostica curta com `ChatContext` correto e sem dependencia textual falsa de Fase 0.

## Garantias Preservadas

Nao houve bypass, nao houve hardcode, nao houve timeout global aumentado, nao houve artifact fake, nao houve backend escrevendo artifact fora do runtime existente, nao houve relaxamento de Validation/Completion/Speaker Truth e nenhum sucesso foi declarado sem evidencia.
