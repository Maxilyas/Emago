"""
Alliances — tables alliance_members et alliance_wars
Agent 7 — Développeur Base de données | Sprint 4

Revision ID: 0004_alliances
Revises: 0003_add_player_daily_data
Create Date: 2026-05-01

Nouvelles tables :
  - alliance_members : relation joueur ↔ alliance avec rôle
  - alliance_wars    : guerres déclarées entre alliances

Note : la table `alliances` et le champ `players.alliance_id` existent déjà
(migration 0001). On ajoute ici les tables de détail manquantes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

revision = '0004_alliances'
down_revision = '0003_add_player_daily_data'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enum rôle dans l'alliance ─────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE alliance_role AS ENUM ('LEADER', 'OFFICER', 'MEMBER');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ── Enum statut de guerre ─────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE war_status AS ENUM ('ACTIVE', 'PEACE');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ── Table alliance_members ────────────────────────────────────────────────
    # Un joueur ne peut appartenir qu'à une seule alliance (UNIQUE player_id)
    op.create_table(
        'alliance_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('alliance_id', UUID(as_uuid=True),
                  sa.ForeignKey('alliances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_id', UUID(as_uuid=True),
                  sa.ForeignKey('players.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String, nullable=False, server_default='MEMBER'),
        sa.Column('joined_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),

        # Contraintes
        sa.UniqueConstraint('player_id', name='uq_alliance_members_player'),
        sa.CheckConstraint("role IN ('LEADER', 'OFFICER', 'MEMBER')", name='ck_alliance_member_role'),
    )
    # Index fréquent : récupérer les membres d'une alliance
    op.create_index('idx_alliance_members_alliance', 'alliance_members', ['alliance_id'])
    # Index pour vérifier si un joueur est dans une alliance
    op.create_index('idx_alliance_members_player', 'alliance_members', ['player_id'])

    # ── Table alliance_wars ───────────────────────────────────────────────────
    op.create_table(
        'alliance_wars',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('attacker_id', UUID(as_uuid=True),
                  sa.ForeignKey('alliances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('defender_id', UUID(as_uuid=True),
                  sa.ForeignKey('alliances.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String, nullable=False, server_default='ACTIVE'),
        sa.Column('declared_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('peace_at', TIMESTAMP(timezone=True), nullable=True),
        sa.Column('xp_bonus', sa.Numeric(4, 2), nullable=False, server_default='1.5'),

        # Une guerre ne peut pas être contre soi-même
        sa.CheckConstraint('attacker_id != defender_id', name='ck_war_different_alliances'),
        sa.CheckConstraint("status IN ('ACTIVE', 'PEACE')", name='ck_war_status'),
    )
    op.create_index('idx_alliance_wars_attacker', 'alliance_wars', ['attacker_id'])
    op.create_index('idx_alliance_wars_defender', 'alliance_wars', ['defender_id'])
    # Index sur les guerres actives (utilisé par combat_engine pour vérifier le bonus XP)
    op.create_index(
        'idx_alliance_wars_active',
        'alliance_wars',
        ['attacker_id', 'defender_id'],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    # ── Colonne last_candidacy_at sur players ─────────────────────────────────
    # Délai de re-candidature après refus/expulsion (24h)
    op.add_column(
        'players',
        sa.Column('alliance_last_candidacy_at', TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('players', 'alliance_last_candidacy_at')
    op.drop_table('alliance_wars')
    op.drop_table('alliance_members')
    op.execute('DROP TYPE IF EXISTS war_status')
    op.execute('DROP TYPE IF EXISTS alliance_role')
