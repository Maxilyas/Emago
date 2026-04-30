# Emago — Spécification QA & Sécurité complète
> Document destiné à **Agent 8 — QA & Sécurité**
> Stack tests : pytest + pytest-asyncio + httpx

---

## 1. Lancer les tests existants

```bash
# Depuis la racine du projet
pip install -r requirements.txt

# Tests unitaires (0 dépendance externe — pas besoin de BDD ni Redis)
pytest tests/services/ -v

# Couverture
pytest tests/services/ --cov=app/services --cov-report=html
```

**Tests déjà écrits :** `tests/services/test_ship_services.py` — 50+ assertions couvrant :
- Distribution RNG rareté (statistique sur 2000 tirages)
- Génération `base_stats` (fourchettes, types, valeurs négatives)
- Pedigree (+5%, immuabilité, stat inconnue)
- `_compute_current_stats` (cap +150%, affinité, grades, régén. bouclier)
- Validation slots modules (premium, out-of-range)
- Formule XP différentielle (equal/stronger/weaker)
- Seuils de grade (0 à 5)
- `CombatShip.take_damage` (bouclier absorbe d'abord, immunité Grade 4)
- Cicatrices (seuil hull 75%, ratio puissance ×2)
- Forge (_merge_best_stats, upgrade rareté, ratio XP)

---

## 2. Tests d'intégration à écrire

### 2.1 conftest.py — fixtures BDD

```python
# tests/conftest.py (à compléter)
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import get_db_dep
from app.models.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://emago:emago_dev@localhost:5432/emago_test"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    async def override_db():
        yield db_session
    app.dependency_overrides[get_db_dep] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
async def auth_headers(client) -> dict:
    """Crée un joueur et retourne ses headers d'auth."""
    resp = await client.post("/api/v1/auth/register", json={
        "username": "testplayer",
        "email": "test@emago.io",
        "password": "password123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

---

### 2.2 tests/routers/test_auth.py

```python
class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "username": "newplayer", "email": "new@test.io", "password": "password123"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_username(self, client, auth_headers):
        resp = await client.post("/api/v1/auth/register", json={
            "username": "testplayer",  # déjà pris par auth_headers fixture
            "email": "other@test.io", "password": "password123"
        })
        assert resp.status_code == 409

    async def test_register_password_too_short(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "username": "abc", "email": "x@y.com", "password": "short"
        })
        assert resp.status_code == 422

    async def test_register_invalid_username_chars(self, client):
        resp = await client.post("/api/v1/auth/register", json={
            "username": "user name!", "email": "x@y.com", "password": "password123"
        })
        assert resp.status_code == 422

class TestLogin:
    async def test_login_success(self, client, auth_headers):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@emago.io", "password": "password123"
        })
        assert resp.status_code == 200

    async def test_login_wrong_password(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "test@emago.io", "password": "wrongpassword"
        })
        assert resp.status_code == 401
        # Message vague (anti-énumération)
        assert "incorrect" in resp.json()["detail"].lower()

    async def test_login_unknown_email(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@nobody.com", "password": "password123"
        })
        # MÊME message d'erreur que mauvais mot de passe (anti-énumération)
        assert resp.status_code == 401

class TestRefresh:
    async def test_refresh_success(self, client, auth_headers):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "test@emago.io", "password": "password123"
        })
        refresh_token = login_resp.json()["refresh_token"]
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_with_access_token_fails(self, client, auth_headers):
        # Un access_token ne doit pas fonctionner comme refresh_token
        access_token = auth_headers["Authorization"].split(" ")[1]
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token
        })
        assert resp.status_code == 401

    async def test_refresh_with_invalid_token_fails(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "completelyfaketoken"
        })
        assert resp.status_code == 401
```

---

### 2.3 tests/routers/test_ships.py

```python
# ⚠️ Vecteur critique n°1 : ownership check
class TestShipOwnership:
    async def test_cannot_get_other_players_ship(self, client, auth_headers):
        """Un joueur ne peut pas voir le vaisseau d'un autre."""
        # Créer un second joueur
        resp2 = await client.post("/api/v1/auth/register", json={
            "username": "player2", "email": "p2@test.io", "password": "password123"
        })
        headers2 = {"Authorization": f"Bearer {resp2.json()['access_token']}"}

        # player2 crée un vaisseau
        build_resp = await client.post("/api/v1/ships/build",
            headers=headers2,
            json={"ship_type": "frigate_attack", "planet_id": "..."}
        )
        ship_id = build_resp.json()["ship_id"]

        # player1 essaie d'y accéder → 404
        resp = await client.get(f"/api/v1/ships/{ship_id}", headers=auth_headers)
        assert resp.status_code == 404

    # ⚠️ Vecteur critique n°2 : module sur vaisseau d'un autre joueur
    async def test_cannot_install_module_on_other_ship(self, client, auth_headers):
        """
        PUT /ships/{id}/modules/{slot} avec ship_id d'un autre joueur → 404.
        C'est le vecteur d'attaque le plus critique selon Agent 3.
        """
        # [Setup : créer un vaisseau appartenant à player2]
        # [Tester que player1 reçoit 404, pas 403 — pour ne pas confirmer l'existence]
        pass  # À implémenter avec fixtures

    async def test_cannot_demolish_other_players_ship(self, client, auth_headers):
        pass

