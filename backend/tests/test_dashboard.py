import uuid
from datetime import datetime

from tests.conftest import onboard, register, run_sql


def test_health_reports_database_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_dashboard_before_onboarding_is_not_found(client):
    register(client)

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"


def test_dashboard_summary_reports_real_state_only(client):
    register(client)
    me = onboard(client).json()

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["workspace"] == {**me["workspace"], "member_count": 1}
    assert body["membership"] == me["membership"]

    metrics = {metric["key"]: metric for metric in body["metrics"]}
    assert set(metrics) == {"participants", "assessments", "studies"}
    assert "patients" not in metrics
    assert metrics["participants"]["available"] is True
    assert metrics["participants"]["value"] == 0
    assert metrics["participants"]["label"] == "Participants"
    assert metrics["participants"]["note"] is None
    assert metrics["assessments"]["available"] is True
    assert metrics["assessments"]["value"] == 0
    assert metrics["studies"]["available"] is True
    assert metrics["studies"]["value"] == 0
    assert "assessments_in_progress" not in metrics
    assert "assessments_needing_review" not in metrics

    activity = body["recent_activity"]
    assert [item["kind"] for item in activity] == ["member_joined", "workspace_created"]
    assert "Dr. Researcher" in activity[0]["title"]
    assert "Oral Sensory Lab" in activity[1]["title"]
    assert len({item["id"] for item in activity}) == len(activity)

    modules = {module["key"]: module for module in body["modules"]}
    assert modules["participants"]["available"] is True
    assert modules["studies"]["available"] is False
    assert modules["assessments"]["available"] is True


def test_recent_activity_is_newest_first_and_counts_members(client):
    register(client)
    onboard(client)
    [(workspace_id,)] = run_sql("SELECT id FROM workspaces")
    later_user_id = uuid.uuid4()
    run_sql(
        "INSERT INTO users (id, email, password_hash) "
        "VALUES (:id, 'assistant@example.org', 'not-a-usable-hash')",
        id=later_user_id,
    )
    run_sql(
        "INSERT INTO workspace_memberships (id, workspace_id, user_id, access_role, created_at) "
        "VALUES (:id, :workspace_id, :user_id, 'member', now() + interval '1 minute')",
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=later_user_id,
    )

    body = client.get("/api/dashboard/summary").json()

    assert body["workspace"]["member_count"] == 2
    activity = body["recent_activity"]
    assert [item["kind"] for item in activity] == [
        "member_joined",
        "member_joined",
        "workspace_created",
    ]
    assert "assistant@example.org" in activity[0]["title"]
    timestamps = [datetime.fromisoformat(item["occurred_at"]) for item in activity]
    assert timestamps == sorted(timestamps, reverse=True)
