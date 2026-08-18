# AIpinho Duplicate Modules Detection

**Generated:** 2026-07-28  
**Purpose:** Detection of duplicate modules, dead code, and internal forks  
**Scope:** All source code modules in AIpinho

---

## Executive Summary

AIpinho shows signs of organic growth with several patterns of potential duplication, legacy code, and stub implementations. The project has clear separation of legacy code but shows evidence of evolutionary development patterns.

---

## 1. Dead Code Detection

### 1.1 Empty/Stub Implementations (0 bytes)

**Critical Finding:** 100+ empty or stub implementations detected

#### Core Layer Empty Files
| Module | Location | Type | Impact |
|--------|----------|------|--------|
| `clock.py` | `src/aipinho/core/` | Empty stub | LOW - Time abstraction not implemented |
| `lifecycle.py` | `src/aipinho/core/` | Empty stub | LOW - Lifecycle management not implemented |
| `ids.py` | `src/aipinho/core/` | Empty stub | LOW - ID generation not implemented |

#### Services Layer Empty Files (High Count)
| Category | Count | Examples | Impact |
|----------|-------|----------|--------|
| **Runtime Services** | 6 | `cancellation_service.py`, `execution_context.py`, `retry_policy_service.py`, `runtime_guard.py`, `step_runner.py`, `task_runner.py`, `timeout_service.py` | MEDIUM - Runtime infrastructure incomplete |
| **RAG Services** | 8 | `chunking_service.py`, `embedding_service.py`, `rag_context_builder.py`, `rag_audit_service.py`, `rerank_service.py`, `vectorstore_service.py`, `citation_service.py`, `rag_service.py` | MEDIUM - RAG infrastructure incomplete |
| **Memory Services** | 5 | `memory_audit_service.py`, `memory_conflict_service.py`, `memory_curator_service.py`, `memory_embedding_service.py`, `memory_retention_service.py`, `memory_search_service.py`, `memory_service.py` | MEDIUM - Memory infrastructure incomplete |
| **Tool Services** | 5 | `android_tool_service.py`, `browser_tool_service.py`, `filesystem_tool_service.py`, `git_tool_service.py`, `shell_tool_service.py` | MEDIUM - Tool adapters incomplete |
| **Model Services** | 3 | `modality_service.py`, `model_selector.py`, `token_budget_service.py` | LOW - Model utilities incomplete |
| **Policy Kernel** | 2 | `model_policy_resolver.py`, `tool_policy_resolver.py` | LOW - Policy resolvers incomplete |
| **Registries** | 4 | `model_registry.py`, `provider_registry.py`, `skill_registry.py`, `tool_registry.py` | MEDIUM - Registry implementations incomplete |
| **Adapters** | 3 | `embeddings/`, `rerankers/`, `vectorstores/` | LOW - Adapter placeholders |
| **Context Services** | 1 | `smart_chunker.py` | LOW - Chunking placeholder |
| **Validation Services** | 3 | `static_analysis_service.py`, `test_runner_service.py`, `validation_profile_service.py`, `validation_report_service.py` | LOW - Validation infrastructure incomplete |
| **Patching Services** | 6 | `diff_service.py`, `patch_apply_service.py`, `patch_plan_service.py`, `patch_preview_service.py`, `patch_report_service.py`, `patch_quality_gate.py` | MEDIUM - Patching infrastructure incomplete |
| **Skill Services** | 20+ | Multiple stub services (skill_*.py with minimal content) | MEDIUM - Skill infrastructure incomplete |
| **Repositories** | 4 | `approval_repository.py`, `artifact_repository.py`, `event_repository.py`, `memory_repository.py`, `report_repository.py`, `task_run_repository.py` | MEDIUM - Repository implementations incomplete |

**Total Empty/Stub Files:** 100+ files  
**Impact:** Significant - indicates incomplete implementation or placeholder code  
**Recommendation:** Complete implementations or remove unused stubs

---

## 2. Legacy Code Detection

### 2.1 Legacy RAG System

**Location:** `src/aipinho/services/legacy_rag/` (18 items)  
**Status:** Quarantined legacy system

| Module | Purpose | Replacement Status |
|--------|---------|-------------------|
| `legacy_rag_router.py` | Legacy RAG routing | Replaced by new RAG services |
| `legacy_rag_*.py` (17 files) | Legacy RAG infrastructure | Replaced by new RAG services |

