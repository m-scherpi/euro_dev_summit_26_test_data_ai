"""Reading the three shapes of source file this use case accepts.

Imported by **both** `analyze_source.py`, which measures the rows to write the
schema contract, and `import_to_egdb.py`, which reads the same rows to load
them. Those two have to agree about what a row is, so sharing the reader is
correct here - unlike the projection formulas and geodatabase type lookups
elsewhere in this repository, which are deliberately written twice
(CLAUDE.md section 4). Nothing here decides anything: no type is inferred, no
CRS is chosen, no value is converted. It returns the columns and the rows as
the file states them.

`verify_featureclass.py` imports none of this and reads the source with its own
few lines, so that the comparison between the geodatabase and the file is not
two readings by the same code.

What is *asserted* rather than converted lives here too, because the assertion
belongs to the reader:

* An **Esri JSON FeatureSet** must declare `geometryType: "esriGeometryPoint"`
  and a spatial reference, or the read fails. CLAUDE.md section 4: this is the
  file that gets described as "a GeoJSON export" and is not one. The
  `{"x": ..., "y": ...}` geometry shape fails loudly in any GeoJSON reader; the
  CRS does not fail at all, and a FeatureSet in another projected CRS is still
  metres, just of a different grid.
* A **GeoJSON FeatureCollection** is EPSG:4326 by RFC 7946, in
  `[longitude, latitude]` order. A legacy `crs` member naming anything else is
  a file claiming two CRS at once, and is refused rather than reconciled.

Stdlib only. Requires Python 3.10+.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ESRI_POINT = "esriGeometryPoint"


class SourceError(Exception):
    """A source file this tool refuses to interpret."""


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------


def read_csv(path: Path, delimiter: str | None, encoding: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Read a delimited text file, sniffing the delimiter unless told."""
    text = path.read_text(encoding=encoding)
    if delimiter is None:
        try:
            delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|").delimiter
        except csv.Error as exc:  # pragma: no cover - depends on the file
            raise SourceError(
                f"cannot determine the delimiter of {path}: {exc}. Pass --delimiter explicitly."
            ) from exc
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    if not reader.fieldnames:
        raise SourceError(f"{path} has no header row")
    rows = [dict(row) for row in reader]
    return list(reader.fieldnames), rows


def _columns_in_order(rows: list[dict[str, Any]]) -> list[str]:
    """Union of keys, in first-seen order - JSON objects need not agree."""
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            seen.setdefault(key, None)
    return list(seen)


def read_json(path: Path, encoding: str) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """Read one of the three JSON shapes this tool understands.

    Returns `(columns, rows, geometry_hint)`, where the hint carries what the
    file itself said about its geometry - which is authoritative and overrides
    any guess from column names.
    """
    payload = json.loads(path.read_text(encoding=encoding))

    if isinstance(payload, list):
        if not payload or not all(isinstance(item, dict) for item in payload):
            raise SourceError(f"{path} is a JSON array but not an array of objects")
        return _columns_in_order(payload), list(payload), {}

    if not isinstance(payload, dict):
        raise SourceError(f"{path} is neither a JSON array of objects nor an object")

    # Esri JSON FeatureSet - checked before GeoJSON, because a FeatureSet also
    # has a `features` array and the two are easy to mistake for each other.
    # CLAUDE.md section 4: this is the file that is described as "a GeoJSON
    # export" and is not one, and the CRS is the part that does not fail loudly.
    if "geometryType" in payload or (
        isinstance(payload.get("features"), list)
        and payload["features"]
        and isinstance(payload["features"][0], dict)
        and "attributes" in payload["features"][0]
    ):
        return _read_esri_featureset(path, payload)

    if payload.get("type") == "FeatureCollection":
        return _read_geojson(path, payload)

    raise SourceError(
        f"{path} is a JSON object of an unrecognised shape. Supported: an array of objects, "
        "a GeoJSON FeatureCollection, or an Esri JSON FeatureSet."
    )


