# H1C0.R2.2 ? Governed External Corpus Root Binding & ObservedEntity Role Projection

## Veredito

`FIRETEST5_H1C0_R2_2_PUBLIC_CORPUS_ROOT_BINDING_BLOCKED`

A corre??o central de root binding e ObservedEntity role projection funcionou: a run p?blica passou de `bound_rows=0` para `bound_rows=100` no `music_inventory.csv`, com `evidence_ref_count=100` e `row_evidence_coverage.status=satisfied`.

A wave n?o pode ser declarada READY porque a run p?blica terminou com `run.status=blocked` e `finished_at` preenchido, mas `result.json` ficou ausente. O blocker final observado ? `RESULT_FINALIZATION_MISSING_AFTER_ARTIFACT_BINDING`.

## Objetivo

Transformar refer?ncias externas declaradas no prompt/contexto p?blico em root bindings governados, com role sem?ntica, policy, provenance, ObservationGoal, ObservedEntity e evidence refs antes da materializa??o do artifact.

## Escopo

- Root binding p?blico para projeto e corpus/library.
- Proje??o de `source_root_role=library_root` para entidades observadas.
- Sele??o sem?ntica de entidades de corpus para `media_corpus_inventory`.
- Materializa??o passiva do artifact a partir de `ObservedEntity`/perception payload.
- CVL awareness para frontiers de root policy e role projection.
- Run p?blica limpa Phase 0?6 com stop no primeiro bloqueio.

## N?o-goals Preservados

- N?o houve hardcode de FireTest, Pinhoabacaxi, path local, artifact espec?fico ou extens?o como autoridade.
- Renderer n?o virou observer.
- Metadata n?o foi inventada.
- RelationshipCandidate n?o virou Truth.
- Validation/Completion/Speaker Truth n?o foram relaxados.
- Fases 2?6 n?o foram executadas ap?s bloqueio da Fase 1.

## Causa Antes

