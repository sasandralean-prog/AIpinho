# AIpinho Runtime Inventory

**Generated:** 2026-07-28  
**Purpose:** Complete runtime data and cache classification  
**Scope:** All runtime data, cache, temporary files, and artifacts

---

## Executive Summary

AIpinho has extensive runtime data infrastructure with clear separation between code, runtime state, cache, temporary files, and artifacts. The system demonstrates mature data management with backup, quarantine, and audit capabilities.

---

## Runtime Data Classification

### 1. Code vs Runtime Data Separation

| Category | Location | File Count | Size Estimate | Type |
|----------|----------|------------|---------------|------|
| **Source Code** | `src/aipinho/` | 2,340+ | ~50MB+ | Immutable (version controlled) |
| **Configuration** | `config/` | 714 | ~5MB+ | Immutable (version controlled) |
| **Tests** | `tests/` | 952 | ~20MB+ | Immutable (version controlled) |
| **Documentation** | `docs/` | 264 | ~2MB+ | Immutable (version controlled) |
| **Scripts** | `scripts/` | 27 | ~500KB | Immutable (version controlled) |
| **Runtime Data** | `data/` | 20+ directories | Variable | Mutable (runtime state) |
| **Artifacts** | `artifacts/` | 1+ index | ~865KB | Mutable (generated content) |
| **Reports** | `reports/` | 541+ | Variable | Mutable (generated reports) |
| **Sandboxes** | `sandboxes/` | 55+ | Variable | Mutable (sandbox state) |
| **Field Trials** | `field_trials/` | 723+ | Variable | Mutable (trial data) |
| **Build Artifacts** | `build/`, `dist/` | 15+ | ~15MB+ | Mutable (build output) |
| **Backups** | `backups/` | 2 | ~3.7MB+ | Mutable (backup archives) |
| **Quarantine** | `quarantine/` | 2 | Variable | Mutable (quarantined code) |
| **Tools** | `tools/` | 105+ | Variable | Immutable (external tools) |
| **Applications** | `apps/` | 1,602+ | Variable | Mixed (code + build) |

---

## 2. Runtime Data Structure (`data/`)

### 2.1 Runtime Data Directories

```
data/
├── artifacts/              # Runtime-generated artifacts
├── cache/                  # Cache storage (empty)
├── external_collaboration/ # External collaboration data (empty)
├── logs/                   # Application logs
│   └── runtime/
│       ├── aipinho_monitor_9099.out.log
│       ├── aipinho_monitor_9099.err.log
│       ├── aipinho_bootstrap_9080.out.log
│       ├── aipinho_bootstrap_9080.err.log
│       ├── aipinho_api_9088.out.log
│       └── aipinho_api_9088.err.log
├── memory/                 # Memory storage (empty)
├── runtime/                # Runtime state
│   ├── aipinho_9088_stdout.log
│   └── aipinho_9088_stderr.log
├── test_artifacts/         # Test-generated artifacts
├── tmp/                    # General temporary files (empty)
├── tmp_artifact_runtime_tests/  # Artifact runtime test temp
├── tmp_debug_runtime_vertical/  # Debug runtime temp
├── tmp_debug_s1s4/         # Debug temp (sprint 1-4)
├── tmp_debug_s1s4_block/   # Debug temp (blocked)
├── tmp_debug_s1s4_block2/  # Debug temp (blocked 2)
├── tmp_debug_safe/         # Debug temp (safe mode)
├── tmp_runtime_debug/      # Runtime debug temp
├── tmp_runtime_doctor_tests/   # Runtime doctor test temp
├── tmp_runtime_operator_tests/  # Runtime operator test temp
├── tmp_runtime_timeline_tests/ # Runtime timeline test temp
├── tmp_runtime_vertical_slice_tests/ # Vertical slice test temp
├── tmp_vertical_slice/    # Vertical slice temp
├── uploads/                # User uploads (empty)
└── vectorstores/           # Vector database storage (empty)
```