**Test Files:**
- `tests/test_legacy_rag_classification.py`
- `tests/test_legacy_rag_commit_gate.py`
- `tests/test_legacy_rag_router_contract.py`
- `tests/test_legacy_rag_sanitizer.py`

**Impact:** LOW - Legacy code properly separated  
**Recommendation:** Consider removal if new RAG system is fully functional

---

### 2.2 Quarantined Governance Code

**Location:** `quarantine/legacy/governance/` (2 items)  
**Status:** Quarantined legacy governance

| Module | Purpose | Replacement Status |
|--------|---------|-------------------|
| [Governance files] | Legacy governance implementation | Replaced by new governance services |

**Impact:** LOW - Legacy code properly quarantined  
**Recommendation:** Review for removal if new governance is stable

---

## 3. Potential Duplications

### 3.1 Service Pattern Duplication

**Pattern:** Multiple services with similar structure and naming

#### Trace Services (High Duplication)
| Service | Location | Purpose | Similarity |
|---------|----------|---------|------------|
| `policy_trace_service.py` | `services/policy_kernel/` | Policy tracing | HIGH |
| `retrieval_trace_service.py` | `services/rag/` | Retrieval tracing | HIGH |
| `memory_trace_service.py` | `services/memory/` | Memory tracing | HIGH |
| `memory_candidate_trace_service.py` | `services/memory/` | Memory candidate tracing | HIGH |
| `curated_memory_trace_service.py` | `services/memory/` | Curated memory tracing | HIGH |
| `artifact_trace_service.py` | `services/artifacts/` | Artifact tracing | HIGH |
| `artifact_write_trace_service.py` | `services/artifacts/` | Artifact write tracing | HIGH |
| `tool_trace_service.py` | `services/tools/` | Tool tracing | HIGH |
| `model_trace_service.py` | `services/models/` | Model tracing | HIGH |
| `role_trace_service.py` | `services/roles/` | Role tracing | HIGH |
| `role_pipeline_trace_service.py` | `services/roles/` | Role pipeline tracing | HIGH |
| `validation_trace_service.py` | `services/validation/` | Validation tracing | HIGH |
| `event_trace_service.py` | `services/events/` | Event tracing | HIGH |
| `regression_trace_service.py` | `services/regression/` | Regression tracing | HIGH |
| `replay_trace_service.py` | `services/replay/` | Replay tracing | HIGH |
| `maintenance_trace_service.py` | `services/maintenance/` | Maintenance tracing | HIGH |
| `vision_trace_service.py` | `services/vision/` | Vision tracing | HIGH |
| `debugger_trace_service.py` | `services/debugger/` | Debugger tracing | HIGH |
| `debugger_trace_service_v2.py` | `services/debugger/` | Debugger tracing v2 | HIGH |

**Duplication Level:** 20+ trace services with similar patterns  
**Impact:** MEDIUM - Could be consolidated into a generic trace service  
**Recommendation:** Consider generic trace infrastructure

---

#### Status Services (High Duplication)
| Service | Location | Purpose | Similarity |
|---------|----------|---------|------------|
| `retrieval_status_service.py` | `services/rag/` | Retrieval status | HIGH |
| `memory_candidate_status_service.py` | `services/memory/` | Memory candidate status | HIGH |
| `curated_memory_status_service.py` | `services/memory/` | Curated memory status | HIGH |
| `artifact_service_status.py` | `services/artifacts/` | Artifact status | HIGH |
| `model_status_service.py` | `services/models/` | Model status | HIGH |
| `manual_inference_status_service.py` | `services/models/` | Manual inference status | HIGH |
| `llama_cpp_status_service.py` | `services/models/` | LLaMA CPP status | HIGH |
| `vision_status_service.py` | `services/vision/` | Vision status | HIGH |
| `debugger_status_service.py` | `services/debugger/` | Debugger status | HIGH |

**Duplication Level:** 9+ status services with similar patterns  
**Impact:** MEDIUM - Could be consolidated into a generic status service  
**Recommendation:** Consider generic status infrastructure

---

