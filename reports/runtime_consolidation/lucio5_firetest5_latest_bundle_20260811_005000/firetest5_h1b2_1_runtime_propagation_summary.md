# FireTest 5 - H1B2.1 Runtime Propagation Summary

## Resultado

Status da wave: `READY_WITH_FINDINGS`.

A H1B2.1 corrigiu a propagacao real de papeis de raiz e contrato de selecao no caminho publico sem criar observer de midia, regra de musica, filtro por extensao ou excecao para FireTest.

## Causa Raiz

A rodada limpa anterior mostrou que `workspace_context` carregava `library_roots`, mas a percepcao do artifact chegava sem:

- `source_root_role`
- `entity_role`
- `expected_entity_role`
- `allowed_root_roles`
- `policy_rejection_reasons`

A investigacao encontrou duas causas:

1. O backend publico estava stale. O processo `uvicorn aipinho.main:app` ainda estava ativo desde `2026-08-10 18:32:53`, antes das ultimas mudancas de H1B2.
2. Mesmo no codigo atual, havia fragilidade de propagacao: roots explicitas podiam ser duplicadas como `external_roots` e `library_roots`, com risco de `external_root` vencer antes de `library_root` na compilacao de entidades.

## Correcoes

### Workspace Root Roles

- A montagem de `workspace_context` agora classifica roots explicitas por marcadores semanticos proximos ao caminho.
- `Biblioteca`, `library`, `corpus`, `collection`, `colecao` e `dataset` indicam papel de biblioteca/corpus de forma generica.
- `Projeto`, `project`, `workspace` e `app` indicam papel de projeto.
- Uma root classificada como `library_root` nao e mais duplicada silenciosamente como `external_root`.

### Deduplicacao de Root Role

`ObservedEntityCompilationService` agora resolve roots duplicadas por precedencia semantica:

`corpus_root > library_root > source_code_root > project_root > artifact_root > external_root > unknown_root`

Assim, se a mesma raiz aparecer como externa e como biblioteca, o papel de biblioteca/corpus vence.

### No Silent All-Files Fallback

`ContractDrivenPerceptionService` agora bloqueia quando detecta roots de corpus no grafo, mas o contrato tabular chega sem politica de selecao aplicavel.

Novo reason code:

- `ENTITY_SELECTION_POLICY_NOT_APPLIED`

Tambem foram adicionados bloqueios para:

- `ROOT_ROLE_METADATA_MISSING`
- `ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT`
- `WORKSPACE_ROLE_MISMATCH`

### Renderer

O renderer tabular continua renderizando apenas `selected_entity_ids`.

Agora o summary curto de entidades selecionadas tambem expoe:

- `source_root_role`
- `entity_role`
- `selection_eligibility`
- `exclusion_reasons`

### Attribute Identity / Schema Validation

Foi corrigida a validacao semantica de schema para usar identidade canonica:

- `expected_schema` permanece auditavel como label bruto.
- `canonical_schema` e `attribute_contracts` sao usados para comparar schema.
- `extens?o`, `extensao` e `extensão` convergem para `canonical_key=extension`.
- O CSV pode renderizar `display_label=extensão`.

Isso evita bloqueio falso como `artifact_schema_field_missing:extens?o` quando o header renderizado esta semanticamente correto.

### Summary Endpoint

`UniversalTaskSessionService.summary()` agora prioriza `BLOCKED` quando:

- `result.status=blocked`
- `validation.status=blocked`
- `approval.status=not_required`

Isso evita a incoerencia `WAITING_USER` em runs bloqueadas por validacao sem approval pendente.

### Runtime Fingerprint

`GET /api/v1/chat/diagnostics` agora inclui `runtime_fingerprint` com hashes dos modulos relevantes:

- `readonly_analysis_artifact_runtime_service.py`
- `observed_entity_compilation_service.py`
- `contract_driven_perception_service.py`
- `cognitive_validation_laboratory_service.py`

Objetivo: detectar endpoint publico rodando codigo stale/import antigo/wiring antigo.

Validacao apos restart do backend publico:

