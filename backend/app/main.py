"""SmartGaz FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.db import Base, engine
from .api.v1 import auth, territory, households, orders, routes, tracking, admin


logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables on dev (SQLite); production uses Alembic migrations.
    if settings.DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="SmartGaz API",
    description="Qishloq hududlarida suyultirilgan gaz yetkazib berishni raqamlashtirish platformasi — backend API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/api/v1/ping", tags=["health"])
async def api_ping():
    return {"ping": "pong"}


# Include versioned routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(territory.router, prefix="/api/v1")
app.include_router(households.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(routes.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
