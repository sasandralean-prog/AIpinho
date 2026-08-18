# FireTest 5 H1B.2 - Workspace Role Boundaries & Corpus-Aware Entity Selection

## Objetivo

Esta wave corrigiu a fronteira semantica entre raizes do workspace e selecao de entidades para artifacts tabulares, sem criar observer especifico de audio/midia/CSV/FireTest e sem relaxar Validation, Completion ou Speaker Truth.

O problema exposto pelo rerun era que o Runtime ja sabia produzir `ObservedEntity`, `ObservationGoal`, `CapabilityMatch`, `EvidenceSet` e `SemanticCoverageReport`, mas ainda deixava arquivos do app/build/cache competirem como entidades do inventario de corpus porque todos possuiriam atributos genericos como `name` e `size_bytes`.

## Principio aplicado

A selecao de entidades nao deve ser decidida apenas por overlap de atributos. Ela tambem deve considerar o papel da raiz de origem e o contrato do artifact.

Fluxo consolidado:

```text
WorkspaceContext
  -> WorkspaceRootDescriptor / CorpusDescriptor
  -> ObservedEntity(source_root_role, entity_role)
  -> ArtifactEntitySelectionContract
  -> CandidateEntity(policy_rejection_reasons)
  -> selected entities only
  -> Contract-aware renderer
  -> SemanticCoverageReport
  -> Validation / Completion / Speaker Truth
```

## O que foi implementado

### 1. Identidade de raiz/escopo

Criados/enriquecidos schemas em `src/aipinho/schemas/artifacts/observed_entity.py`:

- `WorkspaceRootDescriptor`
- `CorpusDescriptor`
- `WorkspaceRootRole`
- `ObservedEntity.source_root`
- `ObservedEntity.source_root_role`
- `ObservedEntity.relative_path`
- `ObservedEntity.entity_role`
- `ObservedEntity.entity_domain_hypotheses`
- `ObservedEntity.selection_eligibility`
- `ObservedEntity.exclusion_reasons`
- `EntityEvidenceGraph.root_descriptors`
- `EntityEvidenceGraph.corpus_descriptors`
- `EntityEvidenceGraph.roots_scanned_by_role`
- `EntityEvidenceGraph.entities_by_root_role`

Cada arquivo observado agora sabe se veio de `project_root`, `library_root`, `external_root` etc.

### 2. Politica configuravel de root roles

Atualizado `config/artifacts/observed_entity_policy.yaml` com uma politica generica:

- `project_root_role`
- `library_root_role`
- `external_root_role`
- segmentos genericos de build/cache/source/generated
- root roles preferidos para corpus
- entity roles excluidos para corpus inventory

Isso evita hardcode de caminho local, nome de projeto, FireTest ou extensao.

### 3. Entity roles genericos

O compilador de entidades agora classifica cada arquivo em papeis como:

- `corpus_file`
- `project_file`
- `project_source_file`
- `build_output_file`
- `cache_file`
- `generated_file`
- `external_file`

A classificacao usa apenas o papel da raiz e segmentos configurados. Nao usa extensao de audio, nome de musica, FireTest, path local ou dominio de midia.

### 4. Selecao por contrato

Enriquecido `ContractObservationPlan` em `src/aipinho/schemas/artifacts/contract_perception.py` com:

- `expected_entity_role`
- `expected_entity_domain`
- `allowed_root_roles`
- `excluded_entity_roles`
- `entity_selection_contract`

`CandidateEntity` agora carrega:

- `source_root_role`
- `entity_role`
- `entity_domain_hypotheses`
- `selection_eligibility`
- `exclusion_reasons`
- `policy_rejection_reasons`

Candidatos inelegiveis continuam auditaveis, mas recebem `status = rejected` e nao sao selecionados/renderizados.

### 5. Corpus-aware selection sem dominio especifico

Quando um artifact `tabular_collection` possui `library_roots` no `workspace_context`, a selecao default passa a tratar esse artifact como inventario de corpus:

```text
allowed_root_roles = [library_root, corpus_root]
expected_entity_role = corpus_file
expected_entity_domain = corpus_member
```

Isso nao e uma regra para musica. E uma regra generica: se o contexto declarou biblioteca/corpus e o artifact e uma colecao tabular de entidades, o corpus e a fonte correta, salvo contrato explicito em contrario.

### 6. Renderer corrigido

O renderer de tabular collection agora consome somente entidades selecionadas pelo contrato. Arquivos rejeitados por papel de raiz continuam no diagnostico, mas nao entram no CSV.

Se nao houver entidade elegivel, o artifact nao e preenchido com arquivos do app. Ele recebe gap estruturado como:

- `ENTITY_SELECTION_EMPTY_FOR_CONTRACT`
- `WORKSPACE_ROLE_MISMATCH`
- `ENTITY_INELIGIBLE_FOR_CONTRACT`

### 7. Attribute Identity reforcada

A H1B.1 ja tinha separado `raw_label`, `display_label` e `canonical_key`. A H1B.2 adicionou labels configuraveis para recuperar display humano quando o raw label vier degradado.

Exemplo:

```text
raw_label = extens?o
display_label = extens?o
canonical_key = extension
```

Matching, coverage e evidence continuam usando `canonical_key`.

### 8. Summary/API enriquecido

O `UniversalTaskSessionService.summary()` agora expoe em `observational_cognition`:

