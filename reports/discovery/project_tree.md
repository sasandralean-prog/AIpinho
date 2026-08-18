# AIpinho Project Tree Discovery

**Generated:** 2026-07-28  
**Purpose:** Complete architectural reverse engineering inventory  
**Scope:** Full project structure analysis

---

## Executive Summary

AIpinho is a local, modular, policy-driven AI runtime built with Python and FastAPI. The project demonstrates significant organic growth with multiple architectural layers, extensive configuration, and comprehensive testing infrastructure.

---

## Root Directory Structure

```
c:\Dev\AIpinho/
├── src/                    # Core source code (Python package)
├── config/                 # YAML configuration files (714 items)
├── tests/                  # Test suites (952 items)
├── apps/                   # Application entrypoints (1602 items)
├── data/                   # Runtime data and cache
├── artifacts/              # Artifact storage and index
├── reports/                # Generated reports and analysis (541 items)
├── docs/                   # Documentation (264 items)
├── scripts/                # Operational scripts (27 items)
├── sandboxes/              # Sandbox environments (55 items)
├── tools/                  # External tools (105 items)
├── field_trials/           # Field trial data (723 items)
├── build/                  # Build artifacts (14 items)
├── dist/                   # Distribution packages
├── backups/               # Backup archives (2 items)
├── quarantine/             # Quarantined legacy code (2 items)
├── pyproject.toml         # Python project configuration
├── docker-compose.yml     # Docker configuration
├── Makefile               # Build automation
├── README.md              # Project documentation
└── [Release notes]        # RC1, RC2, RC3 release notes
```

---

## Source Code Structure (`src/aipinho/`)

### Core Architecture Layers

