"""
app/websocket/connection_manager.py
Gestion des connexions WebSocket actives.

Architecture :
  - Un joueur peut avoir plusieurs connexions simultanées (onglets multiples)
  - Les événements sont broadcastés à toutes les connexions du joueur
  - Le manager est un singleton en mémoire (suffisant pour un VPS unique)
  - En cas de scale horizontal, remplacer par un broadcaster Redis pub/sub inter-process
"""
from __future__ import annotations

import logging
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # player_id → liste de WebSockets actifs
        self._connections: dict[UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, player_id: UUID) -> None:
        await websocket.accept()
        self._connections[player_id].append(websocket)
        logger.info("WS connecté : player=%s (total=%d)", player_id, len(self._connections[player_id]))

    def register(self, websocket: WebSocket, player_id: UUID) -> None:
        """Enregistre un WebSocket déjà accepté (pas de double accept)."""
        self._connections[player_id].append(websocket)
        logger.info("WS enregistré : player=%s (total=%d)", player_id, len(self._connections[player_id]))

    def disconnect(self, websocket: WebSocket, player_id: UUID) -> None:
        conns = self._connections.get(player_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(player_id, None)
        logger.info("WS déconnecté : player=%s", player_id)

    async def send_to_player(self, player_id: UUID, message: dict) -> None:
        """Envoie un message JSON à toutes les connexions d'un joueur."""
        dead: list[WebSocket] = []
        for ws in self._connections.get(player_id, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        # Nettoyage des connexions mortes
        for ws in dead:
            self.disconnect(ws, player_id)

    async def broadcast(self, message: dict) -> None:
        """Envoie un message à TOUS les joueurs connectés (usage rare)."""
        for player_id in list(self._connections.keys()):
            await self.send_to_player(player_id, message)


# Singleton partagé dans toute l'application
manager = ConnectionManager()
