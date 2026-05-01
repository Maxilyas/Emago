# =============================================================================
# Dockerfile — Production multi-stage
# Agent 9 — DevOps
# Sprint 1 — Infrastructure prod
#
# Stage 1 (builder) : installe les dépendances dans un venv isolé
# Stage 2 (runtime) : image légère, copie uniquement le venv + le code
#
# Optimisations :
#   - Pas de hot-reload (pas de volume ./app en prod)
#   - Image python:3.12-slim (sans les outils de build)
#   - .dockerignore exclut __pycache__, .env, tests, etc.
# =============================================================================

# ── Stage 1 : build ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Copier uniquement requirements pour profiter du cache layer Docker
COPY requirements.txt .

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ── Stage 2 : runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Métadonnées
LABEL org.opencontainers.image.title="Emago Backend"
LABEL org.opencontainers.image.description="FastAPI backend — Emago game server"

# Sécurité : utilisateur non-root
RUN addgroup --system emago && adduser --system --ingroup emago emago

WORKDIR /app

# Copier le venv depuis le builder
COPY --from=builder /opt/venv /opt/venv

# Copier le code source (pas les tests, pas les .env)
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Variables d'environnement runtime
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Propriétaire : utilisateur emago
RUN chown -R emago:emago /app
USER emago

EXPOSE 8000

# Démarrage : 4 workers Uvicorn avec reload désactivé
# En prod, les migrations Alembic sont jouées séparément (entrypoint ou CI)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
