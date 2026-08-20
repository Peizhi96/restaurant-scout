from fastapi import APIRouter

from app.api.routes import (
    due_diligence,
    duplicates,
    external_leads,
    health,
    jobs,
    listings,
    scoring,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(listings.router, prefix="/api/listings", tags=["listings"])
api_router.include_router(scoring.router, prefix="/api/listings", tags=["scoring"])
api_router.include_router(
    duplicates.router,
    prefix="/api/possible-duplicates",
    tags=["possible-duplicates"],
)
api_router.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
api_router.include_router(due_diligence.router, tags=["due-diligence"])
api_router.include_router(
    external_leads.router,
    prefix="/api/external-leads",
    tags=["external-leads"],
)
