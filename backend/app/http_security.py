import hmac
from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.deps import SESSION_COOKIE_NAME
from app.errors import AppError, database_unavailable, error_body

CSRF_HEADER_NAME = "X-OralSense-CSRF"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
PRE_SESSION_PATHS = frozenset({"/api/auth/login", "/api/auth/register"})

CORS_ALLOW_HEADERS = ["Accept", "Content-Type", CSRF_HEADER_NAME]
CORS_ALLOW_METHODS = ["GET", "POST", "PATCH", "DELETE"]

_SECURITY_HEADERS = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "same-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("X-Permitted-Cross-Domain-Policies", "none"),
    ("Cache-Control", "no-store"),
    # API-only CSP. Do not reuse this policy if FastAPI later serves the SPA.
    ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"),
)


class CsrfStoreUnavailable(Exception):
    """The session store could not be read while validating a mutating request."""


def client_address(request: Request) -> str:
    # Uses the peer address. X-Forwarded-For is only reflected here after
    # ProxyHeadersMiddleware rewrites the client, which requires TRUST_FORWARDING.
    return request.client.host if request.client else "unknown"


def reject_wildcard_cors_origins(origins: list[str]) -> list[str]:
    if any(origin == "*" for origin in origins):
        raise RuntimeError(
            "CORS_ORIGINS cannot include '*' because OralSense uses credentialed cookies."
        )
    return origins


def reject_wildcard_allowed_hosts(hosts: list[str], *, production: bool) -> list[str]:
    if not hosts:
        raise RuntimeError("ALLOWED_HOSTS must list at least one host.")
    if production and any(host == "*" for host in hosts):
        raise RuntimeError("ALLOWED_HOSTS cannot be '*' in production.")
    return hosts


def reject_wildcard_trusted_proxies(proxies: list[str], *, production: bool) -> list[str]:
    if production and any(proxy == "*" for proxy in proxies):
        raise RuntimeError("TRUSTED_PROXY_IPS cannot be '*' in production.")
    return proxies


def apply_security_headers(headers: MutableHeaders, *, production: bool) -> None:
    for name, value in _SECURITY_HEADERS:
        headers.setdefault(name, value)
    if production:
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


def normalize_origin(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() == "null":
        return None
    parsed = urlparse(stripped)
    if parsed.scheme not in ("http", "https"):
        return None
    if not parsed.netloc or parsed.username or parsed.password:
        return None
    if parsed.path not in ("", "/") or parsed.params or parsed.query or parsed.fragment:
        return None
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"


def request_origin(request: Request) -> str:
    return f"{request.url.scheme}://{request.url.netloc}"


def origin_is_trusted(
    origin_header: str | None, *, request_origin_value: str, cors_origins: list[str]
) -> bool:
    origin = normalize_origin(origin_header)
    if origin is None:
        return False
    allowed = {normalize_origin(item) for item in cors_origins}
    allowed.discard(None)
    allowed.add(normalize_origin(request_origin_value) or request_origin_value.lower())
    return origin in allowed


def csrf_tokens_match(presented: str | None, expected: str | None) -> bool:
    if presented is None or expected is None or not presented or not expected:
        return False
    return hmac.compare_digest(presented, expected)


def is_pre_session_path(path: str) -> bool:
    return path.rstrip("/") in PRE_SESSION_PATHS


def mutation_allowed(
    *,
    path: str,
    origin_header: str | None,
    request_origin_value: str,
    cors_origins: list[str],
    session_csrf: str | None,
    presented_csrf: str | None,
) -> bool:
    """Origin + per-session token policy for cookie-authenticated mutations.

    Login/register have no session yet: a trusted Origin is required. Origin-less,
    null, malformed, and untrusted Origins are rejected. Referer is not used.

    After a session exists: the request must present that session's CSRF token.
    A trusted Origin is also required when Origin is sent. If Origin is omitted
    entirely, a matching unguessable token is the documented fallback — Origin-less
    mutations are never allowed without that token.
    """
    trusted = origin_is_trusted(
        origin_header, request_origin_value=request_origin_value, cors_origins=cors_origins
    )
    if is_pre_session_path(path):
        return trusted

    if session_csrf is not None:
        if not csrf_tokens_match(presented_csrf, session_csrf):
            return False
        if origin_header is None:
            return True
        return trusted

    return trusted


def load_session_csrf_token(session_cookie: str | None) -> str | None:
    if not session_cookie:
        return None

    from app.db import get_session_factory
    from app.models import UserSession
    from app.security import hash_session_token

    try:
        session_factory = get_session_factory()
    except AppError as exc:
        raise CsrfStoreUnavailable from exc

    db = session_factory()
    try:
        token = db.scalar(
            select(UserSession.csrf_token).where(
                UserSession.token_hash == hash_session_token(session_cookie),
                UserSession.expires_at > datetime.now(UTC),
            )
        )
        return token or None
    except SQLAlchemyError as exc:
        raise CsrfStoreUnavailable from exc
    finally:
        db.close()


def _csrf_rejected_response() -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=error_body(
            "csrf_rejected",
            "This request is missing the required security header.",
        ),
    )


def _store_unavailable_response() -> JSONResponse:
    error = database_unavailable()
    return JSONResponse(status_code=error.status_code, content=error_body(error.code, error.message))


class BrowserSecurityMiddleware:
    """Origin + per-session CSRF for mutations, then stamps security headers.

    Implemented as raw ASGI so unhandled errors still reach the JSON error handlers.
    CSRF 403s go through the same header wrapper as other responses.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        async def send_with_security_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                apply_security_headers(headers, production=get_settings().is_production)
            await send(message)

        if request.method not in SAFE_METHODS:
            settings = get_settings()
            session_csrf: str | None = None
            if not is_pre_session_path(request.url.path):
                try:
                    session_csrf = load_session_csrf_token(request.cookies.get(SESSION_COOKIE_NAME))
                except CsrfStoreUnavailable:
                    await _store_unavailable_response()(scope, receive, send_with_security_headers)
                    return

            if not mutation_allowed(
                path=request.url.path,
                origin_header=request.headers.get("origin"),
                request_origin_value=request_origin(request),
                cors_origins=settings.cors_origin_list,
                session_csrf=session_csrf,
                presented_csrf=request.headers.get(CSRF_HEADER_NAME),
            ):
                await _csrf_rejected_response()(scope, receive, send_with_security_headers)
                return

        await self.app(scope, receive, send_with_security_headers)
