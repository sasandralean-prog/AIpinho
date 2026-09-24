# M10 — Diagnóstico Profundo A.31 / A.32 / A.33

**Status:** diagnóstico estático concluído sobre a `main` em `96ccccd210e1a3a084a651537b366dad3cd5537d` antes deste documento.  
**Escopo:** diagnóstico apenas. Nenhuma correção de runtime é implementada por este documento.  
**Princípio:** preservar uma única autoridade canônica por responsabilidade; manter invariantes de governança determinísticos; tornar percepção, seleção semântica, composição de contexto e planejamento técnico dinâmicos, configuráveis e derivados de máquina + prompt + chat + missão + evidência observada.  
**Antiobjetivos:** nenhum bypass, nenhuma autoridade paralela, nenhum hardcode para Pinhoabacaxi/FireTest, nenhuma promoção de heuristic scoring a verdade, nenhuma ampliação implícita de permissão e nenhuma declaração de sucesso sem evidência.

---

## 1. Protocolo de diagnóstico

### 1.1 Objetivos

O diagnóstico foi dividido em três checkpoints:

- **M10-A.31 — cadeia de informação e perda de contexto:** localizar exatamente onde diagnóstico, evidência, semantic goal, requirements e contexto deixam de atravessar a missão até o patch.
- **M10-A.32 — autoridades/responsabilidades duplicadas e determinismo inadequado:** identificar serviços, contratos e fluxos análogos concorrendo pela mesma responsabilidade; localizar heurísticas semânticas hardcoded, soluções de caso e regras estáticas que deveriam ser configuráveis/contextuais.
- **M10-A.33 — budget de contexto/input/output:** identificar limites concorrentes, truncamentos silenciosos ou semanticamente perigosos, envelopes impossíveis e risco de starvation de input/output.

### 1.2 Evidências utilizadas

O diagnóstico usa quatro classes de evidência:

1. **E2E vivo:** FireTest 5 normal-interface mais recente.
2. **Contratos persistidos:** TaskRun, PhaseOutcome, MissionContinuation, dependency evaluation/admission e PatchCandidate.
3. **Código estático da `main`:** serviços, schemas e policies canônicos.
4. **Testes existentes:** usados como prova de comportamento já suportado pelo sistema, especialmente evidence context e artifact context admission.

### 1.3 Regra de interpretação

- **Confirmado:** reproduzido no E2E e explicado por um caminho estático determinístico.
- **Risco estático:** inconsistência comprovada no código/config, mas ainda não ativada como blocker terminal neste E2E.
- **Invariante saudável:** determinismo que protege autoridade, safety, provenance, hashes, escopo ou side effects e deve ser preservado.
- **Heurística cognitiva:** escolha de relevância, target, comportamento esperado, resumo, ranking ou compressão. Essas decisões não devem ser tratadas como autoridade fixa quando dependem do contexto.

---

## 2. Baseline observado

### 2.1 Estado do runtime antes do diagnóstico

A cadeia A.30.b estava promovida na `main` até:

`96ccccd210e1a3a084a651537b366dad3cd5537d — fix(runtime): preserve continuation semantic goal`

Os principais checkpoints anteriores relevantes eram:

- `6bb97129` — leitura completa governada em evidence repair quando o arquivo cabe no budget;
- `955d65b7` — contratos semânticos bounded da continuation;
- `55b5e1d8` — shape de semantic demand;
- `340ac402` — enforcement do output shape governado;
- `b31398f2` — target scope de patch preview;
- `96ccccd2` — preservação do semantic goal entre TaskRuns.

A.28 introduziu o evidence-repair governado, A.29 preservou use-safety, A.30 congelou critérios terminais e A.30.a separou ordem estrutural de dependência semântica. Essas correções são coerentes com a ideologia atual e não devem ser revertidas.

### 2.2 FireTest 5 usado como prova

Prompt: 7.508 caracteres.  
SHA-256: `a724a9f351b82472e54b64b0f8cf566477725d24336135fc6fbadb5d15089a60`  
Sessão: `chat_f5b86864e409410392dc61edc44f9a72`  
Missão: `mission_7310770d507c80d7f2186c7a`

Cadeia observada:

| TaskRun | Fase | Resultado | Evidence repair |
|---|---|---|---:|
| `task_run_b9736596201a4bc084b38881c9cf171c` | discovery | partial | 36 |
| `task_run_e49605e5e2094476b06f4bef58c84078` | phase_001_readonly_artifact_analysis | completed | 22 |
| `task_run_c52ad58100604582aab4bb9228ef7c14` | phase_002_readonly_artifact_analysis | completed | 10 |
| `task_run_f163d13ead864899a7982d13daadf1b3` | phase_003_readonly_artifact_analysis | completed | 1 |
| `task_run_75296eef1ddf4c75a5b9b796ca68f7d5` | phase_004_readonly_artifact_analysis | completed | 0 |
| `task_run_4e6fc2bed52f4d05b9ba217f064eca55` | phase_005_patch | blocked | n/a |

