#!/usr/bin/env python3
"""One-off provisioning: extract the North Rhine-Westphalia boundary from Natural Earth.

This is NOT part of the build pipeline. It produced
`input/nrw_boundary_ne10m.geojson` once; that file is committed, so nobody needs
to run this again. It exists to record the provenance of an input fixture in
code rather than in prose.

Why this boundary is needed at all: the source data set carries a `Bundesland`
column, so filtering NRW looks like a pure attribute query. It is not. An
attribute is an assertion by the data producer; the geometry is the fact. One
row of the 905 NRW rows in the source claims `Bundesland = Nordrhein-Westfalen`
while its coordinates sit in Lower Saxony - and only a geometric test finds it.

Natural Earth is in the public domain ("no restrictions"), which is what makes
it usable in a repository published under CC BY. The authoritative alternative,
`opengeodata.nrw.de` DVG (Datenlizenz Deutschland - Zero - 2.0), is more precise
but ships Shapefile in EPSG:25832 only; see the README for why it was deferred.
Licence and source URL are written into the output feature's properties so the
fixture carries its own attribution.

The upstream file is ~40 MB of world-wide admin-1 polygons; only the NRW feature
is kept, which brings the committed fixture down to ~30 KB.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

NE_10M_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_10m_admin_1_states_provinces.geojson"
)
LICENCE = "Public domain (Natural Earth, https://www.naturalearthdata.com/about/terms-of-use/)"


def find_state(collection: dict, iso_3166_2: str, name: str) -> dict:
    """Return the feature for one admin-1 unit, matched on ISO code or name."""
    for feature in collection.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("iso_3166_2") == iso_3166_2 or properties.get("name") == name:
            return feature
    raise LookupError(f"no feature matching iso_3166_2={iso_3166_2!r} / name={name!r}")


def ring_stats(geometry: dict) -> tuple[int, int]:
    """Return (ring count, vertex count) for a Polygon or MultiPolygon."""
    coordinates = geometry["coordinates"]
    if geometry["type"] == "Polygon":
        rings = coordinates
    elif geometry["type"] == "MultiPolygon":
        rings = [ring for polygon in coordinates for ring in polygon]
    else:
        raise ValueError(f"unsupported geometry type: {geometry['type']}")
    return len(rings), sum(len(ring) for ring in rings)


def bounds(geometry: dict) -> tuple[float, float, float, float]:
    """Return (lon_min, lat_min, lon_max, lat_max) of a Polygon/MultiPolygon."""
    coordinates = geometry["coordinates"]
    rings = (
        coordinates
        if geometry["type"] == "Polygon"
        else [ring for polygon in coordinates for ring in polygon]
    )
    lons = [point[0] for ring in rings for point in ring]
    lats = [point[1] for ring in rings for point in ring]
    return min(lons), min(lats), max(lons), max(lats)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fetch_nrw_boundary_ne10m.py",
        description=(
            "Download Natural Earth 10m admin-1 boundaries, extract one state "
            "and write it as a minimal GeoJSON fixture with source and licence "
            "recorded in its properties. One-off provisioning tool - the output "
            "is committed, so this normally does not need to be run."
        ),
        epilog=(
            "Example:\n"
            "  .venv/bin/python scripts/fetch_nrw_boundary_ne10m.py \\\n"
            "      --output input/nrw_boundary_ne10m.geojson\n\n"
            "Requires network access. The build and verify steps run offline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url", default=NE_10M_URL, metavar="URL",
        help="Natural Earth admin-1 GeoJSON to download (default: the 10m dataset)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("input/nrw_boundary_ne10m.geojson"),
        metavar="GEOJSON", help="where to write the fixture (default: %(default)s)",
    )
    parser.add_argument(
        "--iso-3166-2", default="DE-NW", metavar="CODE",
        help="ISO 3166-2 code of the state to extract (default: %(default)s)",
    )
    parser.add_argument(
        "--name", default="Nordrhein-Westfalen", metavar="NAME",
        help="fallback state name if the ISO code does not match (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print(f"downloading {args.url}")
    try:
        with urllib.request.urlopen(args.url, timeout=300) as response:
            collection = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # network, TLS, JSON - all equally fatal here
        print(f"error: download failed: {exc}", file=sys.stderr)
        return 1

    try:
        feature = find_state(collection, args.iso_3166_2, args.name)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    geometry = feature["geometry"]
    rings, vertices = ring_stats(geometry)
    lon_min, lat_min, lon_max, lat_max = bounds(geometry)

    fixture = {
        "type": "FeatureCollection",
        "name": "nrw_boundary_ne10m",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": args.name,
                    "iso_3166_2": args.iso_3166_2,
                    "admin": feature.get("properties", {}).get("admin", "Germany"),
                    "source": "Natural Earth, ne_10m_admin_1_states_provinces",
                    "source_url": args.url,
                    "licence": LICENCE,
                    "scale": "1:10,000,000 - generalised, not survey accuracy",
                    "epsg": 4326,
                    "note": (
                        "GeoJSON coordinate order is [longitude, latitude] per "
                        "RFC 7946 - not [lat, lon]."
                    ),
                    "authoritative": False,
                    "authoritative_alternative": (
                        "opengeodata.nrw.de DVG1/DVG2 (Datenlizenz Deutschland - "
                        "Zero - 2.0), Shapefile in EPSG:25832"
                    ),
                    "rings": rings,
                    "vertices": vertices,
                    "extracted_by": "scripts/fetch_nrw_boundary_ne10m.py",
                },
                "geometry": geometry,
            }
        ],
    }

    args.output.write_text(
        json.dumps(fixture, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    size_kb = args.output.stat().st_size / 1024
    print(
        f"wrote {args.output} | {geometry['type']}, {rings} ring(s), "
        f"{vertices} vertices, {size_kb:.1f} KB"
    )
    print(f"bbox lon {lon_min:.4f}..{lon_max:.4f} | lat {lat_min:.4f}..{lat_max:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
