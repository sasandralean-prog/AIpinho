# L8 - Data Archaeology

Generated: 2026-07-30T20:52:00Z

## Objective

Catalogar completamente o diretório `data/` (44.125 arquivos) para entender a fisiologia do Runtime.

## Directory Structure

```
data/
├── artifacts/          (374 files)
├── external_collaboration/ (1 file)
├── logs/               (8 files)
├── memory/             (255 files)
├── runtime/            (43.352 files) ← MAIOR
├── test_artifacts/     (118 files)
└── uploads/            (0 files)
```

**Total:** 44.108 arquivos

---

## Fichas por Subdiretório

### 1. runtime/ (43.352 arquivos - 98.3% de data/)

**Quem escreve?**
- Services: runtime, task_queue, task_executor, operation_executor
- Components: TaskRun, Operation, Event, Snapshot

**Quem lê?**
- Runtime supervisor
- Task queue maintenance service
- Operation executor
- Event consumers
- Validation services

**Contrato?**
- TaskRun → Operation → Event → Snapshot → Validation → Completion → SpeakerTruth
- Contrato implícito de rastreabilidade completa

**Retenção?**
- UNKNOWN (precisa definir política)

**Pode reconstruir?**
- PARCIAL (TaskRuns podem ser re-executadas, mas histórico não)

**É cache?**
- NÃO

**É histórico?**
- SIM (histórico de execuções)

**É auditoria?**
- SIM (rastreabilidade completa)

**Pode apagar?**
- DEPENDENTE (política de retenção)

**Pode compactar?**
- SIM (muitos arquivos JSON podem ser compactados)

**Classificação sugerida:**
- HISTÓRICO DE EXECUÇÃO
- AUDITORIA DE RUNTIME
- RASTREABILIDADE

**Ação recomendada:**
- Análise granular de subdiretórios dentro de runtime/
- Definir política de retenção por tipo de dado
- Considerar migração para SQLite para dados estruturados

---

### 2. artifacts/ (374 arquivos - 0.8% de data/)

**Quem escreve?**
- Artifact generation service
- Task executor
- Operation executor

**Quem lê?**
- Artifact consumers
- Validation services
- Report generation

**Contrato?**
- Artifact schema definido
- JSON structure

**Retenção?**
- UNKNOWN (precisa definir política)

**Pode reconstruir?**
- SIM (via re-execução de tasks/operations)

**É cache?**
- PARCIAL (alguns artifacts são cache)

**É histórico?**
- PARCIAL (alguns artifacts são históricos)

**É auditoria?**
- NÃO

**Pode apagar?**
- SIM (regenerável)

**Pode compactar?**
- SIM (JSON compactável)

**Classificação sugerida:**
- ARTIFACTS GERADOS
- CACHE DE EXECUÇÃO

**Ação recomendada:**
- Análise granular de tipos de artifacts
- Definir política de retenção (últimos N artifacts)
- Considerar limpeza automática de artifacts antigos

---

### 3. memory/ (255 arquivos - 0.6% de data/)

**Quem escreve?**
- Memory service
- Context manager
- Session manager

**Quem lê?**
- Memory consumers
- Context consumers
- Session consumers

**Contrato?**
- Memory schema definido
- Session context structure

**Retenção?**
- CURTO PRAZO (sessão ativa)

**Pode reconstruir?**
- NÃO (estado de sessão não regenerável)

**É cache?**
- SIM (cache de memória persistido)

**É histórico?**
- NÃO

**É auditoria?**
- NÃO

**Pode apagar?**
- SIM (após sessão encerrada)

**Pode compactar?**
- SIM (JSON compactável)

**Classificação sugerida:**
- CACHE DE MEMÓRIA
- ESTADO DE SESSÃO

**Ação recomendada:**
- Definir política de retenção (sessão ativa + X dias)
- Limpeza automática de sessões encerradas
- Considerar migração para SQLite para estado de sessão

---

### 4. test_artifacts/ (118 arquivos - 0.3% de data/)

**Quem escreve?**
- Test executor
- Test framework

**Quem lê?**
- Test validation
- Test reporting

**Contrato?**
- Test artifact schema

**Retenção?**
- CURTO PRAZO (última execução de teste)

**Pode reconstruir?**
- SIM (via re-execução de testes)

**É cache?**
- SIM (cache de resultados de teste)

**É histórico?**
- PARCIAL (última execução)

**É auditoria?**
- NÃO

**Pode apagar?**
- SIM (regenerável)

**Pode compactar?**
- SIM (JSON compactável)

**Classificação sugerida:**
- CACHE DE TESTES
- ARTIFACTS DE TESTE