A `phase_004` terminou com `evidence_repair_focus_complete=true` e `safe_for_destructive_action=true`. O planner escolheu corretamente `patch_preview`. O child de patch recebeu o semantic goal técnico completo.

O bloqueio terminal do patch foi:

- `REPAIR_TASK_NOT_ACTIONABLE`
- `REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING`
- `patch_plan_missing`

Dentro do workflow do child de patch:

1. validate_runtime — passou;
2. validate_workspace — passou;
3. run_role_pipeline — passou formalmente;
4. execute_patch_pipeline — bloqueou;
5. validate_patch_result — não executou;
6. compose_final_result — não executou.

Portanto o problema atual não é mais “a missão não chega ao patch”. Ela chega ao patch de forma governada. O problema é o **handoff cognitivo entre diagnóstico validado e geração de reparo acionável**.

---

# M10-A.31 — Onde a informação se perde

## A.31.1 Objetivo

Determinar se a perda ocorre no semantic goal, na autoridade, nas refs de evidência, no conteúdo de evidência, no contexto do child ou dentro do próprio patch planner.

## A.31.2 Achado confirmado: autoridade atravessa; conteúdo diagnóstico não

O `PhaseOutcomeRepository` preserva corretamente:

- `task_run:<id>`;
- `task_run_result:<id>`;
- artifact IDs;
- artifact evidence refs;
- use-safety;
- semantic properties;
- limitations;
- missing truth;
- risk constraints.

Essas refs entram na `PhaseDependencySnapshot`, depois em `PhaseDependencyEvaluation` e `PhaseDependencyAdmission`.

Isso prova que a **identidade/provenance da evidência atravessa a fronteira**.

Entretanto, refs não são conteúdo.

O `MissionContinuationCandidate` carrega semantic goal, requirements, runtime identity, capabilities, resources e metadata, mas não possui um contrato canônico de diagnostic/evidence context materializado. `MissionContinuationDecision`, `Materialization` e `Execution` carregam `evidence_refs`, mas continuam sendo referências.

### Implicação

A dependência pode responder corretamente:

> “há evidência admissível suficiente para permitir o próximo tipo de uso”

sem entregar ao consumidor:

> “aqui está o diagnóstico/evidência bounded que deve orientar esse uso”.

Safety e cognition ficaram desacoplados de forma assimétrica.

## A.31.3 Ponto exato da perda: MissionPhaseCoordinator → TaskRunContext

`MissionPhaseCoordinatorService._intent_map()` herda, entre outros:

- semantic_intent_graph;
- future_side_effect_intent;
- mission_execution_strategy;
- completion_requirements;
- validation_requirements;
- allow_limited_completion;
- semantic_goal;
- dependency evaluation/admission;
- evidence repair quando aplicável.

Ele **não herda `runtime_context`** e não cria/binda um `context_injection_plan_id`.

Já `TaskRunContextService.build()` só hidrata conteúdo de análise anterior se:

1. `run.intent_map.runtime_context` contiver `project_report`, `file_context_bundle` ou `project_analysis_report`; ou
2. o TaskRun tiver um `context_injection_plan_id` resolvível.

O child de patch não recebe nenhuma das duas coisas.

### Conclusão A.31-F01 — confirmada

**A perda principal acontece no handoff de mission continuation para o contexto executável do child.**

A continuation preserva autoridade e provenance, mas não materializa contexto cognitivo admissível para o próximo TaskRun.

## A.31.4 O GovernedTaskStepRunner confirma a ruptura

No `GovernedTaskStepRunner._execute_patch_pipeline()`, o fallback chama:

`ModelAssistedPatchPlannerService.create_plan(... file_context_bundle=context.outputs.get("_file_context"), ...)`

O parâmetro `evidence_context`, que existe no patch planner, não é fornecido.

Como o patch child normalmente não construiu `_file_context` antes de `execute_patch_pipeline`, ambos chegam vazios:

- sem file context herdado;
- sem evidence context herdado.

O patch planner então executa uma nova descoberta local.

### Conclusão A.31-F02 — confirmada

**O patch runtime reinicia cognição a partir do prompt, em vez de continuar a cognição já validada.**

