"""Add employer invite_code column for auth registration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a003employerinvite"
down_revision = "01609c17cb87"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employer_organizations", sa.Column("invite_code", sa.String(32), nullable=True))
    op.execute(
        """
        UPDATE employer_organizations
        SET invite_code = 'PERX-' || UPPER(SUBSTRING(REPLACE(id::text, '-', ''), 1, 6))
        WHERE invite_code IS NULL
        """
    )
    op.alter_column("employer_organizations", "invite_code", nullable=False)
    op.create_index("idx_employer_invite_code", "employer_organizations", ["invite_code"], unique=True)


def downgrade() -> None:
    op.drop_index("idx_employer_invite_code", table_name="employer_organizations")
    op.drop_column("employer_organizations", "invite_code")