Na H1C0.R2.1, a raiz `D:afa\pinho music` j? era detectada como `library_root`, mas `ObservedEntityCompilationService` consumia o or?amento global de 20.000 entidades no `project_root` antes de chegar ao corpus. Resultado: `entities_by_root_role={project_root: 20000}`, `expected_rows=0`, `bound_rows=0`.

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/observed_entity.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/observed_entity_compilation_service.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/cvl/cognitive_validation_laboratory_service.py`
- `tests/unit/test_observed_entity_compilation_service.py`
- `tests/unit/test_music_inventory_observational_binding_public.py`
- `tests/unit/test_cvl_observational_binding_frontiers.py`

## Arquitetura Antes/Depois

Antes:

`prompt path -> workspace_context.library_roots -> root descriptor -> project_root scan consumes global budget -> no corpus ObservedEntity -> music_inventory bound_rows=0`

Depois:

`prompt/context -> workspace_context.library_roots -> RootBinding + RootBindingPolicyDecision -> role-aware root scan budget -> ObservedEntity(source_root_role=library_root) -> SemanticEntitySelectionService -> bound rows with evidence refs -> passive artifact materialization`

## Root Binding

Foram adicionados IRs can?nicos:

- `RootBinding`
- `ExternalRootBinding`
- `CorpusRootBinding`
- `RootBindingEvidence`
- `RootBindingPolicyDecision`

`WorkspaceRootDescriptor` agora tamb?m carrega:

- `policy_status`
- `access_scope`
- `observation_allowed`
- `mutation_allowed=false`
- `policy_reason_codes`
- `evidence_refs`

## Policy

A policy de observa??o ? read-only e expl?cita. Ela permite observa??o quando:

- a raiz tem role conhecido;
- a raiz existe;
- o contexto est? read-only;
- muta??o continua proibida.

Se uma raiz de corpus/library n?o puder ser observada, o sistema registra `CORPUS_ROOT_POLICY_BLOCKED`.

## ObservedEntity Role Projection

`ObservedEntityCompilationService` agora ordena e particiona a janela de scan por root/papel. Isso impede que um projeto grande consuma toda a janela antes de uma raiz `library_root` declarada ser observada.

Valida??o local real:

```json
{
  "roots_scanned_by_role": {
    "project_root": ["C:\Dev\AIpinho"],
    "library_root": ["D:\rafa\pinho music"]
  },
  "entities_by_root_role": {
    "library_root": 1051,
    "project_root": 18949
  }
}
```

## Artifact Materialization

O renderer permaneceu passivo. Ele consome:

- `ObservedEntity graph`
- `ArtifactIntentPlan`
- `ContractDrivenPerceptionService` perception payload
- evidence refs j? produzidos pelo fluxo governado

N?o houve scan direto no renderer.

## CVL / Phase 0

CVL passou a reconhecer novas frontiers:

- `CORPUS_ROOT_POLICY_BLOCKED`
- `CORPUS_OBSERVATION_EXECUTION_UNAVAILABLE`
- `OBSERVED_ENTITY_ROLE_PROJECTION_MISSING`

A previs?o continua baseada em profile metadata/capability/coverage, n?o em path/projeto.

## Testes

Executado:

```text
python -m pytest tests/unit/test_observed_entity_compilation_service.py tests/unit/test_media_corpus_entity_selection.py tests/unit/test_music_inventory_observational_binding_public.py tests/unit/test_semantic_artifact_intent_resolver.py tests/unit/test_artifact_observation_goal_synthesis.py tests/unit/test_media_inventory_evidence_binding.py tests/unit/test_evidence_phase1_semantic_package.py tests/unit/test_cvl_observational_binding_frontiers.py tests/unit/test_music_inventory_artifact_render_lifecycle.py tests/unit/test_music_inventory_semantic_partial.py tests/unit/test_runtime_terminal_event_idempotency.py tests/unit/test_artifact_endpoint_projection_states.py tests/unit/test_artifact_semantic_contract_music_inventory.py tests/unit/test_phase_dependency_semantic_gate.py tests/unit/test_firetest_phase1_phase2_semantic_contract.py tests/unit/test_public_runtime_response_boundary.py tests/unit/test_public_runtime_result_finalization.py tests/unit/test_phase3_public_preacceptance_boundary.py tests/unit/test_firetest_phase_progression_harness.py tests/unit/test_relationship_stack_integration_audit.py tests/unit/test_project_analysis_single_file_read_budget_cooperation.py tests/unit/test_cognitive_validation_laboratory_service.py tests/unit/test_task_run_store.py tests/unit/test_universal_task_session_service.py -q
```

Resultado: `107 passed in 126.28s`.

`py_compile`: PASS nos arquivos de produ??o alterados.

## Anti-hardcode Audit

A busca em arquivos de produ??o alterados n?o encontrou path/projeto/artifact/extens?o como autoridade decis?ria. O ?nico match relevante foi `FireTestProfile`/`FireTestLaboratoryService` no servi?o CVL, permitido por contrato.

## Run P?blica

Sess?o:

`firetest5_h1c0_r2_2_clean_phase0_to_6_20260813_231519`

TaskRun:

`task_run_a36b25645ebf4fe49c124763a29ec138`

Resultado observado:

```json
{
  "client_response_status": "accepted_running",
  "run.status": "blocked",
  "finished_at": "2026-08-13T23:28:11.550725+00:00",
  "result_json_exists": false,
  "queue_after.active_runs": 0,
  "large_run_count": 0
}
```

`music_inventory.csv`:

```json
{
  "status": "blocked",
  "semantic_contract_status": "partial",
  "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
  "expected_rows": 1051,
  "selected_rows": 100,
  "bound_rows": 100,
  "partial_rows": 100,
  "evidence_ref_count": 100,
  "row_evidence_coverage.status": "satisfied",
  "safe_to_use": false
}
```

Fases 2?6: `skipped_due_to_prior_block`.

## Queue/Storage

Antes da run:

- `active_runs=0`
- `queued_runs=0`
- `pending_approvals=0`
- `large_run_count=0`
- `missing_index_count=0`

Depois da run:

- `active_runs=0`
- `queued_runs=0`
- `pending_approvals=0`
- `large_run_count=0`
- `missing_index_count=0`
- `run.json` leve
- `result.json` ausente para o TaskRun p?blico

## Gaps Restantes

P0 atual:

`RESULT_FINALIZATION_MISSING_AFTER_ARTIFACT_BINDING`

A Fase 1 conseguiu gerar o invent?rio parcial ?til com evid?ncia, mas a cadeia p?blica n?o escreveu `result.json` final coerente. Isso impede READY can?nico.

P1:

- CVL previu `TRUTH_READINESS`, enquanto a fronteira real final foi result finalization.
- Relationship cognition continua `not_available` com reason causal `RELATIONSHIP_OBSERVATION_NOT_BOUND`, preservando Truth.

## Pr?xima Recomenda??o

Repair slice estreito:

`H1C0.R2.3 ? Result Finalization After Partial Semantic Artifact Binding`

Objetivo: quando artifacts partial/blocked ?teis s?o materializados com evid?ncia, a run deve finalizar com `result.status=blocked`, `finished_at`, terminal event ?nico e `result.json` presente, sem transformar partial em sucesso.

## Por que N?o Houve Bypass

A observa??o de corpus ocorreu em `ObservedEntityCompilationService`, antes do renderer, com root binding e policy decision expl?citos. O renderer apenas materializou dados j? governados.

## Por que N?o Houve Sucesso Falso

Mesmo com `bound_rows=100`, o artifact permaneceu `blocked/partial`, `safe_to_use=false`, e a Fase 1 n?o liberou Fase 2. Speaker Truth permaneceu conservador.