### 2.2 Runtime Data Classification

| Directory | Type | Purpose | Mutability | Persistence |
|-----------|------|---------|------------|-------------|
| `artifacts/` | Runtime Data | Generated artifacts | Mutable | Persistent |
| `cache/` | Cache | Application cache | Mutable | Temporary |
| `external_collaboration/` | Runtime Data | External collaboration | Mutable | Persistent |
| `logs/` | Logs | Application logs | Mutable | Persistent (rotated) |
| `memory/` | Runtime Data | Memory storage | Mutable | Persistent |
| `runtime/` | Runtime Data | Runtime state | Mutable | Temporary |
| `test_artifacts/` | Temporary | Test artifacts | Mutable | Temporary |
| `tmp/` | Temporary | General temp | Mutable | Temporary |
| `tmp_*/` | Temporary | Specific temp directories | Mutable | Temporary |
| `uploads/` | Temporary | User uploads | Mutable | Temporary |
| `vectorstores/` | Runtime Data | Vector storage | Mutable | Persistent |

**Runtime Data Status:**
- **Active logs:** 8 log files (monitor, bootstrap, API)
- **Empty directories:** cache, external_collaboration, memory, tmp, uploads, vectorstores
- **Temporary directories:** 13 specialized temp directories
- **Size:** Unknown (requires disk usage analysis)

---

## 3. Artifacts Structure (`artifacts/`)

### 3.1 Artifacts Directory

```
artifacts/
├── ARTIFACT_INDEX.json     # Artifact index (885,602 bytes)
└── projects/               # Project-specific artifacts (empty)
```

### 3.2 Artifact Classification

| Component | Type | Size | Purpose | Mutability |
|-----------|------|------|---------|------------|
| `ARTIFACT_INDEX.json` | Index | 885KB | Artifact registry | Mutable |
| `projects/` | Directory | Empty | Project artifacts | Mutable |

**Artifact Status:**
- **Index size:** 885KB (substantial artifact registry)
- **Project artifacts:** Empty (not yet populated)
- **Type:** Generated content index

---

## 4. Reports Structure (`reports/`)

### 4.1 Reports Classification

```
reports/
├── discovery/              # Discovery reports (this analysis)
├── artifacts/              # Artifact reports (empty)
├── audits/                 # Audit reports (empty)
├── autopilot/              # Autopilot reports (empty)
├── baselines/              # Baseline reports (2 items)
├── bridge/                 # Bridge reports (empty)
├── diagnostics/            # Diagnostic reports (2 items)
├── dogfood/                # Dogfood reports (empty)
├── engineering_evolution/  # Engineering evolution (16 items)
├── evals/                  # Evaluation reports (empty)
├── field_trials/           # Field trial reports (empty)
├── fire_tests/             # Fire test reports (64 items)
├── governance_block_*      # Governance block reports (multiple)
├── hardening/              # Hardening reports (empty)
├── health/                 # Health reports (4 items)
├── hotfixes/               # Hotfix reports (4 items)
├── kernel/                 # Kernel reports (10 items)
├── lucio_context/          # Lucio context reports (2 items)
├── memory/                 # Memory reports (empty)
├── mobile/                 # Mobile reports (empty)
├── mobile_connection/      # Mobile connection reports (empty)
├── multi_agent/            # Multi-agent reports (25 items)
├── multimodal/             # Multimodal reports (empty)
├── promotion/              # Promotion reports (empty)
├── rc4/                    # RC4 reports (empty)
├── regression/             # Regression reports (empty)
├── release/                # Release reports (empty)
├── restore/                # Restore reports (empty)
├── review_packs/           # Review pack reports (empty)
├── runtime_cleanup/         # Runtime cleanup (14 items)
├── runtime_r*              # Runtime reports (multiple)
├── runtime_supervisor/     # Runtime supervisor reports (8 items)
├── runtime_vertical_slice/ # Vertical slice reports (5 items)
├── sandbox/                # Sandbox reports (empty)
├── semantic_evolution_history.md
├── skills/                 # Skills reports (empty)
├── sprint_*                # Sprint reports (multiple)
├── sprints/                # Sprint collection (empty)
├── storage/                # Storage reports (12 items)
├── templates/              # Template reports (empty)
├── validations/            # Validation reports (empty)
├── workspaces/             # Workspace reports (empty)
├── openapi.yaml            # OpenAPI spec (1,016 bytes)
├── connector_registry.json (324 bytes)
├── dashboard_snapshot.json (328 bytes)
├── gateway_contract.json (504 bytes)
├── public_contracts.json (919 bytes)
└── runtime_health.json (260 bytes)
```

