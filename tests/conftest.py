from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("AIPINHO_BACKGROUND_TASK_QUEUE", "0")

from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.memory.operational_memory_service import OperationalMemoryService
from aipinho.services.runtime.engineering_autopilot_service import EngineeringAutopilotService


@pytest.fixture
def task_runtime_store(tmp_path: Path) -> TaskRunStore:
    return TaskRunStore(root=tmp_path / "task_runs")


@pytest.fixture
def readonly_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Demo\n\nSmall readonly fixture.\n", encoding="utf-8")
    (workspace / "app.py").write_text("def hello():\n    return 'ok'\n", encoding="utf-8")
    return workspace


@pytest.fixture
def task_runtime_service(task_runtime_store: TaskRunStore, tmp_path: Path) -> TaskRuntimeService:
    return TaskRuntimeService(
        store=task_runtime_store,
        operational_memory=OperationalMemoryService(root=tmp_path / "operational_memory"),
        engineering_autopilot=EngineeringAutopilotService(root=tmp_path / "engineering_missions"),
    )




