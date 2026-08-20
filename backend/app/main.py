from fastapi import FastAPI, Request
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import get_settings, validate_production_settings

settings = get_settings()
validate_production_settings(settings)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="V1 restaurant acquisition and corporate-catering intelligence API.",
    docs_url=None if settings.app_env.casefold() == "production" else "/docs",
    redoc_url=None if settings.app_env.casefold() == "production" else "/redoc",
    openapi_url=None if settings.app_env.casefold() == "production" else "/openapi.json",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.trusted_hosts))


@app.middleware("http")
async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(api_router)