- `roots_scanned_by_role`
- `entities_by_root_role`
- `entities_selected_by_artifact`
- `entities_rejected_by_policy`
- `workspace_role_mismatches`

A UI/API nao precisa abrir o CSV para perceber que houve mistura ou rejeicao por papel de raiz.

## Arquivos alterados

- `config/artifacts/observed_entity_policy.yaml`
- `src/aipinho/schemas/artifacts/observed_entity.py`
- `src/aipinho/schemas/artifacts/contract_perception.py`
- `src/aipinho/services/artifacts/observed_entity_compilation_service.py`
- `src/aipinho/services/artifacts/contract_driven_perception_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/runtime/universal_task_session_service.py`
- `tests/unit/test_contract_driven_perception_service.py`
- `tests/unit/test_workspace_runtime_context.py`

Tambem permanecem as alteracoes da H1B.1 em artifact profile/session/evidence.

## Antes / depois

### Antes

```text
workspace app + library_roots
  -> lista unica de roots
  -> todo arquivo vira file
  -> qualquer file com nome/tamanho ganha overlap
  -> project/build/cache entra no music_inventory.csv
```

### Depois

```text
workspace app + library_roots
  -> root descriptors por papel
  -> file carrega source_root_role/entity_role
  -> contrato tabular com library_roots seleciona corpus_file
  -> project/build/cache ficam rejected por policy
  -> CSV renderiza apenas entidades elegiveis
```

## Testes adicionados/atualizados

Coberturas principais:

1. `WorkspaceContextService` preserva `library_roots` separado de `project_root`.
2. `ObservedEntityCompilationService` produz root roles distintos.
3. Corpus inventory seleciona apenas entidades de `library_root` quando existe library root.
4. Arquivos de `project_root`, `src`, `build` e `.gradle` sao rejeitados para corpus inventory.
5. Renderer nao coloca arquivos do app/build/cache no CSV de corpus.
6. Renderer bloqueia/explica quando nenhum corpus elegivel foi observado.
7. `extens?o` gera `canonical_key = extension` e `display_label = extens?o`.
8. Metadata de midia continua bloqueada sem observer real.

## Validacao executada

Suites focadas:

```bash
python -m pytest tests/unit/test_contract_driven_perception_service.py tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_universal_task_session_service.py tests/unit/test_workspace_runtime_context.py -q
```

Resultado:

```text
33 passed in 18.20s
```

Compilacao dos arquivos alterados:

```bash
python -m py_compile src/aipinho/schemas/artifacts/observed_entity.py src/aipinho/schemas/artifacts/contract_perception.py src/aipinho/services/artifacts/observed_entity_compilation_service.py src/aipinho/services/artifacts/contract_driven_perception_service.py src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py src/aipinho/services/runtime/universal_task_session_service.py src/aipinho/services/runtime/workspace_context_service.py
```

Resultado: PASS.

## Testes amplos e achados fora do escopo

`python -m pytest tests/unit --maxfail=1 -q`:

```text
1 failed, 8 passed
FAILED tests/unit/test_agent_delegation_service.py::test_delegation_request_result_parent_child_and_timeline
PermissionError: agent_profile_disabled
```

Esse bloqueio ocorre na configuracao/fixture de perfil de agente `lucio`, antes das areas alteradas nesta wave.

`python -m pytest tests/governance --maxfail=1 -q`:

```text
1 failed, 16 passed
FAILED tests/governance/test_g16_legacy_chat_services_folded.py::test_chat_service_remains_content_provider_for_plain_conversation
Expected: conversation
Observed: workspace_analysis_readonly
```

Esse bloqueio pertence a fronteira Semantic Intent/Public Chat, ja observada anteriormente, e nao foi corrigido nesta wave para preservar escopo.

## Resultado esperado no proximo rerun do FireTest 5

Espera-se que:

- `project_inventory.md` continue descrevendo o app/projeto.
- `music_inventory.csv` nao misture arquivos do app/build/cache com corpus.
- Entidades vindas de `library_root` sejam candidatas ao inventario tabular de corpus.
- Arquivos de `project_root`, `src`, `build`, `.gradle` e cache sejam rejeitados por policy e fiquem visiveis nos summaries.
- `extension` seja preenchida por evidencia generica de path/name.
- `codec`, `container`, `bitrate`, `sample_rate`, `channels/canais`, `duration/dura??o`, `artwork` e `metadata` continuem bloqueados sem observer real de metadata.
- Speaker Truth continue impedido de declarar READY sem evidencia real.

## Proxima fronteira provavel

Depois desta wave, se o FireTest ainda bloquear corretamente, a fronteira deve estar mais isolada:

```text
Corpus root observado
  -> entidades elegiveis selecionadas
  -> atributos genericos de arquivo observados
  -> metadata de midia sem capability real
  -> NO_MATCHING_CAPABILITY / OBSERVER_CAPABILITY_MISSING
```

Ou seja: o Runtime deve parar de confundir arquivos do projeto com corpus e passar a bloquear apenas pela ausencia de capability observacional de metadata, se esse for o verdadeiro limite restante.

## Veredito

READY_WITH_FINDINGS.

A wave fortaleceu a separacao entre projeto, corpus, build/cache e artifact outputs sem criar solucao especifica para o FireTest ou para audio. Os bloqueios amplos restantes pertencem a agent profile e Semantic Intent/Public Chat, fora do escopo H1B.2.
