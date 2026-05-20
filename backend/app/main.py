from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestIDMiddleware
from app.routes.auth_routes import router as auth_router
from app.routes.finance import router as finance_router
from app.routes.health import router as health_router
from app.routes.watchlist import router as watchlist_router

configure_logging(get_settings().log_level)

app = FastAPI(title="News & Markets Dashboard API", version="0.1.0")
app.add_middleware(RequestIDMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(finance_router)
