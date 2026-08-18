# Inference Runtime Architecture

## Status

READY

## Autoridade canonica

`InferenceRuntimeService` e a fronteira oficial para chamadas reais a modelos.

Ele responde uma pergunta: como perguntar ao modelo de forma governada, rastreavel e auditavel?

Providers como `LlamaCppProvider` continuam existindo apenas como adapters de engine abaixo dessa fronteira. Chamadas operacionais de preview/invoke foram migradas para passar por `InferenceRuntimeService`.

## Responsabilidades consolidadas

- registrar provider/model usados;
- anexar fingerprint de executable e modelo;
- registrar cwd usado pela engine;
- registrar fingerprint de PATH/env sem expor segredos;
- registrar ctx-size, max tokens e timeout;
- registrar parser usado;
- registrar validade JSON quando o output contract pede JSON;
- preservar trace canonico em `ModelResponse`.

## Mudancas principais

- `ModelInvocationService` chama `InferenceRuntimeService` para providers llama.cpp.
- `ChatManualInferenceService` usa `InferenceRuntimeService.invoke_preview`.
- `llama_cpp_router` usa `InferenceRuntimeService` para preview/invoke.
- `LlamaSmokeTestService` usa `InferenceRuntimeService` para preview/smoke.
- `ModelProcessRunner` aceita `cwd` e `env` explicitos.
- `LlamaCppProvider` define `cwd` por configuracao ou diretorio do executable.

## Hardcodes removidos

- Removida mensagem/decisao de role model presa a "Sprint 28".
- A decisao agora usa o tipo do provider registrado: `llama_cpp_text`.
- O processo deixou de depender implicitamente do cwd herdado do processo pai.

## Duplicacoes evitadas

Nao foi criado provider paralelo.

Nao foi criado engine novo.

Nao foi criado fluxo alternativo para llama.cpp.

O provider existente foi mantido como adapter controlado e ficou abaixo da fronteira canonica.

## Compatibilidade

Endpoints publicos permanecem com os mesmos contratos.

`validate_environment` e `estimate` continuam usando utilitarios do provider porque nao iniciam inferencia. Invocacao e preview passam pelo Runtime canonico.

## Testes

Executado:

`python -m pytest tests/unit/test_inference_runtime_service.py tests/unit/test_diagnosis_runtime_service.py tests/unit/test_model_invocation_service.py tests/unit/test_llama_cpp_provider.py tests/unit/test_model_assisted_patch_planner_service.py tests/unit/test_role_inference_runtime_limits.py tests/unit/test_runtime_doctor_service.py -q`

Resultado: 27 passed.
