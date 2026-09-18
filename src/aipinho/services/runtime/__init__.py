from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aipinho.services.runtime.supervised_execution_loop import (
        SupervisedExecutionLoop,
    )
    from aipinho.services.runtime.task_runtime_service import TaskRuntimeService

__all__ = ["TaskRuntimeService", "SupervisedExecutionLoop"]


def __getattr__(name: str) -> Any:
    if name == "TaskRuntimeService":
        from aipinho.services.runtime.task_runtime_service import (
            TaskRuntimeService,
        )

        return TaskRuntimeService
    if name == "SupervisedExecutionLoop":
        from aipinho.services.runtime.supervised_execution_loop import (
            SupervisedExecutionLoop,
        )

        return SupervisedExecutionLoop
    raise AttributeError(
        f"module {__name__!r} has no attribute {name!r}"
    )


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
