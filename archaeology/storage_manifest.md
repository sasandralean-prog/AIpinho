# Storage Manifest

Generated: 2026-07-30T20:52:00Z

## Purpose

Consolidar categorias, produtores, consumidores e políticas de retenção para todos os dados do Runtime AIpinho.

## Storage Categories

### 1. DADOS VIVOS (LIVE DATA)

**Definição:** Dados que são ativamente usados pelo Runtime e não podem ser deletados sem impacto.

**Subcategorias:**
- **SESSION_STATE** (memory/): Estado de sessão ativa
- **USER_UPLOADS** (uploads/): Uploads de usuário em processamento
- **ACTIVE_TASKS** (runtime/tasks/): Tasks ativas
- **ACTIVE_OPERATIONS** (runtime/operations/): Operations ativas

**Política de Retenção:**
- SESSION_STATE: Sessão ativa + 7 dias
- USER_UPLOADS: Processamento + 1 dia
- ACTIVE_TASKS: Task ativa
- ACTIVE_OPERATIONS: Operation ativa

**Ação:** PRESERVAR

---

### 2. HISTÓRICO DE EXECUÇÃO (EXECUTION HISTORY)

**Definição:** Dados históricos de execuções do Runtime, usados para auditoria e rastreabilidade.

**Subcategorias:**
- **TASKRUN_HISTORY** (runtime/taskruns/): Histórico de TaskRuns
- **OPERATION_HISTORY** (runtime/operations/): Histórico de Operations
- **EVENT_HISTORY** (runtime/events/): Histórico de Events
- **SNAPSHOT_HISTORY** (runtime/snapshots/): Histórico de Snapshots
- **VALIDATION_HISTORY** (runtime/validation/): Histórico de Validations
- **COMPLETION_HISTORY** (runtime/completion/): Histórico de Completions
- **SPEAKER_TRUTH_HISTORY** (runtime/speaker_truth/): Histórico de SpeakerTruth

**Política de Retenção:**
- TASKRUN_HISTORY: Últimos 200
- OPERATION_HISTORY: 90 dias
- EVENT_HISTORY: 90 dias
- SNAPSHOT_HISTORY: 30 dias
- VALIDATION_HISTORY: 90 dias
- COMPLETION_HISTORY: 90 dias
- SPEAKER_TRUTH_HISTORY: Última execução

**Ação:** ARQUIVAR (após período de retenção)

---

### 3. CACHE (CACHE)

**Definição:** Dados regeneráveis que podem ser deletados sem impacto.

**Subcategorias:**
- **ARTIFACT_CACHE** (data/artifacts/): Cache de artifacts
- **TEST_ARTIFACT_CACHE** (data/test_artifacts/): Cache de artifacts de teste
- **MEMORY_CACHE** (data/memory/): Cache de memória persistido
- **PYTHON_CACHE** (__pycache__/): Cache de Python
- **BUILD_CACHE** (build/, dist/): Cache de build

**Política de Retenção:**
- ARTIFACT_CACHE: Últimos 100
- TEST_ARTIFACT_CACHE: Última execução
- MEMORY_CACHE: Sessão ativa + 7 dias
- PYTHON_CACHE: Imediato
- BUILD_CACHE: Imediato

**Ação:** DELETAR (após período de retenção)

---

### 4. AUDITORIA (AUDIT)

**Definição:** Dados de auditoria usados para compliance e rastreabilidade.

**Subcategorias:**
- **RUNTIME_LOGS** (data/logs/): Logs de runtime
- **GOVERNANCE_REPORTS** (reports/governance_block_*/): Relatórios de governança
- **HOTFIX_REPORTS** (reports/hotfixes/): Relatórios de hotfix
- **DIAGNOSTIC_REPORTS** (reports/diagnostics/): Relatórios de diagnóstico
- **HEALTH_REPORTS** (reports/health/): Relatórios de saúde

**Política de Retenção:**
- RUNTIME_LOGS: Rotação automática (últimos 7 dias)
- GOVERNANCE_REPORTS: Últimos 3 sprints
- HOTFIX_REPORTS: Últimos 6 meses
- DIAGNOSTIC_REPORTS: Últimos 30 dias
- HEALTH_REPORTS: Últimos 7 dias

**Ação:** ARQUIVAR (após período de retenção)

---

### 5. DOCUMENTAÇÃO (DOCUMENTATION)

**Definição:** Documentação técnica e histórica do projeto.

