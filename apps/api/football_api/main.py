import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from football_api.config import get_settings
from football_api.routes import router

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.getLogger(__name__).info("Football Analytics API iniciada en %s", settings.app_env)
    yield


app = FastAPI(
    title="Football Analytics API",
    version="0.1.0",
    description=(
        "API de analisis probabilistico de goles y corners. "
        "Las predicciones no garantizan resultados ni beneficios."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "environment": settings.app_env,
        "demo_mode": not bool(settings.api_football_key),
    }

