# Canonical Inference Output

## Status

READY

## Autoridade

`InferenceRuntimeService` produz `CanonicalInferenceOutputArtifact` imediatamente apos receber a resposta do adapter de engine.

## Conteudo registrado

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

## Diagnostico de replacement vazio

Casos como:

```json
{"edits": []}
```

geram:

```text
legacy_edits_empty
PATCH_MODEL_EMPTY_OUTPUT
```

sem relaxar validacao e sem criar patch ficticio.
