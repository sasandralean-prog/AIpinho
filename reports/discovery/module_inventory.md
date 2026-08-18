# AIpinho Module Inventory

**Generated:** 2026-07-28  
**Purpose:** Complete module classification and responsibility mapping  
**Scope:** All source code modules in `src/aipinho/`

---

## Executive Summary

AIpinho contains **2,340+ Python source files** organized into a layered architecture with clear separation of concerns. The system demonstrates extensive modularity with specialized services for each domain.

---

## Module Classification

### 1. Core Infrastructure (`src/aipinho/core/`)

**Responsibility:** Foundation infrastructure and cross-cutting concerns

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `bootstrap.py` | 194 | Application bootstrap | HIGH |
| `dependency_container.py` | 1,161 | Dependency injection | HIGH |
| `local_environment.py` | 1,299 | Environment configuration | HIGH |
| `paths.py` | 683 | Path resolution | MEDIUM |
| `exceptions.py` | 622 | Exception definitions | MEDIUM |
| `result.py` | 464 | Result type wrapper | MEDIUM |
| `clock.py` | 0 | Time abstraction | LOW |
| `lifecycle.py` | 0 | Lifecycle management | LOW |
| `ids.py` | 0 | ID generation | LOW |

**Dependencies:** None (foundation layer)  
**Consumers:** All other modules  
**Status:** Stable foundation

—

### 2. API Layer (`src/aipinho/api/`)

**Responsibility:** HTTP API endpoints and routing

**Total Routers:** 139 router modules

#### Key Router Categories

| Category | Count | Examples | Responsibility |
|----------|-------|----------|-----------------|
| **Core Routers** | 15 | `health_router.py`, `config_router.py`, `policy_router.py` | Core system endpoints |
| **Chat Routers** | 5 | `chat_router.py`, `session_router.py`, `intent_router.py` | Chat orchestration |
| **Task Routers** | 8 | `task_runtime_router.py`, `task_draft_router.py`, `task_router.py` | Task management |
| **Tool Routers** | 6 | `tool_router.py`, `tool_registry_router.py`, `tool_execution_router.py` | Tool execution |
| **Artifact Routers** | 5 | `artifact_router.py`, `artifact_write_router.py`, `artifact_library_router.py` | Artifact management |
| **Model Routers** | 8 | `model_router.py`, `model_doctor_router.py`, `role_model_router.py` | Model management |
| **RAG Routers** | 6 | `rag_router.py`, `vector_rag_router.py`, `rag_memory_router.py` | RAG operations |
| **Agent Routers** | 8 | `agent_kernel_router.py`, `agent_delegation_router.py`, `agent_bridge_router.py` | Multi-agent system |
| **Governance Routers** | 12 | `governance_lifecycle_router.py`, `approval_router.py`, `capability_router.py` | Governance |
| **Validation Routers** | 3 | `validation_router.py`, `report_router.py`, `evals_router.py` | Validation |
| **Debugging Routers** | 4 | `debugger_router.py`, `debug_trace_router.py`, `debugger_inspector_router.py` | Debugging |
| **Maintenance Routers** | 6 | `maintenance_router.py`, `maintenance_diagnosis_router.py`, `maintenance_repair_router.py` | Maintenance |
| **Mobile Routers** | 6 | `mobile_view_model_router.py`, `mobile_pairing_router.py`, `mobile_status_router.py` | Mobile integration |
| **Vision Routers** | 3 | `vision_router.py`, `ocr_router.py`, `vision_rag_router.py` | Vision/OCR |
| **Skill Routers** | 6 | `skill_router.py`, `skill_catalog_router.py`, `skill_runtime_router.py` | Skills system |
| **Supervisor Routers** | 5 | `monitor_router.py`, `backend_control_router.py`, `bootstrap_control_router.py` | Service supervision |
| **Regression Routers** | 4 | `regression_router.py`, `regression_suite_router.py`, `regression_report_router.py` | Regression testing |
| **Replay Routers** | 4 | `replay_router.py`, `report_router.py`, `event_router.py` | Replay system |
| **Context Routers** | 5 | `context_router.py`, `context_policy_router.py`, `context_cache_router.py` | Context management |
| **Memory Routers** | 4 | `memory_router.py`, `curated_memory_router.py`, `memory_approval_router.py` | Memory management |
| **Workspace Routers** | 5 | `workspace_flow_router.py`, `workspace_index_router.py`, `workspace_lock_router.py` | Workspace management |
| **Analysis Routers** | 3 | `analysis_router.py`, `project_analysis_router.py`, `project_profiles_router.py` | Analysis |
| **Patching Routers** | 5 | `patch_planning_router.py`, `patch_apply_router.py`, `patch_quality_router.py` | Patch operations |
| **External Routers** | 4 | `external_collaboration_router.py`, `external_gateway_router.py`, `connection_router.py` | External integration |
| **Workflow Routers** | 2 | `workflow_router.py`, `pipeline_sync_router.py` | Workflows |
| **Transfer Routers** | 2 | `transfer_router.py`, `sync_router.py` | Data transfer |
| **UX Routers** | 2 | `ux_router.py`, `feedback_router.py` | User experience |
| **Template Routers** | 2 | `template_router.py`, `prompt_router.py` | Templates |
| **Event Routers** | 4 | `event_router.py`, `event_search_router.py`, `event_contract_router.py` | Events |
| **Semantic Routers** | 2 | `semantic_learning_router.py`, `learning_router.py` | Semantic learning |
| **Cognitive Routers** | 2 | `cognitive_governance_router.py`, `hybrid_agent_router.py` | Cognitive governance |
| **Codex Routers** | 2 | `codex_agent_router.py`, `mobile_codex_router.py` | Codex integration |
| **Gemini Routers** | 2 | `gemini_executor_router.py`, `llama_cpp_router.py` | Model execution |
| **Lucio Routers** | 2 | `lucio_agent_router.py`, `agent_tool_gateway_router.py` | Lucio agent |
| **Pinhoforge Routers** | 2 | `pinhoforge_bridge_router.py`, `promotion_router.py` | Pinhoforge integration |
| **Runtime Routers** | 6 | `runtime_operator_router.py`, `runtime_doctor_router.py`, `runtime_dashboard_router.py` | Runtime operations |
| **Self-Healing Routers** | 2 | `self_healing_router.py`, `runtime_hygiene_router.py` | Self-healing |
| **Multi-Island Routers** | 2 | `multi_island_artifact_router.py`, `multi_agent_dashboard_router.py` | Multi-island |
| **Realtime Routers** | 2 | `realtime_router.py`, `telemetry_router.py` | Realtime operations |
| **Sandbox Routers** | 2 | `sandbox_router.py`, `raw_viewer_router.py` | Sandbox |
| **Universal Routers** | 2 | `universal_approver_router.py`, `public_runtime_api_router.py` | Universal operations |

