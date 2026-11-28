from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.services import auth_service

SESSION_COOKIE_NAME = "oralsense_session"

DbSession = Annotated[Session, Depends(get_db)]


def get_session_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE_NAME)


def get_current_user(request: Request, db: DbSession) -> User:
    return auth_service.get_user_for_session_token(db, get_session_token(request))


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_csrf_token(user: CurrentUser, request: Request, db: DbSession) -> str:
    # CurrentUser runs first so an expired session is session_expired, not a CSRF 403.
    _ = user
    return auth_service.csrf_token_for_session(db, get_session_token(request))


CurrentCsrf = Annotated[str, Depends(get_current_csrf_token)]
