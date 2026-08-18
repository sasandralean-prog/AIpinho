from __future__ import annotations

import json
import os
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.codex_agent import CodexArtifact, CodexChatMessage, CodexChatSession, CodexRun, CodexRunEvent
from aipinho.schemas.events.contracts import utc_now_iso


class CodexAgentStore:
    def __init__(self, root: Path | None = None) -> None:
        env_root = os.getenv("AIPINHO_CODEX_AGENT_ROOT")
        self.root = root or (Path(env_root) if env_root else PATHS.project_root / "data" / "runtime" / "codex_agent")
        self.sessions_path = self.root / "sessions.json"
        self.messages_dir = self.root / "messages"
        self.runs_dir = self.root / "runs"
        self.events_dir = self.root / "events"
        self.artifacts_path = self.root / "artifacts.json"
        self.artifact_files_dir = self.root / "artifact_files"

    def create(self, title: str = "Codex Agent") -> CodexChatSession:
        session = CodexChatSession(title=title)
        sessions = self.list(include_deleted=True)
        sessions.append(session)
        self._write_sessions(sessions)
        return session

    def list(self, *, include_deleted: bool = False) -> list[CodexChatSession]:
        if not self.sessions_path.exists():
            return []
        data = json.loads(self.sessions_path.read_text(encoding="utf-8"))
        sessions = [CodexChatSession(**item) for item in data.get("sessions", [])]
        return sessions if include_deleted else [session for session in sessions if not session.deleted]

    def get(self, session_id: str) -> CodexChatSession | None:
        return next((session for session in self.list(include_deleted=True) if session.session_id == session_id and not session.deleted), None)

    def rename(self, session_id: str, title: str) -> CodexChatSession | None:
        sessions = self.list(include_deleted=True)
        renamed = None
        for index, session in enumerate(sessions):
            if session.session_id == session_id and not session.deleted:
                renamed = session.model_copy(update={"title": title, "updated_at": utc_now_iso()})
                sessions[index] = renamed
                break
        if renamed:
            self._write_sessions(sessions)
        return renamed

    def delete(self, session_id: str) -> bool:
        sessions = self.list(include_deleted=True)
        changed = False
        for index, session in enumerate(sessions):
            if session.session_id == session_id and not session.deleted:
                sessions[index] = session.model_copy(update={"deleted": True, "updated_at": utc_now_iso(), "status": "deleted"})
                changed = True
                break
        if changed:
            self._write_sessions(sessions)
        return changed

    def add_message(self, message: CodexChatMessage) -> CodexChatMessage:
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        path = self.messages_dir / f"{message.session_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(message.model_dump(), ensure_ascii=True) + "\n")
        self.touch(message.session_id)
        return message

    def messages(self, session_id: str, *, after_message_id: str | None = None) -> list[CodexChatMessage]:
        path = self.messages_dir / f"{session_id}.jsonl"
        if not path.exists():
            return []
        rows = []
        seen_after = after_message_id is None
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    item = CodexChatMessage(**json.loads(line))
                    if not seen_after:
                        if item.message_id == after_message_id:
                            seen_after = True
                        continue
                    rows.append(item)
        return rows

    def create_run(
        self,
        *,
        session_id: str,
        user_prompt: str,
        workspace_path: str | None,
        requested_capabilities: list[str],
        autorun_enabled: bool,
        autoreview_enabled: bool,
        autoapproval_enabled: bool,
        autopilot_mode: str,
    ) -> CodexRun:
        run = CodexRun(
            session_id=session_id,
            user_prompt=user_prompt,
            workspace_path=workspace_path,
            requested_capabilities=requested_capabilities,
            autorun_enabled=autorun_enabled,
            autoreview_enabled=autoreview_enabled,
            autoapproval_enabled=autoapproval_enabled,
            autopilot_mode=autopilot_mode,
            status="running",
        )
        self.save_run(run)
        self.touch(session_id, status="running")
        return run

    def save_run(self, run: CodexRun) -> CodexRun:
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        (self.runs_dir / f"{run.run_id}.json").write_text(json.dumps(run.model_dump(), indent=2, ensure_ascii=True), encoding="utf-8")
        return run

    def get_run(self, run_id: str) -> CodexRun | None:
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            return None
        return CodexRun(**json.loads(path.read_text(encoding="utf-8")))

    def list_runs(self, *, session_id: str | None = None) -> list[CodexRun]:
        if not self.runs_dir.exists():
            return []
        runs = [CodexRun(**json.loads(path.read_text(encoding="utf-8"))) for path in self.runs_dir.glob("*.json")]
        if session_id:
            runs = [run for run in runs if run.session_id == session_id]
        return sorted(runs, key=lambda run: run.started_at, reverse=True)

    def latest_run(self, session_id: str) -> CodexRun | None:
        runs = self.list_runs(session_id=session_id)
        return runs[0] if runs else None

    def update_run(self, run_id: str, **updates) -> CodexRun | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        updated = run.model_copy(update=updates)
        self.save_run(updated)
        self.touch(updated.session_id, status=updated.status)
        return updated

    def add_event(self, event: CodexRunEvent) -> CodexRunEvent:
        self.events_dir.mkdir(parents=True, exist_ok=True)
        existing = self.events(event.run_id, limit=100000)
        event = event.model_copy(update={"sequence": len(existing) + 1})
        path = self.events_dir / f"{event.run_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(), ensure_ascii=True) + "\n")
        self.touch(event.session_id)
        return event

    def events(self, run_id: str, *, after_event_id: str | None = None, limit: int = 100) -> list[CodexRunEvent]:
        path = self.events_dir / f"{run_id}.jsonl"
        if not path.exists():
            return []
        rows: list[CodexRunEvent] = []
        seen_after = after_event_id is None
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                event = CodexRunEvent(**json.loads(line))
                if not seen_after:
                    if event.event_id == after_event_id:
                        seen_after = True
                    continue
                rows.append(event)
                if len(rows) >= max(1, limit):
                    break
        return rows

    def add_artifact(self, artifact: CodexArtifact) -> CodexArtifact:
        artifacts = [item for item in self.artifacts(include_deleted=True) if item.artifact_id != artifact.artifact_id]
        artifacts.append(artifact)
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts_path.write_text(json.dumps([item.model_dump() for item in artifacts], indent=2, ensure_ascii=True), encoding="utf-8")
        return artifact

    def artifacts(self, *, session_id: str | None = None, run_id: str | None = None, include_deleted: bool = False) -> list[CodexArtifact]:
        if not self.artifacts_path.exists():
            return []
        items = [CodexArtifact(**item) for item in json.loads(self.artifacts_path.read_text(encoding="utf-8"))]
        if session_id:
            items = [item for item in items if item.session_id == session_id]
        if run_id:
            items = [item for item in items if item.run_id == run_id]
        return items

    def get_artifact(self, artifact_id: str) -> CodexArtifact | None:
        return next((item for item in self.artifacts() if item.artifact_id == artifact_id), None)

    def touch(self, session_id: str, *, status: str | None = None) -> None:
        sessions = self.list(include_deleted=True)
        for index, session in enumerate(sessions):
            if session.session_id == session_id:
                sessions[index] = session.model_copy(update={"updated_at": utc_now_iso(), "status": status or session.status})
                self._write_sessions(sessions)
                return

    def _write_sessions(self, sessions: list[CodexChatSession]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.sessions_path.write_text(json.dumps({"sessions": [session.model_dump() for session in sessions]}, indent=2, ensure_ascii=True), encoding="utf-8")
