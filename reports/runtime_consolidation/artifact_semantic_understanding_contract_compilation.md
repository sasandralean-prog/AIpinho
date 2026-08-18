# AIpinho - Artifact Semantic Understanding & Contract Compilation

## Objetivo

Esta wave introduziu uma camada canonica de compreensao semantica de artifacts entre o Artifact Runtime e as autoridades existentes de Validation, Completion, Speaker Truth e Runtime Doctor.

O objetivo nao foi fazer um teste especifico passar. O objetivo foi fortalecer genericamente a pergunta:

> O artifact produzido representa corretamente aquilo que afirma representar?

## Resultado

Status: READY

A implementacao manteve o fluxo canonico existente:

Artifact Runtime
-> ArtifactSemanticProfile
-> Validation
-> Completion
-> Speaker Truth
-> Runtime Doctor

Nao foram criados Runtime paralelo, Validation paralela, Speaker Truth paralela, bypass ou regra especifica de FireTest.

## Implementacao Canonica

Foi criado o schema `ArtifactSemanticProfile`, com suporte a:

- contrato declarado;
- tipo/material esperado;
- schema esperado;
- comportamento/semantica/evidencia esperados;
- estado observado;
- gaps semanticos;
- gaps contratuais;
- gaps de consistencia;
- comparacao expected vs observed;
- confidence;
- completeness_score;
- status estruturais separados.

Tambem foi criado `ArtifactSemanticGap` e `SemanticComparison`.

## Contract Compiler

O `ArtifactSemanticContractService` foi evoluido para compilar expectativas genericas a partir de:

- logical path;
- content type;
- declared contract;
- prompts com estruturas genericas do tipo "para cada item registrar" / "for each item record" / "fields".

A decisao continua baseada no contrato declarado e no conteudo observado, nao em dominio especifico.

## Semantic Observer

O observador semantico passou a identificar genericamente:

- documento textual/Markdown;
- colecao tabular;
- dados estruturados JSON;
- archive de evidencias;
- binario opaco.

Archives `.zip` agora sao validados como material real de archive quando o artifact declara `application/zip` ou logical path `.zip`.

## Runtime Integration

O `ArtifactRuntimeService` agora valida semanticamente cada artifact e expõe:

- `semantic_profile`;
- `semantic_gaps`;
- `safe_to_use_as_evidence` somente quando estrutura e semantica passam.

O `ReadonlyAnalysisArtifactRuntimeService` agora:

- compila contrato semantico por artifact solicitado;
- registra contrato em metadata/provenance;
- inclui `artifact_semantic_profile:<logical_path>` em expected outputs;
- bloqueia Completion quando um artifact existe mas nao satisfaz o contrato semantico;
- inclui perfis e gaps em Completion metadata.

## Materializacao Binaria

Foi adicionada compatibilidade generica para artifacts binarios via `encoding` no `ArtifactRuntimeCreateRequest`.

Quando o runtime read-only precisa produzir `application/zip`, ele materializa um archive governado com:

- `manifest.json`;
- `analysis.json`;
- `dependencies.json`.

Isso corrige a incoerencia anterior em que um logical path `.zip` podia ser persistido como texto.

## Runtime Doctor

O Runtime Doctor recebeu checks para detectar:

- Validation PASS com artifact semantico incompleto;
- Completion declarando sucesso apesar de semantic gaps;
- divergencia entre Completion e semantic health.

Reason codes adicionados:

- `ARTIFACT_SEMANTIC_VALIDATION_INCOMPLETE`;
- `COMPLETION_ARTIFACT_SEMANTIC_DIVERGENCE`.

## Correcoes Estruturais Encontradas Durante a Wave

### 1. Proposal-only contaminando mutation intent

Durante os testes verticais, foi detectado que `proposal_only` ainda era tratado como efeito positivo de mutacao. Isso fazia uma fase read-only de planejamento com `patch_preview.md` ser promovida para `patch_request`.

Correção:

- `proposal_only` deixou de compor `positive_mutation_effects`;
- `patch_request` agora exige `state_effect == workspace_mutation`;
- proposal artifacts com proibicao de escrita permanecem read-only/planning.

Essa correcao segue o State Effect Principle e nao depende de frase especifica.

### 2. Falso positivo do scanner de segredo

O registry bloqueava metadata/provenance com chave `path_token_groups`, porque qualquer chave contendo `token` era tratada como segredo.

Correção:

- detecção de segredo por chave passou a usar chaves sensiveis canonicas (`access_token`, `api_key`, `authorization`, `password`, etc.);
- valores continuam sendo escaneados por padroes como `Bearer ...`, `sk-...`, `ghp_...`.

Isso preserva segurança e evita bloquear vocabulário legitimo de contrato.

### 3. Validação semântica degradava binários para texto

O runtime read-only validava semanticamente artifacts usando leitura textual do arquivo local. Archives reais viravam `opaque_binary`.

Correção:

- validação interna passou a chamar `validate_artifact(public_artifact)`;
- o semantic observer agora recebe content type, path e bytes reais.

## Arquivos Alterados

- `src/aipinho/schemas/artifacts/artifact_semantic_profile.py`
- `src/aipinho/schemas/artifacts/artifact_runtime.py`
- `src/aipinho/schemas/artifacts/__init__.py`
- `src/aipinho/services/artifacts/artifact_semantic_contract_service.py`
- `src/aipinho/services/artifacts/artifact_runtime_service.py`
- `src/aipinho/services/events/event_core.py`
- `src/aipinho/services/governance/runtime/readonly_analysis_artifact_runtime_service.py`
- `src/aipinho/services/governance/lifecycle/public_route_lifecycle_service.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `src/aipinho/services/runtime_doctor/runtime_doctor_service.py`
- `src/aipinho/services/semantic_runtime/semantic_proposition_normalization_service.py`
- `src/aipinho/services/governance/intent/canonical_intent_router.py`
- `tests/unit/test_artifact_semantic_contract_service.py`
- `tests/unit/test_artifact_runtime_service.py`
- `tests/unit/test_runtime_doctor_service.py`
- `tests/unit/test_sprint33_event_contract_registry.py`
- `tests/unit/test_semantic_proposition_normalization_service.py`
- `tests/unit/test_semantic_intent_resolution_service.py`

## Validacao Executada

Comandos executados:

```text
python -m pytest tests/governance/test_runtime_vertical_slice.py -q --tb=short
Resultado: 11 passed in 155.70s

python -m pytest tests/unit/test_artifact_semantic_contract_service.py tests/unit/test_artifact_runtime_service.py tests/unit/test_runtime_doctor_service.py tests/unit/test_sprint33_event_contract_registry.py tests/unit/test_semantic_proposition_normalization_service.py tests/unit/test_semantic_intent_resolution_service.py tests/unit/test_intent_classifier.py -q --tb=short
Resultado: 63 passed in 22.11s

python -m py_compile ...arquivos alterados...
Resultado: passed
```

## Compatibilidade

APIs publicas foram preservadas.

O `ArtifactRuntimeCreateRequest` ganhou campo opcional `encoding` com default `text`, preservando consumidores existentes.

O lifecycle publico recebeu ponte de leitura para `artifact_semantic_profile:*`, sem se tornar autoridade semantica.

## Conclusao

A AIpinho agora nao apenas verifica se um artifact existe. Ela passa a construir um perfil semantico do artifact, comparar o que era esperado com o que foi observado, registrar gaps e impedir sucesso quando o artifact materialmente ou semanticamente nao corresponde ao contrato declarado.

Essa wave fortalece a infraestrutura cognitiva da AIpinho de forma generica e reutilizavel para qualquer dominio.
