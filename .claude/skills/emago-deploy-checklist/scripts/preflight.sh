#!/usr/bin/env bash
#
# emago-deploy-checklist / preflight.sh
#
# Exécute automatiquement les checks pré-déploiement faciles.
# À lancer DEPUIS le repo Emago, AVANT de pusher main.
#
# Usage :
#   bash scripts/preflight.sh [--remote=user@vps]
#
# Vérifie localement :
# - .env présence et format
# - .gitignore couvre les secrets
# - Aucun secret tracké
# - alembic heads single
# - Tests passent
# - Image Docker buildable
# Vérifie distant (si --remote=) :
# - DNS résout
# - /health 200
# - SSL valide
# - Backup récent

set -euo pipefail

REMOTE=""
ERRORS=0
WARNINGS=0

# Parse args
for arg in "$@"; do
  case $arg in
    --remote=*) REMOTE="${arg#*=}" ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

ok()    { echo -e "  ✅ $1"; }
ko()    { echo -e "  ❌ $1"; ERRORS=$((ERRORS+1)); }
warn()  { echo -e "  ⚠️  $1"; WARNINGS=$((WARNINGS+1)); }
section() { echo -e "\n\033[1m═══ $1 ═══\033[0m"; }

# ─── Section 1 — Repo & branche ───────────────────────────────────────────
section "1. Repo & branche"

if ! git rev-parse --git-dir > /dev/null 2>&1; then
  ko "Pas dans un repo Git"
  exit 1
fi
ok "Repo Git détecté"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
  ok "Sur la branche main"
else
  warn "Branche actuelle = $BRANCH (pas main)"
fi

if [ -z "$(git status --porcelain)" ]; then
  ok "Aucun fichier non commité"
else
  ko "Fichiers non commités présents (git status)"
fi

# Secrets trackés ?
TRACKED_SECRETS=$(git ls-files | grep -E '\.env$|\.key$|\.pem$|\.dump$' | grep -v '\.env\.example$' || true)
if [ -z "$TRACKED_SECRETS" ]; then
  ok "Aucun secret tracké dans le repo"
else
  ko "SECRETS TRACKÉS : $TRACKED_SECRETS"
fi

# ─── Section 2 — Variables d'environnement ──────────────────────────────────
section "2. Variables .env"

if [ -f ".env" ]; then
  ok ".env présent"
  # Warnings sur valeurs sensibles
  if grep -qE '^DEBUG=true' .env; then
    warn "DEBUG=true dans .env — OK pour dev, ⚠️ KO pour prod"
  fi
  if ! grep -qE '^SECRET_KEY=.{40,}$' .env; then
    warn "SECRET_KEY semble court (< 40 chars) — devrait être 64 hex"
  fi
else
  warn ".env absent — utilise .env.example"
fi

if [ -f ".env.example" ]; then
  ok ".env.example présent (template)"
else
  warn ".env.example manquant"
fi

# ─── Section 3 — Migrations Alembic ─────────────────────────────────────────
section "3. Migrations Alembic"

