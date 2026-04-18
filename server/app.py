"""
HoopProphet API v2 — FastAPI app with lifespan model preloading.

V1 references (ml.*, nba_api.*) and per-request training fully removed.
Player/team/game-log data served from SQLite cache.
Model artifact loaded once at startup (not per request).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.core.config import API_HOST, API_PORT, CORS_ORIGINS, MODEL_ARTIFACT_PATH
from server.pipeline.artifact import load_artifact

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model artifact at startup; clean up on shutdown."""
    # Startup: load model artifact per D-10 (graceful degradation)
    try:
        import os

        if os.path.exists(MODEL_ARTIFACT_PATH):
            app.state.model_artifact = load_artifact()
            logger.info("Model artifact loaded successfully from %s", MODEL_ARTIFACT_PATH)
        else:
            app.state.model_artifact = None
            logger.warning(
                "Model artifact not found at %s — prediction endpoints will return empty results",
                MODEL_ARTIFACT_PATH,
            )
    except Exception as e:
        app.state.model_artifact = None
        logger.error("Failed to load model artifact: %s", e)

    yield

    # Shutdown: release artifact reference
    app.state.model_artifact = None


app = FastAPI(
    title="HoopProphet API",
    description="NBA Player Prop Betting Analytics",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    """Health check with model load status per D-16."""
    model_loaded = hasattr(app.state, "model_artifact") and app.state.model_artifact is not None
    return {
        "status": "healthy",
        "service": "HoopProphet API",
        "version": "2.0.0",
        "model_loaded": model_loaded,
    }


# V2 API routers
from server.api.players import router as players_router
from server.api.teams import router as teams_router

app.include_router(players_router)
app.include_router(teams_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.app:app", host=API_HOST, port=API_PORT, reload=True)
