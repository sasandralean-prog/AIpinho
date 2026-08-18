# AIpinho - Deterministic Inference & Diagnosis Consolidated Report

## Status

READY

## Contexto

Esta wave foi executada apos a estabilizacao parcial do Runtime Governado e apos a suspeita de que a fronteira de inferencia local ainda estava pouco observavel.

O objetivo nao foi fazer o FireTest passar artificialmente, nem corrigir um caso especifico. A meta foi fortalecer genericamente duas fronteiras estruturais da AIpinho:

1. Inferencia de modelos.
2. Diagnostico tecnico para tarefas de coding.

A premissa principal foi:

Nenhum componente novo pode tomar autoridade de outro componente existente sem migrar explicitamente a responsabilidade.

## Problema arquitetural identificado

Antes desta wave, a cadeia de inferencia ainda tinha pontos onde o Runtime conversava diretamente com o provider `LlamaCppProvider`.

Fluxo anterior simplificado:

```text
Role / Chat / Router / Smoke Test
    -> LlamaCppProvider
    -> llama.cpp
    -> stdout
    -> parser
    -> Runtime
```

Isso mantinha o modelo como uma fronteira pouco governada:

- `cwd` era herdado implicitamente.
- `env` era herdado implicitamente.
- PATH efetivo nao era fingerprintado.
- executable e modelo nao eram fingerprintados no resultado.
- stdout/stderr existiam, mas nao havia telemetria canonica unica.
- consumers distintos podiam chamar preview/invoke diretamente.

Em paralelo, o fluxo de patch ainda deixava margem para confusao de autoridade:

```text
PatchPlanningService
    -> PatchCandidateBuilder
```

e tambem:

```text
ModelAssistedPatchPlannerService
    -> PatchCandidateBuilder
```

Ou seja, o builder de candidate ainda aparecia como ponto operacional, quando a autoridade correta deveria ser o diagnostico canonico.

## Arquitetura alvo consolidada

O fluxo conceitual consolidado passa a ser:

```text
Prompt
    -> Intent
    -> Contracts
    -> ExecutionPlan
    -> InferenceRuntime
    -> CanonicalDiagnosisArtifact
    -> DiagnosisRuntime
    -> PatchCandidateArtifact
    -> PatchPlanningService
    -> PatchCompiler interno
    -> CanonicalPatchPlan
    -> ExecutionRuntime
    -> Validation
    -> Completion
    -> SpeakerTruth
```

Cada autoridade responde uma pergunta:

- `InferenceRuntimeService`: como perguntar ao modelo?
- `CanonicalDiagnosisArtifact`: o que foi diagnosticado?
- `DiagnosisRuntimeService`: como transformar diagnostico em candidate?
- `PatchPlanningService`: qual PatchPlan canonico pode existir?
- `PatchCompiler`: como converter replacement em hunk/diff/rollback?
- `Validation`: o resultado cumpre contrato?
- `SpeakerTruth`: o que realmente aconteceu?

## Mudancas implementadas

### 1. InferenceRuntimeService

Criado:

```text
src/aipinho/services/models/inference_runtime_service.py
```

Nova autoridade canonica para chamadas reais a modelos.

Responsabilidades:

- receber `ModelRequest`;
- resolver provider/model via registries;
- chamar o adapter de engine apropriado;
- anexar telemetria canonica ao `ModelResponse`;
- registrar trace `inference_runtime`;
- impedir que providers nao governados sejam usados para inferencia real;
- preservar compatibilidade com os providers existentes.

Importante:

`LlamaCppProvider` nao foi duplicado nem substituido por outro provider. Ele foi mantido como adapter controlado abaixo da nova fronteira.

Fluxo atual:

```text
ModelInvocationService
    -> InferenceRuntimeService
    -> LlamaCppProvider
    -> ModelProcessRunner
    -> llama.cpp
```

### 2. Schema de telemetria de inferencia

Criado:

```text
src/aipinho/schemas/models/inference_runtime.py
```

Schemas principais:

- `InferenceRuntimeFingerprint`
- `InferenceRuntimeTelemetry`

Campos observados:

- executable absoluto;
- hash SHA-256 do executable;
- modelo utilizado;
- hash SHA-256 do modelo;
- tamanho do modelo;
- mtime do modelo;
- cwd;
- fingerprint de PATH;
- fingerprint de env com chaves sensiveis removidas;
- Vulkan SDK;
- provider type;
- execution mode;
- ctx-size;
- max output tokens;
- timeout;
- prompt chars;
- completion chars;
- tokens estimados;
- parser;
- validade JSON quando aplicavel;
- retry count;
- timeout;
- stdout raw chars;
- stdout sanitized chars;
- stderr chars.

### 3. Processo de modelo com cwd/env explicitos

Alterado:

```text
src/aipinho/services/models/model_process_runner.py
```

Antes:

```python
subprocess.Popen(..., env=None)
```

Agora:

```python
subprocess.Popen(..., cwd=cwd, env=env)
```

O `LlamaCppProvider` passa a resolver `cwd` por:

1. `llama_cpp.working_directory`, se configurado;
2. diretorio do executable configurado;
3. `None` somente se nao for possivel resolver.

