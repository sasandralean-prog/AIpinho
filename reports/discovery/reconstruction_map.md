# AIpinho Reconstruction Map

**Generated:** 2026-07-28  
**Purpose:** Complete reconstruction map for system rebuilding  
**Scope:** Entire AIpinho system architecture

---

## Executive Summary

This reconstruction map provides a comprehensive guide for rebuilding the AIpinho system from scratch. It identifies the minimum viable system, critical dependencies, and recommended build order for reconstruction.

---

## 1. Reconstruction Strategy

### 1.1 Reconstruction Phases

| Phase | Description | Duration | Dependencies |
|-------|-------------|----------|--------------|
| **Phase 1: Foundation** | Core infrastructure and utilities | 1-2 weeks | None |
| **Phase 2: Data Layer** | Schemas, repositories, registries | 2-3 weeks | Phase 1 |
| **Phase 3: Core Services** | Policy kernel, validation, events | 2-3 weeks | Phase 2 |
| **Phase 4: Domain Services** | Runtime, chat, agents, tools | 4-6 weeks | Phase 3 |
| **Phase 5: API Layer** | Routers and endpoints | 1-2 weeks | Phase 4 |
| **Phase 6: Applications** | Launcher, mobile, CLI | 2-4 weeks | Phase 5 |
| **Phase 7: Testing** | Test suite development | 3-4 weeks | Phase 6 |
| **Phase 8: Configuration** | Configuration files | 1-2 weeks | Phase 7 |
| **Total** | Full system reconstruction | 16-26 weeks | - |

---

## 2. Phase 1: Foundation

### 2.1 Core Infrastructure

**Priority:** CRITICAL  
**Order:** 1

#### 2.1.1 Project Setup

**Files to Create:**
- `pyproject.toml` - Project configuration
- `README.md` - Project documentation
- `.gitignore` - Git ignore rules
- `Makefile` - Build automation

**Dependencies:** None

**Implementation Steps:**
1. Create Python project structure
2. Configure build system (setuptools)
3. Define dependencies (fastapi, uvicorn, pydantic, PyYAML, google-genai, openai)
4. Set up development environment
5. Configure git repository

---

#### 2.1.2 Core Layer

**Files to Create:**
- `src/aipinho/core/__init__.py`
- `src/aipinho/core/bootstrap.py` - Application bootstrap
- `src/aipinho/core/dependency_container.py` - Dependency injection
- `src/aipinho/core/local_environment.py` - Environment configuration
- `src/aipinho/core/paths.py` - Path resolution
- `src/aipinho/core/exceptions.py` - Exception definitions
- `src/aipinho/core/result.py` - Result type wrapper
- `src/aipinho/core/clock.py` - Time abstraction
- `src/aipinho/core/lifecycle.py` - Lifecycle management
- `src/aipinho/core/ids.py` - ID generation

**Dependencies:** None (foundation layer)

**Implementation Steps:**
1. Create core package structure
2. Implement exception definitions
3. Implement result type wrapper
4. Implement path resolution
5. Implement environment configuration
6. Implement dependency injection container
7. Implement application bootstrap
8. Implement clock, lifecycle, and ID generation (complete stubs)

**Critical Path:** YES  
**Testing:** Unit tests for each core module

---

#### 2.1.3 Utils Layer

**Files to Create:**
- `src/aipinho/utils/__init__.py`
- `src/aipinho/utils/json_loader.py` - JSON loading
- `src/aipinho/utils/yaml_loader.py` - YAML loading
- `src/aipinho/utils/hashing.py` - Hashing functions
- `src/aipinho/utils/redaction.py` - Data redaction
- `src/aipinho/utils/safe_paths.py` - Path safety
- `src/aipinho/utils/text.py` - Text utilities
- `src/aipinho/utils/diagnostics.py` - Diagnostic utilities

**Dependencies:** Standard library only