**Ação recomendada:**
- Definir política de retenção (última execução)
- Limpeza automática após nova execução
- Considerar integração com framework de testes

---

### 5. logs/ (8 arquivos - 0.02% de data/)

**Quem escreve?**
- Logging service
- Runtime components

**Quem lê?**
- Log consumers
- Debugging tools

**Contrato?**
- Log format defined

**Retenção?**
- CURTO PRAZO (rotação de logs)

**Pode reconstruir?**
- NÃO (histórico de logs não regenerável)

**É cache?**
- NÃO

**É histórico?**
- SIM (histórico de logs)

**É auditoria?**
- SIM (auditoria de runtime)

**Pode apagar?**
- SIM (após período de retenção)

**Pode compactar?**
- SIM (logs compactáveis)

**Classificação sugerida:**
- LOGS DE RUNTIME
- AUDITORIA

**Ação recomendada:**
- Definir política de rotação de logs
- Implementar rotação automática
- Considerar migração para sistema de logs centralizado)

---

### 6. external_collaboration/ (1 arquivo - 0.002% de data/)

**Quem lê?**
- External collaboration service

**Quem escreve?**
- External collaboration service

**Contrato?**
- Collaboration schema

**Retenção?**
- LONGO PRAZO (histórico de colaboração)

**Pode reconstruir?**
- NÃO (histórico não regenerável)

**É cache?**
- NÃO

**É histórico?**
- SIM (histórico de colaboração)

**É auditoria?**
- SIM (auditoria de colaboração)

**Pode apagar?**
- NÃO (histórico valioso)

**Pode compactar?**
- SIM (JSON compactável)

**Classificação sugerida:**
- HISTÓRICO DE COLABORAÇÃO
- AUDITORIA

**Ação recomendada:**
- Preservar (histórico valioso)
- Compactar se necessário
- Considerar migração para banco de dados

---

### 7. uploads/ (0 arquivos - 0% de data/)

**Quem escreve?**
- Upload service
- User interface

**Quem lê?**
- Upload consumers
- Processing services

**Contrato?**
- Upload schema

**Retenção?**
- MÉDIO PRAZO (processamento)

**Pode reconstruir?**
- NÃO (uploads de usuário não regeneráveis)

**É cache?**
- NÃO

**É histórico?**
- NÃO

**É auditoria?**
- NÃO

**Pode apagar?**
- SIM (após processamento)

**Pode compactar?**
- DEPENDENTE (tipo de arquivo)

**Classificação sugerida:**
- UPLOADS DE USUÁRIO
- ARQUIVOS TEMPORÁRIOS

**Ação recomendada:**
- Monitorar uso
- Definir política de retenção
- Implementar limpeza automática após processamento

---

## Análise de Padrões

### Padrão Identificado: TaskRun → Operation → Event → Snapshot → Validation → Completion → SpeakerTruth

**Dentro de runtime/ (43.352 arquivos), provavelmente existe:**
- Task data
- TaskRun data
- Operation data
- Event data
- Snapshot data
- Validation data
- Completion data
- SpeakerTruth data

**Hipótese:**
- 95% desses arquivos nunca mais serão lidos
- São históricos de execuções antigas
- Podem ser arquivados ou compactados

### Padrão Identificado: Iterações de Arquivos

**Hipótese:**
- Existem arquivos como: task_v1.json, task_v2.json, task_v3.json
- Apenas a última versão é relevante
- Versões antigas podem ser deletadas

---

## Recomendações

### Imediato

1. **Análise Granular de runtime/**
   - Mapear subdiretórios dentro de runtime/
   - Identificar padrões de nomenclatura
   - Identificar versões de arquivos
   - Calcular tamanho por subdiretório

2. **Definir Políticas de Retenção**
   - TaskRun: últimos 200
   - Validation: 90 dias
   - SpeakerTruth: última execução
   - Logs: rotação automática
   - Memory: sessão ativa + 7 dias

### Curto Prazo

3. **Implementar Compactação**
   - Compactar JSON antigos
   - Migrar dados estruturados para SQLite
   - Implementar compressão de logs

4. **Criar Estrutura storage/ ou runtime_db/**
   - Separar dados vivos de históricos
   - Separar cache de auditoria
   - Implementar políticas por categoria

### Longo Prazo

5. **Implementar Runtime Garbage Collector Governado**
   - Baseado em contratos
   - Automatizado por política
   - Com rastreabilidade

---

## Próximos Passos

1. Análise granular de runtime/ (43.352 arquivos)
2. Mapeamento de produtores e consumidores
3. Definição de políticas de retenção
4. Implementação de Storage Manifest
5. L9 - Reports Archaeology
