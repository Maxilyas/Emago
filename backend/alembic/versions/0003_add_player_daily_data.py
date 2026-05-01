"""Add daily_data column to players

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-01

Contexte :
  Le router daily.py utilise Player.daily_data (JSONB) pour stocker le streak
  de connexion et les missions journalières réclamées. Ce champ était absent
  du schéma initial — le router l'accédait via getattr(..., None) ce qui
  empêchait toute sauvegarde effective.

Structure du JSON stocké :
  {
    "last_login_date": "2026-05-01",     # ISO date du dernier /daily/login
    "streak": 3,                          # Jour en cours dans le cycle 1-7
    "missions_claimed": ["build_ship"],   # IDs des missions réclamées aujourd'hui
    "missions_progress": {}               # Progression par mission_id
  }
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0003_add_player_daily_data'
down_revision = '0002_seed_scar_tags'  # ← valeur exacte
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "players",
        sa.Column(
            "daily_data",
            JSONB,
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("players", "daily_data")
