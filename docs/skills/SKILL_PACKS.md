# Skill Packs

Skill Packs sao pacotes internos de capacidades governadas. Eles agrupam skills registradas, declaram risco, agentes suportados, politicas, validacoes e artifacts esperados.

Um pack nao instala codigo remoto, nao cria marketplace e nao executa fora do Tool Gateway.

Fluxo:

1. Manifest em `config/skills/packs/<pack>/pack.yaml`.
2. `SkillPackRegistry` carrega e filtra.
3. `SkillPackValidator` valida manifests e skills incluidas.
4. `SkillPackExecutionService` coordena execucoes via `SkillExecutionService`.
5. Artifacts carregam metadata de `skill_pack_id` quando produzidos por skill dentro de pack.