### 4.2 Reports Classification

| Category | Count | Type | Purpose | Mutability |
|----------|-------|------|---------|------------|
| **Discovery Reports** | 1 | Analysis | Architectural discovery | Mutable |
| **Fire Test Reports** | 64 | Test results | Fire testing | Mutable |
| **Multi-Agent Reports** | 25 | Analysis | Multi-agent system | Mutable |
| **Governance Block Reports** | 50+ | Analysis | Governance analysis | Mutable |
| **Sprint Reports** | 30+ | Analysis | Sprint analysis | Mutable |
| **Runtime Reports** | 20+ | Analysis | Runtime analysis | Mutable |
| **Engineering Evolution** | 16 | Analysis | Engineering history | Mutable |
| **Runtime Cleanup** | 14 | Analysis | Cleanup analysis | Mutable |
| **Runtime Supervisor** | 8 | Analysis | Supervisor analysis | Mutable |
| **Storage Reports** | 12 | Analysis | Storage analysis | Mutable |
| **Hotfix Reports** | 4 | Analysis | Hotfix analysis | Mutable |
| **Health Reports** | 4 | Analysis | Health analysis | Mutable |
| **Kernel Reports** | 10 | Analysis | Kernel analysis | Mutable |
| **Lucio Context** | 2 | Analysis | Lucio analysis | Mutable |
| **Baseline Reports** | 2 | Analysis | Baseline data | Mutable |
| **Diagnostic Reports** | 2 | Analysis | Diagnostic data | Mutable |
| **Vertical Slice** | 5 | Analysis | Vertical slice | Mutable |
| **Configuration Files** | 6 | Config | System configuration | Mutable |
| **Empty Directories** | 15+ | - | Reserved for future use | Mutable |

**Reports Status:**
- **Total reports:** 250+ report files
- **Active report categories:** 15+ categories with content
- **Empty categories:** 15+ categories reserved for future use
- **Size:** Variable (requires disk usage analysis)

---

## 5. Sandboxes Structure (`sandboxes/`)

### 5.1 Sandboxes Directory

```
sandboxes/
├── artifacts/              # Sandbox artifacts (empty)
├── capability_probe/       # Capability probe (12 items)
├── default/                # Default sandbox (2 items)
├── dopamine_test/          # Dopamine test (2 items)
├── logs/                   # Sandbox logs (empty)
├── projects/               # Sandbox projects (empty)
├── reports/                # Sandbox reports (empty)
├── tasks/                  # Sandbox tasks (35 items)
├── tmp/                    # Sandbox temp (empty)
├── trash/                  # Sandbox trash (empty)
├── vitoria_02/             # Vitoria sandbox (4 items)
└── [other sandboxes]
```

### 5.2 Sandbox Classification

