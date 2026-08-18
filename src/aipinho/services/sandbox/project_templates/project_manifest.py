from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.events.contracts import utc_now_iso


def project_manifest_json(**payload: Any) -> str:
    manifest = {
        "generated_by": "AIpinho Sandbox Project Factory",
        "created_at": utc_now_iso(),
        **payload,
    }
    return json.dumps(manifest, ensure_ascii=True, indent=2) + "\n"