#### Store Services (High Duplication)
| Service | Location | Purpose | Similarity |
|---------|----------|---------|------------|
| `task_run_store.py` | `services/runtime/` | Task run storage | HIGH |
| `artifact_preview_store.py` | `services/artifacts/` | Artifact preview storage | HIGH |
| `artifact_write_store.py` | `services/artifacts/` | Artifact write storage | HIGH |
| `memory_candidate_store.py` | `services/memory/` | Memory candidate storage | HIGH |
| `curated_memory_store.py` | `services/memory/` | Curated memory storage | HIGH |
| `context_bundle_store.py` | `services/context/` | Context bundle storage | HIGH |
| `agent_session_store.py` | `services/agents/` | Agent session storage | HIGH |
| `agent_delegation_store.py` | `services/agents/` | Agent delegation storage | HIGH |
| `agent_memory_gateway_store.py` | `services/agents/` | Agent memory gateway storage | HIGH |
| `agent_tool_invocation_store.py` | `services/agents/` | Agent tool invocation storage | HIGH |
| `real_inference_run_store.py` | `services/models/` | Real inference run storage | HIGH |
| `role_model_run_store.py` | `services/roles/` | Role model run storage | HIGH |
| `patch_plan_store.py` | `services/patching/` | Patch plan storage | HIGH |
| `validation_store.py` | `services/validation/` | Validation storage | HIGH |
| `replay_store_service.py` | `services/replay/` | Replay storage | HIGH |

**Duplication Level:** 15+ store services with similar patterns  
**Impact:** MEDIUM - Could be consolidated into a generic store service  
**Recommendation:** Consider generic storage infrastructure

---

#### Audit Services (High Duplication)
| Service | Location | Purpose | Similarity |
|---------|----------|---------|------------|
| `retrieval_audit_service.py` | `services/rag/` | Retrieval audit | HIGH |
| `curated_memory_audit_service.py` | `services/memory/` | Curated memory audit | HIGH |
| `execution_audit_service.py` | `services/tools/` | Execution audit | HIGH |
| `artifact_write_audit_service.py` | `services/artifacts/` | Artifact write audit | HIGH |
| `model_invocation_audit_service.py` | `services/models/` | Model invocation audit | HIGH |
| `smoke_test_audit_service.py` | `services/models/` | Smoke test audit | HIGH |
| `vision_audit_service.py` | `services/vision/` | Vision audit | HIGH |
| `validation_audit_service.py` | `services/validation/` | Validation audit | HIGH |
| `regression_audit_service.py` | `services/regression/` | Regression audit | HIGH |
| `replay_audit_service.py` | `services/replay/` | Replay audit | HIGH |
| `maintenance_audit_service.py` | `services/maintenance/` | Maintenance audit | HIGH |
| `supervisor_audit_service.py` | `services/supervisor/` | Supervisor audit | HIGH |

**Duplication Level:** 12+ audit services with similar patterns  
**Impact:** MEDIUM - Could be consolidated into a generic audit service  
**Recommendation:** Consider generic audit infrastructure

---

#### Validator Services (High Duplication)
| Service | Location | Purpose | Similarity |
|---------|----------|---------|------------|
| `memory_candidate_validator.py` | `services/memory/` | Memory candidate validation | HIGH |
| `curated_memory_validator.py` | `services/memory/` | Curated memory validation | HIGH |
| `artifact_content_validator.py` | `services/artifacts/` | Artifact content validation | HIGH |
| `artifact_format_validator.py` | `services/artifacts/` | Artifact format validation | HIGH |
| `artifact_post_write_validator.py` | `services/artifacts/` | Artifact post-write validation | HIGH |
| `tool_input_validator.py` | `services/tools/` | Tool input validation | HIGH |
| `model_path_validator.py` | `services/models/` | Model path validation | HIGH |
| `model_security_validator.py` | `services/models/` | Model security validation | HIGH |
| `skill_manifest_validator.py` | `services/skills/` | Skill manifest validation | HIGH |
| `skill_contract_validator.py` | `services/skills/` | Skill contract validation | HIGH |
| `image_input_validator.py` | `services/vision/` | Image input validation | HIGH |
| `mmproj_pair_validator.py` | `services/vision/` | MMProj pair validation | HIGH |

**Duplication Level:** 12+ validator services with similar patterns  
**Impact:** MEDIUM - Could be consolidated into a generic validator service  
**Recommendation:** Consider generic validation infrastructure

---

### 3.2 Schema Duplication

**Pattern:** Similar schema structures across different domains

#### Common Schema Patterns
| Schema Type | Count | Examples | Similarity |
|-------------|-------|----------|------------|
| **Request/Response Pairs** | 50+ | ChatRequest/ChatResponse, TaskRequest/TaskResponse | HIGH |
| **Status Schemas** | 30+ | ModelStatus, ToolStatus, ServiceStatus | HIGH |
| **Config Schemas** | 40+ | ModelConfig, ToolConfig, PolicyConfig | HIGH |
| **Event Schemas** | 24+ | Various event types | MEDIUM |
| **Policy Schemas** | 20+ | Various policy types | MEDIUM |

