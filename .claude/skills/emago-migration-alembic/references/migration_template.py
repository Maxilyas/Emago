"""<description courte>

Revision ID: 000X
Revises: 000Y  (revision précédente)
Create Date: YYYY-MM-DD HH:MM:SS

Notes Emago :
- Tous les IDs primaires en UUID avec server_default gen_random_uuid().
- Indexes partiels (WHERE is_completed=FALSE) pour les tables consommées par scheduler.
- Triggers PG pour les colonnes immuables.
- Bypass session var emago.bypass_<x>_trigger pour migrations contrôlées.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '000X'
down_revision = '000Y'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration."""

    # ─── 1. Extensions (idempotent) ────────────────────────────────────────────
    # À ne PAS répéter si déjà créées par migration 0001.
    # op.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')

    # ─── 2. Nouveaux enums Postgres ────────────────────────────────────────────
    # op.execute("CREATE TYPE mon_enum AS ENUM ('VAL1', 'VAL2', 'VAL3')")

    # ─── 3. Nouvelle table ─────────────────────────────────────────────────────
    op.create_table(
        'ma_table',
        # PK UUID
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),

        # FK avec cascade
        sa.Column('player_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('players.id', ondelete='CASCADE'),
                  nullable=False),

        sa.Column('planet_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('planets.id', ondelete='SET NULL'),
                  nullable=True),

        # Strings simples
        sa.Column('name', sa.String(64), nullable=False),

        # Enum (utilise String côté Python pour souplesse)
        sa.Column('status', sa.String, nullable=False, server_default='ACTIVE'),

        # Numerique pour ressources (précision 16,2)
        sa.Column('cost_metal', sa.Integer, nullable=False, server_default='0'),
        sa.Column('reward_metal', sa.Numeric(16, 2), nullable=False, server_default='0'),

        # JSONB extensible
        sa.Column('payload', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('items', postgresql.JSONB, nullable=False, server_default='[]'),

        # Booleens
        sa.Column('is_completed', sa.Boolean, nullable=False, server_default='false'),

        # Timestamps
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column('completes_at', postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('completed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),

        # CHECK constraints
        sa.CheckConstraint("status IN ('ACTIVE', 'COMPLETED', 'CANCELLED')",
                           name='ck_ma_table_status'),
        sa.CheckConstraint('cost_metal >= 0', name='ck_ma_table_cost_positive'),

        # UNIQUE multi-colonnes (si applicable)
        # sa.UniqueConstraint('player_id', 'name', name='uq_ma_table_player_name'),
    )

    # ─── 4. Indexes ────────────────────────────────────────────────────────────

    # Index simple
    op.create_index('idx_ma_table_player', 'ma_table', ['player_id'])

    # Index partiel — CRITIQUE pour scheduler
    op.execute("""
        CREATE INDEX idx_ma_table_pending
        ON ma_table (completes_at)
        WHERE is_completed = FALSE
    """)

    # Index multi-colonnes
    op.create_index('idx_ma_table_player_status', 'ma_table', ['player_id', 'status'])

    # ─── 5. Triggers (si immuabilité requise) ──────────────────────────────────
    # Exemple : empêcher modification de payload après création
    # op.execute("""
    #     CREATE OR REPLACE FUNCTION prevent_ma_table_payload_update_fn()
    #     RETURNS TRIGGER AS $$
    #     BEGIN
    #         IF NEW.payload IS DISTINCT FROM OLD.payload
    #            AND COALESCE(current_setting('emago.bypass_ma_table_trigger', true), '') != 'true'
    #         THEN
    #             RAISE EXCEPTION 'payload is immutable'
    #                 USING ERRCODE = 'integrity_constraint_violation';
    #         END IF;
    #         RETURN NEW;
    #     END;
    #     $$ LANGUAGE plpgsql;
    # """)
    # op.execute("""
    #     CREATE TRIGGER prevent_ma_table_payload_update
    #     BEFORE UPDATE ON ma_table
    #     FOR EACH ROW EXECUTE FUNCTION prevent_ma_table_payload_update_fn();
    # """)

    # ─── 6. Données de seed (si applicable) ────────────────────────────────────
    # ma_table = sa.table('ma_table',
    #     sa.column('name', sa.String),
    #     sa.column('status', sa.String),
    # )
    # op.bulk_insert(ma_table, [
    #     {'name': 'item_1', 'status': 'ACTIVE'},
    #     {'name': 'item_2', 'status': 'ACTIVE'},
    # ])


def downgrade() -> None:
    """Reverse migration."""

    # Ordre inverse de upgrade

    # 1. Drop triggers (si créés)
    # op.execute("DROP TRIGGER IF EXISTS prevent_ma_table_payload_update ON ma_table")
    # op.execute("DROP FUNCTION IF EXISTS prevent_ma_table_payload_update_fn()")

    # 2. Drop indexes (les indexes auto-générés sont droppés avec la table)
    op.execute("DROP INDEX IF EXISTS idx_ma_table_pending")
    op.drop_index('idx_ma_table_player_status', table_name='ma_table')
    op.drop_index('idx_ma_table_player', table_name='ma_table')

    # 3. Drop table
    op.drop_table('ma_table')

    # 4. Drop enums
    # op.execute("DROP TYPE IF EXISTS mon_enum")

    # Note : les bulk_inserts sont automatiquement perdus avec drop_table.
    # Si on voulait conserver les données : DELETE FROM ma_table WHERE ...
    # mais c'est inutile vu qu'on drop la table.
