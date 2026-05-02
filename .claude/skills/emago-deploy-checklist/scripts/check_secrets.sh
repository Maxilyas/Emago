#!/usr/bin/env bash
#
# emago-deploy-checklist / check_secrets.sh
#
# Vérifie qu'aucun secret n'a fuité dans le repo Git Emago.
# À lancer en CI pour bloquer les commits qui contiennent des secrets.

set -euo pipefail

ERRORS=0

ok()   { echo "  ✅ $1"; }
ko()   { echo "  ❌ $1"; ERRORS=$((ERRORS+1)); }
section() { echo -e "\n\033[1m═══ $1 ═══\033[0m"; }

section "1. Fichiers secrets trackés"

# Patterns de fichiers qui ne doivent JAMAIS être trackés
DANGEROUS=$(git ls-files | grep -E '\.env$|\.env\..*[^le]$|\.key$|\.pem$|\.p12$|\.dump$|\.sql$|secret|credentials' | grep -v '\.env\.example$' || true)

if [ -z "$DANGEROUS" ]; then
  ok "Aucun fichier secret tracké"
else
  ko "FICHIERS DANGEREUX TRACKÉS :"
  echo "$DANGEROUS" | sed 's/^/      /'
fi

section "2. Patterns de secrets dans le code"

# Recherche dans tous les fichiers trackés sauf binaires
PATTERNS=(
  "SECRET_KEY\s*=\s*['\"][a-f0-9]{30,}['\"]"           # SECRET_KEY hex committed
  "POSTGRES_PASSWORD\s*=\s*['\"][^'\"]{4,}['\"]"        # password commited
  "REDIS_PASSWORD\s*=\s*['\"][^'\"]{4,}['\"]"
  "AWS_SECRET_ACCESS_KEY\s*=\s*['\"][^'\"]{20,}['\"]"
  "AWS_ACCESS_KEY_ID\s*=\s*['\"]AKIA[A-Z0-9]{16}['\"]"
  "(?i)password\s*=\s*['\"][^'\"]{4,}['\"]"             # généric password=
  "(?i)api_key\s*=\s*['\"][^'\"]{16,}['\"]"
  "(?i)bearer\s+[A-Za-z0-9]{40,}"                       # Bearer tokens
  "-----BEGIN.*PRIVATE KEY"                             # private keys inline
  "ssh-rsa\s+AAAA[A-Za-z0-9+/=]{300,}"                  # SSH private keys
)

FOUND_SECRETS=0
for pattern in "${PATTERNS[@]}"; do
  MATCHES=$(git grep -nE "$pattern" 2>/dev/null | grep -v -E '(\.env\.example|tests/|\.md:|docs/|README|CHANGELOG)' || true)
  if [ -n "$MATCHES" ]; then
    FOUND_SECRETS=1
    ko "Pattern '$pattern' :"
    echo "$MATCHES" | head -3 | sed 's/^/      /'
  fi
done

if [ $FOUND_SECRETS -eq 0 ]; then
  ok "Aucun pattern de secret détecté"
fi

section "3. .gitignore"

REQUIRED_PATTERNS=(
  ".env"
  "*.key"
  "*.pem"
)

if [ -f .gitignore ]; then
  for p in "${REQUIRED_PATTERNS[@]}"; do
    if grep -qF "$p" .gitignore; then
      ok ".gitignore contient '$p'"
    else
      ko ".gitignore N'EXCLUT PAS '$p'"
    fi
  done
else
  ko ".gitignore manquant"
fi

section "4. Historique Git récent"

# Dans les 50 derniers commits
SECRETS_IN_HISTORY=$(git log -p -50 2>/dev/null | grep -iE '^\+.*(secret_key|postgres_password|redis_password|aws_secret).*[a-zA-Z0-9]{20,}' | head -3 || true)

if [ -z "$SECRETS_IN_HISTORY" ]; then
  ok "Aucun secret apparent dans les 50 derniers commits"
else
  ko "Secrets potentiels dans l'historique récent :"
  echo "$SECRETS_IN_HISTORY" | sed 's/^/      /'
  echo ""
  echo "      Si confirmés : ROTATION IMMÉDIATE des secrets + force-push avec rewrite."
fi

# ─── Récap ──────────────────────────────────────────────────────────────────
section "Récap"

if [ $ERRORS -eq 0 ]; then
  echo -e "\n\033[32m✅ Aucun secret détecté.\033[0m"
  exit 0
else
  echo -e "\n\033[31m❌ $ERRORS problèmes potentiels.\033[0m"
  echo ""
  echo "Actions recommandées :"
  echo "  1. Si fichier secret tracké : git rm --cached <file> + ajouter à .gitignore"
  echo "  2. Si secret dans l'historique : git filter-branch ou bfg-repo-cleaner + ROTATION secrets"
  echo "  3. Si pattern faux positif : ajuster les regex dans ce script"
  exit 1
fi
