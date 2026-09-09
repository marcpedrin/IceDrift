"""Ship tracking routes: /ships/nearby and WebSocket /ws/ships"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from app.models.schemas import ShipListResponse, ShipResponse
from app.services.ais_service import get_ais
from app.services.cache_service import get_cache

router = APIRouter(tags=["Ships"])

# ── WebSocket connection manager ───────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        logger.info("WS client connected. Total: {}", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        logger.info("WS client disconnected. Total: {}", len(self.active))

    async def broadcast(self, data: dict) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ── REST endpoint ─────────────────────────────────────────────────────────────

@router.get("/ships/nearby", response_model=ShipListResponse)
async def get_nearby_ships(
    lat: float = Query(-65.0, ge=-90, le=90),
    lon: float = Query(0.0, ge=-180, le=180),
    radius_nm: float = Query(500.0, ge=10, le=2000),
):
    """
    Return live AIS ship positions near the given coordinate.

    - Uses MarineTraffic API if `MARINETRAFFIC_API_KEY` is set
    - Falls back to realistic mock Antarctic vessel data
    - Ships include: research vessels, icebreakers, supply ships, passengers
    """
    cache = get_cache()
    cache_key = cache.make_key("ships_nearby", f"{lat:.1f}", f"{lon:.1f}")

    cached = await cache.get(cache_key)
    if cached:
        return ShipListResponse(**cached)

    ais = get_ais()
    raw_ships = await ais.get_nearby_ships(lat=lat, lon=lon, radius_nm=radius_nm)

    ships = [ShipResponse(**s) for s in raw_ships]
    response = ShipListResponse(count=len(ships), ships=ships, timestamp=datetime.utcnow())

    from config import get_settings
    await cache.set(cache_key, response.model_dump(mode="json"), ttl=get_settings().ship_cache_ttl)

    return response


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@router.websocket("/ws/ships")
async def ws_ships(websocket: WebSocket):
    """
    WebSocket: push live ship position updates every 60 seconds.

    Message format:
    {
        "type": "ship_update",
        "timestamp": "...",
        "ships": [...ShipResponse...]
    }
    """
    await manager.connect(websocket)
    ais = get_ais()

    try:
        # Send initial snapshot immediately
        raw = await ais.get_nearby_ships()
        await websocket.send_json({
            "type": "ship_update",
            "timestamp": datetime.utcnow().isoformat(),
            "ships": raw,
        })

        # Push updates every 60 seconds
        while True:
            await asyncio.sleep(60)
            raw = await ais.get_nearby_ships()
            await websocket.send_json({
                "type": "ship_update",
                "timestamp": datetime.utcnow().isoformat(),
                "ships": raw,
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WS error: {}", exc)
        manager.disconnect(websocket)
