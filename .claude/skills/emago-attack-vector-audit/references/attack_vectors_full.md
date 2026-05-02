# Vecteurs d'attaque Emago — détail des 25 vecteurs

Source : `docs/08_qa_securite.md` section 2.

## Critiques (C1-C7)

### C1 — Ownership cross-player révèle existence

**Risque** : un joueur peut découvrir l'existence d'objets d'autrui (énumération de UUIDs).

**Code KO** :
```python
@router.get("/ships/{ship_id}")
async def get_ship(ship_id: UUID, player: CurrentPlayer, db: DbDep):
    ship = await db.get(Ship, ship_id)
    if not ship:
        raise HTTPException(404, "Vaisseau introuvable.")
    if ship.owner_id != player.id:
        raise HTTPException(403, "Pas votre vaisseau")  # ❌ révèle existence
    return ship
```

**Code OK** :
```python
@router.get("/ships/{ship_id}")
async def get_ship(ship_id: UUID, player: CurrentPlayer, db: DbDep):
    ship = await db.get(Ship, ship_id)
    if not ship or ship.owner_id != player.id:
        raise HTTPException(404, "Vaisseau introuvable.")  # ✅ même code
    return ship
```

**Test** : `test_get_xxx_other_player_returns_404` (cf. fixture `other_player_ship_id`).

---

### C2 — Double-soumission

**Risque** : 2 requêtes simultanées créent 2 ressources concurrentes (ex. forge avec mêmes parents, alliance avec même tag).

**Code KO** :
```python
@router.post("/forge")
async def start_forge(body, player, db):
    ship_a = await db.get(Ship, body.ship_a_id)
    ship_b = await db.get(Ship, body.ship_b_id)
    # ⚠️ deux requêtes simultanées trouvent les ships en DOCKED ici
    if ship_a.status != "DOCKED" or ship_b.status != "DOCKED":
        raise HTTPException(409, "...")
    # ⚠️ deux requêtes simultanées passent ce check
    ship_a.status = "IN_FORGE"
    ship_b.status = "IN_FORGE"
    forge = ForgeQueue(...)
    db.add(forge)
    return forge
```

**Code OK** :
```python
@router.post("/forge")
async def start_forge(body, player, db):
    # SELECT FOR UPDATE ORDER BY id (anti-deadlock)
    sorted_ids = sorted([body.ship_a_id, body.ship_b_id])
    ships = (await db.execute(
        select(Ship).where(Ship.id.in_(sorted_ids)).with_for_update().order_by(Ship.id)
    )).scalars().all()
    # 1 seule des 2 requêtes simultanées passe ici, l'autre attend
    if any(s.status != ShipStatus.DOCKED for s in ships):
        raise HTTPException(409, "...")
    # ...
```

**Test** : `asyncio.gather(post_forge(), post_forge())` → un 201, un 409.

---

### C3 — Modification `base_stats` après création

**Risque** : triche en augmentant les stats d'un ship existant.

**Protection** :
- **Trigger PostgreSQL `prevent_base_stats_update`** : lève une exception sur tout UPDATE qui change `base_stats`.
- Bypass possible UNIQUEMENT via `SET LOCAL emago.bypass_stats_trigger = 'true'` (réservé migrations Alembic).

**Test** :
```python
async def test_base_stats_immutable(db_session, built_ship):
    ship = await db_session.get(Ship, built_ship["ship_id"])
    ship.base_stats = {"hull": 9999}
    db_session.add(ship)
    with pytest.raises(Exception, match="immutable|integrity_constraint"):
        await db_session.flush()
```

---

### C4 — Re-roll de stats (manipuler RNG)

**Risque** : exploit qui déclenche plusieurs builds rapides puis garde uniquement les bons tirages.

**Protection** :
- `secrets.SystemRandom()` non prédictible.
- Trigger PG immuabilité (cf. C3) → impossible de modifier après tirage.
- Rate-limit `ships:build` 10/min.

**Cas légitime** : un joueur qui spamme `POST /ships/build` avec assez de ressources tire des raretés différentes — c'est OK, c'est le RNG normal. Pas un re-roll.

**Cas KO** : si on trouvait une fonction `regenerate_stats(ship_id)` côté API, ce serait une faille. → vérifier qu'aucun endpoint ne fait ça.

---

### C5 — Token JWT expiré accepté

**Risque** : auth bypass si on n'expire pas correctement.

**Protection** :
- `python-jose.decode()` valide automatiquement `exp`.
- `decode_token(token, expected_kind="access")` vérifie aussi le `kind` (refresh ne peut pas être access).