Isso reduz risco de divergencia quando existem multiplas instalacoes de llama.cpp ou DLLs diferentes no ambiente.

### 4. Migração dos consumidores de inferencia

Migrados para `InferenceRuntimeService`:

- `ModelInvocationService`
- `ChatManualInferenceService`
- `llama_cpp_router` para invoke/preview
- `LlamaSmokeTestService`

Mantidos como utilitarios sem inferencia:

- `LlamaCppProvider.validate_environment`
- `LlamaCppProvider.estimate`

Motivo:

Validacao e estimativa nao iniciam modelo e nao produzem output de inferencia, portanto nao competem com `InferenceRuntimeService`.

### 5. Remocao de hardcode conceitual

Removido do gate de roles:

```text
provider_runtime_disabled_this_sprint
```

Substituido por reasons genericos:

```text
provider_runtime_not_allowed_by_policy
provider_runtime_not_text_inference
```

Isso elimina dependencia semantica de sprint especifico.

### 6. DiagnosisRuntimeService

Criado:

```text
src/aipinho/services/patching/diagnosis_runtime_service.py
```

Nova fronteira canonica para:

```text
CanonicalDiagnosisArtifact
    -> PatchCandidateArtifact
```

Responsabilidade:

- traduzir diagnostico tecnico em candidate de patch;
- nao criar patch;
- nao criar diff;
- nao criar rollback;
- nao escolher solucao;
- nao executar LLM;
- nao executar runtime.

`PatchCandidateBuilder` foi rebaixado para utilitario interno do `DiagnosisRuntimeService`.

### 7. Migracao dos consumers de PatchCandidate

Migrados para `DiagnosisRuntimeService`:

- `PatchPlanningService`
- `ModelAssistedPatchPlannerService`

Resultado:

Nao ha mais chamada operacional direta ao `PatchCandidateBuilder`.

Varredura final:

```text
PatchCandidateBuilder(
```

aparece apenas em:

```text
src/aipinho/services/patching/diagnosis_runtime_service.py
```

Isso confirma que o builder nao e mais autoridade operacional.

### 8. Runtime Doctor - dominio inference

Alterados:

```text
src/aipinho/schemas/runtime/runtime_doctor.py
src/aipinho/services/runtime/runtime_doctor_service.py
```

Regression Matrix agora inclui:

```text
inference
```

Novas regressões detectaveis:

```text
INFERENCE_RUNTIME_MISSING
INFERENCE_FINGERPRINT_INCOMPLETE
INFERENCE_PARSER_UNRECORDED
DIRECT_MODEL_PROVIDER_INVOCATION
```

O Runtime Doctor continua read-only.

Ele nao executa modelo, nao corrige arquivos e nao aplica patch.

## Fluxo final de inferencia

```text
Role / Chat / API / Smoke
    -> ModelInvocationService ou endpoint publico
    -> InferenceRuntimeService
    -> Provider Registry
    -> Model Registry
    -> LlamaCppProvider adapter
    -> LlamaCppCommandBuilder
    -> ModelProcessRunner
    -> llama-cli.exe
    -> stdout/stderr
    -> ModelOutputSanitizer
    -> ModelResponse
    -> InferenceRuntimeTelemetry
    -> ModelResponseEvaluator
    -> Runtime
```

## Fluxo final de diagnostico e patch planning

```text
Read-only analysis / evidence
    -> CanonicalDiagnosisArtifact
    -> DiagnosisRuntimeService
    -> PatchCandidateArtifact
    -> PatchPlanningService
    -> replacement vindo do Role LLM
    -> PatchCompiler interno
    -> hunks
    -> diff
    -> rollback
    -> CanonicalPatchPlan
```

O Role LLM continua sem autoridade para decidir:

- arquivo;
- simbolo;
- diff;
- hunk;
- rollback;
- approval;
- execucao.

Ele pode retornar apenas:

- replacement;
- patch snippet;
- rationale;
- confidence.

## Arquivos criados

```text
src/aipinho/schemas/models/inference_runtime.py
src/aipinho/services/models/inference_runtime_service.py
src/aipinho/services/patching/diagnosis_runtime_service.py
tests/unit/test_inference_runtime_service.py
tests/unit/test_diagnosis_runtime_service.py
reports/runtime_consolidation/inference_runtime_architecture.md
reports/runtime_consolidation/deterministic_inference_diagnosis_wave.md
reports/runtime_consolidation/diagnosis_runtime_boundary_update.md
reports/runtime_consolidation/inference_doctor_updates.md
```

## Arquivos alterados

```text
src/aipinho/api/routers/llama_cpp_router.py
src/aipinho/services/chat/chat_manual_inference_service.py
src/aipinho/services/models/llama_cpp_provider.py
src/aipinho/services/models/llama_smoke_test_service.py
src/aipinho/services/models/model_invocation_service.py
src/aipinho/services/models/model_process_runner.py
src/aipinho/services/patching/model_assisted_patch_planner_service.py
src/aipinho/services/patching/patch_planning_service.py
src/aipinho/services/roles/role_model_gate_service_v2.py
src/aipinho/services/runtime/runtime_doctor_service.py
src/aipinho/schemas/runtime/runtime_doctor.py
tests/unit/test_llama_cpp_provider.py
tests/unit/test_model_invocation_service.py
tests/unit/test_role_model_gate_service_v2.py
```

