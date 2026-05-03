from __future__ import annotations
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, Integer, JSON, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.models import Base


class GhostShip(Base):
    __tablename__ = "ghost_ships"

    id:           Mapped[UUID]           = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    galaxy:       Mapped[int]            = mapped_column(SmallInteger, nullable=False)
    system:       Mapped[int]            = mapped_column(SmallInteger, nullable=False)
    name:         Mapped[str]            = mapped_column(String(64), nullable=False)
    ship_type:    Mapped[str]            = mapped_column(String(64), nullable=False)
    rarity:       Mapped[str]            = mapped_column(String(32), nullable=False, server_default="'COMMON'")
    threat_level: Mapped[int]            = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    current_hull: Mapped[int]            = mapped_column(Integer, nullable=False)
    max_hull:     Mapped[int]            = mapped_column(Integer, nullable=False)
    base_stats:   Mapped[dict]           = mapped_column(JSON, nullable=False)
    is_defeated:  Mapped[bool]           = mapped_column(Boolean, nullable=False, server_default=text("false"))
    defeated_at:  Mapped[datetime | None]= mapped_column(TIMESTAMP(timezone=True), nullable=True)
    respawn_at:   Mapped[datetime | None]= mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at:   Mapped[datetime]       = mapped_column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
