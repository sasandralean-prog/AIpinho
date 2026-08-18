# AIpinho Critical Modules

**Generated:** 2026-07-28  
**Purpose:** Identification and analysis of critical system modules  
**Scope:** All source code modules in AIpinho

---

## Executive Summary

AIpinho has a well-defined set of critical modules that form the foundation of the system. These modules are essential for system operation and require special attention for maintenance, testing, and evolution.

---

## 1. Critical Module Classification

### 1.1 Criticality Levels

| Level | Definition | Count | Impact |
|-------|-------------|-------|--------|
| **CRITICAL** | System failure if module fails | 15 | System-wide impact |
| **HIGH** | Major feature impact if module fails | 45 | Feature-wide impact |
| **MEDIUM** | Minor feature impact if module fails | 150 | Localized impact |
| **LOW** | Minimal impact if module fails | 500+ | Negligible impact |

---

## 2. CRITICAL Modules (System Failure Risk)

### 2.1 Core Infrastructure

#### `src/aipinho/main.py`
- **Size:** 103 bytes
- **Purpose:** FastAPI application entrypoint
- **Dependencies:** `app_factory.py`
- **Consumers:** External API clients
- **Failure Impact:** CRITICAL - System cannot start
- **Backup:** None (single entrypoint)
- **Recommendation:** Implement fallback entrypoint

---

#### `src/aipinho/app_factory.py`
- **Size:** 1,039 bytes
- **Purpose:** FastAPI application factory
- **Dependencies:** `core/`, `api/routers/`, `services/`
- **Consumers:** `main.py`
- **Failure Impact:** CRITICAL - System cannot initialize
- **Backup:** None (single factory)
- **Recommendation:** Implement factory fallback

---

#### `src/aipinho/core/bootstrap.py`
- **Size:** 194 bytes
- **Purpose:** Application bootstrap
- **Dependencies:** `core/local_environment.py`
- **Consumers:** All modules
- **Failure Impact:** CRITICAL - System cannot bootstrap
- **Backup:** None (single bootstrap)
- **Recommendation:** Complete implementation

---

#### `src/aipinho/core/dependency_container.py`
- **Size:** 1,161 bytes
- **Purpose:** Dependency injection container
- **Dependencies:** `core/`
- **Consumers:** All services
- **Failure Impact:** CRITICAL - Dependency injection fails
- **Backup:** None (single container)
- **Recommendation:** Implement container fallback

---

#### `src/aipinho/core/local_environment.py`
- **Size:** 1,299 bytes
- **Purpose:** Environment configuration
- **Dependencies:** `utils/`
- **Consumers:** All modules
- **Failure Impact:** CRITICAL - Environment configuration fails
- **Backup:** None (single environment loader)
- **Recommendation:** Implement environment fallback

---

### 2.2 Policy Kernel

#### `src/aipinho/services/policy_kernel/policy_kernel_service.py`
- **Size:** 8,747 bytes
- **Purpose:** Core policy resolution and enforcement
- **Dependencies:** `core/`, `registries/`, `schemas/policy/`
- **Consumers:** ALL services (hub dependency)
- **Failure Impact:** CRITICAL - All policy decisions fail
- **Backup:** None (single policy kernel)
- **Recommendation:** Implement policy kernel fallback

---

#### `src/aipinho/services/policy_kernel/capability_gate_service.py`
- **Size:** 7,979 bytes
- **Purpose:** Capability gating and enforcement
- **Dependencies:** `core/`, `registries/`, `schemas/policy/`
- **Consumers:** Runtime, Tools, Agents, Chat
- **Failure Impact:** CRITICAL - All capability checks fail
- **Backup:** None (single capability gate)
- **Recommendation:** Implement capability gate fallback

---

#### `src/aipinho/services/policy_kernel/workspace_role_contract_service.py`
- **Size:** 13,006 bytes
- **Purpose:** Workspace role contract management
- **Dependencies:** `core/`, `registries/`, `schemas/policy/`
- **Consumers:** Runtime, Tools, Chat
- **Failure Impact:** CRITICAL - Workspace access control fails
- **Backup:** None (single contract service)
- **Recommendation:** Implement contract service fallback

---

### 2.3 Runtime Services

#### `src/aipinho/services/runtime/task_runtime_service.py`
- **Size:** 44,751 bytes
- **Purpose:** Core task runtime orchestration
- **Dependencies:** `core/`, `repositories/`, `schemas/runtime/`, `policy_kernel/`
- **Consumers:** Chat, Agents, API
- **Failure Impact:** CRITICAL - Task execution fails
- **Backup:** None (single task runtime)
- **Recommendation:** Implement task runtime fallback

