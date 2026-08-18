# CVL Prediction Accuracy

## Fase 0 - Predicao

O CVL executou sem criar estado operacional.

Arquivos gerados:

- `C:\Dev\AIpinho\reports\firetest5\phase0_cognitive_readiness.md`
- `C:\Dev\AIpinho\reports\firetest5\phase0_prediction.md`
- `C:\Dev\AIpinho\reports\firetest5\phase0_dependency_graph.md`
- `C:\Dev\AIpinho\reports\firetest5\phase0_coverage.md`
- `C:\Dev\AIpinho\reports\firetest5\phase0_simulation.md`
- `C:\Dev\AIpinho\reports\firetest5\phase0_frontier.md`

Predicao principal:

```text
predicted_status: blocked
probable_component: capability_matching
probable_contract: readonly_workspace_discovery_contract
probable_capability: entity_discovery
confidence: 0.9
reason_code: PREDICTED_CAPABILITY_MISSING
```

Coverage:

```text
overall_coverage: 0.8
pipeline: 1.0
contracts: 1.0
capabilities: 0.0
artifacts: 1.0
success_contract: 1.0
```

## Execucao real

A Fase 1 foi iniciada pelo endpoint publico `POST /api/v1/chat`.

Resultado real:

```text
status: needs_clarification
operation_type: workspace_readonly_audit_report
intent observado no ChatResponse: filesystem_write_request
intent observado no lifecycle: permission_grant_request
contract_type: filesystem_write
runtime_profile: write_file
Task: ausente
TaskRun: ausente
Validation: not_run
Completion: incomplete
Speaker Truth: blocked
```

Pre-Task Bootstrap na Fase 1:

```text
ChatIngressReceived: complete
PromptNormalized: complete
PreviewStarted: complete
IntentResolutionStarted: complete
IntentResolutionFinished: complete
OperationContractSelected: complete
TaskBootstrapStarted: complete
TaskBootstrapFinished: blocked
TaskCreated: blocked
TaskRunCreated: blocked
```

## Acuracia

O CVL errou o ponto de bloqueio desta rodada.

Classificacao:

```text
prediction_accuracy: incorrect
actual_block_before_predicted_boundary: true
predicted_boundary: capability_matching
actual_boundary: semantic_intent_resolution / operation_contract_selection
```

## Causa da divergencia

O CVL assumiu que o prompt chegaria como contrato readonly de discovery. A execucao real mostrou que a camada Public Chat / Intent tratou o texto disponivel localmente como mutavel/permission grant.

Fator observado:

- o prompt integral usado a partir do arquivo local estava com mojibake (`â`, `NÃO`, `mÃºsicas`);
- a classificacao semantica perdeu o readonly forte e promoveu o fluxo para `filesystem_write`;
- isso bloqueou antes da fronteira cognitiva prevista pelo CVL.

## Conclusao

O CVL continua util, mas sua predicao desta rodada foi invalidada por uma regressao anterior ao ponto previsto: normalizacao semantica/contratual do prompt no ingress publico.

