import uuid

import pytest

from tests.conftest import onboard, register, run_sql


def add_member(client, email: str = "assistant@example.org") -> None:
    """Sign in as a second user who is a non-owner member of the existing workspace.

    There is no invitation flow yet, so the membership row is inserted directly.
    """
    [(workspace_id,)] = run_sql("SELECT id FROM workspaces")
    client.cookies.clear()
    user_id = register(client, email=email).json()["user"]["id"]
    run_sql(
        "INSERT INTO workspace_memberships (id, workspace_id, user_id, access_role) "
        "VALUES (:id, :workspace_id, :user_id, 'member')",
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        user_id=uuid.UUID(user_id),
    )


def test_onboarding_creates_workspace_owner_membership_and_display_name(client):
    user_id = register(client).json()["user"]["id"]

    response = onboard(client)

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["display_name"] == "Dr. Researcher"
    assert body["workspace"]["name"] == "Oral Sensory Lab"
    assert body["workspace"]["description"] == "Tactile threshold pilot"
    assert body["workspace"]["created_at"]
    assert body["membership"] == {
        "access_role": "owner",
        "research_role": "researcher",
        "active_context": "research",
    }

    [(workspace_id, created_by)] = run_sql("SELECT id, created_by_user_id FROM workspaces")
    assert str(workspace_id) == body["workspace"]["id"]
    assert str(created_by) == user_id
    assert run_sql(
        "SELECT CAST(user_id AS text), access_role, research_role FROM workspace_memberships"
    ) == [(user_id, "owner", "researcher")]
    assert run_sql("SELECT display_name FROM users") == [("Dr. Researcher",)]
    assert client.get("/api/auth/me").json() == body


def test_onboarding_trims_text_and_applies_limits_after_trimming(client):
    register(client)

    response = onboard(
        client,
        workspace_name=f"  {'a' * 120}  ",
        display_name="  Dr. Researcher ",
        description="   ",
        research_role=None,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["workspace"]["name"] == "a" * 120
    assert body["user"]["display_name"] == "Dr. Researcher"
    assert body["workspace"]["description"] is None
    assert body["membership"]["research_role"] is None


def test_duplicate_onboarding_is_rejected(client):
    register(client)
    assert onboard(client).status_code == 201

    response = onboard(client, workspace_name="Second Lab")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "workspace_exists"
    assert run_sql("SELECT name FROM workspaces") == [("Oral Sensory Lab",)]


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"workspace_name": "   "}, "workspace_name"),
        ({"workspace_name": "a"}, "workspace_name"),
        ({"workspace_name": "a" * 121}, "workspace_name"),
        ({"display_name": "   "}, "display_name"),
        ({"display_name": "d" * 81}, "display_name"),
        ({"description": "x" * 501}, "description"),
        ({"research_role": "clinician"}, "research_role"),
        ({"owner_id": str(uuid.uuid4())}, "owner_id"),
    ],
)
def test_invalid_onboarding_is_rejected_with_field_errors(client, overrides, field):
    register(client)

    response = onboard(client, **overrides)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert field in error["fields"]
    assert run_sql("SELECT count(*) FROM workspaces") == [(0,)]


def test_patch_updates_workspace_and_profile(client):
    register(client)
    onboard(client)

    response = client.patch(
        "/api/workspaces/current",
        json={
            "workspace_name": " Renamed Lab ",
            "display_name": "Dr. Renamed",
            "research_role": "administrator",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["workspace"]["name"] == "Renamed Lab"
    assert body["workspace"]["description"] == "Tactile threshold pilot"
    assert body["user"]["display_name"] == "Dr. Renamed"
    assert body["membership"]["research_role"] == "administrator"
    assert client.get("/api/auth/me").json() == body


def test_patch_null_clears_description_and_research_role(client):
    register(client)
    onboard(client)

    response = client.patch(
        "/api/workspaces/current", json={"description": None, "research_role": None}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["workspace"]["description"] is None
    assert body["membership"]["research_role"] is None
    assert body["workspace"]["name"] == "Oral Sensory Lab"
    assert run_sql("SELECT description FROM workspaces") == [(None,)]


@pytest.mark.parametrize("field", ["workspace_name", "display_name"])
def test_patch_cannot_null_required_fields(client, field):
    register(client)
    onboard(client)

    response = client.patch("/api/workspaces/current", json={field: None})

    assert response.status_code == 422
    assert field in response.json()["error"]["fields"]


def test_patch_before_onboarding_is_not_found(client):
    register(client)

    response = client.patch("/api/workspaces/current", json={"display_name": "Dr. R"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"


@pytest.mark.parametrize(
    "payload", [{"workspace_name": "Taken Over"}, {"description": "Changed by a member"}]
)
def test_non_owner_cannot_edit_workspace_details(client, payload):
    register(client)
    onboard(client)
    add_member(client)

    response = client.patch("/api/workspaces/current", json=payload)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert run_sql("SELECT name, description FROM workspaces") == [
        ("Oral Sensory Lab", "Tactile threshold pilot")
    ]


def test_non_owner_can_edit_own_profile_fields(client):
    register(client)
    onboard(client)
    add_member(client)

    response = client.patch(
        "/api/workspaces/current",
        json={"display_name": "Research Assistant", "research_role": "research_assistant"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["display_name"] == "Research Assistant"
    assert body["membership"] == {
        "access_role": "member",
        "research_role": "research_assistant",
        "active_context": "research",
    }