```
src/aipinho/
├── core/                   # Foundation infrastructure (10 items)
│   ├── bootstrap.py
│   ├── dependency_container.py
│   ├── local_environment.py
│   ├── paths.py
│   ├── exceptions.py
│   ├── result.py
│   ├── clock.py
│   ├── lifecycle.py
│   └── ids.py
│
├── api/                    # FastAPI routers and endpoints (141 items)
│   ├── routers/            # 139 router modules
│   ├── dependencies/
│   ├── errors/
│   ├── middleware/
│   └── openapi/
│
├── services/               # Business logic layer (1182 items)
│   ├── agents/             # Multi-agent system (31 items)
│   ├── analysis/           # Project analysis (13 items)
│   ├── approvals/          # Approval workflows (8 items)
│   ├── artifacts/          # Artifact management (47 items)
│   ├── autopilot/          # Autonomous operations (1 item)
│   ├── chat/               # Chat orchestration (29 items)
│   ├── codex_agent/        # Codex integration (8 items)
│   ├── cognitive_policy_engine_service.py
│   ├── config_governance/  # Configuration governance (3 items)
│   ├── context/            # Context management (42 items)
│   ├── debugger/           # Debugging services (33 items)
│   ├── evals/              # Evaluation services (17 items)
│   ├── evaluation/         # Evaluation framework (15 items)
│   ├── events/             # Event system (18 items)
│   ├── external_adapter_registry.py
│   ├── external_collaboration_service.py
│   ├── external_collaboration_store.py
│   ├── external_connector_service.py
│   ├── external_gateway_service.py
│   ├── external_speaker_truth_auditor.py
│   ├── gemini_executor/    # Gemini model executor (6 items)
│   ├── governance/         # Governance layer (25 items)
│   ├── interaction/        # User interaction (18 items)
│   ├── interpreter/        # Interpretation services (7 items)
│   ├── legacy_rag/         # Legacy RAG system (18 items)
│   ├── lucio_agent/         # Lucio agent (7 items)
│   ├── maintenance/        # Maintenance plane (42 items)
│   ├── memory/             # Memory management (44 items)
│   ├── mobile/             # Mobile services (2 items)
│   ├── mobile_view_models/ # Mobile UI models (42 items)
│   ├── models/             # Model management (47 items)
│   ├── orchestration/      # Workflow orchestration (17 items)
│   ├── patch_intelligence_service.py
│   ├── patching/           # Patch operations (70 items)
│   ├── pinhoforge_bridge/  # Pinhoforge integration (13 items)
│   ├── policy/             # Policy services (3 items)
│   ├── policy_kernel/      # Policy kernel (15 items)
│   ├── projects/          # Project management (7 items)
│   ├── promotion/         # Promotion services (2 items)
│   ├── prompt_intelligence/ # Prompt analysis (15 items)
│   ├── prompts/            # Prompt services (9 items)
│   ├── providers/          # Provider management (9 items)
│   ├── public_runtime_api_service.py
│   ├── rag/                # RAG system (83 items)
│   ├── realtime/          # Realtime services (12 items)
│   ├── regression/         # Regression testing (30 items)
│   ├── replay/             # Replay system (32 items)
│   ├── reports/            # Report generation (12 items)
│   ├── roles/              # Role management (30 items)
│   ├── runtime/            # Task runtime (56 items)
│   ├── runtime_doctor/     # Runtime diagnostics (2 items)
│   ├── sandbox/            # Sandbox services (20 items)
│   ├── sandbox_file_writer_service.py
│   ├── security/           # Security services (7 items)
│   ├── self_healing/       # Self-healing (2 items)
│   ├── semantic_learning_service.py
│   ├── semantic_runtime/   # Semantic runtime (7 items)
│   ├── session/            # Session management (8 items)
│   ├── skills/             # Skills system (35 items)
│   ├── speaker/            # Speaker services (8 items)
│   ├── supervisor/         # Service supervision (24 items)
│   ├── telemetry/          # Telemetry (3 items)
│   ├── templates/          # Template services (5 items)
│   ├── tools/              # Tool execution (28 items)
│   ├── transfers/          # Transfer services (7 items)
│   ├── ux/                 # UX services (11 items)
│   ├── validation/         # Validation services (30 items)
│   ├── vision/             # Vision/OCR services (29 items)
│   ├── web_search_provider_service.py
│   ├── web_search_summary_service.py
│   ├── workspace_flows/    # Workspace flows (2 items)
│   └── workspaces/         # Workspace management (2 items)
│
├── schemas/                # Pydantic schemas (910 items)
│   ├── agents/             # Agent schemas (9 items)
│   ├── analysis/           # Analysis schemas (10 items)
│   ├── approvals/          # Approval schemas (6 items)
│   ├── artifacts/          # Artifact schemas (34 items)
│   ├── chat/               # Chat schemas (16 items)
│   ├── codex_agent.py
│   ├── codex_governed_execution.py
│   ├── cognitive_governance.py
│   ├── common/             # Common schemas (9 items)
│   ├── config_governance/  # Config governance schemas (3 items)
│   ├── context/            # Context schemas (41 items)
│   ├── debugger/           # Debugger schemas (29 items)
│   ├── evals/              # Evaluation schemas (21 items)
│   ├── evaluation/         # Evaluation schemas (11 items)
│   ├── events/             # Event schemas (24 items)
│   ├── external_collaboration.py
│   ├── external_connector.py
│   ├── external_gateway.py
│   ├── external_workspace.py
│   ├── gemini_executor.py
│   ├── governance/         # Governance schemas (6 items)
│   ├── governed_write.py
│   ├── intent/             # Intent schemas (9 items)
│   ├── interaction/        # Interaction schemas (41 items)
│   ├── legacy_rag/         # Legacy RAG schemas (8 items)
│   ├── lucio_agent.py
│   ├── maintenance/        # Maintenance schemas (47 items)
│   ├── memory/             # Memory schemas (38 items)
│   ├── mobile_view_models/ # Mobile view models (19 items)
│   ├── models/             # Model schemas (41 items)
│   ├── multi_agent_observability.py
│   ├── patch_intelligence.py
│   ├── patching/           # Patching schemas (51 items)
│   ├── pinhoforge_bridge/  # Pinhoforge schemas (8 items)
│   ├── policy/             # Policy schemas (10 items)
│   ├── project_generation.py
│   ├── projects/           # Project schemas (3 items)
│   ├── promotion.py
│   ├── prompts/            # Prompt schemas (8 items)
│   ├── public_runtime_api.py
│   ├── rag/                # RAG schemas (59 items)
│   ├── realtime/           # Realtime schemas (6 items)
│   ├── regression/        # Regression schemas (30 items)
│   ├── replay/             # Replay schemas (27 items)
│   ├── reports/            # Report schemas (12 items)
│   ├── roles/              # Role schemas (26 items)
│   ├── runtime/            # Runtime schemas (37 items)
│   ├── runtime_doctor.py
│   ├── sandbox.py
│   ├── sandbox_autopilot.py
│   ├── sandbox_writer.py
│   ├── security/           # Security schemas (3 items)
│   ├── self_healing.py
│   ├── semantic_learning.py
│   ├── semantic_runtime/    # Semantic runtime schemas (5 items)
│   ├── skills/             # Skill schemas (36 items)
│   ├── supervisor/         # Supervisor schemas (24 items)
│   ├── tasks/              # Task schemas (13 items)
│   ├── telemetry/          # Telemetry schemas (5 items)
│   ├── templates.py
│   ├── tools/              # Tool schemas (24 items)
│   ├── transfers/          # Transfer schemas (8 items)
│   ├── ux/                 # UX schemas (14 items)
│   ├── validation/         # Validation schemas (18 items)
│   ├── vision/             # Vision schemas (34 items)
│   ├── web_search.py
│   ├── workflows.py
│   └── workspace_flows/   # Workspace flow schemas (2 items)
│
├── repositories/           # Data access layer (58 items)
│   ├── approval_repository.py
│   ├── artifact_repository.py
│   ├── artifacts/          # Artifact repositories (1 item)
│   ├── context/            # Context repositories (5 items)
│   ├── event_repository.py
│   ├── events/             # Event repositories (2 items)
│   ├── interaction/        # Interaction repositories (5 items)
│   ├── legacy_rag/         # Legacy RAG repositories (8 items)
│   ├── maintenance/        # Maintenance repositories (8 items)
│   ├── memory_repository.py
│   ├── realtime/           # Realtime repositories (2 items)
│   ├── regression/         # Regression repositories (6 items)
│   ├── replay/             # Replay repositories (6 items)
│   ├── report_repository.py
│   ├── skills/             # Skill repositories (6 items)
│   ├── task_run_repository.py
│   └── tools/              # Tool repositories (2 items)
│
├── registries/             # Registry services (9 items)
│   ├── action_registry.py
│   ├── capability_registry.py
│   ├── model_registry.py
│   ├── provider_registry.py
│   ├── role_registry.py
│   ├── route_registry.py
│   ├── skill_registry.py
│   └── tool_registry.py
│
├── adapters/               # External adapters (16 items)
│   ├── android/            # Android adapters (2 items)
│   ├── embeddings/         # Embedding adapters
│   ├── filesystem/         # Filesystem adapters (2 items)
│   ├── git/                # Git adapters (2 items)
│   ├── llm_providers/      # LLM provider adapters (5 items)
│   ├── rerankers/          # Reranker adapters
│   ├── shell/              # Shell adapters (2 items)
│   ├── vectorstores/       # Vectorstore adapters
│   └── web/                # Web adapters (2 items)
│
├── utils/                  # Utility functions (8 items)
│   ├── redaction.py
│   ├── json_loader.py
│   ├── hashing.py
│   ├── diagnostics.py
│   ├── text.py
│   ├── safe_paths.py
│   ├── yaml_loader.py
│   └── __init__.py
│
├── apps/                   # Application modules (3 items)
├── main.py                 # FastAPI entrypoint
├── app_factory.py          # Application factory
└── __init__.py
```

