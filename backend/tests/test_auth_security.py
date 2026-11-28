import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.db import get_db
from app.deps import SESSION_COOKIE_NAME
from app.http_security import CSRF_HEADER_NAME
from app.main import app
from tests.conftest import PASSWORD, onboard, register, run_sql


def assert_error(response, status_code: int, code: str) -> dict:
    assert response.status_code == status_code, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    return error


def assert_no_secret_leak(response) -> None:
    body = response.text.lower()
    assert "traceback" not in body
    assert "postgresql" not in body
    assert "password_hash" not in body


def assert_security_headers(response) -> None:
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "no-store" in response.headers["Cache-Control"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


@pytest.fixture
def isolated_settings():
    yield
    get_settings.cache_clear()


def test_unauthenticated_requests_are_rejected(client):
    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")
    assert_error(client.get("/api/dashboard/summary"), 401, "not_authenticated")
    assert_error(
        client.post(
            "/api/workspaces",
            json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
        ),
        401,
        "not_authenticated",
    )
    assert_error(
        client.patch("/api/workspaces/current", json={"display_name": "Dr. R"}),
        401,
        "not_authenticated",
    )
    assert_no_secret_leak(client.get("/api/auth/me"))


def test_invalid_credentials_do_not_set_a_session(client):
    register(client)
    client.cookies.clear()

    error = assert_error(
        client.post("/api/auth/login", json={"email": "researcher@example.org", "password": "wrong-password-123"}),
        401,
        "invalid_credentials",
    )
    assert error["message"] == "Email or password is incorrect."
    assert SESSION_COOKIE_NAME not in client.cookies
    assert run_sql("SELECT count(*) FROM user_sessions") == [(1,)]


def test_logout_invalidates_cookie_and_database_row(client):
    register(client)
    token = client.cookies[SESSION_COOKIE_NAME]

    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    cookie_header = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in cookie_header
    assert "max-age=0" in cookie_header
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/" in cookie_header

    assert run_sql("SELECT count(*) FROM user_sessions") == [(0,)]
    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")
    client.cookies.set(SESSION_COOKIE_NAME, token)
    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")


def test_two_users_cannot_read_or_write_each_others_workspaces(client):
    register(client, "alpha@example.org")
    alpha = onboard(client, workspace_name="Alpha Lab", display_name="Dr. Alpha").json()
    alpha_token = client.cookies[SESSION_COOKIE_NAME]
    alpha_workspace = alpha["workspace"]["id"]

    client.cookies.clear()
    register(client, "beta@example.org")
    beta = onboard(client, workspace_name="Beta Lab", display_name="Dr. Beta").json()
    assert beta["workspace"]["id"] != alpha_workspace
    assert beta["workspace"]["name"] == "Beta Lab"

    dashboard = client.get("/api/dashboard/summary").json()
    assert dashboard["workspace"]["id"] == beta["workspace"]["id"]
    assert dashboard["workspace"]["name"] == "Beta Lab"
    assert all("Alpha Lab" not in item["title"] for item in dashboard["recent_activity"])

    hijack = client.patch(
        "/api/workspaces/current",
        json={"workspace_id": alpha_workspace, "workspace_name": "Hijacked"},
    )
    assert hijack.status_code == 422
    assert "workspace_id" in hijack.json()["error"]["fields"]

    ignored = client.get(f"/api/dashboard/summary?workspace_id={alpha_workspace}")
    assert ignored.status_code == 200
    assert ignored.json()["workspace"]["id"] == beta["workspace"]["id"]

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, alpha_token)
    alpha_me = client.get("/api/auth/me").json()
    assert alpha_me["user"]["email"] == "alpha@example.org"
    assert alpha_me["workspace"]["name"] == "Alpha Lab"
    assert client.get("/api/dashboard/summary").json()["workspace"]["id"] == alpha_workspace
    assert run_sql("SELECT name FROM workspaces ORDER BY name") == [("Alpha Lab",), ("Beta Lab",)]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        (
            "POST",
            "/api/workspaces",
            {
                "workspace_name": "Lab",
                "display_name": "Dr. R",
                "access_role": "owner",
                "workspace_id": str(uuid.uuid4()),
                "user_id": str(uuid.uuid4()),
            },
        ),
        (
            "PATCH",
            "/api/workspaces/current",
            {"access_role": "owner", "workspace_id": str(uuid.uuid4())},
        ),
    ],
)
def test_client_cannot_supply_role_or_workspace_id(client, method, path, payload):
    register(client)
    if method == "PATCH":
        onboard(client)

    response = client.request(method, path, json=payload)
    assert response.status_code == 422
    fields = response.json()["error"]["fields"]
    assert "access_role" in fields or "workspace_id" in fields
    if method == "POST":
        assert run_sql("SELECT count(*) FROM workspaces") == [(0,)]
    else:
        assert run_sql("SELECT access_role FROM workspace_memberships") == [("owner",)]


