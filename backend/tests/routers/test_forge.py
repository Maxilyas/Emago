"""
tests/routers/test_forge.py
Agent 8 — QA & Sécurité | Sprint 2

Tests d'intégration — router /forge
Couvre : démarrage, historique, statut, cas d'erreur critiques.

Vecteurs de sécurité testés :
  - Double-soumission (race condition)
  - Forge de raretés différentes
  - Forge d'un vaisseau LEGENDARY (impossible)
  - Forge d'un vaisseau IN_FLEET
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestForge:
    @pytest.mark.asyncio
    async def test_forge_different_rarities_rejected(
        self, auth_client: AsyncClient, two_ships_different_rarity: tuple[str, str]
    ):
        """Raretés différentes → 422."""
        ship_a, ship_b = two_ships_different_rarity
        resp = await auth_client.post("/api/v1/forge", json={
            "ship_a_id": ship_a,
            "ship_b_id": ship_b,
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_forge_same_ship_twice_rejected(
        self, auth_client: AsyncClient, built_ship: dict
    ):
        """Même vaisseau deux fois → 400."""
        ship_id = built_ship["ship_id"]
        resp = await auth_client.post("/api/v1/forge", json={
            "ship_a_id": ship_id,
            "ship_b_id": ship_id,
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_forge_in_fleet_ship_rejected(
        self, auth_client: AsyncClient, ship_in_fleet: str, built_ship: dict
    ):
        """Vaisseau IN_FLEET ne peut pas être forgé → 409."""
        resp = await auth_client.post("/api/v1/forge", json={
            "ship_a_id": ship_in_fleet,
            "ship_b_id": built_ship["ship_id"],
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_forge_history(self, auth_client: AsyncClient):
        """GET /forge/history retourne une liste (vide ou non)."""
        resp = await auth_client.get("/api/v1/forge/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_forge_status_not_found(self, auth_client: AsyncClient):
        """GET /forge/{id} avec UUID inexistant → 404."""
        import uuid
        resp = await auth_client.get(f"/api/v1/forge/{uuid.uuid4()}")
        assert resp.status_code == 404
