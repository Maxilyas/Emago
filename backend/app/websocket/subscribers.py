"""
app/websocket/subscribers.py
Pont Redis pub/sub → WebSocket client.

Chaque connexion WebSocket d'un joueur ouvre une souscription Redis
sur le canal emago:events:player:{player_id}.

Les services (combat_engine, forge_service…) publient via publish_event().
Ce module reçoit et forward au client concerné.
"""
from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

import redis.asyncio as aioredis

from app.core.redis_client import get_redis
from app.websocket.connection_manager import manager

logger = logging.getLogger(__name__)


async def subscribe_player_events(player_id: UUID) -> None:
    """
    Tâche asyncio qui tourne pendant toute la durée de la connexion WS.
    Souscrit au canal Redis du joueur et forward chaque événement reçu.

    Cette coroutine est lancée en background task par le handler WS
    et annulée à la déconnexion.
    """
    r: aioredis.Redis = get_redis()
    channel = f"emago:events:player:{player_id}"

    async with r.pubsub() as pubsub:
        await pubsub.subscribe(channel)
        logger.info("Souscription Redis : %s", channel)

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                    await manager.send_to_player(player_id, event)
                except (json.JSONDecodeError, Exception) as exc:
                    logger.warning("Erreur forward WS event : %s", exc)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            logger.info("Désouscription Redis : %s", channel)