| Directory | Type | Item Count | Purpose | Mutability |
|-----------|------|------------|---------|------------|
| `artifacts/` | Sandbox Data | 0 | Sandbox artifacts | Mutable |
| `capability_probe/` | Sandbox Data | 12 | Capability testing | Mutable |
| `default/` | Sandbox Data | 2 | Default sandbox | Mutable |
| `dopamine_test/` | Sandbox Data | 2 | Dopamine testing | Mutable |
| `logs/` | Logs | 0 | Sandbox logs | Mutable |
| `projects/` | Sandbox Data | 0 | Sandbox projects | Mutable |
| `reports/` | Reports | 0 | Sandbox reports | Mutable |
| `tasks/` | Sandbox Data | 35 | Sandbox tasks | Mutable |
| `tmp/` | Temporary | 0 | Sandbox temp | Mutable |
| `trash/` | Temporary | 0 | Sandbox trash | Mutable |
| `vitoria_02/` | Sandbox Data | 4 | Vitoria sandbox | Mutable |

**Sandbox Status:**
- **Active sandboxes:** 4 sandboxes with content
- **Empty directories:** 6 directories reserved for future use
- **Task count:** 35 sandbox tasks
- **Type:** Isolated runtime environments

---

## 6. Field Trials Structure (`field_trials/`)

### 6.1 Field Trials Directory

```
field_trials/
├── dogfood_sprint20/       # Dogfood sprint 20 (11 items)
├── rc1/                    # Release candidate 1 (702 items)
└── rc2/                    # Release candidate 2 (10 items)
```

### 6.2 Field Trials Classification

| Directory | Type | Item Count | Purpose | Mutability |
|-----------|------|------------|---------|------------|
| `dogfood_sprint20/` | Field Trial | 11 | Dogfood testing | Mutable |
| `rc1/` | Field Trial | 702 | RC1 testing | Mutable |
| `rc2/` | Field Trial | 10 | RC2 testing | Mutable |

**Field Trials Status:**
- **Total field trials:** 3 trial sets
- **RC1 data:** 702 items (substantial trial data)
- **RC2 data:** 10 items (smaller trial data)
- **Dogfood data:** 11 items (internal testing)
- **Type:** Historical testing data

---

## 7. Build and Distribution Structure

### 7.1 Build Artifacts (`build/`)

```
build/
└── AIpinhoLauncher/        # Launcher build (14 items)
    ├── [PyInstaller build files]
    └── warn-AIpinhoLauncher.txt
```

### 7.2 Distribution (`dist/`)

```
dist/
├── AIpinhoLauncher.exe     # Launcher executable (14,891,407 bytes ~14.2MB)
├── aipinho_local_rc3/      # RC3 distribution (empty)
└── aipinho_multi_agent_rc1/ # Multi-agent RC1 (empty)
```

### 7.3 Build Classification

| Component | Type | Size | Purpose | Mutability |
|-----------|------|------|---------|------------|
| `AIpinhoLauncher.exe` | Executable | 14.2MB | Desktop launcher | Mutable (rebuildable) |
| `build/AIpinhoLauncher/` | Build Artifacts | Variable | Build intermediate | Mutable (rebuildable) |
| `dist/aipinho_local_rc3/` | Distribution | Empty | RC3 distribution | Mutable |
| `dist/aipinho_multi_agent_rc1/` | Distribution | Empty | Multi-agent RC1 | Mutable |

**Build Status:**
- **Launcher executable:** 14.2MB (substantial desktop application)
- **Build artifacts:** 14 items (PyInstaller build)
- **Distribution directories:** 2 empty (reserved for future releases)
- **Type:** Build output (reproducible from source)

---

## 8. Backup Structure (`backups/`)

### 8.1 Backup Directory

```
backups/
├── aipinho_backup_20260613_205816.json (759 bytes)
└── aipinho_backup_20260613_205816.zip (3,775,190 bytes ~3.6MB)
```

### 8.2 Backup Classification

| Component | Type | Size | Purpose | Mutability |
|-----------|------|------|---------|------------|
| `aipinho_backup_*.json` | Backup Manifest | 759 bytes | Backup metadata | Mutable |
| `aipinho_backup_*.zip` | Backup Archive | 3.6MB | Full backup | Mutable |

**Backup Status:**
- **Backup date:** 2026-06-13 (historical backup)
- **Backup size:** 3.6MB (compressed)
- **Backup type:** Full system backup
- **Frequency:** Unknown (single backup found)

---

## 9. Quarantine Structure (`quarantine/`)

### 9.1 Quarantine Directory

```
quarantine/
└── legacy/                 # Legacy code quarantine
    └── governance/         # Legacy governance (2 items)
```

### 9.2 Quarantine Classification

| Directory | Type | Item Count | Purpose | Mutability |
|-----------|------|------------|---------|------------|
| `legacy/governance/` | Quarantine | 2 | Legacy governance code | Mutable (archived) |

**Quarantine Status:**
- **Quarantined items:** 2 legacy governance files
- **Purpose:** Legacy code preservation
- **Type:** Archived code (not in active use)

---

## 10. Tools Structure (`tools/`)

### 10.1 Tools Directory

```
tools/
├── external/               # External tools (empty)
├── llama_cpp/              # LLaMA CPP tools (105 items)
│   ├── llama-b9558-bin-win-vulkan-x64.zip
│   ├── llama-b9558-bin-win-cpu-x64.zip
│   └── [other LLaMA CPP files]
├── local/                  # Local tools (empty)
```

### 10.2 Tools Classification

| Directory | Type | Item Count | Size | Purpose | Mutability |
|-----------|------|------------|------|---------|------------|
| `external/` | External Tools | 0 | Empty | External tool integration | Mutable |
| `llama_cpp/` | External Tools | 105 | Variable | LLaMA CPP runtime | Immutable |
| `local/` | Local Tools | 0 | Empty | Local tool scripts | Mutable |

**Tools Status:**
- **LLaMA CPP tools:** 105 items (substantial toolset)
- **External tools:** Empty (reserved for future)
- **Local tools:** Empty (reserved for future)
- **Type:** External dependencies (version controlled)

---

## 11. Cache Analysis

### 11.1 Cache Directories

| Directory | Status | Purpose | Estimated Size |
|-----------|--------|---------|----------------|
| `data/cache/` | Empty | Application cache | 0 bytes |
| `data/tmp/` | Empty | General temp | 0 bytes |
| `data/uploads/` | Empty | User uploads | 0 bytes |
| `data/vectorstores/` | Empty | Vector storage | 0 bytes |
| `data/memory/` | Empty | Memory storage | 0 bytes |
| `data/external_collaboration/` | Empty | External data | 0 bytes |
| `__pycache__/` | Active | Python bytecode | Variable (50+ files) |
| `build/*/localpycs/` | Active | Build bytecode | Variable |

### 11.2 Cache Classification

| Cache Type | Location | File Count | Type | Purpose |
|------------|----------|------------|------|---------|
| **Python Bytecode** | `__pycache__/` | 50+ | Cache | Python compilation cache |
| **Build Bytecode** | `build/*/localpycs/` | 7+ | Cache | PyInstaller bytecode |
| **Application Cache** | `data/cache/` | 0 | Cache | Application runtime cache |
| **Vector Storage** | `data/vectorstores/` | 0 | Cache | Vector database cache |
| **Memory Cache** | `data/memory/` | 0 | Cache | Memory system cache |

**Cache Status:**
- **Active cache:** Python bytecode (50+ files)
- **Empty cache directories:** 6 directories (not yet populated)
- **Cache type:** Compilation cache (Python)
- **Size:** Unknown (requires disk usage analysis)

---

## 12. Temporary Files Analysis

### 12.1 Temporary Directories

| Directory | Status | Purpose | Cleanup Policy |
|-----------|--------|---------|----------------|
| `data/tmp/` | Empty | General temp | Manual |
| `data/tmp_*/` | Active | Specialized temp | Multiple (13 dirs) |
| `sandboxes/tmp/` | Empty | Sandbox temp | Manual |
| `sandboxes/trash/` | Empty | Sandbox trash | Manual |
| `data/test_artifacts/` | Active | Test artifacts | Manual |
| `data/uploads/` | Empty | User uploads | Manual |

