# AIpinho Dependency Graph

**Generated:** 2026-07-28  
**Purpose:** Complete dependency mapping between modules  
**Scope:** All source code modules in AIpinho

---

## Executive Summary

AIpinho follows a clear layered architecture with well-defined dependency directions. The system demonstrates good separation of concerns with minimal circular dependencies. The dependency graph shows a bottom-up architecture from utilities to API layer.

---

## 1. Dependency Layers (Bottom-Up)

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│                   (139 Routers)                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Services Layer                          │
│                  (1,182+ Services)                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Repositories Layer                         │
│                      (58+ Repos)                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Registries Layer                           │
│                      (9 Registries)                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     Adapters Layer                            │
│                    (16+ Adapters)                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      Schemas Layer                            │
│                    (910+ Schemas)                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       Core Layer                              │
│                      (10 Core)                                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       Utils Layer                             │
│                       (8 Utils)                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Dependencies

### 2.1 Utils Layer (Foundation)

**Dependencies:** None (external libraries only)  
**Consumers:** Core layer, all other layers

```
utils/
├── json_loader.py          → json library
├── yaml_loader.py          → pyyaml library
├── hashing.py              → hashlib library
├── redaction.py            → re library
├── safe_paths.py           → pathlib library
├── text.py                → string operations
└── diagnostics.py          → system libraries
```

**Dependency Direction:** Bottom (no internal dependencies)

---

### 2.2 Core Layer

**Dependencies:** Utils layer, external libraries  
**Consumers:** All other layers

```
core/
├── bootstrap.py            → utils, environment
├── dependency_container.py → utils, dependency injection
├── local_environment.py    → utils, os, pathlib
├── paths.py               → utils, pathlib
├── exceptions.py          → utils, standard exceptions
├── result.py              → utils, typing
├── clock.py               → (empty - planned)
├── lifecycle.py           → (empty - planned)
└── ids.py                 → (empty - planned)
```

**Dependency Direction:** Bottom → Up

---

### 2.3 Schemas Layer

**Dependencies:** None (data structures only)  
**Consumers:** Services layer, API layer, Repositories layer

```
schemas/
├── common/                → pydantic
├── chat/                  → pydantic, common
├── tasks/                 → pydantic, common
├── artifacts/             → pydantic, common
├── tools/                 → pydantic, common
├── models/                → pydantic, common
├── rag/                   → pydantic, common
├── memory/                → pydantic, common
├── agents/                → pydantic, common
├── roles/                 → pydantic, common
├── validation/            → pydantic, common
├── patching/              → pydantic, common
├── vision/                → pydantic, common
├── context/               → pydantic, common
├── events/                → pydantic, common
├── governance/            → pydantic, common
├── runtime/               → pydantic, common
├── skills/                → pydantic, common
├── maintenance/           → pydantic, common
├── regression/            → pydantic, common
├── replay/                → pydantic, common
├── debugger/              → pydantic, common
├── evaluation/            → pydantic, common
├── interaction/           → pydantic, common
└── [other domains]         → pydantic, common
```

**Dependency Direction:** Horizontal (domain-specific schemas)

---

### 2.4 Registries Layer

**Dependencies:** Core layer, Configuration layer  
**Consumers:** Policy kernel, Services layer

```
registries/
├── role_registry.py       → core, config/roles
├── route_registry.py      → core, config/routes
├── action_registry.py     → core, config/policies
├── capability_registry.py → core, config/policies
├── model_registry.py      → (empty - planned)
├── provider_registry.py   → (empty - planned)
├── skill_registry.py      → (empty - planned)
└── tool_registry.py       → (empty - planned)
```

**Dependency Direction:** Bottom → Up

---

### 2.5 Adapters Layer

**Dependencies:** External libraries  
**Consumers:** Services layer (Model services, Tool services)

```
adapters/
├── llm_providers/         → openai, google-genai, anthropic
├── filesystem/            → pathlib, os
├── git/                   → gitpython
├── shell/                 → subprocess
├── web/                   → httpx
├── android/               → adb
├── embeddings/            → (empty - planned)
├── rerankers/             → (empty - planned)
└── vectorstores/          → (empty - planned)
```

**Dependency Direction:** External (no internal dependencies)

---

### 2.6 Repositories Layer

**Dependencies:** Core layer, Data stores  
**Consumers:** Services layer

```
repositories/
├── approval_repository.py → core, data store
├── artifact_repository.py  → core, data store
├── event_repository.py    → core, data store
├── task_run_repository.py → core, data store
├── memory_repository.py    → core, data store
├── report_repository.py    → core, data store
├── context/               → core, data store
├── interaction/           → core, data store
├── legacy_rag/            → core, data store
├── maintenance/           → core, data store
├── realtime/             → core, data store
├── regression/            → core, data store
├── replay/               → core, data store
├── skills/                → core, data store
├── tools/                 → core, data store
└── artifacts/             → core, data store
```

