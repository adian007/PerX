"""Add gamification tables for journey, quiz, achievements, reviews."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d008gamification"
down_revision = "c007refreshtokenlookup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "achievements",
        if_not_exists=True,
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirement", sa.Text(), nullable=False),
        sa.Column("interactive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("goal", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("slug"),
    )
    op.execute(
        """
        INSERT INTO achievements (slug, title, description, requirement, interactive, goal) VALUES
            ('first-steps', 'Hapat e parë', 'Përfundo hapin e parë të rrugës së përfitimeve.', 'Përfundo çdo milestone udhëtimi', FALSE, NULL),
            ('globe-trotter', 'Eksplorues global', 'Eksploro përfitime në 4 kategori të ndryshme.', 'Vizito 4 kategori në Eksploro', FALSE, NULL),
            ('wishlist-curator', 'Kurues i të ruajturave', 'Shto 5 përfitime te të ruajturat.', '5 artikuj të ruajtur', FALSE, NULL),
            ('smart-spender', 'Zgjedhës i zgjuar', 'Zgjidh një përfitim me bonus pyetësorë.', 'Përfundo rrjedhën Pyetësorë + Zgjidh', FALSE, NULL),
            ('well-rounded', 'I balancuar', 'Përfundo të gjitha hapat e rrugës.', 'Të 4 hapat e rrugës', FALSE, NULL),
            ('budget-master', 'Mjeshtër buxheti', 'Mbaj përdorimin e buxhetit nën 80% për 3 muaj.', '3 muaj nën 80%', FALSE, NULL),
            ('marathoner', 'Maratonist', 'Regjistro 100 km aktiv drejt objektivit të fitnessit.', '100 km të regjistruara', TRUE, 100)
        ON CONFLICT (slug) DO NOTHING
        """
    )
    op.create_table(
        "employee_gamification",
        if_not_exists=True,
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("xp", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("points", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("streak_days", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("class_label", sa.String(length=100), server_default=sa.text("'I ri'"), nullable=False),
        sa.Column("marathoner_miles", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "journey_progress",
        if_not_exists=True,
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'completed'"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category"),
    )
    op.create_index("ix_journey_progress_user_id", "journey_progress", ["user_id"])
    op.create_table(
        "quiz_scores",
        if_not_exists=True,
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "category"),
    )
    op.create_index("ix_quiz_scores_user_id", "quiz_scores", ["user_id"])
    op.create_table(
        "employee_achievements",
        if_not_exists=True,
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("achievement_slug", sa.String(length=50), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["achievement_slug"], ["achievements.slug"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "achievement_slug"),
    )
    op.create_index("ix_employee_achievements_user_id", "employee_achievements", ["user_id"])
    op.create_table(
        "employee_reviews",
        if_not_exists=True,
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("perk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("feedback", sa.Text(), server_default=sa.text("''"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["perk_id"], ["perks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "perk_id"),
    )
    op.create_index("ix_employee_reviews_user_id", "employee_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_reviews_user_id", table_name="employee_reviews")
    op.drop_table("employee_reviews")
    op.drop_index("ix_employee_achievements_user_id", table_name="employee_achievements")
    op.drop_table("employee_achievements")
    op.drop_index("ix_quiz_scores_user_id", table_name="quiz_scores")
    op.drop_table("quiz_scores")
    op.drop_index("ix_journey_progress_user_id", table_name="journey_progress")
    op.drop_table("journey_progress")
    op.drop_table("employee_gamification")
    op.drop_table("achievements")
