from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.chat.chat_response import ChatResponse


class ChatResultIndexService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.project_root / "data" / "runtime" / "interaction" / "result_index"

    def add_final_answer(self, session_id: str, response: ChatResponse, message_id: str) -> str | None:
        if not response.is_final_answer or not response.grounded:
            return None
        if response.message_type not in {"assistant_final_answer", "system_diagnostic_result"}:
            return None
        result_ref_id = response.result_ref_id or f"result_{uuid4().hex}"
        rows = self._read(session_id)
        rows.append({
            "result_ref_id": result_ref_id,
            "message_id": message_id,
            "message_type": response.message_type,
            "operation_type": response.operation_type,
            "result_kind": self._result_kind(response),
            "summary": response.message,
            "grounded": response.grounded,
            "evidence_refs": response.evidence_refs,
        })
        self._write(session_id, rows[-100:])
        return result_ref_id

    def latest_final_answer(self, session_id: str, *, result_kind: str = "answer") -> dict[str, Any] | None:
        for row in reversed(self._read(session_id)):
            if (
                row.get("message_type") in {"assistant_final_answer", "system_diagnostic_result"}
                and row.get("grounded") is True
                and self._row_matches_kind(row, result_kind)
            ):
                return row
        return None

    def _result_kind(self, response: ChatResponse) -> str:
        if response.operation_type in {"session_diagnostic", "readonly_project_analysis", "readonly_analysis_with_artifact_output"}:
            return "summary"
        if response.intent.get("result_kind") in {"answer", "summary"}:
            return str(response.intent["result_kind"])
        return "answer"

    def _row_matches_kind(self, row: dict[str, Any], result_kind: str) -> bool:
        stored_kind = row.get("result_kind")
        if stored_kind:
            return stored_kind == result_kind
        if result_kind == "answer":
            return True
        return row.get("operation_type") in {"session_diagnostic", "readonly_project_analysis", "readonly_analysis_with_artifact_output"}

    def _path(self, session_id: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in session_id)
        return self.root / f"{safe}.json"

    def _read(self, session_id: str) -> list[dict[str, Any]]:
        path = self._path(session_id)
        if not path.exists() or path.stat().st_size == 0:
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []

    def _write(self, session_id: str, rows: list[dict[str, Any]]) -> None:
        path = self._path(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
