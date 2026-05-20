from fastapi import FastAPI

from app.routes.health import router as health_router

app = FastAPI(title="News & Markets Dashboard API", version="0.1.0")
app.include_router(health_router)