def test_login_rotates_the_presented_session(client):
    register(client)
    first = client.cookies[SESSION_COOKIE_NAME]

    response = client.post(
        "/api/auth/login",
        json={"email": "researcher@example.org", "password": PASSWORD},
    )
    assert response.status_code == 200
    second = client.cookies[SESSION_COOKIE_NAME]
    assert second != first
    assert run_sql("SELECT count(*) FROM user_sessions") == [(1,)]

    client.cookies.set(SESSION_COOKIE_NAME, first)
    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")


def test_register_does_not_revoke_another_users_session(client):
    register(client, "alpha@example.org")
    alpha_token = client.cookies[SESSION_COOKIE_NAME]
    client.cookies.clear()
    register(client, "beta@example.org")

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, alpha_token)
    assert client.get("/api/auth/me").json()["user"]["email"] == "alpha@example.org"


def test_tampered_session_token_is_rejected(client):
    register(client)
    token = client.cookies[SESSION_COOKIE_NAME]
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    client.cookies.set(SESSION_COOKIE_NAME, tampered)

    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")
    assert_no_secret_leak(client.get("/api/auth/me"))


def test_expired_session_is_rejected(client):
    register(client)
    run_sql("UPDATE user_sessions SET expires_at = now() - interval '1 minute'")
    assert_error(client.get("/api/auth/me"), 401, "session_expired")
    assert run_sql("SELECT count(*) FROM user_sessions") == [(0,)]


def test_unhandled_error_does_not_leak_internals(monkeypatch):
    leak_marker = "LEAK_MARKER_INTERNAL_DETAIL"

    def explode(*_args, **_kwargs):
        raise RuntimeError(leak_marker)

    monkeypatch.setattr("app.services.auth_service.get_user_for_session_token", explode)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        test_client.headers["Origin"] = get_settings().cors_origin_list[0]
        register(test_client)
        response = test_client.get("/api/auth/me")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["message"] == "Something went wrong on the server. Please try again."
    assert leak_marker not in response.text
    assert "traceback" not in response.text.lower()
    assert "postgresql" not in response.text.lower()


def test_database_failure_does_not_fail_open(client):
    register(client)

    def failing_db():
        raise OperationalError("SELECT 1", {}, Exception("unavailable"))
        yield

    app.dependency_overrides[get_db] = failing_db
    try:
        response = client.get("/api/auth/me")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"
        assert response.json()["error"]["message"] == "The database is unavailable."
        assert "postgresql" not in response.text.lower()
        assert "traceback" not in response.text.lower()
    finally:
        app.dependency_overrides.clear()


def test_login_rate_limit_rejects_further_attempts(client):
    from app.services.auth_service import LOGIN_FAILURE_LIMIT

    register(client)
    client.cookies.clear()
    for _ in range(LOGIN_FAILURE_LIMIT):
        assert_error(
            client.post(
                "/api/auth/login",
                json={"email": "researcher@example.org", "password": "wrong-password-123"},
            ),
            401,
            "invalid_credentials",
        )
    assert_error(
        client.post(
            "/api/auth/login",
            json={"email": "researcher@example.org", "password": PASSWORD},
        ),
        429,
        "too_many_attempts",
    )


def test_mutating_requests_without_origin_are_rejected(raw_client):
    response = raw_client.post(
        "/api/auth/login", json={"email": "nobody@example.org", "password": "x"}
    )
    assert_error(response, 403, "csrf_rejected")
    assert SESSION_COOKIE_NAME not in raw_client.cookies
    assert_security_headers(response)

    raw_client.headers[CSRF_HEADER_NAME] = "nope"
    assert_error(
        raw_client.post("/api/auth/login", json={"email": "nobody@example.org", "password": "x"}),
        403,
        "csrf_rejected",
    )


def test_trusted_origin_allows_login_without_session_csrf(raw_client):
    raw_client.headers["Origin"] = get_settings().cors_origin_list[0]
    response = raw_client.post(
        "/api/auth/login", json={"email": "nobody@example.org", "password": "x"}
    )
    assert_error(response, 401, "invalid_credentials")


