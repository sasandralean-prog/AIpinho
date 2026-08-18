# Deterministic Inference & Diagnosis Wave

## Status

READY

## Fluxo consolidado

Prompt
-> Intent
-> Contracts
-> ExecutionPlan
-> Inference Runtime
-> CanonicalDiagnosisArtifact
-> Diagnosis Runtime
-> PatchCandidateArtifact
-> PatchPlanningService
-> PatchCompiler interno
-> CanonicalPatchPlan
-> Execution Runtime
-> Validation
-> Completion
-> Speaker Truth

## Arquivos alterados

- `src/aipinho/schemas/models/inference_runtime.py`
- `src/aipinho/schemas/runtime/runtime_doctor.py`
- `src/aipinho/services/models/inference_runtime_service.py`
- `src/aipinho/services/models/model_invocation_service.py`
- `src/aipinho/services/models/llama_cpp_provider.py`
- `src/aipinho/services/models/model_process_runner.py`
- `src/aipinho/services/models/llama_smoke_test_service.py`
- `src/aipinho/services/chat/chat_manual_inference_service.py`
- `src/aipinho/api/routers/llama_cpp_router.py`
- `src/aipinho/services/patching/diagnosis_runtime_service.py`
- `src/aipinho/services/patching/patch_planning_service.py`
- `src/aipinho/services/patching/model_assisted_patch_planner_service.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `tests/unit/test_inference_runtime_service.py`
- `tests/unit/test_diagnosis_runtime_service.py`
- `tests/unit/test_model_invocation_service.py`
- `tests/unit/test_llama_cpp_provider.py`

## Decisoes arquiteturais

`InferenceRuntimeService` virou a fronteira canonica para output de modelo.

`DiagnosisRuntimeService` virou a fronteira canonica para derivar `PatchCandidateArtifact` a partir de `CanonicalDiagnosisArtifact`.

`PatchPlanningService` continua autoridade unica de PatchPlan.

`LlamaCppProvider` continua adapter de engine, nao autoridade de Runtime.

## Sem atalhos

Nao foram adicionadas regras especificas para FireTest.

Nao houve relaxamento de Validation, Completion ou Speaker Truth.

Nao houve bypass de approval, patch planning, timeline ou execution.

## Pendencias conscientes

Existem utilitarios que ainda instanciam `LlamaCppProvider` para status/validacao/estimativa sem iniciar modelo. Isso nao compete com `InferenceRuntimeService` porque nao gera output de inferencia.

RAG/vector server continua fora do escopo desta wave; ele inicia `llama-server` para embeddings/rerankers e deve ser tratado em wave propria se a arquitetura exigir a mesma fronteira para server-mode.