Isto explica por que o runtime conseguiu provar `safe_for_destructive_action=true` e, imediatamente depois, escolher um target sem relação causal demonstrada com o diagnóstico anterior.

## A.31.5 O patch planner já suporta o que falta

`ModelAssistedPatchPlannerService.create_plan()` já aceita `evidence_context`.

Quando evidence context existe, o serviço:

- ranqueia evidência;
- deriva focus paths;
- injeta evidence refs;
- injeta excerpts relevantes;
- usa a evidência para observed behavior/localization;
- compacta para o budget da role.

Os testes existentes comprovam esse caminho, inclusive:

- compactação de evidência grande sob ~8k de contexto;
- seleção de janela relevante dentro de relatório longo;
- preservação de evidence refs;
- uso de evidence context para produzir expected behavior mais útil.

### Conclusão A.31-F03 — confirmada

**Não falta uma capacidade cognitiva nova no patch planner. Falta conectar a evidência governada já existente ao input que o patch planner já sabe consumir.**

Criar outro patch-diagnosis service paralelo seria a solução errada.

## A.31.6 Semantic goal: corrigido, mas insuficiente

A.30.b corrigiu a perda do semantic goal. O E2E provou que o patch child recebe o prompt técnico completo.

Isso removeu um bug real, mas também expôs uma distinção arquitetural importante:

- semantic goal responde **o que a missão quer**;
- evidence context responde **o que foi observado no workspace**;
- repair intent responde **qual comportamento específico precisa mudar**;
- authority responde **o que pode ser feito**.

Um único campo `semantic_goal` não deve assumir essas quatro responsabilidades.

## A.31.7 Solução arquitetural possível

Sem criar bypass ou nova autoridade paralela:

1. `PhaseOutcome` continua sendo a verdade semântica do produtor.
2. `evidence_refs` continuam sendo refs/provenance, não conteúdo inline.
3. Antes de materializar o child, o runtime resolve somente refs context-usable por uma autoridade canônica.
4. Artifact content deve passar por `ArtifactLibraryService.use_as_context()` ou por uma única autoridade consolidada equivalente, com sanitização e budget.
5. O conjunto admitido deve gerar/bindar um único context injection plan canônico ao child.
6. `TaskRunContextService` deve materializar esse plano em contexto runtime.
7. `GovernedTaskStepRunner` deve entregar o contexto admitido ao `ModelAssistedPatchPlannerService`.
8. O patch planner não deve ganhar autoridade por receber contexto; contexto é conhecimento read-only, authority continua no MissionContract/Policy/Dependency Admission.

### Critério de desenho

**Evidence refs são identidade. Context admission decide uso. Context plan decide payload. TaskRunContext materializa. Patch planner consome. Nenhuma dessas camadas deve substituir a outra.**

---

# M10-A.32 — Autoridades duplicadas, fluxos análogos e hardcode semântico

## A.32.1 Determinismo saudável versus determinismo inadequado

O diagnóstico não recomenda tornar tudo “LLM-driven”.

Devem continuar determinísticos:

- requested/authorized capabilities;
- workspace/resource scope;
- side-effect classification;
- policy decisions;
- approval/authority;
- dependency admission;
- use-safety gates;
- canonical hashes;
- provenance;
- completion criteria congelados;
- path guards;
- truth/success enforcement.

Devem ser dinâmicos/configuráveis ou derivados do contexto:

- relevância de arquivo;
- relevância de evidência;
- seleção de target técnico;
- expected behavior;
- localização de comportamento;
- tamanho/forma do recorte de contexto;
- escolha da unidade editável;
- estratégia de reparo dentro da autoridade permitida;
- budget de input/output por máquina/modelo/tarefa.

## A.32.2 Duas classes `ContextInjectionPlan` com contratos diferentes

Há duas definições independentes com o mesmo nome conceitual.

### Context Kernel

`src/aipinho/schemas/context/contracts.py`

Possui:

- `bundle_id`;
- `role_id`;
- `purpose`;
- `slots`;
- citation map;
- safe_for_prompt_assembly;
- blocked items/warnings.

### RAG integration

`src/aipinho/schemas/rag/integration/contracts.py`

Possui:

- `admission_id`;
- `policy_decision_id`;
- `usage_mode`;
- `workspace`;
- `context_items`;
- citation map;
- `budget_summary`;
- limitations/warnings/blocked reasons;
- safe_for_prompt_assembly;
- trace.

### Consumidores divergentes

- a API `/context/injection-plan` usa `ContextKernelService`;
- `TaskRunContextService` usa `services.rag.integration.ContextInjectionPlanner`;
- `RolePipelineService` valida a versão RAG.

### Conclusão A.32-F01 — risco arquitetural alto