---

#### `src/aipinho/services/runtime/execution_graph_service.py`
- **Size:** 36,208 bytes
- **Purpose:** Execution graph management
- **Dependencies:** `core/`, `schemas/runtime/`, `policy_kernel/`
- **Consumers:** Runtime, Chat
- **Failure Impact:** CRITICAL - Execution planning fails
- **Backup:** None (single execution graph service)
- **Recommendation:** Implement execution graph fallback

---

#### `src/aipinho/services/runtime/intelligent_planner_service.py`
- **Size:** 21,690 bytes
- **Purpose:** Intelligent task planning
- **Dependencies:** `core/`, `schemas/runtime/`, `policy_kernel/`
- **Consumers:** Runtime, Chat
- **Failure Impact:** CRITICAL - Task planning fails
- **Backup:** None (single planner)
- **Recommendation:** Implement planner fallback

---

### 2.4 Chat Services

#### `src/aipinho/services/chat/chat_service.py`
- **Size:** 187,503 bytes
- **Purpose:** Core chat orchestration
- **Dependencies:** `core/`, `schemas/chat/`, `runtime/`, `policy_kernel/`, `memory/`, `models/`, `tools/`
- **Consumers:** API, Agents
- **Failure Impact:** CRITICAL - Chat functionality fails
- **Backup:** None (single chat service)
- **Recommendation:** Implement chat service fallback

---

#### `src/aipinho/services/chat/chat_operation_router_service.py`
- **Size:** 75,664 bytes
- **Purpose:** Chat operation routing
- **Dependencies:** `core/`, `schemas/chat/`, `runtime/`, `policy_kernel/`, `agents/`, `tools/`
- **Consumers:** Chat, API
- **Failure Impact:** CRITICAL - Chat operations fail
- **Backup:** None (single operation router)
- **Recommendation:** Implement operation router fallback

---

### 2.5 Agent Services

#### `src/aipinho/services/agents/agent_tool_gateway_service.py`
- **Size:** 76,204 bytes
- **Purpose:** Agent tool gateway
- **Dependencies:** `core/`, `schemas/agents/`, `runtime/`, `policy_kernel/`, `tools/`, `workspaces/`
- **Consumers:** Chat, API
- **Failure Impact:** CRITICAL - Agent tool access fails
- **Backup:** None (single tool gateway)
- **Recommendation:** Implement tool gateway fallback

---

#### `src/aipinho/services/agents/agent_local_action_planner.py`
- **Size:** 59,957 bytes
- **Purpose:** Agent local action planning
- **Dependencies:** `core/`, `schemas/agents/`, `runtime/`, `policy_kernel/`, `tools/`
- **Consumers:** Agents, Chat
- **Failure Impact:** CRITICAL - Agent planning fails
- **Backup:** None (single action planner)
- **Recommendation:** Implement action planner fallback

---

### 2.6 Model Services

#### `src/aipinho/services/models/llama_cpp_provider.py`
- **Size:** 15,439 bytes
- **Purpose:** LLaMA CPP model provider
- **Dependencies:** `core/`, `schemas/models/`, `adapters/llm_providers/`
- **Consumers:** Chat, Agents
- **Failure Impact:** CRITICAL - Model execution fails
- **Backup:** Other model providers (partial)
- **Recommendation:** Implement provider fallback

---

### 2.7 Tool Services

#### `src/aipinho/services/tools/governed_tool_execution_service.py`
- **Size:** 29,742 bytes
- **Purpose:** Governed tool execution
- **Dependencies:** `core/`, `schemas/tools/`, `runtime/`, `policy_kernel/`, `adapters/`
- **Consumers:** Agents, Runtime, Chat
- **Failure Impact:** CRITICAL - Tool execution fails
- **Backup:** None (single execution service)
- **Recommendation:** Implement execution service fallback

---

## 3. HIGH Priority Modules (Feature Impact)

### 3.1 API Routers (Critical Surface)