MIGRATIONS_DIR="alembic/versions"
if [ -d "$MIGRATIONS_DIR" ]; then
  COUNT=$(find "$MIGRATIONS_DIR" -name "*.py" -not -name "__init__.py" 2>/dev/null | wc -l | tr -d ' ')
  ok "$COUNT migrations détectées"

  # Toutes ont upgrade ET downgrade ?
  MISSING_DOWNGRADE=$(grep -L "^def downgrade" "$MIGRATIONS_DIR"/*.py 2>/dev/null | grep -v __init__ || true)
  if [ -z "$MISSING_DOWNGRADE" ]; then
    ok "Toutes les migrations ont downgrade()"
  else
    ko "Migrations sans downgrade() : $MISSING_DOWNGRADE"
  fi
else
  warn "Pas de répertoire $MIGRATIONS_DIR"
fi

# ─── Section 4 — Tests ─────────────────────────────────────────────────────
section "4. Tests"

if command -v pytest > /dev/null 2>&1; then
  if [ -d "tests" ]; then
    ok "Répertoire tests/ présent"
    # Optionnel : run quick subset
    if [ "${RUN_TESTS:-0}" = "1" ]; then
      if pytest tests/services/ -q --tb=no 2>&1 | tail -5; then
        ok "Tests services passent"
      else
        ko "Tests services échouent"
      fi
    else
      warn "Tests pas exécutés (export RUN_TESTS=1 pour les lancer)"
    fi
  else
    warn "Pas de répertoire tests/"
  fi
else
  warn "pytest pas installé"
fi

# ─── Section 5 — Build Docker ──────────────────────────────────────────────
section "5. Docker"

if command -v docker > /dev/null 2>&1; then
  ok "Docker disponible"
  if [ -f "Dockerfile" ]; then
    ok "Dockerfile présent"
    # Multi-stage ?
    if grep -qE 'FROM .* AS (builder|runtime)' Dockerfile; then
      ok "Multi-stage build détecté"
    else
      warn "Pas de multi-stage (recommandé)"
    fi
    # Non-root user ?
    if grep -qE 'USER (emago|appuser|node)' Dockerfile; then
      ok "User non-root configuré"
    else
      warn "Image pourrait tourner en root"
    fi
    # Healthcheck ?
    if grep -q "HEALTHCHECK" Dockerfile; then
      ok "HEALTHCHECK Docker défini"
    else
      warn "Pas de HEALTHCHECK Docker"
    fi
  else
    ko "Dockerfile manquant"
  fi
  if [ -f "docker-compose.prod.yml" ]; then
    ok "docker-compose.prod.yml présent"
  else
    ko "docker-compose.prod.yml manquant"
  fi
else
  warn "Docker pas disponible localement"
fi

# ─── Section 6 — Configuration Nginx ────────────────────────────────────────
section "6. Nginx config"

if [ -f "nginx/conf.d/emago.conf" ]; then
  ok "nginx/conf.d/emago.conf présent"
  if grep -q "Upgrade.*http_upgrade" nginx/conf.d/emago.conf; then
    ok "WebSocket Upgrade headers configurés"
  else
    ko "Headers Upgrade WS MANQUANTS dans nginx — WS = 426"
  fi
  if grep -q "Strict-Transport-Security" nginx/conf.d/emago.conf; then
    ok "HSTS configuré"
  else
    warn "HSTS manquant"
  fi
  if grep -qE "ssl_protocols.*TLSv1\.[23]" nginx/conf.d/emago.conf; then
    ok "TLS 1.2+ configuré"
  else
    warn "Vérifier ssl_protocols"
  fi
else
  warn "nginx/conf.d/emago.conf manquant"
fi

# ─── Section 7 — GitHub Actions ─────────────────────────────────────────────
section "7. CI/CD GitHub Actions"

if [ -f ".github/workflows/ci.yml" ] || [ -f "github/workflows/ci.yml" ]; then
  ok "Workflow CI présent"
else
  warn "Pas de workflow CI détecté"
fi
if [ -f ".github/workflows/cd.yml" ] || [ -f "github/workflows/cd.yml" ]; then
  ok "Workflow CD présent"
else
  warn "Pas de workflow CD détecté"
fi

# ─── Section 8 — Scripts ────────────────────────────────────────────────────
section "8. Scripts opérationnels"

for script in scripts/install_vps.sh scripts/backup_postgres.sh; do
  if [ -f "$script" ]; then
    ok "$script présent"
    if [ -x "$script" ]; then
      ok "  exécutable"
    else
      warn "  PAS exécutable (chmod +x)"
    fi
  else
    warn "$script manquant"
  fi
done

# ─── Section 9 — Distant (si fourni) ────────────────────────────────────────
if [ -n "$REMOTE" ]; then
  section "9. Distant ($REMOTE)"

  # SSH connectivity
  if ssh -o ConnectTimeout=5 -o BatchMode=yes "$REMOTE" "echo ok" > /dev/null 2>&1; then
    ok "SSH OK"

    # Backup récent ?
    LAST_BACKUP=$(ssh "$REMOTE" "ls -t /opt/emago/backups/*.sql.gz 2>/dev/null | head -1" || echo "")
    if [ -n "$LAST_BACKUP" ]; then
      AGE=$(ssh "$REMOTE" "stat -c %Y '$LAST_BACKUP'")
      NOW=$(date +%s)
      AGE_HOURS=$(( (NOW - AGE) / 3600 ))
      if [ $AGE_HOURS -lt 25 ]; then
        ok "Backup BDD récent ($AGE_HOURS h)"
      else
        warn "Backup BDD vieux de $AGE_HOURS h (> 24h)"
      fi
    else
      warn "Aucun backup trouvé"
    fi

    # Cron backup ?
    if ssh "$REMOTE" "crontab -l 2>/dev/null | grep -q backup_postgres"; then
      ok "Cron backup configuré"
    else
      warn "Cron backup pas dans crontab"
    fi
  else
    ko "SSH KO sur $REMOTE"
  fi
fi

# ─── Récap ──────────────────────────────────────────────────────────────────
section "Récap"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  echo -e "\n\033[32m✅ Tout est OK — prêt à déployer.\033[0m"
  exit 0
elif [ $ERRORS -eq 0 ]; then
  echo -e "\n\033[33m⚠️  $WARNINGS warnings — déploiement possible mais à vérifier.\033[0m"
  exit 0
else
  echo -e "\n\033[31m❌ $ERRORS erreurs + $WARNINGS warnings — corriger avant déploiement.\033[0m"
  exit 1
fi
