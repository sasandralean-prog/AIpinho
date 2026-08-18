# Runtime Doctor Updates

## Novas verificações

O Runtime Doctor agora detecta regressões no fluxo canônico de diagnóstico e patch:

- `PATCH_CANDIDATE_WITHOUT_DIAGNOSIS`
- `PATCH_PLAN_WITHOUT_PATCH_CANDIDATE`
- `DIAGNOSIS_OUTSIDE_CANONICAL_FLOW`
- `MULTIPLE_DIAGNOSIS_AUTHORITIES`

## Objetivo

Essas verificações impedem que o Runtime volte a aceitar diagnóstico técnico fora do artifact canônico ou PatchCandidate órfão.

## Natureza

O Runtime Doctor continua read-only.

Ele não altera Runtime, não corrige arquivos, não cria patch e não modifica contratos.

## Testes

Cobertura adicionada para detectar candidate sem diagnóstico.