**Implementation Steps:**
1. Create utils package structure
2. Implement JSON loader
3. Implement YAML loader
4. Implement hashing functions
5. Implement redaction utilities
6. Implement safe path utilities
7. Implement text utilities
8. Implement diagnostic utilities

**Critical Path:** YES  
**Testing:** Unit tests for each utility module

---

### 2.2 Entrypoint

**Priority:** CRITICAL  
**Order:** 2

**Files to Create:**
- `src/aipinho/__init__.py` - Package initialization
- `src/aipinho/main.py` - FastAPI entrypoint
- `src/aipinho/app_factory.py` - Application factory

**Dependencies:** Core layer, Utils layer

**Implementation Steps:**
1. Create package initialization
2. Implement application factory
3. Implement FastAPI entrypoint
4. Configure lifespan management
5. Configure router registration

**Critical Path:** YES  
**Testing:** Integration tests for application startup

---

## 3. Phase 2: Data Layer

### 3.1 Schemas Layer

**Priority:** CRITICAL  
**Order:** 3

**Files to Create:**
- `src/aipinho/schemas/__init__.py`
- `src/aipinho/schemas/common/` - Common schemas (9 files)
- `src/aipinho/schemas/chat/` - Chat schemas (16 files)
- `src/aipinho/schemas/tasks/` - Task schemas (13 files)
- `src/aipinho/schemas/artifacts/` - Artifact schemas (34 files)
- `src/aipinho/schemas/tools/` - Tool schemas (24 files)
- `src/aipinho/schemas/models/` - Model schemas (41 files)
- `src/aipinho/schemas/rag/` - RAG schemas (59 files)
- `src/aipinho/schemas/memory/` - Memory schemas (38 files)
- `src/aipinho/schemas/agents/` - Agent schemas (9 files)
- `src/aipinho/schemas/roles/` - Role schemas (26 files)
- `src/aipinho/schemas/validation/` - Validation schemas (18 files)
- `src/aipinho/schemas/policy/` - Policy schemas (10 files)
- `src/aipinho/schemas/events/` - Event schemas (24 files)
- [Other domain schemas]

**Dependencies:** Pydantic, Common schemas

**Implementation Steps:**
1. Create schemas package structure
2. Implement common schemas
3. Implement domain-specific schemas (in dependency order)
4. Validate schema contracts
5. Add schema validation tests

**Critical Path:** YES  
**Testing:** Schema validation tests

---

### 3.2 Registries Layer

**Priority:** HIGH  
**Order:** 4

**Files to Create:**
- `src/aipinho/registries/__init__.py`
- `src/aipinho/registries/role_registry.py` - Role registration
- `src/aipinho/registries/route_registry.py` - Route registration
- `src/aipinho/registries/action_registry.py` - Action registration
- `src/aipinho/registries/capability_registry.py` - Capability registration
- `src/aipinho/registries/model_registry.py` - Model registration
- `src/aipinho/registries/provider_registry.py` - Provider registration
- `src/aipinho/registries/skill_registry.py` - Skill registration
- `src/aipinho/registries/tool_registry.py` - Tool registration

**Dependencies:** Core layer, Configuration layer

**Implementation Steps:**
1. Create registries package structure
2. Implement role registry
3. Implement route registry
4. Implement action registry
5. Implement capability registry
6. Implement model, provider, skill, tool registries
7. Add registry tests

**Critical Path:** YES  
**Testing:** Registry functionality tests

---

### 3.3 Repositories Layer

**Priority:** HIGH  
**Order:** 5

