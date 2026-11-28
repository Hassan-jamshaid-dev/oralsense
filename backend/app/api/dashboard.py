from fastapi import APIRouter

from app.deps import CurrentUser, DbSession
from app.schemas import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def read_dashboard_summary(user: CurrentUser, db: DbSession) -> DashboardSummary:
    return dashboard_service.build_dashboard_summary(db, user)
