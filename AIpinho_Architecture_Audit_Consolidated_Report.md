# AIpinho - Relatorio Consolidado da Auditoria Arquitetural

Gerado em: 2026-07-31 10:15:27 -03:00

Este relatorio foi produzido a partir da versao final de AIpinho_Architecture_Audit.md, apos a revisao consolidada de dependencias e classificacoes.


---

## Revisao Consolidada 2026-07-31 - Dependencias, Classificacoes e Conclusao Arquitetural

Atualizado em: 2026-07-31 10:15:27 -03:00

### Fonte utilizada
Esta revisao foi baseada na versao acumulada de AIpinho_Architecture_Audit.md apos 16 execucoes concluidas com AUDIT_SCOPE_COMPLETED. A revisao nao substitui inventarios anteriores; ela normaliza as conclusoes, dependencias e classificacoes em nivel de dominio para orientar limpeza, consolidacao e refatoracao futura.

### Estatisticas consolidadas
| Indicador | Valor consolidado |
|---|---:|
| Execucoes de auditoria completas | 16 |
| Arquivos catalogados diretamente nas execucoes | 8914 |
| Arquivos com hardcodes/marcadores | 6301 |
| Arquivos com risco medio/alto registrado | 2050+ |
| Candidatos CODE_DEAD/baixa referencia/stale/cache | 1493 |
| Duplicacoes/sobreposicoes/hash groups/simbolos relevantes | 764+ grupos/sinais mistos |
| Classificados UNKNOWN nas secoes novas | 568 |
| Classificados ARCHIVE nas secoes novas | 745 |
| Classificados KEEP_WITH_REFACTOR nas secoes novas | 6029 |

Observacao: os primeiros blocos usavam formato antigo de metricas. Por isso alguns totais de risco/duplicacao sao conservadores ou misturam tipos de evidencia: duplicacao por hash, duplicacao de simbolos, aliases/stubs, fixtures e sobreposicao conceitual.

### Classificacao consolidada por dominio
| Dominio | Classificacao consolidada | Motivo | Acao recomendada |
|---|---|---|---|
| Runtime/task/session/artifacts/events/timeline | KEEP_WITH_REFACTOR | E o coracao operacional, mas ha stores e services paralelos. | Consolidar em UniversalTaskRuntime, ArtifactRuntime e RuntimeTimeline. |
| Policy/security/sandbox/approvals/config governance | KEEP_WITH_REFACTOR P0 | Area de maior risco sistemico: allowed/ask/denied, grants, approvals e sandbox aparecem em multiplos caminhos. | Criar EffectivePolicyDecisionService e pipeline unico de approval/permission. |
| Chat/mobile/launcher/API routers/view-models | KEEP_WITH_REFACTOR | Muitas superficies publicas podem montar status/resposta de forma divergente. | Tornar routers/view-models consumidores de contratos canonicos. |
| Schemas/contracts | KEEP_WITH_REFACTOR | Muitos campos recorrentes de estado, IDs e runtime profile. | Criar tipos comuns e Runtime Contract Bundle versionado. |
| Services de runtime/governance/patching/doctor/validation | KEEP_WITH_REFACTOR P0 | Concentracao de orquestracao e IO sensivel. | Separar planners/builders/guards/executors/validators/publishers. |
| Repositories/runtime data stores | KEEP_WITH_REFACTOR | Dados ativos/historicos, sem ownership uniforme. | Mapear leitores/escritores e aplicar lifecycle governado. |
| Config YAML/docs/root runbooks | KEEP_WITH_REFACTOR | Podem divergir do codigo e de scripts. | Criar indice canonico de config/docs e Operational Runbook. |
| Tests/fixtures | KEEP_WITH_REFACTOR | Alta cobertura potencial, mas helpers/fixtures duplicados. | Criar matriz teste -> contrato -> regressao -> modulo. |
| Tools/binarios | KEEP_WITH_REFACTOR | Binarios bundled exigem rastreabilidade. | Criar ToolingManifest com hash/origem/versao/licenca. |
| Caches .pyc/.tmp_pycache | ARCHIVE / GENERATED_CACHE | Nao sao fonte arquitetural. | Cobrir por ignore/lifecycle; limpar apenas com processo governado. |
| Release notes antigas/fixtures pontuais/firetest outputs | ARCHIVE | Historico util, mas fora do hot path. | Consolidar em changelog/evidence registry antes de mover. |
| Arquivos UNKNOWN | UNKNOWN / NEEDS_IMPORT_GRAPH | Baixa referencia estatica nao prova morte. | Exigir import graph, testes e runtime evidence antes de arquivar/remover. |

### Dependencias consolidadas
`mermaid
graph TD
  Config[Config YAML / Env / Runbooks] --> Contracts[Schemas / Runtime Contracts]
  Docs[Docs / Architecture Decisions] --> Contracts
  API[API Routers / Mobile / Launcher / External Gateway] --> Services[Service Layer]
  Services --> Runtime[Universal Task Runtime]
  Services --> Policy[Effective Policy Decision]
  Services --> Artifacts[Artifact Runtime]
  Runtime --> Timeline[Runtime Timeline / Events]
  Policy --> Approvals[Approval Runtime]
  Runtime --> Repositories[Repositories / Runtime Stores]
  Artifacts --> Repositories
  Timeline --> Doctor[Runtime Doctor / Regression Matrix]
  Doctor --> PatchIntel[Patch Intelligence / Recommendations]
  Tests[Tests / Fixtures / FireTests] --> Contracts
  Tests --> Services
  Tools[Bundled Tools / Scripts] --> Services
`

