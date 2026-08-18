from __future__ import annotations

from fastapi import FastAPI

from aipinho import __version__
from aipinho.api.routers import bootstrap_control_router
from aipinho.core.local_environment import load_local_environment

load_local_environment()

app = FastAPI(title="AIpinho Bootstrap Control", version=__version__)


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "AIpinho Bootstrap Control", "port": 9080}


app.include_router(bootstrap_control_router.router)
