# Prompt Diff

## Status

READY

## Analyzer

`PromptDiffAnalyzer`

## Objetivo

Comparar `prompt_original` com `prompt_final` enviado ao modelo e registrar:

- chars originais;
- chars finais;
- itens removidos;
- itens truncados;
- artifacts omitidos;
- snippets omitidos;
- simbolos omitidos.

## Onde fica

O resultado e parte de:

`inference_input_doctor.prompt_diff`

## Reason code relacionado

`PROMPT_CONTEXT_TRUNCATED`
