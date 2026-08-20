#!/usr/bin/env python3
"""Build the NRW railway station CSV from the committed DB InfraGO source slice.

Nothing here is generated. Every coordinate that reaches `output/` is a value
that DB InfraGO published; this script only selects, deduplicates, rounds and
reprojects. That is the point of the use case: the language model did the web
search and the licence triage, not the geometry.

Three things about the source make this more than a column rename, and all three
were found by measuring rather than by reading the documentation:

1. **`Art lang` is a taxonomy, not a flag.** The 1,671 NRW rows contain
   `Bahnhof`, `Haltepunkt`, `Bahnhofsteil`, `Abzweigstelle`, `Überleitstelle`
   and a dozen more. "All railway stations" was asked for, so the filter is an
   exact match on `Bahnhof` - a `Haltepunkt` is a stop, not a station, and a
   `Bahnhofsteil` would double-count one.

2. **A station has no single position.** The source is route-centric: one
   Betriebsstelle appears once per `Streckennummer` running through it, carrying
   that route's kilometre-marker coordinate. The 893 in-service NRW `Bahnhof`
   rows describe 449 stations, up to 15 rows for one of them. 185 of those
   stations carry more than one position, spread by a median of 326 m - worst
   case Köln-Ehrenfeld at 4.05 km. Taking the first row would silently pick a
   point up to ~2 km off. This script picks the **medoid**: the source row
   closest to the station's mean position. A mean would be a coordinate nobody
   published; the medoid keeps a real, authoritative point and stays traceable
   back to a source row. The spread is carried into the output as a column,
   because throwing the uncertainty away is how it gets forgotten.

3. **The boundary is data too, and it can be the thing that is wrong.** The
   polygon check here exists to referee the `Bundesland` attribute rather than
   trust it. Run against a generalised Natural Earth outline it flagged one
   station - `HOE` Osnabrück-Eversburg, whose name says Lower Saxony - and that
   looked exactly like a caught attribute error. It was not. Reverse geocoding
   and the authoritative Geobasis NRW boundary both put the coordinate inside
   North Rhine-Westphalia, 117 m from the border; the generalised polygon was
   off by 1.3 km. Against the authoritative boundary the source's `Bundesland`
   column and the geometry disagree exactly zero times, in either direction,
   across all 5,367 in-service `Bahnhof` rows of the German data set. The check
   stays - a cross-check that currently finds nothing is what makes "nothing to
   find" a measurement - but it defaults to the authoritative polygon, and a
   finding here is a reason to suspect the boundary first.

Coordinate handling follows the repository conventions: `latitude` before
`longitude`, projected columns suffixed with their EPSG code, and the rounding
happens *before* the projection so that every row agrees with itself.

Runs offline from `input/`. Requires shapely.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

from shapely.geometry import Point, shape

# EPSG:3857 uses a sphere of the WGS 84 semi-major axis radius.
EARTH_RADIUS_M = 6378137.0

# Metres per degree of latitude, good enough for the local tangent plane used to
# compare positions of one station a few kilometres apart. Nothing that reaches
# output/ depends on this constant - it only ranks candidates.
METRES_PER_DEGREE = 111_320.0

SOURCE_ENCODING = "utf-8-sig"
SOURCE_DELIMITER = ";"

COLUMN_NAME = "Bezeichnung"
COLUMN_DS100 = "Kürzel"
COLUMN_KIND = "Art lang"
COLUMN_STATUS = "Betriebszustand"
COLUMN_DISTRICT = "Kreis"
COLUMN_ROUTE = "Streckennummer"
COLUMN_LON = "Geographische Länge (EPSG 4326)"
COLUMN_LAT = "Geographische Breite (EPSG 4326)"

REQUIRED_COLUMNS = (
    COLUMN_NAME, COLUMN_DS100, COLUMN_KIND, COLUMN_STATUS,
    COLUMN_DISTRICT, COLUMN_ROUTE, COLUMN_LON, COLUMN_LAT,
)

FIELDNAMES = [
    "ds100", "name", "district", "latitude", "longitude",
    "x_3857", "y_3857", "source_rows", "position_spread_m",
]
RAW_FIELDNAMES = [
    "ds100", "name", "route_number", "latitude", "longitude",
    "distance_to_mean_m", "is_medoid",
]

# The output stores 5 decimals of a degree, ~1.1 m. Coarser would lose platform
# detail, finer would imply an accuracy the source's route-marker positions do
# not have.
COORDINATE_DECIMALS = 5


def parse_german_decimal(value: str) -> float:
    """Parse a number written with a comma as the decimal separator."""
    return float(value.strip().replace(",", "."))


def lonlat_to_web_mercator(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Project EPSG:4326 decimal degrees to EPSG:3857 metres.

    Uses the textbook form `y = R * ln(tan(pi/4 + phi/2))`. The verifier does
    not reimplement this - it calls pyproj, an entirely separate code base - so
    agreement between the two is evidence rather than a tautology.

    Longitude first, then latitude, matching the x/y order of the result.
    """
    x = math.radians(lon_deg) * EARTH_RADIUS_M
    y = EARTH_RADIUS_M * math.log(math.tan(math.pi / 4.0 + math.radians(lat_deg) / 2.0))
    return x, y