**“Context injection plan” não tem uma única autoridade/schema no runtime.**

Uma evidência pode ser corretamente admitida por um sistema e invisível para outro porque os consumidores não compartilham o mesmo contrato/store.

### Possível solução

Escolher um contrato canônico de ContextPlan e transformar RAG, artifact context, chat attachments e phase evidence em **adapters/producers**, não em autoridades paralelas.

A decisão deve ser feita por responsabilidade, não por nome:

- Context Kernel: candidato natural a autoridade genérica.
- RAG integration: deve especializar/adaptar fontes RAG/memory.
- ArtifactLibrary: deve materializar artifact refs de modo seguro.
- TaskRunContext: deve consumir o plano canônico já admitido.

Não renomear e manter dois kernels equivalentes; consolidar semantics/ownership primeiro.

## A.32.3 ArtifactLibrary já implementa materialização segura de artifact context

`ArtifactLibraryService.use_as_context()` já:

- exige artifact `ready`;
- exige `context_usable`;
- respeita `max_context_bytes`;
- sanitiza/redige;
- devolve preview + warnings + evidence refs.

Testes existentes comprovam:

- texto é permitido;
- binário é negado;
- segredo é redigido;
- evidence refs são preservadas.

### Conclusão A.32-F02 — confirmada

Existe uma autoridade pronta para parte do handoff que atualmente é ignorada pela mission continuation.

**Não criar leitura direta de storage no coordinator/patch planner.**

## A.32.4 Dois caminhos de análise read-only

Há pelo menos dois executores relevantes:

- `ReadOnlyTaskStepRunner`;
- `ReadonlyAnalysisArtifactRuntimeService`.

Ambos:

- constroem ProjectAnalysisRequest;
- consomem EvidenceRepairSemanticService;
- projetam semantic outcome;
- operam com file-selection/read budgets.

Entretanto, os budgets não vêm da mesma fonte.

O runtime especializado usa os budgets de `ProjectAnalysisService`.

O generic `ReadOnlyTaskStepRunner._request()` contém limites próprios como `max_files=40..100` e `max_total_bytes=700000`.

### Conclusão A.32-F03 — risco estático

**Há responsabilidade análoga com policy/budget divergente.**

Isso pode fazer uma mesma missão ter comportamento diferente dependendo de qual runner materializou a fase.

### Possível solução

Extrair uma única autoridade para construir `ProjectAnalysisRequest` a partir de:

- phase purpose;
- machine budget;
- task semantic vocabulary;
- evidence repair contract;
- workspace/resource scope;
- downstream use.

Os runners deveriam executar o request, não reinterpretar budgets.

## A.32.5 Role pipeline de patch versus ModelAssistedPatchPlanner

O patch workflow executa um role pipeline `patch_planning` antes do `execute_patch_pipeline`.

No E2E observado, planner/coder/reviewers terminaram formalmente, mas usaram `stub.default` ou passes determinísticos com `real_inference=false`.

Depois disso, `ModelAssistedPatchPlannerService` executa seu próprio fluxo:

diagnosis → patch candidate → actionability → repair proposal → model role `patch_planner` → PatchPlan.

### Conclusão A.32-F04 — responsabilidade análoga

Existem dois conceitos de “patch planning” no mesmo child:

1. role pipeline multi-role;
2. ModelAssistedPatchPlanner.

No estado atual, o primeiro não fornece o RepairTask usado pelo segundo e pode aparecer como `completed` mesmo sem cognição real.

### Implicação

- custo/latência sem transferência de conhecimento;
- status “completed” semanticamente ambíguo;
- dois locais potenciais para planner/coder/reviewer;
- maior risco de futuras correções entrarem no pipeline errado.

### Possíveis soluções

Escolher uma das relações:

- **pipeline como produtor real de evidência:** seus outputs entram no context plan/RepairTask consumido pelo patch planner; ou
- **pipeline como validação posterior:** remover passes cognitivos redundantes antes do RepairTask e usá-los somente após existir proposta; ou
- consolidar patch planner dentro de um único workflow cognitivo governado.

Não manter duas cadeias independentes com nomes equivalentes.

## A.32.6 Heurística estática: `candidates[0]` vira diagnóstico

`ModelAssistedPatchPlannerService._diagnosis_artifact()` escolhe:

`selected = candidates[0]`

Sem evidência suficiente, cria:

- observed behavior genérico: `Current file context was selected for governed patch planning.`;
- evidence ref sintética `file_context:<source>:<target>`;
- semantic goal reduzido a expected behavior ou filepath;
- RepairHint fixo.

No E2E, isto escolheu `DesktopDspRuntime.kt` sem causalidade demonstrada.

