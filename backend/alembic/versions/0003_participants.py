"""Workspace-scoped participants

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-12

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey(
                "workspaces.id",
                ondelete="CASCADE",
                name="fk_participants_workspace_id_workspaces",
            ),
            nullable=False,
        ),
        sa.Column("reference_code", sa.String(32), nullable=False),
        sa.Column("display_label", sa.String(80), nullable=True),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        sa.UniqueConstraint(
            "workspace_id",
            "reference_code",
            name="uq_participants_workspace_reference_code",
        ),
        sa.CheckConstraint(
            "reference_code = trim(reference_code) AND length(reference_code) BETWEEN 2 AND 32",
            name="ck_participants_reference_code",
        ),
        sa.CheckConstraint(
            "display_label IS NULL OR ("
            "display_label = trim(display_label) AND length(display_label) BETWEEN 1 AND 80"
            ")",
            name="ck_participants_display_label",
        ),
    )
    op.create_index("ix_participants_workspace_id", "participants", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_participants_workspace_id", table_name="participants")
    op.drop_table("participants")
