"""Application factory. Routers are added here as each stage lands."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, collection, dev, health, library, listening, profile, recommendations, songs
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Tunewise API",
        version="0.1.0",
        description="Understand your music. Discover beyond it.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in (
        health.router,
        auth.router,
        profile.router,
        songs.router,
        collection.router,
        library.router,
        recommendations.router,
        listening.router,
    ):
        app.include_router(router, prefix="/api/v1")
    if settings.mock_provider_enabled:
        app.include_router(dev.router, prefix="/api/v1")
    return app


app = create_app()
