from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["system"])


@router.get("/healthz")
def health() -> dict[str, Literal["ok"]]:
    return {"status": "ok"}


@router.get("/readyz")
def readiness(db: Session = Depends(get_db)) -> dict[str, Literal["ready"]]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