### 12.2 Temporary File Types

| Type | Location | Count | Purpose | Lifecycle |
|------|----------|---------|---------|------------|
| **Debug Temp** | `data/tmp_debug_*/` | 6 | Debugging | Session-based |
| **Runtime Test Temp** | `data/tmp_runtime_*/` | 4 | Runtime testing | Test-based |
| **Artifact Test Temp** | `data/tmp_artifact_*/` | 1 | Artifact testing | Test-based |
| **Vertical Slice Temp** | `data/tmp_vertical_slice/` | 2 | Vertical slice testing | Test-based |
| **General Temp** | `data/tmp/` | 0 | General purpose | Manual |
| **Test Artifacts** | `data/test_artifacts/` | 1 | Test output | Test-based |
| **Sandbox Temp** | `sandboxes/tmp/` | 0 | Sandbox temp | Session-based |
| **Sandbox Trash** | `sandboxes/trash/` | 0 | Sandbox trash | Session-based |

**Temporary Files Status:**
- **Active temp directories:** 13 specialized temp directories
- **Empty temp directories:** 3 directories (not yet populated)
- **Temp type:** Debug and test temporary files
- **Cleanup:** Manual (no automatic cleanup observed)

---

## 13. Generated Files Analysis

### 13.1 Generated File Categories

| Category | Location | Count | Type | Purpose |
|----------|----------|-------|------|---------|
| **Log Files** | `data/logs/`, `data/runtime/` | 8 | Logs | Runtime logging |
| **Report Files** | `reports/` | 250+ | Reports | Analysis reports |
| **Artifact Files** | `data/artifacts/`, `artifacts/` | Variable | Artifacts | Generated artifacts |
| **Build Artifacts** | `build/`, `dist/` | 15+ | Build | Build output |
| **Test Artifacts** | `data/test_artifacts/` | Variable | Test | Test output |
| **Sandbox Data** | `sandboxes/` | 55+ | Sandbox | Sandbox state |
| **Field Trial Data** | `field_trials/` | 723+ | Trial | Field trial data |
| **Backup Files** | `backups/` | 2 | Backup | System backups |

### 13.2 Generated File Lifecycle

| File Type | Generation Trigger | Retention Policy | Cleanup Policy |
|-----------|-------------------|-----------------|----------------|
| **Log Files** | Runtime operation | Persistent (rotated) | Manual rotation |
| **Report Files** | Analysis runs | Persistent | Manual cleanup |
| **Artifact Files** | Artifact generation | Persistent | Manual cleanup |
| **Build Artifacts** | Build process | Rebuildable | Manual cleanup |
| **Test Artifacts** | Test execution | Temporary | Manual cleanup |
| **Sandbox Data** | Sandbox usage | Session-based | Manual cleanup |
| **Field Trial Data** | Field trials | Historical | Manual cleanup |
| **Backup Files** | Backup runs | Historical | Manual cleanup |

---

## 14. Runtime Data Health Assessment

### 14.1 Data Organization Health

| Aspect | Status | Assessment |
|--------|--------|------------|
| **Separation of Concerns** | GOOD | Clear separation between code, config, runtime data |
| **Directory Structure** | GOOD | Well-organized directory hierarchy |
| **Naming Conventions** | GOOD | Consistent naming patterns |
| **Empty Directories** | ACCEPTABLE | Many empty directories reserved for future use |
| **Temporary File Management** | NEEDS IMPROVEMENT | Manual cleanup, no automatic cleanup observed |
| **Cache Management** | ACCEPTABLE | Python bytecode cache only, no application cache |
| **Backup Strategy** | LIMITED | Single historical backup, no regular backup schedule observed |
| **Log Management** | ACCEPTABLE | Log files present, rotation policy unclear |
| **Artifact Management** | GOOD | Centralized artifact index |
| **Quarantine Process** | GOOD | Legacy code properly quarantined |

