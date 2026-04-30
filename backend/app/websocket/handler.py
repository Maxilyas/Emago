"""
app/websocket/handler.py
Endpoint WebSocket principal : ws://.../ws?token=<JWT>

Flux de connexion :
  1. Client envoie ?token=<access_token> dans la query string
  2. Serveur valide le JWT et charge le joueur
  3. Souscription Redis pub/sub sur emago:events:player:{id}
  4. La coroutine tourne jusqu'à déconnexion

Events client → serveur supportés :
  { "type": "ping" }           → { "type": "pong" }
  { "type": "forge.poll", ... } → statut de forge retourné
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.models.models import Player
from app.websocket.connection_manager import manager
from app.websocket.subscribers import subscribe_player_events

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
) -> None:
    """
    Connexion WebSocket authentifiée.
    Le token est passé en query param (header Authorization non disponible en WS).
    """
    # --- Auth ---
    try:
        player_id_str = decode_token(token, expected_kind="access")
        player_id = uuid.UUID(player_id_str)
    except (ValueError, Exception) as exc:
        await websocket.close(code=4001, reason="Token invalide.")
        logger.warning("WS rejeté (token invalide) : %s", exc)
        return

    # Vérification joueur en BDD
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalar_one_or_none()

    if player is None:
        await websocket.close(code=4004, reason="Joueur introuvable.")
        return

    # --- Connexion ---
    await manager.connect(websocket, player_id)

    # Lance la souscription Redis en background
    subscriber_task = asyncio.create_task(subscribe_player_events(player_id))

    try:
        # Message de bienvenue
        await websocket.send_json({
            "type": "connected",
            "data": {"player_id": str(player_id)},
        })

        # Boucle de lecture des messages client
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "JSON invalide."})
                continue

            await _handle_client_message(websocket, player_id, msg)

    except WebSocketDisconnect:
        logger.info("WS déconnecté proprement : player=%s", player_id)
    except Exception as exc:
        logger.error("WS erreur inattendue : %s", exc, exc_info=True)
    finally:
        subscriber_task.cancel()
        manager.disconnect(websocket, player_id)


async def _handle_client_message(
    websocket: WebSocket,
    player_id: uuid.UUID,
    msg: dict,
) -> None:
    """Dispatche les messages entrants du client."""
    msg_type = msg.get("type", "")

    if msg_type == "ping":
        await websocket.send_json({"type": "pong"})

    elif msg_type == "forge.poll":
        # Fallback polling : le client demande le statut d'une forge
        forge_id_raw = msg.get("data", {}).get("forge_id")
        if forge_id_raw:
            from app.services.forge_service import get_forge_status
            status = await get_forge_status(uuid.UUID(forge_id_raw))
            await websocket.send_json({
                "type": "forge.status",
                "data": status or {"forge_id": forge_id_raw, "error": "introuvable"},
            })

    else:
        await websocket.send_json({
            "type": "error",
            "detail": f"Type de message inconnu : {msg_type!r}",
        })
