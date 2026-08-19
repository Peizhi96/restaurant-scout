import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_internal_api_key(
    x_internal_api_key: Annotated[str | None, Header()] = None,
) -> None:
    configured_key = get_settings().internal_api_key
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal API key is not configured",
        )
    if not x_internal_api_key or not secrets.compare_digest(
        x_internal_api_key, configured_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )
