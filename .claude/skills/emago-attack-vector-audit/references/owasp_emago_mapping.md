# Mapping OWASP Top 10 (2021) ↔ vecteurs Emago

Pour faciliter les audits OWASP périodiques.

| OWASP | Catégorie | Vecteurs Emago | Statut global |
|---|---|---|---|
| A01 | Broken Access Control | C1 (ownership), E2 (WS isolation), E4 (combat participation), E5 (pedigree) | ✅ FAIT |
| A02 | Cryptographic Failures | bcrypt password, JWT HS256, SECRET_KEY env-only, HTTPS forcé | ✅ FAIT |
| A03 | Injection | E7 (JSONB), SQLAlchemy paramétré | ✅ FAIT |
| A04 | Insecure Design | C3 (immuabilité), C4 (RNG anti-triche), C6 (XP) | ✅ FAIT |
| A05 | Security Misconfiguration | E8 (DEBUG prod), M5 (headers HTTP) | ⚠️ EN COURS (CSP à durcir) |
| A06 | Vulnerable Components | F5 (`pip-audit`, `npm audit`) | ⚠️ EN COURS (à automatiser CI) |
| A07 | Auth Failures | E3 (énumération login), C5 (JWT), E6 (rate-limit auth) | ✅ FAIT |
| A08 | Data Integrity Failures | C3 (trigger PG), combat replay determinism | ✅ FAIT |
| A09 | Logging & Monitoring | M8 (logs sensibles), F4 (centralisation), Uptime Kuma | ⚠️ EN COURS |
| A10 | SSRF | N/A (pas de fetch externe utilisateur) | N/A |

---

## A01 — Broken Access Control

**Vecteurs Emago couverts** :
- **C1** Ownership masqué (404 vs 403) — protégé par helper `_get_owned_*`.
- **E2** WebSocket isolation — channel `player:{id}` strict via Redis pub/sub.
- **E4** Participation `/combat/{id}` — helper `_is_participant`.
- **E5** Pedigree avec parent d'autrui — `_validate_pedigree_parent` 403.
- Alliance role hierarchy — `_require_role(min_role)` 403.

**Tests recommandés** : `tests/routers/test_*.py` avec fixture `other_player_ship_id`.

---

## A02 — Cryptographic Failures

**Protection Emago** :
- **bcrypt** pour password (passlib).
- **JWT HS256** avec SECRET_KEY 64-char hex (généré via `secrets.token_hex(32)`).
- **HTTPS forcé** par Nginx (HTTP → 301 HTTPS).
- **TLS 1.2+** uniquement (pas TLS 1.0/1.1).
- **HSTS** : `max-age=31536000; includeSubDomains`.
- SECRET_KEY **JAMAIS** committée (cf. `scripts/check_secrets.sh`).

**Audit** :
```bash
curl -I https://YOUR_DOMAIN.COM | grep -iE "strict-transport-security"
git log --all -p | grep -i "SECRET_KEY"  # doit être vide
```

---

## A03 — Injection

**Protection Emago** :
- SQLAlchemy paramétré partout.
- Aucun raw SQL avec interpolation.
- Cas légitimes (`text()` avec binds) audités.

**Test** :
```python
async def test_no_sql_injection(auth_client, planet_id):
    payload = {
        "ship_type": "frigate_attack'; DROP TABLE ships; --",
        "planet_id": str(planet_id)
    }
    res = await auth_client.post("/api/v1/ships/build", json=payload)
    assert res.status_code in (400, 422)  # rejet validation, pas crash
```

---

## A04 — Insecure Design

**Vecteurs critiques** :
- **C3** Immuabilité `base_stats` via trigger PG.
- **C4** RNG `secrets.SystemRandom()` non prédictible.
- **C6** XP jamais en input API.
- **Source de vérité = serveur** : tout calcul de jeu côté serveur.

---

## A05 — Security Misconfiguration

