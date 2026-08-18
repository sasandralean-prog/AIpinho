from __future__ import annotations

import asyncio

from aipinho.services.runtime.task_queue_service import TaskQueueService


class TaskQueueMaintenanceService:
    def __init__(self, queue: TaskQueueService | None = None) -> None:
        self.queue = queue or TaskQueueService()

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                await asyncio.to_thread(self._process_queue)
            except Exception:
                # Queue maintenance is best-effort and must never terminate the API.
                pass
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=self.queue.reconcile_interval_seconds,
                )
            except TimeoutError:
                continue

    @staticmethod
    def _process_queue() -> None:
        from aipinho.services.runtime.task_runtime_service import TaskRuntimeService

        TaskRuntimeService().process_queue()