**Test** :
```python
def expired_token(player_id: str) -> str:
    payload = {"sub": player_id, "kind": "access",
               "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
               "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp())}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

async def test_expired_token_rejected(client):
    token = expired_token(str(uuid4()))
    res = await client.get("/api/v1/ships",
                            headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
```

---

### C6 — Manipulation XP en input API

**Risque** : un endpoint accepte XP en input → triche directe.

**Protection** : aucun endpoint Emago n'accepte XP en input. XP calculé uniquement par `combat_engine` (after combat) et `expedition_service` (lead_ship gain).

**À auditer** : si tu vois un endpoint avec `combat_xp` ou `xp` dans le body Pydantic → STOP, ce n'est jamais OK.

---

### C7 — SECRET_KEY fuitée

**Risque** : compromission totale (forge JWT pour n'importe quel utilisateur).

**Protection** :
- `.env` JAMAIS committé (`.gitignore` strict).
- Génération via `secrets.token_hex(32)` (64 chars hex).
- Rotation après suspicion (= invalide tous les tokens existants).

**Audit** :
```bash
git log --all -p | grep -iE 'secret_key' | head -20
git ls-files | grep -E '\.env$'
```

Cf. `scripts/check_secrets.sh` du skill `emago-deploy-checklist`.

---

## Élevés (E1-E8)

### E1 — Vaisseau IN_FLEET envoyé en forge

**Code KO** :
```python
@router.post("/forge")
async def start_forge(body, player, db):
    ship_a = await db.get(Ship, body.ship_a_id)
    # ⚠️ pas de check status
    forge = ForgeQueue(...)
    return forge
```

**Code OK** :
```python
if any(s.status != ShipStatus.DOCKED for s in ships):
    raise HTTPException(409, f"Le vaisseau {ship.id} n'est pas DOCKED.")
```

**Test** : `test_forge_in_fleet_ship_rejected` avec fixture `ship_in_fleet`.

---

### E2 — WebSocket cross-player

**Risque** : joueur A reçoit les events de joueur B.

**Protection** :
- Channel pub/sub Redis `emago:events:player:{id}` → 1 channel par joueur.
- `subscribe_player_events(player_id)` (côté backend WS handler) ne s'abonne qu'au channel de SON joueur (validé par JWT au handshake).

**Audit** : vérifier que tout `publish_event` utilise `channel=f"player:{owner_id}"` et JAMAIS `channel="all"` ou un broadcast.

**Test** :
```python
async def test_ws_isolation(client_ws_a, client_ws_b):
    await client_ws_b.action_qui_genere_event()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(client_ws_a.receive_text(), timeout=2.0)
```

---

### E3 — Énumération login

**Code KO** :
```python
if not user:
    raise HTTPException(401, "Email inconnu")
if not check_password(password):
    raise HTTPException(401, "Mauvais mot de passe")
```

**Code OK** :
```python
if not user or not check_password(password):
    raise HTTPException(401, "Email ou mot de passe incorrect.")
```

**Test** : email inconnu et mauvais MDP renvoient même status + même message.

---

### E4 — Participation `/combat/{id}` non vérifiée

**Code OK** (cf. `app/routers/combat.py`) :
```python
async def get_combat_report(combat_id, player, db):
    log = await db.get(CombatLog, combat_id)
    if not log:
        raise HTTPException(404, "Combat introuvable.")
    if not _is_participant(log, player.id):
        raise HTTPException(403, "Vous n'êtes pas participant de ce combat.")
    return log
```

`_is_participant` parse les snapshots JSONB pour vérifier owner_id.

**TODO connu (ligne 107 combat.py)** : index JSONB pour perf en Phase 2.

---

### E5 — Pedigree avec parent d'autrui

**Code OK** (cf. `ship_build_service._validate_pedigree_parent`) :
```python
parent = await db.get(Ship, parent_ship_id)
if not parent:
    raise HTTPException(404, "Parent introuvable.")
if parent.owner_id != player_id:
    raise HTTPException(403, "Le parent ne vous appartient pas.")
if parent.ship_type != ship_type:
    raise HTTPException(409, "Type différent.")
if parent.grade < 3:
    raise HTTPException(409, "Grade 3+ requis.")
if parent.status != ShipStatus.DOCKED:
    raise HTTPException(409, "Parent doit être DOCKED.")
```

> **Note** : ici 403 explicite (pas 404) car le user a fourni l'ID en input — il sait qu'il existe.

---

### E6 — Rate-limit absent sur endpoint sensible

**Endpoints sensibles à protéger** :
- `POST /auth/register` (5/min) — anti-spam comptes.
- `POST /auth/login` (10/min) — anti-brute-force.
- `POST /ships/build` (10/min) — anti-spam, RNG abuse.
- `POST /forge` (5/min) — anti-double submission.
- `POST /fleets` (20/min) — anti-spam attaques.
- `PUT /ships/.../modules/...` (30/min) — anti-spam.

**À ajouter** :
- `POST /alliances` (5/min) — anti-spam création.
- `POST /alliances/.../wars` (1/heure) — anti-troll guerre.
- `POST /espionage/probe` (5/min) — anti-spam sondes.
- `POST /tech/research` (10/min) — anti-spam recherches.

**Code** :
```python
# app/middleware/rate_limit.py
_LIMITS = {
    "ships:build": 10,
    "forge:start": 5,
    # ajouter :
    "espionage:probe": 5,
    "alliances:create": 5,
}

# Dans le router :
from app.middleware.rate_limit import check_rate_limit

@router.post("/probe", status_code=201)
async def launch_probe(...):
    await check_rate_limit(player.id, "espionage:probe")
    # ...
```

---

### E7 — Injection SQL via JSONB

**Risque** : payload JSONB avec contenu malicieux qui n'est pas escape.

**Protection** : SQLAlchemy paramétrise tout. Aucun raw SQL avec `f-string` du body utilisateur.

**Audit** : grep le code pour `f"...{...}..."` dans des `text()` ou `execute()`. Si trouvé avec input utilisateur → STOP, refacto avec params binds.

**Cas légitime** : les `text("INSERT INTO fleet_ships ...")` dans `routers/fleets.py` utilisent paramètres binds (`:fid`), donc OK.

---

### E8 — DEBUG=true en prod (CORS permissif, Swagger UI exposé)

**Conséquences** :
- Swagger UI exposé (`/docs`) → cartographie des endpoints publique.
- CORS autorisé pour `localhost:5173` → CSRF possible si user mal protégé.

**Audit** :
```bash
grep "DEBUG=" /opt/emago/.env  # doit afficher DEBUG=false
curl https://YOUR_DOMAIN.COM/docs  # doit retourner 404 si DEBUG=false
```

---

## Moyens (M1-M8)

### M1 — `with_for_update` manquant sur mutation

(Cf. C2 — variant moins critique mais à corriger.)

### M2 — `math.floor` manquant sur ressources

**Risque** : bug 1999.87 affiché 2000 en UI mais `1999.87 < 2000` → refus injuste.

**Code OK** :
```python
import math
if math.floor(float(planet.metal)) < cost_metal:
    raise HTTPException(402, "Ressources insuffisantes.")
```

### M3 — N+1 queries

**Risque** : 1 SELECT initial + N SELECTs en boucle → perf catastrophique avec scale.

**Audit** : monitor les queries en CI ou avec `pytest-postgresql`.

**Solution** : `joinedload`, batch SELECT `WHERE id IN (...)`.

### M4 — Index manquant

**Audit** : `EXPLAIN ANALYZE` sur queries fréquentes.

**Indexes Emago déjà critiques** : cf. `docs/07_base_de_donnees.md` section 7.

### M5 — Headers HTTP de sécurité

**Vérifier `nginx/conf.d/emago.conf`** :
- `Strict-Transport-Security` ✅
- `X-Content-Type-Options nosniff` ✅
- `X-Frame-Options SAMEORIGIN` ✅
- `Content-Security-Policy ...` ✅
- (Phase 2 : tighten CSP, supprimer `unsafe-inline`)

### M6 — `_active_research` mémoire

**Bug connu** : `routers/tech.py` ligne 212. Perdu au redémarrage Uvicorn.

**Fix** : migration BDD `0007_research_queue` (cf. `emago-migration-alembic`).

### M7 — Pas de heartbeat WS server-side

**Risque** : connexions zombies non détectées.

**Solution** : ajouter ping périodique server → client avec timeout côté client.

### M8 — Logs avec données sensibles

**Audit** :
```bash
grep -rE 'password|token|secret_key' app/ --include="*.py" | grep -i "log\|print"
```

Si trouvé → refacto pour ne pas log les valeurs sensibles.

---

## Faibles (F1-F5)

### F1 — Scaling WS horizontal pas activé
ConnectionManager mémoire seul. À activer avec sticky sessions Nginx ou Redis pub/sub strict si > 1 worker Uvicorn.

### F2 — Index JSONB pour participation combat
`routers/combat.py` ligne 107 — TODO Phase 2.

### F3 — Heartbeat WS timeout client
Frontend ping 30s. Pas de timeout serveur → connexions persistent indéfiniment.

### F4 — Logs JSON pas centralisés
Loki/Grafana ou Papertrail à envisager Phase 2C.

### F5 — Monitoring dépendances
`pip-audit` + `npm audit` à automatiser en CI.
