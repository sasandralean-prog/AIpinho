# Inference Doctor Updates

## Status

READY

## Runtime Doctor

O Runtime Doctor passou a ter dominio `inference` na Regression Matrix.

Novas verificacoes:

- `INFERENCE_RUNTIME_MISSING`
- `INFERENCE_FINGERPRINT_INCOMPLETE`
- `INFERENCE_PARSER_UNRECORDED`
- `DIRECT_MODEL_PROVIDER_INVOCATION`

## Contrato observado

Quando existir inferencia real, o resumo runtime deve carregar telemetria de `InferenceRuntimeService` com:

- executable absoluto;
- hash do executable;
- modelo utilizado;
- hash e tamanho do modelo;
- cwd;
- fingerprint de PATH;
- fingerprint de env com chaves sensiveis removidas;
- parser;
- ctx-size;
- timeout;
- stdout bruto em contagem de chars;
- stdout sanitizado em contagem de chars;
- stderr em contagem de chars.

## Natureza

O Doctor continua read-only.

Ele nao corrige, nao aplica patch, nao executa modelo e nao muda contratos.
