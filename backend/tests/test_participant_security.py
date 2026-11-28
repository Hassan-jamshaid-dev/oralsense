import uuid

from app.config import get_settings
from app.deps import SESSION_COOKIE_NAME
from app.http_security import CSRF_HEADER_NAME
from tests.conftest import PASSWORD, onboard, register, run_sql


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


def test_unauthenticated_participant_routes_are_rejected(client):
    participant_id = uuid.uuid4()
    assert_error(client.get("/api/participants"), 401, "not_authenticated")
    assert_error(client.get(f"/api/participants/{participant_id}"), 401, "not_authenticated")
    assert_error(
        client.post("/api/participants", json={"reference_code": "P-01"}),
        401,
        "not_authenticated",
    )
    assert run_sql("SELECT count(*) FROM participants") == [(0,)]


def test_other_workspace_participant_is_not_found(client):
    register(client, "alpha@example.org")
    alpha = onboard(client, workspace_name="Alpha Lab", display_name="Dr. Alpha").json()
    created = create_participant(client, display_label="Alpha only")
    assert created.status_code == 201, created.text
    participant_id = created.json()["id"]
    code = created.json()["reference_code"]
    alpha_token = client.cookies.get(SESSION_COOKIE_NAME)

    client.cookies.clear()
    register(client, "beta@example.org")
    onboard(client, workspace_name="Beta Lab", display_name="Dr. Beta")

    missing = client.get(f"/api/participants/{participant_id}")
    assert_error(missing, 404, "participant_not_found")
    assert code not in missing.text
    assert "Alpha only" not in missing.text
    assert alpha["workspace"]["id"] not in missing.text

    listed = client.get("/api/participants", params={"q": "ALPHA", "workspace_id": alpha["workspace"]["id"]})
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 0
    assert body["items"] == []

    hijack = client.post(
        "/api/participants",
        json={"reference_code": "BETA-1", "workspace_id": alpha["workspace"]["id"]},
    )
    assert hijack.status_code == 422
    assert "workspace_id" in hijack.json()["error"]["fields"]
    assert run_sql(
        "SELECT count(*) FROM participants WHERE workspace_id = CAST(:id AS uuid)",
        id=alpha["workspace"]["id"],
    ) == [(1,)]
    assert run_sql("SELECT reference_code FROM participants ORDER BY reference_code") == [(code,)]

    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE_NAME, alpha_token)
    own = client.get(f"/api/participants/{participant_id}")
    assert own.status_code == 200
    assert own.json()["reference_code"] == code


def test_generated_codes_differ_and_labels_are_trimmed(client):
    register(client, "alpha@example.org")
    onboard(client, workspace_name="Alpha Lab", display_name="Dr. Alpha")

    first = create_participant(client, display_label="  Lingual  ")
    assert first.status_code == 201, first.text
    assert first.json()["reference_code"].startswith("RS-")
    assert first.json()["display_label"] == "Lingual"
    assert first.json()["context"] == "research"
    assert first.json()["created_at"]
    assert first.json()["updated_at"]

    second = create_participant(client)
    assert second.status_code == 201, second.text
    assert second.json()["reference_code"] != first.json()["reference_code"]
    assert run_sql("SELECT count(*) FROM participants") == [(2,)]

    client.cookies.clear()
    register(client, "beta@example.org")
    onboard(client, workspace_name="Beta Lab", display_name="Dr. Beta")
    other = create_participant(client)
    assert other.status_code == 201, other.text
    run_sql(
        "UPDATE participants SET reference_code = :code WHERE id = :id",
        code=first.json()["reference_code"],
        id=other.json()["id"],
    )
    assert run_sql("SELECT count(*) FROM participants") == [(3,)]