| Router | Purpose | Failure Impact | Priority |
|--------|---------|----------------|----------|
| `health_router.py` | Health checks | HIGH - Monitoring fails | HIGH |
| `chat_router.py` | Chat endpoints | HIGH - Chat API fails | HIGH |
| `task_runtime_router.py` | Task runtime endpoints | HIGH - Task API fails | HIGH |
| `tool_router.py` | Tool endpoints | HIGH - Tool API fails | HIGH |
| `model_router.py` | Model endpoints | HIGH - Model API fails | HIGH |
| `artifact_router.py` | Artifact endpoints | HIGH - Artifact API fails | HIGH |
| `agent_router.py` | Agent endpoints | HIGH - Agent API fails | HIGH |
| `policy_router.py` | Policy endpoints | HIGH - Policy API fails | HIGH |

**Total Critical Routers:** 8  
**Recommendation:** Implement router fallback mechanisms

---

### 3.2 Runtime Services (Feature Critical)

| Service | Purpose | Failure Impact | Priority |
|---------|---------|----------------|----------|
| `runtime_doctor_service.py` | Runtime diagnostics | HIGH - Diagnostics fail | HIGH |
| `runtime_state_hygiene_service.py` | State management | HIGH - State corruption risk | HIGH |
| `runtime_timeline_service.py` | Timeline tracking | HIGH - Timeline loss | HIGH |
| `runtime_truth_engine.py` | Truth validation | HIGH - Validation fails | HIGH |
| `task_queue_service.py` | Queue management | HIGH - Queue management fails | HIGH |
| `supervised_execution_loop.py` | Execution supervision | HIGH - Supervision fails | HIGH |

**Total High Priority Runtime Services:** 6  
**Recommendation:** Implement service fallback mechanisms

---

### 3.3 Chat Services (Feature Critical)

| Service | Purpose | Failure Impact | Priority |
|---------|---------|----------------|----------|
| `chat_approval_command_service.py` | Approval commands | HIGH - Approval workflow fails | HIGH |
| `chat_artifact_fulfillment_service.py` | Artifact fulfillment | HIGH - Artifact handling fails | HIGH |
| `governed_write_chat_service.py` | Governed write | HIGH - Write governance fails | HIGH |
| `chat_permission_grant_service.py` | Permission grants | HIGH - Permission system fails | HIGH |
| `session_execution_report_service.py` | Session reports | HIGH - Reporting fails | HIGH |

**Total High Priority Chat Services:** 5  
**Recommendation:** Implement service fallback mechanisms

---

### 3.4 Agent Services (Feature Critical)

| Service | Purpose | Failure Impact | Priority |
|---------|---------|----------------|----------|
| `agent_delegation_service.py` | Agent delegation | HIGH - Delegation fails | HIGH |
| `agent_memory_gateway_service.py` | Memory gateway | HIGH - Memory access fails | HIGH |
| `agent_session_kernel_service.py` | Session kernel | HIGH - Session management fails | HIGH |
| `agent_delegation_policy_service.py` | Delegation policy | HIGH - Policy enforcement fails | HIGH |
| `agent_memory_policy_service.py` | Memory policy | HIGH - Memory policy fails | HIGH |

**Total High Priority Agent Services:** 5  
**Recommendation:** Implement service fallback mechanisms

---

### 3.5 RAG Services (Feature Critical)

| Service | Purpose | Failure Impact | Priority |
|---------|---------|----------------|----------|
| `retrieval_service.py` | Core retrieval | HIGH - Retrieval fails | HIGH |
| `workspace_index_service.py` | Workspace indexing | HIGH - Indexing fails | HIGH |
| `retrieval_scope_service.py` | Retrieval scoping | HIGH - Scoping fails | HIGH |
| `retrieval_source_policy_service.py` | Source policy | HIGH - Policy fails | HIGH |

**Total High Priority RAG Services:** 4  
**Recommendation:** Implement service fallback mechanisms

---

### 3.6 Memory Services (Feature Critical)

| Service | Purpose | Failure Impact | Priority |
|---------|---------|----------------|----------|
| `memory_candidate_service.py` | Memory candidates | HIGH - Candidate processing fails | HIGH |
| `curated_memory_persistence_service.py` | Memory persistence | HIGH - Persistence fails | HIGH |
| `memory_candidate_extractor.py` | Candidate extraction | HIGH - Extraction fails | HIGH |
| `learning_memory_service.py` | Learning memory | HIGH - Learning fails | HIGH |

**Total High Priority Memory Services:** 4  
**Recommendation:** Implement service fallback mechanisms

---

### 3.7 Artifact Services (Feature Critical)