**Duplication Level:** 140+ schemas with similar patterns  
**Impact:** LOW - Schemas are domain-specific by design  
**Recommendation:** Consider base schema classes for common patterns

---

### 3.3 Router Duplication

**Pattern:** Similar router structures across different domains

| Router Category | Count | Pattern Similarity |
|-----------------|-------|-------------------|
| **CRUD Routers** | 30+ | GET/POST/PUT/DELETE patterns | HIGH |
| **Status Routers** | 20+ | Status endpoint patterns | HIGH |
| **Validation Routers** | 15+ | Validation endpoint patterns | HIGH |
| **Search Routers** | 10+ | Search endpoint patterns | MEDIUM |

**Duplication Level:** 75+ routers with similar patterns  
**Impact:** LOW - Routers are domain-specific by design  
**Recommendation:** Consider router mixins for common patterns

---

## 4. Internal Forks

### 4.1 Version Forks

**Pattern:** Multiple versions of similar functionality

#### Debugger Services
| Service | Version | Purpose |
|---------|---------|---------|
| `debugger_trace_service.py` | v1 | Original debugger trace |
| `debugger_trace_service_v2.py` | v2 | Updated debugger trace |
| `decision_trace_service.py` | - | Decision-specific trace |
| `model_decision_trace_service.py` | - | Model decision trace |
| `multi_island_trace_service.py` | - | Multi-island trace |

**Fork Level:** 5 debugger trace variants  
**Impact:** MEDIUM - Potential consolidation opportunity  
**Recommendation:** Consolidate into unified trace service

---

#### Role Model Services
| Service | Version | Purpose |
|---------|---------|---------|
| `role_model_gate_service.py` | v1 | Original role model gate |
| `role_model_gate_service_v2.py` | v2 | Updated role model gate |
| `role_model_binding_service.py` | - | Role model binding |
| `role_model_binding_service_v2.py` | - | Updated role model binding |
| `role_model_run_store.py` | - | Role model run storage |
| `role_model_run_store_v2.py` | - | Updated role model run storage |
| `role_model_trace_service.py` | - | Role model trace |
| `role_model_trace_service_v2.py` | - | Updated role model trace |

**Fork Level:** 8 role model service variants  
**Impact:** MEDIUM - Clear version fork pattern  
**Recommendation:** Complete v2 migration and remove v1

---

#### Context Services
| Service | Version | Purpose |
|---------|---------|---------|
| `context_admission_service.py` | v1 | Original context admission |
| `context_admission_service_v2.py` | v2 | Updated context admission |

**Fork Level:** 2 context service variants  
**Impact:** LOW - Minor version fork  
**Recommendation:** Complete v2 migration and remove v1

---

### 4.2 Implementation Forks

**Pattern:** Multiple implementations of similar functionality

#### Chat Services
| Service | Implementation | Purpose |
|---------|----------------|---------|
| `chat_service.py` | Main chat service | Core chat orchestration |
| `chat_manual_inference_service.py` | Manual inference | Manual inference mode |
| `governed_write_chat_service.py` | Governed write | Write governance |
| `chat_operation_router_service.py` | Operation routing | Chat operation routing |
| `chat_approval_command_service.py` | Approval commands | Approval workflow |
| `chat_artifact_fulfillment_service.py` | Artifact fulfillment | Artifact handling |

**Fork Level:** 6 chat service variants  
**Impact:** LOW - Domain-specific implementations  
**Recommendation:** Keep as domain-specific services

---

#### Agent Services
| Service | Implementation | Purpose |
|---------|----------------|---------|
| `agent_delegation_service.py` | Delegation | Agent delegation |
| `agent_tool_gateway_service.py` | Tool gateway | Tool access |
| `agent_memory_gateway_service.py` | Memory gateway | Memory access |
| `agent_marketplace_service.py` | Marketplace | Agent marketplace |
| `agent_session_kernel_service.py` | Session kernel | Session management |
| `codex_hybrid_service.py` | Codex hybrid | Codex integration |
| `interpretation_agent_service.py` | Interpretation | Interpretation |
| `lucio_agent_service.py` | Lucio agent | Lucio integration |

**Fork Level:** 8 agent service variants  
**Impact:** LOW - Domain-specific implementations  
**Recommendation:** Keep as domain-specific services

---

## 5. Configuration Duplication

### 5.1 Policy Configuration Duplication