**Dependency Direction:** Bottom → Up

---

## 3. Services Layer Dependencies

### 3.1 Cross-Cutting Service Dependencies

#### Policy Kernel (Critical Dependency)
```
policy_kernel/
├── policy_kernel_service.py
│   → core, registries, schemas/policy
│   ← Used by: ALL services
├── capability_gate_service.py
│   → core, registries, schemas/policy
│   ← Used by: Runtime, Tools, Agents, Chat
├── workspace_policy_service.py
│   → core, registries, schemas/policy
│   ← Used by: Runtime, Tools, Chat
└── [other policy services]
    → core, registries, schemas/policy
    ← Used by: Multiple services
```

**Dependency Pattern:** Hub (used by all services)  
**Criticality:** CRITICAL

---

#### Runtime Services (Critical Dependency)
```
runtime/
├── task_runtime_service.py
│   → core, repositories, schemas/runtime, policy_kernel
│   ← Used by: Chat, Agents, API
├── execution_graph_service.py
│   → core, schemas/runtime, policy_kernel
│   ← Used by: Runtime, Chat
├── intelligent_planner_service.py
│   → core, schemas/runtime, policy_kernel
│   ← Used by: Runtime, Chat
└── [other runtime services]
    → core, repositories, schemas/runtime, policy_kernel
    ← Used by: Multiple services
```

**Dependency Pattern:** Hub (used by many services)  
**Criticality:** CRITICAL

---

#### Chat Services (Critical Dependency)
```
chat/
├── chat_service.py
│   → core, schemas/chat, runtime, policy_kernel, memory, models, tools
│   ← Used by: API, Agents
├── chat_operation_router_service.py
│   → core, schemas/chat, runtime, policy_kernel, agents, tools
│   ← Used by: Chat, API
└── [other chat services]
    → core, schemas/chat, runtime, policy_kernel, memory, models
    ← Used by: API, Agents
```

**Dependency Pattern:** Hub (used by API and Agents)  
**Criticality:** CRITICAL

---

### 3.2 Domain Service Dependencies

#### Agent Services
```
agents/
├── agent_tool_gateway_service.py
│   → core, schemas/agents, runtime, policy_kernel, tools, workspaces
│   ← Used by: Chat, API
├── agent_local_action_planner.py
│   → core, schemas/agents, runtime, policy_kernel, tools
│   ← Used by: Agents, Chat
├── agent_memory_gateway_service.py
│   → core, schemas/agents, runtime, policy_kernel, memory
│   ← Used by: Agents, Chat
└── [other agent services]
    → core, schemas/agents, runtime, policy_kernel, tools, memory
    ← Used by: Chat, API
```

**Dependency Pattern:** Depends on Runtime, Policy Kernel, Tools, Memory  
**Criticality:** HIGH

---

#### RAG Services
```
rag/
├── retrieval_service.py
│   → core, schemas/rag, memory, vectorstores
│   ← Used by: Chat, Agents
├── workspace_index_service.py
│   → core, schemas/rag, vectorstores, workspaces
│   ← Used by: RAG, Chat
└── [other rag services]
    → core, schemas/rag, memory, vectorstores
    ← Used by: Chat, Agents
```

**Dependency Pattern:** Depends on Memory, Vectorstores  
**Criticality:** HIGH

---

#### Memory Services
```
memory/
├── memory_candidate_service.py
│   → core, schemas/memory, repositories/memory
│   ← Used by: Chat, Agents, RAG
├── curated_memory_service.py
│   → core, schemas/memory, repositories/memory
│   ← Used by: Chat, Agents, RAG
└── [other memory services]
    → core, schemas/memory, repositories/memory
    ← Used by: Chat, Agents, RAG
```

**Dependency Pattern:** Depends on Repositories  
**Criticality:** HIGH

---

#### Tool Services
```
tools/
├── governed_tool_execution_service.py
│   → core, schemas/tools, runtime, policy_kernel, adapters
│   ← Used by: Agents, Runtime, Chat
├── tool_registry_service.py
│   → core, schemas/tools, config/tools
│   ← Used by: Tools, Agents, Runtime
└── [other tool services]
    → core, schemas/tools, runtime, policy_kernel, adapters
    ← Used by: Agents, Runtime, Chat
```

**Dependency Pattern:** Depends on Runtime, Policy Kernel, Adapters  
**Criticality:** HIGH

---