def test_safe_methods_do_not_require_csrf_header(raw_client):
    assert raw_client.get("/api/health").status_code == 200
    assert_error(raw_client.get("/api/auth/me"), 401, "not_authenticated")


def test_api_responses_include_security_headers(client):
    response = client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "no-store" in response.headers["Cache-Control"]
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "strict-transport-security" not in response.headers


def test_production_forces_secure_cookie(client, monkeypatch, isolated_settings):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("ALLOW_REGISTRATION", "true")
    get_settings.cache_clear()

    response = register(client)
    assert response.status_code == 201
    cookie_header = response.headers["set-cookie"].lower()
    assert "secure" in cookie_header
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header


def test_production_disables_openapi_and_sets_hsts(monkeypatch, isolated_settings):
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as production_client:
        assert production_client.get("/docs").status_code == 404
        assert production_client.get("/redoc").status_code == 404
        assert production_client.get("/openapi.json").status_code == 404
        health = production_client.get("/api/health")
        assert health.status_code == 200
        assert "max-age=31536000" in health.headers["strict-transport-security"]


def test_wildcard_cors_is_rejected_at_startup(monkeypatch, isolated_settings):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    get_settings.cache_clear()

    from app.main import create_app

    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        create_app()


def test_session_token_is_stored_hashed(client):
    register(client)
    token = client.cookies[SESSION_COOKIE_NAME]
    [(token_hash,)] = run_sql("SELECT token_hash FROM user_sessions")
    assert token not in token_hash
    assert len(token_hash) == 64


def test_registration_disabled_is_enforced_server_side(client, monkeypatch, isolated_settings):
    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    get_settings.cache_clear()

    error = assert_error(register(client), 403, "registration_disabled")
    assert error["message"]
    assert run_sql("SELECT count(*) FROM users") == [(0,)]


# --- CSRF: trusted Origin + per-session token ---

MUTATING_ROUTES = (
    ("POST", "/api/auth/register", {"email": "followup@example.org", "password": PASSWORD}),
    ("POST", "/api/auth/login", {"email": "nobody@example.org", "password": "x"}),
    ("POST", "/api/auth/logout", None),
    ("POST", "/api/workspaces", {"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"}),
    ("PATCH", "/api/workspaces/current", {"display_name": "Dr. R"}),
)


def _trusted_origin() -> str:
    return get_settings().cors_origin_list[0]


@pytest.mark.parametrize(("method", "path", "payload"), MUTATING_ROUTES)
def test_missing_origin_rejected_on_every_mutating_route(raw_client, method, path, payload):
    response = raw_client.request(method, path, json=payload)
    assert_error(response, 403, "csrf_rejected")
    assert_security_headers(response)
    assert SESSION_COOKIE_NAME not in raw_client.cookies
    assert run_sql("SELECT count(*) FROM users") == [(0,)]
    assert run_sql("SELECT count(*) FROM user_sessions") == [(0,)]
    assert run_sql("SELECT count(*) FROM workspaces") == [(0,)]


@pytest.mark.parametrize(("method", "path", "payload"), MUTATING_ROUTES)
def test_untrusted_origin_rejected_on_every_mutating_route(raw_client, method, path, payload):
    response = raw_client.request(
        method, path, json=payload, headers={"Origin": "https://evil.example"}
    )
    assert_error(response, 403, "csrf_rejected")
    assert_security_headers(response)
    assert "access-control-allow-origin" not in response.headers
    assert run_sql("SELECT count(*) FROM users") == [(0,)]


@pytest.mark.parametrize(("method", "path", "payload"), MUTATING_ROUTES)
def test_null_origin_rejected_on_every_mutating_route(raw_client, method, path, payload):
    response = raw_client.request(method, path, json=payload, headers={"Origin": "null"})
    assert_error(response, 403, "csrf_rejected")
    assert_security_headers(response)
    assert run_sql("SELECT count(*) FROM users") == [(0,)]


@pytest.mark.parametrize(
    "origin",
    ["", "not-a-url", "ftp://localhost:5173", "http://evil.example/path", "http://"],
)
def test_malformed_origin_is_rejected(raw_client, origin):
    response = raw_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.org", "password": "x"},
        headers={"Origin": origin},
    )
    assert_error(response, 403, "csrf_rejected")
    assert_security_headers(response)


