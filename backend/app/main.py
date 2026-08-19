from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="V1 restaurant acquisition and corporate-catering intelligence API.",
)
app.include_router(api_router)
