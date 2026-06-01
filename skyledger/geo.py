from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt


EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)

    a = sin(d_lat / 2) ** 2 + cos(r_lat1) * cos(r_lat2) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def cardinal_direction(heading: float | None) -> str:
    if heading is None:
        return "approaching"
    labels = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    index = round((heading % 360) / 45) % 8
    return labels[index]