### 14.2 Runtime Data Growth Indicators

| Indicator | Observation | Assessment |
|-----------|-------------|------------|
| **Sprint Evolution** | Multiple sprint-specific temp directories | Organic growth |
| **Field Trial Accumulation** | 723+ field trial items | Historical data accumulation |
| **Report Proliferation** | 250+ report files | Extensive reporting |
| **Debug Temp Accumulation** | 13 specialized temp directories | Debug activity |
| **Build Artifacts** | 14.2MB launcher executable | Active development |
| **Artifact Index Size** | 885KB index | Substantial artifact registry |

---

## 15. Runtime Data Recommendations

### 15.1 Immediate Actions

1. **Temporary File Cleanup**
   - Implement automatic cleanup for temp directories
   - Define retention policies for debug temp files
   - Clean up empty temp directories

2. **Cache Management**
   - Implement application-level caching strategy
   - Define cache eviction policies
   - Monitor cache size and performance

3. **Log Management**
   - Implement log rotation policy
   - Define log retention periods
   - Monitor log file sizes

4. **Backup Strategy**
   - Implement regular backup schedule
   - Define backup retention policy
   - Test backup restoration process

### 15.2 Long-term Improvements

1. **Data Lifecycle Management**
   - Implement automated data lifecycle policies
   - Define data retention schedules
   - Implement automatic cleanup processes

2. **Storage Optimization**
   - Analyze storage usage patterns
   - Implement compression for historical data
   - Archive old field trial data

3. **Monitoring and Alerting**
   - Implement storage monitoring
   - Set up alerts for storage thresholds
   - Monitor data growth patterns

---

## 16. Runtime Data Statistics Summary

### 16.1 File Count by Category

| Category | File Count | Percentage |
|----------|------------|------------|
| **Source Code** | 2,340+ | ~45% |
| **Configuration** | 714 | ~14% |
| **Tests** | 952 | ~18% |
| **Runtime Data** | 1,000+ | ~19% |
| **Documentation** | 264 | ~5% |
| **Build Artifacts** | 15+ | ~0.3% |
| **Scripts** | 27 | ~0.5% |
| **Tools** | 105+ | ~2% |
| **Applications** | 1,602+ | ~31% (includes mobile) |
| **Total** | ~7,000+ | 100% |

### 16.2 Storage Estimation

| Category | Estimated Size | Notes |
|----------|----------------|-------|
| **Source Code** | ~50MB+ | Python source |
| **Configuration** | ~5MB+ | YAML files |
| **Tests** | ~20MB+ | Test files |
| **Runtime Data** | Unknown | Requires analysis |
| **Documentation** | ~2MB+ | Markdown files |
| **Build Artifacts** | ~15MB+ | Launcher executable |
| **Tools** | Variable | LLaMA CPP binaries |
| **Applications** | Variable | Android build |
| **Total** | ~100MB+ | Excluding runtime data |

### 16.3 Runtime Data Distribution

| Data Type | Count | Size | Percentage |
|-----------|-------|------|------------|
| **Code** | 2,340+ | ~50MB | ~50% |
| **Config** | 714 | ~5MB | ~5% |
| **Tests** | 952 | ~20MB | ~20% |
| **Runtime** | 1,000+ | Unknown | ~15% (estimated) |
| **Cache** | 50+ | Unknown | ~5% (estimated) |
| **Temporary** | 13 dirs | Unknown | ~3% (estimated) |
| **Generated** | 250+ | Unknown | ~2% (estimated) |

---

## Next Steps

This runtime inventory provides the foundation for:
- Cache analysis and optimization
- Temporary file cleanup strategy
- Storage optimization planning
- Backup strategy improvement
- Data lifecycle management