---

## Configuration Structure (`config/`)

### Configuration Domains (714 items total)

```
config/
├── agents/                 # Agent configuration (12 items)
├── analysis/               # Analysis policies (7 items)
├── app/                    # Application settings (4 items)
├── artifacts/              # Artifact policies (30 items)
├── autopilot/              # Autopilot settings (2 items)
├── chat/                   # Chat configuration (6 items)
├── codex_agent/            # Codex agent config (3 items)
├── context/                # Context policies (19 items)
├── debugger/               # Debugger settings (14 items)
├── evals/                  # Evaluation config (13 items)
├── evaluation/             # Evaluation policies (8 items)
├── events/                 # Event configuration (10 items)
├── feature_flags/          # Feature flags (3 items)
├── gemini_executor/         # Gemini executor (1 item)
├── governance/             # Governance policies (10 items)
├── integrations/           # Integration config (1 item)
├── interaction/            # Interaction policies (16 items)
├── launcher/               # Launcher settings (14 items)
├── maintenance/            # Maintenance policies (16 items)
├── memory/                 # Memory policies (32 items)
├── mobile/                 # Mobile configuration (30 items)
├── models/                 # Model configuration (28 items)
├── patching/               # Patching policies (41 items)
├── policies/               # Policy definitions (31 items)
├── projects/               # Project config (3 items)
├── promotion/              # Promotion config (1 item)
├── prompts/                # Prompt templates (6 items)
├── providers/              # Provider settings (14 items)
├── rag/                    # RAG configuration (54 items)
├── realtime/               # Realtime settings (3 items)
├── regression/             # Regression config (11 items)
├── replay/                 # Replay settings (7 items)
├── reports/                # Report configuration (9 items)
├── roles/                  # Role definitions (18 items)
├── routes/                 # Route configuration (4 items)
├── runtime/                # Runtime policies (48 items)
├── sandbox/                # Sandbox settings (1 item)
├── security/               # Security policies (7 items)
├── semantic_runtime/        # Semantic runtime (4 items)
├── skills/                 # Skill configuration (81 items)
├── supervisor/             # Supervisor settings (16 items)
├── templates/              # Template config (10 items)
├── tools/                  # Tool configuration (12 items)
├── transfers/              # Transfer settings (3 items)
├── ux/                     # UX policies (12 items)
├── validation/             # Validation policies (14 items)
├── vision/                 # Vision/OCR config (20 items)
└── workspaces/             # Workspace policies (5 items)
```