def local_offsets(
    lat: float, lon: float, lat0: float, lon0: float
) -> tuple[float, float]:
    """Approximate east/north offsets in metres on a local tangent plane."""
    east = (lon - lon0) * METRES_PER_DEGREE * math.cos(math.radians(lat0))
    north = (lat - lat0) * METRES_PER_DEGREE
    return east, north


def local_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distance in metres between two (lat, lon) pairs on a local tangent plane."""
    east, north = local_offsets(a[0], a[1], b[0], b[1])
    return math.hypot(east, north)


def load_boundary(path: Path):
    """Return (shapely geometry, name) of the first feature in a GeoJSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data["features"] if data.get("type") == "FeatureCollection" else [data]
    for feature in features:
        geometry = feature.get("geometry", feature)
        if geometry.get("type") in ("Polygon", "MultiPolygon"):
            properties = feature.get("properties", {}) or {}
            name = properties.get("name") or data.get("name") or path.stem
            return shape(geometry), name
    raise ValueError(f"no Polygon or MultiPolygon geometry found in {path}")


def read_source(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding=SOURCE_ENCODING, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=SOURCE_DELIMITER)
        return list(reader), list(reader.fieldnames or [])


def group_stations(rows: list[dict[str, str]]) -> dict[str, list[dict]]:
    """Group parsed rows by DS 100 code, keeping the source order stable."""
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["ds100"], []).append(row)
    return groups


