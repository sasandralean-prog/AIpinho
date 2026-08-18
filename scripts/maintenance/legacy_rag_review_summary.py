
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from aipinho.services.legacy_rag.legacy_core import cli_review_summary

raise SystemExit(cli_review_summary())
