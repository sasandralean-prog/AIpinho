from __future__ import annotations

from pathlib import Path

from aipinho.services.patching.apply.patch_apply_hashing import sha256_file


class AtomicPatchWriteService:
    TEMP_SUFFIX = ".aipinho_patch_tmp"

    def write(self, target: Path, content: str) -> str:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + self.TEMP_SUFFIX)
        if temp.exists():
            raise ValueError("patch_temp_file_exists")
        try:
            temp.write_text(content, encoding="utf-8")
            temp.replace(target)
            return sha256_file(target)
        finally:
            if temp.exists():
                temp.unlink()

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "atomic_patch_write", "shell_enabled": False, "git_enabled": False}
