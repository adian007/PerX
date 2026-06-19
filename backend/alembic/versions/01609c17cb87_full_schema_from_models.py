"""Baseline schema — managed via database/migrations/001_initial.sql + 002_packages_currency_payments.sql

Revision ID: 01609c17cb87
Revises:
Create Date: 2026-06-19 19:20:32.894910

DO NOT RUN upgrade() against an existing database bootstrapped from the SQL files.
Use: alembic stamp head

Autogenerate was run for comparison only; discrepancies are documented in the
project README / deliverable summary (index naming, partial indexes, triggers,
GIN/tsvector, unique constraints on models not declared in ORM, etc.).
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "01609c17cb87"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — canonical DDL lives in database/migrations/*.sql."""

    pass


def downgrade() -> None:
    """No-op — canonical DDL lives in database/migrations/*.sql."""

    pass
