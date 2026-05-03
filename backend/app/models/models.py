"""
Emago — Modèles SQLAlchemy 2.0 (mode async)
Correspondent 1:1 au schéma schema.sql
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Base declarative
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Base commune pour tous les modèles Emago."""
    type_annotation_map = {
        dict: JSONB,
        list: JSONB,
    }


# ---------------------------------------------------------------------------
# Enums Python (miroirs des enums PostgreSQL)
# ---------------------------------------------------------------------------

class ShipClass(str, enum.Enum):
    ATTACK = "ATTACK"
    DEFENSE = "DEFENSE"
    SUPPORT = "SUPPORT"
    EXPLORATION = "EXPLORATION"


class ShipRarity(str, enum.Enum):
    COMMON = "COMMON"
    UNCOMMON = "UNCOMMON"
    RARE = "RARE"
    EPIC = "EPIC"
    LEGENDARY = "LEGENDARY"


class ShipStatus(str, enum.Enum):
    DOCKED = "DOCKED"
    IN_FLEET = "IN_FLEET"
    IN_FORGE = "IN_FORGE"
    SCRAPPED = "SCRAPPED"


class ModuleFamily(str, enum.Enum):
    PROPELLER = "PROPELLER"
    ARMOR = "ARMOR"
    CANNON = "CANNON"
    EMITTER = "EMITTER"
    SHIELD = "SHIELD"
    CARGO = "CARGO"


class FleetMission(str, enum.Enum):
    ATTACK = "ATTACK"
    TRANSPORT = "TRANSPORT"
    ESPIONAGE = "ESPIONAGE"
    COLONIZE = "COLONIZE"
    RECALL = "RECALL"


# ---------------------------------------------------------------------------
# TABLE : alliances  (déclarée avant players pour la FK)
# ---------------------------------------------------------------------------

class Alliance(Base):
    __tablename__ = "alliances"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    tag: Mapped[str] = mapped_column(String(8), nullable=False, unique=True)
    leader_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("players.id", use_alter=True), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    members: Mapped[list["Player"]] = relationship(
        "Player", back_populates="alliance", foreign_keys="Player.alliance_id"
    )
    leader: Mapped["Player"] = relationship(
        "Player", foreign_keys=[leader_id], post_update=True
    )


# ---------------------------------------------------------------------------
# TABLE : players
# ---------------------------------------------------------------------------

class Player(Base):
    __tablename__ = "players"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    username: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    alliance_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("alliances.id", use_alter=True, ondelete="SET NULL"),
    )

    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    refresh_token: Mapped[str | None] = mapped_column(Text)
    refresh_token_expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    daily_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    alliance: Mapped["Alliance | None"] = relationship(
        "Alliance", back_populates="members", foreign_keys=[alliance_id]
    )
    ships: Mapped[list["Ship"]] = relationship("Ship", back_populates="owner")
    planets: Mapped[list["Planet"]] = relationship("Planet", back_populates="owner")
    fleets: Mapped[list["Fleet"]] = relationship("Fleet", back_populates="owner")

    __table_args__ = (
        Index("idx_players_score", score.desc()),
    )


# ---------------------------------------------------------------------------
# TABLE : planets
# ---------------------------------------------------------------------------

class Planet(Base):
    __tablename__ = "planets"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL")
    )
    galaxy: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    system: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="Planète sans nom")
    is_homeworld: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Ressources
    metal: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=500)
    crystal: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=300)
    deuterium: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=100)
    metal_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    crystal_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    deut_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)
    resources_last_updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    buildings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    owner: Mapped["Player | None"] = relationship("Player", back_populates="planets")
    ships: Mapped[list["Ship"]] = relationship("Ship", back_populates="planet")
    build_queue: Mapped[list["BuildQueue"]] = relationship("BuildQueue", back_populates="planet")

    __table_args__ = (
        UniqueConstraint("galaxy", "system", "position", name="uq_planet_coordinates"),
        CheckConstraint("galaxy BETWEEN 1 AND 9", name="ck_planet_galaxy"),
        CheckConstraint("system BETWEEN 1 AND 499", name="ck_planet_system"),
        CheckConstraint("position BETWEEN 1 AND 15", name="ck_planet_position"),
        Index("idx_planets_owner", "owner_id"),
    )


# ---------------------------------------------------------------------------
# TABLE : build_queue
# ---------------------------------------------------------------------------

class BuildQueue(Base):
    __tablename__ = "build_queue"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    planet_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("planets.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(16), nullable=False)
    item_name: Mapped[str] = mapped_column(String(64), nullable=False)
    target_level: Mapped[int | None] = mapped_column(SmallInteger)
    cost_metal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_crystal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_deuterium: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    completes_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    planet: Mapped["Planet"] = relationship("Planet", back_populates="build_queue")

    __table_args__ = (
        CheckConstraint("item_type IN ('BUILDING', 'RESEARCH', 'SHIP')", name="ck_build_item_type"),
        # Index partiel : ignore les éléments terminés — scheduler n'itère que sur pending
        Index("idx_build_queue_planet_pending", "planet_id", "completes_at",
              postgresql_where=text("completed = FALSE")),
    )


# ---------------------------------------------------------------------------
# TABLE : technologies
# ---------------------------------------------------------------------------

class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    player_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tech_levels: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )


# ---------------------------------------------------------------------------
# TABLE : scar_tags
# ---------------------------------------------------------------------------

class ScarTag(Base):
    __tablename__ = "scar_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tag_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)


# ---------------------------------------------------------------------------
# TABLE : ships  ⭐
# ---------------------------------------------------------------------------

class Ship(Base):
    __tablename__ = "ships"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    planet_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("planets.id", ondelete="SET NULL")
    )

    ship_type: Mapped[str] = mapped_column(String(64), nullable=False)
    class_: Mapped[ShipClass] = mapped_column("class", String, nullable=False)
    rarity: Mapped[ShipRarity] = mapped_column(String, nullable=False)
    status: Mapped[ShipStatus] = mapped_column(String, nullable=False, default=ShipStatus.DOCKED)

    grade: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    combat_xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # IMMUABLE — protégé par trigger PostgreSQL prevent_base_stats_update
    base_stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    parent_ship_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ships.id", ondelete="SET NULL")
    )
    pedigree_bonus: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    grade4_immunity_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grade4_immunity_reset_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # ── Champs RPG narratifs — Sprint 1.1 ─────────────────────────────────
    # Nom procédural (RARE+) — ex: "Astraeus Noir". NULL pour COMMON/UNCOMMON.
    name: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Nom procédural généré à la construction pour RARE+"
    )

    # Trait narratif — tiré à la construction pour tous les vaisseaux.
    # Format JSONB : {"key": "bounty_hunter", "name": "...", "description": "..."}
    # NULL pour les vaisseaux antérieurs à la migration 0006.
    trait: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment={"key": str, "name": str, "description": str}
    )

    # Drapeau Dérive — True uniquement pour les vaisseaux issus d\'une Forge Dérive.
    # Affiché distinctement dans l\'UI (badge violet pâle, bordure en pointillé).
    is_drift: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"),
        comment="True si issu d\'une Forge Dérive (5% chance)"
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    owner: Mapped["Player"] = relationship("Player", back_populates="ships")
    planet: Mapped["Planet | None"] = relationship("Planet", back_populates="ships")
    modules: Mapped[list["ShipModule"]] = relationship(
        "ShipModule", back_populates="ship", cascade="all, delete-orphan"
    )
    scars: Mapped[list["ShipScar"]] = relationship(
        "ShipScar", back_populates="ship", cascade="all, delete-orphan"
    )
    missions: Mapped[list["ShipMission"]] = relationship(
        "ShipMission", back_populates="ship", cascade="all, delete-orphan"
    )
    parent: Mapped["Ship | None"] = relationship("Ship", remote_side="Ship.id", foreign_keys=[parent_ship_id])

    __table_args__ = (
        CheckConstraint("grade BETWEEN 0 AND 5", name="ck_ship_grade"),
        CheckConstraint("combat_xp >= 0", name="ck_ship_xp_positive"),
        # Requête la plus fréquente : hangar actif d'un joueur
        Index("idx_ships_owner_status", "owner_id", "status"),
        Index("idx_ships_owner_planet", "owner_id", "planet_id"),
        Index("idx_ships_rarity", "rarity"),
    )


# ---------------------------------------------------------------------------
# TABLE : ship_modules
# ---------------------------------------------------------------------------

class ShipModule(Base):
    __tablename__ = "ship_modules"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    ship_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ships.id", ondelete="CASCADE"), nullable=False
    )
    slot_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    module_type: Mapped[ModuleFamily] = mapped_column(String, nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    affinity_bonus: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    installed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    ship: Mapped["Ship"] = relationship("Ship", back_populates="modules")

    __table_args__ = (
        CheckConstraint("slot_index BETWEEN 0 AND 5", name="ck_module_slot_index"),
        CheckConstraint("level BETWEEN 1 AND 5", name="ck_module_level"),
        UniqueConstraint("ship_id", "slot_index", name="uq_ship_module_slot"),
        # CRITIQUE : appelé à chaque calcul de current_stats
        Index("idx_ship_modules_ship_id", "ship_id"),
    )


# ---------------------------------------------------------------------------
# TABLE : forge_queue
# ---------------------------------------------------------------------------

class ForgeQueue(Base):
    __tablename__ = "forge_queue"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    player_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    ship_a_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ships.id"), nullable=False
    )
    ship_b_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ships.id"), nullable=False
    )
    cost_metal: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_crystal: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_deuterium: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    completed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("now() + INTERVAL '8 hours'"),
    )
    result_ship_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ships.id", ondelete="SET NULL")
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    ship_a: Mapped["Ship"] = relationship("Ship", foreign_keys=[ship_a_id])
    ship_b: Mapped["Ship"] = relationship("Ship", foreign_keys=[ship_b_id])
    result_ship: Mapped["Ship | None"] = relationship("Ship", foreign_keys=[result_ship_id])

    __table_args__ = (
        CheckConstraint("ship_a_id != ship_b_id", name="ck_forge_ships_distinct"),
        # ⚠ CRITIQUE : utilisé par APScheduler toutes les 60s
        Index(
            "idx_forge_queue_completed_at", "completed_at",
            postgresql_where=text("is_completed = FALSE"),
        ),
        Index(
            "idx_forge_queue_player", "player_id",
            postgresql_where=text("is_completed = FALSE"),
        ),
    )