def test_referer_does_not_replace_origin(raw_client):
    allowed = _trusted_origin()
    for headers in (
        {"Referer": f"{allowed}/sign-in"},
        {"Referer": "https://evil.example/attack"},
    ):
        response = raw_client.post(
            "/api/auth/login",
            json={"email": "nobody@example.org", "password": "x"},
            headers=headers,
        )
        assert_error(response, 403, "csrf_rejected")


def test_static_csrf_header_is_not_sufficient(raw_client):
    raw_client.headers[CSRF_HEADER_NAME] = "1"
    assert_error(
        raw_client.post("/api/auth/login", json={"email": "nobody@example.org", "password": "x"}),
        403,
        "csrf_rejected",
    )
    response = raw_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.org", "password": "x"},
        headers={"Origin": "https://evil.example"},
    )
    assert_error(response, 403, "csrf_rejected")


def test_login_and_register_accept_trusted_origin_without_csrf_token(raw_client):
    origin = _trusted_origin()
    login = raw_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.org", "password": "x"},
        headers={"Origin": origin},
    )
    assert_error(login, 401, "invalid_credentials")

    created = raw_client.post(
        "/api/auth/register",
        json={"email": "frontend-like@example.org", "password": PASSWORD},
        headers={"Origin": origin},
    )
    assert created.status_code == 201
    assert created.json()["csrf_token"]


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
@pytest.mark.parametrize("static_header", [False, True])
def test_vite_origins_do_not_require_static_csrf_header(raw_client, origin, static_header):
    headers = {"Origin": origin}
    if static_header:
        headers[CSRF_HEADER_NAME] = "1"
    login = raw_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.org", "password": "x"},
        headers=headers,
    )
    assert_error(login, 401, "invalid_credentials")

    slug = origin.removeprefix("http://").replace(".", "-").replace(":", "-")
    created = raw_client.post(
        "/api/auth/register",
        json={
            "email": f"{slug}-{'static' if static_header else 'plain'}@example.org",
            "password": PASSWORD,
        },
        headers=headers,
    )
    assert created.status_code == 201
    assert created.status_code != 403


def test_same_host_origin_is_trusted_for_login(raw_client):
    response = raw_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.org", "password": "x"},
        headers={"Origin": "http://testserver"},
    )
    assert_error(response, 401, "invalid_credentials")


def test_authenticated_mutations_require_session_csrf_token(raw_client):
    origin = _trusted_origin()
    created = raw_client.post(
        "/api/auth/register",
        json={"email": "csrf@example.org", "password": PASSWORD},
        headers={"Origin": origin},
    )
    assert created.status_code == 201
    token = created.json()["csrf_token"]

    missing = raw_client.post(
        "/api/workspaces",
        json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
        headers={"Origin": origin},
    )
    assert_error(missing, 403, "csrf_rejected")
    assert_security_headers(missing)
    assert run_sql("SELECT count(*) FROM workspaces") == [(0,)]

    for value in ("", "0", "true", "1", "1 ", token[:-1] + ("A" if token[-1] != "A" else "B")):
        rejected = raw_client.post(
            "/api/workspaces",
            json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
            headers={"Origin": origin, CSRF_HEADER_NAME: value},
        )
        assert_error(rejected, 403, "csrf_rejected")
    assert run_sql("SELECT count(*) FROM workspaces") == [(0,)]

    assert_error(
        raw_client.patch(
            "/api/workspaces/current",
            json={"display_name": "Dr. R"},
            headers={"Origin": origin},
        ),
        403,
        "csrf_rejected",
    )
    assert_error(raw_client.post("/api/auth/logout", headers={"Origin": origin}), 403, "csrf_rejected")
    assert run_sql("SELECT count(*) FROM user_sessions") == [(1,)]


def test_authenticated_mutations_accept_trusted_origin_and_session_token(raw_client):
    origin = _trusted_origin()
    created = raw_client.post(
        "/api/auth/register",
        json={"email": "ok@example.org", "password": PASSWORD},
        headers={"Origin": origin},
    )
    token = created.json()["csrf_token"]
    csrf = {CSRF_HEADER_NAME: token, "Origin": origin}

    workspace = raw_client.post(
        "/api/workspaces",
        json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
        headers=csrf,
    )
    assert workspace.status_code == 201
    assert workspace.json()["csrf_token"] == token

    patched = raw_client.patch(
        "/api/workspaces/current", json={"display_name": "Dr. Renamed"}, headers=csrf
    )
    assert patched.status_code == 200
    assert patched.json()["user"]["display_name"] == "Dr. Renamed"

    assert raw_client.post("/api/auth/logout", headers=csrf).status_code == 204
    assert run_sql("SELECT count(*) FROM user_sessions") == [(0,)]


