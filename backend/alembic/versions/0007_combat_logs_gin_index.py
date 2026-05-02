"""
alembic/versions/0007_combat_logs_gin_index.py
Agent 7 — Développeur Base de données

Responsabilité : Index GIN sur les colonnes JSONB des snapshots de combat.

Contexte (Agent 8 — QA) :
  Les requêtes GET /combat/history filtrent avec l'opérateur PostgreSQL @>
  (containment) sur attacker_ships_snapshot et defender_ships_snapshot pour
  retrouver les combats d'un joueur. Sans index GIN, chaque requête effectue
  un seq-scan sur la table combat_logs qui peut atteindre des millions de lignes.

Décision technique (Agent 3) :
  - Opérateur jsonb_path_ops : plus compact qu'ops par défaut, couvre @> et @?
  - CREATE INDEX CONCURRENTLY : évite le lock exclusif en production
  - Downgrade avec DROP INDEX CONCURRENTLY pour rester non-bloquant
"""
from alembic import op

revision = "0007_combat_logs_gin_index"
down_revision = "0006_ship_rpg_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_combat_logs_attacker_snapshot
        ON combat_logs USING GIN (attacker_ships_snapshot jsonb_path_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_combat_logs_defender_snapshot
        ON combat_logs USING GIN (defender_ships_snapshot jsonb_path_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_combat_logs_attacker_snapshot")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_combat_logs_defender_snapshot")