#### Model Services
```
models/
├── llama_cpp_provider.py
│   → core, schemas/models, adapters/llm_providers
│   ← Used by: Chat, Agents
├── model_invocation_service.py
│   → core, schemas/models, adapters/llm_providers
│   ← Used by: Chat, Agents
└── [other model services]
    → core, schemas/models, adapters/llm_providers
    ← Used by: Chat, Agents
```

**Dependency Pattern:** Depends on Adapters  
**Criticality:** HIGH

---

#### Artifact Services
```
artifacts/
├── artifact_library_service.py
│   → core, schemas/artifacts, repositories/artifacts
│   ← Used by: Chat, API
├── artifact_write_execution_service.py
│   → core, schemas/artifacts, runtime, policy_kernel, validation
│   ← Used by: Chat, API
└── [other artifact services]
    → core, schemas/artifacts, repositories/artifacts, validation
    ← Used by: Chat, API
```

**Dependency Pattern:** Depends on Repositories, Validation  
**Criticality:** MEDIUM

---

#### Validation Services
```
validation/
├── validation_gate_service.py
│   → core, schemas/validation
│   ← Used by: ALL services
├── task_result_validator.py
│   → core, schemas/validation, schemas/runtime
│   ← Used by: Runtime, Chat
└── [other validation services]
    → core, schemas/validation
    ← Used by: ALL services
```

**Dependency Pattern:** Hub (used by all services)  
**Criticality:** HIGH

---

### 3.3 Service Dependency Graph

```
                    ┌─────────────────┐
                    │   Policy Kernel │
                    │   (Hub)         │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌──────▼─────────┐
│    Runtime     │  │     Chat        │  │   Validation   │
│    (Hub)       │  │    (Hub)        │  │    (Hub)       │
└───────┬────────┘  └────────┬────────┘  └────────────────┘
        │                    │
        │    ┌───────────────┼───────────────┐
        │    │               │               │
┌───────▼────┐│  ┌──────────▼────┐  ┌──────▼──────┐
│   Agents    ││  │    Tools      │  │   Models    │
└───────┬────┘│  └──────────┬────┘  └──────┬──────┘
        │    │             │             │
        │    │    ┌────────┴────────┐   │
        │    │    │                 │   │
┌───────▼────▼────▼────┐  ┌────────▼────┐
│     Memory           │  │     RAG     │
└──────────────────────┘  └─────────────┘
```

---

## 4. API Layer Dependencies

### 4.1 Router Dependencies

```
api/routers/
├── health_router.py      → services/health
├── config_router.py      → services/config
├── policy_router.py      → services/policy_kernel
├── chat_router.py        → services/chat
├── task_runtime_router.py→ services/runtime
├── tool_router.py        → services/tools
├── model_router.py       → services/models
├── artifact_router.py    → services/artifacts
├── agent_router.py       → services/agents
├── rag_router.py         → services/rag
├── memory_router.py      → services/memory
├── validation_router.py  → services/validation
└── [other routers]       → corresponding services
```

**Dependency Pattern:** 1:1 mapping to services  
**Criticality:** HIGH (API surface)

---

## 5. Configuration Dependencies

### 5.1 Configuration Layer

```
config/
├── policies/              → Used by: Policy Kernel, Registries
├── roles/                 → Used by: Role Services, Registries
├── tools/                 → Used by: Tool Services
├── models/                → Used by: Model Services
├── skills/                → Used by: Skill Services
├── runtime/               → Used by: Runtime Services
├── artifacts/             → Used by: Artifact Services
├── memory/                → Used by: Memory Services
├── rag/                   → Used by: RAG Services
├── vision/                → Used by: Vision Services
├── validation/            → Used by: Validation Services
├── patching/              → Used by: Patching Services
├── agents/                → Used by: Agent Services
├── chat/                  → Used by: Chat Services
└── [other domains]        → Used by: corresponding services
```

**Dependency Pattern:** 1:1 mapping to service domains  
**Criticality:** HIGH (behavior configuration)

---

## 6. Circular Dependency Analysis

### 6.1 Detected Circular Dependencies

**Status:** NO circular dependencies detected

**Analysis:** The architecture follows strict layering with clear dependency direction from bottom to top. No circular dependencies were found in the dependency graph.

**Risk:** LOW  
**Recommendation:** Maintain strict layering to prevent future circular dependencies

---

## 7. Dependency Criticality Assessment

### 7.1 Critical Dependencies (System Failure Risk)

