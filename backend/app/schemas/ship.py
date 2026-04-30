"""
app/schemas/ship.py
Schémas Pydantic pour les endpoints /ships et /ships/{id}/modules.
Tous les noms de champs correspondent exactement à models.py (Agent 7).
"""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class BuildShipRequest(BaseModel):
    ship_type: str = Field(..., examples=["frigate_attack"])
    planet_id: UUID
    parent_ship_id: UUID | None = None   # Pedigree optionnel


class InstallModuleRequest(BaseModel):
    module_type: str = Field(..., examples=["CANNON"])
    level: int = Field(..., ge=1, le=5)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class BaseStatsOut(BaseModel):
    hull: int
    shield: int
    dps: int
    speed: float
    cargo: int
    stealth: float
    support_aura: float


class ModuleDetailOut(BaseModel):
    slot: int
    type: str
    level: int
    affinity_bonus: bool
    boost_applied: float   # en %


class CurrentStatsOut(BaseModel):
    hull: int
    shield: int
    dps: int
    speed: float
    cargo: int
    stealth: float
    support_aura: float
    grade: int
    grade_bonus_pct: float
    shield_regen_per_round: float
    cap_reached: list[str]
    modules: list[ModuleDetailOut]
    slots_total: int
    slots_premium: int


class ShipSummaryOut(BaseModel):
    """Utilisé dans la liste hangar (GET /ships)."""
    id: UUID
    ship_type: str
    ship_class: str   # valeur de l'enum ShipClass
    rarity: str
    grade: int
    status: str
    planet_id: UUID | None

    model_config = {"from_attributes": True}


class ShipDetailOut(BaseModel):
    """Détail complet d'un vaisseau (GET /ships/{id})."""
    id: UUID
    ship_type: str
    ship_class: str
    rarity: str
    grade: int
    combat_xp: int
    status: str
    parent_ship_id: UUID | None
    base_stats: BaseStatsOut
    current_stats: CurrentStatsOut   # calculé par ship_stats_service, jamais stocké

    model_config = {"from_attributes": True}


class BuildShipResponse(BaseModel):
    ship_id: UUID
    rarity: str
    ship_class: str
    base_stats: BaseStatsOut
    slots_total: int
    slots_premium: int
    pedigree_applied: bool


class ModuleInstallResponse(BaseModel):
    current_stats: CurrentStatsOut
    cap_reached: list[str]
