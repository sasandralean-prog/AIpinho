# State Effect Resolution

## Principio

Operacoes devem ser explicadas pelo efeito pretendido sobre o estado canonico, nao por palavras isoladas.

## Representacao

`StateEffect` foi introduzido como IR diagnostica com:

- target
- effect
- confidence
- evidence_refs
- reason_codes

Targets iniciais:

- `workspace`
- `filesystem`
- `runtime`
- `knowledge`

Efeitos suportados:

- `none`
- `immutable`
- `read_only`
- `temporary`
- `mutable`
- `destructive`
- `prohibited`

## Diagnosticos

O Doctor registra:

- `STATE_EFFECT_UNRESOLVED` quando nenhum efeito semantico suficiente existe.
- `STATE_EFFECT_CONTRACT_MISMATCH` quando a intent selecionada conflita com o efeito observado.
- `READONLY_CONTRACT_PROMOTED_TO_MUTATION` quando um contrato readonly observado aparece ligado a contrato mutavel.

## Resultado

O Runtime segue decidindo como antes; agora a divergencia pode ser auditada de forma deterministica.
