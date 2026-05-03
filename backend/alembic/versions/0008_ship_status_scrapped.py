"""
alembic/versions/0008_ship_status_scrapped.py

Ajoute la valeur SCRAPPED à l'enum ship_status (ou à la colonne String).

Contexte :
  La Forge doit marquer les vaisseaux parents comme SCRAPPED après fusion.
  ShipStatus.SCRAPPED était manquant, entraînant un stockage de la valeur
  brute "SCRAPPED" et un bug d'initialisation dans finalize_forge.

  La colonne ships.status est définie comme String (pas comme un type ENUM
  PostgreSQL natif), donc aucune migration DDL n'est nécessaire pour la
  colonne elle-même. Ce script ajoute simplement un index partiel pour exclure
  les vaisseaux scrappés des requêtes hangar courantes.
"""
from __future__ import annotations

from alembic import op

revision = "0008_ship_status_scrapped"
down_revision = "0007_combat_logs_gin_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # La colonne ships.status est VARCHAR — pas besoin d'ALTER TYPE.
    # On ajoute un index partiel pour accélérer les requêtes qui filtrent
    # sur les vaisseaux actifs (excluant SCRAPPED et IN_FORGE).
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_ships_active_status
        ON ships (owner_id, status)
        WHERE status NOT IN ('SCRAPPED', 'IN_FORGE')
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_ships_active_status")
