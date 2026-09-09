"""IceNavigator FastAPI application entry point."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger

# Add parent to sys.path so `config` is importable from routes
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_settings
from app.routes import ice, icebergs, ships, navigation


# ── Startup / Shutdown ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services on startup, clean up on shutdown."""
    settings = get_settings()
    logger.info("IceNavigator starting up [env={}]", settings.app_env)

    # Ensure directories exist
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.model_cache_dir).mkdir(parents=True, exist_ok=True)

    # Connect cache
    from app.services.cache_service import get_cache
    cache = get_cache()
    await cache.connect()

    # Pre-load models (non-blocking – logs warnings if weights missing)
    from app.services.icenet_service import get_icenet
    from app.services.drift_service import get_drift
    from app.services.bathymetry_service import get_bathymetry

    get_icenet()   # loads or falls back
    get_drift()    # loads or falls back
    get_bathymetry()  # loads GEBCO or falls back

    logger.info("All services initialized.")
    yield

    # Shutdown
    await cache.disconnect()
    logger.info("IceNavigator shut down.")


# ── App Factory ────────────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="IceNavigator API",
    description=(
        "Antarctic Navigation Decision Support System. "
        "Provides sea-ice forecasting, iceberg tracking, ship AIS data, "
        "and A* route optimization for Southern Ocean navigation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(ice.router)
app.include_router(icebergs.router)
app.include_router(ships.router)
app.include_router(navigation.router)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "IceNavigator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