---

## Applications Structure (`apps/`)

```
apps/
├── launcher/               # Desktop launcher (141 items)
│   ├── AIpinhoLauncher.spec
│   ├── launcher_bootstrap.py
│   ├── launcher_main.py
│   ├── launcher_config_loader.py
│   ├── launcher_process_manager.py
│   ├── launcher_token_view.py
│   ├── launcher_tray.py
│   ├── launcher_watchdog.py
│   ├── ui/                 # Launcher UI (130 items)
│   └── assets/
│
├── mobile/                 # Mobile application (1460 items)
│   └── android/            # Android project
│       ├── app/
│       ├── build/
│       └── gradle files
│
├── admin/                  # Admin interface
├── api/                    # API interface
├── cli/                    # CLI interface
└── worker/                 # Worker interface
```

---

## Test Structure (`tests/`)

```
tests/
├── unit/                   # Unit tests (589 items)
│   ├── test_*.py files (comprehensive unit test coverage)
│   ├── context_test_helpers.py
│   ├── curated_memory_test_helpers.py
│   ├── rag_memory_test_helpers.py
│   └── retrieval_test_helpers.py
│
├── integration/            # Integration tests (149 items)
│   ├── test_*_api.py files (API integration tests)
│   ├── test_*_flow.py files (workflow integration tests)
│   └── sprint-specific integration tests
│
├── contract/               # Contract tests (46 items)
│   ├── test_*_contracts.py files (schema validation)
│   └── test_policy_config_validity.py
│
├── e2e/                    # End-to-end tests (43 items)
│   ├── test_*_flow.py files (complete workflow tests)
│   └── operational flow tests
│
├── governance/             # Governance tests (20 items)
├── multi_agent/            # Multi-agent tests (25 items)
├── skills/                 # Skill tests (2 items)
├── skill_packs/            # Skill pack tests (1 item)
├── sandbox/                # Sandbox tests (2 items)
├── workflows/              # Workflow tests (2 items)
├── workspaces/             # Workspace tests (1 item)
├── fixtures/               # Test fixtures (50 items)
│   ├── templates/
│   ├── workflows/
│   └── project_profiles/
├── artifact_library/       # Artifact library tests (1 item)
├── autopilot/              # Autopilot tests (1 item)
├── certification/          # Certification tests (1 item)
├── evals/                  # Evaluation tests (3 items)
├── learning/               # Learning tests (2 items)
├── project_factory/        # Project factory tests (1 item)
├── promotion/              # Promotion tests (1 item)
├── templates/              # Template tests (1 item)
├── artifact_fixtures.py
├── patch_fixtures.py
├── validation_fixtures.py
├── manual_inference_test_helpers.py
├── maintenance_helpers.py
├── replay_regression_helpers.py
└── conftest.py             # Pytest configuration
```