# ---------------------------------------------------------------------------
# TABLE : ship_scars
# ---------------------------------------------------------------------------

class ShipScar(Base):
    __tablename__ = "ship_scars"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    ship_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ships.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("scar_tags.id"), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relationships
    ship: Mapped["Ship"] = relationship("Ship", back_populates="scars")
    tag: Mapped["ScarTag"] = relationship("ScarTag")

    __table_args__ = (
        UniqueConstraint("ship_id", "tag_id", name="uq_ship_scar_tag"),
        Index("idx_ship_scars_ship", "ship_id"),
    )


# ---------------------------------------------------------------------------
# TABLE : ship_missions
# ---------------------------------------------------------------------------

class ShipMission(Base):
    __tablename__ = "ship_missions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    ship_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("ships.id", ondelete="CASCADE"), nullable=False
    )
    mission_type: Mapped[str] = mapped_column(String(64), nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    progress: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    reward: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    reward_claimed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    ship: Mapped["Ship"] = relationship("Ship", back_populates="missions")

    __table_args__ = (
        Index(
            "idx_ship_missions_ship_expires", "ship_id", "expires_at",
            postgresql_where=text("completed = FALSE"),
        ),
    )


# ---------------------------------------------------------------------------
# TABLE : fleets
# ---------------------------------------------------------------------------

class Fleet(Base):
    __tablename__ = "fleets"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    origin_planet_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("planets.id"), nullable=False
    )
    target_planet_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("planets.id")
    )
    target_galaxy: Mapped[int | None] = mapped_column(SmallInteger)
    target_system: Mapped[int | None] = mapped_column(SmallInteger)
    target_position: Mapped[int | None] = mapped_column(SmallInteger)

    mission: Mapped[FleetMission] = mapped_column(String, nullable=False)

    cargo_metal: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    cargo_crystal: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    cargo_deuterium: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)

    departed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    arrives_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    return_arrives_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    is_returning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_recalled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    owner: Mapped["Player"] = relationship("Player", back_populates="fleets")
    ships: Mapped[list["Ship"]] = relationship(
        "Ship", secondary="fleet_ships", viewonly=True
    )

    __table_args__ = (
        Index(
            "idx_fleets_arrives_at", "arrives_at",
            postgresql_where=text("is_recalled = FALSE"),
        ),
        Index("idx_fleets_owner", "owner_id"),
    )


# ---------------------------------------------------------------------------
# TABLE : fleet_ships  (association)
# ---------------------------------------------------------------------------

fleet_ships = Table(
    "fleet_ships",
    Base.metadata,
    Column("fleet_id", PG_UUID(as_uuid=True), ForeignKey("fleets.id", ondelete="CASCADE"), primary_key=True),
    Column("ship_id", PG_UUID(as_uuid=True), ForeignKey("ships.id", ondelete="CASCADE"), primary_key=True),
)


# ---------------------------------------------------------------------------
# TABLE : combat_logs
# ---------------------------------------------------------------------------

class CombatLog(Base):
    __tablename__ = "combat_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    fleet_attacker_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fleets.id"), nullable=False
    )
    fleet_defender_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fleets.id")
    )
    defender_planet_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("planets.id")
    )

    outcome: Mapped[str] = mapped_column(String(16), nullable=False)

    pillaged_metal: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    pillaged_crystal: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)
    pillaged_deuterium: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False, default=0)

    rounds_log: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    attacker_ships_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    defender_ships_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    attacker_power: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    defender_power: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    fought_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('ATTACKER_WIN', 'DEFENDER_WIN', 'DRAW')",
            name="ck_combat_outcome",
        ),
        Index("idx_combat_logs_attacker", "fleet_attacker_id", "fought_at"),
        Index(
            "idx_combat_logs_attacker_snapshot",
            "attacker_ships_snapshot",
            postgresql_using="gin",
            postgresql_ops={"attacker_ships_snapshot": "jsonb_path_ops"},
        ),
        Index(
            "idx_combat_logs_defender_snapshot",
            "defender_ships_snapshot",
            postgresql_using="gin",
            postgresql_ops={"defender_ships_snapshot": "jsonb_path_ops"},
        ),
    )
