"""
app/schemas/forge.py
Schémas Pydantic pour les endpoints /forge.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ForgeStartRequest(BaseModel):
    ship_a_id: UUID
    ship_b_id: UUID


class ForgeStatusResponse(BaseModel):
    forge_id: UUID
    completed_at: datetime
    progress_pct: int
    eta_seconds: int
    result_ship_id: UUID | None = None


class ForgeHistoryItem(BaseModel):
    forge_id: UUID
    ship_a_id: UUID
    ship_b_id: UUID
    result_ship_id: UUID | None
    started_at: datetime
    completed_at: datetime
    is_completed: bool

    model_config = {"from_attributes": True}
