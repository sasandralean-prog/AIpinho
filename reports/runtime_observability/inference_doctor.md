# Inference Input Doctor

## Status

READY

## Servico

`InferenceInputDoctorService`

## Responsabilidade

Responder deterministicamente:

O modelo recebeu informacao suficiente para produzir replacement?

Ele nao chama modelo, nao cria patch, nao altera runtime e nao executa ferramentas.

## Reason codes canonicos

- `INFERENCE_INPUT_INCOMPLETE`
- `DIAGNOSIS_TOO_GENERIC`
- `PATCH_CANDIDATE_TOO_WEAK`
- `PROMPT_CONTEXT_TRUNCATED`
- `PROMPT_SYMBOL_MISSING`
- `PROMPT_EXPECTED_BEHAVIOR_MISSING`
- `PROMPT_OBSERVED_BEHAVIOR_MISSING`
- `PROMPT_CODE_SNIPPET_MISSING`
- `PATCH_MODEL_EMPTY_OUTPUT`

## Integracao com Runtime Doctor

`RuntimeDoctorService` agora le:

- `canonical_inference_input_artifact`;
- `canonical_inference_output_artifact`;
- `inference_input_doctor`;
- `quality_gate`.

Com isso, `PATCH_MODEL_EMPTY_OUTPUT` deixa de aparecer isolado e passa a vir acompanhado de causa estruturada.