**Files to Create:**
- `src/aipinho/repositories/__init__.py`
- `src/aipinho/repositories/approval_repository.py`
- `src/aipinho/repositories/artifact_repository.py`
- `src/aipinho/repositories/event_repository.py`
- `src/aipinho/repositories/task_run_repository.py`
- `src/aipinho/repositories/memory_repository.py`
- `src/aipinho/repositories/report_repository.py`
- `src/aipinho/repositories/context/` - Context repositories (5 files)
- `src/aipinho/repositories/interaction/` - Interaction repositories (5 files)
- `src/aipinho/repositories/legacy_rag/` - Legacy RAG repositories (8 files)
- `src/aipinho/repositories/maintenance/` - Maintenance repositories (8 files)
- `src/aipinho/repositories/realtime/` - Realtime repositories (2 files)
- `src/aipinho/repositories/regression/` - Regression repositories (6 files)
- `src/aipinho/repositories/replay/` - Replay repositories (6 files)
- `src/aipinho/repositories/skills/` - Skill repositories (6 files)
- `src/aipinho/repositories/tools/` - Tool repositories (2 files)
- `src/aipinho/repositories/artifacts/` - Artifact repositories (1 file)

**Dependencies:** Core layer, Data stores

**Implementation Steps:**
1. Create repositories package structure
2. Implement core repositories
3. Implement domain-specific repositories
4. Implement data store integration
5. Add repository tests

**Critical Path:** YES  
**Testing:** Repository functionality tests

---

### 3.4 Adapters Layer

**Priority:** MEDIUM  
**Order:** 6

**Files to Create:**
- `src/aipinho/adapters/__init__.py`
- `src/aipinho/adapters/llm_providers/` - LLM provider adapters (5 files)
- `src/aipinho/adapters/filesystem/` - Filesystem adapters (2 files)
- `src/aipinho/adapters/git/` - Git adapters (2 files)
- `src/aipinho/adapters/shell/` - Shell adapters (2 files)
- `src/aipinho/adapters/web/` - Web adapters (2 files)
- `src/aipinho/adapters/android/` - Android adapters (2 files)
- `src/aipinho/adapters/embeddings/` - Embedding adapters
- `src/aipinho/adapters/rerankers/` - Reranker adapters
- `src/aipinho/adapters/vectorstores/` - Vectorstore adapters

**Dependencies:** External libraries

**Implementation Steps:**
1. Create adapters package structure
2. Implement LLM provider adapters (OpenAI, Gemini, Anthropic)
3. Implement filesystem adapters
4. Implement git adapters
5. Implement shell adapters
6. Implement web adapters
7. Implement android adapters
8. Add adapter tests

**Critical Path:** NO (can be implemented in parallel)  
**Testing:** Adapter integration tests

---

## 4. Phase 3: Core Services

### 4.1 Policy Kernel

**Priority:** CRITICAL  
**Order:** 7

**Files to Create:**
- `src/aipinho/services/policy_kernel/__init__.py`
- `src/aipinho/services/policy_kernel/policy_kernel_service.py`
- `src/aipinho/services/policy_kernel/capability_gate_service.py`
- `src/aipinho/services/policy_kernel/workspace_role_contract_service.py`
- `src/aipinho/services/policy_kernel/effective_policy_builder.py`
- `src/aipinho/services/policy_kernel/policy_context_builder.py`
- `src/aipinho/services/policy_kernel/workspace_policy_service.py`
- `src/aipinho/services/policy_kernel/approval_policy_service.py`
- `src/aipinho/services/policy_kernel/policy_precedence_service.py`
- `src/aipinho/services/policy_kernel/action_registry_service.py`
- `src/aipinho/services/policy_kernel/policy_trace_service.py`

**Dependencies:** Core layer, Registries, Schemas

**Implementation Steps:**
1. Create policy kernel package structure
2. Implement policy kernel service
3. Implement capability gate service
4. Implement workspace role contract service
5. Implement policy builders
6. Implement policy resolvers
7. Implement policy tracing
8. Add policy kernel tests

**Critical Path:** YES  
**Testing:** Policy kernel functionality tests

---

### 4.2 Validation Services

**Priority:** HIGH  
**Order:** 8

