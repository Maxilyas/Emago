"""
alembic/versions/0006_ship_rpg_fields.py
Agent 7 — Développeur Base de données

Responsabilité : Ajout des champs RPG narratifs sur la table ships.

Nouveaux champs :
  - ships.name      : VARCHAR(64) nullable — nom procédural pour RARE+
                      ex: "Astraeus Noir", "Corvus Prime"
  - ships.trait     : JSONB nullable — trait narratif tiré à la construction
                      format: {"key": "bounty_hunter", "name": "...", "description": "..."}
  - ships.is_drift  : BOOLEAN NOT NULL DEFAULT FALSE
                      True si le vaisseau est issu d'une Forge ratée créativement
                      (variante "Dérive" — 5% chance)

Note sur ships.name :
  - NULL pour COMMON et UNCOMMON (pas de nom)
  - Généré par naming_service.generate_ship_name() pour RARE+
  - Immuable après création (pas de trigger nécessaire — le service ne le modifie pas)

Note sur ships.trait :
  - Toujours présent (tiré à la construction même pour COMMON)
  - Structure immuable (même logique que base_stats)
  - Effet résolu à l'exécution via TRAIT_INDEX[key]

Note sur ships.is_drift :
  - Défaut FALSE — uniquement True pour les Forges qui déclenchent la Dérive
  - Visible dans l'UI (affichage distinct, badge "Dérive")

Dépendances : migration 0005 doit être appliquée avant.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# Alembic identifiers
revision = "0006_ship_rpg_fields"
down_revision = "0005_expedition_logs_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ships.name ───────────────────────────────────────────────────────────
    op.add_column(
        "ships",
        sa.Column(
            "name",
            sa.String(64),
            nullable=True,
            comment="Nom procédural — généré pour RARE+ à la construction",
        ),
    )

    # ── ships.trait ──────────────────────────────────────────────────────────
    op.add_column(
        "ships",
        sa.Column(
            "trait",
            JSONB,
            nullable=True,  # NULL pour les vaisseaux créés avant cette migration
            comment='Trait narratif — {"key": str, "name": str, "description": str}',
        ),
    )

    # ── ships.is_drift ───────────────────────────────────────────────────────
    op.add_column(
        "ships",
        sa.Column(
            "is_drift",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="True si issu d'une Forge Dérive (5% chance)",
        ),
    )

    # Index partiel sur is_drift=TRUE (rare, donc très petit — lecture rapide)
    op.create_index(
        "idx_ships_is_drift",
        "ships",
        ["is_drift"],
        postgresql_where=sa.text("is_drift = true"),
    )

    # ── Seed scar tag "Né dans la Dérive" ────────────────────────────────────
    # Inséré ici pour être disponible lors de la première Forge Dérive
    op.execute(
        sa.text(
            """
            INSERT INTO scar_tags (tag_code, narrative)
            VALUES ('born_in_drift', 'Né dans la Dérive')
            ON CONFLICT (tag_code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("idx_ships_is_drift", table_name="ships")
    op.drop_column("ships", "is_drift")
    op.drop_column("ships", "trait")
    op.drop_column("ships", "name")
    # Note : le scar_tag "born_in_drift" est conservé (pas de DELETE pour éviter
    # de casser les cicatrices existantes en cas de rollback partiel)