| Service | Purpose | Failure Impact | Priority |
|---------|---------|----------------|----------|
| `artifact_library_service.py` | Artifact library | HIGH - Library access fails | HIGH |
| `artifact_generator_service.py` | Artifact generation | HIGH - Generation fails | HIGH |
| `universal_artifact_registry_service.py` | Universal registry | HIGH - Registry fails | HIGH |
| `artifact_write_execution_service.py` | Write execution | HIGH - Write execution fails | HIGH |

**Total High Priority Artifact Services:** 4  
**Recommendation:** Implement service fallback mechanisms

---

### 3.8 Validation Services (Feature Critical)

| Service | Purpose | Failure Impact | Priority |
|---------|---------|----------------|----------|
| `validation_gate_service.py` | Validation gates | HIGH - Validation fails | HIGH |
| `contract_compliance_validator.py` | Contract compliance | HIGH - Compliance fails | HIGH |
| `side_effect_validator.py` | Side effect validation | HIGH - Validation fails | HIGH |
| `task_result_validator.py` | Task result validation | HIGH - Validation fails | HIGH |

**Total High Priority Validation Services:** 4  
**Recommendation:** Implement validator fallback mechanisms

---

## 4. Module Dependency Criticality

### 4.1 Hub Dependencies (Single Points of Failure)

| Hub Module | Dependent Count | Failure Impact | Risk Level |
|------------|-----------------|----------------|------------|
| **Policy Kernel** | 50+ services | CRITICAL - System-wide | HIGH |
| **Task Runtime** | 20+ services | CRITICAL - Execution fails | HIGH |
| **Chat Service** | 10+ services | CRITICAL - Chat fails | HIGH |
| **Validation Services** | 30+ services | HIGH - Quality fails | MEDIUM |
| **Tool Services** | 15+ services | HIGH - Tools fail | MEDIUM |
| **Model Services** | 10+ services | HIGH - Models fail | MEDIUM |

**Total Hub Dependencies:** 6  
**Risk Level:** HIGH  
**Recommendation:** Implement hub redundancy

---

### 4.2 Chain Dependencies (Cascading Failure Risk)

| Dependency Chain | Length | Failure Impact | Risk Level |
|------------------|--------|----------------|------------|
| Chat → Runtime → Policy Kernel | 3 | CRITICAL - System-wide | HIGH |
| Agents → Tools → Adapters | 3 | HIGH - Agent tools fail | MEDIUM |
| RAG → Memory → Repositories | 3 | HIGH - RAG fails | MEDIUM |
| Artifacts → Validation → Runtime | 3 | HIGH - Artifacts fail | MEDIUM |
| Models → Adapters → External | 3 | HIGH - Models fail | MEDIUM |

**Total Chain Dependencies:** 5  
**Risk Level:** MEDIUM  
**Recommendation:** Implement chain breakers

---

## 5. Critical Module Testing

### 5.1 Test Coverage Analysis

| Module | Test Coverage | Test Count | Coverage Status |
|--------|---------------|------------|----------------|
| `main.py` | UNKNOWN | 0 | NEEDS TESTS |
| `app_factory.py` | UNKNOWN | 0 | NEEDS TESTS |
| `bootstrap.py` | UNKNOWN | 0 | NEEDS TESTS |
| `dependency_container.py` | UNKNOWN | 0 | NEEDS TESTS |
| `local_environment.py` | UNKNOWN | 0 | NEEDS TESTS |
| `policy_kernel_service.py` | HIGH | 5+ | GOOD |
| `capability_gate_service.py` | HIGH | 3+ | GOOD |
| `task_runtime_service.py` | HIGH | 10+ | GOOD |
| `chat_service.py` | HIGH | 15+ | GOOD |
| `agent_tool_gateway_service.py` | HIGH | 8+ | GOOD |

**Test Coverage Status:** GOOD for services, NEEDS IMPROVEMENT for core  
**Recommendation:** Add tests for core infrastructure

---

### 5.2 Critical Test Gaps

| Module | Gap Type | Impact | Priority |
|--------|----------|--------|----------|
| `main.py` | No tests | CRITICAL - Entrypoint untested | HIGH |
| `app_factory.py` | No tests | CRITICAL - Factory untested | HIGH |
| `bootstrap.py` | No tests | CRITICAL - Bootstrap untested | HIGH |
| `dependency_container.py` | No tests | CRITICAL - DI untested | HIGH |
| `local_environment.py` | No tests | CRITICAL - Environment untested | HIGH |

**Total Critical Test Gaps:** 5  
**Recommendation:** Add critical infrastructure tests