**Dependencies:** Services layer, Schemas layer  
**Consumers:** External API clients  
**Status:** Comprehensive API coverage

—

### 3. Services Layer (`src/aipinho/services/`)

**Responsibility:** Business logic and domain services

**Total Service Modules:** 1,182+ modules

#### 3.1 Runtime Services (56 modules)

**Responsibility:** Task execution and runtime management

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `task_runtime_service.py` | 44,751 | Core task runtime orchestration | CRITICAL |
| `execution_graph_service.py` | 36,208 | Execution graph management | HIGH |
| `intelligent_planner_service.py` | 21,690 | Intelligent planning | HIGH |
| `governed_task_step_runner.py` | 20,228 | Governed step execution | HIGH |
| `runtime_doctor_service.py` | 25,153 | Runtime diagnostics | HIGH |
| `runtime_operator_doctor_service.py` | 15,360 | Operator diagnostics | HIGH |
| `runtime_state_hygiene_service.py` | 19,120 | Runtime state management | HIGH |
| `runtime_timeline_service.py` | 18,968 | Timeline tracking | HIGH |
| `runtime_truth_engine.py` | 10,184 | Truth validation | HIGH |
| `task_queue_service.py` | 17,234 | Task queue management | HIGH |
| `universal_task_session_service.py` | 21,489 | Universal session management | HIGH |
| `supervised_execution_loop.py` | 12,018 | Supervised execution | HIGH |
| `readonly_task_step_runner.py` | 10,317 | Read-only execution | HIGH |
| `tool_governance_service.py` | 15,396 | Tool governance | HIGH |
| `task_run_guard.py` | 12,997 | Task run guard | MEDIUM |
| `workspace_context_service.py` | 11,125 | Workspace context | MEDIUM |
| `runtime_kernel_service.py` | 12,121 | Runtime kernel | MEDIUM |
| `runtime_contracts_v2_service.py` | 10,616 | Runtime contracts | MEDIUM |
| `evidence_engine_service.py` | 9,479 | Evidence collection | MEDIUM |
| `task_run_chat_result_publisher_service.py` | 8,242 | Chat result publishing | MEDIUM |
| `engineering_autopilot_service.py` | 8,674 | Engineering autopilot | MEDIUM |
| `continuous_runtime_service.py` | 5,165 | Continuous runtime | MEDIUM |
| `delegation_polling_service.py` | 5,262 | Delegation polling | MEDIUM |
| `canonical_operation_state_service.py` | 8,083 | Operation state | MEDIUM |
| `task_run_result_service.py` | 6,745 | Task results | MEDIUM |
| `task_run_store.py` | 5,965 | Task storage | MEDIUM |
| `workflow_runtime_service.py` | 11,625 | Workflow runtime | MEDIUM |
| `project_generation_plan_executor.py` | 7,045 | Project generation | MEDIUM |
| `task_no_change_evidence_service.py` | 6,831 | No-change evidence | MEDIUM |
| `health_semantics_service.py` | 2,746 | Health semantics | LOW |
| `delegation_decision_engine.py` | 3,609 | Delegation decisions | LOW |
| `delegation_truth_validator.py` | 1,655 | Delegation validation | LOW |
| `planner_v2_service.py` | 4,733 | Planning v2 | LOW |
| `runtime_dispatcher_v2_service.py` | 4,053 | Runtime dispatcher | LOW |
| `runtime_profile_service.py` | 3,689 | Runtime profiles | LOW |
| `task_block_cause_service.py` | 4,463 | Block cause analysis | LOW |
| `task_bootstrap_runtime_service.py` | 5,007 | Bootstrap runtime | LOW |
| `task_queue_maintenance_service.py` | 1,027 | Queue maintenance | LOW |
| `task_run_audit_service.py` | 1,177 | Task audit | LOW |
| `task_run_cancellation_service.py` | 2,059 | Cancellation | LOW |
| `task_run_event_service.py` | 1,550 | Event service | LOW |
| `task_run_context_service.py` | 1,226 | Context service | LOW |
| `task_run_executor.py` | 503 | Executor | LOW |
| `task_run_lifecycle_service.py` | 1,790 | Lifecycle | LOW |
| `task_run_planner.py` | 5,568 | Planner | LOW |
| `task_run_trace_service.py` | 594 | Trace | LOW |
| `worker_registry_service.py` | 4,413 | Worker registry | LOW |
| `cancellation_service.py` | 0 | Cancellation | LOW |
| `execution_context.py` | 0 | Execution context | LOW |
| `retry_policy_service.py` | 0 | Retry policy | LOW |
| `runtime_guard.py` | 0 | Runtime guard | LOW |
| `step_runner.py` | 0 | Step runner | LOW |
| `task_runner.py` | 0 | Task runner | LOW |
| `timeout_service.py` | 0 | Timeout | LOW |

**Dependencies:** Core, Repositories, Schemas  
**Consumers:** API layer, Other services  
**Status:** Core runtime engine

#### 3.2 Chat Services (29 modules)

**Responsibility:** Chat orchestration and conversation management

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `chat_service.py` | 187,503 | Core chat orchestration | CRITICAL |
| `chat_operation_router_service.py` | 75,664 | Chat operation routing | HIGH |
| `chat_approval_command_service.py` | 35,916 | Approval commands | HIGH |
| `chat_artifact_fulfillment_service.py` | 25,435 | Artifact fulfillment | HIGH |
| `governed_write_chat_service.py` | 28,782 | Governed write | HIGH |
| `chat_permission_grant_service.py` | 12,769 | Permission grants | MEDIUM |
| `permission_status_response_service.py` | 10,252 | Permission status | MEDIUM |
| `session_execution_report_service.py` | 9,241 | Session reports | MEDIUM |
| `chat_manual_inference_service.py` | 13,880 | Manual inference | MEDIUM |
| `workspace_metadata_query_service.py` | 8,315 | Workspace queries | MEDIUM |
| `session_grant_service.py` | 7,212 | Session grants | MEDIUM |
| `chat_model_policy_service.py` | 5,971 | Model policy | MEDIUM |
| `chat_persistence_gate_service.py` | 7,832 | Persistence gate | MEDIUM |
| `followup_result_review_service.py` | 4,248 | Followup review | MEDIUM |
| `blocked_policy_response_service.py` | 4,930 | Blocked responses | LOW |
| `chat_attachment_context_service.py` | 3,524 | Attachment context | LOW |
| `chat_model_fallback_service.py` | 1,978 | Model fallback | LOW |
| `chat_model_response_service.py` | 3,761 | Model response | LOW |
| `chat_response_policy_service.py` | 1,985 | Response policy | LOW |
| `chat_result_index_service.py` | 3,274 | Result indexing | LOW |
| `chat_inference_trace_service.py` | 727 | Inference trace | LOW |
| `chat_manual_inference_audit_service.py` | 3,804 | Inference audit | LOW |
| `chat_router_service.py` | 474 | Router | LOW |
| `chat_context_builder.py` | 253 | Context builder | LOW |
| `artifact_request_preview_service.py` | 2,308 | Artifact preview | LOW |
| `readonly_project_analysis_preview_service.py` | 2,390 | Analysis preview | LOW |
| `session_diagnostic_service.py` | 2,283 | Diagnostics | LOW |
| `governed_configuration_change_chat_service.py` | 3,300 | Config changes | LOW |

