from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from apps.launcher.ui.launcher_app import LauncherApp


def main() -> int:
    app = LauncherApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
