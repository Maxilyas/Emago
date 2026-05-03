"""0010_ghost_ships — table des vaisseaux fantômes NPC dans la galaxie

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-04
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0010_ghost_ships"
down_revision = "0009_module_inventory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS ghost_ships (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            galaxy       SMALLINT NOT NULL,
            system       SMALLINT NOT NULL,
            name         VARCHAR(64) NOT NULL,
            ship_type    VARCHAR(64) NOT NULL,
            rarity       VARCHAR(32) NOT NULL DEFAULT 'COMMON',
            threat_level SMALLINT NOT NULL DEFAULT 1,
            current_hull INTEGER NOT NULL,
            max_hull     INTEGER NOT NULL,
            base_stats   JSONB NOT NULL,
            is_defeated  BOOLEAN NOT NULL DEFAULT false,
            defeated_at  TIMESTAMPTZ,
            respawn_at   TIMESTAMPTZ,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ghost_ships_system
        ON ghost_ships(galaxy, system)
    """)


def downgrade() -> None:
    op.drop_table("ghost_ships")