**Files to Create:**
- `src/aipinho/services/validation/__init__.py`
- `src/aipinho/services/validation/validation_gate_service.py`
- `src/aipinho/services/validation/validation_common.py`
- `src/aipinho/services/validation/contract_compliance_validator.py`
- `src/aipinho/services/validation/side_effect_validator.py`
- `src/aipinho/services/validation/task_result_validator.py`
- `src/aipinho/services/validation/task_run_validator.py`
- `src/aipinho/services/validation/evidence_compliance_validator.py`
- `src/aipinho/services/validation/report_quality_gate_service.py`
- `src/aipinho/services/validation/role_pipeline_validator.py`
- `src/aipinho/services/validation/workspace_access_validator.py`
- [Other validators]

**Dependencies:** Core layer, Schemas

**Implementation Steps:**
1. Create validation package structure
2. Implement validation gate service
3. Implement common validation utilities
4. Implement domain-specific validators
5. Implement validation tracing
6. Add validation tests

**Critical Path:** YES  
**Testing:** Validation functionality tests

---

### 4.3 Event Services

**Priority:** HIGH  
**Order:** 9

**Files to Create:**
- `src/aipinho/services/events/__init__.py`
- `src/aipinho/services/events/event_core.py`
- `src/aipinho/services/events/event_publisher_service.py`
- `src/aipinho/services/events/event_filter_service.py`
- `src/aipinho/services/events/event_search_service.py`
- `src/aipinho/services/events/event_schema_validator.py`
- `src/aipinho/services/events/event_view_model_service.py`
- `src/aipinho/services/events/event_visibility_service.py`
- `src/aipinho/services/events/event_severity_service.py`
- `src/aipinho/services/events/event_status_service.py`
- `src/aipinho/services/events/event_trace_service.py`
- [Other event services]

**Dependencies:** Core layer, Schemas, Repositories

**Implementation Steps:**
1. Create events package structure
2. Implement event core service
3. Implement event publisher
4. Implement event filtering
5. Implement event search
6. Implement event validation
7. Implement event tracing
8. Add event tests

**Critical Path:** YES  
**Testing:** Event functionality tests

---

## 5. Phase 4: Domain Services

### 5.1 Runtime Services

**Priority:** CRITICAL  
**Order:** 10

**Files to Create:**
- `src/aipinho/services/runtime/__init__.py`
- `src/aipinho/services/runtime/task_runtime_service.py`
- `src/aipinho/services/runtime/execution_graph_service.py`
- `src/aipinho/services/runtime/intelligent_planner_service.py`
- `src/aipinho/services/runtime/governed_task_step_runner.py`
- `src/aipinho/services/runtime/runtime_doctor_service.py`
- `src/aipinho/services/runtime/runtime_operator_doctor_service.py`
- `src/aipinho/services/runtime/runtime_state_hygiene_service.py`
- `src/aipinho/services/runtime/runtime_timeline_service.py`
- `src/aipinho/services/runtime/runtime_truth_engine.py`
- `src/aipinho/services/runtime/task_queue_service.py`
- [Other runtime services]

**Dependencies:** Core layer, Policy Kernel, Repositories, Schemas

**Implementation Steps:**
1. Create runtime package structure
2. Implement task runtime service
3. Implement execution graph service
4. Implement intelligent planner
5. Implement governed step runner
6. Implement runtime diagnostics
7. Implement task queue management
8. Add runtime tests

**Critical Path:** YES  
**Testing:** Runtime functionality tests

---

### 5.2 Chat Services

**Priority:** CRITICAL  
**Order:** 11

**Files to Create:**
- `src/aipinho/services/chat/__init__.py`
- `src/aipinho/services/chat/chat_service.py`
- `src/aipinho/services/chat/chat_operation_router_service.py`
- `src/aipinho/services/chat/chat_approval_command_service.py`
- `src/aipinho/services/chat/chat_artifact_fulfillment_service.py`
- `src/aipinho/services/chat/governed_write_chat_service.py`
- `src/aipinho/services/chat/chat_permission_grant_service.py`
- `src/aipinho/services/chat/session_execution_report_service.py`
- [Other chat services]

**Dependencies:** Core layer, Runtime, Policy Kernel, Memory, Models, Tools

