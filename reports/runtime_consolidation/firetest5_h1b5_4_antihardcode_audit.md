# H1B5.4 Anti-Hardcode Audit

## Escopo

Arquivos auditados:

- schemas H1B5 de relationship/profile/perception
- services de relationship detector, contract perception, semantic profile, validation policy, renderer, summary e CVL
- testes unitários H1B5.0-H1B5.4

Termos buscados:

```text
FireTest
Pinhoabacaxi
music_inventory
C:\Dev
.lrc
.jpg
.mp4
.m4a
lyrics_for
artwork_for
album_art_for
sidecar_of
```

## Resultado

Veredito:

```text
PASS
```

## Achados Permitidos

Foram encontrados usos de `FireTestProfile`, `FireTestSuite` e `FireTestLaboratoryService` no CVL:

- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `tests/unit/test_cognitive_validation_laboratory_service.py`
- `tests/unit/test_relationship_validation_policy.py`

Esses achados são permitidos porque pertencem ao vocabulário genérico do CVL/Fase 0 e não criam regra específica de FireTest 5.

## Achados Bloqueantes

Nenhum.

Não foram encontrados nos arquivos novos/alterados da pilha H1B5:

- regra condicional nova baseada em FireTest;
- regra baseada em `Pinhoabacaxi`;
- regra baseada em `music_inventory`;
- path local usado como comportamento;
- extensão específica usada para validar relação;
- relação final proibida usada como Truth;
- artifact específico usado como sucesso.

## Observações

Alguns testes criam entidades sintéticas com nomes genéricos como `song.media` e `song.text`. Esses nomes não são usados como regra de autoridade; servem apenas para exercitar sinais genéricos de stem/diretório, e os testes afirmam que esses sinais não viram Truth.
