from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import get_settings
from app.database.session import async_session_factory

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    description="MVP Wirtualny CFO – integracja KSeF API 2.0",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


async def _check_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{settings.ollama_host.rstrip('/')}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


@app.get("/health")
async def health_check():
    database_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            database_ok = True
    except Exception:
        database_ok = False

    ollama_ok = await _check_ollama()

    return {
        "status": "ok" if database_ok else "degraded",
        "app": settings.app_name,
        "database": database_ok,
        "ollama": ollama_ok,
    }
