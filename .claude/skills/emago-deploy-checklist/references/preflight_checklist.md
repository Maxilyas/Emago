# Checklist pré-déploiement Emago

Tous les items doivent être ✅ avant un push prod.

## 1. Repo & branche

- ☐ La branche déployée est `main` (sauf cas explicite).
- ☐ Aucun fichier non commité (`git status`).
- ☐ Aucun fichier secret tracké (`.env`, clés, dumps) — `git ls-files | grep -E '\.env$|\.key$|\.pem$|\.dump$'` doit être vide.
- ☐ Pas de `print()`, `console.log()`, ou TODO critique dans le diff.
- ☐ Le tag de release est cohérent (`v0.X.Y` semver).

## 2. Variables d'environnement (`.env` prod)

Vérifier le `.env` sur le VPS prod :

- ☐ `SECRET_KEY` : 64 chars hexadécimaux (généré par `python -c "import secrets; print(secrets.token_hex(32))"`).
- ☐ `DEBUG=false` (CRITIQUE — sinon Swagger UI exposé en prod + CORS localhost autorisé).
- ☐ `DATABASE_URL` : `postgresql+asyncpg://emago:<password>@db:5432/emago`.
- ☐ `POSTGRES_PASSWORD` : mot de passe fort (≥ 24 chars, mix lettres/chiffres/symboles).
- ☐ `REDIS_URL` : `redis://:<password>@redis:6379/0`.
- ☐ `REDIS_PASSWORD` : mot de passe fort.
- ☐ `APP_VERSION` : à jour (ex. `0.2.0`).
- ☐ `ACCESS_TOKEN_EXPIRE_MINUTES=60`, `REFRESH_TOKEN_EXPIRE_DAYS=30`.
- ☐ Game tuning : `RESOURCE_TICK_SECONDS=60`, `BUILD_QUEUE_MAX=5`, `FLEET_SPEED_BASE=1.0`, `RANKING_RECALC_MINUTES=10`, `FORGE_DURATION_HOURS=8`.
- ☐ `.env` chmod 600 (root-only readable).

## 3. Migrations Alembic

- ☐ Pas de migration "fantôme" (alembic heads doit afficher 1 head).
- ☐ Toutes les migrations ont `upgrade()` ET `downgrade()`.
- ☐ Tester `alembic upgrade head` puis `alembic downgrade -1` puis re-`upgrade head` en local.
- ☐ Si migration touche `base_stats` ou data critique : **backup obligatoire avant prod**.
- ☐ Documenter dans le commit message : breaking change ? Data loss ?

## 4. Tests CI

- ☐ `pytest tests/services/` passe (47+ tests).
- ☐ `pytest tests/routers/` passe (28+ tests, plus si Phase 2).
- ☐ Coverage ≥ 70 % sur services métier critiques (ship_build, ship_stats, combat_engine, forge).
- ☐ `pip-audit` (si activé) : aucune vulnérabilité critique.
- ☐ `npm audit` (si activé) : aucune vulnérabilité critique.
- ☐ Linter (ruff/black) sans warnings non corrigés.

## 5. Build Docker

- ☐ Image buildable localement : `docker compose -f docker-compose.prod.yml build api`.
- ☐ Image en mode `target: runtime` (pas builder).
- ☐ Image utilise utilisateur non-root `emago`.
- ☐ HEALTHCHECK Docker présent dans le Dockerfile.
- ☐ Image taggable et pushable sur GHCR (`ghcr.io/<repo>/emago-api`).
- ☐ Taille image < 300 MB (alpine + multi-stage).

## 6. Configuration Nginx

- ☐ `nginx/nginx.conf` : worker_processes auto, gzip on, JSON access log.
- ☐ `nginx/conf.d/emago.conf` :
  - HTTP redirect → HTTPS (301).
  - HTTPS server avec ssl_certificate / ssl_certificate_key valides.
  - `ssl_protocols TLSv1.2 TLSv1.3` (pas TLS 1.0/1.1).
  - Security headers : HSTS 31536000, X-Content-Type-Options nosniff, X-Frame-Options SAMEORIGIN, CSP.
  - location `/api/` proxy_pass api:8000.
  - **location `/ws`** : `proxy_http_version 1.1`, `Upgrade $http_upgrade`, `Connection "upgrade"`, `proxy_buffering off`, `proxy_read_timeout 3600s`. **Sans ces headers, WS = 426.**
  - location `/` SPA fallback `try_files $uri $uri/ /index.html`.
- ☐ `nginx -t` (syntaxe valide).
- ☐ React build présent dans `frontend/dist/` (volumé sur Nginx).

## 7. Certbot SSL

