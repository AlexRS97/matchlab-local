from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes_fixture import router as fixture_router
from app.api.routes_learning import router as learning_router
from app.api.routes_odds import router as odds_router
from app.api.routes_settings import router as settings_router
from app.api.routes_today import router as today_router
from app.api.routes_top import router as top_router
from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.connection import Database
from app.services.runtime import AnalyticsRuntime


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging()
        app.state.db = Database(settings.duckdb_path)
        app.state.settings = settings
        app.state.runtime = AnalyticsRuntime(settings, app.state.db)
        if settings.enable_scheduler:
            if app.state.runtime.learning.config["enabled"]:
                app.state.runtime.learning.start()
            app.state.runtime.scheduler.start()
        yield
        await app.state.runtime.close()
        app.state.db.close()

    app = FastAPI(title="MatchLab · Football Analytics AI", version="1.0.0", lifespan=lifespan)
    app.include_router(today_router)
    app.include_router(top_router)
    app.include_router(fixture_router)
    app.include_router(odds_router)
    app.include_router(settings_router)
    app.include_router(learning_router)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver", "api"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health")
    @app.get("/api/health")
    def health():
        return {"status": "ok", "application": "matchlab-local", "version": "1.0.0"}

    @app.middleware("http")
    async def security_headers(request, call_next):
        if request.method in {"POST", "PUT", "DELETE", "PATCH"} and request.headers.get(
            "origin"
        ) not in {
            None,
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        }:
            return JSONResponse({"detail": "Origen no autorizado"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    return app


app = create_app()