def _read_esri_featureset(
    path: Path, payload: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    geometry_type = payload.get("geometryType")
    if geometry_type != ESRI_POINT:
        raise SourceError(
            f"{path} is an Esri JSON FeatureSet with geometryType {geometry_type!r}. "
            f"This tool only handles {ESRI_POINT!r} - it will not convert a geometry type it "
            "was not written for."
        )

    spatial_reference = payload.get("spatialReference") or {}
    wkid = spatial_reference.get("latestWkid") or spatial_reference.get("wkid")
    if not wkid:
        raise SourceError(
            f"{path} is an Esri JSON FeatureSet without a spatialReference. Its coordinates are "
            "in some CRS and the file does not say which; a projected FeatureSet is metres of an "
            "unknown grid, so nothing here can be salvaged by guessing."
        )

    rows: list[dict[str, Any]] = []
    for index, feature in enumerate(payload.get("features") or []):
        geometry = feature.get("geometry") or {}
        if "x" not in geometry or "y" not in geometry:
            raise SourceError(f"{path}: feature {index} has no x/y geometry")
        row = dict(feature.get("attributes") or {})
        row["_geometry_x"] = geometry["x"]
        row["_geometry_y"] = geometry["y"]
        rows.append(row)
    if not rows:
        raise SourceError(f"{path} contains no features")

    columns = [c for c in _columns_in_order(rows) if not c.startswith("_geometry_")]
    # A FeatureSet exported from a geodatabase carries its own schema in a
    # `fields` block: real Esri types and real TEXT lengths. Passed through
    # verbatim rather than interpreted here - the reader's job is to hand over
    # what the file says, and `schema.declared_field` decides what to do with it.
    declared = {
        field["name"]: field
        for field in (payload.get("fields") or [])
        if isinstance(field, dict) and field.get("name")
    }

    hint = {
        "from": "esri_featureset",
        "x_column": "_geometry_x",
        "y_column": "_geometry_y",
        "wkid": int(wkid),
        "wkid_source": (
            f"spatialReference.latestWkid={spatial_reference.get('latestWkid')!r}, "
            f"wkid={spatial_reference.get('wkid')!r} in the source file"
        ),
        "declared_fields": declared,
    }
    return columns, rows, hint


def _read_geojson(
    path: Path, payload: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    # RFC 7946 removed the `crs` member and fixes the CRS at EPSG:4326. A file
    # carrying a legacy crs member that says something else is not a
    # disagreement to resolve, it is a file claiming two CRS at once.
    legacy_crs = payload.get("crs")
    if legacy_crs is not None:
        name = json.dumps(legacy_crs, sort_keys=True)
        if "4326" not in name and "CRS84" not in name:
            raise SourceError(
                f"{path} is a GeoJSON FeatureCollection with a legacy crs member {name}. "
                "RFC 7946 fixes GeoJSON at EPSG:4326; a file asserting another CRS in that "
                "member is self-contradictory and will not be interpreted here."
            )

    rows: list[dict[str, Any]] = []
    for index, feature in enumerate(payload.get("features") or []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            raise SourceError(
                f"{path}: feature {index} has geometry type {geometry.get('type')!r}; "
                "only Point is handled."
            )
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2:
            raise SourceError(f"{path}: feature {index} has fewer than two coordinates")
        row = dict(feature.get("properties") or {})
        # RFC 7946 is always [longitude, latitude]. Flagged here rather than
        # assumed, because it is the one place in this repository where the
        # axis order is the opposite of the column order used everywhere else.
        row["_geometry_x"] = coordinates[0]
        row["_geometry_y"] = coordinates[1]
        rows.append(row)
    if not rows:
        raise SourceError(f"{path} contains no features")

    columns = [c for c in _columns_in_order(rows) if not c.startswith("_geometry_")]
    hint = {
        "from": "geojson",
        "x_column": "_geometry_x",
        "y_column": "_geometry_y",
        "wkid": 4326,
        "wkid_source": "RFC 7946 fixes GeoJSON at EPSG:4326 and coordinates are [longitude, latitude]",
    }
    return columns, rows, hint
