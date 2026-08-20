#!/usr/bin/env python3
"""Verify the NRW railway station CSV against its source and against the geometry.

`build_stations.py` claims three things: that it invented nothing, that every
station is inside North Rhine-Westphalia, and that the EPSG:3857 columns follow
from the geographic ones. This script tests all three, and it is deliberately
built so that none of the tests can pass by accident:

* **Projections come from pyproj**, not from a second copy of the builder's
  formula. The builder hand-writes spherical Web Mercator as
  `R * ln(tan(pi/4 + phi/2))`; PROJ is an independent implementation by
  independent authors. Agreement is then evidence rather than a tautology - the
  reason `pyproj` is a dependency of this use case at all.
* **Containment is pure-Python ray casting**, not the shapely call the builder
  makes. Same input polygon, different code path.
* **Provenance is checked against the source fixture.** Every output coordinate
  must be findable, unmodified, in a source row carrying the same DS 100 code.
  This is the check that would catch a hallucinated station: a plausible name at
  a plausible position that nobody published.

Three measurements ride along, all informational. None of them is this
repository's bug; they are the reason not to treat an official data set - or an
official boundary - as ground truth without measuring it:

* the source's own EPSG:25832 columns recomputed from its own EPSG:4326 columns
* the source's numeric EPSG:4326 columns against its `WKT WGS84` column, which
  are two different derivations of the same point and disagree by ~1.3 m
* how close each station sits to the state border. This one exists because the
  containment check has already produced a false positive once: a generalised
  Natural Earth boundary put a station 1.3 km outside NRW that the authoritative
  boundary puts 117 m inside. Any station within a few hundred metres of the
  border is a station whose membership depends on which polygon you asked, and
  saying so is more honest than a bare PASS.

Runs offline. Exit code 0 if every structural check passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

from pyproj import Transformer

SOURCE_ENCODING = "utf-8-sig"
SOURCE_DELIMITER = ";"

COLUMN_DS100 = "Kürzel"
COLUMN_LON = "Geographische Länge (EPSG 4326)"
COLUMN_LAT = "Geographische Breite (EPSG 4326)"
COLUMN_UTM_X = "UTM Rechtswert (EPSG 25832)"
COLUMN_UTM_Y = "UTM Hochwert (EPSG 25832)"
COLUMN_WKT_4326 = "WKT WGS84 (EPSG 4326)"

REQUIRED_OUTPUT_COLUMNS = (
    "ds100", "name", "district", "latitude", "longitude",
    "x_3857", "y_3857", "source_rows", "position_spread_m",
)

# The builder writes 5 decimals of a degree. Matching an output row back to its
# source row therefore has to compare at that precision, not exactly.
COORDINATE_DECIMALS = 5

# Metres per degree of latitude. Only ever used for distances of a few hundred
# metres on a local tangent plane, never for anything that reaches a data file.
METRES_PER_DEGREE = 111_320.0

WKT_POINT = re.compile(r"POINT\s*\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)")


def parse_german_decimal(value: str) -> float:
    """Parse a number written with a comma as the decimal separator."""
    return float(value.strip().replace(",", "."))


def parse_wkt_point(value: str) -> tuple[float, float] | None:
    """Return (x, y) of a WKT POINT, or None if it does not parse."""
    match = WKT_POINT.match(value.strip())
    if match is None:
        return None
    return float(match.group(1)), float(match.group(2))


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test on a single [lon, lat] ring.

    Deliberately hand-written rather than delegated to shapely: the builder uses
    shapely for the same decision, and two calls into GEOS would only prove that
    GEOS is deterministic.
    """
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
    """A Polygon or MultiPolygon with a ray-casting `contains` test."""

    def __init__(self, parts: list[tuple[list, list]], name: str):
        self.name = name
        self._parts = parts

    @property
    def vertex_count(self) -> int:
        return sum(
            len(outer) + sum(len(hole) for hole in holes) for outer, holes in self._parts
        )

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Return (lon_min, lon_max, lat_min, lat_max)."""
        points = [
            point
            for outer, holes in self._parts
            for ring in (outer, *holes)
            for point in ring
        ]
        lons = [point[0] for point in points]
        lats = [point[1] for point in points]
        return min(lons), max(lons), min(lats), max(lats)

    def contains(self, lon: float, lat: float) -> bool:
        for outer, holes in self._parts:
            if point_in_ring(lon, lat, outer) and not any(
                point_in_ring(lon, lat, hole) for hole in holes
            ):
                return True
        return False

    def min_distance_m(
        self, lon: float, lat: float, window_deg: float = 0.1
    ) -> float | None:
        """Shortest distance in metres from a point to the boundary line.

        Only segments whose bounding box comes within `window_deg` of the point
        are measured; returns None when none does, which for the default window
        means "further than roughly 7 km from the border" - far enough that the
        precision of the polygon cannot decide this station's membership.

        Distances are computed on a local tangent plane, which is exact enough
        for a question asked in hundreds of metres.
        """
        scale = math.cos(math.radians(lat))
        best: float | None = None
        for outer, holes in self._parts:
            for ring in (outer, *holes):
                for i in range(len(ring)):
                    x1, y1 = ring[i][0], ring[i][1]
                    x2, y2 = ring[(i + 1) % len(ring)][0], ring[(i + 1) % len(ring)][1]
                    if (
                        min(x1, x2) - window_deg > lon
                        or max(x1, x2) + window_deg < lon
                        or min(y1, y2) - window_deg > lat
                        or max(y1, y2) + window_deg < lat
                    ):
                        continue
                    ax = (x1 - lon) * METRES_PER_DEGREE * scale
                    ay = (y1 - lat) * METRES_PER_DEGREE
                    bx = (x2 - lon) * METRES_PER_DEGREE * scale
                    by = (y2 - lat) * METRES_PER_DEGREE
                    dx, dy = bx - ax, by - ay
                    length_squared = dx * dx + dy * dy
                    if length_squared == 0.0:
                        distance = math.hypot(ax, ay)
                    else:
                        t = max(0.0, min(1.0, -(ax * dx + ay * dy) / length_squared))
                        distance = math.hypot(ax + t * dx, ay + t * dy)
                    if best is None or distance < best:
                        best = distance
        return best


def load_boundary(path: Path) -> Boundary:
    """Read the first Polygon/MultiPolygon feature of a GeoJSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data["features"] if data.get("type") == "FeatureCollection" else [data]
    for feature in features:
        geometry = feature.get("geometry", feature)
        coordinates = geometry.get("coordinates")
        if geometry.get("type") == "Polygon":
            parts = [(coordinates[0], list(coordinates[1:]))]
        elif geometry.get("type") == "MultiPolygon":
            parts = [(polygon[0], list(polygon[1:])) for polygon in coordinates]
        else:
            continue
        properties = feature.get("properties", {}) or {}
        name = properties.get("name") or data.get("name") or path.stem
        return Boundary(parts, name)
    raise ValueError(f"no Polygon or MultiPolygon geometry found in {path}")


