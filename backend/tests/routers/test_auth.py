"""
tests/routers/test_auth.py
Agent 8 — QA & Sécurité | Sprint 2

Tests d'intégration — router /auth
Couvre les cas : register, login, refresh, doublons, mauvais credentials.

Requires: BDD de test PostgreSQL (pytest-asyncio, httpx ASGI transport)
Voir conftest.py pour les fixtures.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ===========================================================================
# POST /auth/register
# ===========================================================================

class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Un nouvel utilisateur peut s'inscrire et reçoit des tokens."""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "testplayer",
            "email": "test@emago.io",
            "password": "password123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient):
        """Deux inscriptions avec le même username → 409."""
        payload = {"username": "dupuser", "email": "first@emago.io", "password": "pass1234"}
        await client.post("/api/v1/auth/register", json=payload)
        resp = await client.post("/api/v1/auth/register", json={
            **payload,
            "email": "second@emago.io",  # email différent, username identique
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        """Deux inscriptions avec le même email → 409."""
        await client.post("/api/v1/auth/register", json={
            "username": "user_a", "email": "shared@emago.io", "password": "pass1234"
        })
        resp = await client.post("/api/v1/auth/register", json={
            "username": "user_b", "email": "shared@emago.io", "password": "pass1234"
        })
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Email invalide → 422."""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "player", "email": "not-an-email", "password": "pass1234"
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_username(self, client: AsyncClient):
        """Username < 3 caractères → 422."""
        resp = await client.post("/api/v1/auth/register", json={
            "username": "ab", "email": "ab@emago.io", "password": "pass1234"
        })
        assert resp.status_code == 422


# ===========================================================================
# POST /auth/login
# ===========================================================================

class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, registered_player: dict):
        """Login avec les bons credentials → 200 + tokens."""
        resp = await client.post("/api/v1/auth/login", json={
            "email": registered_player["email"],
            "password": registered_player["password"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, registered_player: dict):
        """Mauvais mot de passe → 401 (message volontairement vague)."""
        resp = await client.post("/api/v1/auth/login", json={
            "email": registered_player["email"],
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        # Vérifier que le message ne révèle pas si l'email existe
        assert "email ou mot de passe" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_unknown_email(self, client: AsyncClient):
        """Email inexistant → 401 (même message que mauvais mdp — anti-enumeration)."""
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@emago.io",
            "password": "irrelevant",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, client: AsyncClient):
        """Payload incomplet → 422."""
        resp = await client.post("/api/v1/auth/login", json={"email": "x@y.com"})
        assert resp.status_code == 422


# ===========================================================================
# POST /auth/refresh
# ===========================================================================

class TestRefresh:
    @pytest.mark.asyncio
    async def test_refresh_success(self, client: AsyncClient, registered_player: dict):
        """Un refresh token valide génère une nouvelle paire."""
        login = await client.post("/api/v1/auth/login", json={
            "email": registered_player["email"],
            "password": registered_player["password"],
        })
        tokens = login.json()
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert "access_token" in new_tokens
        # Le nouveau access token doit être différent
        assert new_tokens["access_token"] != tokens["access_token"]

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client: AsyncClient, registered_player: dict):
        """Utiliser un access token comme refresh → 401."""
        login = await client.post("/api/v1/auth/login", json={
            "email": registered_player["email"],
            "password": registered_player["password"],
        })
        access = login.json()["access_token"]
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Token forgé → 401."""
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "this.is.not.a.valid.jwt"
        })
        assert resp.status_code == 401