### Conclusão A.32-F05 — confirmada

**Ranking de arquivo foi promovido indevidamente a diagnóstico.**

File relevance pode indicar onde investigar; não deve, sozinho, afirmar “este é o target de reparo”.

### Possível solução

Target selection deve exigir uma das seguintes provas governadas:

- evidence ref que localiza target;
- diagnosis artifact com target confidence;
- explicit focus path derivado de evidência;
- cognitive target proposal validada contra evidência e workspace.

Se nenhum target satisfizer o contrato, o runtime deve solicitar nova análise focada, não escolher o primeiro arquivo.

## A.32.7 Hardcode semântico em expected behavior

`_diagnosis_expected_behavior()`:

- corta o objetivo nos primeiros 1.200 chars;
- rejeita texto considerado “operational”;
- exige que algum termo derivado do target_file apareça nesse prefixo;
- caso contrário retorna vazio.

Isto gerou diretamente `REPAIR_TASK_EXPECTED_BEHAVIOR_MISSING`.

### Conclusão A.32-F06 — causa confirmada

O expected behavior é inferido por **posição textual + nome do target**, em vez de ser derivado do intent/requirements/evidence.

### Possível solução

Criar/usar um **behavior contract** derivado de fontes canônicas:

- semantic intent graph;
- mission completion/validation requirements;
- diagnosis evidence;
- observed behavior;
- target localization.

O modelo pode propor a ligação entre evidência e comportamento, mas runtime valida provenance/scope.

Não extrair comportamento esperado por prefix truncation.

## A.32.8 Hardcodes cognitivos adicionais no patch planner

Foram encontrados valores/regras embutidos diretamente no serviço:

- first 3 evidence items para summary;
- 1.200 chars para ranking/excerpt em diversos pontos;
- 500-char evidence excerpt;
- 240-char fallback semantic goal/field caps;
- relevance terms fixos: analysis, diagnosis, diff, risk, static, patch, preview, hypothesis etc.;
- preferência fixa de produção sobre testes;
- desempate por tamanho de path;
- repair strategy literal;
- constraints `replacement_only/no_diff_generation/no_target_selection` embutidas no diagnosis builder.

Nem todos são incorretos. O problema é a **origem**.

### Regra recomendada

- Safety constraints → policy/config/action contract.
- Model-output contract → role/output contract.
- Relevance semantics → task semantic vocabulary + purpose/profile.
- Budget/truncation → budget authority.
- Repair strategy → RepairTask/diagnosis, não literal genérico.
- Target preference → evidence/diagnosis, não path heuristic fixa.

## A.32.9 FileSelection semantic scoring é excessivamente lexical

`FileSelectionService._semantic_score()` combina:

- direct token intersection;
- semantic token groups;
- pesos fixos da policy.

Problemas observados:

1. tokens estruturais como `src`, `main`, `kotlin`, `com`, package/project names entram como “semântica”;
2. direct match satura rapidamente;
3. semantic group concede bônus se a query contém qualquer termo do grupo e o path qualquer outro termo do grupo;
4. prompts longos naturalmente ativam muitos grupos simultaneamente;
5. termos polissêmicos como “codec” não distinguem codec JSON/preset de media codec.

No E2E, arquivos DSP/JSON codec ultrapassaram componentes explicitamente relevantes como AdaptivePcmDecoder, JavaSoundPcmDecoder, JvmDesktopPlayer e DesktopPlayableUriResolver.

### Conclusão A.32-F07 — confirmada pelo E2E

**A seleção lexical atual funciona como recall amplo, mas é fraca como ranking causal para patch planning.**

### Possíveis soluções

- usar semantic facets compiladas do intent graph em vez do prompt cru;
- stop tokens dependentes do project profile;
- separar namespace/package tokens de domínio;
- exigir correspondência semântica mais específica dentro dos grupos;
- tornar grupos purpose-specific;
- priorizar focus/evidence paths sobre lexical discovery;
- usar lexical scoring apenas para discovery, nunca sozinho para target de patch.

## A.32.10 Public status duplica verdade terminal

`canonical_public_chat_service.py` calcula a resposta a partir do root result e do root `mission_continuation_runtime`.

No E2E, o root dizia “child started”, enquanto o descendente terminal já estava bloqueado no patch. A resposta pública foi `WORKSPACE_FIX_DISCOVERY_COMPLETED_WITH_LIMITATIONS`, não o blocker terminal da missão.

### Conclusão A.32-F08 — observabilidade/authority projection

Existe uma segunda projeção de “estado da missão” que não acompanha a cadeia terminal.

### Possível solução

