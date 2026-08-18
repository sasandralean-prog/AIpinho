# AIpinho Genome Summary

Generated: 2026-07-30T20:01:00Z

## Architecture

**Architecture Type**: Config-first, contract-first modular architecture

**Number of Layers**: 5
- entrypoint
- core
- utils
- services
- api
- repositories
- registries
- adapters
- schemas

**Number of Pipelines**: 8
- chat_pipeline
- task_pipeline
- tool_pipeline
- model_pipeline
- validation_pipeline
- approval_pipeline
- artifact_pipeline
- memory_pipeline
- rag_pipeline

## Main Modules

**Core Modules**:
- core.bootstrap
- core.dependency_container
- core.local_environment
- core.paths
- core.exceptions
- core.result

**Service Modules**:
- services.policy_kernel.policy_kernel_service
- services.runtime.task_runtime_service
- services.chat.chat_service
- services.agents.agent_tool_gateway_service
- services.models.llama_cpp_provider
- services.tools.governed_tool_execution_service
- services.validation.validation_gate_service

**API Modules**:
- api.routers.chat_router
- api.routers.task_runtime_router
- api.routers.tool_router
- api.routers.model_router
- api.routers.artifact_router
- api.routers.agent_router
- api.routers.policy_router

## Observable Bottlenecks

**Hub Dependencies**:
- services.policy_kernel.policy_kernel_service (dependents: services.runtime, services.chat, services.agents, services.tools)
- services.runtime.task_runtime_service (dependents: services.chat, services.agents, services.tools)
- core (dependents: all service layers)

**Critical Path**: entrypoint → core → services.policy_kernel → services.runtime → services.chat → api

## Areas with Higher Coupling

**High Coupling Areas**:
- services.policy_kernel (depends on: core, registries, schemas.policy)
- services.chat (depends on: core, schemas.chat, services.runtime, services.policy_kernel, services.memory, services.models, services.tools)
- services.agents.agent_tool_gateway_service (depends on: core, schemas.agents, services.runtime, services.policy_kernel, services.tools, services.workspaces)

## Highly Cohesive Areas

**High Cohesion Areas**:
- services.policy_kernel (3 services focused on governance)
- services.runtime (3 services focused on task execution)
- services.chat (2 services focused on chat operations)
- services.tools (28 services focused on tool execution)

## Consolidation Candidates

**Potential Consolidation**:
- services.tools.tool_* services (28 services could be consolidated)
- api.routers.* routers (139 routers could be consolidated)
- schemas.* (910 schemas could be consolidated)

## Critical Areas

**Critical Services**:
- services.policy_kernel.policy_kernel_service
- services.runtime.task_runtime_service
- services.chat.chat_service
- services.tools.governed_tool_execution_service
- services.validation.validation_gate_service

**Critical Endpoints**:
- POST /chat
- POST /tasks
- POST /tools/execute
- POST /models/invoke
- POST /artifacts
- POST /agents/delegate
- POST /policy/check

## Experimental Areas

**Experimental Areas**:
- services.vision.* (vision processing services)
- services.agents.agent_* (agent-related services)
- services.patch.* (patch-related services)
- services.evaluation.* (evaluation services)

## Legacy Areas

**Legacy Areas**:
- core.clock (empty stub)
- core.lifecycle (empty stub)
- core.ids (empty stub)
- services.runtime.runtime_doctor_service (diagnostics service)
- services.runtime.runtime_state_hygiene_service (state management service)

## Unknown Areas

**Unknown Areas**:
- roles capabilities (all marked as UNKNOWN)
- role dependencies (all marked as UNKNOWN)
- runtime state values (all marked as UNKNOWN)
- execution graph steps (some marked as UNKNOWN)