class TestBuildShip:
    async def test_build_success(self, client, auth_headers):
        resp = await client.post("/api/v1/ships/build",
            headers=auth_headers,
            json={"ship_type": "frigate_attack", "planet_id": "valid-planet-uuid"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "ship_id" in data
        assert data["rarity"] in ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]
        assert data["ship_class"] == "ATTACK"
        assert isinstance(data["slots_total"], int)
        assert isinstance(data["slots_premium"], int)

    async def test_build_unknown_type_returns_400(self, client, auth_headers):
        resp = await client.post("/api/v1/ships/build",
            headers=auth_headers,
            json={"ship_type": "death_star", "planet_id": "uuid"}
        )
        assert resp.status_code == 400

    async def test_build_insufficient_resources_returns_402(self, client, auth_headers):
        # Requiert un joueur sans ressources
        pass

    async def test_rng_distribution_over_1000_builds(self, client, auth_headers):
        """
        Test statistique : sur 1000 builds, LEGENDARY entre 0.3% et 3%.
        À lancer en mode intégration seulement (lent).
        """
        counts = {}
        for _ in range(1000):
            resp = await client.post("/api/v1/ships/build", headers=auth_headers,
                json={"ship_type": "frigate_attack", "planet_id": "uuid"})
            rarity = resp.json().get("rarity")
            counts[rarity] = counts.get(rarity, 0) + 1
        legendary_pct = counts.get("LEGENDARY", 0) / 1000
        assert 0.003 < legendary_pct < 0.03, f"LEGENDARY = {legendary_pct:.1%}"

class TestModules:
    async def test_install_module_returns_current_stats(self, client, auth_headers):
        # Build ship, install module, verify current_stats
        pass

    async def test_cap_reached_when_stacking_modules(self, client, auth_headers):
        """Vérifier que cap_reached est rempli quand on pile des modules."""
        pass

    async def test_level4_module_in_standard_slot_returns_422(self, client, auth_headers):
        pass

    async def test_module_on_in_forge_ship_returns_409(self, client, auth_headers):
        """Un vaisseau IN_FORGE ne peut pas être modifié."""
        pass

class TestDemolish:
    async def test_demolish_docked_ship_success(self, client, auth_headers):
        pass

    async def test_demolish_in_fleet_ship_returns_409(self, client, auth_headers):
        pass

    async def test_unauthenticated_request_returns_401(self, client):
        resp = await client.delete("/api/v1/ships/some-uuid")
        assert resp.status_code == 403  # HTTPBearer retourne 403 sans credentials
```

---

### 2.4 tests/routers/test_forge.py

```python
class TestForge:
    # ⚠️ Vecteur critique n°3 : double soumission
    async def test_double_forge_submission_blocked(self, client, auth_headers):
        """
        Deux requêtes POST /forge identiques quasi-simultanées.
        La deuxième doit retourner 409 (vaisseau déjà IN_FORGE).
        Le SELECT FOR UPDATE dans forge_service protège contre ce cas.
        """
        import asyncio
        # [Setup : créer deux vaisseaux compatibles]
        ship_a_id = "..."
        ship_b_id = "..."

        # Envoyer deux requêtes simultanées
        results = await asyncio.gather(
            client.post("/api/v1/forge", headers=auth_headers,
                       json={"ship_a_id": ship_a_id, "ship_b_id": ship_b_id}),
            client.post("/api/v1/forge", headers=auth_headers,
                       json={"ship_a_id": ship_a_id, "ship_b_id": ship_b_id}),
        )
        statuses = {r.status_code for r in results}
        assert 201 in statuses
        assert 409 in statuses

    async def test_forge_same_ship_twice_returns_400(self, client, auth_headers):
        ship_id = "..."
        resp = await client.post("/api/v1/forge", headers=auth_headers,
            json={"ship_a_id": ship_id, "ship_b_id": ship_id})
        assert resp.status_code == 400

    async def test_forge_different_rarities_returns_422(self, client, auth_headers):
        pass

    async def test_forge_different_types_returns_422(self, client, auth_headers):
        pass

    async def test_forge_legendary_returns_422(self, client, auth_headers):
        """Un vaisseau LEGENDARY ne peut pas être forgé."""
        pass

    async def test_forge_in_fleet_ship_returns_409(self, client, auth_headers):
        """Un vaisseau IN_FLEET ne peut pas entrer en forge."""
        pass

    async def test_forge_status_polling(self, client, auth_headers):
        """GET /forge/:id retourne le bon format."""
        pass

    async def test_forge_history_returns_list(self, client, auth_headers):
        resp = await client.get("/api/v1/forge/history", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
```

---

## 3. Checklist Sécurité

### Authentification
- [ ] Token expiré → 401 (pas 500)
- [ ] Token forgé (mauvaise signature) → 401
- [ ] `refresh_token` utilisé comme `access_token` → 401
- [ ] `access_token` utilisé comme `refresh_token` → 401
- [ ] Requête sans header → 403 (HTTPBearer)
- [ ] Rotation des refresh tokens : l'ancien est invalidé après `/auth/refresh`

### Ownership (vecteur critique n°1)
- [ ] `GET /ships/:id` avec UUID d'un autre joueur → 404
- [ ] `PUT /ships/:id/modules/:slot` avec UUID d'un autre joueur → 404
- [ ] `DELETE /ships/:id` avec UUID d'un autre joueur → 404
- [ ] `GET /forge/:id` avec forge_id d'un autre joueur → 404

### Double-spend / Race conditions
- [ ] Deux builds simultanés ne doublent pas les ressources (SELECT FOR UPDATE)
- [ ] Deux forges simultanées sur la même paire → 1 succès + 1 erreur 409
- [ ] Build + forge simultanés sur le même vaisseau → cohérence garantie

### Manipulation des stats
- [ ] `base_stats` ne peut pas être modifié via l'API (trigger BDD côté Agent 7)
- [ ] `current_stats` n'est jamais accepté en input par aucun endpoint
- [ ] Le cap +150% est vérifié côté serveur (pas uniquement dans l'UI)
- [ ] Un module niveau IV/V ne peut pas être installé dans un slot standard

### Statuts de vaisseau
- [ ] Vaisseau `IN_FORGE` → ne peut pas recevoir de modules (409)
- [ ] Vaisseau `IN_FORGE` → ne peut pas être démoli (409)
- [ ] Vaisseau `IN_FLEET` → ne peut pas être envoyé en forge (409)
- [ ] Vaisseau `IN_FLEET` → ne peut pas être démoli (409)

### WebSocket
- [ ] Connexion sans token → fermeture avec code 4001
- [ ] Connexion avec token valide mais joueur supprimé → fermeture 4004
- [ ] Message JSON malformé → `{"type": "error", "detail": "JSON invalide."}`
- [ ] Type de message inconnu → `{"type": "error", ...}` (pas de crash)

---

## 4. Vecteurs d'attaque à tester explicitement

### Injection SQL
Tous les inputs passent par SQLAlchemy paramétré — aucune interpolation manuelle de SQL.
Tester avec : `'; DROP TABLE ships; --` dans les champs de texte.

### Enumération d'utilisateurs
- `POST /auth/login` avec email inexistant retourne **exactement** le même message et code que mot de passe incorrect.
- Vérifier que le temps de réponse est similaire (pas de timing attack).

### Manipulation du RNG
Le RNG utilise `secrets.SystemRandom()` côté serveur. Il n'y a aucune façon de prédire ou influencer le résultat depuis le client.

### Manipulation de la progression XP
L'XP n'est jamais acceptée en input — elle est calculée exclusivement dans `combat_engine.py` côté serveur.

---

## 5. Tests de charge (indicatifs)

Pour le contexte "quelques dizaines de joueurs" :
- **Target :** < 200ms p95 sur tous les endpoints REST
- **WebSocket :** 50 connexions simultanées sans dégradation
- **Scheduler :** `forge_tick` (60s) ne doit pas dépasser 10s d'exécution

Outil recommandé : `locust` ou `k6`.

---

## 6. Ce qui n'est pas encore implémenté (phase 2)

Ces endpoints/fonctionnalités ne peuvent pas encore être testés — ils sont listés pour planification :
- Routes `/planets`, `/fleets`, `/combat/:id`, `/ranking`
- Tests d'intégration WebSocket complets (nécessitent un serveur WebSocket de test)
- Tests de charge (nécessitent un environnement dédié)
- Rapport d'espionnage, colonisation (stubs dans fleet_arrival.py)