def test_origin_less_authenticated_mutation_allowed_only_with_valid_token(raw_client):
    origin = _trusted_origin()
    created = raw_client.post(
        "/api/auth/register",
        json={"email": "no-origin@example.org", "password": PASSWORD},
        headers={"Origin": origin},
    )
    token = created.json()["csrf_token"]

    assert_error(
        raw_client.post(
            "/api/workspaces",
            json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
        ),
        403,
        "csrf_rejected",
    )
    allowed = raw_client.post(
        "/api/workspaces",
        json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
        headers={CSRF_HEADER_NAME: token},
    )
    assert allowed.status_code == 201


def test_null_origin_rejected_even_with_valid_csrf_token(raw_client):
    origin = _trusted_origin()
    created = raw_client.post(
        "/api/auth/register",
        json={"email": "null-origin@example.org", "password": PASSWORD},
        headers={"Origin": origin},
    )
    token = created.json()["csrf_token"]
    response = raw_client.post(
        "/api/workspaces",
        json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
        headers={"Origin": "null", CSRF_HEADER_NAME: token},
    )
    assert_error(response, 403, "csrf_rejected")
    assert run_sql("SELECT count(*) FROM workspaces") == [(0,)]


def test_untrusted_origin_rejected_even_with_valid_csrf_token(raw_client):
    origin = _trusted_origin()
    created = raw_client.post(
        "/api/auth/register",
        json={"email": "evil-origin@example.org", "password": PASSWORD},
        headers={"Origin": origin},
    )
    token = created.json()["csrf_token"]
    response = raw_client.post(
        "/api/workspaces",
        json={"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"},
        headers={"Origin": "https://evil.example", CSRF_HEADER_NAME: token},
    )
    assert_error(response, 403, "csrf_rejected")
    assert run_sql("SELECT count(*) FROM workspaces") == [(0,)]


def test_csrf_rejection_includes_security_headers(raw_client):
    response = raw_client.post("/api/auth/logout")
    assert_error(response, 403, "csrf_rejected")
    assert_security_headers(response)


def test_me_returns_the_session_csrf_token(client):
    created = register(client)
    token = created.json()["csrf_token"]
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["csrf_token"] == token
    [(stored,)] = run_sql("SELECT csrf_token FROM user_sessions")
    assert stored == token
    assert token != client.cookies[SESSION_COOKIE_NAME]


def test_cors_allows_configured_origin_and_rejects_unknown_origin(raw_client):
    allowed = get_settings().cors_origin_list[0]
    allowed_response = raw_client.get("/api/health", headers={"Origin": allowed})
    assert allowed_response.status_code == 200
    assert allowed_response.headers.get("access-control-allow-origin") == allowed
    assert allowed_response.headers.get("access-control-allow-credentials") == "true"

    blocked = raw_client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert blocked.status_code == 200
    assert "access-control-allow-origin" not in blocked.headers


