from __future__ import annotations

import hashlib
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.utils.yaml_loader import load_yaml_file


class AtomicWriteResult(AIpinhoModel):
    status: str
    target_path: str
    temp_path: str
    content_hash: str = ""
    bytes_written: int = 0
    chars_written: int = 0
    blocked_reasons: list[str] = []


class ArtifactAtomicWriteService:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_atomic_write_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        self.execution_policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_write_execution_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")

    def write_text_atomic(self, target_path: str, content: str, *, overwrite: bool) -> AtomicWriteResult:
        path = Path(target_path)
        suffix = str((self.policy.get("atomic_write", {}) or {}).get("temp_suffix", ".aipinho_tmp"))
        temp = path.with_name(path.name + suffix)
        if temp.exists():
            return AtomicWriteResult(status="blocked", target_path=str(path), temp_path=str(temp), blocked_reasons=["temp_exists"])
        if path.exists() and not overwrite:
            return AtomicWriteResult(status="blocked", target_path=str(path), temp_path=str(temp), blocked_reasons=["target_exists"])
        max_bytes = int((self.execution_policy.get("execution", {}) or {}).get("max_write_bytes", 300000))
        encoded = content.encode("utf-8")
        if len(encoded) > max_bytes:
            return AtomicWriteResult(status="blocked", target_path=str(path), temp_path=str(temp), blocked_reasons=["write_bytes_limit_exceeded"])
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
            temp.replace(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            return AtomicWriteResult(status="completed", target_path=str(path), temp_path=str(temp), content_hash=digest, bytes_written=len(encoded), chars_written=len(content))
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_atomic_write", "shell_enabled": False}