---

## Runtime Data Structure (`data/`)

```
data/
├── artifacts/              # Runtime artifacts
├── cache/                  # Cache storage
├── external_collaboration/ # External collaboration data
├── logs/                   # Application logs
├── memory/                 # Memory storage
├── runtime/                # Runtime state
├── test_artifacts/         # Test artifacts
├── tmp/                    # Temporary files
├── tmp_artifact_runtime_tests/
├── tmp_debug_runtime_vertical/
├── tmp_debug_s1s4/
├── tmp_debug_s1s4_block/
├── tmp_debug_s1s4_block2/
├── tmp_debug_safe/
├── tmp_runtime_debug/
├── tmp_runtime_doctor_tests/
├── tmp_runtime_operator_tests/
├── tmp_runtime_timeline_tests/
├── tmp_runtime_vertical_slice_tests/
├── tmp_vertical_slice/
├── uploads/                # User uploads
└── vectorstores/           # Vector database storage
```

---

## Reports Structure (`reports/`)

```
reports/
├── discovery/              # Discovery reports (this analysis)
├── artifacts/              # Artifact reports
├── audits/                 # Audit reports
├── autopilot/              # Autopilot reports
├── baselines/              # Baseline reports
├── bridge/                 # Bridge reports
├── diagnostics/            # Diagnostic reports
├── dogfood/                # Dogfood reports
├── engineering_evolution/  # Engineering evolution (16 items)
├── evals/                  # Evaluation reports
├── field_trials/           # Field trial reports
├── fire_tests/             # Fire test reports (64 items)
├── governance_block_*       # Governance block reports (multiple)
├── hardening/              # Hardening reports
├── health/                 # Health reports
├── hotfixes/               # Hotfix reports
├── kernel/                 # Kernel reports
├── lucio_context/          # Lucio context reports
├── memory/                 # Memory reports
├── mobile/                 # Mobile reports
├── mobile_connection/      # Mobile connection reports
├── multi_agent/            # Multi-agent reports (25 items)
├── multimodal/             # Multimodal reports
├── promotion/              # Promotion reports
├── rc4/                    # RC4 reports
├── regression/             # Regression reports
├── release/                # Release reports
├── restore/                # Restore reports
├── review_packs/           # Review pack reports
├── runtime_cleanup/         # Runtime cleanup (14 items)
├── runtime_r*              # Runtime reports (multiple)
├── runtime_supervisor/     # Runtime supervisor reports
├── runtime_vertical_slice/ # Vertical slice reports
├── sandbox/                # Sandbox reports
├── semantic_evolution_history.md
├── skills/                 # Skill reports
├── sprint_*                # Sprint reports (multiple)
├── sprints/                # Sprint collection
├── storage/                # Storage reports
├── templates/              # Template reports
├── validations/            # Validation reports
├── workspaces/             # Workspace reports
├── openapi.yaml
├── connector_registry.json
├── dashboard_snapshot.json
├── gateway_contract.json
├── public_contracts.json
└── runtime_health.json
```

