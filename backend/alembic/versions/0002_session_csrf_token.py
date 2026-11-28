"""Per-session CSRF synchronizer token

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing rows get an empty placeholder; those sessions cannot pass the token
    # check until the user signs in again. New sessions always set a real token.
    op.add_column(
        "user_sessions",
        sa.Column("csrf_token", sa.String(64), nullable=False, server_default=""),
    )
    op.alter_column("user_sessions", "csrf_token", server_default=None)


def downgrade() -> None:
    op.drop_column("user_sessions", "csrf_token")
