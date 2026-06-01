from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class EnrichmentResult:
    registration: str | None = None
    aircraft_type: str | None = None
    operator: str | None = None
    photo_url: str | None = None
    route_from: str | None = None
    route_to: str | None = None
    source: str | None = None


class EnrichmentProvider:
    """Cache-first placeholder for optional free/public aircraft enrichment."""

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    async def lookup(self, hex_value: str) -> EnrichmentResult | None:
        if not self.enabled or not hex_value:
            return None
        return None
