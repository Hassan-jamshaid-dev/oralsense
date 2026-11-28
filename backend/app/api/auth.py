from fastapi import APIRouter, Request, Response, status

from app.config import get_settings
from app.deps import SESSION_COOKIE_NAME, CurrentCsrf, CurrentUser, DbSession, get_session_token
from app.http_security import client_address
from app.schemas import LoginRequest, MeResponse, RegisterRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_flags() -> dict[str, object]:
    # __Host- is not used. Local HTTP would drop that Secure-only prefix, and the
    # cookie name is shared with deps.SESSION_COOKIE_NAME.
    return {
        "httponly": True,
        "secure": get_settings().session_cookie_secure,
        "samesite": "lax",
        "path": "/",
    }


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=get_settings().session_ttl_hours * 3600,
        **_cookie_flags(),
    )


def _clear_session_cookie(response: Response) -> None:
    # Attributes must match the cookie that was set or some browsers will keep it.
    response.delete_cookie(SESSION_COOKIE_NAME, **_cookie_flags())


@router.post("/register", response_model=MeResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response, db: DbSession) -> MeResponse:
    user, token, csrf_token = auth_service.register_user(
        db,
        payload.email,
        payload.password,
        client_address=client_address(request),
    )
    _set_session_cookie(response, token)
    return auth_service.build_me_response(db, user, csrf_token=csrf_token)


@router.post("/login", response_model=MeResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: DbSession) -> MeResponse:
    user, token, csrf_token = auth_service.login_user(
        db,
        payload.email,
        payload.password,
        incoming_token=get_session_token(request),
        client_address=client_address(request),
    )
    _set_session_cookie(response, token)
    return auth_service.build_me_response(db, user, csrf_token=csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DbSession) -> Response:
    auth_service.logout_session(db, get_session_token(request))
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response)
    return response


@router.get("/me", response_model=MeResponse)
def read_me(user: CurrentUser, csrf_token: CurrentCsrf, db: DbSession) -> MeResponse:
    return auth_service.build_me_response(db, user, csrf_token=csrf_token)
