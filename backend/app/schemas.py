import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH

ResearchRole = Literal["researcher", "research_assistant", "administrator"]
AccessRole = Literal["owner", "member"]
WorkflowContext = Literal["clinical", "research"]


def _strip_required(value: str, label: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} cannot be blank.")
    return stripped


def _clean_workspace_name(value: str) -> str:
    stripped = _strip_required(value, "Workspace name")
    if len(stripped) < 2:
        raise ValueError("Workspace name must be at least 2 characters.")
    return stripped


def _strip_text(value: object) -> object:
    # Runs before length constraints so limits apply to the trimmed value that gets stored.
    return value.strip() if isinstance(value, str) else value


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- Auth ----------


class Credentials(RequestModel):
    email: EmailStr
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class RegisterRequest(Credentials):
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class LoginRequest(Credentials):
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str | None


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_role: AccessRole
    research_role: ResearchRole | None
    active_context: WorkflowContext


class MeResponse(BaseModel):
    user: UserOut
    workspace: WorkspaceOut | None
    membership: MembershipOut | None
    csrf_token: str


# ---------- Workspaces ----------


class WorkspaceCreateRequest(RequestModel):
    workspace_name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=500)
    display_name: str = Field(max_length=80)
    research_role: ResearchRole | None = None
    context: WorkflowContext

    @field_validator("workspace_name", "description", "display_name", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("workspace_name")
    @classmethod
    def validate_workspace_name(cls, value: str) -> str:
        return _clean_workspace_name(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        return _strip_required(value, "Display name")

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class WorkspaceUpdateRequest(RequestModel):
    """Partial update: omitted fields are left unchanged; description/research_role accept null to clear."""

    workspace_name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    display_name: str | None = Field(default=None, max_length=80)
    research_role: ResearchRole | None = None
    active_context: WorkflowContext | None = None

    @field_validator("workspace_name", "description", "display_name", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("workspace_name")
    @classmethod
    def validate_workspace_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Workspace name cannot be empty.")
        return _clean_workspace_name(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Display name cannot be empty.")
        return _strip_required(value, "Display name")

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return _strip_optional(value)


# ---------- Participants ----------


ParticipantSort = Literal[
    "reference_code",
    "-reference_code",
    "display_label",
    "-display_label",
    "created_at",
    "-created_at",
]


class ParticipantCreateRequest(RequestModel):
    """The working context and any research code come from the server, not this body."""

    display_label: str | None = Field(default=None, max_length=80)

    @field_validator("display_label", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("display_label")
    @classmethod
    def validate_display_label(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    context: WorkflowContext
    reference_code: str | None
    display_label: str | None
    created_at: datetime
    updated_at: datetime


class ParticipantListResponse(BaseModel):
    items: list[ParticipantOut]
    total: int
    page: int
    page_size: int


class AssessmentHistoryItem(BaseModel):
    id: uuid.UUID
    protocol_label: str | None
    protocol_version: str | None
    visit_label: str | None
    study_name: str | None
    status: str
    created_at: datetime


class AssessmentHistoryResponse(BaseModel):
    items: list[AssessmentHistoryItem]


# ---------- Dashboard ----------


class DashboardWorkspace(WorkspaceOut):
    member_count: int


class DashboardMetric(BaseModel):
    key: str
    label: str
    # None means "not measurable yet", which is different from zero.
    value: int | None
    available: bool
    note: str | None


class ActivityItem(BaseModel):
    id: str
    kind: Literal["workspace_created", "member_joined", "person_recorded"]
    title: str
    occurred_at: datetime


class DashboardModule(BaseModel):
    key: str
    label: str
    available: bool
    note: str


class DashboardSummary(BaseModel):
    workspace: DashboardWorkspace
    membership: MembershipOut
    metrics: list[DashboardMetric]
    recent_activity: list[ActivityItem]
    modules: list[DashboardModule]


# ---------- Health ----------


class HealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["ok", "not_configured", "unavailable"]


# ---------- Assessment recording ----------

SessionStatus = Literal["in_progress", "paused", "awaiting_review", "completed"]
DetectionResponse = Literal["detected", "not_detected"]
ReviewLevel = Literal["error", "warning", "information"]


class TrialCountParameter(BaseModel):
    minimum: int
    maximum: int
    default: int


class StimulusLabelParameter(BaseModel):
    min_length: int
    max_length: int


class StaircaseParameters(BaseModel):
    analysis_method: str
    rule: str
    unit: str
    level_grid: list[float]
    start_index: int
    target_reversals: int
    max_trials: int
    reversals_for_estimate: int
    min_reversals_for_estimate: int
    uncertainty: str
    threshold_label: str | None = None
    uncertainty_label: str | None = None
    limitation_note: str | None = None


class DefinitionParameters(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    trial_count: TrialCountParameter
    stimulus_label: StimulusLabelParameter
    staircase: StaircaseParameters | None = None


class AssessmentDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    version: str
    modality: str | None
    name: str
    available: bool
    unavailable_reason: str | None
    summary: str
    prototype_notice: str
    instructions: list[str]
    materials_note: str
    response_scale: str
    response_options: list[str]
    parameters: DefinitionParameters | None
    sort_order: int


class AssessmentDefinitionListResponse(BaseModel):
    items: list[AssessmentDefinitionOut]


class SessionCreateRequest(RequestModel):
    participant_id: uuid.UUID
    definition_key: str = Field(min_length=1, max_length=64)
    idempotency_key: uuid.UUID
    trial_count: int = Field(ge=1, le=100)
    stimulus_label: str = Field(min_length=1, max_length=80)
    visit_label: str | None = Field(default=None, max_length=120)
    # Optional. A clinical session omits it. The column and foreign key already exist.
    study_id: uuid.UUID | None = None
    # Optional library identity. Omitted when the operator starts from a person
    # without a protocol. The server copies the published version; it does not
    # trust a later edit of that protocol to rewrite the session.
    protocol_id: uuid.UUID | None = None
    protocol_version_id: uuid.UUID | None = None
    protocol_version: str | None = Field(default=None, max_length=40)

    @field_validator("definition_key", "stimulus_label", "visit_label", "protocol_version", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("stimulus_label")
    @classmethod
    def stimulus_label_present(cls, value: str) -> str:
        return _strip_required(value, "Stimulus label")

    @field_validator("visit_label", "protocol_version")
    @classmethod
    def empty_optional_text_is_absent(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class SessionVersionRequest(RequestModel):
    version: int = Field(ge=1)


class TrialWriteRequest(RequestModel):
    version: int = Field(ge=1)
    trial_number: int = Field(ge=1, le=40)
    response: DetectionResponse
    note: str | None = Field(default=None, max_length=500)

    @field_validator("note", mode="before")
    @classmethod
    def strip_note(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("note")
    @classmethod
    def empty_note_is_absent(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class TrialCorrectionRequest(RequestModel):
    version: int = Field(ge=1)
    response: DetectionResponse
    note: str | None = Field(default=None, max_length=500)
    correction_note: str | None = Field(default=None, max_length=500)

    @field_validator("note", "correction_note", mode="before")
    @classmethod
    def strip_note(cls, value: object) -> object:
        return _strip_text(value)

    @field_validator("note", "correction_note")
    @classmethod
    def empty_note_is_absent(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class PersonRef(BaseModel):
    id: uuid.UUID
    context: WorkflowContext
    reference_code: str | None
    display_label: str | None


class TrialOut(BaseModel):
    trial_number: int
    response: DetectionResponse
    response_scale: str
    stimulus_level: float | None = None
    note: str | None
    recorded_at: datetime
    corrected_at: datetime | None
    prior_response: DetectionResponse | None
    original_response: DetectionResponse | None
    correction_note: str | None
    correction_count: int


class SessionListItem(BaseModel):
    """Summary row for the assessments hub. Trials stay on the detail endpoints."""

    id: uuid.UUID
    participant: PersonRef
    context: WorkflowContext
    status: SessionStatus
    protocol_label: str | None
    protocol_version: str | None
    modality: str | None
    visit_label: str | None
    study_id: uuid.UUID | None
    study_name: str | None
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    items: list[SessionListItem]
    total: int
    page: int
    page_size: int


class SessionOut(BaseModel):
    id: uuid.UUID
    participant: PersonRef
    context: WorkflowContext
    status: SessionStatus
    version: int
    definition_key: str | None
    modality: str | None
    protocol_label: str | None
    protocol_version: str | None
    stimulus_label: str | None
    trial_count: int | None
    visit_label: str | None
    study_id: uuid.UUID | None
    study_name: str | None
    prototype_notice: str | None
    instructions: list[str]
    materials_note: str | None
    response_options: list[str]
    next_trial_number: int | None
    # Authoritative next force label for staircase sessions; null for fixed detection.
    recommended_stimulus_level: float | None = None
    recommended_stimulus_unit: str | None = None
    analysis_method: str | None = None
    staircase_stopped: bool | None = None
    started_at: datetime | None
    paused_at: datetime | None
    completed_at: datetime | None
    trials: list[TrialOut]


class ReviewCheckOut(BaseModel):
    level: ReviewLevel
    code: str
    message: str


class SessionReviewOut(BaseModel):
    session: SessionOut
    checks: list[ReviewCheckOut]
    can_finalize: bool


class SessionResultsOut(BaseModel):
    session: SessionOut
    expected_trials: int | None
    recorded_trials: int
    missing_trials: int | None
    detected: int | None
    not_detected: int | None
    derived_metric: None
    derived_metric_note: str
    analysis_method: str | None = None
    estimated_threshold: float | None = None
    uncertainty: float | None = None
    threshold_unit: str | None = None
    threshold_unavailable_reason: str | None = None
    threshold_label: str | None = None
    uncertainty_label: str | None = None
    limitation_note: str | None = None
    reversal_count: int | None = None
    reversals_used: int | None = None
