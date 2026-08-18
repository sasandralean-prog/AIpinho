from __future__ import annotations

from fastapi import FastAPI

from aipinho import __version__
from aipinho.api.routers import backend_control_router, health_router, monitor_router
from aipinho.core.local_environment import load_local_environment

load_local_environment()

app = FastAPI(title="AIpinho Monitor Supervisor", version=__version__)
app.include_router(health_router.router)
app.include_router(monitor_router.router)
app.include_router(backend_control_router.router)
