import pytest

import base64

from app.config import get_settings
from app.deps import SESSION_COOKIE_NAME
from app.security import SCRYPT_DKLEN, SCRYPT_SALT_BYTES, hash_password, verify_password
from app.services.auth_service import LOGIN_FAILURE_LIMIT
from tests.conftest import PASSWORD, register, run_sql

EMAIL = "researcher@example.org"


def login(client, email: str = EMAIL, password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def assert_error(response, status_code: int, code: str) -> dict:
    assert response.status_code == status_code, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    return error


def test_register_creates_session_and_returns_me(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"user", "workspace", "membership", "csrf_token"}
    assert body["user"]["email"] == EMAIL
    assert body["user"]["display_name"] is None
    assert body["user"]["id"]
    assert body["workspace"] is None
    assert body["membership"] is None
    assert body["csrf_token"]

    cookie_header = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in cookie_header
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/" in cookie_header
    assert f"max-age={get_settings().session_ttl_hours * 3600}" in cookie_header

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == body


def test_register_stores_only_a_password_hash(client):
    register(client)

    [(password_hash,)] = run_sql("SELECT password_hash FROM users")
    assert PASSWORD not in password_hash
    assert password_hash.startswith("scrypt$")


def test_register_normalizes_email(client):
    response = register(client, email="  Researcher@Example.ORG  ")

    assert response.status_code == 201
    assert response.json()["user"]["email"] == EMAIL


@pytest.mark.parametrize("duplicate", [EMAIL, "RESEARCHER@example.org", "  researcher@EXAMPLE.org "])
def test_duplicate_email_is_rejected(client, duplicate):
    assert register(client).status_code == 201
    client.cookies.clear()

    error = assert_error(register(client, email=duplicate), 409, "email_taken")
    assert "email" in error["fields"]
    assert run_sql("SELECT count(*) FROM users") == [(1,)]


def test_short_password_is_rejected(client):
    error = assert_error(register(client, password="short"), 422, "validation_error")

    assert "password" in error["fields"]
    assert run_sql("SELECT count(*) FROM users") == [(0,)]


def test_invalid_email_is_rejected(client):
    error = assert_error(register(client, email="not-an-email"), 422, "validation_error")

    assert "email" in error["fields"]


def test_login_returns_me_and_new_session(client):
    register(client)
    client.cookies.clear()

    response = login(client, email="  RESEARCHER@example.org")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == EMAIL
    assert SESSION_COOKIE_NAME in response.cookies
    assert client.get("/api/auth/me").status_code == 200


def test_login_with_wrong_password_is_rejected(client):
    register(client)
    client.cookies.clear()

    error = assert_error(login(client, password="wrong-password-123"), 401, "invalid_credentials")
    assert error["message"] == "Email or password is incorrect."
    assert SESSION_COOKIE_NAME not in client.cookies


def test_login_with_unknown_email_is_rejected_identically(client):
    error = assert_error(login(client, email="nobody@example.org"), 401, "invalid_credentials")

    assert error["message"] == "Email or password is incorrect."


def test_login_is_blocked_after_repeated_failures(client):
    register(client)
    client.cookies.clear()
    for _ in range(LOGIN_FAILURE_LIMIT):
        assert_error(login(client, password="wrong-password-123"), 401, "invalid_credentials")

    # Even the correct password is refused while the email is blocked.
    assert_error(login(client), 429, "too_many_attempts")


def test_preregistration_failures_do_not_block_first_login(client):
    email = "new-researcher@example.org"
    for _ in range(LOGIN_FAILURE_LIMIT):
        assert_error(
            login(client, email=email, password="wrong-password-123"),
            401,
            "invalid_credentials",
        )

    assert register(client, email=email).status_code == 201
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.clear()

    assert login(client, email=email).status_code == 200


def test_duplicate_register_does_not_clear_login_lockout(client):
    register(client)
    client.cookies.clear()
    for _ in range(LOGIN_FAILURE_LIMIT):
        assert_error(login(client, password="wrong-password-123"), 401, "invalid_credentials")

    assert_error(register(client), 409, "email_taken")
    assert_error(login(client), 429, "too_many_attempts")


def test_malformed_stored_password_hash_is_invalid_credentials(client):
    register(client)
    client.cookies.clear()
    run_sql("UPDATE users SET password_hash = 'not-a-hash'")

    response = login(client)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"
    assert "not-a-hash" not in response.text


def test_verify_password_rejects_malformed_hashes(client):
    stored = hash_password(PASSWORD)
    assert verify_password(PASSWORD, stored) is True
    assert verify_password("wrong-password-123", stored) is False

    salt = base64.b64encode(b"\x01" * SCRYPT_SALT_BYTES).decode("ascii")
    digest = base64.b64encode(b"\x02" * SCRYPT_DKLEN).decode("ascii")
    malformed = (
        "",
        "not-a-hash",
        "md5$1$2$3$aa$bb",
        f"scrypt$16$8$1${salt}${digest}",
        f"scrypt$16384$8$1$!!!!${digest}",
        f"scrypt$16384$8$1${salt}$YQ==",
        f"scrypt$1073741824$8$1${salt}${digest}",
    )
    for stored_hash in malformed:
        assert verify_password(PASSWORD, stored_hash) is False


def test_logout_revokes_session_server_side(client):
    register(client)
    token = client.cookies[SESSION_COOKIE_NAME]

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert run_sql("SELECT count(*) FROM user_sessions") == [(0,)]
    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")
    # Replaying the old cookie must not work either.
    client.cookies.set(SESSION_COOKIE_NAME, token)
    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")


def test_logout_without_session_is_idempotent(client):
    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/logout").status_code == 204


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/auth/me", None),
        ("GET", "/api/dashboard/summary", None),
        ("POST", "/api/workspaces", {"workspace_name": "Lab", "display_name": "Dr. R", "context": "research"}),
        ("PATCH", "/api/workspaces/current", {"display_name": "Dr. R"}),
    ],
)
def test_protected_endpoints_require_a_session(client, method, path, payload):
    assert_error(client.request(method, path, json=payload), 401, "not_authenticated")


def test_unknown_session_token_is_rejected(client):
    client.cookies.set(SESSION_COOKIE_NAME, "forged-token")

    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")


def test_expired_session_is_rejected_and_removed(client):
    register(client)
    run_sql("UPDATE user_sessions SET expires_at = now() - interval '1 minute'")

    assert_error(client.get("/api/auth/me"), 401, "session_expired")
    assert run_sql("SELECT count(*) FROM user_sessions") == [(0,)]
    assert_error(client.get("/api/auth/me"), 401, "not_authenticated")