**Subcategorias:**
- **DISCOVERY_DOCS** (reports/discovery/): Documentação de descoberta
- **ENGINEERING_EVOLUTION** (reports/engineering_evolution/): Evolução da engenharia
- **KERNEL_REPORTS** (reports/kernel/): Relatórios de kernel
- **MULTI_AGENT_REPORTS** (reports/multi_agent/): Relatórios de multi-agent

**Política de Retenção:**
- DISCOVERY_DOCS: PRESERVAR (documentação valiosa)
- ENGINEERING_EVOLUTION: PRESERVAR (documentação valiosa)
- KERNEL_REPORTS: PRESERVAR (documentação valiosa)
- MULTI_AGENT_REPORTS: PRESERVAR (documentação valiosa)

**Ação:** PRESERVAR

---

### 6. COLABORAÇÃO EXTERNA (EXTERNAL COLLABORATION)

**Definição:** Dados de colaboração externa com parceiros.

**Subcategorias:**
- **EXTERNAL_COLLABORATION** (data/external_collaboration/): Dados de colaboração

**Política de Retenção:**
- EXTERNAL_COLLABORATION: LONGO PRAZO (histórico valioso)

**Ação:** PRESERVAR

---

### 7. BASELINES (BASELINES)

**Definição:** Baselines de teste e referências de performance.

**Subcategorias:**
- **TEST_BASELINES** (reports/baselines/): Baselines de teste

**Política de Retenção:**
- TEST_BASELINES: Últimos 10

**Ação:** ARQUIVAR (baselines antigos)

---

## Storage Structure Proposal

### Estrutura Atual

```
data/
├── artifacts/
├── external_collaboration/
├── logs/
├── memory/
├── runtime/
├── test_artifacts/
└── uploads/

reports/
├── governance_block_*/
├── hotfixes/
├── discovery/
├── engineering_evolution/
├── diagnostics/
├── kernel/
├── multi_agent/
├── health/
├── baselines/
└── [40+ subdiretórios]
```

### Estrutura Proposta: storage/

```
storage/
├── live/                    # DADOS VIVOS
│   ├── session_state/
│   ├── user_uploads/
│   ├── active_tasks/
│   └── active_operations/
├── history/                 # HISTÓRICO DE EXECUÇÃO
│   ├── taskruns/
│   ├── operations/
│   ├── events/
│   ├── snapshots/
│   ├── validation/
│   ├── completion/
│   └── speaker_truth/
├── cache/                   # CACHE
│   ├── artifacts/
│   ├── test_artifacts/
│   ├── memory/
│   ├── python/
│   └── build/
├── audit/                   # AUDITORIA
│   ├── logs/
│   ├── governance/
│   ├── hotfixes/
│   ├── diagnostics/
│   └── health/
├── docs/                    # DOCUMENTAÇÃO
│   ├── discovery/
│   ├── engineering_evolution/
│   ├── kernel/
│   └── multi_agent/
├── collaboration/           # COLABORAÇÃO EXTERNA
│   └── external/
└── baselines/               # BASELINES
    └── test/
```

## Runtime Garbage Collector Governado

### Contratos de Retenção

**Contrato TaskRun:**
```
TaskRun
↓
últimos 200
↓
resto
↓
archive
```

**Contrato Validation:**
```
Validation
↓
90 dias
↓
archive
```

**Contrato SpeakerTruth:**
```
SpeakerTruth
↓
última execução
↓
resto
↓
delete
```

**Contrato Logs:**
```
Logs
↓
rotação automática (últimos 7 dias)
↓
delete
```

**Contrato Governance:**
```
Governance
↓
últimos 3 sprints
↓
archive
```

### Implementação

**Componentes:**
1. **Storage Policy Service:** Define políticas de retenção por categoria
2. **Garbage Collector Service:** Executa limpeza baseada em políticas
3. **Archive Service:** Move dados para arquivo
4. **Retention Monitor:** Monitora compliance de retenção

**Governance:**
- Todas as decisões de deleção são pre-registradas
- Nenhuma decisão heurística durante execução
- Rastreabilidade completa de todas as ações
- Rollback possível para todas as ações

## Próximos Passos

1. Criar estrutura storage/
2. Migrar dados existentes para nova estrutura
3. Implementar Storage Policy Service
4. Implementar Garbage Collector Service
5. Implementar Archive Service
6. Implementar Retention Monitor
7. Testar Runtime Garbage Collector Governado
