"""FastAPI application for the Agentic SDLC dashboard backend."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agents, approvals, ingest, plan, projects, reports
from src.api.routes import prototype as prototype_routes
from src.api.schemas.project import HealthResponse
from src.config import settings

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="D8X Platform",
    description="D8X — AI-powered SDLC pipeline with 8 specialized agents",
    version="0.1.0",
)


@app.on_event("startup")
async def _dispose_stale_pool() -> None:
    """Dispose the connection pool on startup to clear any stale asyncpg enum caches."""
    from src.context_store.database import engine

    await engine.dispose()
    logger.info("Database connection pool disposed — fresh connections will use updated enum types")

# CORS - allow dashboard dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(projects.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(plan.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(prototype_routes.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.app_env,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