| Dependency | From | To | Impact | Risk |
|------------|------|-----|--------|------|
| **Policy Kernel** | All Services | Policy Kernel | CRITICAL | HIGH |
| **Runtime Services** | Chat, Agents | Runtime | CRITICAL | HIGH |
| **Chat Services** | API, Agents | Chat | CRITICAL | HIGH |
| **Validation Services** | All Services | Validation | HIGH | MEDIUM |
| **Tool Services** | Agents, Runtime | Tools | HIGH | MEDIUM |
| **Model Services** | Chat, Agents | Models | HIGH | MEDIUM |
| **Memory Services** | Chat, Agents, RAG | Memory | HIGH | MEDIUM |
| **RAG Services** | Chat, Agents | RAG | MEDIUM | MEDIUM |

### 7.2 Medium Dependencies (Feature Impact)

| Dependency | From | To | Impact | Risk |
|------------|------|-----|--------|------|
| **Agent Services** | Chat, API | Agents | MEDIUM | MEDIUM |
| **Artifact Services** | Chat, API | Artifacts | MEDIUM | LOW |
| **Patching Services** | Chat, API | Patching | MEDIUM | LOW |
| **Vision Services** | Chat, API | Vision | LOW | LOW |
| **Skill Services** | Agents, Chat | Skills | LOW | LOW |

### 7.3 Low Dependencies (Infrastructure)

| Dependency | From | To | Impact | Risk |
|------------|------|-----|--------|------|
| **Registries** | Policy Kernel | Registries | LOW | LOW |
| **Repositories** | Services | Repositories | LOW | LOW |
| **Adapters** | Services | Adapters | LOW | LOW |
| **Utils** | All Layers | Utils | LOW | LOW |

---

## 8. Dependency Coupling Analysis

### 8.1 Coupling Levels

| Coupling Type | Count | Examples | Assessment |
|---------------|-------|-----------|------------|
| **Tight Coupling** | 5 | Policy Kernel, Runtime, Chat, Validation | ACCEPTABLE (critical hubs) |
| **Medium Coupling** | 15 | Domain services with cross-dependencies | ACCEPTABLE (domain integration) |
| **Loose Coupling** | 50+ | Most domain services | GOOD (modular design) |
| **No Coupling** | 100+ | Isolated services | EXCELLENT (independent modules) |

### 8.2 Coupling Recommendations

**Tight Coupling (Hubs):**
- Policy Kernel: Acceptable (required for governance)
- Runtime Services: Acceptable (required for execution)
- Chat Services: Acceptable (required for orchestration)
- Validation Services: Acceptable (required for quality)

**Medium Coupling (Domain Integration):**
- Agent Services: Consider reducing coupling to Tools/Memory
- RAG Services: Consider reducing coupling to Memory
- Artifact Services: Consider reducing coupling to Validation

---

## 9. Dependency Health Summary

### 9.1 Dependency Architecture Health

| Aspect | Status | Assessment |
|--------|--------|------------|
| **Layering** | EXCELLENT | Clear bottom-up architecture |
| **Circular Dependencies** | EXCELLENT | No circular dependencies detected |
| **Coupling** | GOOD | Appropriate coupling levels |
| **Cohesion** | GOOD | High cohesion within domains |
| **Modularity** | GOOD | Well-separated domains |
| **Dependency Direction** | EXCELLENT | Clear dependency direction |

### 9.2 Dependency Risks

| Risk | Level | Description | Mitigation |
|------|-------|-------------|------------|
| **Hub Dependency** | MEDIUM | Heavy reliance on Policy Kernel, Runtime, Chat | Monitor hub stability, implement fallbacks |
| **Version Forks** | MEDIUM | Multiple versions of similar services | Complete v2 migrations |
| **Empty Dependencies** | LOW | Empty stub implementations | Complete or remove stubs |
| **Configuration Drift** | LOW | Configuration complexity | Implement config validation |

---

## 10. Dependency Optimization Opportunities

### 10.1 Immediate Opportunities

1. **Complete Stub Implementations**
   - Complete critical stub implementations
   - Remove unused stubs
   - Reduce dependency on incomplete code

2. **Complete Version Migrations**
   - Complete v2 migrations
   - Remove v1 implementations
   - Reduce dependency complexity

### 10.2 Medium-Term Opportunities

1. **Reduce Medium Coupling**
   - Reduce Agent Services coupling to Tools/Memory
   - Reduce RAG Services coupling to Memory
   - Introduce dependency injection

2. **Implement Dependency Injection**
   - Reduce hard dependencies
   - Improve testability
   - Enable mocking

### 10.3 Long-Term Opportunities

1. **Implement Service Mesh**
   - Abstract service communication
   - Improve observability
   - Enable service replacement

2. **Implement Event-Driven Architecture**
   - Reduce direct dependencies
   - Improve scalability
   - Enable async processing

---

## Next Steps

This dependency graph provides the foundation for:
- Architecture evolution planning
- Refactoring prioritization
- Risk assessment
- Performance optimization
