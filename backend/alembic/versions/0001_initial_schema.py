"""Initial migration — schéma complet Emago v1.0

Revision ID: 0001_initial_schema
Revises: —
Create Date: 2025-01-29

Ce script crée l'intégralité du schéma : enums, tables, triggers, index.
Il est idempotent grâce aux IF NOT EXISTS.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Métadonnées Alembic
# ---------------------------------------------------------------------------
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crée le schéma complet Emago."""

    # ------------------------------------------------------------------
    # EXTENSIONS
    # ------------------------------------------------------------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

    # ------------------------------------------------------------------
    # ENUMS PostgreSQL
    # ------------------------------------------------------------------
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ship_class AS ENUM (
                'ATTACK', 'DEFENSE', 'SUPPORT', 'EXPLORATION'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ship_rarity AS ENUM (
                'COMMON', 'UNCOMMON', 'RARE', 'EPIC', 'LEGENDARY'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ship_status AS ENUM (
                'DOCKED', 'IN_FLEET', 'IN_FORGE'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE module_family AS ENUM (
                'PROPELLER', 'ARMOR', 'CANNON', 'EMITTER', 'SHIELD', 'CARGO'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fleet_mission AS ENUM (
                'ATTACK', 'TRANSPORT', 'ESPIONAGE', 'COLONIZE', 'RECALL'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ------------------------------------------------------------------
    # TABLE : alliances  (avant players — FK circulaire)
    # ------------------------------------------------------------------
    op.create_table(
        "alliances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("tag", sa.String(8), nullable=False),
        # leader_id FK ajoutée après players via ADD CONSTRAINT
        sa.Column("leader_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("score", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_alliance_name"),
        sa.UniqueConstraint("tag", name="uq_alliance_tag"),
    )
    op.create_index("idx_alliances_score", "alliances", [sa.text("score DESC")])

    # ------------------------------------------------------------------
    # TABLE : players
    # ------------------------------------------------------------------
    op.create_table(
        "players",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(32), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("score", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("alliance_id", postgresql.UUID(as_uuid=True)),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("refresh_token", sa.Text),
        sa.Column("refresh_token_expires_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("username", name="uq_player_username"),
        sa.UniqueConstraint("email", name="uq_player_email"),
    )
    op.create_index("idx_players_score", "players", [sa.text("score DESC")])

    # FK circulaires players ↔ alliances
    op.create_foreign_key(
        "fk_alliance_leader", "alliances", "players",
        ["leader_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_player_alliance", "players", "alliances",
        ["alliance_id"], ["id"], ondelete="SET NULL"
    )

    # ------------------------------------------------------------------
    # TABLE : scar_tags  (avant ship_scars)
    # ------------------------------------------------------------------
    op.create_table(
        "scar_tags",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("tag_code", sa.String(64), nullable=False),
        sa.Column("narrative", sa.Text, nullable=False),
        sa.UniqueConstraint("tag_code", name="uq_scar_tag_code"),
    )

    # ------------------------------------------------------------------
    # TABLE : planets
    # ------------------------------------------------------------------
    op.create_table(
        "planets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="SET NULL")),
        sa.Column("galaxy", sa.SmallInteger, nullable=False),
        sa.Column("system", sa.SmallInteger, nullable=False),
        sa.Column("position", sa.SmallInteger, nullable=False),
        sa.Column("name", sa.String(64), nullable=False, server_default="Planète sans nom"),
        sa.Column("is_homeworld", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("metal", sa.Numeric(16, 2), nullable=False, server_default="500"),
        sa.Column("crystal", sa.Numeric(16, 2), nullable=False, server_default="300"),
        sa.Column("deuterium", sa.Numeric(16, 2), nullable=False, server_default="100"),
        sa.Column("metal_capacity", sa.Integer, nullable=False, server_default="10000"),
        sa.Column("crystal_capacity", sa.Integer, nullable=False, server_default="10000"),
        sa.Column("deut_capacity", sa.Integer, nullable=False, server_default="5000"),
        sa.Column("resources_last_updated_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("buildings", postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("galaxy", "system", "position", name="uq_planet_coordinates"),
        sa.CheckConstraint("galaxy BETWEEN 1 AND 9", name="ck_planet_galaxy"),
        sa.CheckConstraint("system BETWEEN 1 AND 499", name="ck_planet_system"),
        sa.CheckConstraint("position BETWEEN 1 AND 15", name="ck_planet_position"),
    )
    op.create_index("idx_planets_owner", "planets", ["owner_id"])

    # ------------------------------------------------------------------
    # TABLE : build_queue
    # ------------------------------------------------------------------
    op.create_table(
        "build_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("planet_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("planets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.String(16), nullable=False),
        sa.Column("item_name", sa.String(64), nullable=False),
        sa.Column("target_level", sa.SmallInteger),
        sa.Column("cost_metal", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_crystal", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_deuterium", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completes_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.CheckConstraint(
            "item_type IN ('BUILDING', 'RESEARCH', 'SHIP')",
            name="ck_build_item_type"
        ),
    )
    op.create_index(
        "idx_build_queue_planet_pending", "build_queue",
        ["planet_id", "completes_at"],
        postgresql_where=sa.text("completed = FALSE"),
    )

    # ------------------------------------------------------------------
    # TABLE : technologies
    # ------------------------------------------------------------------
    op.create_table(
        "technologies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("tech_levels", postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # ------------------------------------------------------------------
    # TABLE : ships  ⭐
    # ------------------------------------------------------------------
    op.create_table(
        "ships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("planet_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("planets.id", ondelete="SET NULL")),
        sa.Column("ship_type", sa.String(64), nullable=False),
        sa.Column("class", sa.String, nullable=False),        # enum ship_class
        sa.Column("rarity", sa.String, nullable=False),       # enum ship_rarity
        sa.Column("status", sa.String, nullable=False,        # enum ship_status
                  server_default="'DOCKED'"),
        sa.Column("grade", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("combat_xp", sa.Integer, nullable=False, server_default="0"),
        sa.Column("base_stats", postgresql.JSONB, nullable=False),
        sa.Column("parent_ship_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id", ondelete="SET NULL")),
        sa.Column("pedigree_bonus", postgresql.JSONB),
        sa.Column("grade4_immunity_active", sa.Boolean, nullable=False,
                  server_default="FALSE"),
        sa.Column("grade4_immunity_reset_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("grade BETWEEN 0 AND 5", name="ck_ship_grade"),
        sa.CheckConstraint("combat_xp >= 0", name="ck_ship_xp_positive"),
    )
    op.create_index("idx_ships_owner_status", "ships", ["owner_id", "status"])
    op.create_index("idx_ships_owner_planet", "ships", ["owner_id", "planet_id"])
    op.create_index("idx_ships_rarity", "ships", ["rarity"])

    # ------------------------------------------------------------------
    # TRIGGER : prevent_base_stats_update
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_base_stats_update()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $func$
        BEGIN
            -- Bypass pour les migrations Alembic contrôlées :
            -- SET LOCAL emago.bypass_stats_trigger = 'true';
            IF current_setting('emago.bypass_stats_trigger', true) = 'true' THEN
                RETURN NEW;
            END IF;

            IF NEW.base_stats IS DISTINCT FROM OLD.base_stats THEN
                RAISE EXCEPTION
                    'VIOLATION INTÉGRITÉ : base_stats est immuable pour le vaisseau % (owner: %). '
                    'Pour une migration contrôlée, utilisez : SET LOCAL emago.bypass_stats_trigger = ''true'';',
                    OLD.id, OLD.owner_id
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;

            RETURN NEW;
        END;
        $func$
    """)

    op.execute("""
        CREATE TRIGGER trg_ships_prevent_base_stats_update
            BEFORE UPDATE ON ships
            FOR EACH ROW
            EXECUTE FUNCTION prevent_base_stats_update()
    """)

    # ------------------------------------------------------------------
    # TRIGGER : updated_at automatique
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $func$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $func$
    """)

    op.execute("""
        CREATE TRIGGER trg_ships_updated_at
            BEFORE UPDATE ON ships
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at()
    """)

    # ------------------------------------------------------------------
    # TABLE : ship_modules
    # ------------------------------------------------------------------
    op.create_table(
        "ship_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ship_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot_index", sa.SmallInteger, nullable=False),
        sa.Column("module_type", sa.String, nullable=False),  # enum module_family
        sa.Column("level", sa.SmallInteger, nullable=False),
        sa.Column("affinity_bonus", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("installed_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("slot_index BETWEEN 0 AND 5", name="ck_module_slot_index"),
        sa.CheckConstraint("level BETWEEN 1 AND 5", name="ck_module_level"),
        sa.UniqueConstraint("ship_id", "slot_index", name="uq_ship_module_slot"),
    )
    # CRITIQUE : requête systématique au calcul de current_stats
    op.create_index("idx_ship_modules_ship_id", "ship_modules", ["ship_id"])

    # ------------------------------------------------------------------
    # TABLE : forge_queue
    # ------------------------------------------------------------------
    op.create_table(
        "forge_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("player_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ship_a_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id"), nullable=False),
        sa.Column("ship_b_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id"), nullable=False),
        sa.Column("cost_metal", sa.Integer, nullable=False),
        sa.Column("cost_crystal", sa.Integer, nullable=False),
        sa.Column("cost_deuterium", sa.Integer, nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now() + INTERVAL '8 hours'")),
        sa.Column("result_ship_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id", ondelete="SET NULL")),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.CheckConstraint("ship_a_id != ship_b_id", name="ck_forge_ships_distinct"),
    )
    # ⚠ INDEX CRITIQUE — APScheduler toutes les 60s
    op.create_index(
        "idx_forge_queue_completed_at", "forge_queue", ["completed_at"],
        postgresql_where=sa.text("is_completed = FALSE"),
    )
    op.create_index(
        "idx_forge_queue_player", "forge_queue", ["player_id"],
        postgresql_where=sa.text("is_completed = FALSE"),
    )

    # ------------------------------------------------------------------
    # TABLE : ship_scars
    # ------------------------------------------------------------------
    op.create_table(
        "ship_scars",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ship_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Integer,
                  sa.ForeignKey("scar_tags.id"), nullable=False),
        sa.Column("earned_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("ship_id", "tag_id", name="uq_ship_scar_tag"),
    )
    op.create_index("idx_ship_scars_ship", "ship_scars", ["ship_id"])

    # ------------------------------------------------------------------
    # TABLE : ship_missions
    # ------------------------------------------------------------------
    op.create_table(
        "ship_missions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ship_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_type", sa.String(64), nullable=False),
        sa.Column("condition", postgresql.JSONB, nullable=False),
        sa.Column("progress", postgresql.JSONB, nullable=False,
                  server_default='{}'),
        sa.Column("reward", postgresql.JSONB, nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("reward_claimed", sa.Boolean, nullable=False, server_default="FALSE"),
    )
    op.create_index(
        "idx_ship_missions_ship_expires", "ship_missions",
        ["ship_id", "expires_at"],
        postgresql_where=sa.text("completed = FALSE"),
    )

    # ------------------------------------------------------------------
    # TABLE : fleets
    # ------------------------------------------------------------------
    op.create_table(
        "fleets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("origin_planet_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("planets.id"), nullable=False),
        sa.Column("target_planet_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("planets.id")),
        sa.Column("target_galaxy", sa.SmallInteger),
        sa.Column("target_system", sa.SmallInteger),
        sa.Column("target_position", sa.SmallInteger),
        sa.Column("mission", sa.String, nullable=False),  # enum fleet_mission
        sa.Column("cargo_metal", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("cargo_crystal", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("cargo_deuterium", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("departed_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("arrives_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("return_arrives_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_returning", sa.Boolean, nullable=False, server_default="FALSE"),
        sa.Column("is_recalled", sa.Boolean, nullable=False, server_default="FALSE"),
    )
    op.create_index(
        "idx_fleets_arrives_at", "fleets", ["arrives_at"],
        postgresql_where=sa.text("is_recalled = FALSE"),
    )
    op.create_index("idx_fleets_owner", "fleets", ["owner_id"])

    # ------------------------------------------------------------------
    # TABLE : fleet_ships  (table d'association)
    # ------------------------------------------------------------------
    op.create_table(
        "fleet_ships",
        sa.Column("fleet_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fleets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ship_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ships.id", ondelete="CASCADE"), primary_key=True),
    )

    # ------------------------------------------------------------------
    # TABLE : combat_logs
    # ------------------------------------------------------------------
    op.create_table(
        "combat_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("fleet_attacker_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fleets.id"), nullable=False),
        sa.Column("fleet_defender_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fleets.id")),
        sa.Column("defender_planet_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("planets.id")),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("pillaged_metal", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("pillaged_crystal", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("pillaged_deuterium", sa.Numeric(16, 2), nullable=False, server_default="0"),
        sa.Column("rounds_log", postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column("attacker_ships_snapshot", postgresql.JSONB, nullable=False,
                  server_default='[]'),
        sa.Column("defender_ships_snapshot", postgresql.JSONB, nullable=False,
                  server_default='[]'),
        sa.Column("attacker_power", sa.Numeric(12, 2), nullable=False),
        sa.Column("defender_power", sa.Numeric(12, 2), nullable=False),
        sa.Column("fought_at", sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "outcome IN ('ATTACKER_WIN', 'DEFENDER_WIN', 'DRAW')",
            name="ck_combat_outcome",
        ),
    )
    op.create_index(
        "idx_combat_logs_attacker", "combat_logs",
        ["fleet_attacker_id", sa.text("fought_at DESC")],
    )


def downgrade() -> None:
    """Supprime l'intégralité du schéma Emago.

    ⚠ DESTRUCTIF — à n'utiliser qu'en environnement de dev.
    En production, préférer une migration ciblée.
    """
    # Tables dans l'ordre inverse des dépendances
    op.drop_table("combat_logs")
    op.drop_table("fleet_ships")
    op.drop_table("fleets")
    op.drop_table("ship_missions")
    op.drop_table("ship_scars")
    op.drop_table("forge_queue")
    op.drop_table("ship_modules")

    # Trigger et fonction avant la table ships
    op.execute("DROP TRIGGER IF EXISTS trg_ships_prevent_base_stats_update ON ships")
    op.execute("DROP TRIGGER IF EXISTS trg_ships_updated_at ON ships")
    op.execute("DROP FUNCTION IF EXISTS prevent_base_stats_update()")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_table("ships")
    op.drop_table("technologies")
    op.drop_table("build_queue")
    op.drop_table("planets")
    op.drop_table("scar_tags")

    # FK circulaires avant drop des tables
    op.drop_constraint("fk_player_alliance", "players", type_="foreignkey")
    op.drop_constraint("fk_alliance_leader", "alliances", type_="foreignkey")
    op.drop_table("players")
    op.drop_table("alliances")

    # Enums
    op.execute("DROP TYPE IF EXISTS fleet_mission")
    op.execute("DROP TYPE IF EXISTS module_family")
    op.execute("DROP TYPE IF EXISTS ship_status")
    op.execute("DROP TYPE IF EXISTS ship_rarity")
    op.execute("DROP TYPE IF EXISTS ship_class")
