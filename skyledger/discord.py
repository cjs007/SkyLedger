from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any


class DiscordNotifier:
    def __init__(self, webhook_url: str, enabled: bool) -> None:
        self.webhook_url = webhook_url
        self.enabled = enabled and bool(webhook_url)

    async def send_alert(self, aircraft: dict[str, Any]) -> tuple[bool, str | None]:
        if not self.enabled:
            return False, "Discord alerts are disabled or webhook is not configured."

        content = self._format_message(aircraft)
        payload = json.dumps({"content": content}).encode("utf-8")

        def post() -> None:
            request = urllib.request.Request(
                self.webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                response.read()

        try:
            await asyncio.to_thread(post)
            return True, None
        except Exception as exc:  # noqa: BLE001 - surfaced to status/UI.
            return False, str(exc)

    async def send_test(self) -> tuple[bool, str | None]:
        return await self.send_alert(
            {
                "callsign": "SKYLEDGER",
                "hex": "test",
                "altitude_ft": 3200,
                "distance_mi": 0.4,
                "speed_kt": 175,
                "operator": "Test Alert",
                "total_sightings": 1,
                "lowest_altitude_ft": 3200,
                "timestamp": "now",
            }
        )

    def _format_message(self, aircraft: dict[str, Any]) -> str:
        callsign = aircraft.get("callsign") or aircraft.get("hex") or "Unknown aircraft"
        altitude = _fmt(aircraft.get("altitude_ft"), " ft")
        distance = _fmt(aircraft.get("distance_mi"), " mi")
        speed = _fmt(aircraft.get("speed_kt"), " kt")
        operator = aircraft.get("operator") or aircraft.get("aircraft_type") or "Unknown type/operator"
        sightings = aircraft.get("total_sightings") or aircraft.get("seen_before_count") or 0
        lowest = _fmt(aircraft.get("lowest_altitude_ft"), " ft")
        timestamp = aircraft.get("timestamp") or ""
        return (
            f"**SkyLedger flyover**\n"
            f"Aircraft: `{callsign}`\n"
            f"Altitude: **{altitude}** | Distance: **{distance}** | Speed: **{speed}**\n"
            f"Type/operator: {operator}\n"
            f"Seen before: {sightings} time(s) | Lowest previous pass: {lowest}\n"
            f"{timestamp}"
        )


def _fmt(value: Any, suffix: str) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"