def pick_medoid(group: list[dict]) -> tuple[dict, float, list[float]]:
    """Return (medoid row, max pairwise distance in m, distance of each row to the mean).

    The medoid is the input row closest to the group's mean position. Ties are
    broken by source order, so the result is deterministic.
    """
    lat0 = sum(row["lat"] for row in group) / len(group)
    lon0 = sum(row["lon"] for row in group) / len(group)

    distances = [
        math.hypot(*local_offsets(row["lat"], row["lon"], lat0, lon0)) for row in group
    ]
    medoid_index = min(range(len(group)), key=lambda i: (distances[i], i))

    spread = 0.0
    for i in range(len(group)):
        for j in range(i + 1, len(group)):
            spread = max(
                spread,
                local_distance(
                    (group[i]["lat"], group[i]["lon"]),
                    (group[j]["lat"], group[j]["lon"]),
                ),
            )
    return group[medoid_index], spread, distances


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_stations.py",
        description=(
            "Build a CSV of railway stations from the committed DB InfraGO source "
            "slice: filter one Betriebsstellen category, deduplicate the "
            "route-centric rows per station by medoid, drop anything outside the "
            "boundary polygon, round the geographic coordinates and derive "
            "EPSG:3857 from the rounded values. Coordinates are never invented, "
            "only selected."
        ),
        epilog=(
            "Example:\n"
            "  .venv/bin/python scripts/build_stations.py \\\n"
            "      --input    input/db_infrago_betriebsstellen_nrw.csv \\\n"
            "      --boundary input/nrw_boundary_dvg2.geojson \\\n"
            "      --output   output/nrw_stations.csv \\\n"
            "      --raw-output output/nrw_stations_raw_positions.csv\n\n"
            "Runs offline. Verify the result with scripts/verify_stations.py."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", type=Path,
        default=Path("input/db_infrago_betriebsstellen_nrw.csv"), metavar="CSV",
        help="committed DB InfraGO source slice (default: %(default)s)",
    )
    parser.add_argument(
        "--boundary", type=Path, default=Path("input/nrw_boundary_dvg2.geojson"),
        metavar="GEOJSON",
        help="boundary polygon every station must fall inside. The default is the "
        "authoritative Geobasis NRW outline; input/nrw_boundary_ne10m.geojson is "
        "the generalised one it replaced, kept for comparison "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output/nrw_stations.csv"), metavar="CSV",
        help="where to write the deduplicated station CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--raw-output", type=Path,
        default=Path("output/nrw_stations_raw_positions.csv"), metavar="CSV",
        help="where to write every pre-deduplication source position, as evidence "
        "of the per-station spread (default: %(default)s)",
    )
    parser.add_argument(
        "--kind", default="Bahnhof", metavar="NAME",
        help=f"exact value of the source's {COLUMN_KIND!r} column to keep. "
        "'Haltepunkt' and 'Bahnhofsteil' are deliberately NOT included "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--betriebszustand", default="in Betrieb", metavar="NAME",
        help=f"exact value of the source's {COLUMN_STATUS!r} column to keep; pass "
        "an empty string to keep all operational states (default: %(default)s)",
    )
    parser.add_argument(
        "--keep-outside-boundary", action="store_true",
        help="keep stations whose coordinates fall outside the boundary polygon "
        "instead of dropping them; they are listed on stdout either way",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    for path in (args.input, args.boundary):
        if not path.is_file():
            print(f"error: input file not found: {path}", file=sys.stderr)
            return 1

    source_rows, fieldnames = read_source(args.input)
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        print(
            f"error: {args.input} is missing columns: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    print(f"source: {args.input} | {len(source_rows):,} rows, {len(fieldnames)} columns")

    kinds = sorted({row[COLUMN_KIND] for row in source_rows})
    by_kind = [row for row in source_rows if row[COLUMN_KIND] == args.kind]
    if not by_kind:
        print(
            f"error: no rows with {COLUMN_KIND}={args.kind!r}. Values present: "
            f"{', '.join(kinds)}",
            file=sys.stderr,
        )
        return 1
    print(
        f"filter {COLUMN_KIND} == {args.kind!r}: {len(by_kind):,} rows "
        f"(of {len(kinds)} categories in the source)"
    )

    if args.betriebszustand:
        before = len(by_kind)
        dropped_status = sorted(
            {row[COLUMN_STATUS] for row in by_kind if row[COLUMN_STATUS] != args.betriebszustand}
        )
        by_kind = [row for row in by_kind if row[COLUMN_STATUS] == args.betriebszustand]
        print(
            f"filter {COLUMN_STATUS} == {args.betriebszustand!r}: {len(by_kind):,} rows "
            f"({before - len(by_kind)} dropped"
            + (f", states removed: {', '.join(dropped_status)}" if dropped_status else "")
            + ")"
        )

    parsed: list[dict] = []
    for number, row in enumerate(by_kind, start=2):  # line 1 is the header
        try:
            lat = parse_german_decimal(row[COLUMN_LAT])
            lon = parse_german_decimal(row[COLUMN_LON])
        except (TypeError, ValueError) as exc:
            print(
                f"error: line {number} ({row.get(COLUMN_NAME)!r}) has unparseable "
                f"coordinates: {exc}",
                file=sys.stderr,
            )
            return 1
        parsed.append(
            {
                "ds100": row[COLUMN_DS100].strip(),
                "name": row[COLUMN_NAME].strip(),
                "district": row[COLUMN_DISTRICT].strip(),
                "route": row[COLUMN_ROUTE].strip(),
                "lat": lat,
                "lon": lon,
            }
        )

    groups = group_stations(parsed)
    print(f"distinct stations by {COLUMN_DS100}: {len(groups):,}")

    boundary, boundary_name = load_boundary(args.boundary)

    stations: list[dict] = []
    raw_rows: list[dict] = []
    outside: list[tuple[str, str, float, float]] = []
    spreads: list[float] = []
    multi_row_stations = 0

    for ds100, group in groups.items():
        medoid, spread, distances = pick_medoid(group)
        spreads.append(spread)
        if len(group) > 1:
            multi_row_stations += 1

        for row, distance in zip(group, distances):
            raw_rows.append(
                {
                    "ds100": ds100,
                    "name": row["name"],
                    "route_number": row["route"],
                    "latitude": f"{row['lat']:.{COORDINATE_DECIMALS}f}",
                    "longitude": f"{row['lon']:.{COORDINATE_DECIMALS}f}",
                    "distance_to_mean_m": f"{distance:.1f}",
                    "is_medoid": "true" if row is medoid else "false",
                }
            )

        inside = boundary.contains(Point(medoid["lon"], medoid["lat"]))
        if not inside:
            outside.append((ds100, medoid["name"], medoid["lat"], medoid["lon"]))
            if not args.keep_outside_boundary:
                continue

        # Round FIRST, then project. The CSV carries 5 decimals (~1.1 m), so
        # projecting the unrounded value would leave x_3857/y_3857 disagreeing
        # with the latitude/longitude in the same row. Anyone recomputing the
        # projection from this file must get these numbers back exactly.
        lat = round(medoid["lat"], COORDINATE_DECIMALS)
        lon = round(medoid["lon"], COORDINATE_DECIMALS)
        x, y = lonlat_to_web_mercator(lon, lat)
        stations.append(
            {
                "ds100": ds100,
                "name": medoid["name"],
                "district": medoid["district"],
                "latitude": f"{lat:.{COORDINATE_DECIMALS}f}",
                "longitude": f"{lon:.{COORDINATE_DECIMALS}f}",
                "x_3857": f"{x:.2f}",
                "y_3857": f"{y:.2f}",
                "source_rows": len(group),
                "position_spread_m": f"{spread:.1f}",
            }
        )

    stations.sort(key=lambda station: (station["name"], station["ds100"]))
    raw_rows.sort(key=lambda row: (row["name"], row["ds100"], row["route_number"]))

    for path, names, rows in (
        (args.output, FIELDNAMES, stations),
        (args.raw_output, RAW_FIELDNAMES, raw_rows),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    print(
        f"stations outside {boundary_name}: {len(outside)}"
        + (" (kept, --keep-outside-boundary)" if args.keep_outside_boundary and outside else "")
    )
    for ds100, name, lat, lon in outside:
        verb = "kept" if args.keep_outside_boundary else "dropped"
        print(f"  {verb}: {ds100} {name} at {lat:.5f}, {lon:.5f}")

    # Two medians, because one of them is misleading on its own: most stations
    # sit on a single route and have a spread of exactly 0 m, which drags the
    # overall median to zero and hides the multi-route cases entirely.
    spreads.sort()
    multi_spreads = sorted(spread for spread in spreads if spread > 0.0)
    median_all = spreads[len(spreads) // 2] if spreads else 0.0
    median_multi = multi_spreads[len(multi_spreads) // 2] if multi_spreads else 0.0
    print(
        f"per-station position spread: median {median_all:,.0f} m over all "
        f"{len(groups):,} stations, {median_multi:,.0f} m over the "
        f"{multi_row_stations:,} with more than one source row | "
        f"max {max(spreads, default=0.0):,.0f} m"
    )
    print(
        f"wrote {args.output} | {len(stations):,} stations, "
        f"{args.output.stat().st_size / 1024:.1f} KB"
    )
    print(
        f"wrote {args.raw_output} | {len(raw_rows):,} source positions, "
        f"{args.raw_output.stat().st_size / 1024:.1f} KB"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