- ☐ Certificat SSL valide pour le domaine cible (`certbot certificates`).
- ☐ Renouvellement automatique configuré (cron mensuel ou loop perpétuelle dans docker-compose.prod.yml).
- ☐ Test renouvellement à blanc : `docker compose run --rm certbot renew --dry-run`.

## 8. GitHub Secrets

Pour CI/CD automatique :

- ☐ `VPS_HOST` (IP ou DNS du VPS).
- ☐ `VPS_USER` (utilisateur SSH, ex. `emago`).
- ☐ `VPS_SSH_KEY` (clé privée SSH, **sans passphrase**).
- ☐ `VPS_DEPLOY_DIR` (ex. `/opt/emago`).
- ☐ `GITHUB_TOKEN` (auto pour GHCR).
- ☐ La clé SSH publique est dans `~/.ssh/authorized_keys` du user VPS.

## 9. Backup pg_dump

- ☐ Script `scripts/backup_postgres.sh` exécutable (`chmod +x`).
- ☐ Cron quotidien : `0 3 * * * /opt/emago/scripts/backup_postgres.sh >> /var/log/emago_backup.log 2>&1`.
- ☐ Au moins 1 backup récent dans `/opt/emago/backups/` (< 25h).
- ☐ Restauration testée au moins une fois (sur env staging) :
   ```
   gunzip emago_*.sql.gz && docker compose exec -T db psql -U emago -d emago < emago_*.sql
   ```
- ☐ (Optionnel) `BACKUP_S3_BUCKET` configuré pour upload off-site.

## 10. Monitoring & alerting

- ☐ Endpoint `/health` accessible publiquement (utilisé par Uptime Kuma).
- ☐ Uptime Kuma configuré avec monitors HTTP /health, TCP db:5432, TCP redis:6379.
- ☐ Alertes (email / Discord / Slack) en cas de KO.
- ☐ Logs JSON-structurés activés sur tous les services (driver json-file dans docker-compose.prod.yml).
- ☐ Rotation logs : max-size 10-20m, max-file 3-5.

## 11. Spécifique Emago — checks gameplay

- ☐ Trigger PG `prevent_base_stats_update` actif :
  ```sql
  SELECT * FROM pg_trigger WHERE tgname = 'prevent_base_stats_update';
  ```
- ☐ Indexes critiques scheduler créés :
  ```sql
  SELECT indexname FROM pg_indexes WHERE indexname IN (
    'idx_forge_queue_completed_at',
    'idx_fleets_arrives_at',
    'idx_build_queue_planet_pending'
  );
  ```
- ☐ Seed `scar_tags` chargé (au moins 30 entrées) :
  ```sql
  SELECT COUNT(*) FROM scar_tags;
  ```
- ☐ Tag Forge Dérive présent :
  ```sql
  SELECT * FROM scar_tags WHERE tag_code = 'born_in_drift';
  ```

## 12. Communication

- ☐ Ticket / PR mergée référençant ce déploiement.
- ☐ Changelog ou release notes prêts pour les joueurs (si breaking change).
- ☐ Annonce planifiée dans le canal joueurs (si interruption attendue).

## 13. Rollback plan

- ☐ Backup BDD < 24h disponible.
- ☐ Image Docker précédente accessible (GHCR tag `sha-<previous>` ou `latest-1`).
- ☐ Procédure rollback documentée (cf. `references/rollback_paths.md`).
- ☐ Au moins 1 personne joignable en cas de problème (24h post-deploy).

## 14. Rate limiting & sécurité

- ☐ Middleware `rate_limit.py` actif (Redis sliding-window).
- ☐ Limites configurées (`_LIMITS`) cohérentes avec attendus de prod.
- ☐ CSP raisonnablement stricte (cf. `references/env_template.md`).
- ☐ Pas de port db/redis exposé publiquement (`docker compose -f docker-compose.prod.yml ps` → seulement nginx exposé).

## 15. Vérifications finales

- ☐ Domaine résout correctement : `dig YOUR_DOMAIN.COM` retourne IP du VPS.
- ☐ Firewall configuré : ports 80, 443, 22 (SSH) ouverts ; reste fermé.
- ☐ SSH désactive password auth (`PasswordAuthentication no` dans sshd_config).
- ☐ User `emago` n'a PAS sudo sans password (sauf docker via groupe `docker`).
- ☐ Volumes Docker persistent les données critiques (postgres_data, redis_data, certbot_certs).

---

## Récap final avant push

> Si **tous les items ci-dessus** sont ✅, tu peux déployer.
>
> **Au moindre doute → STOP.** Mieux vaut 30 min de plus en pré-flight que 4h de panique post-incident.