```text
GET /api/v1/chat/diagnostics
status = ok
service = canonical_chat_diagnostics
runtime_fingerprint = 6adb1fe25db2618264b96bcc8ba9bab3bb902996b343603bda354813386f83dd
modules =
  readonly_analysis_artifact_runtime_service.py: loaded
  observed_entity_compilation_service.py: loaded
  contract_driven_perception_service.py: loaded
  cognitive_validation_laboratory_service.py: loaded
```

Isso confirma que o endpoint publico reiniciado esta carregando os modulos instrumentados por H1B2.1.

### CVL

O CVL ganhou fronteira anterior a capability matching:

- `WORKSPACE_ROLE_BOUNDARY`
- `ENTITY_SELECTION_POLICY`

Novos reason codes preditivos:

- `PREDICTED_WORKSPACE_ROLE_BOUNDARY`
- `PREDICTED_ENTITY_SELECTION_POLICY_GAP`
- `PREDICTED_CORPUS_ROOT_NOT_OBSERVED`

Assim o CVL pode prever que o bloqueio ainda esta em root-role/entity-selection antes de concluir que a fronteira dominante e metadata capability missing.

## Arquivos Alterados

- `config/artifacts/observed_entity_policy.yaml`
- `src/aipinho/api/routers/governance_lifecycle_router.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/artifacts/observed_entity_compilation_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `src/aipinho/services/runtime_doctor/runtime_doctor_service.py`
- `tests/governance/test_runtime_vertical_slice.py`
- `tests/unit/test_cognitive_validation_laboratory_service.py`
- `tests/unit/test_contract_driven_perception_service.py`

## Testes

Executados com sucesso:

```text
python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_universal_task_session_service.py -q
38 passed
```

```text
python -m pytest tests/governance/test_runtime_vertical_slice.py::test_h3_complete_readonly_artifact_prompt_bootstraps_without_clarification tests/governance/test_runtime_vertical_slice.py::test_readonly_artifact_discovery_with_no_workspace_mutation_language_keeps_all_roots tests/governance/test_runtime_vertical_slice.py::test_public_chat_and_service_path_apply_corpus_entity_selection_policy -q
3 passed
```

Tambem executado com sucesso:

```text
python -m pytest tests/governance/test_runtime_vertical_slice.py::test_public_chat_and_service_path_apply_corpus_entity_selection_policy tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py -q
23 passed
```

Observacao: a execucao completa de `tests/governance/test_runtime_vertical_slice.py` e a suite combinada maior excederam o timeout local. Os testes focados da fronteira H1B2.1 passaram.

## Antes / Depois

### Antes

```text
workspace_context.library_roots = presente
observed_entity_graph.root_descriptors = ausente no runtime publico antigo
source_root_role = null
entity_role = null
allowed_root_roles = null
selected_entity_count = todos os arquivos
renderer = preenchia CSV com project/build/cache
```

### Depois

No teste publico/service equivalente:

```text
project_root = project_app
library_roots = library_corpus
roots_scanned_by_role.project_root = [project_app]
roots_scanned_by_role.library_root = [library_corpus]
selected_entity_count = 2
candidate_entity_count = 11
selected entities source_root_role = library_root
selected entities entity_role = corpus_file
project/build/.gradle/src rejected by policy
CSV rows = Alpha.track, Beta.track
extension/extensão derived generically
codec blocked by NO_MATCHING_CAPABILITY
Speaker Truth safe_to_report_success = false
```

## Gaps Restantes

- Sem `MediaMetadataObserver`, atributos como `codec`, `container`, `bitrate`, `sample_rate`, `canais`, `duracao`, `artwork` e `metadata` devem continuar bloqueados.
- A proxima rodada do FireTest 5 deve confirmar no backend reiniciado se a H1B2.1 atravessa o endpoint publico real.
- A proxima fronteira esperada continua sendo `Observational Capability Execution Boundary`, nao metadata observer ainda.

## Por Que MediaMetadataObserver Nao Foi Criado

Esta wave nao implementa observer de audio/midia porque isso resolveria o sintoma do FireTest antes de provar a fronteira de identidade de raiz e selecao de entidade.

O objetivo desta wave foi garantir:

```text
antes de perguntar quais atributos faltam,
o Runtime precisa provar que a entidade veio da raiz certa
e que foi selecionada pelo contrato certo.
```

Esse objetivo agora esta coberto por testes e por bloqueios causais.
