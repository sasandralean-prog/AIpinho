from __future__ import annotations


class MemoryPolicyResolver:
    def status(self) -> dict[str, object]:
        return {"status": "ok", "runtime_enabled": False, "auto_save_enabled": False}