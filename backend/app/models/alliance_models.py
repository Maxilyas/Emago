"""
app/models/alliance_models.py
Agent 7 — Développeur Base de données | Sprint 4

Modèles SQLAlchemy pour les tables alliances (extension).
Importer dans models.py ou directement dans les services.

Note : AllianceMember et AllianceWar sont des NOUVELLES tables.
Le modèle Alliance existant dans models.py est étendu via relationship.
"""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint, ForeignKey, Index, Numeric,
    String, Text, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.models.models import Base  # réutiliser la Base commune


class AllianceRole(str, enum.Enum):
    LEADER  = "LEADER"
    OFFICER = "OFFICER"
    MEMBER  = "MEMBER"


class WarStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PEACE  = "PEACE"


class AllianceMember(Base):
    """
    Table de jonction Joueur ↔ Alliance avec rôle.
    Un joueur ne peut appartenir qu'à une seule alliance (UNIQUE player_id).
    """
    __tablename__ = "alliance_members"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    alliance_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("alliances.id", ondelete="CASCADE"), nullable=False
    )
    player_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False, default=AllianceRole.MEMBER)
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("player_id", name="uq_alliance_members_player"),
        CheckConstraint("role IN ('LEADER', 'OFFICER', 'MEMBER')", name="ck_alliance_member_role"),
        Index("idx_alliance_members_alliance", "alliance_id"),
        Index("idx_alliance_members_player", "player_id"),
    )


class AllianceWar(Base):
    """
    Guerre déclarée entre deux alliances.
    Une guerre ACTIVE donne un bonus XP ×1.5 aux combats entre membres.
    """
    __tablename__ = "alliance_wars"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    attacker_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("alliances.id", ondelete="CASCADE"), nullable=False
    )
    defender_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("alliances.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default=WarStatus.ACTIVE)
    declared_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    peace_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # GDD §alliances : bonus XP ×1.5 en guerre (configurable)
    xp_bonus: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False, default=Decimal("1.5"))

    __table_args__ = (
        CheckConstraint("attacker_id != defender_id", name="ck_war_different_alliances"),
        CheckConstraint("status IN ('ACTIVE', 'PEACE')", name="ck_war_status"),
        Index("idx_alliance_wars_attacker", "attacker_id"),
        Index("idx_alliance_wars_defender", "defender_id"),
    )