**Dependencies:** Runtime services, Policy kernel, Memory  
**Consumers:** API layer, Agent services  
**Status:** Core conversation engine

#### 3.3 Agent Services (31 modules)

**Responsibility:** Multi-agent system and agent orchestration

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `agent_tool_gateway_service.py` | 76,204 | Tool gateway | CRITICAL |
| `agent_local_action_planner.py` | 59,957 | Local action planning | HIGH |
| `multi_agent_observability_service.py` | 47,154 | Multi-agent observability | HIGH |
| `agent_delegation_service.py` | 19,736 | Agent delegation | HIGH |
| `agent_memory_gateway_service.py` | 23,605 | Memory gateway | HIGH |
| `agent_session_kernel_service.py` | 27,719 | Session kernel | HIGH |
| `agent_delegation_policy_service.py` | 12,857 | Delegation policy | MEDIUM |
| `multi_agent_policy_kernel_service.py` | 23,854 | Policy kernel | MEDIUM |
| `agent_marketplace_service.py` | 13,151 | Agent marketplace | MEDIUM |
| `agent_tool_policy_service.py` | 1,717 | Tool policy | MEDIUM |
| `agent_memory_policy_service.py` | 7,178 | Memory policy | MEDIUM |
| `agent_request_enrichment_service.py` | 4,008 | Request enrichment | MEDIUM |
| `agent_event_bus.py` | 8,148 | Event bus | MEDIUM |
| `agent_session_store.py` | 9,287 | Session storage | MEDIUM |
| `agent_tool_invocation_store.py` | 4,516 | Tool invocation storage | MEDIUM |
| `agent_delegation_store.py` | 3,468 | Delegation storage | MEDIUM |
| `agent_memory_gateway_store.py` | 6,712 | Memory gateway storage | MEDIUM |
| `agent_tool_workspace_resolver.py` | 6,220 | Workspace resolution | MEDIUM |
| `agent_tool_registry_service.py` | 2,321 | Tool registry | MEDIUM |
| `agent_profile_registry_service.py` | 3,053 | Profile registry | MEDIUM |
| `workspace_lock_service.py` | 9,299 | Workspace locking | MEDIUM |
| `agent_timeline_mapper.py` | 4,527 | Timeline mapping | LOW |
| `agent_delegation_adapters.py` | 2,437 | Delegation adapters | LOW |
| `agent_text_artifact_service.py` | 2,003 | Text artifacts | LOW |
| `canonical_prompt_builder_service.py` | 1,786 | Prompt building | LOW |
| `codex_hybrid_service.py` | 11,188 | Codex hybrid | LOW |
| `delegation_log_summary_service.py` | 2,246 | Log summary | LOW |
| `hybrid_execution_policy_service.py` | 1,438 | Hybrid policy | LOW |
| `interpretation_agent_service.py` | 9,354 | Interpretation | LOW |

**Dependencies:** Chat services, Runtime, Policy kernel  
**Consumers:** API layer, External systems  
**Status:** Multi-agent orchestration

#### 3.4 RAG Services (83 modules)

**Responsibility:** Retrieval-Augmented Generation

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `retrieval_service.py` | 8,314 | Core retrieval | HIGH |
| `workspace_index_service.py` | 13,195 | Workspace indexing | HIGH |
| `retrieval_scope_service.py` | 3,349 | Retrieval scoping | MEDIUM |
| `retrieval_source_policy_service.py` | 2,788 | Source policy | MEDIUM |
| `retrieval_source_registry.py` | 3,140 | Source registry | MEDIUM |
| `retrieval_status_service.py` | 3,433 | Status service | MEDIUM |
| `retrieval_router_service.py` | 1,506 | Retrieval routing | MEDIUM |
| `retrieval_context_builder.py` | 2,350 | Context building | MEDIUM |
| `retrieval_executor.py` | 2,421 | Retrieval execution | MEDIUM |
| `retrieval_ranker.py` | 1,224 | Ranking | MEDIUM |
| `retrieval_dedupe_service.py` | 633 | Deduplication | LOW |
| `retrieval_budget_service.py` | 1,228 | Budget management | LOW |
| `retrieval_query_service.py` | 1,096 | Query service | LOW |
| `retrieval_sensitivity_filter.py` | 1,820 | Sensitivity filtering | LOW |
| `source_ref_validator.py` | 1,353 | Reference validation | LOW |
| `source_registry_service.py` | 184 | Source registry | LOW |
| `rag_service.py` | 784 | RAG service | LOW |
| `citation_builder.py` | 1,096 | Citation building | LOW |
| `citation_service.py` | 0 | Citation service | LOW |
| `evidence_bundle_builder.py` | 1,035 | Evidence building | LOW |
| `retrieval_audit_service.py` | 1,541 | Retrieval audit | LOW |
| `retrieval_trace_service.py` | 537 | Trace service | LOW |
| `chunking_service.py` | 0 | Chunking | LOW |
| `embedding_service.py` | 0 | Embeddings | LOW |
| `rag_context_builder.py` | 0 | Context builder | LOW |
| `rag_audit_service.py` | 0 | RAG audit | LOW |
| `rerank_service.py` | 0 | Reranking | LOW |
| `vectorstore_service.py` | 0 | Vectorstore | LOW |

**Dependencies:** Memory services, Vector stores  
**Consumers:** Chat services, Agent services  
**Status:** RAG infrastructure