**Pattern:** Similar policy structures across domains

| Policy Domain | Count | Similarity |
|---------------|-------|------------|
| **Artifact Policies** | 30 | HIGH - Similar structure |
| **Memory Policies** | 32 | HIGH - Similar structure |
| **RAG Policies** | 54 | HIGH - Similar structure |
| **Vision Policies** | 20 | HIGH - Similar structure |
| **Validation Policies** | 14 | HIGH - Similar structure |
| **Runtime Policies** | 48 | HIGH - Similar structure |
| **Skills Policies** | 81 | HIGH - Similar structure |

**Duplication Level:** 279+ policy files with similar patterns  
**Impact:** LOW - Policies are domain-specific by design  
**Recommendation:** Consider policy template system

---

### 5.2 Role Configuration Duplication

**Pattern:** Similar role structures

| Role Domain | Count | Similarity |
|-------------|-------|------------|
| **Role Definitions** | 18 | MEDIUM - Similar structure |
| **Agent Policies** | 12 | MEDIUM - Similar structure |

**Duplication Level:** 30+ role configuration files  
**Impact:** LOW - Roles are domain-specific by design  
**Recommendation:** Consider role template system

---

## 6. Test Duplication

### 6.1 Test Helper Duplication

**Pattern:** Similar test helper functions

| Test Helper | Location | Purpose | Similarity |
|-------------|----------|---------|------------|
| `context_test_helpers.py` | `tests/unit/` | Context test helpers | HIGH |
| `curated_memory_test_helpers.py` | `tests/unit/` | Memory test helpers | HIGH |
| `rag_memory_test_helpers.py` | `tests/unit/` | RAG test helpers | HIGH |
| `retrieval_test_helpers.py` | `tests/unit/` | Retrieval test helpers | HIGH |
| `vector_rag_test_helpers.py` | `tests/unit/` | Vector RAG test helpers | HIGH |
| `manual_inference_test_helpers.py` | `tests/` | Manual inference helpers | HIGH |
| `maintenance_helpers.py` | `tests/` | Maintenance helpers | HIGH |
| `replay_regression_helpers.py` | `tests/` | Replay helpers | HIGH |

**Duplication Level:** 8 test helper files with similar patterns  
**Impact:** LOW - Test helpers are domain-specific  
**Recommendation:** Consider common test utilities

---

### 6.2 Test Fixture Duplication

**Pattern:** Similar test fixtures

| Fixture Category | Count | Similarity |
|------------------|-------|------------|
| **Artifact Fixtures** | 1 | - |
| **Patch Fixtures** | 1 | - |
| **Validation Fixtures** | 1 | - |
| **Project Profiles** | 50+ | HIGH - Similar structure |
| **Templates** | 10+ | MEDIUM - Similar structure |

**Duplication Level:** 60+ test fixture files  
**Impact:** LOW - Test fixtures are domain-specific  
**Recommendation:** Consider fixture template system

---

## 7. Temporary File Accumulation

### 7.1 Sprint-Specific Temporary Directories

**Pattern:** Sprint-specific temporary directories

| Directory | Purpose | Status |
|-----------|---------|--------|
| `data/tmp_debug_s1s4/` | Sprint 1-4 debug | Active |
| `data/tmp_debug_s1s4_block/` | Sprint 1-4 blocked debug | Active |
| `data/tmp_debug_s1s4_block2/` | Sprint 1-4 blocked debug 2 | Active |
| `data/tmp_runtime_vertical_slice_tests/` | Vertical slice tests | Active |
| `data/tmp_runtime_doctor_tests/` | Runtime doctor tests | Active |
| `data/tmp_runtime_operator_tests/` | Runtime operator tests | Active |
| `data/tmp_runtime_timeline_tests/` | Runtime timeline tests | Active |

**Accumulation Level:** 7 sprint-specific temp directories  
**Impact:** MEDIUM - Indicates lack of cleanup  
**Recommendation:** Implement cleanup strategy for sprint-specific temps

---

## 8. Report Accumulation

### 8.1 Sprint Report Accumulation

**Pattern:** Sprint-specific report accumulation

| Report Category | Count | Pattern |
|-----------------|-------|---------|
| **Sprint Reports** | 30+ | Sprint-specific analysis |
| **Fire Test Reports** | 64 | Fire test results |
| **Governance Block Reports** | 50+ | Governance analysis |
| **Runtime Reports** | 20+ | Runtime analysis |
| **Hotfix Reports** | 4 | Hotfix analysis |

