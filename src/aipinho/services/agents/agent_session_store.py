from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.contracts import AgentEvent, AgentMessage, AgentRun, AgentSession
from aipinho.schemas.events.contracts import utc_now_iso


def _dump_model(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value.dict()


def _json_read(path: Path, default: Any) -> Any:
    if not path.exists() or path.stat().st_size == 0:
        return default
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return default
    return json.loads(text)


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


class AgentSessionStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_AGENT_KERNEL_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "agent_kernel")
        self.sessions_path = self.root / "sessions.json"
        self.messages_dir = self.root / "messages"
        self.runs_dir = self.root / "runs"
        self.events_dir = self.root / "events"
        self.session_sequence_dir = self.events_dir / "session_sequences"

    def create_session(self, session: AgentSession) -> AgentSession:
        sessions = self.list_sessions(include_deleted=True)
        sessions.append(session)
        self._write_sessions(sessions)
        return session

    def list_sessions(self, *, agent_id: str | None = None, include_deleted: bool = False) -> list[AgentSession]:
        payload = _json_read(self.sessions_path, {"sessions": []})
        sessions = [AgentSession(**item) for item in payload.get("sessions", [])]
        if agent_id is not None:
            sessions = [session for session in sessions if session.agent_id == agent_id]
        if not include_deleted:
            sessions = [session for session in sessions if not session.deleted]
        return sessions

    def get_session(self, agent_id: str, session_id: str, *, include_deleted: bool = False) -> AgentSession | None:
        for session in self.list_sessions(agent_id=agent_id, include_deleted=include_deleted):
            if session.session_id == session_id:
                return session
        return None

    def update_session(self, updated: AgentSession) -> AgentSession:
        sessions = self.list_sessions(include_deleted=True)
        for index, session in enumerate(sessions):
            if session.session_id == updated.session_id and session.agent_id == updated.agent_id:
                sessions[index] = updated
                self._write_sessions(sessions)
                return updated
        raise FileNotFoundError(updated.session_id)

    def soft_delete_session(self, agent_id: str, session_id: str) -> AgentSession | None:
        session = self.get_session(agent_id, session_id, include_deleted=True)
        if session is None:
            return None
        updated = session.model_copy(update={"deleted": True, "archived": True, "updated_at": utc_now_iso()})
        return self.update_session(updated)

    def add_message(self, message: AgentMessage) -> AgentMessage:
        path = self._messages_path(message.agent_id, message.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump_model(message), ensure_ascii=True) + "\n")
        self.touch_session(message.agent_id, message.session_id)
        return message

    def list_messages(self, agent_id: str, session_id: str, *, limit: int = 200) -> list[AgentMessage]:
        path = self._messages_path(agent_id, session_id)
        if not path.exists():
            return []
        rows: list[AgentMessage] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    rows.append(AgentMessage(**json.loads(line)))
        return rows[-limit:]

    def save_run(self, run: AgentRun) -> AgentRun:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        (self.runs_dir / f"{run.run_id}.json").write_text(json.dumps(_dump_model(run), indent=2, ensure_ascii=True), encoding="utf-8")
        self.touch_session(run.agent_id, run.session_id)
        return run

    def get_run(self, run_id: str) -> AgentRun | None:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return AgentRun(**json.loads(path.read_text(encoding="utf-8")))

    def list_runs(self, *, agent_id: str | None = None, session_id: str | None = None) -> list[AgentRun]:
        if not self.runs_dir.exists():
            return []
        rows = [AgentRun(**json.loads(path.read_text(encoding="utf-8"))) for path in self.runs_dir.glob("*.json")]
        if agent_id is not None:
            rows = [run for run in rows if run.agent_id == agent_id]
        if session_id is not None:
            rows = [run for run in rows if run.session_id == session_id]
        return sorted(rows, key=lambda run: run.started_at, reverse=True)

    def add_event(self, event: AgentEvent) -> AgentEvent:
        self.events_dir.mkdir(parents=True, exist_ok=True)
        existing_run_events = self.list_events(event.run_id, limit=100000, include_hidden=True)
        duplicate = next((item for item in existing_run_events if item.event_id == event.event_id), None)
        if duplicate is not None:
            return duplicate
        event = event.model_copy(update={
            "sequence": len(existing_run_events) + 1,
            "session_sequence": self._next_session_sequence(event.agent_id, event.session_id),
        })
        path = self._events_path(event.run_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_dump_model(event), ensure_ascii=True) + "\n")
        self.touch_session(event.agent_id, event.session_id)
        return event

    def list_events(self, run_id: str, *, limit: int = 200, include_hidden: bool = False) -> list[AgentEvent]:
        path = self._events_path(run_id)
        if not path.exists():
            return []
        rows: list[AgentEvent] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    event = AgentEvent(**json.loads(line))
                    if include_hidden or event.visible_in_timeline:
                        rows.append(event)
        return rows[-limit:]

    def list_events_by_session(self, agent_id: str, session_id: str, *, include_hidden: bool = False) -> list[AgentEvent]:
        if not self.events_dir.exists():
            return []
        rows: list[AgentEvent] = []
        for path in self.events_dir.glob("*.jsonl"):
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    event = AgentEvent(**json.loads(line))
                    if event.agent_id != agent_id or event.session_id != session_id:
                        continue
                    if include_hidden or event.visible_in_timeline:
                        rows.append(event)
        return sorted(rows, key=lambda event: (event.session_sequence, event.created_at, event.event_id))

    def touch_session(self, agent_id: str, session_id: str) -> None:
        session = self.get_session(agent_id, session_id, include_deleted=True)
        if session is None:
            return
        self.update_session(session.model_copy(update={"updated_at": utc_now_iso()}))

    def _write_sessions(self, sessions: list[AgentSession]) -> None:
        _json_write(self.sessions_path, {"sessions": [_dump_model(session) for session in sessions]})

    def _next_session_sequence(self, agent_id: str, session_id: str) -> int:
        path = self._session_sequence_path(agent_id, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        current = 0
        if path.exists():
            try:
                current = int(path.read_text(encoding="utf-8").strip() or "0")
            except ValueError:
                current = 0
        next_value = current + 1
        path.write_text(str(next_value), encoding="utf-8")
        return next_value

    def _messages_path(self, agent_id: str, session_id: str) -> Path:
        safe_agent = agent_id.replace("/", "_")
        safe_session = session_id.replace("/", "_")
        return self.messages_dir / safe_agent / f"{safe_session}.jsonl"

    def _events_path(self, run_id: str) -> Path:
        return self.events_dir / f"{run_id}.jsonl"

    def _session_sequence_path(self, agent_id: str, session_id: str) -> Path:
        safe_agent = agent_id.replace("/", "_")
        safe_session = session_id.replace("/", "_")
        return self.session_sequence_dir / safe_agent / f"{safe_session}.txt"
