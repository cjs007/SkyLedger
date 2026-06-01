from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator

from .adsb import AircraftSnapshot, utc_now_iso


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS aircraft (
    hex TEXT PRIMARY KEY,
    registration TEXT,
    aircraft_type TEXT,
    operator TEXT,
    photo_url TEXT,
    first_seen TEXT,
    last_seen TEXT,
    total_sightings INTEGER DEFAULT 0,
    lowest_altitude_ft INTEGER,
    lowest_distance_mi REAL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS flyover_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seen_at TEXT,
    hex TEXT,
    callsign TEXT,
    altitude_ft INTEGER,
    speed_kt INTEGER,
    heading REAL,
    vertical_rate_fpm INTEGER,
    distance_mi REAL,
    closest_lat REAL,
    closest_lon REAL,
    event_type TEXT,
    was_alerted INTEGER,
    was_revealed INTEGER,
    is_new_aircraft INTEGER,
    is_new_lowest INTEGER
);

CREATE INDEX IF NOT EXISTS idx_flyover_events_seen_at ON flyover_events(seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_flyover_events_hex ON flyover_events(hex, seen_at DESC);

CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT PRIMARY KEY,
    total_flyovers INTEGER DEFAULT 0,
    new_aircraft INTEGER DEFAULT 0,
    repeat_aircraft INTEGER DEFAULT 0,
    low_flyovers INTEGER DEFAULT 0,
    lowest_altitude_ft INTEGER
);

CREATE TABLE IF NOT EXISTS aircraft_enrichment_cache (
    hex TEXT PRIMARY KEY,
    registration TEXT,
    aircraft_type TEXT,
    operator TEXT,
    photo_url TEXT,
    route_from TEXT,
    route_to TEXT,
    source TEXT,
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS raw_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seen_at TEXT,
    hex TEXT,
    lat REAL,
    lon REAL,
    altitude_ft INTEGER,
    speed_kt INTEGER,
    heading REAL
);

