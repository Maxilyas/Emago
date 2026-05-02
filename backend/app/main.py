"""
app/main.py — Sprint 4
Agent 5 — Développeur Backend

Ajouts Sprint 4 : router alliances enregistré.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
import sqlalchemy as sa
from app.core.database import AsyncSessionLocal
from app.core.redis_client import get_redis
from app.core.config import get_settings
from app.core.redis_client import close_redis, init_redis

settings = get_settings()
scheduler = AsyncIOScheduler(timezone="UTC")


def _register_jobs() -> None:
    from app.tasks.forge_tick import run_forge_tick_job
    from app.tasks.resource_tick import run_resource_tick
    from app.tasks.build_tick import run_build_tick
    from app.tasks.fleet_arrival import run_fleet_arrivals
    from app.tasks.ranking import run_ranking_recalc
    from app.tasks.immunity_reset import run_immunity_reset

    scheduler.add_job(run_resource_tick,  "interval", seconds=settings.RESOURCE_TICK_SECONDS,
                      id="resource_tick",  max_instances=1, coalesce=True)
    scheduler.add_job(run_build_tick,     "interval", seconds=10,
                      id="build_tick",     max_instances=1, coalesce=True)
    scheduler.add_job(run_fleet_arrivals, "interval", seconds=5,
                      id="fleet_arrivals", max_instances=1, coalesce=True)
    scheduler.add_job(run_forge_tick_job, "interval", seconds=60,
                      id="forge_tick",     max_instances=1, coalesce=True)
    scheduler.add_job(run_ranking_recalc, "interval", minutes=settings.RANKING_RECALC_MINUTES,
                      id="ranking",        max_instances=1, coalesce=True)
    scheduler.add_job(
        run_immunity_reset,
        "interval",
        minutes=5,
        id="immunity_reset",
        max_instances=1,
        coalesce=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    _register_jobs()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import (
    auth, ships, modules, forge, planets, fleets,
    combat, ranking, scars, galaxy, expeditions, tech, daily, alliances,  # ← Sprint 4
)
from app.websocket.handler import router as ws_router

app.include_router(auth.router,       prefix="/api/v1")
app.include_router(ships.router,      prefix="/api/v1")
app.include_router(modules.router,    prefix="/api/v1")
app.include_router(forge.router,      prefix="/api/v1")
app.include_router(planets.router,    prefix="/api/v1")
app.include_router(fleets.router,     prefix="/api/v1")
app.include_router(combat.router,     prefix="/api/v1")
app.include_router(ranking.router,    prefix="/api/v1")
app.include_router(scars.router,      prefix="/api/v1")
app.include_router(galaxy.router,     prefix="/api/v1")
app.include_router(expeditions.router, prefix="/api/v1")
app.include_router(tech.router,       prefix="/api/v1")
app.include_router(daily.router,      prefix="/api/v1")
app.include_router(alliances.router,  prefix="/api/v1")  # ← Sprint 4
app.include_router(ws_router)


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    """
    Endpoint de santé pour Uptime Kuma et le load balancer.
    Vérifie la connectivité BDD et Redis.
    Retourne HTTP 200 si tout va bien, HTTP 503 sinon.
    """
    checks: dict[str, str] = {}
    overall_ok = True

    # Check PostgreSQL
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(sa.text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {str(e)[:50]}"
        overall_ok = False

    # Check Redis
    try:
        r = get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:50]}"
        overall_ok = False

    result = {
        "status": "ok" if overall_ok else "degraded",
        "version": settings.APP_VERSION,
        "checks": checks,
        "timestamp": time.time(),
    }

    if not overall_ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=result)

    return result
