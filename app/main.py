import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.agent_routes import router as agent_router
from app.api.auth_routes import router as auth_router
from app.auth import decode_access_token, is_public_path
from app.config import get_settings
from app.api.alerts_routes import router as alerts_router
from app.api.demo_routes import router as demo_router
from app.api.routes import router
from app.api.scheduler_routes import router as scheduler_router
from app.api.settings_routes import router as settings_router
from app.brand import PRODUCT_NAME, PRODUCT_TAGLINE
from app.config import reload_settings
from app.db_migrate import run_migrations
from app.database import init_db, SessionLocal
from app.scheduler import start_scheduler, stop_scheduler
from app.seed import seed_competitors
from app.services.alerts import seed_default_alert_rules

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=PRODUCT_NAME,
    description=f"{PRODUCT_TAGLINE} — pricing, messaging, hiring, and news signals powered by Bright Data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    settings = get_settings()
    if not settings.auth_enabled:
        return await call_next(request)

    path = request.url.path.rstrip("/") or "/"
    if request.method == "OPTIONS" or is_public_path(path):
        return await call_next(request)

    if not path.startswith("/api/v1"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[7:].strip()
    try:
        decode_access_token(token)
    except Exception:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired session"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await call_next(request)


app.include_router(router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    reload_settings()
    init_db()
    run_migrations()
    db = SessionLocal()
    try:
        seed_competitors(db)
        seed_default_alert_rules(db)
    finally:
        db.close()
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/")
def root():
    return {
        "service": PRODUCT_NAME,
        "docs": "/docs",
        "api": "/api/v1",
    }