def test_post_participant_rejects_missing_or_wrong_csrf(raw_client):
    origin = get_settings().cors_origin_list[0]
    created = raw_client.post(
        "/api/auth/register",
        json={"email": "participant-csrf@example.org", "password": PASSWORD},
        headers={"Origin": origin},
    )
    assert created.status_code == 201
    token = created.json()["csrf_token"]
    csrf = {CSRF_HEADER_NAME: token, "Origin": origin}
    onboarded = raw_client.post(
        "/api/workspaces",
        json={
            "workspace_name": "Oral Sensory Lab",
            "display_name": "Dr. Researcher",
            "context": "research",
        },
        headers=csrf,
    )
    assert onboarded.status_code == 201

    missing = raw_client.post(
        "/api/participants",
        json={},
        headers={"Origin": origin},
    )
    assert_error(missing, 403, "csrf_rejected")

    wrong = raw_client.post(
        "/api/participants",
        json={},
        headers={CSRF_HEADER_NAME: "not-the-session-token", "Origin": origin},
    )
    assert_error(wrong, 403, "csrf_rejected")
    assert run_sql("SELECT count(*) FROM participants") == [(0,)]

    accepted = raw_client.post(
        "/api/participants",
        json={},
        headers=csrf,
    )
    assert accepted.status_code == 201
    assert accepted.json()["reference_code"].startswith("RS-")


def test_search_query_is_not_executed_as_sql(client):
    register(client)
    onboard(client)
    first = create_participant(client, display_label="Lingual pilot")
    second = create_participant(client)
    assert first.status_code == 201
    assert second.status_code == 201
    run_sql(
        "UPDATE participants SET reference_code = :code WHERE id = :id",
        code="P-01",
        id=first.json()["id"],
    )
    run_sql(
        "UPDATE participants SET reference_code = :code WHERE id = :id",
        code="A%B",
        id=second.json()["id"],
    )

    for term in ("' OR 1=1 --", "'; DROP TABLE participants; --", "%", "_", "\\", "P-01' OR '1'='1"):
        response = client.get("/api/participants", params={"q": term})
        assert response.status_code == 200, response.text

    assert client.get("/api/participants", params={"q": "%"}).json()["total"] == 1
    assert client.get("/api/participants", params={"q": "%"}).json()["items"][0]["reference_code"] == "A%B"
    assert client.get("/api/participants", params={"q": "P-01"}).json()["total"] == 1
    assert client.get("/api/participants").json()["total"] == 2

    dropped = client.get("/api/participants", params={"sort": "reference_code; DROP TABLE participants"})
    assert dropped.status_code == 422
    oversized = client.get("/api/participants", params={"page_size": 10_000})
    assert oversized.status_code == 422
    assert client.get("/api/participants").json()["total"] == 2


def test_search_covers_the_full_workspace_before_paging(client):
    register(client)
    onboard(client)
    created = []
    for code in ("P-01", "P-02", "P-03"):
        response = create_participant(client, display_label=f"Label {code}")
        assert response.status_code == 201
        created.append((response.json()["id"], code))
    for participant_id, code in created:
        run_sql(
            "UPDATE participants SET reference_code = :code WHERE id = :id",
            code=code,
            id=participant_id,
        )

    found = client.get(
        "/api/participants",
        params={"q": "P-03", "page": 1, "page_size": 1, "sort": "reference_code"},
    )
    assert found.status_code == 200
    body = found.json()
    assert body["total"] == 1
    assert [item["reference_code"] for item in body["items"]] == ["P-03"]
    assert body["page"] == 1
    assert body["page_size"] == 1

    by_label = client.get("/api/participants", params={"q": "label p-02", "page_size": 1})
    assert by_label.status_code == 200
    assert by_label.json()["total"] == 1
    assert by_label.json()["items"][0]["reference_code"] == "P-02"

    summary = client.get("/api/dashboard/summary").json()
    metrics = {metric["key"]: metric for metric in summary["metrics"]}
    assert metrics["participants"]["available"] is True
    assert metrics["participants"]["value"] == 3
    assert metrics["assessments"]["available"] is True
    assert metrics["assessments"]["value"] == 0
    assert "assessments_in_progress" not in metrics
    assert "assessments_needing_review" not in metrics