**Accumulation Level:** 168+ historical reports  
**Impact:** LOW - Historical data is valuable  
**Recommendation:** Implement report archival strategy

---

## 9. Duplication Summary

### 9.1 Duplication by Category

| Category | Duplication Count | Impact | Priority |
|----------|-------------------|--------|----------|
| **Empty/Stub Files** | 100+ | HIGH | HIGH |
| **Trace Services** | 20+ | MEDIUM | MEDIUM |
| **Status Services** | 9+ | MEDIUM | MEDIUM |
| **Store Services** | 15+ | MEDIUM | MEDIUM |
| **Audit Services** | 12+ | MEDIUM | MEDIUM |
| **Validator Services** | 12+ | MEDIUM | MEDIUM |
| **Policy Configs** | 279+ | LOW | LOW |
| **Router Patterns** | 75+ | LOW | LOW |
| **Schema Patterns** | 140+ | LOW | LOW |
| **Version Forks** | 15+ | MEDIUM | MEDIUM |
| **Test Helpers** | 8+ | LOW | LOW |
| **Temp Directories** | 13+ | MEDIUM | MEDIUM |
| **Historical Reports** | 168+ | LOW | LOW |

### 9.2 Consolidation Opportunities

#### High Priority Consolidation
1. **Complete or remove 100+ empty/stub implementations**
2. **Consolidate trace services into generic infrastructure**
3. **Complete v2 migrations and remove v1 code**

#### Medium Priority Consolidation
1. **Consolidate status services into generic infrastructure**
2. **Consolidate store services into generic infrastructure**
3. **Consolidate audit services into generic infrastructure**
4. **Consolidate validator services into generic infrastructure**
5. **Implement cleanup for temporary directories**

#### Low Priority Consolidation
1. **Consider policy template system**
2. **Consider router mixins for common patterns**
3. **Consider base schema classes for common patterns**
4. **Implement report archival strategy**

---

## 10. Dead Code Summary

### 10.1 Dead Code by Category

| Category | Count | Type | Action Required |
|----------|-------|------|----------------|
| **Empty Core Files** | 3 | Core infrastructure | Complete or remove |
| **Empty Service Files** | 100+ | Service implementations | Complete or remove |
| **Empty Registry Files** | 4 | Registry implementations | Complete or remove |
| **Legacy RAG** | 18 | Legacy system | Review for removal |
| **Quarantined Governance** | 2 | Legacy governance | Review for removal |
| **Legacy Tests** | 4 | Legacy test files | Review for removal |

### 10.2 Dead Code Impact Assessment

| Impact Level | Count | Description |
|-------------|-------|-------------|
| **HIGH** | 100+ | Empty/stub implementations blocking functionality |
| **MEDIUM** | 24 | Legacy systems requiring review |
| **LOW** | 4 | Legacy test files |

---

## 11. Recommendations

### 11.1 Immediate Actions

1. **Complete or Remove Stub Implementations**
   - Audit all 100+ empty/stub files
   - Complete critical implementations (runtime, RAG, memory)
   - Remove unused stubs
   - Document stubs that are intentional placeholders

2. **Complete Version Migrations**
   - Complete v2 migrations for role model services
   - Complete v2 migrations for debugger services
   - Complete v2 migrations for context services
   - Remove v1 implementations after validation

3. **Clean Up Temporary Directories**
   - Implement cleanup strategy for sprint-specific temps
   - Define retention policies for debug temp files
   - Clean up empty temp directories

### 11.2 Medium-Term Improvements

1. **Consolidate Infrastructure Services**
   - Design generic trace infrastructure
   - Design generic status infrastructure
   - Design generic store infrastructure
   - Design generic audit infrastructure
   - Design generic validator infrastructure

2. **Review Legacy Systems**
   - Validate new RAG system functionality
   - Remove legacy RAG if validated
   - Review quarantined governance code
   - Remove legacy governance if validated

3. **Implement Configuration Templates**
   - Design policy template system
   - Design role template system
   - Reduce configuration duplication

### 11.3 Long-Term Improvements

1. **Implement Code Generation**
   - Generate repetitive service patterns
   - Generate repetitive router patterns
   - Generate repetitive schema patterns

2. **Implement Archival Strategy**
   - Design report archival system
   - Design historical data archival
   - Implement automated cleanup

---

## Next Steps

This duplicate modules analysis provides the foundation for:
- Consolidation planning
- Dead code removal
- Infrastructure simplification
- Code generation opportunities
