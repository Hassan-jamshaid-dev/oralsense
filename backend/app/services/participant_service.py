import uuid

from psycopg.errors import UniqueViolation
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.participant_codes import CODE_ATTEMPTS, generate_participant_code
from app.errors import AppError
from app.models import AssessmentSession, Participant, Study, User, Visit
from app.schemas import (
    AssessmentHistoryItem,
    AssessmentHistoryResponse,
    ParticipantCreateRequest,
    ParticipantListResponse,
    ParticipantOut,
    ParticipantSort,
)
from app.services.workspace_service import require_current_membership

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
MAX_PAGE = 10_000
MAX_QUERY_LENGTH = 80

_REFERENCE_CONSTRAINT = "uq_participants_workspace_reference_code"

# Leading "-" is descending. Anything else is rejected before it can reach SQL.
_SORT_COLUMNS: dict[ParticipantSort, tuple] = {
    "reference_code": (Participant.reference_code.asc(), Participant.id.asc()),
    "-reference_code": (Participant.reference_code.desc(), Participant.id.asc()),
    "display_label": (
        Participant.display_label.asc(),
        Participant.reference_code.asc(),
        Participant.id.asc(),
    ),
    "-display_label": (
        Participant.display_label.desc(),
        Participant.reference_code.asc(),
        Participant.id.asc(),
    ),
    "created_at": (Participant.created_at.asc(), Participant.id.asc()),
    "-created_at": (Participant.created_at.desc(), Participant.id.asc()),
}


def count_for_workspace(db: Session, workspace_id: uuid.UUID, context: str) -> int:
    total = db.scalar(
        select(func.count())
        .select_from(Participant)
        .where(Participant.workspace_id == workspace_id, Participant.context == context)
    )
    return int(total or 0)


def list_participants(
    db: Session,
    user: User,
    *,
    q: str | None,
    sort: ParticipantSort,
    page: int,
    page_size: int,
) -> ParticipantListResponse:
    membership = require_current_membership(db, user.id)
    # Membership supplies both the tenant and the working context. Neither is read from the client.
    workspace_id = membership.workspace_id
    filters = [
        Participant.workspace_id == workspace_id,
        Participant.context == membership.active_context,
    ]
    term = (q or "").strip()
    if term:
        pattern = _contains_pattern(term)
        filters.append(
            or_(
                Participant.reference_code.ilike(pattern, escape="\\"),
                Participant.display_label.ilike(pattern, escape="\\"),
            )
        )

    order = _SORT_COLUMNS.get(sort)
    if order is None:
        raise AppError(
            422,
            "validation_error",
            "Some fields need attention.",
            {"sort": "Choose a supported sort."},
        )

    total = db.scalar(select(func.count()).select_from(Participant).where(*filters)) or 0
    rows = db.scalars(
        select(Participant)
        .where(*filters)
        .order_by(*order)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ParticipantListResponse(
        items=[ParticipantOut.model_validate(row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def get_participant(db: Session, user: User, participant_id: uuid.UUID) -> Participant:
    membership = require_current_membership(db, user.id)
    participant = db.scalar(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.workspace_id == membership.workspace_id,
            Participant.context == membership.active_context,
        )
    )
    # Missing, another workspace, and the other context are the same response.
    if participant is None:
        raise AppError(404, "participant_not_found", "That record was not found.")
    return participant


def create_participant(db: Session, user: User, request: ParticipantCreateRequest) -> Participant:
    membership = require_current_membership(db, user.id)
    if membership.active_context == "clinical":
        return _create_patient(db, membership.workspace_id, request.display_label)
    return _create_research_participant(db, membership.workspace_id, request.display_label)


def list_history(db: Session, user: User, participant_id: uuid.UUID) -> AssessmentHistoryResponse:
    participant = get_participant(db, user, participant_id)
    rows = db.execute(
        select(AssessmentSession, Visit.label, Study.name)
        .outerjoin(Visit, Visit.id == AssessmentSession.visit_id)
        .outerjoin(Study, Study.id == AssessmentSession.study_id)
        .where(
            AssessmentSession.participant_id == participant.id,
            AssessmentSession.workspace_id == participant.workspace_id,
            AssessmentSession.context == participant.context,
        )
        .order_by(AssessmentSession.created_at.asc(), AssessmentSession.id.asc())
    ).all()
    return AssessmentHistoryResponse(
        items=[
            AssessmentHistoryItem(
                id=session.id,
                protocol_label=session.protocol_label,
                protocol_version=session.protocol_version,
                visit_label=visit_label,
                study_name=study_name,
                status=session.status,
                created_at=session.created_at,
            )
            for session, visit_label, study_name in rows
        ]
    )


def _create_patient(db: Session, workspace_id: uuid.UUID, display_label: str | None) -> Participant:
    if not display_label:
        raise AppError(
            422,
            "validation_error",
            "Some fields need attention.",
            {"display_label": "Enter a name or label."},
        )
    participant = Participant(
        workspace_id=workspace_id,
        context="clinical",
        reference_code=None,
        display_label=display_label,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def _create_research_participant(
    db: Session, workspace_id: uuid.UUID, display_label: str | None
) -> Participant:
    # A collision retries with a new random code. The unique constraint is the authority.
    for _ in range(CODE_ATTEMPTS):
        participant = Participant(
            workspace_id=workspace_id,
            context="research",
            reference_code=generate_participant_code(),
            display_label=display_label,
        )
        try:
            with db.begin_nested():
                db.add(participant)
                db.flush()
        except IntegrityError as exc:
            if _is_duplicate_reference(exc):
                continue
            db.rollback()
            raise
        db.commit()
        db.refresh(participant)
        return participant

    db.rollback()
    raise AppError(
        409,
        "reference_code_taken",
        "A participant code could not be assigned. Try again.",
        {"reference_code": "A participant code could not be assigned. Try again."},
    )


def _contains_pattern(term: str) -> str:
    # Bind the term as data. Escape LIKE metacharacters so a search for "%" is literal.
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _is_duplicate_reference(exc: IntegrityError) -> bool:
    orig = exc.orig
    if not isinstance(orig, UniqueViolation):
        return False
    return getattr(orig.diag, "constraint_name", None) == _REFERENCE_CONSTRAINT