A resposta pública deve consumir uma única visão agregada de mission lifecycle/terminal frontier, não recomputar status a partir do primeiro TaskRun.

---

# M10-A.33 — Context budget, input budget e output budget

## A.33.1 Mapa atual de budgets

### Role inference

`role_inference_budget_policy.yaml`:

| Classe | Prompt chars | Context chars | Output tokens |
|---|---:|---:|---:|
| low | 6.000 | 4.000 | 512 |
| medium | 12.000 | 8.000 | 1.024 |
| large_cpu_slow | 16.000 | 10.000 | 1.536 |

`patch_planner`, planner, coder, code reviewer e patch-quality reviewer usam classe `medium`.

### Patch planner policy

`model_patch_planner_policy.yaml`:

- max_context_chars: 48.000;
- max_evidence_context_chars: 3.000;
- max_file_context_chars: 12.000;
- max_role_objective_chars: 300;
- max_candidate_field_chars: 240;
- max_replacement_context_chars: 3.400;
- max_replacement_evidence_context_chars: 1.400;
- max_output_tokens: 192;
- max_candidate_files: 8;
- max_file_edit_chars: 3.400.

### Modelo primário

`qwen2_5_coder_7b_q4_k_m`:

- context window: 8.192 tokens;
- model max output: 2.048 tokens.

## A.33.2 Três autoridades de budget sobrepostas

O patch planner declara 48k chars, mas `_role_context_limit()` pega o menor valor entre policy e `RoleInferenceBudgetService`.

Para `patch_planner=medium`, o teto efetivo de **context** é 8.000 chars.

Logo:

`48.000 configurado → 8.000 efetivo`

### Conclusão A.33-F01 — risco estático confirmado

A policy do patch planner comunica um budget que não representa o envelope efetivo.

Isso dificulta tuning e diagnóstico porque uma alteração em `max_context_chars: 48000` pode não mudar absolutamente nada.

### Possível solução

Um único `EffectiveInferenceBudget` deve ser calculado com provenance:

- hardware;
- model registry;
- role binding;
- phase/purpose;
- policy;
- prompt/chat workload;
- required output reserve.

Cada consumidor deve receber o budget efetivo, não recalculá-lo parcialmente.

## A.33.3 O RoleModelGate mede request bruto, não o prompt final

`RoleInferenceBudgetService.calculate()` mede:

- `len(request.prompt)`;
- `len(str(request.context))`.

Depois, `RolePromptContractBuilder` constrói um prompt maior, adicionando:

- Role;
- Policy;
- Output contract;
- reminder;
- User/task input;
- `Context:\n{request.context}`.

O gate não reavalia esse envelope final.

### Conclusão A.33-F02 — risco alto

É possível prompt e context passarem individualmente no gate e o **prompt final montado** exceder o limite real.

A.24-A.26 já corrigiram problema análogo no PromptAssembly principal, mas RoleInference usa outra cadeia de montagem/budget.

### Possível solução

Aplicar o mesmo princípio A.26 ao role inference:

**budget final deve ser verificado depois da montagem final do prompt.**

A autoridade de budget deve receber as mensagens finais e reservar output antes da chamada.

## A.33.4 Char budget e token window não estão reconciliados como envelope único

O gate usa chars; o model registry define context window em tokens.

Não há, nesse caminho, prova única de:

`input tokens + reserved output tokens <= model context window`.

### Implicação

Mesmo abaixo de 8k chars, conteúdo altamente tokenizável pode ter comportamento diferente. Inversamente, chars podem ser conservadores demais.

### Possível solução

Budget em duas dimensões:

- char budget para proteção simples/rápida;
- token estimate/model tokenizer quando disponível;
- sempre reservar output antes de admitir contexto.

## A.33.5 Output starvation do patch planner

O patch planner limita a saída a **192 tokens**.

Ao mesmo tempo o output contract exige um `RepairProposal` com:

- target;
- intent;
- concrete_change;
- rollback;
- impact;
- risks;
- confidence;
- e potencialmente `suggested_replacement` contendo o **replacement completo**.

A actionability aceita unidade editável de até 3.400 chars.

### Conclusão A.33-F03 — blocker latente

Existe uma incompatibilidade estrutural entre:

- tamanho máximo aceito da unidade de edição;
- exigência de replacement completo;
- envelope JSON obrigatório;
- output máximo de 192 tokens.

Mesmo que A.31 seja corrigido e o target seja perfeito, um patch legítimo pode ficar impossível de serializar.

### Possíveis soluções

O runtime deve calcular antes da inferência:

`required_output_budget = schema_overhead + repair_reasoning_budget + estimated_replacement_budget`

