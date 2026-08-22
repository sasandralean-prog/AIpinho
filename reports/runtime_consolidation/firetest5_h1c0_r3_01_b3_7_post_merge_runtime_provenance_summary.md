# H1C0.R3.01 B3.7 Post-Merge Runtime Sync Provenance

Mission class: post_merge_operational_runtime_provenance

Canonical main SHA: d76a1a21ceeef00f953d87a6aca07dcb6635c834
Local HEAD at runtime start: d76a1a21ceeef00f953d87a6aca07dcb6635c834
Origin main: d76a1a21ceeef00f953d87a6aca07dcb6635c834
Ahead/behind origin/main: 0	0
Runtime repo: C:\Dev\AIpinho

## Official Backend Restart

Backend was restarted using the official repository script:

`	ext
scripts/start_aipinho.ps1 -HostName 0.0.0.0 -Port 9088
`

The script delegates to:

`	ext
scripts/dev/start_aipinho_9088.ps1
`

Runtime process:

`	ext
PID: 22032
Started at: 08/21/2026 22:37:10
CWD: C:\Dev\AIpinho
Python: C:\Program Files\Python311\python.exe
Command: C:\Program Files\Python311\python.exe -m uvicorn aipinho.main:app --host 0.0.0.0 --port 9088
Listen: 0.0.0.0:9088
`

Official status:

`	ext
AIpinho status: ready_with_warnings
- Bootstrap Control 9080: offline
- Core Backend 9088: online
- Realtime 9089: optional
- Artifacts Port 9098: offline
- Monitor Supervisor 9099: reserved
- backend_health: ok
- health_semantics: offline
- mobile_dashboard: offline
- mobile_debugger: ok
- agents_status: ok
- runtime_hygiene_status: ok
`

## Import Provenance

`	ext
aipinho.__file__: C:\Dev\AIpinho\src\aipinho\__init__.py
aipinho.main: C:\Dev\AIpinho\src\aipinho\main.py
GovernedObservationExecutionStageService: C:\Dev\AIpinho\src\aipinho\services\artifacts\governed_observation_execution_stage_service.py
MediaMetadataObserverAdapter: C:\Dev\AIpinho\src\aipinho\capabilities\media_metadata\adapter.py
ReadonlyAnalysisArtifactRuntimeService: C:\Dev\AIpinho\src\aipinho\services\governance\runtime\readonly_analysis_artifact_runtime_service.py
public_runtime_api_router: C:\Dev\AIpinho\src\aipinho\api\routers\public_runtime_api_router.py
public_runtime_api_service: C:\Dev\AIpinho\src\aipinho\services\public_runtime_api_service.py
task_runtime_router: C:\Dev\AIpinho\src\aipinho\api\routers\task_runtime_router.py
`

All resolved AIpinho modules are under C:\Dev\AIpinho\src.

## Canonical Endpoints

- GET /api/v1/version: 200
- GET /api/v1/runtime: 200
- GET /api/v1/modules: 200
- GET /api/v1/contracts: 200

## Gates

FireTest 5: NOT_READY / NOT_EXECUTED
C gate: CORRECTIVE_REQUIRED_BEFORE_C
R3.01: OPEN

Remaining P0: none observed
Remaining P1: R3_01_B3_7_P1_PUBLIC_CANARY_NO_ELIGIBLE_MEDIA_CANDIDATES_IN_SELECTED_TARGET_SCOPE
Remaining P2: R3_01_B3_7_P2_ACCEPTED_RUNNING_WORKER_PROGRESS_VISIBILITY_DELAY

No FireTest 5 was run. ffprobe was not installed. Main was not modified directly after sync; reports are recorded on a report-only branch.
