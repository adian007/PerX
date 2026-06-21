"""Add refresh token lookup_hash for O(1) token resolution."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c007refreshtokenlookup"
down_revision = "b100addvisionjobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("refresh_tokens", sa.Column("lookup_hash", sa.String(length=64), nullable=True))
    op.execute("UPDATE refresh_tokens SET is_revoked = TRUE WHERE lookup_hash IS NULL")
    op.execute("DELETE FROM refresh_tokens WHERE lookup_hash IS NULL")
    op.alter_column("refresh_tokens", "lookup_hash", nullable=False)
    op.create_index("ix_refresh_tokens_lookup_hash", "refresh_tokens", ["lookup_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_lookup_hash", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "lookup_hash")
