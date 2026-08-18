from __future__ import annotations

import json
import os
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.gemini_executor import GeminiExecutorMessage, GeminiExecutorSession


class GeminiExecutorSessionStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_GEMINI_EXECUTOR_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "gemini_executor")
        self.sessions_path = self.root / "sessions.json"
        self.messages_dir = self.root / "messages"

    def create(self, title: str = "Gemini Executor") -> GeminiExecutorSession:
        session = GeminiExecutorSession(title=title)
        sessions = self.list()
        sessions.append(session)
        self._write_sessions(sessions)
        return session

    def list(self) -> list[GeminiExecutorSession]:
        if not self.sessions_path.exists():
            return []
        data = json.loads(self.sessions_path.read_text(encoding="utf-8"))
        return [GeminiExecutorSession(**item) for item in data.get("sessions", [])]

    def get(self, session_id: str) -> GeminiExecutorSession | None:
        return next((session for session in self.list() if session.session_id == session_id), None)

    def rename(self, session_id: str, title: str) -> GeminiExecutorSession | None:
        sessions = self.list()
        renamed: GeminiExecutorSession | None = None
        for index, session in enumerate(sessions):
            if session.session_id == session_id:
                renamed = session.model_copy(update={"title": title, "updated_at": utc_now_iso()})
                sessions[index] = renamed
                break
        if renamed is not None:
            self._write_sessions(sessions)
        return renamed

    def delete(self, session_id: str) -> bool:
        sessions = self.list()
        remaining = [session for session in sessions if session.session_id != session_id]
        if len(remaining) == len(sessions):
            return False
        self._write_sessions(remaining)
        path = self.messages_dir / f"{session_id}.jsonl"
        if path.exists():
            path.unlink()
        return True

    def touch(self, session_id: str, *, status: str | None = None) -> GeminiExecutorSession | None:
        sessions = self.list()
        updated: GeminiExecutorSession | None = None
        for index, session in enumerate(sessions):
            if session.session_id == session_id:
                updated = session.model_copy(update={"updated_at": utc_now_iso(), "status": status or session.status})
                sessions[index] = updated
                break
        if updated is not None:
            self._write_sessions(sessions)
        return updated

    def add_message(self, message: GeminiExecutorMessage) -> GeminiExecutorMessage:
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        path = self.messages_dir / f"{message.session_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.model_dump(), ensure_ascii=True) + "\n")
        self.touch(message.session_id)
        return message

    def messages(self, session_id: str) -> list[GeminiExecutorMessage]:
        path = self.messages_dir / f"{session_id}.jsonl"
        if not path.exists():
            return []
        rows: list[GeminiExecutorMessage] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(GeminiExecutorMessage(**json.loads(line)))
        return rows

    def _write_sessions(self, sessions: list[GeminiExecutorSession]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {"sessions": [session.model_dump() for session in sessions]}
        self.sessions_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