### Principais conclusoes
1. A AIpinho ja possui quase todos os blocos de um runtime governado, mas muitos aparecem em trilhas paralelas: schemas, services, configs, docs, tests e stores repetem conceitos de task, approval, validation, artifact, policy e status.
2. O maior risco nao e falta de componente; e excesso de fontes de verdade. A estrategia correta agora e consolidar runtime e contratos, nao adicionar features isoladas.
3. policy/security/sandbox/approval e o eixo P0. Qualquer divergencia ali recria bugs antigos: write/shell allowed sem plano, approval sem draft executavel, validation passed com outputs ausentes, Speaker Truth contraditorio.
4. untime/task/artifact/timeline/doctor e o segundo eixo P0. Sem isso, execucoes ficam sem bootstrap, sem artifact binding, sem timeline e sem diagnostico reproduzivel.
5. Mobile, Launcher, API publica e conectores externos devem ser consumidores de Universal Task Session e contratos canonicos, nao fontes proprias de estado.
6. Tests existem em volume alto, mas precisam de matriz de cobertura. A suite deve virar evidencia arquitetural: cada teste precisa apontar para contrato/regressao/modulo protegido.
7. Muitos arquivos marcados como CODE_DEAD/UNKNOWN nao devem ser removidos automaticamente. A decisao de limpeza exige import graph, runtime evidence e testes.

### Oportunidades prioritarias
| Prioridade | Oportunidade | Resultado esperado |
|---|---|---|
| P0 | EffectivePolicyDecisionService | Uma unica decisao allowed/ask/denied/block, com reason_code e source_channel. |
| P0 | UniversalTaskRuntime | Nenhuma execucao sem task_id/task_run_id/contexto. |
| P0 | Runtime Contracts V2 / tipos comuns | IDs, status, operation_type, runtime_profile, validation e artifact refs padronizados. |
| P0 | ArtifactRuntime + artifact binding | Evidencias read-only sem mutar workspace e sem artifact solto. |
| P0 | RuntimeTimeline + Speaker Truth | Completion/Validation/UI derivados de timeline, sem false success. |
| P1 | External Gateway/Connector unificado | Codex/Gemini/Mobile/Launcher como clientes, sem if provider. |
| P1 | Test Coverage Matrix | Testes viram mapa de garantia de contrato/regressao. |
| P1 | ToolingManifest + Storage Lifecycle | Binarios, caches, artifacts e logs com hash, origem, retention e rollback. |
| P2 | ArchitectureDocsIndex | Docs alinhados ao codigo/config, sem runbooks divergentes. |

### Recomendacao de abordagem para o Lucio
A abordagem recomendada e manter a filosofia ja definida: sem hardcode, sem solucao por caso especifico, modular, rastreavel e governada. O proximo bloco nao deveria expandir capacidades; deveria consolidar o Kernel/Runtime ao redor de quatro fontes de verdade:

1. **Contratos canonicos**: Runtime Contract Bundle, IDs fortes, estados canonicos e schemas versionados.
2. **Runtime canonico**: Task bootstrap, ExecutionResult, Timeline, Artifact Runtime e Validation/Completion/Speaker Truth derivados.
3. **Policy canonica**: EffectivePolicyDecision, Approval Runtime e Sandbox/Permission Resolver unificados.
4. **Observabilidade/Doctor**: cada execucao gera timeline, artifacts, validation e diagnostico contratual reproduzivel.

Somente depois disso faz sentido retomar features de agentes, planner avancado, marketplace e fire tests maiores. Caso contrario, novas features voltam a se apoiar em cabos antigos e recriam rotas paralelas.

### Status desta revisao consolidada
AUDIT_CONSOLIDATED_REVIEW_COMPLETED

## Plano sugerido de consolidacao

### Fase 1 - Congelar e proteger
- Congelar remocoes: nada marcado como UNKNOWN ou baixa referencia deve ser removido sem import graph/testes.
- Declarar generated_cache, untime_evidence, historical_release, ixture, untime_store e source_contract como classes formais de arquivo.
- Criar manifest dos binarios em 	ools e dos stores sensiveis.

### Fase 2 - Consolidar contratos
- Criar tipos comuns para IDs, status, reason_code, artifact_ref, workspace_ref, task_ref, approval_ref.
- Alinhar schemas de chat/mobile/external/approval/runtime com Runtime Contract Bundle.
- Marcar schemas/provider-specific como adapter-level, nao dominio central.

### Fase 3 - Consolidar runtime
- UniversalTaskRuntime como entrada para qualquer operacao executavel.
- ArtifactRuntime independente do workspace.
- Timeline obrigatoria por TaskRun.
- Completion e Speaker Truth derivados da Timeline.

### Fase 4 - Consolidar policy e approval
- EffectivePolicyDecisionService unico.
- Approval so existe com plano executavel quando envolve mutacao.
- Denied/blocked/ask tratados como estados distintos, sem mensagens contraditorias.

### Fase 5 - Tornar testes evidenciais
- Construir matriz 	este -> contrato -> regressao -> modulo.
- Separar unit/contract/integration/e2e/certification/eval.
- Remover duplicacao de helpers somente apos cobertura e consumidores mapeados.

## Veredito

A AIpinho esta arquiteturalmente madura o suficiente para consolidacao de runtime. O gargalo atual e governanca estrutural, nao falta de feature. A prioridade recomendada e reduzir fontes de verdade concorrentes e transformar o catalogo atual em um plano de rewire canonico, com limpeza governada e rastreavel.
