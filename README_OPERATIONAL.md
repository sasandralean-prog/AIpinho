# AIpinho Operational README

AIpinho RC3 is a local daily-use candidate. It provides scripts for start, stop, status, doctor, mobile pairing, backup and restore preview.

## Official Ports

- `9088`: core backend.
- `9089`: realtime/optional.
- `9098`: artifact service port when separated; artifact endpoints are also available through the core backend.
- `9099`: monitor/supervisor control plane. It must not restart itself.

## Daily Flow

1. Run `START_AIPINHO.bat` from the RC3 package or `scripts\start_aipinho.ps1` from the project root.
2. Run `STATUS_AIPINHO.bat`.
3. Run `DOCTOR_AIPINHO.bat` if status is unclear.
4. Open Launcher or mobile.
5. Use agents and artifacts.
6. Run backup before long field trials.
7. Stop with `STOP_AIPINHO.bat`.

## Evidence

Health, doctor and release reports are written under `reports\health` and `reports\release`.

