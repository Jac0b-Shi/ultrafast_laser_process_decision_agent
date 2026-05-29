from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import data_management, datasets, feedback, recommendations
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Ultrafast Laser Process Decision API",
        version="0.1.0",
        description="Data-driven process decision MVP for ultrafast laser machining.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(data_management.router)
    app.include_router(datasets.router)
    app.include_router(recommendations.router)
    app.include_router(feedback.router)
    return app


app = create_app()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "laser-process-decision-api"}
