#!/usr/bin/env bash
#
# emago-deploy-checklist / postdeploy.sh
#
# Vérifications post-déploiement Emago.
# Lance les smoke tests sur l'environnement déployé.
#
# Usage :
#   bash scripts/postdeploy.sh --domain=emago.example.com [--smoke-token=<jwt>]

set -euo pipefail

DOMAIN=""
TOKEN=""
ERRORS=0

for arg in "$@"; do
  case $arg in
    --domain=*) DOMAIN="${arg#*=}" ;;
    --smoke-token=*) TOKEN="${arg#*=}" ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if [ -z "$DOMAIN" ]; then
  echo "Usage: $0 --domain=emago.yourdomain.com [--smoke-token=JWT]" >&2
  exit 2
fi

ok()   { echo "  ✅ $1"; }
ko()   { echo "  ❌ $1"; ERRORS=$((ERRORS+1)); }
warn() { echo "  ⚠️  $1"; }
section() { echo -e "\n\033[1m═══ $1 ═══\033[0m"; }

# ─── 1. Health endpoint ────────────────────────────────────────────────────
section "1. /health"

HEALTH=$(curl -sf "https://$DOMAIN/health" 2>&1) || HEALTH=""
if [ -n "$HEALTH" ]; then
  if echo "$HEALTH" | grep -q '"status":"ok"'; then
    ok "Health endpoint répond 200 OK"
    VERSION=$(echo "$HEALTH" | grep -oE '"version":"[^"]*"' | cut -d'"' -f4)
    [ -n "$VERSION" ] && ok "Version : $VERSION"
  else
    ko "Health répond mais status != ok"
    echo "    $HEALTH"
  fi
else
  ko "Health endpoint NE RÉPOND PAS"
fi

# ─── 2. SSL ────────────────────────────────────────────────────────────────
section "2. SSL"

SSL_INFO=$(curl -sI "https://$DOMAIN" 2>&1 | head -5) || SSL_INFO=""
if echo "$SSL_INFO" | grep -qiE "HTTP/[12].* 200"; then
  ok "HTTPS répond 200"
else
  warn "HTTPS pas 200 (peut-être SPA / 304)"
fi

if echo "$SSL_INFO" | grep -qi "strict-transport-security"; then
  ok "HSTS header présent"
else
  warn "HSTS manquant"
fi

# ─── 3. /api/v1 ────────────────────────────────────────────────────────────
section "3. /api/v1"

# Endpoint public ranking
RANKING=$(curl -sf "https://$DOMAIN/api/v1/ranking?limit=1" 2>&1) || RANKING=""
if [ -n "$RANKING" ] && echo "$RANKING" | grep -q "rank"; then
  ok "/api/v1/ranking répond"
else
  ko "/api/v1/ranking ne répond pas correctement"
fi

# ─── 4. WebSocket ──────────────────────────────────────────────────────────
section "4. WebSocket"

# Test bas niveau : Upgrade headers
WS_RESPONSE=$(curl -i -s -o /dev/null -w "%{http_code}" \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Sec-WebSocket-Version: 13" \
  "https://$DOMAIN/ws" 2>&1) || WS_RESPONSE=""

if [ "$WS_RESPONSE" = "101" ] || [ "$WS_RESPONSE" = "401" ] || [ "$WS_RESPONSE" = "403" ]; then
  ok "WebSocket Upgrade géré (code $WS_RESPONSE — 101 normal sans token, 401/403 si auth requise)"
elif [ "$WS_RESPONSE" = "426" ]; then
  ko "WebSocket renvoie 426 — Nginx ne proxifie pas Upgrade headers !"
else
  warn "WebSocket code $WS_RESPONSE (vérifier manuellement)"
fi

# Test fonctionnel si token fourni
if [ -n "$TOKEN" ]; then
  if command -v websocat > /dev/null 2>&1; then
    WS_MSG=$(timeout 5 websocat "wss://$DOMAIN/ws?token=$TOKEN" -n1 2>&1) || WS_MSG=""
    if echo "$WS_MSG" | grep -q '"type":"connected"'; then
      ok "WebSocket auth fonctionne (message connected reçu)"
    else
      warn "WebSocket connect token : pas de message connected"
    fi
  else
    warn "websocat pas installé — skip test WS auth"
  fi
fi

# ─── 5. Smoke test login ───────────────────────────────────────────────────
section "5. /auth/login"

# Test avec credentials inexistants : doit renvoyer 401 anti-énumération
LOGIN_RES=$(curl -s -o /dev/null -w "%{http_code}" -X POST "https://$DOMAIN/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"nonexistent@x.com","password":"any"}')

if [ "$LOGIN_RES" = "401" ]; then
  ok "Login email inexistant renvoie 401 (anti-énumération)"
else
  ko "Login renvoie $LOGIN_RES (attendu 401)"
fi

# ─── 6. /api/v1/alliances (public) ─────────────────────────────────────────
section "6. /api/v1/alliances"

ALLIANCES=$(curl -sf "https://$DOMAIN/api/v1/alliances" 2>&1) || ALLIANCES=""
if [ -n "$ALLIANCES" ]; then
  ok "/api/v1/alliances répond (public)"
else
  warn "/api/v1/alliances ne répond pas"
fi

# ─── Récap ──────────────────────────────────────────────────────────────────
section "Récap"

if [ $ERRORS -eq 0 ]; then
  echo -e "\n\033[32m✅ Post-deploy OK — déploiement validé.\033[0m"
  exit 0
else
  echo -e "\n\033[31m❌ $ERRORS erreurs détectées — investiguer ou rollback.\033[0m"
  echo "Voir references/rollback_paths.md pour les options."
  exit 1
fi
