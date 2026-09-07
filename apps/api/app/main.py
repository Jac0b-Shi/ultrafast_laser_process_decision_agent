from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import agent, administration, datasets, recommendations
from app.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Ultrafast Laser Process Decision API",
        version="0.1.0",
        description="Data-driven process decision MVP for ultrafast laser machining.",
    )
    @app.middleware("http")
    async def reject_cross_origin_writes(request, call_next):
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in settings.cors_origins:
            return JSONResponse({"detail": "不允许从该来源修改数据"}, status_code=403)
        return await call_next(request)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(administration.router)
    app.include_router(agent.router)
    app.include_router(datasets.router)
    app.include_router(recommendations.router)
    return app


app = create_app()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "laser-process-decision-api"}
