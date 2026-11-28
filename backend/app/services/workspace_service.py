import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.errors import AppError
from app.models import User, Workspace, WorkspaceMembership
from app.schemas import WorkspaceCreateRequest, WorkspaceUpdateRequest


def get_current_membership(db: Session, user_id: uuid.UUID) -> WorkspaceMembership | None:
    """The single definition of a user's "current workspace".

    Today this is the earliest membership. Workspace switching can change this one function.
    """
    return db.scalar(
        select(WorkspaceMembership)
        .options(joinedload(WorkspaceMembership.workspace))
        .where(WorkspaceMembership.user_id == user_id)
        .order_by(WorkspaceMembership.created_at, WorkspaceMembership.id)
        .limit(1)
    )


def require_current_membership(db: Session, user_id: uuid.UUID) -> WorkspaceMembership:
    membership = get_current_membership(db, user_id)
    if membership is None:
        raise AppError(404, "workspace_not_found", "Set up a workspace to continue.")
    return membership


def create_workspace_for_onboarding(
    db: Session, user: User, request: WorkspaceCreateRequest
) -> WorkspaceMembership:
    # Lock the user row so two concurrent onboarding submissions cannot both pass the check below.
    locked_user = db.scalar(select(User).where(User.id == user.id).with_for_update())
    if locked_user is None:
        raise AppError(401, "not_authenticated", "Sign in to continue.")

    if get_current_membership(db, locked_user.id) is not None:
        db.rollback()
        raise AppError(409, "workspace_exists", "Your workspace is already set up.")

    workspace = Workspace(
        name=request.workspace_name,
        description=request.description,
        created_by_user_id=locked_user.id,
    )
    db.add(workspace)
    db.flush()
    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=locked_user.id,
        access_role="owner",
        research_role=request.research_role,
        active_context=request.context,
    )
    db.add(membership)
    locked_user.display_name = request.display_name
    db.commit()
    return require_current_membership(db, locked_user.id)


def update_current_workspace(
    db: Session, user: User, request: WorkspaceUpdateRequest
) -> WorkspaceMembership:
    membership = require_current_membership(db, user.id)
    provided = request.model_fields_set

    if "workspace_name" in provided or "description" in provided:
        if membership.access_role != "owner":
            raise AppError(403, "forbidden", "Only the workspace owner can change workspace details.")
        if "workspace_name" in provided and request.workspace_name is not None:
            membership.workspace.name = request.workspace_name
        if "description" in provided:
            membership.workspace.description = request.description
    if "display_name" in provided and request.display_name is not None:
        user.display_name = request.display_name
    if "research_role" in provided:
        membership.research_role = request.research_role
    if "active_context" in provided:
        if request.active_context is None:
            raise AppError(
                422,
                "validation_error",
                "Some fields need attention.",
                {"active_context": "Choose clinical or research."},
            )
        membership.active_context = request.active_context

    db.commit()
    return membership
