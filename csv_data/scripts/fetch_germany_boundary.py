#!/usr/bin/env python3
"""One-off provisioning: extract the Germany boundary from Natural Earth.

This is NOT part of the generation pipeline. It produced
`input/germany_boundary_ne50m.geojson` once; that file is committed, so nobody
needs to run this again. It exists to record the provenance of an input fixture
in code rather than in prose.

Natural Earth is in the public domain ("no restrictions"), which is what makes
it usable in a repository published under CC BY. Licence and source URL are
written into the output feature's properties so the fixture carries its own
attribution.

The upstream file is ~3 MB of world-wide country polygons; only the Germany
feature is kept, which brings the committed fixture down to ~25 KB.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

NE_50M_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_50m_admin_0_countries.geojson"
)
LICENCE = "Public domain (Natural Earth, https://www.naturalearthdata.com/about/terms-of-use/)"


def find_country(collection: dict, iso_a3: str, admin: str) -> dict:
    """Return the feature for one country, matched on ISO A3 or admin name."""
    for feature in collection.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("ISO_A3") == iso_a3 or properties.get("ADMIN") == admin:
            return feature
    raise LookupError(f"no feature matching ISO_A3={iso_a3!r} / ADMIN={admin!r}")


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
    lons = [lon for ring in rings for lon, _ in ring]
    lats = [lat for ring in rings for _, lat in ring]
    return min(lons), min(lats), max(lons), max(lats)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fetch_germany_boundary.py",
        description=(
            "Download Natural Earth 50m admin-0 boundaries, extract one country "
            "and write it as a minimal GeoJSON fixture with source and licence "
            "recorded in its properties. One-off provisioning tool - the output "
            "is committed, so this normally does not need to be run."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/fetch_germany_boundary.py \\\n"
            "      --output input/germany_boundary_ne50m.geojson\n\n"
            "Requires network access. Everything else in this use case runs offline."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url", default=NE_50M_URL, metavar="URL",
        help="Natural Earth admin-0 GeoJSON to download (default: the 50m dataset)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("input/germany_boundary_ne50m.geojson"),
        metavar="GEOJSON", help="where to write the fixture (default: %(default)s)",
    )
    parser.add_argument(
        "--iso-a3", default="DEU", metavar="CODE",
        help="ISO 3166-1 alpha-3 code of the country to extract (default: %(default)s)",
    )
    parser.add_argument(
        "--admin", default="Germany", metavar="NAME",
        help="fallback admin name if the ISO code does not match (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print(f"downloading {args.url}")
    try:
        with urllib.request.urlopen(args.url, timeout=120) as response:
            collection = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # network, TLS, JSON - all equally fatal here
        print(f"error: download failed: {exc}", file=sys.stderr)
        return 1

    try:
        feature = find_country(collection, args.iso_a3, args.admin)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    geometry = feature["geometry"]
    rings, vertices = ring_stats(geometry)
    lon_min, lat_min, lon_max, lat_max = bounds(geometry)

    fixture = {
        "type": "FeatureCollection",
        "name": f"{args.admin.lower()}_boundary_ne50m",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": args.admin,
                    "iso_a3": args.iso_a3,
                    "source": "Natural Earth, ne_50m_admin_0_countries",
                    "source_url": args.url,
                    "licence": LICENCE,
                    "scale": "1:50,000,000 - generalised, not survey accuracy",
                    "epsg": 4326,
                    "note": (
                        "GeoJSON coordinate order is [longitude, latitude] per "
                        "RFC 7946 - not [lat, lon]."
                    ),
                    "rings": rings,
                    "vertices": vertices,
                    "extracted_by": "scripts/fetch_germany_boundary.py",
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
    print(
        f"bbox lon {lon_min:.3f}..{lon_max:.3f} | lat {lat_min:.3f}..{lat_max:.3f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
