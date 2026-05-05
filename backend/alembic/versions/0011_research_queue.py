"""0011_research_queue — persistance des recherches technologiques en BDD

Revision ID: 0011_research_queue
Revises: 0010_ghost_ships
Create Date: 2026-05-05
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0011_research_queue"
down_revision = "0010_ghost_ships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_queue",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("player_id", sa.UUID(), nullable=False),
        sa.Column("tech_id", sa.String(64), nullable=False),
        sa.Column("tech_label", sa.String(128), nullable=False),
        sa.Column("target_level", sa.SmallInteger(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completes_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
    )
    # Index partiel pour les recherches actives (interrogé par le scheduler et les routers)
    op.create_index(
        "idx_research_queue_active",
        "research_queue",
        ["player_id", "completes_at"],
        postgresql_where=sa.text("is_completed = false"),
    )


def downgrade() -> None:
    op.drop_table("research_queue")