#### 3.5 Memory Services (44 modules)

**Responsibility:** Memory management and curation

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `learning_memory_service.py` | 29,586 | Learning memory | HIGH |
| `memory_candidate_service.py` | 11,552 | Memory candidates | HIGH |
| `curated_memory_store.py` | 7,397 | Curated storage | MEDIUM |
| `memory_candidate_store.py` | 6,009 | Candidate storage | MEDIUM |
| `memory_candidate_extractor.py` | 7,610 | Candidate extraction | MEDIUM |
| `curated_memory_persistence_service.py` | 4,619 | Persistence | MEDIUM |
| `memory_candidate_source_resolver.py` | 3,440 | Source resolution | MEDIUM |
| `memory_candidate_scope_service.py` | 2,253 | Scope service | MEDIUM |
| `operational_memory_service.py` | 11,409 | Operational memory | MEDIUM |
| `memory_approval_service.py` | 1,216 | Approval service | MEDIUM |
| `memory_approval_bridge.py` | 4,022 | Approval bridge | MEDIUM |
| `memory_candidate_validator.py` | 1,760 | Candidate validation | LOW |
| `memory_candidate_classifier.py` | 1,388 | Classification | LOW |
| `memory_candidate_conflict_service.py` | 1,171 | Conflict handling | LOW |
| `memory_candidate_dedupe_service.py` | 1,882 | Deduplication | LOW |
| `memory_candidate_risk_service.py` | 1,312 | Risk assessment | LOW |
| `memory_candidate_sensitivity_scanner.py` | 1,808 | Sensitivity scanning | LOW |
| `memory_candidate_evidence_service.py` | 1,964 | Evidence service | LOW |
| `memory_candidate_event_service.py` | 496 | Event service | LOW |
| `memory_candidate_status_service.py` | 405 | Status service | LOW |
| `memory_candidate_trace_service.py` | 350 | Trace service | LOW |
| `curated_memory_service.py` | 4,383 | Curated memory | LOW |
| `curated_memory_search_service.py` | 1,096 | Search service | LOW |
| `curated_memory_validator.py` | 1,924 | Validation | LOW |
| `curated_memory_version_service.py` | 1,064 | Versioning | LOW |
| `curated_memory_status_service.py` | 406 | Status | LOW |
| `curated_memory_trace_service.py` | 340 | Trace | LOW |
| `curated_memory_audit_service.py` | 495 | Audit | LOW |
| `curated_memory_event_service.py` | 480 | Events | LOW |
| `memory_persistence_guard.py` | 2,701 | Persistence guard | LOW |
| `memory_read_policy_service.py` | 634 | Read policy | LOW |
| `memory_expiration_service.py` | 772 | Expiration | LOW |
| `memory_supersede_service.py` | 1,645 | Supersede | LOW |
| `memory_conflict_resolution_service.py` | 473 | Conflict resolution | LOW |
| `memory_dedupe_resolution_service.py` | 676 | Dedupe resolution | LOW |
| `memory_audit_service.py` | 0 | Audit | LOW |
| `memory_conflict_service.py` | 0 | Conflict | LOW |
| `memory_curator_service.py` | 0 | Curation | LOW |
| `memory_embedding_service.py` | 0 | Embeddings | LOW |
| `memory_retention_service.py` | 0 | Retention | LOW |
| `memory_search_service.py` | 0 | Search | LOW |
| `memory_service.py` | 0 | Memory service | LOW |

**Dependencies:** RAG services, Validation  
**Consumers:** Chat services, Agent services  
**Status:** Memory management

#### 3.6 Artifact Services (47 modules)

**Responsibility:** Artifact generation and management

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `artifact_library_service.py` | 23,873 | Artifact library | HIGH |
| `artifact_generator_service.py` | 13,114 | Artifact generation | HIGH |
| `universal_artifact_registry_service.py` | 14,111 | Universal registry | HIGH |
| `artifact_write_execution_service.py` | 14,268 | Write execution | HIGH |
| `artifact_path_archive_service.py` | 13,371 | Path archiving | HIGH |
| `workspace_evidence_bundle_service.py` | 20,886 | Evidence bundles | HIGH |
| `workspace_readonly_audit_report_service.py` | 14,323 | Audit reports | MEDIUM |
| `workspace_static_reachability_report_service.py` | 8,930 | Reachability reports | MEDIUM |
| `artifact_interaction_core.py` | 10,236 | Interaction core | MEDIUM |
| `artifact_runtime_service.py` | 8,374 | Runtime service | MEDIUM |
| `artifact_writer_preview_service.py` | 10,078 | Writer preview | MEDIUM |
| `artifact_path_guard_service.py` | 7,414 | Path guarding | MEDIUM |
| `artifact_write_guard_service.py` | 6,679 | Write guarding | MEDIUM |
| `artifact_source_resolver.py` | 6,216 | Source resolution | MEDIUM |
| `artifact_approval_bridge.py` | 4,982 | Approval bridge | MEDIUM |
| `artifact_write_store.py` | 5,776 | Write storage | MEDIUM |
| `artifact_preview_store.py` | 6,582 | Preview storage | MEDIUM |
| `task_run_artifact_export_service.py` | 3,646 | Artifact export | MEDIUM |
| `artifact_content_validator.py` | 4,361 | Content validation | MEDIUM |
| `artifact_risk_service.py` | 3,188 | Risk assessment | MEDIUM |
| `artifact_diff_preview_service.py` | 2,928 | Diff preview | MEDIUM |
| `artifact_target_policy_service.py` | 2,734 | Target policy | MEDIUM |
| `artifact_overwrite_policy_service.py` | 1,716 | Overwrite policy | MEDIUM |
| `artifact_post_write_validator.py` | 2,542 | Post-write validation | MEDIUM |
| `artifact_format_validator.py` | 2,503 | Format validation | MEDIUM |
| `artifact_secret_scanner.py` | 935 | Secret scanning | LOW |
| `artifact_backup_service.py` | 2,888 | Backup service | LOW |
| `artifact_atomic_write_service.py` | 2,517 | Atomic write | LOW |
| `artifact_draft_service.py` | 1,823 | Draft service | LOW |
| `artifact_write_lifecycle_service.py` | 1,058 | Write lifecycle | LOW |
| `artifact_write_event_service.py` | 819 | Write events | LOW |
| `artifact_write_audit_service.py` | 486 | Write audit | LOW |
| `artifact_write_reconciliation_service.py` | 683 | Reconciliation | LOW |
| `artifact_trace_service.py` | 524 | Trace service | LOW |
| `artifact_service_status.py` | 254 | Service status | LOW |
| `artifact_link_policy_service.py` | 252 | Link policy | LOW |
| `artifact_link_service.py` | 93 | Link service | LOW |
| `artifact_manifest_service.py` | 90 | Manifest service | LOW |
| `artifact_registry_repository.py` | 93 | Registry repository | LOW |
| `artifact_hash_service.py` | 93 | Hash service | LOW |
| `artifact_cleanup_service.py` | 99 | Cleanup | LOW |
| `artifact_download_service.py` | 90 | Download service | LOW |
| `artifact_upload_service.py` | 88 | Upload service | LOW |
| `artifact_zip_service.py` | 85 | Zip service | LOW |
| `chat_report_composer.py` | 818 | Report composer | LOW |

