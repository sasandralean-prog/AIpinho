from __future__ import annotations
import hashlib
import json
import secrets
from pathlib import Path
from typing import Any
from aipinho.core.paths import PATHS
from aipinho.schemas.supervisor.contracts import MobilePairingResult

class LocalTokenService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.project_root / "data" / "runtime" / "security" / "mobile_pairing" / "token.json"

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    def status(self) -> dict[str, object]:
        data = self._read()
        return {"status": "ok", "token_configured": bool(data.get("token_hash")), "token_preview": data.get("token_preview"), "plaintext_available": False}

    def create_token(self, status: str = "created") -> MobilePairingResult:
        token = secrets.token_urlsafe(32)
        preview = f"{token[:4]}...{token[-4:]}"
        self._write({"token_hash": self._hash(token), "token_preview": preview})
        return MobilePairingResult(status=status, token_configured=True, token=token, token_preview=preview, human_message="Token criado. Guarde agora; o plaintext nao sera exibido em status futuro.")

    def ensure_token(self) -> dict[str, object]:
        if not self.status()["token_configured"]:
            result = self.create_token()
            return {"token_configured": True, "token_preview": result.token_preview, "created": True}
        return {"token_configured": True, "token_preview": self.status().get("token_preview"), "created": False}

    def validate_token(self, token: str | None) -> bool:
        if not token:
            return False
        expected = self._read().get("token_hash")
        return bool(expected) and self._hash(token) == expected

    def validate_authorization(self, authorization: str | None) -> bool:
        if not authorization or not authorization.lower().startswith("bearer "):
            return False
        return self.validate_token(authorization.split(" ", 1)[1].strip())

    def redact(self, value: str | None) -> str:
        if not value:
            return ""
        return "Bearer [REDACTED_TOKEN]" if value.lower().startswith("bearer ") else "[REDACTED_TOKEN]"
