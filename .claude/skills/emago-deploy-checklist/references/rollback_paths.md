# Rollback paths Emago

Trois méthodes selon la nature de l'incident.

## Méthode 1 — Rollback image Docker

**Quand** : bug dans l'API, pas de migration BDD problématique, image précédente fonctionne.

**Vitesse** : ~30 secondes.

```bash
ssh emago@vps
cd /opt/emago

# Lister les commits récents
git log --oneline -5

# Checkout commit précédent (avant le déploiement KO)
git checkout <previous-sha>

# Rebuild + restart api uniquement
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d --no-deps api

# Vérification
sleep 5
curl -sf https://YOUR_DOMAIN.COM/health
docker compose -f docker-compose.prod.yml logs --tail=50 api
```

**Variante via tag image GHCR** :
```bash
# Si une image image:sha-XXX est encore sur GHCR :
docker compose -f docker-compose.prod.yml pull api  # tire le tag du fichier compose
# OU modifier compose pour utiliser l'image précédente
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

## Méthode 2 — Rollback migration Alembic

**Quand** : la migration a tout cassé (perf, incompatibilité, trigger qui block).

**Attention** : `downgrade -1` peut perdre des données ajoutées par la migration. **Backup obligatoire avant**.

```bash
ssh emago@vps
cd /opt/emago

# Voir l'état actuel
docker compose -f docker-compose.prod.yml exec api alembic current
docker compose -f docker-compose.prod.yml exec api alembic history

# Rollback d'une migration
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1

# Vérifier
docker compose -f docker-compose.prod.yml exec api alembic current

# Restart api pour s'aligner sur le schéma rollbacké
docker compose -f docker-compose.prod.yml restart api
```

Si le code déployé dépend de la nouvelle migration → faire AUSSI méthode 1 pour aligner code et schéma.

## Méthode 3 — Restauration backup BDD

**Quand** : data corruption, suppression accidentelle, migration non rollbackable.

**Vitesse** : 5-30 minutes selon taille DB.

```bash
ssh emago@vps
cd /opt/emago

# 1. Stopper l'api pour éviter les writes pendant restore
docker compose -f docker-compose.prod.yml stop api

# 2. Identifier le backup à restaurer
ls -lh /opt/emago/backups/ | tail -10

# 3. Décompresser
BACKUP_FILE=/opt/emago/backups/emago_<DATE>.sql.gz
gunzip -k "$BACKUP_FILE"  # -k garde l'archive originale
SQL_FILE="${BACKUP_FILE%.gz}"

# 4. (Optionnel) sauvegarder l'état actuel avant restauration
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U emago emago | gzip > /opt/emago/backups/before_restore_$(date +%Y%m%d_%H%M).sql.gz

# 5. Drop + recréer la BDD
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres <<EOF
DROP DATABASE IF EXISTS emago;
CREATE DATABASE emago OWNER emago;
EOF

# 6. Restaurer
docker compose -f docker-compose.prod.yml exec -T db psql -U emago -d emago < "$SQL_FILE"

# 7. Restart api
docker compose -f docker-compose.prod.yml up -d api

# 8. Vérifier
sleep 10
curl -sf https://YOUR_DOMAIN.COM/health
docker compose -f docker-compose.prod.yml logs --tail=50 api
```

## Méthode 4 — Rollback complet (image + migration)

**Quand** : déploiement majeur cassé sur tous les fronts.

```bash
# 1. Stopper api
docker compose -f docker-compose.prod.yml stop api

# 2. Rollback migration
docker compose -f docker-compose.prod.yml exec api alembic downgrade <previous-revision>

# 3. Checkout commit précédent
git checkout <previous-sha>

# 4. Rebuild + start
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d api

# 5. Vérification
sleep 5
curl -sf https://YOUR_DOMAIN.COM/health
```

## Décision rollback flowchart

```
Incident détecté
    │
    ▼
Erreur 5xx massive ?
    │ oui
    ├─→ Migration récente ? ─ oui → Méthode 4 (rollback complet)
    │                       └ non → Méthode 1 (rollback image)
    │
Performance dégradée ?
    │ oui → EXPLAIN ANALYZE → identifier index manquant → Phase 2 fix (pas rollback)
    │
Data corruption ?
    │ oui → Méthode 3 (restauration backup)
    │
WebSocket cassé ?
    │ oui → Vérifier nginx config → restart nginx (pas rollback)
    │
Auth cassée (tous tokens invalides) ?
    │ oui → SECRET_KEY a changé entre 2 deploys → restaurer .env précédent + restart api
```

## Préventions pour le prochain déploiement

Après un rollback, **toujours** documenter :
- ☐ Cause exacte du problème.
- ☐ Pourquoi pas détecté en CI/staging.
- ☐ Test à ajouter pour anti-régression.
- ☐ Mise à jour pré-flight checklist si nouveau cas.
- ☐ Postmortem dans `docs/decisions/` si systémique.

## Contacts urgence

| Rôle | Quand contacter |
|---|---|
| Antoine (mainteneur) | Tout incident production |
| Hostingue VPS (Hetzner/OVH) | Si VPS lui-même down |
| Registrar DNS | Si DNS résolution problème |
| Cloudflare (si utilisé) | Si proxy CDN problème |

## Vitesses cibles

| Action | Cible |
|---|---|
| Détection incident (via Uptime Kuma) | < 1 min |
| Décision rollback vs hotfix | < 5 min |
| Rollback image (méthode 1) | < 30 sec |
| Rollback migration (méthode 2) | < 2 min |
| Restauration backup (méthode 3) | < 30 min |
| Communication aux joueurs | < 10 min après détection |

## Smoke tests post-rollback

```bash
# Health
curl -sf https://YOUR_DOMAIN.COM/health
# Login
curl -X POST https://YOUR_DOMAIN.COM/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@test.com","password":"smoketest123"}'
# Hangar
curl -H "Authorization: Bearer $TOKEN" https://YOUR_DOMAIN.COM/api/v1/ships
# WS
websocat "wss://YOUR_DOMAIN.COM/ws?token=$TOKEN" | head -1
```

Si tous OK → rollback réussi.
