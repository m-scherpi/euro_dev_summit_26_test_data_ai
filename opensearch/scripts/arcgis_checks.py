"""Verifier-side building blocks: what ArcGIS requires, and how to check it.

Moved out of `verify_index.py` unchanged when a second index appeared, and
imported by the **verifiers only**. Nothing here is imported by an indexer, and
that is the invariant worth protecting: the geo_point decoder below is written
from the OpenSearch field specification rather than from
`geopoint.format_location`, so the two readings agreeing is evidence. If an
indexer ever imports this module, the checks it feeds stop meaning anything.

The same reasoning explains why `haversine_m` lives here rather than being
delegated to the search engine: the point of the geo_distance check is to
compare OpenSearch's answer against a distance computed somewhere else
entirely.
"""

from __future__ import annotations

import math
import re

# Which OpenSearch field types ArcGIS maps to which ArcGIS type. Transcribed
# from the Esri table, not from any indexer's mapping, so a wrong type in the
# index is a finding rather than a shared assumption.
# https://doc.esri.com/en/arcgis-pro/latest/help/data/databases/dbms-data-types-supported.html
ARCGIS_TYPE_OF = {
    "long": "Big Integer",
    "unsigned_long": "Big Integer",
    "binary": "Blob",
    "date": "Date",
    "double": "Double",
    "float": "Float",
    "scaled_float": "Float",
    "half_float": "Float",
    "geo_point": "Geometry",
    "geo_shape": "Geometry",
    "integer": "Long Integer",
    "keyword": "Text",
    "text": "Text",
    "alias": "Text",
    "object": "Text",
    "long_range": "Text",
    "integer_range": "Text",
    "date_range": "Text",
    "double_range": "Text",
}

EARTH_RADIUS_M = 6371008.8  # mean radius, as used by OpenSearch's arc distance

WKT_POINT = re.compile(
    r"^\s*POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)\s*$", re.IGNORECASE
)


class Check:
    """One verification result, rendered as a row of the report table."""

    def __init__(self, name: str, passed: bool | None, detail: str) -> None:
        self.name = name
        self.passed = passed  # None = informational
        self.detail = detail

    @property
    def verdict(self) -> str:
        if self.passed is None:
            return "INFO"
        return "PASS" if self.passed else "FAIL"


def decode_location(value) -> tuple[float, float]:
    """Decode a geo_point value into (latitude, longitude).

    Written from the OpenSearch field-type specification rather than from any
    indexer's `format_location`, on purpose: two readings of the spec that
    agree is evidence, one function calling itself is not.

    Raises ValueError for the object format, which is valid OpenSearch and
    unusable from ArcGIS.
    """
    if isinstance(value, dict):
        raise ValueError(
            "object format {lat, lon} - valid in OpenSearch, unsupported by ArcGIS"
        )
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError(f"array of length {len(value)}, expected 2")
        longitude, latitude = float(value[0]), float(value[1])  # GeoJSON order
        return latitude, longitude
    if isinstance(value, str):
        match = WKT_POINT.match(value)
        if match:
            longitude, latitude = float(match.group(1)), float(match.group(2))
            return latitude, longitude
        if "," in value:
            latitude, longitude = (float(part) for part in value.split(",", 1))
            return latitude, longitude
        raise ValueError(f"unrecognised string form: {value!r}")
    raise ValueError(f"unsupported geo_point value of type {type(value).__name__}")


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres. Independent of anything in the indexer."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def flatten_properties(properties: dict, prefix: str = "") -> dict[str, str]:
    """Flatten the mapping's properties into {field path: type}."""
    flat: dict[str, str] = {}
    for name, definition in properties.items():
        path = f"{prefix}{name}"
        if "type" in definition:
            flat[path] = definition["type"]
        for sub_name, sub_def in definition.get("fields", {}).items():
            if "type" in sub_def:
                flat[f"{path}.{sub_name}"] = sub_def["type"]
        if "properties" in definition:
            flat.update(flatten_properties(definition["properties"], f"{path}."))
    return flat


def render_check_table(checks: list[Check]) -> list[str]:
    """Render the checks as the report's summary table.

    The exact shape the existing `output/verification_report.md` already has,
    so lifting this out of `verify_index.py` leaves the committed report
    byte-identical. A refactor that also improves the output is a refactor
    whose regression test cannot tell the two apart.
    """
    lines = ["| Check | Result | Detail |", "|---|---|---|"]
    for check in checks:
        lines.append(f"| {check.name} | {check.verdict} | {check.detail} |")
    return lines