**Implementation Steps:**
1. Create chat package structure
2. Implement chat service
3. Implement chat operation router
4. Implement approval commands
5. Implement artifact fulfillment
6. Implement governed write
7. Implement permission grants
8. Add chat tests

**Critical Path:** YES  
**Testing:** Chat functionality tests

---

### 5.3 Agent Services

**Priority:** HIGH  
**Order:** 12

**Files to Create:**
- `src/aipinho/services/agents/__init__.py`
- `src/aipinho/services/agents/agent_tool_gateway_service.py`
- `src/aipinho/services/agents/agent_local_action_planner.py`
- `src/aipinho/services/agents/agent_delegation_service.py`
- `src/aipinho/services/agents/agent_memory_gateway_service.py`
- `src/aipinho/services/agents/agent_session_kernel_service.py`
- [Other agent services]

**Dependencies:** Core layer, Runtime, Policy Kernel, Tools, Memory

**Implementation Steps:**
1. Create agents package structure
2. Implement agent tool gateway
3. Implement agent action planner
4. Implement agent delegation
5. Implement agent memory gateway
6. Implement agent session kernel
7. Add agent tests

**Critical Path:** YES  
**Testing:** Agent functionality tests

---

### 5.4 Tool Services

**Priority:** HIGH  
**Order:** 13

**Files to Create:**
- `src/aipinho/services/tools/__init__.py`
- `src/aipinho/services/tools/governed_tool_execution_service.py`
- `src/aipinho/services/tools/tool_safety_service.py`
- `src/aipinho/services/tools/tool_contract_core.py`
- `src/aipinho/services/tools/tool_registry_service.py`
- `src/aipinho/services/tools/tool_preview_service.py`
- `src/aipinho/services/tools/tool_execution_guard.py`
- [Other tool services]

**Dependencies:** Core layer, Runtime, Policy Kernel, Adapters

**Implementation Steps:**
1. Create tools package structure
2. Implement governed tool execution
3. Implement tool safety
4. Implement tool contracts
5. Implement tool registry
6. Implement tool preview
7. Add tool tests

**Critical Path:** YES  
**Testing:** Tool functionality tests

---

### 5.5 Model Services

**Priority:** HIGH  
**Order:** 14

**Files to Create:**
- `src/aipinho/services/models/__init__.py`
- `src/aipinho/services/models/llama_cpp_provider.py`
- `src/aipinho/services/models/model_invocation_service.py`
- `src/aipinho/services/models/capability_router_service.py`
- `src/aipinho/services/models/model_doctor_service.py`
- `src/aipinho/services/models/model_registry_service.py`
- [Other model services]

**Dependencies:** Core layer, Adapters, Schemas

**Implementation Steps:**
1. Create models package structure
2. Implement LLaMA CPP provider
3. Implement model invocation service
4. Implement capability router
5. Implement model diagnostics
6. Implement model registry
7. Add model tests

**Critical Path:** YES  
**Testing:** Model functionality tests

---

### 5.6 Memory Services

**Priority:** MEDIUM  
**Order:** 15

**Files to Create:**
- `src/aipinho/services/memory/__init__.py`
- `src/aipinho/services/memory/memory_candidate_service.py`
- `src/aipinho/services/memory/curated_memory_service.py`
- `src/aipinho/services/memory/curated_memory_persistence_service.py`
- [Other memory services]

**Dependencies:** Core layer, Repositories, Schemas

**Implementation Steps:**
1. Create memory package structure
2. Implement memory candidate service
3. Implement curated memory service
4. Implement memory persistence
5. Add memory tests

**Critical Path:** NO (can be implemented in parallel)  
**Testing:** Memory functionality tests

---

### 5.7 RAG Services

**Priority:** MEDIUM  
**Order:** 16

**Files to Create:**
- `src/aipinho/services/rag/__init__.py`
- `src/aipinho/services/rag/retrieval_service.py`
- `src/aipinho/services/rag/workspace_index_service.py`
- [Other RAG services]

