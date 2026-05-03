"""0010_ghost_ships — table des vaisseaux fantômes NPC dans la galaxie

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-04
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ghost_ships",
        sa.Column("id",           sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("galaxy",       sa.SmallInteger(), nullable=False),
        sa.Column("system",       sa.SmallInteger(), nullable=False),
        sa.Column("name",         sa.String(64), nullable=False),
        sa.Column("ship_type",    sa.String(64), nullable=False),
        sa.Column("rarity",       sa.String(32), nullable=False, server_default="'COMMON'"),
        sa.Column("threat_level", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("current_hull", sa.Integer(), nullable=False),
        sa.Column("max_hull",     sa.Integer(), nullable=False),
        sa.Column("base_stats",   sa.JSON(), nullable=False),
        sa.Column("is_defeated",  sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("defeated_at",  sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("respawn_at",   sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at",   sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("idx_ghost_ships_system", "ghost_ships", ["galaxy", "system"])
    op.create_index("idx_ghost_ships_active", "ghost_ships", ["is_defeated"],
                    postgresql_where=sa.text("is_defeated = false"))


def downgrade() -> None:
    op.drop_table("ghost_ships")