**Dependencies:** Runtime services, Validation  
**Consumers:** Chat services, API layer  
**Status:** Artifact management

#### 3.7 Tool Services (28 modules)

**Responsibility:** Tool execution and governance

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `governed_tool_execution_service.py` | 29,742 | Governed execution | HIGH |
| `tool_safety_service.py` | 11,962 | Tool safety | HIGH |
| `filesystem_read_service.py` | 9,402 | Filesystem reading | HIGH |
| `tool_contract_core.py` | 8,706 | Tool contracts | MEDIUM |
| `tool_registry_service.py` | 7,692 | Tool registry | MEDIUM |
| `tool_preview_service.py` | 6,918 | Tool preview | MEDIUM |
| `tool_execution_guard.py` | 7,847 | Execution guard | MEDIUM |
| `shell_command_policy_service.py` | 4,767 | Shell policy | MEDIUM |
| `write_capability_envelope_service.py` | 5,797 | Write envelope | MEDIUM |
| `tool_dry_run_executor.py` | 6,113 | Dry-run execution | MEDIUM |
| `tool_input_validator.py` | 4,058 | Input validation | MEDIUM |
| `read_only_execution_service.py` | 8,648 | Read-only execution | MEDIUM |
| `execution_audit_service.py` | 5,277 | Execution audit | MEDIUM |
| `tool_router.py` | 1,052 | Tool routing | LOW |
| `tool_execution_service.py` | 1,137 | Execution service | LOW |
| `tool_availability_service.py` | 120 | Availability | LOW |
| `tool_contract_loader.py` | 110 | Contract loader | LOW |
| `tool_contract_validator.py` | 116 | Contract validation | LOW |
| `tool_invocation_preview_service.py` | 130 | Invocation preview | LOW |
| `tool_permission_service.py` | 116 | Permission service | LOW |
| `tool_result_sanitizer.py` | 112 | Result sanitization | LOW |
| `tool_trace_service.py` | 665 | Trace service | LOW |
| `android_tool_service.py` | 0 | Android tools | LOW |
| `browser_tool_service.py` | 0 | Browser tools | LOW |
| `filesystem_tool_service.py` | 0 | Filesystem tools | LOW |
| `git_tool_service.py` | 0 | Git tools | LOW |
| `shell_tool_service.py` | 0 | Shell tools | LOW |

**Dependencies:** Runtime services, Policy kernel  
**Consumers:** Agent services, Chat services  
**Status:** Tool execution framework

#### 3.8 Model Services (47 modules)

**Responsibility:** Model management and execution

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `llama_cpp_provider.py` | 15,439 | LLaMA CPP provider | HIGH |
| `model_invocation_service.py` | 8,798 | Model invocation | HIGH |
| `capability_router_service.py` | 11,960 | Capability routing | MEDIUM |
| `model_doctor_service.py` | 9,763 | Model diagnostics | MEDIUM |
| `model_registry_service.py` | 4,658 | Model registry | MEDIUM |
| `model_router_service.py` | 6,587 | Model routing | MEDIUM |
| `llama_cpp_command_builder.py` | 3,627 | Command building | MEDIUM |
| `llama_smoke_test_service.py` | 7,399 | Smoke testing | MEDIUM |
| `llama_smoke_prompt_service.py` | 5,110 | Smoke prompts | MEDIUM |
| `manual_inference_gate_service.py` | 8,745 | Manual inference gate | MEDIUM |
| `real_inference_gate_service.py` | 7,161 | Real inference gate | MEDIUM |
| `model_path_validator.py` | 5,653 | Path validation | MEDIUM |
| `model_process_runner.py` | 5,622 | Process running | MEDIUM |
| `model_security_validator.py` | 2,960 | Security validation | MEDIUM |
| `model_output_sanitizer.py` | 2,482 | Output sanitization | MEDIUM |
| `llama_cpp_status_service.py` | 3,895 | Status service | MEDIUM |
| `manual_inference_status_service.py` | 3,316 | Manual inference status | MEDIUM |
| `model_status_service.py` | 2,211 | Model status | MEDIUM |
| `model_runtime_policy_service.py` | 1,513 | Runtime policy | MEDIUM |
| `model_runtime_estimator.py` | 2,427 | Runtime estimation | LOW |
| `model_latency_estimator.py` | 1,211 | Latency estimation | LOW |
| `model_hardware_estimator.py` | 1,593 | Hardware estimation | LOW |
| `model_load_probe_service.py` | 1,557 | Load probing | LOW |
| `model_profile_service.py` | 1,921 | Profile service | LOW |
| `manual_inference_profile_service.py` | 2,869 | Manual inference profile | LOW |
| `model_capability_service.py` | 2,263 | Capability service | LOW |
| `model_health_service.py` | 2,237 | Health service | LOW |
| `local_model_path_service.py` | 2,563 | Local model paths | LOW |
| `provider_registry_service.py` | 1,955 | Provider registry | LOW |
| `model_provider_registry_service.py` | 194 | Model provider registry | LOW |
| `model_invocation_audit_service.py` | 590 | Invocation audit | LOW |
| `model_trace_service.py` | 1,310 | Trace service | LOW |
| `inference_runtime_limiter.py` | 2,154 | Runtime limiting | LOW |
| `model_capability_detector_service.py` | 463 | Capability detection | LOW |
| `stub_model_provider.py` | 92 | Stub provider | LOW |
| `modality_service.py` | 0 | Modality service | LOW |
| `model_selector.py` | 0 | Model selector | LOW |
| `token_budget_service.py` | 0 | Token budget | LOW |
| `smoke_test_audit_service.py` | 1,898 | Smoke test audit | LOW |
| `real_inference_run_store.py` | 2,807 | Real inference storage | LOW |

