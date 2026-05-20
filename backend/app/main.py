from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.finance import router as finance_router
from app.routes.health import router as health_router
from app.routes.watchlist import router as watchlist_router
from app.scheduler import shutdown_scheduler, start_scheduler

# Load backend/.env (if present) before any settings are read.
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="News & Markets Dashboard API", version="0.1.0",
              lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials="*" not in _settings.cors_origins,
)
app.add_middleware(RequestIDMiddleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(finance_router)
