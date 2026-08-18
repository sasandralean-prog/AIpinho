# Duplicate Authorities Removed

## Duplicações removidas

O papel de "diagnóstico técnico" foi removido de `PatchCandidateArtifact`.

O fluxo assistido por modelo deixou de criar candidate como primeira autoridade de diagnóstico.

## Compatibilidade residual controlada

Entradas antigas com candidates diretos são convertidas para diagnóstico canônico antes de qualquer compilação.

Isso evita dois fluxos vivos:

- candidate legado direto
- candidate derivado de diagnóstico canônico

Somente o segundo segue para compilação.

## Sem remoção física ampla

Não houve limpeza global ou exclusão ampla de arquivos nesta entrega. O escopo foi limitado às duplicações diretamente relacionadas a diagnóstico, PatchCandidate e PatchPlanning.
