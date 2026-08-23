# FireTest C FFmpeg Environment Closure

Verdict: `FFMPEG_ENVIRONMENT_READY`

Generated: 2026-08-23T18:49:58.433392+00:00

AIpinho branch: `agent/codex/firetest-c-ffmpeg-full-phase-diagnostic`
AIpinho HEAD: `cb6aca595eb12dd64171c52f7dd779f50ebf2d5c`

Installation: `winget install --id Gyan.FFmpeg --exact`
FFmpeg: `C:\Users\rafae\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe`
FFmpeg version: `ffmpeg version 9.0-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers`
FFprobe: `C:\Users\rafae\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffprobe.exe`
FFprobe version: `ffprobe version 9.0-full_build-www.gyan.dev Copyright (c) 2007-2026 the FFmpeg developers`

## Contract Closure
- Added deterministic media CLI discovery/version contract for ffmpeg and ffprobe.
- Expanded media backend statuses: available, unavailable, executable_but_unusable, version_or_probe_error.
- FFprobe backend records resolved executable path/version and uses resolved executable for subprocess argv with shell=False.
- Media metadata payload now exposes media_environment with ffmpeg/ffprobe state.
- PinhoForge hardware profiler now includes ffprobe and media readiness requires ffmpeg+ffprobe.
- Artifact runtime preserves compile_only observer-deferred semantics when FFprobe availability makes media capability configured.

## Real Media Fixture
- Path: `reports\firetest_c_media_fixture\sine.wav`
- Size: 88278 bytes
- SHA256: `d74a5bc0d070b17330bc5d14643c33fd8feb5326638c0ddf161dc32c362e6f7b`
- Container: `wav`
- Duration: `1.000000`
- Streams: 1

## Validation
- compile: python -m compileall -q src tests -> PASS
- focused: python -m pytest tests/unit/test_media_metadata_capability_pack.py tests/unit/test_pinhoforge_bridge.py -q -> 82 passed, 1 skipped
- relevant_regression: python -m pytest tests/unit/test_media_metadata_capability_pack.py tests/unit/test_media_metadata_capability_policy.py tests/unit/test_pinhoforge_bridge.py tests/unit/test_governed_post_compile_observation_execution_stage.py tests/unit/test_contract_driven_perception_service.py -q -> 151 passed, 1 skipped
- diff_check: git diff --check -> PASS

Media extraction success is technical evidence only; it is not semantic media understanding.
