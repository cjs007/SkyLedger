from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from skyledger.adsb import normalize_aircraft
from skyledger.config import update_config_file
from skyledger.db import Database
from skyledger.geo import haversine_miles


class CoreTests(unittest.TestCase):
    def test_haversine_distance(self) -> None:
        distance = haversine_miles(41.0, -87.0, 41.01, -87.0)
        self.assertGreater(distance, 0.65)
        self.assertLess(distance, 0.75)

    def test_normalize_aircraft(self) -> None:
        snapshot = normalize_aircraft(
            {
                "hex": "A1B2C3",
                "flight": " SKY123 ",
                "lat": 41.01,
                "lon": -87.0,
                "alt_baro": "4200",
                "gs": 180.4,
                "track": 92,
                "baro_rate": -128,
                "category": "A3",
            },
            41.0,
            -87.0,
            "2026-06-01T12:00:00Z",
        )
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.hex, "a1b2c3")
        self.assertEqual(snapshot.callsign, "SKY123")
        self.assertEqual(snapshot.altitude_ft, 4200)
        self.assertIsNotNone(snapshot.distance_mi)

    def test_normalize_keeps_zero_values(self) -> None:
        snapshot = normalize_aircraft(
            {
                "hex": "A1B2C4",
                "lat": 41.0,
                "lon": -87.0,
                "alt_baro": 0,
                "gs": 0,
                "track": 0,
            },
            41.0,
            -87.0,
            "2026-06-01T12:00:00Z",
        )
        self.assertIsNotNone(snapshot)
        assert snapshot is not None
        self.assertEqual(snapshot.altitude_ft, 0)
        self.assertEqual(snapshot.speed_kt, 0)
        self.assertEqual(snapshot.heading, 0)

    def test_record_flyover_updates_stats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(str(Path(tmp) / "skyledger.db"))
            db.init()
            snapshot = normalize_aircraft(
                {
                    "hex": "ABC123",
                    "flight": " N123AB ",
                    "lat": 41.001,
                    "lon": -87.0,
                    "alt_baro": 2200,
                    "gs": 120,
                    "track": 180,
                },
                41.0,
                -87.0,
                "2026-06-01T12:00:00Z",
            )
            assert snapshot is not None
            context = db.record_flyover(snapshot, "reveal", True, True)
            stats = db.get_today_stats("2026-06-01")
            record = db.get_aircraft_record("abc123")
            self.assertTrue(context["is_new_aircraft"])
            self.assertEqual(stats["total_flyovers"], 1)
            self.assertEqual(stats["new_aircraft"], 1)
            self.assertEqual(record["total_sightings"], 1)

    def test_clear_history_removes_logged_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(str(Path(tmp) / "skyledger.db"))
            db.init()
            snapshot = normalize_aircraft(
                {
                    "hex": "ABC123",
                    "flight": " N123AB ",
                    "lat": 41.001,
                    "lon": -87.0,
                    "alt_baro": 2200,
                },
                41.0,
                -87.0,
                "2026-06-01T12:00:00Z",
            )
            assert snapshot is not None
            db.record_raw_positions([snapshot], retention_days=14)
            db.record_flyover(snapshot, "reveal", True, True)

            deleted = db.clear_history()

            self.assertEqual(deleted["flyover_events"], 1)
            self.assertEqual(deleted["aircraft"], 1)
            self.assertEqual(deleted["daily_stats"], 1)
            self.assertEqual(deleted["raw_positions"], 1)
            self.assertEqual(deleted["received_aircraft"], 1)
            self.assertEqual(db.get_history(), [])
            self.assertIsNone(db.get_aircraft_record("abc123"))
            self.assertEqual(db.get_today_stats("2026-06-01")["total_flyovers"], 0)

    def test_received_aircraft_summary_tracks_unique_and_max_distance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(str(Path(tmp) / "skyledger.db"))
            db.init()
            first = normalize_aircraft(
                {"hex": "ABC123", "lat": 41.001, "lon": -87.0, "alt_baro": 2200},
                41.0,
                -87.0,
                "2026-06-01T12:00:00Z",
            )
            second = normalize_aircraft(
                {"hex": "DEF456", "lat": 41.01, "lon": -87.0, "alt_baro": 3500},
                41.0,
                -87.0,
                "2026-06-01T12:01:00Z",
            )
            assert first is not None
            assert second is not None

            db.record_raw_positions([first, second], retention_days=14)
            summary = db.get_summary_stats()

            self.assertEqual(summary["total_aircraft"], 2)
            self.assertEqual(summary["total_flyovers"], 0)
            self.assertGreater(summary["max_distance_mi"], first.distance_mi)

    def test_update_config_file_persists_map_zoom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text("home_lat: 41.0\nhome_lon: -87.0\n", encoding="utf-8")

            config = update_config_file(str(path), {"map_zoom_level": 15})

            self.assertEqual(config.map_zoom_level, 15)
            self.assertIn("map_zoom_level: 15", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
