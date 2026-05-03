"""
app/schemas/modules.py
Schémas Pydantic pour le système d'inventaire de modules (Phase 1).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Inventaire ────────────────────────────────────────────────────────────────

class PlayerModuleOut(BaseModel):
    id: UUID
    module_type: str
    level: int
    # Traits
    trait: str | None
    trait_value: float | None
    bonus_trait: str | None
    bonus_trait_value: float | None
    bonus_trait_2: str | None
    bonus_trait_2_value: float | None
    trait_slots_used: int
    # Corruption
    is_corrupted: bool
    corruption_malus_stat: str | None
    corruption_malus_value: float | None
    # Durabilité
    reinstall_charges: int
    is_destroyed: bool
    # Source
    obtained_from: str
    memory_ship_name: str | None
    memory_battle_ref: str | None
    obtained_at: datetime

    model_config = {"from_attributes": True}


# ── Loot Crates ──────────────────────────────────────────────────────────────

class LootCrateOut(BaseModel):
    id: UUID
    crate_type: str
    source: str
    source_ship_name: str | None
    opened: bool
    obtained_at: datetime

    model_config = {"from_attributes": True}


class LootCrateOpenResult(BaseModel):
    crate_id: UUID
    module: PlayerModuleOut | None
    shards: int
    empty: bool


# ── Artisanat ─────────────────────────────────────────────────────────────────

class CraftModuleRequest(BaseModel):
    module_ids: list[UUID] = Field(..., min_length=3, max_length=3)
    planet_id: UUID


# ── Installation depuis inventaire ───────────────────────────────────────────

class InstallModuleFromInventoryRequest(BaseModel):
    module_id: UUID


# ── Shards ───────────────────────────────────────────────────────────────────

class ShardCountOut(BaseModel):
    shards: dict[str, int]
