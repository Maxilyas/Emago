"""
alembic/versions/0009_module_inventory.py

Phase 1 du système d'économie des modules :
  - Table player_modules  : inventaire des modules avec traits, charges, mémoire
  - Table loot_crates     : boîtes de butin fermées
  - ship_modules          : ajout colonne player_module_id (FK nullable)
  - players               : ajout colonne module_shards (JSONB, default {})
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID

revision = "0009_module_inventory"
down_revision = "0008_ship_status_scrapped"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. player_modules ────────────────────────────────────────────────
    op.create_table(
        "player_modules",
        sa.Column("id",          PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("player_id",   PG_UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("module_type", sa.String(32),   nullable=False),
        sa.Column("level",       sa.SmallInteger, nullable=False),
        # traits
        sa.Column("trait",               sa.String(32),  nullable=True),
        sa.Column("trait_value",         sa.Float,       nullable=True),
        sa.Column("bonus_trait",         sa.String(32),  nullable=True),
        sa.Column("bonus_trait_value",   sa.Float,       nullable=True),
        sa.Column("bonus_trait_2",       sa.String(32),  nullable=True),
        sa.Column("bonus_trait_2_value", sa.Float,       nullable=True),
        sa.Column("trait_slots_used",    sa.SmallInteger, nullable=False, server_default="0"),
        # corruption
        sa.Column("is_corrupted",           sa.Boolean, nullable=False, server_default="false"),
        sa.Column("corruption_malus_stat",  sa.String(32), nullable=True),
        sa.Column("corruption_malus_value", sa.Float,      nullable=True),
        # durabilité
        sa.Column("reinstall_charges", sa.SmallInteger, nullable=False),
        sa.Column("is_destroyed",      sa.Boolean, nullable=False, server_default="false"),
        # source
        sa.Column("obtained_from",     sa.String(32), nullable=False),
        sa.Column("memory_ship_name",  sa.String(64), nullable=True),
        sa.Column("memory_battle_ref", sa.String(64), nullable=True),
        sa.Column("obtained_at", TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        # contraintes
        sa.CheckConstraint("level BETWEEN 1 AND 5",         name="ck_player_module_level"),
        sa.CheckConstraint("reinstall_charges >= 0",         name="ck_player_module_charges"),
        sa.CheckConstraint("trait_slots_used BETWEEN 0 AND 3", name="ck_player_module_trait_slots"),
    )
    op.create_index(
        "idx_player_modules_player", "player_modules", ["player_id"],
        postgresql_where=sa.text("is_destroyed = FALSE"),
    )

    # ── 2. loot_crates ───────────────────────────────────────────────────
    op.create_table(
        "loot_crates",
        sa.Column("id",         PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("player_id",  PG_UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("crate_type", sa.String(16), nullable=False),
        sa.Column("source",     sa.String(16), nullable=False),
        sa.Column("source_ship_name", sa.String(64), nullable=True),
        sa.Column("source_battle_id", sa.String(64), nullable=True),
        sa.Column("opened",    sa.Boolean, nullable=False, server_default="false"),
        sa.Column("opened_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("result_module_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("player_modules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("shards_awarded", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("obtained_at", TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index(
        "idx_loot_crates_player_unopened", "loot_crates", ["player_id"],
        postgresql_where=sa.text("opened = FALSE"),
    )

    # ── 3. ship_modules : ajouter player_module_id ───────────────────────
    op.add_column(
        "ship_modules",
        sa.Column(
            "player_module_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("player_modules.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── 4. players : ajouter module_shards ───────────────────────────────
    op.add_column(
        "players",
        sa.Column("module_shards", JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("players", "module_shards")
    op.drop_column("ship_modules", "player_module_id")
    op.drop_index("idx_loot_crates_player_unopened", table_name="loot_crates")
    op.drop_table("loot_crates")
    op.drop_index("idx_player_modules_player", table_name="player_modules")
    op.drop_table("player_modules")
