from __future__ import annotations
from aipinho.services.supervisor.launcher_bootstrap_service import LauncherBootstrapService
from aipinho.services.supervisor.adb_reverse_service import ADBReverseService

def main() -> int:
    bootstrap = LauncherBootstrapService().bootstrap()
    print("AIpinho launcher bootstrap")
    print("monitor_first=", bootstrap["monitor_first"])
    print("planned_start_order=", ",".join(bootstrap["planned_start_order"]))
    print("token_configured=", bootstrap["token_configured"])
    for command in ADBReverseService().commands().commands:
        print(command)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
