"""Add vision_jobs table."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b100addvisionjobs"
down_revision = "a003employerinvite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vision_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vision_jobs_user_id", "vision_jobs", ["user_id"], unique=False)
    op.create_index("ix_vision_jobs_task", "vision_jobs", ["task"], unique=False)
    op.create_index("ix_vision_jobs_status", "vision_jobs", ["status"], unique=False)
    op.create_index("ix_vision_jobs_created_at", "vision_jobs", ["created_at"], unique=False)
    op.create_index("ix_vision_jobs_expires_at", "vision_jobs", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vision_jobs_expires_at", table_name="vision_jobs")
    op.drop_index("ix_vision_jobs_created_at", table_name="vision_jobs")
    op.drop_index("ix_vision_jobs_status", table_name="vision_jobs")
    op.drop_index("ix_vision_jobs_task", table_name="vision_jobs")
    op.drop_index("ix_vision_jobs_user_id", table_name="vision_jobs")
    op.drop_table("vision_jobs")

