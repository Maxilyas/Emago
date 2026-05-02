# `.env` Emago — variables requises

## Production complète

```bash
# ─── Auth & sécurité ────────────────────────────────────────────────────────
# Générer avec : python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<64 chars hex aléatoires>

ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# ─── Database ───────────────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://emago:<POSTGRES_PASSWORD>@db:5432/emago
POSTGRES_PASSWORD=<min 24 chars, mix lettres/chiffres/symboles>

# ─── Redis ──────────────────────────────────────────────────────────────────
REDIS_URL=redis://:<REDIS_PASSWORD>@redis:6379/0
REDIS_PASSWORD=<min 24 chars>

# ─── App ────────────────────────────────────────────────────────────────────
APP_NAME=Emago
APP_VERSION=0.1.0           # MAJ à chaque release
DEBUG=false                  # ⚠️ CRITIQUE : false en prod (sinon Swagger UI exposé)

# ─── Game tuning ────────────────────────────────────────────────────────────
RESOURCE_TICK_SECONDS=60
BUILD_QUEUE_MAX=5
FLEET_SPEED_BASE=1.0
RANKING_RECALC_MINUTES=10
FORGE_DURATION_HOURS=8

# ─── Optionnel : backup S3 ──────────────────────────────────────────────────
# BACKUP_S3_BUCKET=emago-backups
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
# AWS_DEFAULT_REGION=eu-west-3

# ─── Optionnel : monitoring ─────────────────────────────────────────────────
# SENTRY_DSN=https://...
# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## Dev local (pour référence)

```bash
SECRET_KEY=467651bf5af95b0140238e48b3fe7d7be50577c0528ed2999800f11c37ad6b32
DATABASE_URL=postgresql+asyncpg://emago:emago_dev@localhost:5432/emago
REDIS_URL=redis://localhost:6379/0
APP_NAME=Emago
APP_VERSION=0.1.0
DEBUG=true                   # OK en dev — active Swagger UI sur /docs
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
RESOURCE_TICK_SECONDS=60
BUILD_QUEUE_MAX=5
FLEET_SPEED_BASE=1.0
RANKING_RECALC_MINUTES=10
FORGE_DURATION_HOURS=8
```

## Permissions du fichier

```bash
chmod 600 /opt/emago/.env
chown emago:emago /opt/emago/.env
```

## Ne JAMAIS commiter

`.gitignore` doit contenir :
```
.env
.env.*
!.env.example
*.key
*.pem
*.p12
secrets/
```

## Génération sécurisée des secrets

```bash
# SECRET_KEY (Python required)
python -c "import secrets; print(secrets.token_hex(32))"

# POSTGRES_PASSWORD / REDIS_PASSWORD (pas de caractères spéciaux problématiques pour URL)
openssl rand -base64 32 | tr -d '/+=' | head -c 32
```

## Validation

À l'init, le code Pydantic-settings valide la présence des champs obligatoires :
- `SECRET_KEY`
- `DATABASE_URL`

Si manquants → l'application refuse de démarrer.

## Bypass session var (cas migrations contrôlées)

Pour les migrations Alembic qui doivent modifier des colonnes immuables, utiliser temporairement :

```sql
SET LOCAL emago.bypass_stats_trigger = 'true';
UPDATE ships SET base_stats = ... WHERE ...;
SET LOCAL emago.bypass_stats_trigger = '';
```

**Ne jamais** activer cette variable au niveau session ou globalement — uniquement transaction-local dans une migration explicite.

## Audit secrets

Pour vérifier qu'aucun secret n'a fuité dans le repo :

```bash
git log --all -p | grep -iE 'secret_key|postgres_password|redis_password' | head
git ls-files | grep -E '\.env$|\.key$|\.pem$|secret'
```

Si quelque chose remonte : **rotation immédiate** des secrets compromis + force push hors historique.
