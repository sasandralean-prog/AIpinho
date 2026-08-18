# H1C.1 - Conversation Runtime Truth & Meta-Conversation Routing

## Objetivo

Corrigir a camada conversacional publica antes de novo FireTest 5, sem tocar no pipeline operacional, artifact runtime, observers, Validation, Completion ou Speaker Truth.

O ajuste preserva a autoridade unica de intent: a classificacao continua no `CanonicalIntentRouter` via `SemanticIntentResolutionService`. A rota publica apenas renderiza a resposta adequada depois da decisao canonica.

## Problema

Conversas simples e meta-conversas podiam degradar de duas formas:

- `allowed_actions=[]` era interpretado como ausencia de resposta, quando significa apenas ausencia de acao operacional.
- perguntas sobre falha anterior, intent ou classificacao podiam ser promovidas para analise de workspace.
- falhas do modelo speaker podiam ser descritas como falha de intent.

## Mudancas

Arquivos alterados:

- `config/policies/concept_registry.yaml`
- `src/aipinho/services/governance/intent/canonical_intent_router.py`
- `src/aipinho/services/governance/lifecycle/canonical_public_chat_service.py`
- `src/aipinho/services/chat/chat_service.py`
- `tests/unit/test_h1c1_conversation_runtime_truth.py`

## Decisoes arquiteturais

- Nao foi criado classificador paralelo de intent.
- Meta-conversa nasce de conceitos semanticos ja consumidos pelo roteador canonico: estado conversacional e falha de runtime/modelo.
- Intencao informacional sem alvo operacional continua conversa.
- Analise readonly de workspace exige escopo semantico de workspace/projeto/artifact ou pedido explicito de analise.
- Restricao negativa como "nao escrever arquivos" nao vira, sozinha, alvo de analise de workspace.
- `conversation` pode responder texto mesmo com `allowed_actions=[]` e `safe_to_execute=false`.
- Speaker Truth continua impedido de declarar sucesso operacional quando ha apenas resposta conversacional.

## Resultado funcional

Casos cobertos:

- "Quanto e 2+2?" fica `conversation`, sem Task, sem Approval.
- "Como voce confundiu o intent?" vira `conversation_self_diagnosis`, sem workspace analysis.
- "Explique por que voce falhou" vira diagnostico conversacional.
- Premissa falsa de confusao de intent e recusada quando o lifecycle mostra `conversation`.
- Timeout/stderr/saida vazia do modelo speaker vira reason code de modelo/runtime, nao de intent.

Reason codes adicionados no fallback conversacional:

- `MODEL_TIMEOUT`
- `STDERR_CAPTURED`
- `EMPTY_OUTPUT`
- `CONVERSATION_MODEL_UNAVAILABLE`

## Testes executados

```text
python -m pytest tests/unit/test_h1c1_conversation_runtime_truth.py -q
5 passed

python -m pytest tests/unit/test_semantic_intent_resolution_service.py tests/governance/test_g16_legacy_chat_services_folded.py -q
13 passed

python -m pytest tests/unit/test_media_metadata_capability_pack.py tests/unit/test_observation_execution_boundary_service.py -q
17 passed
```

## Fronteira preservada

```text
Prompt
-> Semantic Proposition Normalization
-> Canonical Intent Router
-> Operation Contract
-> Public Chat Rendering
```

Nao houve nova autoridade entre Prompt e Intent. O patch apenas impede que conversa comum ou meta-conversa seja promovida para workspace analysis sem escopo semantico real.

## Proximo passo

Com a boca publica do Runtime mais confiavel, o proximo passo seguro e rerodar o FireTest 5 diagnostico para avaliar H1B2.1/H1B3/H1B4 sem contaminacao conversacional.