**Dependencies:** External adapters, Runtime services  
**Consumers:** Chat services, Agent services  
**Status:** Model execution framework

#### 3.9 Governance Services (25 modules)

**Responsibility:** Governance and policy enforcement

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `live_alignment_conflict_detector.py` | 23,262 | Alignment conflict detection | HIGH |
| `operation_contract_service.py` | 9,136 | Operation contracts | MEDIUM |
| [Subdirectories] | - | Specialized governance | MEDIUM |

**Dependencies:** Policy kernel, Runtime services  
**Consumers:** All services  
**Status:** Governance layer

#### 3.10 Policy Kernel Services (15 modules)

**Responsibility:** Policy resolution and enforcement

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `policy_kernel_service.py` | 8,747 | Policy kernel core | HIGH |
| `workspace_role_contract_service.py` | 13,006 | Workspace role contracts | HIGH |
| `capability_gate_service.py` | 7,979 | Capability gating | HIGH |
| `effective_policy_builder.py` | 6,181 | Policy building | MEDIUM |
| `policy_context_builder.py` | 4,738 | Policy context | MEDIUM |
| `workspace_policy_service.py` | 5,340 | Workspace policy | MEDIUM |
| `approval_policy_service.py` | 3,949 | Approval policy | MEDIUM |
| `policy_precedence_service.py` | 2,818 | Policy precedence | MEDIUM |
| `action_registry_service.py` | 3,331 | Action registry | MEDIUM |
| `policy_trace_service.py` | 630 | Policy tracing | LOW |
| `memory_policy_resolver.py` | 193 | Memory policy | LOW |
| `model_policy_resolver.py` | 0 | Model policy | LOW |
| `rag_policy_resolver.py` | 216 | RAG policy | LOW |
| `tool_policy_resolver.py` | 213 | Tool policy | LOW |

**Dependencies:** Core, Registries  
**Consumers:** All services  
**Status:** Policy enforcement core

#### 3.11 Skill Services (35 modules)

**Responsibility:** Skill system and execution

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `skill_runtime_core.py` | 32,515 | Skill runtime core | HIGH |
| `skill_manifest_registry_service.py` | 21,575 | Manifest registry | HIGH |
| `skill_pack_registry_service.py` | 24,479 | Pack registry | HIGH |
| `skill_execution_service.py` | 21,470 | Skill execution | MEDIUM |
| `skill_manifest_validator.py` | 119 | Manifest validation | LOW |
| [Many stub services] | - | Skill infrastructure | LOW |

**Dependencies:** Runtime services, Tool services  
**Consumers:** Agent services, Chat services  
**Status:** Skill execution framework

#### 3.12 Validation Services (30 modules)

**Responsibility:** Validation and quality gates

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `validation_gate_service.py` | 10,463 | Validation gates | HIGH |
| `validation_common.py` | 2,706 | Common validation | MEDIUM |
| `contract_compliance_validator.py` | 4,006 | Contract compliance | MEDIUM |
| `side_effect_validator.py` | 4,249 | Side effect validation | MEDIUM |
| `task_result_validator.py` | 1,767 | Task result validation | MEDIUM |
| `task_run_validator.py` | 2,159 | Task run validation | MEDIUM |
| `evidence_compliance_validator.py` | 2,527 | Evidence compliance | MEDIUM |
| `report_quality_gate_service.py` | 3,422 | Report quality gates | MEDIUM |
| `role_pipeline_validator.py` | 3,867 | Role pipeline validation | MEDIUM |
| `workspace_access_validator.py` | 2,231 | Workspace access validation | MEDIUM |
| [Other validators] | - | Specialized validation | LOW |

**Dependencies:** Runtime services, Schemas  
**Consumers:** All services  
**Status:** Validation framework

#### 3.13 Patching Services (70 modules)

**Responsibility:** Patch planning and operations

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `model_assisted_patch_planner_service.py` | 12,075 | Model-assisted planning | HIGH |
| `patch_planning_service.py` | 9,957 | Patch planning | MEDIUM |
| `patch_plan_store.py` | 6,052 | Patch plan storage | MEDIUM |
| `patch_target_guard.py` | 4,110 | Patch target guarding | MEDIUM |
| `patch_validation_service.py` | 2,103 | Patch validation | MEDIUM |
| `patch_risk_service.py` | 1,302 | Patch risk assessment | MEDIUM |
| [Quality subdirectory] | - | Patch quality (26 items) | MEDIUM |
| [Apply subdirectory] | - | Patch application (19 items) | LOW |

**Dependencies:** Runtime services, Model services  
**Consumers:** Chat services, API layer  
**Status:** Patch operations framework

#### 3.14 Other Service Categories

**Vision Services (29 modules):** OCR, image processing, visual analysis  
**Context Services (42 modules):** Context management, caching, filtering  
**Event Services (18 modules):** Event publishing, filtering, search  
**Role Services (30 modules):** Role management, inference, pipelines  
**Maintenance Services (42 modules):** Maintenance plane, diagnostics, repair  
**Debugger Services (33 modules):** Debugging, tracing, inspection  
**Regression Services (30 modules):** Regression testing, comparison  
**Replay Services (32 modules):** Replay capture, execution, diff  
**Supervisor Services (24 modules):** Service supervision, health checking  
**External Services (6 modules):** External collaboration, gateways  
**Prompt Intelligence Services (15 modules):** Prompt analysis, segmentation  
**Semantic Services (7 modules):** Semantic learning, interpretation  
**Analysis Services (13 modules):** Project analysis, file context  
**Approval Services (8 modules):** Approval workflows, lifecycle  
**Evaluation Services (17 modules):** Evaluation framework, metrics  
**Templates Services (5 modules):** Template management  
**UX Services (11 modules):** UX policies, notifications  
**Security Services (7 modules):** Security policies, validation  
**Self-Healing Services (2 modules):** Self-healing mechanisms  
**Realtime Services (12 modules):** Realtime operations, telemetry  
**Transfer Services (7 modules):** Data transfer, sync  
**Mobile Services (2 modules):** Mobile integration  
**Mobile View Models (42 modules):** Mobile UI models  
**Autopilot Services (1 module):** Autonomous operations  
**Codex Agent Services (8 modules):** Codex integration  
**Lucio Agent Services (7 modules):** Lucio agent  
**Gemini Executor Services (6 modules):** Gemini model execution  
**Pinhoforge Bridge Services (13 modules):** Pinhoforge integration  
**Workspace Flow Services (2 modules):** Workspace workflows  
**Workspace Services (2 modules):** Workspace management  
**Config Governance Services (3 modules):** Configuration governance  
**Interpreter Services (7 modules):** Interpretation services  
**Legacy RAG Services (18 modules):** Legacy RAG system  
**Interaction Services (18 modules):** User interaction  
**Orchestration Services (17 modules):** Workflow orchestration  
**Promotion Services (2 modules):** Promotion workflows  
**Prompts Services (9 modules):** Prompt management  
**Providers Services (9 modules):** Provider management  
**Reports Services (12 modules):** Report generation  
**Sandbox Services (20 modules):** Sandbox management  
**Speaker Services (8 modules):** Speaker/output services  
**Telemetry Services (3 modules):** Telemetry collection  
**Tools Services (28 modules):** Tool execution (detailed above)  
**Validation Services (30 modules):** Validation (detailed above)  

