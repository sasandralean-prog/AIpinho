from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from aipinho import __version__
from aipinho.core.local_environment import load_local_environment

load_local_environment()

from aipinho.api.routers import ROUTERS
from aipinho.services.runtime.task_queue_maintenance_service import TaskQueueMaintenanceService


@asynccontextmanager
async def _lifespan(_: FastAPI):
    if os.getenv("AIPINHO_BACKGROUND_TASK_QUEUE", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        yield
        return
    stop_event = asyncio.Event()
    maintenance = TaskQueueMaintenanceService()
    worker = asyncio.create_task(maintenance.run_forever(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await worker


def create_app() -> FastAPI:
    app = FastAPI(title="AIpinho", version=__version__, lifespan=_lifespan)
    for router in ROUTERS:
        app.include_router(router)
    return app
