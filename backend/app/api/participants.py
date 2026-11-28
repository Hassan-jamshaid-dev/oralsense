import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.deps import CurrentCsrf, CurrentUser, DbSession
from app.schemas import (
    AssessmentHistoryResponse,
    ParticipantCreateRequest,
    ParticipantListResponse,
    ParticipantOut,
    ParticipantSort,
)
from app.services import participant_service

router = APIRouter(prefix="/participants", tags=["participants"])


@router.get("", response_model=ParticipantListResponse)
def list_participants(
    user: CurrentUser,
    db: DbSession,
    q: Annotated[str | None, Query(max_length=participant_service.MAX_QUERY_LENGTH)] = None,
    sort: Annotated[ParticipantSort, Query()] = "reference_code",
    page: Annotated[int, Query(ge=1, le=participant_service.MAX_PAGE)] = 1,
    page_size: Annotated[int, Query(ge=1, le=participant_service.MAX_PAGE_SIZE)] = (
        participant_service.DEFAULT_PAGE_SIZE
    ),
) -> ParticipantListResponse:
    return participant_service.list_participants(
        db, user, q=q, sort=sort, page=page, page_size=page_size
    )


@router.post("", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
def create_participant(
    payload: ParticipantCreateRequest,
    user: CurrentUser,
    csrf_token: CurrentCsrf,
    db: DbSession,
) -> ParticipantOut:
    # CurrentCsrf matches other mutations. The middleware rejects a bad token before this runs.
    del csrf_token
    return participant_service.create_participant(db, user, payload)


@router.get("/{participant_id}", response_model=ParticipantOut)
def read_participant(participant_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ParticipantOut:
    return participant_service.get_participant(db, user, participant_id)


@router.get("/{participant_id}/history", response_model=AssessmentHistoryResponse)
def read_participant_history(
    participant_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> AssessmentHistoryResponse:
    return participant_service.list_history(db, user, participant_id)