## Validacoes executadas

Comando:

```text
python -m pytest tests/unit/test_role_model_gate_service_v2.py tests/unit/test_inference_runtime_service.py tests/unit/test_diagnosis_runtime_service.py tests/unit/test_model_invocation_service.py tests/unit/test_llama_cpp_provider.py tests/unit/test_model_assisted_patch_planner_service.py tests/unit/test_role_inference_runtime_limits.py tests/unit/test_runtime_doctor_service.py tests/unit/test_chat_manual_inference_service.py tests/unit/test_llama_smoke_test_service.py tests/e2e/test_controlled_llama_smoke_gate.py tests/e2e/test_stub_default_llama_disabled_gate.py tests/contract/test_llama_cpp_contracts.py tests/contract/test_manual_inference_contracts.py tests/contract/test_chat_manual_inference_contracts.py -q
```

Resultado:

```text
67 passed in 47.74s
```

## Varreduras finais

### Chamadas diretas ao provider

Busca por:

```text
llama_cpp.invoke
self.llama_cpp
```

Resultado relevante:

```text
src/aipinho/services/models/inference_runtime_service.py
```

Interpretacao:

A chamada direta ao adapter de engine ficou concentrada somente dentro da fronteira canonica.

### Builder de PatchCandidate

Busca por:

```text
PatchCandidateBuilder(
```

Resultado relevante:

```text
src/aipinho/services/patching/diagnosis_runtime_service.py
```

Interpretacao:

O builder nao e mais chamado por services operacionais. Ele virou detalhe interno da fronteira de diagnostico.

### Hardcode antigo de sprint

Busca por:

```text
Sprint 28
provider_runtime_disabled_this_sprint
```

Resultado:

Nao ha ocorrencia operacional remanescente nos arquivos verificados.

## Pendencias conscientes

### 1. RAG / llama-server

Foi identificado anteriormente que existe runtime separado para `llama-server` em RAG/vector.

Ele nao foi migrado nesta wave porque:

- usa server-mode;
- tem semantica diferente de CLI text inference;
- pode envolver embeddings/reranking;
- exigiria uma wave propria para evitar misturar fronteiras.

Recomendacao:

Criar uma wave especifica para decidir se `llama-server` tambem deve ficar abaixo do `InferenceRuntimeService` ou de uma subfronteira como `InferenceServerRuntime`.

### 2. Hash de modelo grande

O `InferenceRuntimeService` calcula SHA-256 do modelo e usa cache por:

```text
path + size + mtime
```

Isso atende auditabilidade, mas pode ter custo na primeira chamada de cada modelo.

Recomendacao:

Persistir fingerprints de modelos em um `ModelFingerprintRepository` ou no Model Doctor, evitando recalculo apos restart.

### 3. Status/validate/estimate ainda instanciam provider

Alguns endpoints continuam instanciando `LlamaCppProvider` para:

- status;
- validate_environment;
- estimate.

Isso nao e concorrencia de inferencia porque nao gera output de modelo.

Recomendacao:

Em wave posterior, pode-se mover tambem esses utilitarios para uma interface de `InferenceRuntimeStatus`, apenas por limpeza conceitual.

## Avaliacao arquitetural

### Antes

```text
ModelInvocationService
    -> LlamaCppProvider

ChatManualInferenceService
    -> LlamaCppProvider preview

llama_cpp_router
    -> LlamaCppProvider invoke/preview

LlamaSmokeTestService
    -> LlamaCppProvider
```

### Depois

```text
Todos os consumers operacionais
    -> InferenceRuntimeService
    -> LlamaCppProvider adapter
```

### Antes

```text
PatchPlanningService
    -> PatchCandidateBuilder

ModelAssistedPatchPlannerService
    -> PatchCandidateBuilder
```

### Depois

```text
PatchPlanningService
    -> DiagnosisRuntimeService
    -> PatchCandidateBuilder interno

ModelAssistedPatchPlannerService
    -> DiagnosisRuntimeService
    -> PatchCandidateBuilder interno
```

## Conclusao

Esta wave reduziu incerteza em duas fronteiras criticas:

1. Modelo deixou de ser caixa preta operacional.
2. PatchCandidate deixou de ser produzido diretamente por planners.

O Runtime agora consegue auditar melhor:

- qual executable realmente foi usado;
- qual modelo realmente foi usado;
- com quais fingerprints;
- com qual cwd/env;
- qual parser foi aplicado;
- se houve timeout;
- se o output JSON era valido quando esperado;
- se PatchCandidate nasceu de diagnostico canonico.

Nao houve criacao de novo runtime paralelo, novo provider paralelo, nova governanca paralela, novo PatchPlan, novo SpeakerTruth ou bypass de validacao.

Resultado final:

```text
DETERMINISTIC_INFERENCE_DIAGNOSIS_READY
```
