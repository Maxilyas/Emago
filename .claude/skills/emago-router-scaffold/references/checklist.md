# Checklist router Emago — avant merge

Toujours vérifier ces items pour un nouveau router (ou modif d'existant).

## Structure

- [ ] Préfixe `prefix="/<name>"` cohérent (kebab-case).
- [ ] Tags Swagger explicites : `tags=["<name>"]`.
- [ ] Routes statiques (`/history`, `/active`, `/incoming`) déclarées AVANT routes paramétrées (`/{id}`).
- [ ] Inclus dans `main.py` avec `prefix="/api/v1"`.

## Auth & deps

- [ ] Endpoints auth-required ont `player: CurrentPlayer` ; endpoints publics explicitement sans auth (ranking, alliances list).
- [ ] `db: DbDep` injecté quand nécessaire.
- [ ] Pas d'override manuel de la session BDD — le `get_db_dep` gère commit/rollback.

## Schémas Pydantic

- [ ] Request models en début de fichier (kebab→PascalCase, suffix `Request`).
- [ ] Response models avec `class Config: from_attributes = True` si construits depuis un modèle SQLAlchemy.
- [ ] Validators côté Pydantic pour formats spécifiques (ex. tag alliance regex `^[A-Z0-9]+$`).
- [ ] Champs marqués `Field(..., min_length, max_length, ge, le)` pour les contraintes.

## Sécurité — vecteurs critiques

- [ ] **V1** Helper `_get_owned_<resource>` lève **404** (jamais 403) pour ressource d'autrui.
- [ ] **V2** `with_for_update()` sur les mutations qui consomment ressources.
- [ ] **V3** Aucune mutation de `base_stats` côté router (trigger PG s'en occupe).
- [ ] **V4** JWT validé via `CurrentPlayer` (kind="access").
- [ ] **V5** `math.floor(float(planet.X))` pour comparer ressources entières.
- [ ] **V6** Rate-limit dans `_LIMITS` du middleware si endpoint sensible (build, forge, fleet send, register, login).

## Codes d'erreur

- [ ] 401 : token absent / invalide / kind incorrect (géré par `CurrentPlayer`).
- [ ] 402 : ressources insuffisantes — message détaillé requis vs disponible.
- [ ] 403 : refus explicite uniquement (alliance role, pedigree d'autrui en input).
- [ ] 404 : introuvable OU ownership masqué (préférer 404 par défaut).
- [ ] 409 : conflit d'état (statut bloquant, déjà existant, race condition).
- [ ] 422 : validation Pydantic OU contrainte business (slot invalide, level non compatible).
- [ ] 429 : rate-limit dépassé (header `Retry-After: 60`).

## Messages d'erreur

- [ ] Tous en français.
- [ ] Détaillés et actionnables ("Ressources insuffisantes. Requis : métal=10000…").
- [ ] Pas de fuite d'info technique (pas de stack trace, pas de SQL).
- [ ] Cohérents avec ceux d'autres routers (ex. "Vaisseau introuvable.", "Planète introuvable.").

## Transactions

- [ ] Toutes les mutations dans une transaction unique (pas de commit intermédiaire qui laisse un état partiel).
- [ ] `await db.flush()` si on a besoin de l'ID auto-généré avant la fin de la transaction.
- [ ] Pas de `await db.commit()` explicite — `get_db_dep` s'en charge en fin de requête.

## Délégation

- [ ] Logique métier dans `app/services/<feature>_service.py`, PAS dans le router.
- [ ] Le router : valide inputs, vérifie auth/ownership, délègue, sérialise.
- [ ] Si la logique tient en < 5 lignes → OK inline. Sinon → service.

## Cache Redis

- [ ] Après mutation ship : `await invalidate_ship_cache(ship_id)`.
- [ ] Après build/forge/demolish : `await invalidate_hangar_cache(player.id)`.
- [ ] Lecture cache : `await get_redis()` puis `r.get(key)` ; si miss, fallback BDD.
- [ ] Écriture cache : `r.setex(key, TTL, json.dumps(...))`.

## WebSocket

- [ ] `publish_event(channel=f"player:{owner_id}", event=...)` après l'écriture BDD (HORS transaction si possible).
- [ ] Channel toujours `f"player:{id}"` pour les events utilisateur.
- [ ] `event = {"type": "feature.action", "data": {...}}` — type avec namespace (forge.complete, combat.result, alliance.war_declared).
- [ ] Type côté frontend défini dans `frontend/src/types/index.ts`.

## Documentation

- [ ] Docstring sur le router (1 paragraphe).
- [ ] Docstring sur chaque endpoint (description + Raises).
- [ ] Mise à jour `docs/05_dev_backend.md` section 4 (liste routers).
- [ ] Mise à jour `docs/03_architecte.md` section 3 (contrats API).
- [ ] Si nouveaux events WS : section 5 de `03_architecte.md`.

## Tests

- [ ] Tests pytest dans `tests/routers/test_<name>.py`.
- [ ] Couverture des codes d'erreur (404 ownership, 402 ressources, 409 conflit, 422 validation).
- [ ] Test V2 (double-soumission) si endpoint critique.
- [ ] Test V8 (cross-player WS) si publish_event.
- [ ] Suggérer `emago-test-integration-writer` pour générer le squelette.

## Audit final

- [ ] `pytest tests/routers/test_<name>.py` : tout vert.
- [ ] `mypy app/routers/<name>.py` : aucune erreur.
- [ ] `ruff check app/routers/<name>.py` : aucun warning.
- [ ] Test smoke en local : POST/GET/DELETE marchent.
- [ ] Logs cohérents (pas d'INFO bruyant en boucle).

## Performance

- [ ] Requêtes simples (pas de N+1 — utiliser `joinedload` ou batch SELECT).
- [ ] Index utilisés (vérifier avec EXPLAIN ANALYZE pour endpoints fréquents).
- [ ] Pagination pour listes potentiellement longues (`limit` cap à 500).
- [ ] Cache Redis pour réponses chères (combat report, ranking si possible).
