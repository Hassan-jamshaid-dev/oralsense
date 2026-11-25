from fastapi import APIRouter

from app.db import check_database_status
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def read_health() -> HealthResponse:
    return HealthResponse(status="ok", database=check_database_status())