Se não couber:

- escolher uma unidade editável menor, baseada em symbol/localization;
- executar uma etapa de proposal sem replacement e uma etapa separada de code generation governada;
- selecionar/escalar um modelo/budget compatível;
- ou bloquear explicitamente com `PATCH_OUTPUT_BUDGET_INSUFFICIENT`.

Nunca truncar replacement e tratá-lo como patch válido.

## A.33.6 Input starvation por prefix truncation

Mesmo com o semantic goal completo preservado no TaskRun, o patch planner reduz significado cedo:

- role objective: 300 chars por policy;
- expected behavior: primeiros 1.200 chars;
- candidate fields: 240 chars;
- evidence: 3.000 chars;
- replacement evidence: 1.400 chars.

No FireTest, os primeiros 1.200 chars continham principalmente:

- instrução E2E;
- autorização;
- workspace;
- corpus;
- Git.

Os critérios técnicos específicos apareciam mais tarde.

### Conclusão A.33-F04 — causa confirmada em expected behavior

**Prefix truncation preserva posição, não relevância.**

### Possível solução

Nunca usar “primeiros N chars do prompt” como semantic capsule.

Compilar um `TaskSemanticCapsule` bounded a partir de:

- semantic intent graph;
- frozen completion requirements;
- validation requirements;
- current phase;
- unsatisfied effects;
- target-specific evidence;
- chat constraints relevantes.

O capsule deve ser reconstruível/provenanced e caber no budget.

## A.33.7 Evidence budget só funciona se houver evidence handoff

Os limites de 3.000/1.400 chars de evidência são potencialmente aceitáveis porque o serviço já possui ranking/excerpt relevante.

Mas no E2E `evidence_context` chegou vazio.

### Conclusão

Antes de aumentar budget, corrigir handoff.

**Budget maior não corrige contexto ausente.**

## A.33.8 Hardware e máquina devem participar do budget, não da semântica

`RoleInferenceBudgetService` já considera hardware class para budget.

Esse é o padrão desejado:

- máquina influencia latency/context/output envelope;
- máquina não altera verdade, authority ou expected behavior;
- hardware limitado pode causar chunking/escalation/partial planning;
- hardware limitado nunca deve justificar perda silenciosa de evidence requirement.

## A.33.9 Telemetria recomendada

Cada inferência relevante deveria publicar um snapshot único:

- model id;
- hardware class;
- role;
- purpose;
- model context window;
- prompt chars/tokens;
- admitted context chars/tokens;
- omitted/truncated context IDs;
- reserved output tokens;
- actual output tokens;
- schema overhead estimate;
- evidence items admitted/omitted;
- reason for every truncation;
- whether semantic capsule, source excerpt ou optional context foi truncado.

Isso transforma `budget_exceeded` de sintoma genérico em diagnóstico reproduzível.

---

# 3. Mapa de responsabilidades recomendado

| Responsabilidade | Autoridade recomendada |
|---|---|
| Missão, authority e recursos | MissionContract |
| Sequenciamento/continuação | TaskRunPlanner + MissionPhaseCoordinator |
| Verdade do produtor | PhaseOutcome |
| Admissão semântica downstream | PhaseDependencyEvaluation/Admission |
| Artifact persistence/provenance | Artifact Runtime/Library |
| Artifact → contexto seguro | ArtifactLibrary context-use adapter |
| Admissão/composição de contexto | um único Context Kernel/ContextInjectionPlan canônico |
| Contexto do child | TaskRunContextService |
| Análise de projeto | ProjectAnalysisService |
| Diagnosis/RepairTask | canonical diagnosis/patch intelligence |
| Proposta de reparo | ModelAssistedPatchPlanner |
| Mutação | patch apply/runtime governado |
| Truth terminal da missão | mission lifecycle/terminal aggregate |
| Resposta pública | projeção do truth terminal, sem recomputar autoridade |

A tabela é uma direção arquitetural, não autorização para criar novos kernels. Sempre que já existir uma autoridade equivalente, consolidar/adaptar em vez de duplicar.

---

# 4. Fluxo alvo proposto

O fluxo conceitual ideal é:

`prompt + chat + machine context`
→ ingress semântico
→ MissionContract congelado
→ análise read-only
→ artifacts + PhaseOutcome
→ evidence refs
→ dependency admission
→ **context admission/materialization**
→ child TaskRun com ContextPlan canônico
→ TaskRunContext
→ diagnosis evidence
→ RepairTask
→ PatchCandidate
→ RepairProposal
→ output-budget admission
→ PatchPlan
→ approval/policy quando exigido
→ patch apply
→ build/test/runtime
→ completion evidence
→ git/push
→ mission terminal truth
→ public response.

O ponto em negrito é a lacuna mais importante observada hoje.

---

# 5. Priorização de riscos para uma futura correção

## Prioridade 1 — information handoff

Corrigir a ponte entre PhaseOutcome/evidence refs e TaskRunContext do child.

Sem isso, qualquer melhoria do patch planner continuará redescobrindo o workspace e poderá escolher targets arbitrários.

## Prioridade 2 — consolidar ContextPlan

Resolver a duplicidade dos dois `ContextInjectionPlan` antes de criar integração nova. Escolher autoridade canônica e adaptar consumidores.

## Prioridade 3 — RepairTask evidence-first

Impedir `candidates[0]` de virar target de patch sem causalidade suficiente. O target deve nascer de diagnosis/evidence/localization.

## Prioridade 4 — budget envelope único

Unificar role/model/hardware/purpose budgets e verificar o prompt final + output reserve.

## Prioridade 5 — output budget do patch

Tornar o output budget compatível com o tamanho da unidade editável e o schema do RepairProposal.

## Prioridade 6 — reduzir heurística lexical

Separar discovery lexical de target selection causal e substituir raw prompt prefix por semantic capsule.

## Prioridade 7 — remover/ligar fluxos cognitivos duplicados

Clarificar relação entre role pipeline `patch_planning` e `ModelAssistedPatchPlanner`, e entre os dois caminhos read-only.

## Prioridade 8 — truth público agregado

A UI/public response deve refletir o terminal descendant frontier da missão.

---

# 6. Hipóteses que NÃO devem virar solução

Não corrigir este problema por:

- aumentar `max_candidate_files` até “achar o arquivo certo”;
- aumentar 1.200 para outro número arbitrário;
- adicionar nomes `Decoder`, `Player`, `M4A` ou paths do Pinhoabacaxi a heurísticas;
- detectar especificamente FireTest 5;
- copiar o project report inteiro para todo child;
- colocar evidence content bruto dentro de MissionContract;
- ignorar ContextAdmission/Artifact sanitization;
- permitir patch só porque `safe_for_destructive_action=true`;
- desligar actionability;
- aceitar RepairTask sem expected behavior;
- elevar output tokens cegamente sem reservar context window;
- fazer LLM escolher authority/capabilities;
- criar um “patch runtime v2” paralelo.

Essas alternativas mascarariam o sintoma e aumentariam dívida arquitetural.

---

# 7. Critérios para considerar A.31/A.32/A.33 diagnosticamente encerrados

### A.31 — encerrado como diagnóstico

Foi localizado o ponto de perda:

`PhaseOutcome/evidence refs → dependency admission → MissionPhaseCoordinator → child TaskRun → TaskRunContext`.

Authority/provenance atravessam; evidence payload utilizável não.

### A.32 — encerrado como diagnóstico

Foram identificadas responsabilidades análogas/disputadas:

- dois `ContextInjectionPlan` incompatíveis;
- ArtifactLibrary context use versus RAG ContextInjectionPlanner versus ContextKernel versus evidence_context direto;
- dois caminhos de read-only analysis com budgets distintos;
- role pipeline patch planning versus ModelAssistedPatchPlanner;
- public root status versus mission terminal descendant truth;
- lexical file selection e patch target heuristic promovidos indevidamente a decisão semântica.

### A.33 — encerrado como diagnóstico

Foram identificadas incompatibilidades de budget:

- 48k patch policy versus 8k effective role context;
- raw request budget versus final assembled role prompt;
- char budget versus model token window;
- 192 output tokens versus RepairProposal estruturado + replacement de até 3.400 chars;
- prefix truncation de 300/1.200 chars versus prompt longo;
- evidence budgets úteis, mas hoje sem evidence handoff.

---

# 8. Próximo passo recomendado

Não iniciar outra rodada de FireTest antes de desenhar a correção arquitetural.

A próxima etapa deve produzir um plano de implementação que:

1. escolha a autoridade canônica de ContextPlan;
2. defina como refs do PhaseOutcome são materializadas com sanitização e budget;
3. ligue esse plano ao child TaskRun e TaskRunContext;
4. faça RepairTask/target derivar de evidência;
5. consolide o budget final de inferência;
6. ajuste o output contract/budget do patch;
7. preserve todos os gates de authority/safety existentes;
8. só então implemente regressões e repita o E2E.

O objetivo não é “fazer o FireTest passar”. O objetivo é fazer qualquer missão governada atravessar **diagnóstico → contexto → reparo → mutação → validação** sem perder significado nem ampliar autoridade.