—

### 4. Schemas Layer (`src/aipinho/schemas/`)

**Responsibility:** Pydantic schemas for data validation

**Total Schema Modules:** 910+ modules

#### Key Schema Categories

| Category | Count | Examples | Responsibility |
|----------|-------|----------|-----------------|
| **Common Schemas** | 9 | Common types, base classes | Shared data structures |
| **Chat Schemas** | 16 | ChatRequest, ChatResponse | Chat data structures |
| **Task Schemas** | 13 | TaskRun, TaskDraft | Task data structures |
| **Artifact Schemas** | 34 | Artifact, ArtifactPreview | Artifact data structures |
| **Tool Schemas** | 24 | Tool, ToolExecution | Tool data structures |
| **Model Schemas** | 41 | Model, ModelInvocation | Model data structures |
| **RAG Schemas** | 59 | Retrieval, Citation | RAG data structures |
| **Memory Schemas** | 38 | Memory, MemoryCandidate | Memory data structures |
| **Agent Schemas** | 9 | Agent, AgentDelegation | Agent data structures |
| **Role Schemas** | 26 | Role, RolePipeline | Role data structures |
| **Validation Schemas** | 18 | Validation, ValidationGate | Validation data structures |
| **Patching Schemas** | 51 | PatchPlan, DiffProposal | Patching data structures |
| **Vision Schemas** | 34 | Vision, OCR | Vision data structures |
| **Context Schemas** | 41 | Context, ContextBundle | Context data structures |
| **Event Schemas** | 24 | Event, EventFilter | Event data structures |
| **Governance Schemas** | 6 | Governance, Policy | Governance data structures |
| **Runtime Schemas** | 37 | Runtime, TaskRuntime | Runtime data structures |
| **Skill Schemas** | 36 | Skill, SkillPack | Skill data structures |
| **Maintenance Schemas** | 47 | Maintenance, Diagnosis | Maintenance data structures |
| **Regression Schemas** | 30 | Regression, Replay | Regression data structures |
| **Replay Schemas** | 27 | Replay, ReplayCase | Replay data structures |
| **Debugger Schemas** | 29 | Debugger, Trace | Debugger data structures |
| **Evaluation Schemas** | 21 | Evaluation, Metric | Evaluation data structures |
| **Evals Schemas** | 21 | Evals, EvalSet | Evals data structures |
| **Interaction Schemas** | 41 | Interaction, Feedback | Interaction data structures |
| **Mobile View Models** | 19 | MobileViewModel | Mobile UI models |
| **External Schemas** | 4 | ExternalCollaboration, ExternalGateway | External integration |
| **Prompt Schemas** | 8 | Prompt, PromptAssembly | Prompt data structures |
| **Template Schemas** | 1 | Templates | Template data structures |
| **UX Schemas** | 14 | UX, Notification | UX data structures |
| **Security Schemas** | 3 | Security, Redaction | Security data structures |
| **Self-Healing Schemas** | 1 | SelfHealing | Self-healing data structures |
| **Semantic Schemas** | 5 | SemanticLearning | Semantic data structures |
| **Telemetry Schemas** | 5 | Telemetry, Metric | Telemetry data structures |
| **Transfer Schemas** | 8 | Transfer, Sync | Transfer data structures |
| **Workflow Schemas** | 1 | Workflows | Workflow data structures |
| **Workspace Flow Schemas** | 2 | WorkspaceFlow | Workspace flow data structures |
| **Analysis Schemas** | 10 | Analysis, ProjectAnalysis | Analysis data structures |
| **Intent Schemas** | 9 | Intent, IntentMap | Intent data structures |
| **Projects Schemas** | 3 | Project, ProjectProfile | Project data structures |
| **Promotion Schemas** | 1 | Promotion | Promotion data structures |
| **Policy Schemas** | 10 | Policy, PolicyDecision | Policy data structures |
| **Realtime Schemas** | 6 | Realtime, Connection | Realtime data structures |
| **Supervisor Schemas** | 24 | Supervisor, ServiceManifest | Supervisor data structures |
| **Codex Schemas** | 2 | CodexAgent, CodexGovernedExecution | Codex integration |
| **Lucio Schemas** | 1 | LucioAgent | Lucio agent |
| **Gemini Schemas** | 1 | GeminiExecutor | Gemini executor |
| **Pinhoforge Schemas** | 8 | PinhoforgeBridge | Pinhoforge integration |
| **Legacy RAG Schemas** | 8 | LegacyRAG | Legacy RAG |
| **Governed Write Schemas** | 1 | GovernedWrite | Governed write |
| **Cognitive Governance Schemas** | 1 | CognitiveGovernance | Cognitive governance |
| **Multi-Agent Observability Schemas** | 1 | MultiAgentObservability | Multi-agent observability |
| **Public Runtime API Schemas** | 1 | PublicRuntimeAPI | Public runtime API |
| **Web Search Schemas** | 1 | WebSearch | Web search |
| **Sandbox Schemas** | 3 | Sandbox, SandboxAutopilot | Sandbox |
| **Project Generation Schemas** | 1 | ProjectGeneration | Project generation |

**Dependencies:** None (data structures)  
**Consumers:** All services, API layer  
**Status:** Comprehensive schema coverage

—

### 5. Repositories Layer (`src/aipinho/repositories/`)

**Responsibility:** Data access and persistence

**Total Repository Modules:** 58+ modules

#### Repository Categories

