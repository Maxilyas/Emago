"""
alembic/versions/0005_expedition_logs_table.py
Agent 7 — Développeur Base de données

Responsabilité : Persistance des expéditions en vraie table.

Problème actuel (rapport v1.1) : routers/expeditions.py génère des résultats
d'expédition mais ne les persiste pas en BDD. Un redémarrage serveur pendant
une expédition active fait perdre les données.

Cette migration crée expedition_logs avec :
  - Clé primaire UUID
  - Liaison player_id + FK planets
  - ship_ids JSONB (liste des UUIDs des vaisseaux envoyés)
  - duration_hours : 2 | 6 | 12
  - event_type : RESOURCES | SHIPS_LOST | ANOMALY | EMPTY | DISCOVERY
  - result JSONB : contenu de l'événement (ressources, description, etc.)
  - launched_at + completes_at + completed_at (nullable — quand traité)
  - Index sur completes_at pour le scheduler

Dépendances : migration 0004 (alliances) doit être appliquée avant.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Alembic identifiers
revision = "0005_expedition_logs_table"
down_revision = "0004_alliances"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Table expedition_logs ────────────────────────────────────────────────
    op.create_table(
        "expedition_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "player_id",
            UUID(as_uuid=True),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "planet_id",
            UUID(as_uuid=True),
            sa.ForeignKey("planets.id", ondelete="SET NULL"),
            nullable=True,
        ),

        # Vaisseaux envoyés (snapshot UUID list)
        sa.Column("ship_ids", JSONB, nullable=False, server_default='[]'),

        # Durée de l'expédition
        sa.Column(
            "duration_hours",
            sa.SmallInteger,
            sa.CheckConstraint("duration_hours IN (2, 6, 12)", name="ck_expedition_duration"),
            nullable=False,
        ),
        sa.Column("cost_deuterium", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"),

        # Résultat
        sa.Column(
            "event_type",
            sa.String(32),
            sa.CheckConstraint(
                "event_type IN ('RESOURCES','SHIPS_LOST','ANOMALY','EMPTY','DISCOVERY')",
                name="ck_expedition_event_type",
            ),
            nullable=True,   # NULL tant que non complétée
        ),
        sa.Column("result", JSONB, nullable=True),   # NULL tant que non complétée

        # Timestamps
        sa.Column(
            "launched_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "completes_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,    # rempli quand le scheduler traite le retour
        ),
    )

    # Index pour le scheduler APScheduler (expéditions dont le retour est dû)
    op.create_index(
        "idx_expedition_completes_at",
        "expedition_logs",
        ["completes_at"],
        postgresql_where=sa.text("completed_at IS NULL"),
    )
    # Index pour les requêtes "expéditions actives d'un joueur"
    op.create_index(
        "idx_expedition_player_active",
        "expedition_logs",
        ["player_id", "completes_at"],
        postgresql_where=sa.text("completed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_expedition_player_active", table_name="expedition_logs")
    op.drop_index("idx_expedition_completes_at", table_name="expedition_logs")
    op.drop_table("expedition_logs")