CREATE INDEX IF NOT EXISTS idx_raw_positions_seen_at ON raw_positions(seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_raw_positions_hex ON raw_positions(hex, seen_at DESC);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = Path(path).expanduser()
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def execute_with_retry(self, fn, attempts: int = 4) -> Any:
        delay = 0.05
        for attempt in range(attempts):
            try:
                return fn()
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == attempts - 1:
                    raise
                time.sleep(delay)
                delay *= 2
        return None

    def record_raw_positions(self, snapshots: Iterable[AircraftSnapshot], retention_days: int) -> None:
        rows = [
            (
                item.received_at,
                item.hex,
                item.lat,
                item.lon,
                item.altitude_ft,
                item.speed_kt,
                item.heading,
            )
            for item in snapshots
            if item.has_position
        ]
        if not rows:
            return

        def write() -> None:
            with self.connect() as conn:
                conn.executemany(
                    """
                    INSERT INTO raw_positions (seen_at, hex, lat, lon, altitude_ft, speed_kt, heading)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.execute(
                    "DELETE FROM raw_positions WHERE seen_at < datetime('now', ?)",
                    (f"-{int(retention_days)} days",),
                )

        self.execute_with_retry(write)

    def record_flyover(
        self,
        snapshot: AircraftSnapshot,
        event_type: str,
        was_alerted: bool,
        was_revealed: bool,
    ) -> dict[str, Any]:
        seen_at = snapshot.received_at or utc_now_iso()
        date = seen_at[:10]

        def write() -> dict[str, Any]:
            with self.connect() as conn:
                aircraft = conn.execute(
                    "SELECT * FROM aircraft WHERE hex = ?",
                    (snapshot.hex,),
                ).fetchone()
                is_new_aircraft = aircraft is None
                previous_lowest = aircraft["lowest_altitude_ft"] if aircraft else None
                previous_sightings = int(aircraft["total_sightings"]) if aircraft else 0
                is_new_lowest = (
                    snapshot.altitude_ft is not None
                    and (previous_lowest is None or snapshot.altitude_ft < previous_lowest)
                )

                if is_new_aircraft:
                    conn.execute(
                        """
                        INSERT INTO aircraft (
                            hex, first_seen, last_seen, total_sightings,
                            lowest_altitude_ft, lowest_distance_mi
                        )
                        VALUES (?, ?, ?, 1, ?, ?)
                        """,
                        (
                            snapshot.hex,
                            seen_at,
                            seen_at,
                            snapshot.altitude_ft,
                            snapshot.distance_mi,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE aircraft
                        SET last_seen = ?,
                            total_sightings = total_sightings + 1,
                            lowest_altitude_ft = CASE
                                WHEN ? IS NULL THEN lowest_altitude_ft
                                WHEN lowest_altitude_ft IS NULL THEN ?
                                WHEN ? < lowest_altitude_ft THEN ?
                                ELSE lowest_altitude_ft
                            END,
                            lowest_distance_mi = CASE
                                WHEN ? IS NULL THEN lowest_distance_mi
                                WHEN lowest_distance_mi IS NULL THEN ?
                                WHEN ? < lowest_distance_mi THEN ?
                                ELSE lowest_distance_mi
                            END
                        WHERE hex = ?
                        """,
                        (
                            seen_at,
                            snapshot.altitude_ft,
                            snapshot.altitude_ft,
                            snapshot.altitude_ft,
                            snapshot.altitude_ft,
                            snapshot.distance_mi,
                            snapshot.distance_mi,
                            snapshot.distance_mi,
                            snapshot.distance_mi,
                            snapshot.hex,
                        ),
                    )

                conn.execute(
                    """
                    INSERT INTO flyover_events (
                        seen_at, hex, callsign, altitude_ft, speed_kt, heading,
                        vertical_rate_fpm, distance_mi, closest_lat, closest_lon,
                        event_type, was_alerted, was_revealed, is_new_aircraft, is_new_lowest
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        seen_at,
                        snapshot.hex,
                        snapshot.callsign,
                        snapshot.altitude_ft,
                        snapshot.speed_kt,
                        snapshot.heading,
                        snapshot.vertical_rate_fpm,
                        snapshot.distance_mi,
                        snapshot.lat,
                        snapshot.lon,
                        event_type,
                        int(was_alerted),
                        int(was_revealed),
                        int(is_new_aircraft),
                        int(is_new_lowest),
                    ),
                )

                conn.execute(
                    """
                    INSERT INTO daily_stats (
                        date, total_flyovers, new_aircraft, repeat_aircraft,
                        low_flyovers, lowest_altitude_ft
                    )
                    VALUES (?, 1, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        total_flyovers = total_flyovers + 1,
                        new_aircraft = new_aircraft + excluded.new_aircraft,
                        repeat_aircraft = repeat_aircraft + excluded.repeat_aircraft,
                        low_flyovers = low_flyovers + excluded.low_flyovers,
                        lowest_altitude_ft = CASE
                            WHEN excluded.lowest_altitude_ft IS NULL THEN daily_stats.lowest_altitude_ft
                            WHEN daily_stats.lowest_altitude_ft IS NULL THEN excluded.lowest_altitude_ft
                            WHEN excluded.lowest_altitude_ft < daily_stats.lowest_altitude_ft THEN excluded.lowest_altitude_ft
                            ELSE daily_stats.lowest_altitude_ft
                        END
                    """,
                    (
                        date,
                        int(is_new_aircraft),
                        int(not is_new_aircraft),
                        int(snapshot.altitude_ft is not None and snapshot.altitude_ft <= 2500),
                        snapshot.altitude_ft,
                    ),
                )

                return {
                    "is_new_aircraft": is_new_aircraft,
                    "is_new_lowest": is_new_lowest,
                    "previous_sightings": previous_sightings,
                    "previous_lowest_altitude_ft": previous_lowest,
                }

        return self.execute_with_retry(write)

    def get_aircraft_record(self, hex_value: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT a.*, e.route_from, e.route_to, e.source AS enrichment_source, e.last_updated AS enrichment_updated
                FROM aircraft a
                LEFT JOIN aircraft_enrichment_cache e ON e.hex = a.hex
                WHERE a.hex = ?
                """,
                (hex_value.lower(),),
            ).fetchone()
            return dict(row) if row else None

    def get_aircraft_history(self, hex_value: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM flyover_events
                WHERE hex = ?
                ORDER BY seen_at DESC
                LIMIT ?
                """,
                (hex_value.lower(), limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_recent_events(self, limit: int = 12) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT f.*, a.registration, a.aircraft_type, a.operator, a.photo_url
                FROM flyover_events f
                LEFT JOIN aircraft a ON a.hex = f.hex
                ORDER BY f.seen_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_history(self, limit: int = 200) -> list[dict[str, Any]]:
        return self.get_recent_events(limit=limit)

    def get_today_stats(self, date: str | None = None) -> dict[str, Any]:
        date = date or utc_now_iso()[:10]
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM daily_stats WHERE date = ?", (date,)).fetchone()
            if not row:
                return {
                    "date": date,
                    "total_flyovers": 0,
                    "new_aircraft": 0,
                    "repeat_aircraft": 0,
                    "low_flyovers": 0,
                    "lowest_altitude_ft": None,
                }
            return dict(row)

    def count_distinct_aircraft_today(self, date: str | None = None) -> int:
        date = date or utc_now_iso()[:10]
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(DISTINCT hex) AS count FROM flyover_events WHERE substr(seen_at, 1, 10) = ?",
                (date,),
            ).fetchone()
            return int(row["count"])
