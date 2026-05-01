"""
app/middleware/rate_limit.py
Agent 5 — Développeur Backend | Sprint 2
Validation : Agent 8 — QA & Sécurité

Rate limiting par endpoint via Redis (sliding window counter).

Stratégie :
  - Clé Redis : ratelimit:{player_id}:{endpoint_tag}
  - Fenêtre glissante de 60 secondes
  - Limites par endpoint (voir _LIMITS)
  - 429 Too Many Requests avec header Retry-After

Décision technique (Agent 3) :
  Approche Redis > in-memory pour survivre aux redémarrages
  et rester compatible avec un futur scale horizontal.
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.redis_client import get_redis

# ---------------------------------------------------------------------------
# Limites par tag d'endpoint (requêtes / 60 secondes)
# ---------------------------------------------------------------------------
_LIMITS: dict[str, int] = {
    "ships:build":    10,   # POST /ships/build — évite le spam de fabrication
    "forge:start":     5,   # POST /forge — 5 forges/min max
    "fleets:send":    20,   # POST /fleets
    "auth:register":   5,   # POST /auth/register
    "auth:login":     10,   # POST /auth/login — anti brute-force
    "modules:install": 30,  # PUT /ships/{id}/modules/{slot}
    "default":       120,   # Tous les autres endpoints authentifiés
}

_WINDOW_SECONDS = 60


async def check_rate_limit(player_id: str, endpoint_tag: str) -> None:
    """
    Vérifie et incrémente le compteur de rate limit pour un joueur/endpoint.

    Raises:
        HTTPException 429 si la limite est dépassée.
    """
    limit = _LIMITS.get(endpoint_tag, _LIMITS["default"])
    redis = get_redis()
    key = f"ratelimit:{player_id}:{endpoint_tag}"
    now = int(time.time())
    window_start = now - _WINDOW_SECONDS

    # Pipeline atomique : ZREMRANGEBYSCORE + ZADD + ZCARD + EXPIRE
    async with redis.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(key, 0, window_start)   # Supprimer les vieilles entrées
        pipe.zadd(key, {str(now): now})                # Ajouter l'entrée courante
        pipe.zcard(key)                                # Compter
        pipe.expire(key, _WINDOW_SECONDS + 1)          # TTL de nettoyage
        results = await pipe.execute()

    count = results[2]  # zcard result

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trop de requêtes. Limite : {limit} par {_WINDOW_SECONDS}s.",
            headers={"Retry-After": str(_WINDOW_SECONDS)},
        )
