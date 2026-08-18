from __future__ import annotations


class MemoryReadPolicyService:
    def explicit_read_allowed(self) -> bool:
        return True

    def chat_listing_allowed(self) -> bool:
        return True

    def prompt_assembly_auto_injection_allowed(self) -> bool:
        return False

    def chat_auto_injection_allowed(self) -> bool:
        return False

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "explicit_read_allowed": True,
            "chat_listing_allowed": True,
            "prompt_assembly_auto_injection": False,
            "chat_auto_injection": False,
        }
