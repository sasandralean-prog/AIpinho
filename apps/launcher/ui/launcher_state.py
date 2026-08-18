from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LauncherState:
    host: str = "127.0.0.1"
    core_port: int = 9088
    realtime_port: int = 9089
    artifact_port: int = 9098
    monitor_port: int = 9099
    token: str | None = None
    selected_session_id: str | None = None
    selected_session_by_agent: dict[str, str] | None = None
    event_cursor: str = "0"

    @property
    def core_url(self) -> str: return f"http://{self.host}:{self.core_port}"
    @property
    def realtime_url(self) -> str: return f"http://{self.host}:{self.realtime_port}"
    @property
    def artifact_url(self) -> str: return f"http://{self.host}:{self.artifact_port}"
    @property
    def monitor_url(self) -> str: return f"http://{self.host}:{self.monitor_port}"

    @classmethod
    def config_path(cls) -> Path:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".aipinho")
        return base / "AIpinho" / "launcher_state.json"

    @classmethod
    def load(cls) -> "LauncherState":
        path = cls.config_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        allowed = {field for field in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in data.items() if key in allowed})

    def save(self) -> None:
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: getattr(self, key) for key in self.__dataclass_fields__}
        path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")

    def agent_session(self, agent_id: str) -> str | None:
        return (self.selected_session_by_agent or {}).get(agent_id)

    def save_agent_session(self, agent_id: str, session_id: str | None) -> None:
        sessions = dict(self.selected_session_by_agent or {})
        if session_id:
            sessions[agent_id] = session_id
        else:
            sessions.pop(agent_id, None)
        self.selected_session_by_agent = sessions
        self.save()
