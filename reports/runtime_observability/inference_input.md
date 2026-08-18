# Canonical Inference Input

## Status

READY

## Autoridade

`InferenceRuntimeService` produz `CanonicalInferenceInputArtifact` para toda chamada de inferencia real ou bloqueada na fronteira canonica.

## Conteudo registrado

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
- fingerprint.

## Onde fica

O artifact e anexado ao `ModelResponse.metadata` em:

`canonical_inference_input_artifact`

Nao cria workspace write e nao cria store paralelo.