---

## Documentation Structure (`docs/`)

```
docs/
├── agents/                 # Agent documentation (8 items)
├── api/                    # API documentation (3 items)
├── architecture/           # Architecture docs (37 items)
├── artifacts/              # Artifact documentation (9 items)
├── autopilot/              # Autopilot docs (2 items)
├── cognitive_governance/   # Cognitive governance (4 items)
├── debugger/               # Debugger docs (8 items)
├── decisions/              # Decision records (4 items)
├── desktop/                # Desktop docs (8 items)
├── dogfood/                # Dogfood docs (5 items)
├── external/               # External integration docs (3 items)
├── governed_runtime/       # Governed runtime docs (5 items)
├── integrations/           # Integration docs (1 item)
├── launcher/               # Launcher docs (1 item)
├── memory/                 # Memory docs (2 items)
├── mobile/                 # Mobile docs (15 items)
├── observability/          # Observability docs (3 items)
├── operations/             # Operations docs (20 items)
├── patch_intelligence/     # Patch intelligence docs (3 items)
├── planning/               # Planning docs (2 items)
├── policies/               # Policy docs (4 items)
├── projects/               # Project docs (7 items)
├── rag/                    # RAG docs (3 items)
├── rag_curated/            # Curated RAG docs (30 items)
├── release/                # Release docs (2 items)
├── roles/                  # Role docs (3 items)
├── sandbox/                # Sandbox docs (12 items)
├── security/               # Security docs
├── semantic_learning/      # Semantic learning docs (4 items)
├── semantic_runtime/       # Semantic runtime docs (5 items)
├── skills/                 # Skills docs (22 items)
├── templates/              # Template docs (3 items)
└── testing/                # Testing docs (14 items)
```

---

## Scripts Structure (`scripts/`)

```
scripts/
├── backup_aipinho.ps1
├── doctor_aipinho.ps1
├── restore_aipinho.ps1
├── start_aipinho.ps1
├── stop_aipinho.ps1
├── status_aipinho.ps1
├── open_launcher.ps1
├── prepare_mobile_pairing.ps1
├── package_aipinho_rc3.ps1
├── package_launcher_desktop.ps1
├── bootstrap/              # Bootstrap scripts
├── dev/                    # Development scripts (11 items)
├── maintenance/            # Maintenance scripts (4 items)
├── migrations/             # Migration scripts
└── validation/             # Validation scripts (2 items)
```

---

## Key Observations

### Scale Indicators
- **Total source files**: ~2,340 Python files in `src/aipinho/`
- **Configuration files**: 714 YAML configuration files
- **Test files**: 952 test files across unit/integration/contract/e2e
- **API routers**: 139 router modules
- **Service modules**: 1,182 service modules
- **Schema modules**: 910 schema modules

### Architectural Patterns
1. **Layered Architecture**: Core → Services → API → Routers
2. **Config-First**: Extensive YAML configuration driving behavior
3. **Policy-Driven**: Governance and policy kernel at core
4. **Multi-Modal**: Support for agents, skills, tools, RAG, vision
5. **Test-Driven**: Comprehensive test coverage across all layers

### Growth Indicators
- Multiple sprint-based evolution (Sprint 00-26+)
- Field trials and RC releases
- Extensive reporting and audit trails
- Legacy code quarantine
- Backup and restore infrastructure

---

## Next Steps

This project tree provides the foundation for:
- Module inventory analysis
- Dependency mapping
- Duplication detection
- Critical module identification
- Architecture summary generation
