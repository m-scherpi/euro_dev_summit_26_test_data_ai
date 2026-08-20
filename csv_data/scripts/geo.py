#!/usr/bin/env python3
"""Shared plane geometry for the csv_data use case.

Deliberately contains **no projection maths**. The generator and the verifier
implement the Web Mercator transform independently of each other, so that the
verifier is a genuine check on the generator rather than a second call into the
same function. Sharing boundary handling is safe; sharing the projection would
defeat the purpose.

Standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path

# A ring is a list of [longitude, latitude] pairs - GeoJSON order per RFC 7946.
Ring = list[list[float]]


def ring_bounds(ring: Ring) -> tuple[float, float, float, float]:
    """Return (lon_min, lon_max, lat_min, lat_max) of a ring."""
    lons = [point[0] for point in ring]
    lats = [point[1] for point in ring]
    return min(lons), max(lons), min(lats), max(lats)


def point_in_ring(lon: float, lat: float, ring: Ring) -> bool:
    """Ray-casting point-in-polygon test on a single [lon, lat] ring."""
    inside = False
    count = len(ring)
    for i in range(count):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % count][0], ring[(i + 1) % count][1]
        if (y1 > lat) != (y2 > lat):
            if lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                inside = not inside
    return inside


class Boundary:
    """A Polygon or MultiPolygon boundary with a fast `contains` test.

    Interior rings are honoured as holes. Each part carries a precomputed
    bounding box, which is checked first - for a country-sized MultiPolygon
    that skips almost all of the edge tests during rejection sampling.
    """

    def __init__(self, parts: list[tuple[Ring, list[Ring]]], properties: dict, name: str):
        self.properties = properties
        self.name = name
        self._parts = [(outer, holes, ring_bounds(outer)) for outer, holes in parts]

    @property
    def ring_count(self) -> int:
        return sum(1 + len(holes) for _, holes, _ in self._parts)

    @property
    def vertex_count(self) -> int:
        return sum(
            len(outer) + sum(len(hole) for hole in holes)
            for outer, holes, _ in self._parts
        )

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Return (lon_min, lon_max, lat_min, lat_max) over all parts."""
        boxes = [box for _, _, box in self._parts]
        return (
            min(b[0] for b in boxes),
            max(b[1] for b in boxes),
            min(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )

    def contains(self, lon: float, lat: float) -> bool:
        for outer, holes, (lon_min, lon_max, lat_min, lat_max) in self._parts:
            if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
                continue
            if point_in_ring(lon, lat, outer) and not any(
                point_in_ring(lon, lat, hole) for hole in holes
            ):
                return True
        return False


def load_boundary(path: Path) -> Boundary:
    """Read the first Polygon/MultiPolygon feature of a GeoJSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    features = data["features"] if data.get("type") == "FeatureCollection" else [data]

    for feature in features:
        geometry = feature.get("geometry", feature)
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        if geometry_type == "Polygon":
            parts = [(coordinates[0], list(coordinates[1:]))]
        elif geometry_type == "MultiPolygon":
            parts = [(polygon[0], list(polygon[1:])) for polygon in coordinates]
        else:
            continue

        properties = feature.get("properties", {}) or {}
        name = properties.get("name") or data.get("name") or Path(path).stem
        return Boundary(parts, properties, name)

    raise ValueError(f"no Polygon or MultiPolygon geometry found in {path}")
