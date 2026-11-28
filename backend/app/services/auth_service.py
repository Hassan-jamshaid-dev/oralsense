import threading
import time
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AppError
from app.models import User, UserSession
from app.schemas import MembershipOut, MeResponse, UserOut, WorkspaceOut
from app.security import (
    DUMMY_PASSWORD_HASH,
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.services.workspace_service import get_current_membership

LOGIN_FAILURE_LIMIT = 10
LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60


class LoginFailureLimiter:
    """Counts failed logins per email in a sliding window.

    State lives in this process only: it resets on restart and is not shared between
    multiple server processes. Adequate for a single-process prototype, not for production.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self._limit = limit
        self._window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, email: str, now: float) -> deque[float]:
        failures = self._failures.setdefault(email, deque())
        while failures and now - failures[0] > self._window_seconds:
            failures.popleft()
        return failures

    def is_blocked(self, email: str) -> bool:
        with self._lock:
            return len(self._prune(email, time.monotonic())) >= self._limit

    def record(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def record_failure(self, email: str) -> None:
        self.record(email)

    def reset(self, email: str) -> None:
        with self._lock:
            self._failures.pop(email, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginFailureLimiter(LOGIN_FAILURE_LIMIT, LOGIN_FAILURE_WINDOW_SECONDS)
# Separate counters so a guessed email from one address cannot hide behind NAT-shared IPs,
# and so one IP cannot spray many emails. Still process-local; see the class docstring.
login_ip_limiter = LoginFailureLimiter(20, LOGIN_FAILURE_WINDOW_SECONDS)
register_ip_limiter = LoginFailureLimiter(10, LOGIN_FAILURE_WINDOW_SECONDS)


def _invalid_credentials() -> AppError:
    return AppError(401, "invalid_credentials", "Email or password is incorrect.")


def _create_session(db: Session, user: User) -> tuple[str, str]:
    token = generate_session_token()
    csrf_token = generate_csrf_token()
    expires_at = datetime.now(UTC) + timedelta(hours=get_settings().session_ttl_hours)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
    )
    return token, csrf_token


def register_user(
    db: Session, email: str, password: str, *, client_address: str = "unknown"
) -> tuple[User, str, str]:
    if not get_settings().registration_allowed:
        raise AppError(403, "registration_disabled", "Account creation is disabled on this server.")
    if register_ip_limiter.is_blocked(client_address):
        raise AppError(
            429,
            "too_many_attempts",
            "Too many account creation attempts. Wait 15 minutes and try again.",
        )
    register_ip_limiter.record(client_address)

    # Intentional registration enumeration: the create-account screen branches on email_taken.
    email_taken = AppError(
        409,
        "email_taken",
        "An account with this email already exists. Sign in instead.",
        {"email": "An account with this email already exists."},
    )
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise email_taken

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    try:
        db.flush()
        token, csrf_token = _create_session(db, user)
        db.commit()
    except IntegrityError as exc:
        # A concurrent registration for the same email won the race.
        db.rollback()
        raise email_taken from exc
    # Failures recorded before this account existed must not block the first sign-in.
    login_limiter.reset(email)
    return user, token, csrf_token


def _revoke_own_session(db: Session, user_id: uuid.UUID, token: str | None) -> None:
    if not token:
        return
    db.execute(
        delete(UserSession).where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.user_id == user_id,
        )
    )


def login_user(
    db: Session,
    email: str,
    password: str,
    *,
    incoming_token: str | None = None,
    client_address: str = "unknown",
) -> tuple[User, str, str]:
    if login_ip_limiter.is_blocked(client_address) or login_limiter.is_blocked(email):
        raise AppError(
            429,
            "too_many_attempts",
            "Too many failed sign-in attempts. Wait 15 minutes and try again.",
        )

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        login_limiter.record_failure(email)
        login_ip_limiter.record_failure(client_address)
        raise _invalid_credentials()
    if not verify_password(password, user.password_hash):
        login_limiter.record_failure(email)
        login_ip_limiter.record_failure(client_address)
        raise _invalid_credentials()

    login_limiter.reset(email)
    login_ip_limiter.reset(client_address)
    _revoke_own_session(db, user.id, incoming_token)
    db.execute(
        delete(UserSession).where(
            UserSession.user_id == user.id, UserSession.expires_at <= datetime.now(UTC)
        )
    )
    token, csrf_token = _create_session(db, user)
    db.commit()
    return user, token, csrf_token


def get_user_for_session_token(db: Session, token: str | None) -> User:
    not_authenticated = AppError(401, "not_authenticated", "Sign in to continue.")
    if not token:
        raise not_authenticated

    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_session_token(token)))
    if session is None:
        raise not_authenticated
    if session.expires_at <= datetime.now(UTC):
        db.delete(session)
        db.commit()
        raise AppError(401, "session_expired", "Your session has expired. Sign in again.")

    user = db.get(User, session.user_id)
    if user is None:
        raise not_authenticated
    return user


def logout_session(db: Session, token: str | None) -> None:
    if not token:
        return
    db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(token)))
    db.commit()


def csrf_token_for_session(db: Session, token: str | None) -> str:
    if not token:
        raise AppError(401, "not_authenticated", "Sign in to continue.")
    csrf_token = db.scalar(
        select(UserSession.csrf_token).where(UserSession.token_hash == hash_session_token(token))
    )
    if not csrf_token:
        raise AppError(401, "not_authenticated", "Sign in to continue.")
    return csrf_token


def build_me_response(db: Session, user: User, *, csrf_token: str) -> MeResponse:
    membership = get_current_membership(db, user.id)
    return MeResponse(
        user=UserOut.model_validate(user),
        workspace=WorkspaceOut.model_validate(membership.workspace) if membership else None,
        membership=MembershipOut.model_validate(membership) if membership else None,
        csrf_token=csrf_token,
    )
