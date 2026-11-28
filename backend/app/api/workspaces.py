from fastapi import APIRouter, status

from app.deps import CurrentCsrf, CurrentUser, DbSession
from app.schemas import MeResponse, WorkspaceCreateRequest, WorkspaceUpdateRequest
from app.services import auth_service, workspace_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreateRequest, user: CurrentUser, csrf_token: CurrentCsrf, db: DbSession
) -> MeResponse:
    workspace_service.create_workspace_for_onboarding(db, user, payload)
    return auth_service.build_me_response(db, user, csrf_token=csrf_token)


@router.patch("/current", response_model=MeResponse)
def update_current_workspace(
    payload: WorkspaceUpdateRequest,
    user: CurrentUser,
    csrf_token: CurrentCsrf,
    db: DbSession,
) -> MeResponse:
    workspace_service.update_current_workspace(db, user, payload)
    return auth_service.build_me_response(db, user, csrf_token=csrf_token)
