# AIpinho - LLM Runtime Observability Wave

## Veredito

LLM_RUNTIME_OBSERVABILITY_READY

## Objetivo da wave

Esta wave teve como objetivo tornar completamente auditavel a fronteira de inferencia da AIpinho e a cadeia:

```text
DiagnosisRuntime
-> PatchCandidate
-> PatchPlanning
-> InferenceRuntime
-> Model Output
```

O foco nao foi fazer FireTest passar, nem alterar o PatchCompiler, nem relaxar validacoes.

A pergunta central foi:

```text
Por que o modelo retornou replacement vazio ou PATCH_MODEL_EMPTY_OUTPUT?
```

Antes desta wave, o Runtime bloqueava corretamente `PATCH_MODEL_EMPTY_OUTPUT`, mas ainda havia pouca explicabilidade sobre a causa:

- o input entregue ao modelo era pouco visivel;
- o output bruto/sanitizado nao tinha artifact canonico;
- `edits: []` era detectado, mas sem diagnostico estruturado suficiente;
- truncamentos de contexto nao carregavam item-level explanation;
- qualidade de diagnostico e PatchCandidate nao era medida por score;
- Runtime Doctor nao tinha dominios especificos para prompt, completeness e context budget.

## Premissas preservadas

Nao foram alterados:

- ExecutionPlan;
- Approval Runtime;
- Validation;
- Completion;
- Speaker Truth;
- PatchCompiler;
- Governed Runtime;
- InferenceRuntime como autoridade;
- DiagnosisRuntime como autoridade;
- PatchPlanningService como autoridade de PatchPlan;
- RuntimeDoctorService como autoridade de diagnostico.

Nao foi criado:

- runtime paralelo;
- provider paralelo;
- planner paralelo;
- patch plan paralelo;
- validation paralela;
- speaker truth paralelo;
- bypass;
- regra especifica para FireTest.

## Arquitetura antes da wave

Fluxo canonico ja existente:

```text
Prompt
-> InferenceRuntime
-> CanonicalDiagnosisArtifact
-> DiagnosisRuntime
-> PatchCandidateArtifact
-> PatchPlanningService
-> PatchCompiler
-> CanonicalPatchPlan
```

Ponto fraco:

```text
PatchPlanning
-> Role LLM
-> output
```

Ainda nao havia uma representacao canonica completa de:

- o que exatamente foi entregue ao modelo;
- quais evidencias entraram;
- quais ficaram de fora;
- qual candidate foi usado;
- qual simbolo e arquivo foram apresentados;
- qual snippet de codigo foi enviado;
- qual schema de output foi exigido;
- se o output continha replacement real;
- se a resposta era JSON valido;
- se `edits: []` representava vazio real;
- se o input estava completo o suficiente para esperar replacement.

## Arquitetura depois da wave

Fluxo observavel consolidado:

```text
Role / PatchPlanning
-> InferenceRuntimeService
-> CanonicalInferenceInputArtifact
-> Model Provider Adapter
-> CanonicalInferenceOutputArtifact
-> InferenceInputDoctorService
-> RuntimeDoctorService
```

Fluxo completo de coding:

```text
CanonicalDiagnosisArtifact
-> DiagnosisQualityAnalyzer
-> DiagnosisRuntimeService
-> PatchCandidateArtifact
-> PatchCandidateQualityAnalyzer
-> PatchPlanningService
-> RoleInferenceService
-> InferenceRuntimeService
-> CanonicalInferenceInputArtifact
-> CanonicalInferenceOutputArtifact
-> InferenceInputDoctorService
-> PatchPlanning result
-> RuntimeDoctorService
```

## Novos schemas canonicos

### CanonicalInferenceInputArtifact

Arquivo:

```text
src/aipinho/schemas/models/inference_observability.py
```

Responsabilidade:

Representar exatamente o input entregue ao modelo.

Nao representa resposta.

Nao representa patch.

Nao representa inferencia completa.

Nao representa sucesso.

Campos principais:

- role;
- operation_type;
- semantic_goal;
- prompt_original;
- prompt_final;
- system_prompt;
- output_schema;
- artifacts_used;
- evidence_used;
- diagnosis_ids;
- patch_candidate_id;
- symbol_targets;
- file_targets;
- code_snippets;
- estimated_tokens;
- prompt_chars;
- truncated_items;
- context_budget;
- provider;
- model;
- fingerprint;
- metadata estruturada.

Onde fica:

```text
ModelResponse.metadata["canonical_inference_input_artifact"]
```

### CanonicalInferenceOutputArtifact

Arquivo:

```text
src/aipinho/schemas/models/inference_observability.py
```

Responsabilidade:

Representar exatamente o output retornado pelo modelo, com parsing e diagnosticos.

Campos principais:

- raw_output;
- sanitized_output;
- parsed_output;
- parser;
- completion_chars;
- json_valid;
- retry_count;
- finish_reason;
- confidence;
- replacement_detected;
- replacement_count;
- empty_output;
- diagnostics.

Onde fica:

```text
ModelResponse.metadata["canonical_inference_output_artifact"]
```

Exemplo de diagnostico:

```json
{"edits": []}
```

gera:

```text
empty_output = true
replacement_detected = false
diagnostics = ["legacy_edits_empty"]
reason_code = PATCH_MODEL_EMPTY_OUTPUT
```

## Novos analyzers

### CompletenessAnalyzer

Arquivo:

```text
src/aipinho/services/models/inference_input_doctor_service.py
```

Pergunta respondida:

```text
O input entregue ao modelo continha os elementos minimos para esperar replacement?
```

Elementos avaliados:

- observed_behavior;
- expected_behavior;
- symbol_targets;
- file_targets;
- code_snippets;
- output_schema;
- evidence_used;
- diagnosis_ids;
- patch_candidate_id.

Saida:

- score 0-100;
- confidence: baixa, media ou alta;
- campos presentes;
- campos ausentes;
- reason_codes.

Reason codes principais:

- INFERENCE_INPUT_INCOMPLETE
- PROMPT_OBSERVED_BEHAVIOR_MISSING
- PROMPT_EXPECTED_BEHAVIOR_MISSING
- PROMPT_SYMBOL_MISSING
- PROMPT_TARGET_FILE_MISSING
- PROMPT_CODE_SNIPPET_MISSING
- PROMPT_OUTPUT_SCHEMA_MISSING
- PROMPT_EVIDENCE_MISSING
- PROMPT_DIAGNOSIS_MISSING
- PROMPT_PATCH_CANDIDATE_MISSING

### PromptDiffAnalyzer

Arquivo:

```text
src/aipinho/services/models/inference_input_doctor_service.py
```

Pergunta respondida:

```text
O que mudou entre o prompt original e o prompt final entregue ao modelo?
```

Registra:

- chars originais;
- chars finais;
- itens removidos;
- itens truncados;
- artifacts omitidos;
- snippets omitidos;
- simbolos omitidos.

Reason code principal:

```text
PROMPT_CONTEXT_TRUNCATED
```

### ContextBudgetAnalyzer

Arquivo:

```text
src/aipinho/services/models/inference_input_doctor_service.py
```

Pergunta respondida:

```text
Quanto do contexto realmente coube e o que ficou de fora?
```

Registra:

- limite do role;
- limite estimado do provider;
- tamanho real em chars;
- tokens estimados;
- chars descartados;
- itens descartados;
- itens truncados.

### InferenceInputDoctorService

Arquivo:

```text
src/aipinho/services/models/inference_input_doctor_service.py
```

Responsabilidade:

Servico read-only para diagnosticar a qualidade do input e relacionar isso com o output.

Nao chama modelo.

Nao gera patch.

Nao altera Runtime.

Nao modifica Validation.

Nao decide sucesso.

Onde fica:

```text
ModelResponse.metadata["inference_input_doctor"]
```

## Diagnostico e PatchCandidate quality

### DiagnosisQualityAnalyzer

Arquivo:

```text
src/aipinho/services/patching/diagnosis_quality_analyzer.py
```

Avalia `CanonicalDiagnosisArtifact`.

Campos avaliados:

- simbolo;
- arquivo alvo;
- comportamento observado;
- comportamento esperado;
- hipotese;
- confidence;
- evidencia.

Reason code principal:

```text
DIAGNOSIS_TOO_GENERIC
```

### PatchCandidateQualityAnalyzer

Arquivo:

```text
src/aipinho/services/patching/patch_candidate_quality_analyzer.py
```

Avalia `PatchCandidateArtifact`.

Campos avaliados:

- target_file;
- target_symbol;
- observed_behavior;
- expected_behavior;
- evidence_refs;
- confidence;
- diagnosis_id;
- current_content_excerpt.

Reason code principal:

```text
PATCH_CANDIDATE_TOO_WEAK
```

## Integracao com autoridades existentes

### InferenceRuntimeService

Arquivo alterado:

```text
src/aipinho/services/models/inference_runtime_service.py
```

Agora produz:

- `canonical_inference_input_artifact`;
- `canonical_inference_output_artifact`;
- `inference_input_doctor`;
- telemetria de inferencia ja existente.

Ele continua sendo a unica fronteira operacional de inferencia.

### RoleInferenceService

Arquivo alterado:

```text
src/aipinho/services/roles/role_inference_service.py
```

Agora repassa metadados estruturados para o InferenceRuntime:

- `semantic_goal`;
- `prompt_original`;
- `role_context`;
- `patch_candidate`;
- `context_budget`;
- `operation_type`.

Tambem preserva os artifacts no `RoleInferenceResult.metadata`, permitindo diagnostico posterior sem parsear prompt bruto.

### DiagnosisRuntimeService

Arquivo alterado:

```text
src/aipinho/services/patching/diagnosis_runtime_service.py
```

Agora anexa:

- `diagnosis_quality`;
- `patch_candidate_quality`;

em:

```text
PatchCandidateArtifact.technical_context
```

### PatchPlanningService

Arquivo alterado:

```text
src/aipinho/services/patching/patch_planning_service.py
```

Agora consolida quality reports em:

```text
PatchPlan.quality_gate
```

Esse campo e observacional.

Nao altera status.

Nao relaxa bloqueios.

Nao substitui Validation.

### ModelAssistedPatchPlannerService

Arquivo alterado:

```text
src/aipinho/services/patching/model_assisted_patch_planner_service.py
```

Agora, quando o modelo retorna output vazio ou replacement invalido, o resultado bloqueado carrega:

- inference_input_doctor;
- canonical_inference_input_artifact;
- canonical_inference_output_artifact.

Com isso, um `PATCH_MODEL_EMPTY_OUTPUT` nao fica mais sem causa estruturada.

### RuntimeDoctorService

Arquivos alterados:

```text
src/aipinho/schemas/runtime/runtime_doctor.py
src/aipinho/services/runtime/runtime_doctor_service.py
```

Novos dominios na Regression Matrix:

- inference;
- diagnosis;
- patch_candidate;
- prompt;
- completeness;
- context_budget.

Novos reason codes tratados:

- INFERENCE_INPUT_INCOMPLETE
- DIAGNOSIS_TOO_GENERIC
- PATCH_CANDIDATE_TOO_WEAK
- PROMPT_CONTEXT_TRUNCATED
- PROMPT_SYMBOL_MISSING
- PROMPT_EXPECTED_BEHAVIOR_MISSING
- PROMPT_OBSERVED_BEHAVIOR_MISSING
- PROMPT_CODE_SNIPPET_MISSING
- PATCH_MODEL_EMPTY_OUTPUT
- INFERENCE_EMPTY_OUTPUT

O Runtime Doctor continua read-only.

## Como PATCH_MODEL_EMPTY_OUTPUT fica explicavel agora

Antes:

```text
blocked_reasons = ["PATCH_MODEL_EMPTY_OUTPUT"]
```

Depois:

```text
canonical_inference_input_artifact:
    prompt_final
    output_schema
    diagnosis_ids
    patch_candidate_id
    file_targets
    symbol_targets
    code_snippets
    evidence_used
    context_budget

canonical_inference_output_artifact:
    raw_output
    sanitized_output
    parsed_output
    json_valid
    replacement_detected
    replacement_count
    empty_output
    diagnostics

inference_input_doctor:
    completeness score
    missing fields
    prompt diff
    context budget
    reason codes
```

Exemplo:

```text
PATCH_MODEL_EMPTY_OUTPUT
causado por:
    legacy_edits_empty
    PROMPT_CODE_SNIPPET_MISSING
    PROMPT_SYMBOL_MISSING
    INFERENCE_INPUT_INCOMPLETE
```

ou:

```text
PATCH_MODEL_EMPTY_OUTPUT
causado por:
    replacement_empty
    input completo
    json valido
    candidate forte
```

Nesse segundo caso, a falha tenderia a ser atribuida ao comportamento do modelo ou estrategia de prompt, nao a falta de evidencia.

## Arquivos criados

```text
src/aipinho/schemas/models/inference_observability.py
src/aipinho/schemas/patching/patch_observability.py
src/aipinho/services/models/inference_input_doctor_service.py
src/aipinho/services/patching/diagnosis_quality_analyzer.py
src/aipinho/services/patching/patch_candidate_quality_analyzer.py
reports/runtime_observability/inference_input.md
reports/runtime_observability/inference_output.md
reports/runtime_observability/diagnosis_quality.md
reports/runtime_observability/patch_candidate_quality.md
reports/runtime_observability/prompt_diff.md
reports/runtime_observability/context_budget.md
reports/runtime_observability/inference_doctor.md
```

## Arquivos alterados

