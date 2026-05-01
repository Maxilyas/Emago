#!/bin/bash
# =============================================================================
# scripts/backup_postgres.sh — Sauvegarde quotidienne PostgreSQL
# Agent 9 — DevOps | Sprint 1
#
# Usage (cron quotidien à 3h UTC sur le VPS) :
#   0 3 * * * /opt/emago/scripts/backup_postgres.sh >> /var/log/emago_backup.log 2>&1
#
# Variables d'environnement requises (charger depuis .env) :
#   POSTGRES_PASSWORD
#   BACKUP_S3_BUCKET (optionnel — pour upload S3/Hetzner Object Storage)
#   BACKUP_RETAIN_DAYS (défaut : 30)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${PROJECT_DIR}/backups"
BACKUP_FILE="${BACKUP_DIR}/emago_${TIMESTAMP}.sql.gz"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-30}"

# Charger les variables d'environnement
if [[ -f "${PROJECT_DIR}/.env" ]]; then
    set -a
    source "${PROJECT_DIR}/.env"
    set +a
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Début backup PostgreSQL"

# Créer le répertoire de backup si absent
mkdir -p "${BACKUP_DIR}"

# Dump PostgreSQL via le conteneur Docker
docker compose -f "${PROJECT_DIR}/docker-compose.prod.yml" exec -T db \
    pg_dump -U emago -d emago --no-owner --no-acl \
    | gzip -9 > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup créé : ${BACKUP_FILE} (${BACKUP_SIZE})"

# Upload optionnel vers S3 / Hetzner Object Storage
if [[ -n "${BACKUP_S3_BUCKET:-}" ]]; then
    if command -v aws &>/dev/null; then
        aws s3 cp "${BACKUP_FILE}" "s3://${BACKUP_S3_BUCKET}/emago_backups/$(basename "${BACKUP_FILE}")"
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Upload S3 OK : ${BACKUP_S3_BUCKET}"
    else
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] WARN : aws CLI introuvable, upload skipped"
    fi
fi

# Purge des backups anciens
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Purge backups > ${RETAIN_DAYS} jours"
find "${BACKUP_DIR}" -name "emago_*.sql.gz" -mtime "+${RETAIN_DAYS}" -delete

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup terminé avec succès"
