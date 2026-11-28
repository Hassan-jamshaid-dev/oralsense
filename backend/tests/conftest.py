import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, make_url, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings

TEST_DATABASE_NAME = "oralsense_test"
BACKEND_DIR = Path(__file__).resolve().parent.parent


def _derive_test_database_url() -> str | None:
    url = Settings().database_url
    if not url or "CHANGE_ME" in url:
        return None
    return make_url(url).set(database=TEST_DATABASE_NAME).render_as_string(hide_password=False)


TEST_DATABASE_URL = _derive_test_database_url()
if TEST_DATABASE_URL:
    # Environment variables take precedence over backend/.env, so the app under test
    # never touches the development database.
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _database_unreachable_reason() -> str | None:
    if not TEST_DATABASE_URL:
        return "DATABASE_URL in backend/.env is missing or still uses the CHANGE_ME placeholder."
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return f"Test database '{TEST_DATABASE_NAME}' is unreachable ({type(exc).__name__})."
    finally:
        engine.dispose()
    return None


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    reason = _database_unreachable_reason()
    if reason:
        pytest.skip(reason)

    from alembic import command
    from alembic.config import Config

    from app.config import get_settings
    from app.db import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["database_url"] = TEST_DATABASE_URL
    command.upgrade(config, "head")
    yield
    get_engine().dispose()


@pytest.fixture(autouse=True)
def clean_tables(migrated_database: None) -> Iterator[None]:
    from app.db import get_engine
    from app.services.auth_service import login_ip_limiter, login_limiter, register_ip_limiter
    from app.services.quality_control_service import (
        quality_review_ip_limiter,
        quality_review_user_limiter,
    )

    with get_engine().begin() as connection:
        connection.execute(
            text(
                "TRUNCATE quality_reviews, study_participants, protocol_versions, assessment_trials, "
                "assessment_sessions, visits, studies, protocols, participants, "
                "user_sessions, workspace_memberships, workspaces, users CASCADE"
            )
        )
    login_limiter.clear()
    login_ip_limiter.clear()
    register_ip_limiter.clear()
    quality_review_user_limiter.clear()
    quality_review_ip_limiter.clear()
    yield


class ApiClient(TestClient):
    """Frontend-like client: trusted Origin, and CSRF header taken from Me responses."""

    def request(self, method, url, **kwargs):  # noqa: ANN001
        response = super().request(method, url, **kwargs)
        if response.status_code in {200, 201} and "application/json" in response.headers.get(
            "content-type", ""
        ):
            try:
                body = response.json()
            except ValueError:
                return response
            token = body.get("csrf_token") if isinstance(body, dict) else None
            if isinstance(token, str) and token:
                from app.http_security import CSRF_HEADER_NAME

                self.headers[CSRF_HEADER_NAME] = token
        return response


@pytest.fixture
def client():
    from app.config import get_settings
    from app.main import app

    with ApiClient(app) as test_client:
        test_client.headers["Origin"] = get_settings().cors_origin_list[0]
        yield test_client


@pytest.fixture
def raw_client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


PASSWORD = "correct-horse-battery"


def run_sql(statement: str, **params) -> list:
    """Read or tamper with rows directly, bypassing the API under test."""
    from app.db import get_engine

    with get_engine().begin() as connection:
        result = connection.execute(text(statement), params)
        return result.all() if result.returns_rows else []


def register(client, email: str = "researcher@example.org", password: str = PASSWORD):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def onboard(client, **overrides):
    payload = {
        "workspace_name": "Oral Sensory Lab",
        "description": "Tactile threshold pilot",
        "display_name": "Dr. Researcher",
        "research_role": "researcher",
        "context": "research",
    }
    payload.update(overrides)
    return client.post("/api/workspaces", json=payload)
