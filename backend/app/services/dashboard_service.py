import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import AssessmentSession, Participant, Study, User, Workspace, WorkspaceMembership
from app.schemas import (
    ActivityItem,
    DashboardMetric,
    DashboardModule,
    DashboardSummary,
    DashboardWorkspace,
    MembershipOut,
)
from app.services import participant_service
from app.services.workspace_service import require_current_membership

RECENT_ACTIVITY_LIMIT = 10


def _count_metric(key: str, label: str, value: int) -> DashboardMetric:
    return DashboardMetric(key=key, label=label, value=value, available=True, note=None)


def count_people(db: Session, workspace_id: uuid.UUID, context: str) -> DashboardMetric:
    counted = participant_service.count_for_workspace(db, workspace_id, context)
    if context == "clinical":
        return _count_metric("patients", "Patients", counted)
    return _count_metric("participants", "Participants", counted)


def count_assessments(db: Session, workspace_id: uuid.UUID, context: str) -> DashboardMetric:
    total = db.scalar(
        select(func.count())
        .select_from(AssessmentSession)
        .where(
            AssessmentSession.workspace_id == workspace_id,
            AssessmentSession.context == context,
        )
    )
    return _count_metric("assessments", "Assessments", int(total or 0))


def count_studies(db: Session, workspace_id: uuid.UUID) -> DashboardMetric:
    total = db.scalar(
        select(func.count()).select_from(Study).where(Study.workspace_id == workspace_id)
    )
    return _count_metric("studies", "Studies", int(total or 0))


def list_recent_activity(db: Session, workspace: Workspace, context: str) -> list[ActivityItem]:
    memberships = db.scalars(
        select(WorkspaceMembership)
        .options(joinedload(WorkspaceMembership.user))
        .where(WorkspaceMembership.workspace_id == workspace.id)
        .order_by(WorkspaceMembership.created_at.desc())
        .limit(RECENT_ACTIVITY_LIMIT)
    ).all()
    people = db.scalars(
        select(Participant)
        .where(Participant.workspace_id == workspace.id, Participant.context == context)
        .order_by(Participant.created_at.desc())
        .limit(RECENT_ACTIVITY_LIMIT)
    ).all()

    items = [
        ActivityItem(
            id=f"member_joined:{membership.id}",
            kind="member_joined",
            title=f"{membership.user.display_name or membership.user.email} joined as {membership.access_role}",
            occurred_at=membership.created_at,
        )
        for membership in memberships
    ]
    items.extend(_person_activity(person) for person in people)
    items.append(
        ActivityItem(
            id=f"workspace_created:{workspace.id}",
            kind="workspace_created",
            title=f"Workspace \u201c{workspace.name}\u201d created",
            occurred_at=workspace.created_at,
        )
    )
    # Stable sort keeps "joined" above "created" when both share a transaction timestamp.
    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items[:RECENT_ACTIVITY_LIMIT]


def list_modules(context: str) -> list[DashboardModule]:
    if context == "clinical":
        people = ("patients", "Patient records")
    else:
        people = ("participants", "Participant records")
    pending = [
        ("protocols", "Protocol library"),
        ("analysis", "Analysis & quality review"),
        ("exports", "Data & exports"),
    ]
    if context == "research":
        pending.insert(1, ("studies", "Studies"))
    modules = [
        DashboardModule(
            key=people[0],
            label=people[1],
            available=True,
            note="Records for this context",
        ),
        DashboardModule(
            key="assessments",
            label="Assessment recording",
            available=True,
            note="Start a recording from a person's profile.",
        ),
    ]
    modules.extend(
        DashboardModule(key=key, label=label, available=False, note="Not available yet")
        for key, label in pending
    )
    return modules


def build_dashboard_summary(db: Session, user: User) -> DashboardSummary:
    membership = require_current_membership(db, user.id)
    workspace = membership.workspace
    context = membership.active_context
    member_count = db.scalar(
        select(func.count())
        .select_from(WorkspaceMembership)
        .where(WorkspaceMembership.workspace_id == workspace.id)
    )
    metrics = [
        count_people(db, workspace.id, context),
        count_assessments(db, workspace.id, context),
    ]
    if context == "research":
        metrics.append(count_studies(db, workspace.id))

    return DashboardSummary(
        workspace=DashboardWorkspace(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description,
            created_at=workspace.created_at,
            member_count=member_count or 0,
        ),
        membership=MembershipOut.model_validate(membership),
        metrics=metrics,
        recent_activity=list_recent_activity(db, workspace, context),
        modules=list_modules(context),
    )


def _person_activity(person: Participant) -> ActivityItem:
    if person.context == "clinical":
        title = f"Patient {person.display_label} recorded"
    else:
        title = f"Participant {person.reference_code} recorded"
    return ActivityItem(
        id=f"person_recorded:{person.id}",
        kind="person_recorded",
        title=title,
        occurred_at=person.created_at,
    )