```text
src/aipinho/services/models/inference_runtime_service.py
src/aipinho/services/roles/role_inference_service.py
src/aipinho/services/patching/diagnosis_runtime_service.py
src/aipinho/services/patching/patch_planning_service.py
src/aipinho/services/patching/model_assisted_patch_planner_service.py
src/aipinho/services/runtime/runtime_doctor_service.py
src/aipinho/schemas/runtime/runtime_doctor.py
tests/unit/test_inference_runtime_service.py
tests/unit/test_diagnosis_runtime_service.py
tests/unit/test_runtime_doctor_service.py
```

## Testes executados

Comando:

```text
python -m pytest tests/unit/test_role_model_gate_service_v2.py tests/unit/test_inference_runtime_service.py tests/unit/test_diagnosis_runtime_service.py tests/unit/test_model_invocation_service.py tests/unit/test_llama_cpp_provider.py tests/unit/test_model_assisted_patch_planner_service.py tests/unit/test_role_inference_runtime_limits.py tests/unit/test_runtime_doctor_service.py tests/unit/test_chat_manual_inference_service.py tests/unit/test_llama_smoke_test_service.py tests/e2e/test_controlled_llama_smoke_gate.py tests/e2e/test_stub_default_llama_disabled_gate.py tests/contract/test_llama_cpp_contracts.py tests/contract/test_manual_inference_contracts.py tests/contract/test_chat_manual_inference_contracts.py -q
```

Resultado:

```text
69 passed in 70.43s
```

## Varredura final

Foi feita varredura por:

- `FireTest`;
- `firetest`;
- `Fase 4`;
- `Fase 5`;
- condicionais especificos de prompt;
- chamadas diretas a `llama_cpp.invoke`;
- uso operacional direto de `PatchCandidateBuilder`.

Resultado relevante:

- as ocorrencias de FireTest encontradas pertencem a componentes antigos e oficiais de Runtime Doctor/API, nao a esta wave;
- chamadas ao adapter llama.cpp permanecem concentradas dentro de `InferenceRuntimeService`;
- `PatchCandidateBuilder` permanece apenas dentro de `DiagnosisRuntimeService`;
- nao foi adicionada logica especifica para FireTest;
- nao foi criado bypass;
- nao foi relaxada validation.

## Limites conscientes

### 1. Artifacts como metadata canonica

Os novos artifacts de inferencia foram anexados ao `ModelResponse.metadata`.

Eles nao foram persistidos automaticamente no Artifact Runtime nesta wave.

Motivo:

O objetivo era observabilidade canonica sem mexer em Artifact Runtime, ExecutionPlan, Completion ou Speaker Truth.

Possivel evolucao futura:

Persistir esses artifacts via Artifact Runtime quando existir TaskRun governado disponivel, mantendo read-only e sem workspace write.

### 2. Prompt diff estrutural, nao visual

O `PromptDiffAnalyzer` registra fragments removidos/truncados e contagens.

Nao foi implementado diff visual linha-a-linha completo.

Motivo:

O objetivo era diagnostico deterministico inicial sem criar novo subsistema de diff.

### 3. Scores deterministico simples

Os scores de completeness, diagnosis e candidate sao baseados em presenca de campos canonicos.

Nao usam LLM.

Nao usam heuristica criativa.

Nao tentam julgar semanticamente se a solucao tecnica e correta.

Isso e intencional: observabilidade deve ser previsivel.

## Impacto arquitetural

Esta wave melhora a capacidade da AIpinho de responder:

```text
O modelo falhou porque:
1. nao recebeu simbolo?
2. nao recebeu arquivo?
3. nao recebeu snippet?
4. nao recebeu comportamento esperado?
5. nao recebeu comportamento observado?
6. nao recebeu evidencia?
7. recebeu tudo, mas retornou JSON vazio?
8. recebeu prompt truncado?
9. o candidate era fraco?
10. o diagnostico era generico?
```

Antes, muitas dessas respostas dependiam de leitura manual de RAW.

Depois, elas ficam disponiveis por:

- metadata do ModelResponse;
- metadata do RoleInferenceResult;
- metadata do ModelPatchPlanningResult;
- PatchPlan.quality_gate;
- RuntimeDoctor Regression Matrix.

## Conclusao

A fronteira LLM ficou substancialmente mais auditavel.

O Runtime agora consegue explicar `PATCH_MODEL_EMPTY_OUTPUT` sem:

- inventar patch;
- reexecutar modelo cegamente;
- reduzir criterios de validacao;
- criar regra especifica para FireTest;
- criar provider paralelo;
- bypassar PatchPlanningService;
- bypassar RuntimeDoctorService.

O bloqueio continua correto quando nao ha replacement concreto.

A diferenca e que agora o bloqueio vem acompanhado de causa estruturada.

## Veredito final

```text
LLM_RUNTIME_OBSERVABILITY_READY
```
