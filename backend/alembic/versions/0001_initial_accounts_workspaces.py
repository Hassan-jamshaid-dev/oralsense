"""Initial accounts, sessions, workspaces and memberships

Revision ID: 0001
Revises:
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(80), nullable=True),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )

    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT", name="fk_workspaces_created_by_user_id_users"),
            nullable=False,
        ),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        sa.CheckConstraint("length(trim(name)) BETWEEN 2 AND 120", name="ck_workspaces_name_length"),
    )

    op.create_table(
        "workspace_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE", name="fk_workspace_memberships_workspace_id_workspaces"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_workspace_memberships_user_id_users"),
            nullable=False,
        ),
        sa.Column("access_role", sa.String(20), nullable=False),
        sa.Column("research_role", sa.String(40), nullable=True),
        _timestamp("created_at"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_workspace_user"),
        sa.CheckConstraint(
            "access_role IN ('owner', 'member')", name="ck_workspace_memberships_access_role"
        ),
        sa.CheckConstraint(
            "research_role IS NULL OR research_role IN ('researcher', 'research_assistant', 'administrator')",
            name="ck_workspace_memberships_research_role",
        ),
    )
    op.create_index("ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"])

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_user_sessions_user_id_users"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        _timestamp("created_at"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
    )
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_workspace_memberships_user_id", table_name="workspace_memberships")
    op.drop_table("workspace_memberships")
    op.drop_table("workspaces")
    op.drop_table("users")
