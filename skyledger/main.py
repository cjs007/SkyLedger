from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .adsb import ADSBReader
from .config import load_config, update_config_file
from .db import Database
from .discord import DiscordNotifier
from .tracker import SkyLedgerTracker

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"


class MapZoomRequest(BaseModel):
    map_zoom_level: int = Field(ge=0, le=19)


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        for websocket in self.connections:
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket)


def create_app(config_path: str | None = None) -> FastAPI:
    config = load_config(config_path)
    manager = ConnectionManager()
    db = Database(config.database_path)
    reader = ADSBReader(config.adsb_json_path, config.home_lat, config.home_lon)
    notifier = DiscordNotifier(config.discord_webhook_url, config.enable_discord_alerts)
    tracker = SkyLedgerTracker(config, db, reader, notifier, manager.broadcast)

    app = FastAPI(title="SkyLedger", version="0.1.0")
    app.state.config = config
    app.state.db = db
    app.state.tracker = tracker
    app.state.manager = manager
    app.state.tracker_task = None

    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.on_event("startup")
    async def startup() -> None:
        await asyncio.to_thread(db.init)
        app.state.tracker_task = asyncio.create_task(tracker.run())

    @app.on_event("shutdown")
    async def shutdown() -> None:
        tracker.stop()
        task = app.state.tracker_task
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @app.get("/")
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/history")
    async def history_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "history.html")

    @app.get("/aircraft/{hex_value}")
    async def aircraft_page(hex_value: str) -> FileResponse:
        return FileResponse(STATIC_DIR / "aircraft.html")

    @app.get("/settings")
    async def settings_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "settings.html")

    @app.websocket("/ws/live")
    async def live_ws(websocket: WebSocket) -> None:
        await manager.connect(websocket)
        try:
            if tracker.last_payload:
                await websocket.send_json(tracker.last_payload)
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    @app.get("/api/status")
    async def api_status() -> dict[str, Any]:
        return tracker.status_payload()

    @app.get("/api/aircraft/live")
    async def api_live_aircraft() -> dict[str, Any]:
        return tracker.build_payload()

    @app.get("/api/events/recent")
    async def api_recent_events(limit: int = 20) -> list[dict[str, Any]]:
        return db.get_recent_events(limit=min(max(limit, 1), 100))

    @app.get("/api/stats/today")
    async def api_today_stats() -> dict[str, Any]:
        today = db.get_today_stats()
        today["aircraft_count"] = db.count_distinct_aircraft_today(today["date"])
        return today

    @app.get("/api/aircraft/{hex_value}")
    async def api_aircraft(hex_value: str) -> dict[str, Any]:
        record = db.get_aircraft_record(hex_value)
        if not record:
            raise HTTPException(status_code=404, detail="Aircraft has not been logged yet.")
        return {
            "aircraft": record,
            "events": db.get_aircraft_history(hex_value, limit=100),
        }

    @app.get("/api/history")
    async def api_history(limit: int = 200) -> list[dict[str, Any]]:
        return db.get_history(limit=min(max(limit, 1), 500))

    @app.post("/api/test-discord")
    async def api_test_discord() -> dict[str, Any]:
        ok, error = await notifier.send_test()
        return {"ok": ok, "error": error}

    @app.post("/api/test-countdown")
    async def api_test_countdown() -> dict[str, Any]:
        return await tracker.trigger_test_countdown()

    @app.post("/api/history/clear")
    async def api_clear_history() -> dict[str, Any]:
        tracker.active.clear()
        tracker.alert_cooldowns.clear()
        counts = await asyncio.to_thread(db.clear_history)
        payload = tracker.build_payload()
        tracker.last_payload = payload
        await manager.broadcast(payload)
        return {"ok": True, "deleted": counts}

    @app.post("/api/settings/map-zoom")
    async def api_update_map_zoom(request: MapZoomRequest) -> dict[str, Any]:
        updated = await asyncio.to_thread(
            update_config_file,
            config_path,
            {"map_zoom_level": request.map_zoom_level},
        )
        config.map_zoom_level = updated.map_zoom_level
        tracker.last_payload = tracker.build_payload()
        await manager.broadcast(tracker.last_payload)
        return {"ok": True, "map_zoom_level": config.map_zoom_level}

    return app


app = create_app()
