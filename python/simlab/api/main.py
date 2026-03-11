"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from simlab.api.routes_runs import router as runs_router
from simlab.config import load_app_paths, load_grounding_settings
from simlab.storage.db import connect, initialize


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        paths = load_app_paths()
        paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
        paths.runs_dir.mkdir(parents=True, exist_ok=True)
        paths.cache_dir.mkdir(parents=True, exist_ok=True)
        connection = connect(paths.db_path)
        initialize(connection)
        connection.close()
        app.state.paths = paths
        app.state.grounding_settings = load_grounding_settings()
        yield

    app = FastAPI(
        title="SimLab Control Plane",
        version="0.1.0",
        summary="Thin control plane for large-scale agent simulation runs.",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(runs_router)
    return app


app = create_app()
