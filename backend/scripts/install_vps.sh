#!/bin/bash
# =============================================================================
# scripts/install_vps.sh — Installation initiale sur VPS vierge
# Agent 9 — DevOps | Sprint 1
#
# Prérequis : Ubuntu 22.04 LTS, accès root
# Usage : bash install_vps.sh
# =============================================================================

set -euo pipefail

DEPLOY_DIR="/opt/emago"
DEPLOY_USER="emago"
REPO_URL="https://github.com/YOUR_ORG/emago.git"  # ← à adapter

echo "=== [1/7] Mise à jour système ==="
apt-get update && apt-get upgrade -y

echo "=== [2/7] Installation Docker ==="
apt-get install -y ca-certificates curl gnupg lsb-release
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "=== [3/7] Création utilisateur ${DEPLOY_USER} ==="
useradd -m -s /bin/bash "${DEPLOY_USER}" || true
usermod -aG docker "${DEPLOY_USER}"

echo "=== [4/7] Clone du dépôt ==="
mkdir -p "${DEPLOY_DIR}"
git clone "${REPO_URL}" "${DEPLOY_DIR}"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_DIR}"

echo "=== [5/7] Configuration .env ==="
echo "⚠️  Copier manuellement le fichier .env dans ${DEPLOY_DIR}/backend/"
echo "    Modèle : ${DEPLOY_DIR}/backend/.env.example"
echo "    Appuyer sur Entrée après avoir créé le .env..."
read -r

echo "=== [6/7] Démarrage de la stack ==="
cd "${DEPLOY_DIR}/backend"
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d db redis
sleep 10
docker compose -f docker-compose.prod.yml run --rm api /opt/venv/bin/alembic upgrade head
docker compose -f docker-compose.prod.yml up -d

echo "=== [7/7] Vérification ==="
sleep 5
curl -sf http://localhost:8000/health && echo "✓ API OK" || echo "✗ API KO"

echo ""
echo "=== Installation terminée ==="
echo "Étapes restantes :"
echo "  1. Configurer DNS : pointer YOUR_DOMAIN.COM vers $(curl -s ifconfig.me)"
echo "  2. Obtenir certificat SSL : docker compose -f docker-compose.prod.yml run --rm certbot certonly --webroot -w /var/www/certbot -d YOUR_DOMAIN.COM"
echo "  3. Recharger Nginx : docker compose -f docker-compose.prod.yml exec nginx nginx -s reload"
echo "  4. Configurer le cron de backup : crontab -e"
echo "     0 3 * * * ${DEPLOY_DIR}/backend/scripts/backup_postgres.sh >> /var/log/emago_backup.log 2>&1"