---

## 6. Critical Module Monitoring

### 6.1 Monitoring Requirements

| Module | Monitoring Needs | Current Status | Priority |
|--------|------------------|----------------|----------|
| `policy_kernel_service.py` | Performance, errors | PARTIAL | HIGH |
| `task_runtime_service.py` | Performance, queue depth | PARTIAL | HIGH |
| `chat_service.py` | Performance, latency | PARTIAL | HIGH |
| `agent_tool_gateway_service.py` | Tool usage, errors | NONE | HIGH |
| `llama_cpp_provider.py` | Model health, latency | PARTIAL | HIGH |
| `governed_tool_execution_service.py` | Execution metrics, errors | NONE | HIGH |

**Monitoring Status:** PARTIAL (needs improvement)  
**Recommendation:** Implement comprehensive monitoring

---

## 7. Critical Module Recovery

### 7.1 Recovery Mechanisms

| Module | Recovery Mechanism | Status | Priority |
|--------|-------------------|--------|----------|
| `policy_kernel_service.py` | None | NOT IMPLEMENTED | HIGH |
| `task_runtime_service.py` | Queue recovery | PARTIAL | HIGH |
| `chat_service.py` | Session recovery | PARTIAL | HIGH |
| `agent_tool_gateway_service.py` | None | NOT IMPLEMENTED | HIGH |
| `llama_cpp_provider.py` | Provider fallback | PARTIAL | MEDIUM |
| `governed_tool_execution_service.py` | None | NOT IMPLEMENTED | HIGH |

**Recovery Status:** POOR (needs improvement)  
**Recommendation:** Implement recovery mechanisms

---

## 8. Critical Module Recommendations

### 8.1 Immediate Actions

1. **Add Critical Infrastructure Tests**
   - Add tests for `main.py`, `app_factory.py`, `bootstrap.py`
   - Add tests for `dependency_container.py`, `local_environment.py`
   - Achieve >80% coverage for critical modules

2. **Implement Fallback Mechanisms**
   - Implement policy kernel fallback
   - Implement task runtime fallback
   - Implement chat service fallback
   - Implement agent tool gateway fallback

3. **Implement Comprehensive Monitoring**
   - Add monitoring for all critical modules
   - Implement alerting for critical failures
   - Add performance metrics tracking

### 8.2 Medium-Term Improvements

1. **Implement Recovery Mechanisms**
   - Implement automatic recovery for policy kernel
   - Implement queue recovery for task runtime
   - Implement session recovery for chat service
   - Implement tool gateway recovery

2. **Implement Redundancy**
   - Implement policy kernel redundancy
   - Implement task runtime redundancy
   - Implement chat service redundancy

### 8.3 Long-Term Improvements

1. **Implement Circuit Breakers**
   - Add circuit breakers for critical dependencies
   - Implement fallback chains
   - Implement graceful degradation

2. **Implement Chaos Engineering**
   - Add failure injection testing
   - Test recovery mechanisms
   - Validate fallback strategies

---

## 9. Critical Module Summary

### 9.1 Critical Module Statistics

| Category | Count | Percentage |
|----------|-------|------------|
| **CRITICAL Modules** | 15 | ~2% of total modules |
| **HIGH Priority Modules** | 45 | ~6% of total modules |
| **MEDIUM Priority Modules** | 150 | ~20% of total modules |
| **LOW Priority Modules** | 500+ | ~72% of total modules |

### 9.2 Critical Module Distribution

| Layer | Critical Count | High Count | Total |
|-------|----------------|------------|-------|
| **Core** | 5 | 0 | 5 |
| **Policy Kernel** | 3 | 0 | 3 |
| **Runtime** | 3 | 6 | 9 |
| **Chat** | 2 | 5 | 7 |
| **Agents** | 2 | 5 | 7 |
| **Models** | 1 | 3 | 4 |
| **Tools** | 1 | 2 | 3 |
| **RAG** | 0 | 4 | 4 |
| **Memory** | 0 | 4 | 4 |
| **Artifacts** | 0 | 4 | 4 |
| **Validation** | 0 | 4 | 4 |
| **API** | 0 | 8 | 8 |
| **Total** | 15 | 45 | 60 |

---

## Next Steps

This critical modules analysis provides the foundation for:
- Testing strategy prioritization
- Monitoring implementation planning
- Recovery mechanism design
- Redundancy planning
- Chaos engineering preparation