**Dependencies:** Core layer, Memory, Vectorstores

**Implementation Steps:**
1. Create RAG package structure
2. Implement retrieval service
3. Implement workspace indexing
4. Add RAG tests

**Critical Path:** NO (can be implemented in parallel)  
**Testing:** RAG functionality tests

---

### 5.8 Artifact Services

**Priority:** MEDIUM  
**Order:** 17

**Files to Create:**
- `src/aipinho/services/artifacts/__init__.py`
- `src/aipinho/services/artifacts/artifact_library_service.py`
- `src/aipinho/services/artifacts/artifact_generator_service.py`
- `src/aipinho/services/artifacts/universal_artifact_registry_service.py`
- [Other artifact services]

**Dependencies:** Core layer, Repositories, Validation

**Implementation Steps:**
1. Create artifacts package structure
2. Implement artifact library
3. Implement artifact generator
4. Implement universal registry
5. Add artifact tests

**Critical Path:** NO (can be implemented in parallel)  
**Testing:** Artifact functionality tests

---

### 5.9 Other Domain Services

**Priority:** LOW  
**Order:** 18

**Services to Implement:**
- Vision services (29 modules)
- Patching services (70 modules)
- Maintenance services (42 modules)
- Debugger services (33 modules)
- Regression services (30 modules)
- Replay services (32 modules)
- Supervisor services (24 modules)
- Skill services (35 modules)
- Context services (42 modules)
- Role services (30 modules)
- [Other domain services]

**Dependencies:** Core layer, Policy Kernel, Validation

**Implementation Steps:**
1. Implement services in priority order
2. Add service tests
3. Validate service contracts

**Critical Path:** NO (can be implemented in parallel)  
**Testing:** Service functionality tests

---

## 6. Phase 5: API Layer

### 6.1 API Routers

**Priority:** HIGH  
**Order:** 19

