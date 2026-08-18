
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aipinho.services.legacy_rag.legacy_core import cli_preview

raise SystemExit(cli_preview())