**Audit** :
```bash
# DEBUG=false en prod
ssh emago@vps "grep DEBUG /opt/emago/.env"  # → DEBUG=false

# Swagger UI désactivé
curl https://YOUR_DOMAIN.COM/docs  # → 404

# CORS strict
curl -i -X OPTIONS https://YOUR_DOMAIN.COM/api/v1/ships \
  -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: GET"
# → ne doit PAS renvoyer Access-Control-Allow-Origin: https://evil.com

# CSP raisonnable
curl -I https://YOUR_DOMAIN.COM | grep -i content-security
```

**Phase 2** : tighten CSP (suppression `unsafe-inline` script-src).

---

## A06 — Vulnerable Components

**Audit recommandé en CI** :

```yaml
# .github/workflows/ci.yml
- name: pip-audit
  run: pip install pip-audit && pip-audit --requirement backend/requirements.txt --exit-on=critical

- name: npm-audit
  working-directory: ./frontend
  run: npm audit --audit-level=high
```

**Manuellement** :
```bash
cd backend && pip-audit
cd frontend && npm audit
```

---

## A07 — Identification & Authentication Failures

**Protection Emago** :
- **E3** Anti-énumération login (même message 401).
- **E6** Rate-limit `auth:register` 5/min, `auth:login` 10/min.
- **C5** JWT expiration validée (access 60min, refresh 30j).
- Rotation refresh token (un nouveau refresh émis à chaque utilisation).
- bcrypt password (cost 12 par défaut).

---

## A08 — Software & Data Integrity Failures

**Protection Emago** :
- **Trigger PG `prevent_base_stats_update`** : intégrité données.
- **Combat replay determinism** : `random.Random(combat_seed)` permet rejouer un combat exact.
- **Migrations Alembic** : versionning du schéma.

---

## A09 — Security Logging & Monitoring

**État actuel** :
- ✅ Logs JSON-structurés via Docker driver.
- ✅ Endpoint `/health` pour Uptime Kuma.
- ⚠️ Pas de centralisation logs (Loki/Grafana à venir).
- ⚠️ Alertes Discord/Slack à configurer.

**Audit** :
```bash
# Logs JSON ?
docker compose -f docker-compose.prod.yml logs --tail=10 api | jq .

# Uptime Kuma running ?
curl http://localhost:3001/api/status-page/heartbeat/emago
```

---

## A10 — SSRF

**N/A** : Emago ne fetch aucun URL externe d'utilisateur. Aucun endpoint qui prend une URL en input et fait un GET dessus.

**Si Phase 2 ajoute** (par ex. avatar URL) → audit nécessaire :
- Whitelist domaines.
- Pas de redirection chain.
- Pas d'IPs internes (10.x, 172.16.x, 192.168.x, 127.x).

---

## Audit OWASP périodique — checklist

À faire trimestriellement :

- [ ] A01 : audit chaque router via `emago-attack-vector-audit`.
- [ ] A02 : `curl -I` HSTS / TLS / `git log` SECRET_KEY.
- [ ] A03 : tests SQL injection sur tous les endpoints qui acceptent body.
- [ ] A04 : audit nouveaux endpoints (XP en input ? mutation base_stats ?).
- [ ] A05 : audit `.env` prod, headers HTTP, CSP.
- [ ] A06 : `pip-audit` + `npm audit`.
- [ ] A07 : tests rate-limit auth, expiration JWT.
- [ ] A08 : test replay combat determinism.
- [ ] A09 : logs centralisés ? alertes actives ?
- [ ] A10 : N/A (à revérifier si nouveaux endpoints fetch).

---

## Outils tiers

| Outil | Usage | Recommandé pour |
|---|---|---|
| **OWASP ZAP** | Scan auto vulnérabilités | A01, A03, A05 |
| **Burp Suite** | Test manuel injection / authz | A01, A07 |
| **`pip-audit`** | Scan deps Python | A06 |
| **`npm audit`** | Scan deps JS | A06 |
| **`nuclei`** | Scan vulnérabilités templates | A05, A06 |
| **`trivy`** | Scan image Docker | A06 |
| **`securityheaders.com`** | Audit headers HTTP | A05 |
| **`mozilla observatory`** | Audit sécurité web | A05 |

À automatiser dans CI : `pip-audit`, `npm audit`, `trivy` sur l'image Docker.