| Category | Count | Examples | Responsibility |
|----------|-------|----------|-----------------|
| **Core Repositories** | 4 | approval_repository, artifact_repository, event_repository, task_run_repository | Core data access |
| **Context Repositories** | 5 | Context-specific repositories | Context data access |
| **Interaction Repositories** | 5 | Interaction-specific repositories | Interaction data access |
| **Legacy RAG Repositories** | 8 | Legacy RAG data access | Legacy RAG persistence |
| **Maintenance Repositories** | 8 | Maintenance-specific repositories | Maintenance data access |
| **Realtime Repositories** | 2 | Realtime data access | Realtime persistence |
| **Regression Repositories** | 6 | Regression-specific repositories | Regression data access |
| **Replay Repositories** | 6 | Replay-specific repositories | Replay data access |
| **Skills Repositories** | 6 | Skill-specific repositories | Skill data access |
| **Tools Repositories** | 2 | Tool-specific repositories | Tool data access |
| **Artifacts Repositories** | 1 | Artifact-specific repository | Artifact data access |
| **Events Repositories** | 2 | Event-specific repositories | Event data access |

**Dependencies:** Core, Data stores  
**Consumers:** Services layer  
**Status:** Data access layer

—

### 6. Registries Layer (`src/aipinho/registries/`)

**Responsibility:** Registry services for system components

**Total Registry Modules:** 9 modules

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `role_registry.py` | 3,190 | Role registration | HIGH |
| `route_registry.py` | 805 | Route registration | MEDIUM |
| `action_registry.py` | 130 | Action registration | MEDIUM |
| `capability_registry.py` | 138 | Capability registration | MEDIUM |
| `model_registry.py` | 0 | Model registration | LOW |
| `provider_registry.py` | 0 | Provider registration | LOW |
| `skill_registry.py` | 0 | Skill registration | LOW |
| `tool_registry.py` | 0 | Tool registration | LOW |

**Dependencies:** Core, Configuration  
**Consumers:** Policy kernel, Services  
**Status:** Registry infrastructure

—

### 7. Adapters Layer (`src/aipinho/adapters/`)

**Responsibility:** External system integration

**Total Adapter Modules:** 16+ modules

#### Adapter Categories

| Category | Count | Examples | Responsibility |
|----------|-------|----------|-----------------|
| **LLM Provider Adapters** | 5 | OpenAI, Gemini, Anthropic, etc. | LLM provider integration |
| **Filesystem Adapters** | 2 | Filesystem read/write | Filesystem operations |
| **Git Adapters** | 2 | Git operations | Git integration |
| **Shell Adapters** | 2 | Shell command execution | Shell operations |
| **Web Adapters** | 2 | Web requests | HTTP operations |
| **Android Adapters** | 2 | Android operations | Mobile integration |
| **Embeddings Adapters** | 0 | Embedding providers | Embedding generation |
| **Rerankers Adapters** | 0 | Reranking providers | Result reranking |
| **Vectorstores Adapters** | 0 | Vector databases | Vector storage |

**Dependencies:** External libraries  
**Consumers:** Services layer  
**Status:** Integration layer

—

### 8. Utils Layer (`src/aipinho/utils/`)

**Responsibility:** Utility functions and helpers

**Total Utility Modules:** 8 modules

| Module | Size (bytes) | Responsibility | Criticality |
|--------|--------------|-----------------|-------------|
| `diagnostics.py` | - | Diagnostic utilities | MEDIUM |
| `json_loader.py` | - | JSON loading | MEDIUM |
| `yaml_loader.py` | - | YAML loading | MEDIUM |
| `hashing.py` | - | Hashing functions | LOW |
| `redaction.py` | - | Data redaction | LOW |
| `safe_paths.py` | - | Path safety | LOW |
| `text.py` | - | Text utilities | LOW |

**Dependencies:** None (utilities)  
**Consumers:** All modules  
**Status:** Utility infrastructure

—

## Module Criticality Summary

### Critical Modules (System Failure Risk)
- `chat_service.py` - Core chat orchestration
- `task_runtime_service.py` - Core task runtime
- `execution_graph_service.py` - Execution graph management
- `agent_tool_gateway_service.py` - Tool gateway
- `agent_local_action_planner.py` - Action planning
- `policy_kernel_service.py` - Policy enforcement
- `workspace_role_contract_service.py` - Role contracts
- `capability_gate_service.py` - Capability gating
- `governed_tool_execution_service.py` - Tool execution
- `llama_cpp_provider.py` - Model provider

### High Priority Modules (Feature Impact)
- All router modules (139 total)
- Runtime services (56 modules)
- Chat services (29 modules)
- Agent services (31 modules)
- RAG services (83 modules)
- Memory services (44 modules)
- Artifact services (47 modules)
- Tool services (28 modules)
- Model services (47 modules)

### Medium Priority Modules (Operational Support)
- Governance services (25 modules)
- Validation services (30 modules)
- Patching services (70 modules)
- Maintenance services (42 modules)
- Debugger services (33 modules)
- Regression services (30 modules)
- Replay services (32 modules)
- Supervisor services (24 modules)

### Low Priority Modules (Infrastructure/Utilities)
- Utils (8 modules)
- Registries (9 modules)
- Adapters (16 modules)
- Stub services (many empty implementations)

---

## Module Dependencies Overview

### Dependency Layers (Bottom-Up)
1. **Utils Layer** - No dependencies
2. **Core Layer** - Depends on Utils
3. **Schemas Layer** - No dependencies (data structures)
4. **Registries Layer** - Depends on Core, Configuration
5. **Adapters Layer** - Depends on External libraries
6. **Repositories Layer** - Depends on Core, Data stores
7. **Services Layer** - Depends on Core, Schemas, Repositories, Registries, Adapters
8. **API Layer** - Depends on Services, Schemas

### Cross-Cutting Dependencies
- **Policy Kernel** → Used by all services
- **Runtime Services** → Used by most services
- **Validation Services** → Used by most services
- **Event Services** → Used by most services
- **Memory Services** → Used by Chat, Agents, RAG
- **Tool Services** → Used by Agents, Runtime
- **Model Services** → Used by Chat, Agents

---

## Module Health Indicators

### Well-Structured Modules
- Clear single responsibility
- Appropriate size (1K-30K bytes)
- Good naming conventions
- Proper dependency direction

### Modules Needing Attention
- Many empty/stub implementations (0 bytes)
- Some very large modules (>50K bytes) may need splitting
- Some modules with unclear responsibilities
- Potential duplication in similar service patterns

### Growth Patterns
- Sprint-based evolution evident
- Legacy code quarantined
- Extensive configuration-driven behavior
- Strong test coverage across all modules

---

## Next Steps

This module inventory provides the foundation for:
- Dependency graph mapping
- Duplication detection
- Critical path analysis
- Consolidation planning
- Architecture evolution