def percentile(sorted_values: list[float], fraction: float) -> float:
    """Nearest-rank percentile of an already sorted list."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round(fraction * (len(sorted_values) - 1))))
    return sorted_values[index]


def statistics_block(values: list[float]) -> list[str]:
    """Render min/median/mean/p95/max of a distance sample as Markdown rows."""
    if not values:
        return ["| _no rows_ | - |"]
    ordered = sorted(values)
    return [
        f"| min | {ordered[0]:,.3f} |",
        f"| median | {percentile(ordered, 0.5):,.3f} |",
        f"| mean | {sum(ordered) / len(ordered):,.3f} |",
        f"| p95 | {percentile(ordered, 0.95):,.3f} |",
        f"| max | {ordered[-1]:,.3f} |",
    ]


def read_source_positions(path: Path) -> dict[str, list[dict]]:
    """Index the source fixture by DS 100 code, parsing every CRS column."""
    by_ds100: dict[str, list[dict]] = {}
    with path.open(encoding=SOURCE_ENCODING, newline="") as handle:
        for row in csv.DictReader(handle, delimiter=SOURCE_DELIMITER):
            try:
                lat = parse_german_decimal(row[COLUMN_LAT])
                lon = parse_german_decimal(row[COLUMN_LON])
            except (KeyError, TypeError, ValueError):
                continue
            try:
                utm_x = parse_german_decimal(row[COLUMN_UTM_X])
                utm_y = parse_german_decimal(row[COLUMN_UTM_Y])
            except (KeyError, TypeError, ValueError):
                utm_x = utm_y = None
            by_ds100.setdefault(row[COLUMN_DS100].strip(), []).append(
                {
                    "lat": lat,
                    "lon": lon,
                    "utm_x": utm_x,
                    "utm_y": utm_y,
                    "wkt_4326": parse_wkt_point(row.get(COLUMN_WKT_4326, "") or ""),
                }
            )
    return by_ds100


def check(
    rows: list[dict[str, str]],
    source: dict[str, list[dict]],
    boundary: Boundary,
    bbox: tuple[float, float, float, float],
    to_3857: Transformer,
    to_25832: Transformer,
) -> dict:
    """Run every check over all rows and collect the findings."""
    lon_min, lon_max, lat_min, lat_max = bbox
    findings: dict = {
        "schema_errors": [],
        "duplicate_ds100": [],
        "provenance_errors": [],
        "axis_order_errors": [],
        "bbox_errors": [],
        "outside_boundary": [],
        "deviations_3857": [],
        "source_25832": [],
        "source_wkt": [],
        "border_distances": [],
    }

    seen_ds100: set[str] = set()

    for number, row in enumerate(rows, start=2):  # line 1 is the header
        label = row.get("ds100") or f"line {number}"

        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            written_x = float(row["x_3857"])
            written_y = float(row["y_3857"])
            int(row["source_rows"])
            float(row["position_spread_m"])
        except (KeyError, TypeError, ValueError) as exc:
            findings["schema_errors"].append(f"{label}: unparseable column ({exc})")
            continue

        if not (row.get("name") or "").strip():
            findings["schema_errors"].append(f"{label}: empty name")
        if label in seen_ds100:
            findings["duplicate_ds100"].append(f"{label}: DS 100 code appears more than once")
        seen_ds100.add(label)

        # (1) Provenance. The coordinate has to exist in the source, unmodified.
        candidates = source.get(label, [])
        if not candidates:
            findings["provenance_errors"].append(
                f"{label} ({row.get('name')!r}): no source row with this DS 100 code"
            )
        else:
            matches = [
                candidate
                for candidate in candidates
                if round(candidate["lat"], COORDINATE_DECIMALS) == lat
                and round(candidate["lon"], COORDINATE_DECIMALS) == lon
            ]
            if not matches:
                findings["provenance_errors"].append(
                    f"{label} ({row.get('name')!r}): {lat}, {lon} is not any of the "
                    f"{len(candidates)} position(s) the source publishes for this code"
                )
            else:
                origin = matches[0]

                # (5) The source's own EPSG:25832 against its own EPSG:4326.
                if origin["utm_x"] is not None:
                    exact_x, exact_y = to_25832.transform(origin["lat"], origin["lon"])
                    findings["source_25832"].append(
                        {
                            "id": label,
                            "distance": math.hypot(
                                origin["utm_x"] - exact_x, origin["utm_y"] - exact_y
                            ),
                        }
                    )

                # (6) The source's numeric EPSG:4326 against its own WKT column.
                if origin["wkt_4326"] is not None:
                    wkt_lon, wkt_lat = origin["wkt_4326"]
                    north = (wkt_lat - origin["lat"]) * METRES_PER_DEGREE
                    east = (
                        (wkt_lon - origin["lon"])
                        * METRES_PER_DEGREE
                        * math.cos(math.radians(origin["lat"]))
                    )
                    findings["source_wkt"].append(
                        {"id": label, "distance": math.hypot(east, north)}
                    )

        # (2) Axis order. A swapped pair puts latitude into the longitude band.
        if not lat_min <= lat <= lat_max:
            if lon_min <= lat <= lon_max:
                findings["axis_order_errors"].append(
                    f"{label}: latitude {lat} lies in the longitude band "
                    f"- latitude and longitude look swapped"
                )
            else:
                findings["bbox_errors"].append(
                    f"{label}: latitude {lat} outside {lat_min}..{lat_max}"
                )
        if not lon_min <= lon <= lon_max:
            findings["bbox_errors"].append(
                f"{label}: longitude {lon} outside {lon_min}..{lon_max}"
            )

        # (3) Containment in the boundary polygon, by ray casting.
        if not boundary.contains(lon, lat):
            findings["outside_boundary"].append(
                f"{label} ({row.get('name')!r}): {lat}, {lon} outside {boundary.name}"
            )

        # (7) How much room the containment verdict had. A station a hundred
        # metres from the border is classified by the polygon's precision as
        # much as by its own coordinate.
        border_distance = boundary.min_distance_m(lon, lat)
        if border_distance is not None:
            findings["border_distances"].append(
                {"id": label, "name": row.get("name", ""), "distance": border_distance}
            )

        # (4) EPSG:3857 recomputed by pyproj.
        exact_x, exact_y = to_3857.transform(lat, lon)
        dx = written_x - exact_x
        dy = written_y - exact_y
        findings["deviations_3857"].append(
            {"id": label, "dx": dx, "dy": dy, "distance": math.hypot(dx, dy)}
        )

    return findings


def render_report(
    findings: dict,
    source_path: Path,
    input_path: Path,
    boundary: Boundary,
    bbox: tuple[float, float, float, float],
    tolerance: float,
    border_margin: float,
    row_count: int,
    bands_overlap: bool,
    max_listed: int,
) -> str:
    """Render the verification result as Markdown."""
    lon_min, lon_max, lat_min, lat_max = bbox
    off_tolerance = [d for d in findings["deviations_3857"] if d["distance"] > tolerance]
    near_border = sorted(
        (d for d in findings["border_distances"] if d["distance"] <= border_margin),
        key=lambda d: d["distance"],
    )

    def status(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    lines = [
        "# Station verification report",
        "",
        f"- Verified file: `{input_path}`",
        f"- Source fixture: `{source_path}`",
        f"- Stations checked: {row_count:,}",
        f"- Boundary: {boundary.name}, {boundary.vertex_count:,} vertices",
        f"- Bounding box: lat {lat_min:.4f}..{lat_max:.4f} / lon {lon_min:.4f}..{lon_max:.4f}",
        f"- EPSG:3857 tolerance: {tolerance:g} m",
        f"- Boundary-sensitivity margin: {border_margin:g} m",
        "",
        "Generated by `scripts/verify_stations.py`. Projections are recomputed with",
        "pyproj (PROJ), independently of the builder's hand-written formula;",
        "containment is recomputed by ray casting, independently of the builder's",
        "shapely call. Regenerate with the command in [`../README.md`](../README.md).",
        "",
    ]

    if bands_overlap:
        lines += [
            "> **Warning:** the latitude and longitude bands of this bounding box",
            "> overlap, so a swapped coordinate pair can still fall inside both.",
            "> The axis-order check below cannot be trusted for this region.",
            "",
        ]

    lines += [
        "## Summary",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
        f"| Schema and column types | {status(not findings['schema_errors'])} | "
        f"{len(findings['schema_errors'])} violations |",
        f"| DS 100 codes unique | {status(not findings['duplicate_ds100'])} | "
        f"{len(findings['duplicate_ds100'])} duplicates |",
        f"| Provenance: coordinate exists in the source | "
        f"{status(not findings['provenance_errors'])} | "
        f"{len(findings['provenance_errors'])} rows not traceable |",
        f"| Axis order (latitude/longitude not swapped) | "
        f"{status(not findings['axis_order_errors'])} | "
        f"{len(findings['axis_order_errors'])} suspected swaps |",
        f"| Inside bounding box | {status(not findings['bbox_errors'])} | "
        f"{len(findings['bbox_errors'])} violations |",
        f"| Inside {boundary.name} (ray casting) | "
        f"{status(not findings['outside_boundary'])} | "
        f"{len(findings['outside_boundary'])} outside |",
        f"| EPSG:3857 within tolerance (pyproj) | {status(not off_tolerance)} | "
        f"{len(off_tolerance):,} of {len(findings['deviations_3857']):,} rows off |",
        f"| Distance to the state border | INFO | "
        f"{len(near_border):,} station(s) within {border_margin:g} m, of "
        f"{len(findings['border_distances']):,} measured |",
        "",
        "## EPSG:3857 deviation",
        "",
        "Distance between the `x_3857`/`y_3857` written into the CSV and the value",
        "pyproj computes from the `latitude`/`longitude` of the same row. The builder",
        "rounds the geographic coordinates *before* projecting, so this should be",
        "zero to within floating-point noise; anything else means one of the two",
        "implementations is wrong.",
        "",
        "| Metric | Metres |",
        "|---|---|",
        *statistics_block([d["distance"] for d in findings["deviations_3857"]]),
        "",
    ]

    top = sorted(
        findings["deviations_3857"], key=lambda d: d["distance"], reverse=True
    )[:10]
    if top and top[0]["distance"] > tolerance:
        lines += [
            "### Ten largest deviations",
            "",
            "| ds100 | dx (m) | dy (m) | distance (m) |",
            "|---|---|---|---|",
            *(
                f"| {d['id']} | {d['dx']:+,.3f} | {d['dy']:+,.3f} | {d['distance']:,.3f} |"
                for d in top
            ),
            "",
        ]

    lines += [
        "## Source quality (informational)",
        "",
        "Neither of the following is a defect of this repository. Both are properties",
        "of the upstream data set, measured here because an official source is still",
        "only a source.",
        "",
        "### The source's EPSG:25832 columns against its own EPSG:4326 columns",
        "",
        "UTM 32N recomputed by pyproj from the source's `Geographische Länge/Breite`,",
        "compared with the source's `UTM Rechtswert/Hochwert` of the same row.",
        "",
        "| Metric | Metres |",
        "|---|---|",
        *statistics_block([d["distance"] for d in findings["source_25832"]]),
        "",
        "### The source's numeric EPSG:4326 columns against its own WKT column",
        "",
        "`Geographische Länge/Breite (EPSG 4326)` compared with the coordinate inside",
        "`WKT WGS84 (EPSG 4326)` of the *same row* - two derivations of one point that",
        "do not agree.",
        "",
        "| Metric | Metres |",
        "|---|---|",
        *statistics_block([d["distance"] for d in findings["source_wkt"]]),
        "",
        "## Boundary sensitivity (informational)",
        "",
        f"Distance from each station to the border of {boundary.name}. A station a",
        "few hundred metres from the line is classified as much by the precision of",
        "the polygon as by its own coordinate - which is not hypothetical here: a",
        "generalised Natural Earth outline put one station 1.3 km outside NRW that",
        "the authoritative boundary puts 117 m inside.",
        "",
        f"Measured for {len(findings['border_distances']):,} of {row_count:,} stations;",
        "the rest lie further from every border segment than the search window, which",
        "is answer enough. The statistics below therefore describe the near-border",
        "subset, not all stations.",
        "",
        "| Metric | Metres |",
        "|---|---|",
        *statistics_block([d["distance"] for d in findings["border_distances"]]),
        "",
        f"### Stations within {border_margin:g} m of the border",
        "",
    ]
    if near_border:
        lines += [
            "| ds100 | name | distance (m) |",
            "|---|---|---|",
            *(
                f"| {d['id']} | {d['name']} | {d['distance']:,.0f} |"
                for d in near_border[:max_listed]
            ),
            "",
        ]
    else:
        lines += ["_none_", ""]

    sections = (
        ("Schema violations", "schema_errors", "Structural failure - blocks a pass."),
        (
            "Duplicate DS 100 codes", "duplicate_ds100",
            "Structural failure - blocks a pass. One station, one row.",
        ),
        (
            "Untraceable coordinates", "provenance_errors",
            "Structural failure - blocks a pass. Every coordinate in the output must "
            "be a coordinate the source published for that DS 100 code, rounded to "
            f"{COORDINATE_DECIMALS} decimals and otherwise untouched. This is the "
            "check that separates transformed data from invented data.",
        ),
        ("Suspected axis swaps", "axis_order_errors", "Structural failure - blocks a pass."),
        ("Bounding box violations", "bbox_errors", "Structural failure - blocks a pass."),
        (
            f"Stations outside {boundary.name}", "outside_boundary",
            "Structural failure - blocks a pass. The builder already drops these, so a "
            "finding here means the two containment implementations disagree. The "
            "polygon is generalised, so a borderline station would show up here first.",
        ),
    )
    for title, key, note in sections:
        lines += [f"## {title}", "", note, ""]
        entries = findings[key]
        if entries:
            lines += [f"- {entry}" for entry in entries[:max_listed]]
            if len(entries) > max_listed:
                lines.append(
                    f"- _... and {len(entries) - max_listed:,} more, not listed "
                    f"(raise `--max-listed` to see them all)_"
                )
        else:
            lines.append("_none_")
        lines.append("")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_stations.py",
        description=(
            "Verify a station CSV against its source fixture and its boundary "
            "polygon: schema, DS 100 uniqueness, provenance of every coordinate, "
            "latitude/longitude axis order, bounding box, polygon containment and "
            "EPSG:3857 accuracy. Projections come from pyproj and containment from "
            "ray casting, so neither check shares an implementation with the "
            "builder it is checking."
        ),
        epilog=(
            "Examples:\n"
            "  # Report to stdout\n"
            "  .venv/bin/python scripts/verify_stations.py\n\n"
            "  # Report to a file\n"
            "  .venv/bin/python scripts/verify_stations.py \\\n"
            "      --input  output/nrw_stations.csv \\\n"
            "      --report output/verification_report.md\n\n"
            "Exit code 0 if every structural check passes, 1 otherwise. Unlike the\n"
            "csv_data verifier this one has nothing to correct - the coordinates are\n"
            "the source's, not a model's - so it writes no data file and needs no\n"
            "destructive flag."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", type=Path, default=Path("output/nrw_stations.csv"), metavar="CSV",
        help="station CSV to verify (default: %(default)s)",
    )
    parser.add_argument(
        "--source", type=Path,
        default=Path("input/db_infrago_betriebsstellen_nrw.csv"), metavar="CSV",
        help="source fixture every coordinate must be traceable to "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--boundary", type=Path, default=Path("input/nrw_boundary_dvg2.geojson"),
        metavar="GEOJSON",
        help="boundary polygon for the containment check; the bounding box is "
        "derived from it. The default is the authoritative Geobasis NRW outline; "
        "pass input/nrw_boundary_ne10m.geojson to reproduce what the generalised "
        "one reports (default: %(default)s)",
    )
    parser.add_argument(
        "--report", type=Path, default=None, metavar="MD",
        help="write the Markdown report to this path; without it the report goes "
        "to stdout. No default on purpose - a verifier must not overwrite a file "
        "nobody named",
    )
    parser.add_argument(
        "--bbox", nargs=4, type=float, metavar=("LON_MIN", "LON_MAX", "LAT_MIN", "LAT_MAX"),
        help="override the bounding box instead of deriving it from --boundary",
    )
    parser.add_argument(
        "--tolerance", type=float, default=1.0, metavar="METRES",
        help="allowed EPSG:3857 deviation before a row counts as off "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--border-margin", type=float, default=250.0, metavar="METRES",
        help="stations closer than this to the boundary are listed as "
        "boundary-sensitive: their membership depends on the precision of the "
        "polygon, not on the data (default: %(default)s)",
    )
    parser.add_argument(
        "--max-listed", type=int, default=200, metavar="N",
        help="maximum number of individual findings listed per report section "
        "(default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    for path in (args.input, args.source, args.boundary):
        if not path.is_file():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 1

    with args.input.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    missing = [c for c in REQUIRED_OUTPUT_COLUMNS if c not in fieldnames]
    if missing:
        print(
            f"error: {args.input} is missing columns: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    boundary = load_boundary(args.boundary)
    bbox = tuple(args.bbox) if args.bbox else boundary.bounds  # type: ignore[assignment]
    lon_min, lon_max, lat_min, lat_max = bbox
    bands_overlap = lat_min <= lon_max and lon_min <= lat_max
    if bands_overlap:
        print(
            "warning: latitude and longitude bands overlap for this bounding box "
            "- the axis-order check cannot detect a swap here",
            file=sys.stderr,
        )

    source = read_source_positions(args.source)
    print(
        f"source: {args.source} | {len(source):,} distinct DS 100 codes, "
        f"{sum(len(v) for v in source.values()):,} positions"
    )

    # always_xy=False: these transformers take (latitude, longitude), matching the
    # column order of the CSV. Getting this wrong is the classic pyproj trap.
    to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=False)
    to_25832 = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=False)

    findings = check(rows, source, boundary, bbox, to_3857, to_25832)

    report = render_report(
        findings, args.source, args.input, boundary, bbox, args.tolerance,
        args.border_margin, len(rows), bands_overlap, args.max_listed,
    )
    if args.report is None:
        print(report)
    else:
        args.report.write_text(report + "\n", encoding="utf-8")
        print(f"wrote {args.report}")

    distances = [d["distance"] for d in findings["deviations_3857"]]
    off_tolerance = [d for d in distances if d > args.tolerance]
    structural = sum(
        len(findings[key])
        for key in (
            "schema_errors", "duplicate_ds100", "provenance_errors",
            "axis_order_errors", "bbox_errors", "outside_boundary",
        )
    ) + len(off_tolerance)

    print(
        f"{len(rows):,} stations checked | structural failures: {structural} | "
        f"max EPSG:3857 deviation: {max(distances, default=0.0):,.3f} m | "
        f"untraceable coordinates: {len(findings['provenance_errors'])} | "
        f"outside {boundary.name}: {len(findings['outside_boundary'])}"
    )
    return 1 if structural else 0


if __name__ == "__main__":
    sys.exit(main())
