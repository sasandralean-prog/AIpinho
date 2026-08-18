# Hardcode Removal

## Escopo

A implementação não adicionou regras específicas para FireTest, paths absolutos, nomes de arquivos obrigatórios, intents específicos, fases ou prompts.

## Configuração preservada

Limites de contexto, budget, seleção de role e política do planner assistido continuam vindo da configuração existente.

## Decisões determinísticas

O `PatchCandidateBuilder` usa apenas contratos estruturados:

- diagnóstico canônico
- localização técnica
- evidências
- hints de reparo
- constraints

Nenhuma decisão foi baseada em string específica de teste.