**Files to Create:**
- `src/aipinho/api/__init__.py`
- `src/aipinho/api/routers/__init__.py`
- `src/aipinho/api/routers/health_router.py'
- `src/aipinho/api/routers/config_router.py`
- `src/aipinho/api/routers/policy_router.py`
- `src/aipinho/api/routers/chat_router.py`
- `src/aipinho/api/routers/task_runtime_router.py`
- `src/aipinho/api/routers/tool_router.py`
- `src/aipinho/api/routers/model_router.py`
- `src/aipinho/api/routers/artifact_router.py`
- `src/aipinho/api/routers/agent_router.py`
- [Other routers - 139 total]

**Dependencies:** Services layer, Schemas

**Implementation Steps:**
1. Create API package structure
2. Implement core routers (health, config, policy)
3. Implement domain routers (chat, task, tool, model, artifact, agent)
4. Implement remaining routers
5. Add router tests

**Critical Path:** YES  
**Testing:** API integration tests

---

### 6.2 API Configuration

**Priority:** MEDIUM  
**Order:** 20

**Files to Create:**
- `src/aipinho/api/dependencies/` - Dependency injection
- `src/aipinho/api/errors/` - Error handlers
- `src/aipinho/api/middleware/` - Middleware
- `src/aipinho/api/openapi/` - OpenAPI configuration

**Dependencies:** Services layer

**Implementation Steps:**
1. Implement dependency injection
2. Implement error handlers
3. Implement middleware
4. Configure OpenAPI
5. Add API configuration tests

**Critical Path:** NO  
**Testing:** API configuration tests

---

## 7. Phase 6: Applications

### 7.1 Desktop Launcher

**Priority:** MEDIUM  
**Order:** 21

**Files to Create:**
- `apps/launcher/` - Desktop launcher (141 files)
- `apps/launcher/launcher_bootstrap.py`
- `apps/launcher/launcher_main.py`
- `apps/launcher/launcher_config_loader.py`
- [Other launcher files]

**Dependencies:** API layer

**Implementation Steps:**
1. Create launcher package structure
2. Implement launcher bootstrap
3. Implement launcher main
4. Implement launcher UI
5. Add launcher tests

**Critical Path:** NO  
**Testing:** Launcher integration tests

---

### 7.2 Mobile Application

**Priority:** LOW  
**Order:** 22

**Files to Create:**
- `apps/mobile/android/` - Android application (1460 files)
- [Android project structure]

**Dependencies:** API layer

**Implementation Steps:**
1. Create Android project structure
2. Implement mobile UI
3. Implement API integration
4. Add mobile tests

**Critical Path:** NO  
**Testing:** Mobile integration tests

---

### 7.3 CLI Application

**Priority:** LOW  
**Order:** 23

**Files to Create:**
- `apps/cli/` - CLI application

**Dependencies:** API layer

**Implementation Steps:**
1. Create CLI package structure
2. Implement CLI commands
3. Add CLI tests

**Critical Path:** NO  
**Testing:** CLI integration tests

---

## 8. Phase 7: Testing

### 8.1 Test Suite

**Priority:** HIGH  
**Order:** 24

**Files to Create:**
- `tests/__init__.py`
- `tests/conftest.py` - Pytest configuration
- `tests/unit/` - Unit tests (589 files)
- `tests/integration/` - Integration tests (149 files)
- `tests/contract/` - Contract tests (46 files)
- `tests/e2e/` - E2E tests (43 files)
- `tests/fixtures/` - Test fixtures (50 files)
- [Other test files]

**Dependencies:** All layers

**Implementation Steps:**
1. Create test package structure
2. Implement unit tests
3. Implement integration tests
4. Implement contract tests
5. Implement E2E tests
6. Implement test fixtures
7. Configure pytest markers

**Critical Path:** YES  
**Testing:** Test suite validation

---

## 9. Phase 8: Configuration

### 9.1 Configuration Files

**Priority:** HIGH  
**Order:** 25

**Files to Create:**
- `config/policies/` - Policy configurations (31 files)
- `config/roles/` - Role configurations (18 files)
- `config/tools/` - Tool configurations (12 files)
- `config/models/` - Model configurations (28 files)
- `config/skills/` - Skill configurations (81 files)
- `config/runtime/` - Runtime configurations (48 files)
- `config/artifacts/` - Artifact configurations (30 files)
- `config/memory/` - Memory configurations (32 files)
- `config/rag/` - RAG configurations (54 files)
- `config/vision/` - Vision configurations (20 files)
- `config/validation/` - Validation configurations (14 files)
- `config/patching/` - Patching configurations (41 files)
- [Other configurations - 714 total]

**Dependencies:** All layers

**Implementation Steps:**
1. Create configuration directory structure
2. Implement policy configurations
3. Implement role configurations
4. Implement domain-specific configurations
5. Validate configuration files
6. Add configuration tests

**Critical Path:** YES  
**Testing:** Configuration validation tests

---

## 10. Minimum Viable System

### 10.1 MVP Components

**Minimum Viable System (MVP) includes:**

1. **Foundation** (Phase 1)
   - Core infrastructure
   - Utils layer
   - Entrypoint

2. **Data Layer** (Phase 2)
   - Common schemas
   - Core registries
   - Core repositories

3. **Core Services** (Phase 3)
   - Policy kernel
   - Validation services
   - Event services

4. **Domain Services** (Phase 4 - Subset)
   - Runtime services
   - Chat services
   - Tool services
   - Model services

5. **API Layer** (Phase 5 - Subset)
   - Core routers (health, config, policy)
   - Domain routers (chat, task, tool, model)

6. **Testing** (Phase 7 - Subset)
   - Unit tests
   - Integration tests

7. **Configuration** (Phase 8 - Subset)
   - Core configurations
   - Domain configurations

**MVP Duration:** 8-12 weeks  
**MVP Scope:** Basic chat with tool execution and model inference

---

## 11. Reconstruction Dependencies

### 11.1 Critical Path

```
Foundation (Phase 1)
  ↓
