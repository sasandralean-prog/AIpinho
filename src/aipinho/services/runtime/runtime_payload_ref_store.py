from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from aipinho.utils.safe_paths import resolve_within_root


class RuntimePayloadRefStore:
    """Run-scoped content-addressed JSON payload storage."""

    def __init__(self, *, root: Path) -> None:
        self.root = root

    def write_payload_ref(self, *, run_id: str, key: str, path: str, value: Any) -> dict[str, Any]:
        encoded = json.dumps(value, ensure_ascii=False, default=str, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        run_dir = resolve_within_root(self.root / run_id, self.root)
        ref_dir = resolve_within_root(run_dir / "payload_refs", self.root)
        ref_dir.mkdir(parents=True, exist_ok=True)
        ref_path = resolve_within_root(ref_dir / f"{digest}.json", self.root)
        if not ref_path.exists():
            tmp_path = ref_path.with_suffix(f".{os.getpid()}.tmp")
            tmp_path.write_bytes(encoded)
            os.replace(tmp_path, ref_path)
        try:
            content_ref = str(ref_path.relative_to(self.root))
        except Exception:
            content_ref = str(ref_path)
        return {
            "content_ref": content_ref,
            "hash": digest,
            "sha256": digest,
            "size_bytes": len(encoded),
            "record_count": len(value) if isinstance(value, list) else len(value) if isinstance(value, dict) else None,
            "reason_code": "RUNTIME_PAYLOAD_SPILLED_TO_REF",
            "path": path,
            "key": key,
            "summary": self.payload_summary(value),
        }

    def read_payload_ref(self, content_ref: Any, *, run_id: str | None = None, expected_sha256: str | None = None) -> Any:
        path = self._resolve_ref(content_ref, run_id=run_id)
        if path is None or not path.exists() or not path.is_file():
            return None
        raw = path.read_bytes()
        if expected_sha256 and hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("payload_ref_integrity_failed")
        return json.loads(raw.decode("utf-8-sig"))

    def _resolve_ref(self, content_ref: Any, *, run_id: str | None = None) -> Path | None:
        if not isinstance(content_ref, str) or not content_ref.strip():
            return None
        ref = content_ref.strip().replace("\\", "/")
        if ref.startswith("task_run_payload_ref:"):
            ref = ref.split(":", 1)[1].lstrip("/")
        candidates = [self.root / ref]
        if run_id:
            run_dir = self.root / run_id
            candidates.extend([run_dir / ref, run_dir / "payload_refs" / Path(ref).name])
        for candidate in candidates:
            try:
                return resolve_within_root(candidate, self.root)
            except Exception:
                continue
        return None

    def payload_summary(self, value: Any) -> dict[str, Any]:
        if isinstance(value, list):
            return {
                "type": "list",
                "count": len(value),
                "sample": [self.light_row(item) for item in value[:10]],
            }
        if isinstance(value, dict):
            return {
                "type": "dict",
                "keys": sorted(str(k) for k in value.keys())[:50],
                "counts": {
                    str(k): len(v)
                    for k, v in value.items()
                    if isinstance(v, (list, dict))
                },
            }
        return {"type": type(value).__name__}

    def light_row(self, item: Any) -> Any:
        if not isinstance(item, dict):
            return item
        allowed = {
            "artifact_id",
            "logical_path",
            "status",
            "validation_status",
            "content_type",
            "size_bytes",
            "sha256",
            "entity_id",
            "canonical_key",
            "attribute_name",
            "capability_id",
            "backend_id",
            "confidence",
            "observation_state",
            "gap_type",
            "reason_code",
        }
        return {key: value for key, value in item.items() if key in allowed}