def test_cors_preflight_unknown_origin_is_not_allowed(raw_client):
    response = raw_client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": CSRF_HEADER_NAME,
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allowed_origin_permits_csrf_header(raw_client):
    allowed = get_settings().cors_origin_list[0]
    response = raw_client.options(
        "/api/auth/login",
        headers={
            "Origin": allowed,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": CSRF_HEADER_NAME,
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed
    assert CSRF_HEADER_NAME.lower() in response.headers.get("access-control-allow-headers", "").lower()


def test_production_logout_clears_cookie_with_secure_and_matching_flags(
    client, monkeypatch, isolated_settings
):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.setenv("ALLOW_REGISTRATION", "true")
    get_settings.cache_clear()

    created = register(client)
    assert created.status_code == 201
    token = created.cookies[SESSION_COOKIE_NAME]
    assert "secure" in created.headers["set-cookie"].lower()

    # TestClient is HTTP, so it may omit a Secure cookie from the jar. Present it
    # explicitly; production browsers only attach this cookie on HTTPS.
    response = client.post("/api/auth/logout", cookies={SESSION_COOKIE_NAME: token})
    assert response.status_code == 204
    cookie_header = response.headers["set-cookie"].lower()
    assert "secure" in cookie_header
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/" in cookie_header
    assert "max-age=0" in cookie_header
    assert run_sql("SELECT count(*) FROM user_sessions") == [(0,)]


def test_login_does_not_adopt_an_unknown_presented_cookie(client):
    register(client)
    client.cookies.clear()

    response = client.post(
        "/api/auth/login",
        json={"email": "researcher@example.org", "password": PASSWORD},
        cookies={SESSION_COOKIE_NAME: "attacker-chosen-token"},
    )
    assert response.status_code == 200
    issued = response.cookies[SESSION_COOKIE_NAME]
    assert issued != "attacker-chosen-token"
    assert client.get("/api/auth/me", cookies={SESSION_COOKIE_NAME: issued}).status_code == 200
    assert_error(
        client.get("/api/auth/me", cookies={SESSION_COOKIE_NAME: "attacker-chosen-token"}),
        401,
        "not_authenticated",
    )


def test_logout_does_not_revoke_another_users_session(client):
    register(client, "alpha@example.org")
    alpha_token = client.cookies[SESSION_COOKIE_NAME]
    client.cookies.clear()
    register(client, "beta@example.org")

    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.set(SESSION_COOKIE_NAME, alpha_token)
    assert client.get("/api/auth/me").json()["user"]["email"] == "alpha@example.org"
    assert run_sql("SELECT count(*) FROM user_sessions") == [(1,)]


def test_two_users_isolated_on_every_existing_tenant_endpoint(client):
    register(client, "alpha@example.org")
    alpha = onboard(client, workspace_name="Alpha Lab", display_name="Dr. Alpha").json()
    alpha_token = client.cookies[SESSION_COOKIE_NAME]
    alpha_workspace = alpha["workspace"]["id"]

    client.cookies.clear()
    register(client, "beta@example.org")
    beta = onboard(client, workspace_name="Beta Lab", display_name="Dr. Beta").json()
    beta_workspace = beta["workspace"]["id"]
    assert beta_workspace != alpha_workspace

    me = client.get("/api/auth/me").json()
    assert me["user"]["email"] == "beta@example.org"
    assert me["workspace"]["id"] == beta_workspace

    dashboard = client.get("/api/dashboard/summary").json()
    assert dashboard["workspace"]["id"] == beta_workspace
    assert dashboard["workspace"]["name"] == "Beta Lab"

    create_again = client.post(
        "/api/workspaces",
        json={"workspace_name": "Should Not Exist", "display_name": "Dr. Beta", "context": "research"},
    )
    assert create_again.status_code == 409
    assert create_again.json()["error"]["code"] == "workspace_exists"

    patched = client.patch("/api/workspaces/current", json={"workspace_name": "Beta Renamed"})
    assert patched.status_code == 200
    assert patched.json()["workspace"]["name"] == "Beta Renamed"
    assert patched.json()["workspace"]["id"] == beta_workspace

    assert run_sql("SELECT name FROM workspaces WHERE id = CAST(:id AS uuid)", id=alpha_workspace) == [
        ("Alpha Lab",)
    ]

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, alpha_token)
    alpha_me = client.get("/api/auth/me").json()
    assert alpha_me["user"]["email"] == "alpha@example.org"
    assert alpha_me["workspace"]["id"] == alpha_workspace
    assert alpha_me["workspace"]["name"] == "Alpha Lab"
    assert client.get("/api/dashboard/summary").json()["workspace"]["id"] == alpha_workspace


def test_login_unknown_email_and_wrong_password_are_identical(client):
    register(client)
    client.cookies.clear()
    unknown = client.post(
        "/api/auth/login", json={"email": "nobody@example.org", "password": "wrong-password-123"}
    )
    wrong = client.post(
        "/api/auth/login", json={"email": "researcher@example.org", "password": "wrong-password-123"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()
    assert unknown.json()["error"]["code"] == "invalid_credentials"


def test_get_logout_does_not_mutate_state(client):
    register(client)
    response = client.get("/api/auth/logout")
    assert response.status_code == 405
    assert run_sql("SELECT count(*) FROM user_sessions") == [(1,)]
    assert client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/api/assessments",
        "/api/workspaces/not-current",
    ],
)
def test_planned_resource_routes_are_not_implemented(client, path):
    assert client.get(path).status_code == 404
    assert client.post(path, json={}).status_code == 404


@pytest.mark.parametrize("path", ["/api/studies", "/api/protocols"])
def test_batch4_collection_routes_require_a_session(client, path):
    assert client.get(path).status_code == 401
    assert client.post(path, json={}).status_code == 401