Data Layer (Phase 2)
  ↓
Core Services (Phase 3)
  ↓
Domain Services (Phase 4)
  ↓
API Layer (Phase 5)
  ↓
Applications (Phase 6)
  ↓
Testing (Phase 7)
  ↓
Configuration (Phase 8)
```

**Critical Path Duration:** 16-26 weeks

---

### 12. Reconstruction Checklist

### 12.1 Phase 1 Checklist

- [ ] Create project structure
- [ ] Configure build system
- [ ] Implement core layer
- [ ] Implement utils layer
- [ ] Implement entrypoint
- [ ] Add core tests

### 12.2 Phase 2 Checklist

- [ ] Implement common schemas
- [ ] Implement domain schemas
- [ ] Implement registries
- [ ] Implement repositories
- [ ] Implement adapters
- [ ] Add data layer tests

### 12.3 Phase 3 Checklist

- [ ] Implement policy kernel
- [ ] Implement validation services
- [ ] Implement event services
- [ ] Add core service tests

### 12.4 Phase 4 Checklist

- [ ] Implement runtime services
- [ ] Implement chat services
- [ ] Implement agent services
- [ ] Implement tool services
- [ ] Implement model services
- [ ] Implement memory services
- [ ] Implement RAG services
- [ ] Implement artifact services
- [ ] Implement other domain services
- [ ] Add domain service tests

### 12.5 Phase 5 Checklist

- [ ] Implement core routers
- [ ] Implement domain routers
- [ ] Implement API configuration
- [ ] Add API tests

### 12.6 Phase 6 Checklist

- [ ] Implement desktop launcher
- [ ] Implement mobile application
- [ ] Implement CLI application
- [ ] Add application tests

### 12.7 Phase 7 Checklist

- [ ] Implement unit tests
- [ ] Implement integration tests
- [ ] Implement contract tests
- [ ] Implement E2E tests
- [ ] Implement test fixtures

### 12.8 Phase 8 Checklist

- [ ] Implement policy configurations
- [ ] Implement role configurations
- [ ] Implement domain configurations
- [ ] Validate configurations
- [ ] Add configuration tests

---

## 13. Reconstruction Risks

### 13.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Incomplete Documentation** | HIGH | HIGH | Document as you build |
| **Missing Dependencies** | MEDIUM | HIGH | Validate dependencies early |
| **Configuration Complexity** | HIGH | MEDIUM | Start with simple configs |
| **Test Coverage Gaps** | MEDIUM | MEDIUM | Test-driven development |
| **Integration Issues** | MEDIUM | HIGH | Incremental integration |

### 13.2 Timeline Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Scope Creep** | HIGH | HIGH | Strict scope management |
| **Technical Debt** | MEDIUM | MEDIUM | Refactor continuously |
| **Resource Constraints** | MEDIUM | HIGH | Prioritize MVP |
| **Integration Complexity** | MEDIUM | HIGH | Incremental integration |

---

## 14. Reconstruction Recommendations

### 14.1 Best Practices

1. **Test-Driven Development**
   - Write tests before implementation
   - Maintain high test coverage
   - Use contract tests for boundaries

2. **Incremental Integration**
   - Integrate incrementally
   - Validate at each step
   - Use feature flags

3. **Documentation**
   - Document as you build
   - Maintain architecture docs
   - Update API documentation

4. **Code Quality**
   - Follow coding standards
   - Use code reviews
   - Refactor continuously

### 14.2 Success Criteria

1. **Functional Criteria**
   - All core services functional
   - API endpoints operational
   - Applications working

2. **Quality Criteria**
   - Test coverage >80%
   - No critical bugs
   - Performance acceptable

3. **Documentation Criteria**
   - All APIs documented
   - Architecture documented
   - Configuration documented

---

## Next Steps

This reconstruction map provides the foundation for:
- System rebuilding from scratch
- MVP development
- Incremental feature addition
- Risk mitigation planning
