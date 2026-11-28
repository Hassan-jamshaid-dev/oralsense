import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ACCESS_ROLES = ("owner", "member")
RESEARCH_ROLES = ("researcher", "research_assistant", "administrator")
WORKFLOW_CONTEXTS = ("clinical", "research")
SESSION_STATUSES = ("in_progress", "paused", "awaiting_review", "completed")
DETECTION_RESPONSES = ("detected", "not_detected")
MODALITIES = ("tactile", "thermal", "chemesthetic")
PROTOCOL_STATUSES = ("draft", "active", "archived")
PROTOCOL_VERSION_STATUSES = ("draft", "published")
STUDY_STATUSES = ("active", "archived")
QUALITY_REVIEW_SOURCES = ("deterministic", "openai")
QUALITY_REVIEW_OUTCOMES = ("completed", "unavailable")


def _sql_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def _optional_text(column: str, maximum: int) -> str:
    return (
        f"{column} IS NULL OR ("
        f"{column} = trim({column}) AND length({column}) BETWEEN 1 AND {maximum}"
        f")"
    )


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Workspace(Base):
    """The tenant boundary. Participants belong to one workspace; studies and assessments will too."""

    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) BETWEEN 2 AND 120", name="ck_workspaces_name_length"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_workspace_user"),
        CheckConstraint(
            f"access_role IN ({_sql_in_list(ACCESS_ROLES)})",
            name="ck_workspace_memberships_access_role",
        ),
        CheckConstraint(
            f"research_role IS NULL OR research_role IN ({_sql_in_list(RESEARCH_ROLES)})",
            name="ck_workspace_memberships_research_role",
        ),
        CheckConstraint(
            f"active_context IN ({_sql_in_list(WORKFLOW_CONTEXTS)})",
            name="ck_workspace_memberships_active_context",
        ),
        Index("ix_workspace_memberships_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    access_role: Mapped[str] = mapped_column(String(20), nullable=False)
    research_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # The member's working context. Records stay in the context where they were created.
    active_context: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="research"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped[Workspace] = relationship()
    user: Mapped[User] = relationship()


class Participant(Base):
    """A person in one workspace and one workflow context.

    Clinical patients store a label and no research code. Research participants store a
    server-generated code that is unique per workspace. The internal id is not that code.
    (id, workspace_id, context) is unique so a session can reference the same triple and
    cannot attach to a person from the other context.
    """

    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "reference_code",
            name="uq_participants_workspace_reference_code",
        ),
        UniqueConstraint(
            "id",
            "workspace_id",
            "context",
            name="uq_participants_id_workspace_context",
        ),
        CheckConstraint(
            f"context IN ({_sql_in_list(WORKFLOW_CONTEXTS)})",
            name="ck_participants_context",
        ),
        CheckConstraint(
            "(context = 'research' AND reference_code IS NOT NULL) "
            "OR (context = 'clinical' AND reference_code IS NULL AND display_label IS NOT NULL)",
            name="ck_participants_context_identity",
        ),
        CheckConstraint(
            "reference_code IS NULL OR ("
            "reference_code = trim(reference_code) AND length(reference_code) BETWEEN 2 AND 32"
            ")",
            name="ck_participants_reference_code",
        ),
        CheckConstraint(
            "display_label IS NULL OR ("
            "display_label = trim(display_label) AND length(display_label) BETWEEN 1 AND 80"
            ")",
            name="ck_participants_display_label",
        ),
        Index("ix_participants_workspace_id", "workspace_id"),
        Index("ix_participants_workspace_context", "workspace_id", "context"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    context: Mapped[str] = mapped_column(String(20), nullable=False, server_default="research")
    reference_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    workspace: Mapped[Workspace] = relationship()


class Protocol(Base):
    """A workspace protocol. Built-in recordings stay in assessment_definitions.

    Shared by clinical and research sessions. version_label is the current label only.
    Historical sessions keep protocol_snapshot and must not be rewritten from this row.
    """

    __tablename__ = "protocols"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_protocols_id_workspace"),
        CheckConstraint(
            "name = trim(name) AND length(name) BETWEEN 2 AND 120",
            name="ck_protocols_name",
        ),
        CheckConstraint(_optional_text("description", 500), name="ck_protocols_description"),
        CheckConstraint(_optional_text("purpose", 500), name="ck_protocols_purpose"),
        CheckConstraint(_optional_text("limitations", 500), name="ck_protocols_limitations"),
        CheckConstraint(
            f"modality IS NULL OR modality IN ({_sql_in_list(MODALITIES)})",
            name="ck_protocols_modality",
        ),
        CheckConstraint(
            f"status IN ({_sql_in_list(PROTOCOL_STATUSES)})",
            name="ck_protocols_status",
        ),
        CheckConstraint(_optional_text("version_label", 40), name="ck_protocols_version_label"),
        CheckConstraint(
            _optional_text("definition_key", 64),
            name="ck_protocols_definition_key",
        ),
        Index("ix_protocols_workspace_id", "workspace_id"),
        Index("ix_protocols_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(500), nullable=True)
    limitations: Mapped[str | None] = mapped_column(String(500), nullable=True)
    modality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )
    # Denormalized current label. The immutable copy lives on protocol_versions.
    version_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    definition_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProtocolVersion(Base):
    """One immutable published revision, or a draft no completed session has to keep.

    A published row cannot be updated. Sessions copy label and snapshot at start.
    """

    __tablename__ = "protocol_versions"
    __table_args__ = (
        UniqueConstraint(
            "protocol_id",
            "version_number",
            name="uq_protocol_versions_protocol_number",
        ),
        UniqueConstraint(
            "id",
            "protocol_id",
            "workspace_id",
            name="uq_protocol_versions_id_protocol_workspace",
        ),
        ForeignKeyConstraint(
            ["protocol_id", "workspace_id"],
            ["protocols.id", "protocols.workspace_id"],
            name="fk_protocol_versions_protocol",
            ondelete="CASCADE",
        ),
        CheckConstraint("version_number >= 1", name="ck_protocol_versions_number"),
        CheckConstraint(
            "version_label = trim(version_label) AND length(version_label) BETWEEN 1 AND 40",
            name="ck_protocol_versions_label",
        ),
        CheckConstraint(
            "name = trim(name) AND length(name) BETWEEN 2 AND 120",
            name="ck_protocol_versions_name",
        ),
        CheckConstraint(_optional_text("description", 500), name="ck_protocol_versions_description"),
        CheckConstraint(_optional_text("purpose", 500), name="ck_protocol_versions_purpose"),
        CheckConstraint(
            _optional_text("limitations", 500), name="ck_protocol_versions_limitations"
        ),
        CheckConstraint(
            f"modality IS NULL OR modality IN ({_sql_in_list(MODALITIES)})",
            name="ck_protocol_versions_modality",
        ),
        CheckConstraint(
            f"status IN ({_sql_in_list(PROTOCOL_VERSION_STATUSES)})",
            name="ck_protocol_versions_status",
        ),
        CheckConstraint(
            "(status = 'draft' AND published_at IS NULL) "
            "OR (status = 'published' AND published_at IS NOT NULL)",
            name="ck_protocol_versions_published_at",
        ),
        CheckConstraint(
            _optional_text("definition_key", 64),
            name="ck_protocol_versions_definition_key",
        ),
        CheckConstraint(
            _optional_text("response_scale", 40),
            name="ck_protocol_versions_response_scale",
        ),
        CheckConstraint(
            _optional_text("change_summary", 500),
            name="ck_protocol_versions_change_summary",
        ),
        CheckConstraint(
            _optional_text("materials_note", 500),
            name="ck_protocol_versions_materials_note",
        ),
        CheckConstraint(
            "instructions IS NULL OR jsonb_typeof(instructions) = 'array'",
            name="ck_protocol_versions_instructions",
        ),
        CheckConstraint(
            "parameters IS NULL OR jsonb_typeof(parameters) = 'object'",
            name="ck_protocol_versions_parameters",
        ),
        Index("ix_protocol_versions_protocol_id", "protocol_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    protocol_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_label: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(500), nullable=True)
    limitations: Mapped[str | None] = mapped_column(String(500), nullable=True)
    modality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    definition_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_scale: Mapped[str | None] = mapped_column(String(40), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    materials_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    instructions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Study(Base):
    """A research study. Clinical sessions cannot reference one.

    Archiving changes status only. It does not delete sessions.
    """

    __tablename__ = "studies"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", "context", name="uq_studies_id_workspace_context"),
        UniqueConstraint("id", "workspace_id", name="uq_studies_id_workspace"),
        CheckConstraint("context = 'research'", name="ck_studies_context"),
        CheckConstraint(
            "name = trim(name) AND length(name) BETWEEN 2 AND 120",
            name="ck_studies_name",
        ),
        CheckConstraint(_optional_text("description", 500), name="ck_studies_description"),
        CheckConstraint(_optional_text("purpose", 500), name="ck_studies_purpose"),
        CheckConstraint(
            f"status IN ({_sql_in_list(STUDY_STATUSES)})",
            name="ck_studies_status",
        ),
        Index("ix_studies_workspace_id", "workspace_id"),
        Index("ix_studies_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    context: Mapped[str] = mapped_column(String(20), nullable=False, server_default="research")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StudyParticipant(Base):
    """Links a research participant to a study. This is not an assessment session."""

    __tablename__ = "study_participants"
    __table_args__ = (
        UniqueConstraint(
            "study_id",
            "participant_id",
            name="uq_study_participants_study_participant",
        ),
        CheckConstraint("context = 'research'", name="ck_study_participants_context"),
        ForeignKeyConstraint(
            ["study_id", "workspace_id", "context"],
            ["studies.id", "studies.workspace_id", "studies.context"],
            name="fk_study_participants_study",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["participant_id", "workspace_id", "context"],
            ["participants.id", "participants.workspace_id", "participants.context"],
            name="fk_study_participants_participant",
            ondelete="CASCADE",
        ),
        Index("ix_study_participants_study_id", "study_id"),
        Index("ix_study_participants_participant_id", "participant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    study_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    context: Mapped[str] = mapped_column(
        String(20), nullable=False, default="research", server_default="research"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Visit(Base):
    """An optional clinical visit for one patient. Research sessions cannot reference one."""

    __tablename__ = "visits"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", "context", name="uq_visits_id_workspace_context"),
        CheckConstraint("context = 'clinical'", name="ck_visits_context"),
        CheckConstraint(
            "label IS NULL OR (label = trim(label) AND length(label) BETWEEN 1 AND 120)",
            name="ck_visits_label",
        ),
        ForeignKeyConstraint(
            ["participant_id", "workspace_id", "context"],
            ["participants.id", "participants.workspace_id", "participants.context"],
            name="fk_visits_participant_context",
            ondelete="CASCADE",
        ),
        Index("ix_visits_workspace_id", "workspace_id"),
        Index("ix_visits_participant_id", "participant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    context: Mapped[str] = mapped_column(String(20), nullable=False, server_default="clinical")
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AssessmentDefinition(Base):
    """A recording this version can store. Rows are seeded, not edited from the client.

    Historical sessions keep a snapshot, so these rows are not a rewrite of past work.
    """

    __tablename__ = "assessment_definitions"
    __table_args__ = (
        UniqueConstraint("key", name="uq_assessment_definitions_key"),
        CheckConstraint(
            "key = trim(key) AND length(key) BETWEEN 2 AND 64",
            name="ck_assessment_definitions_key",
        ),
        CheckConstraint(
            "version = trim(version) AND length(version) BETWEEN 1 AND 40",
            name="ck_assessment_definitions_version",
        ),
        CheckConstraint(
            "modality IS NULL OR modality IN ('tactile', 'thermal', 'chemesthetic')",
            name="ck_assessment_definitions_modality",
        ),
        CheckConstraint(
            "name = trim(name) AND length(name) BETWEEN 2 AND 120",
            name="ck_assessment_definitions_name",
        ),
        CheckConstraint(
            "(available = true AND unavailable_reason IS NULL) "
            "OR (available = false AND unavailable_reason IS NOT NULL)",
            name="ck_assessment_definitions_availability",
        ),
        CheckConstraint("sort_order >= 0", name="ck_assessment_definitions_sort_order"),
        CheckConstraint(
            "jsonb_typeof(instructions) = 'array'",
            name="ck_assessment_definitions_instructions",
        ),
        CheckConstraint(
            "jsonb_typeof(response_options) = 'array'",
            name="ck_assessment_definitions_response_options",
        ),
        CheckConstraint(
            "parameters IS NULL OR jsonb_typeof(parameters) IN ('object', 'null')",
            name="ck_assessment_definitions_parameters",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    modality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    unavailable_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    prototype_notice: Mapped[str] = mapped_column(String(500), nullable=False)
    instructions: Mapped[list] = mapped_column(JSONB, nullable=False)
    materials_note: Mapped[str] = mapped_column(String(500), nullable=False)
    response_scale: Mapped[str] = mapped_column(String(40), nullable=False)
    response_options: Mapped[list] = mapped_column(JSONB, nullable=False)
    parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AssessmentSession(Base):
    """A recorded assessment, linked to one person and that person's context.

    Study and visit are optional. A check constraint rejects a study on a clinical
    session and a visit on a research session. The participant foreign key includes
    context, so a session cannot point at a person from the other workflow.
    protocol_label, protocol_version, and protocol_snapshot are copies taken at start.
    protocol_version_id points at the library revision when one was used. Publishing a
    later revision must not change those snapshot columns.
    """

    __tablename__ = "assessment_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["participant_id", "workspace_id", "context"],
            ["participants.id", "participants.workspace_id", "participants.context"],
            name="fk_assessment_sessions_participant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["visit_id", "workspace_id", "context"],
            ["visits.id", "visits.workspace_id", "visits.context"],
            name="fk_assessment_sessions_visit",
        ),
        ForeignKeyConstraint(
            ["study_id", "workspace_id", "context"],
            ["studies.id", "studies.workspace_id", "studies.context"],
            name="fk_assessment_sessions_study",
        ),
        ForeignKeyConstraint(
            ["protocol_id", "workspace_id"],
            ["protocols.id", "protocols.workspace_id"],
            name="fk_assessment_sessions_protocol",
        ),
        ForeignKeyConstraint(
            ["protocol_version_id", "protocol_id", "workspace_id"],
            [
                "protocol_versions.id",
                "protocol_versions.protocol_id",
                "protocol_versions.workspace_id",
            ],
            name="fk_assessment_sessions_protocol_version",
        ),
        UniqueConstraint("id", "workspace_id", name="uq_assessment_sessions_id_workspace"),
        CheckConstraint(
            f"context IN ({_sql_in_list(WORKFLOW_CONTEXTS)})",
            name="ck_assessment_sessions_context",
        ),
        CheckConstraint(
            "study_id IS NULL OR context = 'research'",
            name="ck_assessment_sessions_clinical_has_no_study",
        ),
        CheckConstraint(
            "visit_id IS NULL OR context = 'clinical'",
            name="ck_assessment_sessions_research_has_no_visit",
        ),
        CheckConstraint(
            "protocol_label IS NULL OR ("
            "protocol_label = trim(protocol_label) AND length(protocol_label) BETWEEN 1 AND 120"
            ")",
            name="ck_assessment_sessions_protocol_label",
        ),
        CheckConstraint(
            "protocol_version IS NULL OR ("
            "protocol_version = trim(protocol_version) AND length(protocol_version) BETWEEN 1 AND 40"
            ")",
            name="ck_assessment_sessions_protocol_version",
        ),
        CheckConstraint(
            f"status IN ({_sql_in_list(SESSION_STATUSES)})",
            name="ck_assessment_sessions_status",
        ),
        CheckConstraint("version >= 1", name="ck_assessment_sessions_version"),
        CheckConstraint(
            "(status = 'paused' AND paused_at IS NOT NULL) OR (status <> 'paused' AND paused_at IS NULL)",
            name="ck_assessment_sessions_paused_at",
        ),
        CheckConstraint(
            "(status = 'completed' AND completed_at IS NOT NULL) "
            "OR (status <> 'completed' AND completed_at IS NULL)",
            name="ck_assessment_sessions_completed_at",
        ),
        CheckConstraint(
            "config_snapshot IS NULL OR jsonb_typeof(config_snapshot) = 'object'",
            name="ck_assessment_sessions_config_snapshot",
        ),
        CheckConstraint(
            "protocol_snapshot IS NULL OR jsonb_typeof(protocol_snapshot) = 'object'",
            name="ck_assessment_sessions_protocol_snapshot",
        ),
        CheckConstraint(
            "analysis_method IS NULL OR ("
            "analysis_method = trim(analysis_method) AND length(analysis_method) BETWEEN 1 AND 80"
            ")",
            name="ck_assessment_sessions_analysis_method",
        ),
        CheckConstraint(
            "threshold_unit IS NULL OR ("
            "threshold_unit = trim(threshold_unit) AND length(threshold_unit) BETWEEN 1 AND 16"
            ")",
            name="ck_assessment_sessions_threshold_unit",
        ),
        CheckConstraint(
            "threshold_unavailable_reason IS NULL OR ("
            "threshold_unavailable_reason = trim(threshold_unavailable_reason) "
            "AND length(threshold_unavailable_reason) BETWEEN 1 AND 500"
            ")",
            name="ck_assessment_sessions_threshold_unavailable_reason",
        ),
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_assessment_sessions_workspace_idempotency",
        ),
        Index("ix_assessment_sessions_workspace_context", "workspace_id", "context"),
        Index("ix_assessment_sessions_participant_id", "participant_id"),
        Index("ix_assessment_sessions_definition_id", "definition_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    context: Mapped[str] = mapped_column(String(20), nullable=False)
    protocol_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    protocol_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    protocol_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    protocol_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    visit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    study_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    definition_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("assessment_definitions.id", ondelete="RESTRICT"), nullable=True
    )
    # in_progress, paused, awaiting_review, completed. Completed sessions stay completed.
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="in_progress")
    # Optimistic concurrency. A stale client version cannot overwrite a newer write.
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    idempotency_key: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # Frozen at start so a later definition edit cannot rewrite this session.
    config_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    protocol_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Persisted at finalize for staircase sessions. Recomputable from trials.
    estimated_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    uncertainty: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    threshold_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    threshold_unavailable_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AssessmentTrial(Base):
    """One saved observation. Corrections update this row; they do not insert another."""

    __tablename__ = "assessment_trials"
    __table_args__ = (
        UniqueConstraint("session_id", "trial_number", name="uq_assessment_trials_session_trial"),
        CheckConstraint(
            "trial_number BETWEEN 1 AND 40",
            name="ck_assessment_trials_trial_number",
        ),
        CheckConstraint(
            f"response IN ({_sql_in_list(DETECTION_RESPONSES)})",
            name="ck_assessment_trials_response",
        ),
        CheckConstraint(
            "response_scale = 'detected_not_detected'",
            name="ck_assessment_trials_response_scale",
        ),
        CheckConstraint(
            "note IS NULL OR (note = trim(note) AND length(note) BETWEEN 1 AND 500)",
            name="ck_assessment_trials_note",
        ),
        CheckConstraint(
            "correction_note IS NULL OR ("
            "correction_note = trim(correction_note) AND length(correction_note) BETWEEN 1 AND 500"
            ")",
            name="ck_assessment_trials_correction_note",
        ),
        CheckConstraint(
            f"prior_response IS NULL OR prior_response IN ({_sql_in_list(DETECTION_RESPONSES)})",
            name="ck_assessment_trials_prior_response",
        ),
        CheckConstraint(
            f"original_response IS NULL OR original_response IN ({_sql_in_list(DETECTION_RESPONSES)})",
            name="ck_assessment_trials_original_response",
        ),
        CheckConstraint("correction_count >= 0", name="ck_assessment_trials_correction_count"),
        CheckConstraint(
            "("
            "correction_count = 0 AND corrected_at IS NULL AND prior_response IS NULL "
            "AND original_response IS NULL AND corrected_by_user_id IS NULL AND correction_note IS NULL"
            ") OR ("
            "correction_count > 0 AND corrected_at IS NOT NULL AND prior_response IS NOT NULL "
            "AND original_response IS NOT NULL AND corrected_by_user_id IS NOT NULL"
            ")",
            name="ck_assessment_trials_correction",
        ),
        Index("ix_assessment_trials_session_id", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("assessment_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    trial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    response: Mapped[str] = mapped_column(String(32), nullable=False)
    response_scale: Mapped[str] = mapped_column(String(40), nullable=False)
    # Authoritative recommended force label at record time (staircase only).
    stimulus_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    corrected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    prior_response: Mapped[str | None] = mapped_column(String(32), nullable=True)
    original_response: Mapped[str | None] = mapped_column(String(32), nullable=True)
    correction_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    correction_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class QualityReview(Base):
    """Stored advisory review. Rows are not observations and do not change trial data.

    The quality service inserts source, outcome, flags, and the session or study id.
    A review cannot point at a session or study outside its workspace.
    """

    __tablename__ = "quality_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "workspace_id"],
            ["assessment_sessions.id", "assessment_sessions.workspace_id"],
            name="fk_quality_reviews_session",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["study_id", "workspace_id"],
            ["studies.id", "studies.workspace_id"],
            name="fk_quality_reviews_study",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "session_id IS NOT NULL OR study_id IS NOT NULL",
            name="ck_quality_reviews_subject",
        ),
        CheckConstraint(
            f"source IN ({_sql_in_list(QUALITY_REVIEW_SOURCES)})",
            name="ck_quality_reviews_source",
        ),
        CheckConstraint(
            f"outcome IN ({_sql_in_list(QUALITY_REVIEW_OUTCOMES)})",
            name="ck_quality_reviews_outcome",
        ),
        CheckConstraint(
            "quality_status = trim(quality_status) AND length(quality_status) BETWEEN 2 AND 40",
            name="ck_quality_reviews_quality_status",
        ),
        CheckConstraint(
            "confidence = trim(confidence) AND length(confidence) BETWEEN 2 AND 40",
            name="ck_quality_reviews_confidence",
        ),
        CheckConstraint(
            "summary = trim(summary) AND length(summary) BETWEEN 1 AND 2000",
            name="ck_quality_reviews_summary",
        ),
        CheckConstraint("jsonb_typeof(flags) = 'array'", name="ck_quality_reviews_flags"),
        CheckConstraint(
            "octet_length(flags::text) <= 20000",
            name="ck_quality_reviews_flags_size",
        ),
        Index("ix_quality_reviews_session_id", "session_id"),
        Index("ix_quality_reviews_study_id", "study_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    study_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(40), nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    flags: Mapped[list] = mapped_column(JSONB, nullable=False)
    summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    review_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Only the SHA-256 of the cookie token is stored, so a database leak does not leak sessions.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Synchronizer token returned to the SPA; stored as-is so GET /auth/me can return it.
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship()
