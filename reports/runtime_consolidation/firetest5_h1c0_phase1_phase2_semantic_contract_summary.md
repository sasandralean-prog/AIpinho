# H1C0 Phase 1/2 Semantic Contract Summary

## Veredito
FIRETEST5_H1C0_PHASE1_PHASE2_SEMANTIC_CONTRACT_BLOCKED

## Objetivo
Corrigir a verdade semantica da cadeia Fase 1 -> Fase 2: artifact fisico nao basta; dependency fisica nao basta; Speaker Truth nao pode passar em cima de artifact semanticamente raso.

## Escopo
- Contrato semantico generalista para inventario de corpus musical/media.
- Materializacao com campos semanticos derivados do profile/perception payload.
- Gate semantico de dependencia entre fases.
- accepted_running.task_run_id estruturado quando local.
- Corre??o geral de leitura BOM em registry legado.

## Nao-goals
- Nao implementar Fase 3.
- Nao corrigir accepted_running/public pre-acceptance amplo.
- Nao promover relationship candidate para Truth.
- Nao criar artifact fake.
- Nao hardcodar projeto, FireTest, caminho local ou extensao como regra decisoria.

## Arquivos Alterados
- config/artifacts/artifact_semantic_contract_policy.yaml
- src/aipinho/services/artifacts/artifact_semantic_contract_service.py
- src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py
- src/aipinho/schemas/chat/chat_response.py
- src/aipinho/services/artifacts/artifact_interaction_core.py
- tests/unit/test_artifact_semantic_contract_music_inventory.py
- tests/unit/test_phase_dependency_semantic_gate.py
- tests/unit/test_firetest_phase1_phase2_semantic_contract.py
- tests/unit/test_public_runtime_response_boundary.py
- tests/unit/test_artifact_runtime_service.py

## Contrato Music Inventory
Foi adicionado contrato `media_corpus_inventory_artifact`, selecionado por tokens semanticos genericos de media/audio/music + inventory/catalog/corpus. O contrato exige schema rico e rejeita CSV de findings (`severity,title,summary`) como inventario musical. Findings continuam podendo existir como artifacts de findings, mas nao como inventario de corpus.

## Materializacao
O runtime agora tenta preencher campos de inventario a partir de `ObservedEntity`/`ArtifactSemanticProfile`: `entity_id`, `source_root_role`, `relative_path`, `filename`, `extension`, `media_type`, `metadata_status`, `evidence_ref`, `limitations`, `relationship_candidate_refs` e `validation_status`. Ausencia de metadata vira estado/limitation, nao sucesso silencioso.

## Phase Dependency Gate
A Fase 2 agora revalida semanticamente artifacts de dependencia por contrato. Se uma dependencia existir fisicamente mas falhar semanticamente, o gate retorna `PHASE_DEPENDENCY_SEMANTIC_INSUFFICIENT` e `safe_to_report_success=false`.

## Validation / Completion / Speaker Truth
Validation distingue shape/arquivo de contrato semantico. Completion nao considera outputs satisfeitos quando artifact semanticamente exigido falha. Speaker Truth permaneceu conservador nos testes e na run publica (`safe_to_report_success=false`).

## accepted_running task_run_id
Corrigido no contrato publico: a resposta `accepted_running` agora inclui `task_run_id` estruturado. Na run final, `task_run_id=task_run_a7b57ac3e0034762a70db6290b8cfd61` veio no campo estruturado e em `result_ref_id`.

## Higiene Antes da Run Publica
Foi feita higiene governada: artifacts/runs/sessoes antigas foram movidos para `D:\AIpinho_runtime_hygiene\h1c0_cleanup_20260813_081500`. O registry legado invalido de 731 MB saiu do caminho ativo. Store ativo ficou com JSONs validos e fila limpa.

## Run Publica Fase 1
Tentativa 1 apos higiene bloqueou antes da prova H1C0 por `Unexpected UTF-8 BOM` no registry stub; corrigido com leitura `utf-8-sig` geral no registry. Tentativa 2 atravessou ProjectAnalysis e criou dois artifacts (`phase1_discovery.md`, `project_inventory.md`), mas ficou presa apos `artifact_creation_started` do terceiro artifact de inventario. Foi terminalizada por budget governado.

## Run Publica Fase 2
Nao executada. Motivo canonico: Fase 1 nao completou nem provou satisfacao semantica do inventario musical. Avancar Fase 2 seria repetir o bug conceitual que esta wave quer matar.

## Resultados Publicos Finais
- phase1_task_run_id: task_run_a7b57ac3e0034762a70db6290b8cfd61
- client_status: accepted_running
- client_elapsed_ms: 6675
- summary.status: BLOCKED
- result.status: blocked
- artifacts endpoint count: 2
- artifact_creation_started_count: 3
- artifact_created_count: 2
- terminal_event_count: 2
- truth.safe_to_report_success: False

## Finding Bloqueante
A H1C0 passou em testes service-equivalent/integrados, mas a run publica bloqueou antes de demonstrar o contrato semantico de `music_inventory`. A fronteira publica atual e `ARTIFACT_RENDER_TERMINALITY`: renderizacao longa do inventario nao terminou sob budget e houve duplicidade de `run_blocked` durante reconciliacao/terminalizacao.

## Testes
- Integrated `python -m pytest ... -q`: 56 passed in 25.10s.
- Final focused rerun after cosmetic cleanup: 21 passed in 11.82s.
- `python -m py_compile ...`: PASS.
- Anti-hardcode scan: achados apenas em testes/logical paths; nenhuma regra nova em source hardcodando projeto/path/extensao.

## Gaps Restantes
- Artifact render de inventario ainda pode prender a run publica antes da validacao semantica final.
- Terminalidade idempotente regrediu/raceou na reconciliacao: dois `run_blocked` apareceram na run final.
- Summary ainda mostra `observational_cognition.status=not_available` quando a run bloqueia antes do binding completo.
- Phase0 previu `TRUTH_READINESS`, nao a fronteira real de artifact render timeout nesta run; calibration deve registrar mismatch.

## Proxima Recomendacao
Repair slice especifico em Artifact Render Lifecycle / public terminal idempotency para garantir renderizacao cooperativa do inventario e terminal event unico. Depois repetir H1C0 public rerun para provar Fase 1 bloqueando/passing por semantica e Fase 2 respeitando dependency gate.

## Sem Bypass / Sem Hardcode
A correcao foi por contrato semantico extensivel e gate generico. Nao houve if para FireTest, Pinhoabacaxi, path local ou extensao como autoridade. O nome `music_inventory` aparece em testes e requisicoes de FireTest, nao como regra de decisao no source.

## Por Que Nao Houve Sucesso Falso
A Fase 2 foi pulada porque a Fase 1 bloqueou antes de satisfazer o contrato. Speaker Truth ficou `safe_to_report_success=false`. O veredito e BLOCKED, nao READY.

