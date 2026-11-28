import uuid

import pytest

from app.services.participant_service import MAX_PAGE_SIZE
from tests.conftest import onboard, register, run_sql


def assert_error(response, status_code: int, code: str) -> dict:
    assert response.status_code == status_code, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert error["message"]
    return error


def create_participant(client, display_label: str | None = None, **extra):
    payload: dict = {}
    if display_label is not None:
        payload["display_label"] = display_label
    payload.update(extra)
    return client.post("/api/participants", json=payload)


def sign_in_workspace(client, email: str, workspace_name: str) -> None:
    client.cookies.clear()
    registered = register(client, email=email)
    assert registered.status_code == 201, registered.text
    onboarded = onboard(client, workspace_name=workspace_name, display_name="Dr. Researcher")
    assert onboarded.status_code == 201, onboarded.text


@pytest.mark.parametrize("reference_code", ["   ", "A", "A" * 33, "P-01"])
def test_client_supplied_reference_code_is_rejected(client, reference_code):
    sign_in_workspace(client, "researcher@example.org", "Oral Sensory Lab")

    response = create_participant(client, reference_code=reference_code)

    error = assert_error(response, 422, "validation_error")
    assert "reference_code" in error["fields"]
    assert run_sql("SELECT count(*) FROM participants") == [(0,)]


def test_same_code_is_allowed_in_another_workspace_only(client):
    sign_in_workspace(client, "alpha@example.org", "Alpha Lab")
    first = create_participant(client, display_label="Alpha")
    assert first.status_code == 201, first.text
    code = first.json()["reference_code"]

    sign_in_workspace(client, "beta@example.org", "Beta Lab")
    second = create_participant(client, display_label="Beta")
    assert second.status_code == 201, second.text
    run_sql(
        "UPDATE participants SET reference_code = :code WHERE id = :id",
        code=code,
        id=second.json()["id"],
    )
    assert run_sql("SELECT count(*) FROM participants WHERE reference_code = :code", code=code) == [(2,)]

    listed = client.get("/api/participants")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["reference_code"] == code


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"page": 0}, "page"),
        ({"page_size": 0}, "page_size"),
        ({"page_size": MAX_PAGE_SIZE + 1}, "page_size"),
        ({"sort": "email"}, "sort"),
    ],
)
def test_invalid_list_query_is_rejected(client, params, field):
    sign_in_workspace(client, "researcher@example.org", "Oral Sensory Lab")

    response = client.get("/api/participants", params=params)

    error = assert_error(response, 422, "validation_error")
    assert field in error["fields"]


def test_search_percent_and_quotes_does_not_error_or_leak(client):
    sign_in_workspace(client, "alpha@example.org", "Alpha Lab")
    leaked = create_participant(client, display_label='secret "alpha"')
    assert leaked.status_code == 201, leaked.text
    leaked_id = leaked.json()["id"]

    sign_in_workspace(client, "beta@example.org", "Beta Lab")
    assert create_participant(client, display_label="plain").status_code == 201
    quoted = create_participant(client, display_label="quoted 'beta'")
    assert quoted.status_code == 201, quoted.text
    run_sql(
        "UPDATE participants SET reference_code = :code WHERE id = :id",
        code="B%2",
        id=quoted.json()["id"],
    )

    percent = client.get("/api/participants", params={"q": "%"})
    assert percent.status_code == 200, percent.text
    assert percent.json()["total"] == 1
    assert [item["reference_code"] for item in percent.json()["items"]] == ["B%2"]
    assert leaked_id not in percent.text
    assert "secret" not in percent.text

    quote = client.get("/api/participants", params={"q": '"'})
    assert quote.status_code == 200, quote.text
    assert quote.json()["total"] == 0
    assert quote.json()["items"] == []
    assert leaked_id not in quote.text
    assert "secret" not in quote.text

    apostrophe = client.get("/api/participants", params={"q": "'"})
    assert apostrophe.status_code == 200, apostrophe.text
    assert apostrophe.json()["total"] == 1
    assert [item["reference_code"] for item in apostrophe.json()["items"]] == ["B%2"]
    assert leaked_id not in apostrophe.text
    assert "secret" not in apostrophe.text

    combined = client.get("/api/participants", params={"q": "%\"'"})
    assert combined.status_code == 200, combined.text
    assert combined.json()["total"] == 0
    assert leaked_id not in combined.text


def test_unknown_participant_uuid_is_not_found(client):
    sign_in_workspace(client, "researcher@example.org", "Oral Sensory Lab")

    response = client.get(f"/api/participants/{uuid.uuid4()}")

    assert_error(response, 404, "participant_not_found")


def test_two_creates_store_two_distinct_codes(client):
    sign_in_workspace(client, "researcher@example.org", "Oral Sensory Lab")

    first = create_participant(client)
    second = create_participant(client)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["reference_code"] != second.json()["reference_code"]
    assert run_sql("SELECT count(*) FROM participants") == [(2,)]


def test_dashboard_participant_count_matches_rows(client):
    sign_in_workspace(client, "researcher@example.org", "Oral Sensory Lab")
    for _ in range(3):
        created = create_participant(client)
        assert created.status_code == 201, created.text

    listed = client.get("/api/participants")
    assert listed.status_code == 200, listed.text
    [(row_count,)] = run_sql("SELECT count(*) FROM participants")

    summary = client.get("/api/dashboard/summary")
    assert summary.status_code == 200, summary.text
    metrics = {metric["key"]: metric for metric in summary.json()["metrics"]}

    assert metrics["participants"]["available"] is True
    assert metrics["participants"]["value"] == listed.json()["total"] == len(listed.json()["items"])
    assert metrics["participants"]["value"] == row_count == 3


def test_logout_then_list_participants_is_unauthorized(client):
    sign_in_workspace(client, "researcher@example.org", "Oral Sensory Lab")
    assert create_participant(client).status_code == 201

    assert client.post("/api/auth/logout").status_code == 204

    assert_error(client.get("/api/participants"), 401, "not_authenticated")
    assert run_sql("SELECT count(*) FROM participants") == [(1,)]
