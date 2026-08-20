#!/usr/bin/env python3
"""One-off provisioning: extract the authoritative NRW boundary from OpenGeodata.NRW.

This is NOT part of the build pipeline. It produced
`input/nrw_boundary_dvg2.geojson` once; that file is committed, so nobody needs
to run this again.

**Why this script exists at all is the most useful thing in this use case.** The
first version of the pipeline used a Natural Earth 10m polygon (see
`fetch_nrw_boundary_ne10m.py`, kept as evidence). It is public domain, it is a
30 KB GeoJSON in EPSG:4326, and it was wrong: it placed `HOE`
Osnabrück-Eversburg 1.3 km *outside* North Rhine-Westphalia, so the builder
dropped a station that really is in NRW. The station's name says Osnabrück -
Lower Saxony - which made the false positive look exactly like a genuine
attribute error in the source, and it was reported as one.

Two independent checks settled it. Reverse geocoding puts the coordinate in
Lotte, Kreis Steinfurt, North Rhine-Westphalia. The authoritative boundary
below puts it 117 m inside the state. Across all 5,367 in-service `Bahnhof`
rows of the German data set, the source's `Bundesland` attribute and this
polygon disagree exactly zero times, in either direction. The data was right;
the boundary was the bug.

Hence: `Datenlizenz Deutschland - Zero - Version 2.0` ("any use is permitted
without restrictions or conditions"), which is as compatible with CC BY as a
licence gets. Source and licence are written into the output feature's
properties so the fixture carries its own attribution, together with the
generalisation figures the provider publishes about its own data.

DVG2 is the low-vertex-density variant: 74,816 km of boundary line against
76,843 km in the original, a 2.6 % reduction. That is generalisation measured in
metres, not the kilometres Natural Earth costs, and the provider states it - so
the fixture records it too.

The upstream download is a 2.5 MB ZIP of five Shapefiles at four administrative
levels; only the `dvg2bld_nw` state layer is kept and reprojected from
EPSG:25832 to EPSG:4326.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import requests
import shapefile
from pyproj import Transformer

DVG2_ZIP_URL = (
    "https://www.opengeodata.nrw.de/produkte/geobasis/vkg/dvg/dvg2/"
    "dvg2_EPSG25832_Shape.zip"
)
PRODUCT_URL = "https://www.opengeodata.nrw.de/produkte/geobasis/vkg/dvg/dvg2/"
LAYER = "dvg2bld_nw"  # bld = Bundesland, the state outline
SOURCE_EPSG = 25832  # ETRS89 / UTM zone 32N, per the Shapefile's .prj
TARGET_EPSG = 4326
LICENCE = (
    "Datenlizenz Deutschland - Zero - Version 2.0 "
    "(https://www.govdata.de/dl-de/zero-2-0)"
)
ATTRIBUTION = "Land NRW / Geobasis NRW - Digitale Verwaltungsgrenzen (DVG2)"

# 6 decimals is ~0.11 m at this latitude - far finer than a generalised
# administrative boundary can justify, and it keeps the fixture small.
COORDINATE_DECIMALS = 6
DOWNLOAD_CHUNK = 1 << 16


def reproject_ring(
    ring: list[tuple[float, float]], transformer: Transformer
) -> list[list[float]]:
    """Reproject one ring to EPSG:4326 and round it, in GeoJSON [lon, lat] order."""
    xs = [point[0] for point in ring]
    ys = [point[1] for point in ring]
    lons, lats = transformer.transform(xs, ys)
    return [
        [round(lon, COORDINATE_DECIMALS), round(lat, COORDINATE_DECIMALS)]
        for lon, lat in zip(lons, lats)
    ]


def shapefile_to_multipolygon(
    reader: shapefile.Reader, transformer: Transformer
) -> tuple[dict, dict]:
    """Return (GeoJSON MultiPolygon in EPSG:4326, the layer's single record)."""
    records = list(reader.iterShapeRecords())
    if len(records) != 1:
        raise ValueError(
            f"expected exactly one feature in {LAYER}, found {len(records)}"
        )
    entry = records[0]
    geometry = entry.shape.__geo_interface__

    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = list(geometry["coordinates"])
    else:
        raise ValueError(f"unsupported geometry type: {geometry['type']}")

    reprojected = [
        [reproject_ring(ring, transformer) for ring in polygon] for polygon in polygons
    ]
    record = {
        key: (value.isoformat() if isinstance(value, date) else value)
        for key, value in entry.record.as_dict().items()
    }
    return {"type": "MultiPolygon", "coordinates": reprojected}, record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fetch_nrw_boundary.py",
        description=(
            "Download the authoritative Digitale Verwaltungsgrenzen (DVG2) of "
            "North Rhine-Westphalia from OpenGeodata.NRW, reproject the state "
            "outline from EPSG:25832 to EPSG:4326 and write it as a GeoJSON "
            "fixture with source, licence and the provider's own generalisation "
            "figures in its properties. One-off provisioning tool - the output is "
            "committed, so this normally does not need to be run."
        ),
        epilog=(
            "Example:\n"
            "  .venv/bin/python scripts/fetch_nrw_boundary.py \\\n"
            "      --output input/nrw_boundary_dvg2.geojson\n\n"
            "Requires network access. The build and verify steps run offline.\n"
            "This supersedes scripts/fetch_nrw_boundary_ne10m.py, which produced a\n"
            "generalised public-domain boundary that misclassified one station."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url", default=DVG2_ZIP_URL, metavar="URL",
        help="Shapefile ZIP to download (default: the DVG2 EPSG:25832 package)",
    )
    parser.add_argument(
        "--layer", default=LAYER, metavar="NAME",
        help="Shapefile base name inside the ZIP to extract; 'bld' is the state "
        "outline, 'rbz'/'krs'/'gem' are the finer levels (default: %(default)s)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("input/nrw_boundary_dvg2.geojson"),
        metavar="GEOJSON", help="where to write the fixture (default: %(default)s)",
    )
    parser.add_argument(
        "--build-dir", type=Path, default=Path("build"), metavar="DIR",
        help="disposable directory for the downloaded ZIP and the extracted "
        "Shapefiles (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, metavar="SECONDS",
        help="HTTP timeout for the download (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.build_dir.mkdir(parents=True, exist_ok=True)

    archive = args.build_dir / Path(args.url).name
    print(f"downloading {args.url}")
    try:
        with requests.get(args.url, stream=True, timeout=args.timeout) as response:
            response.raise_for_status()
            with archive.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK):
                    handle.write(chunk)
    except Exception as exc:  # network, TLS, HTTP status - all equally fatal here
        print(f"error: download failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {archive} | {archive.stat().st_size / 1_048_576:.1f} MB")

    extracted = args.build_dir / archive.stem
    try:
        with zipfile.ZipFile(archive) as bundle:
            members = [
                name for name in bundle.namelist() if Path(name).stem == args.layer
            ]
            if not members:
                stems = sorted({Path(name).stem for name in bundle.namelist()})
                print(
                    f"error: no layer {args.layer!r} in the archive. Layers: "
                    f"{', '.join(stems)}",
                    file=sys.stderr,
                )
                return 1
            bundle.extractall(extracted, members=members)
    except Exception as exc:  # a truncated or moved archive
        print(f"error: could not read the archive: {exc}", file=sys.stderr)
        return 1

    transformer = Transformer.from_crs(
        f"EPSG:{SOURCE_EPSG}", f"EPSG:{TARGET_EPSG}", always_xy=True
    )
    try:
        with shapefile.Reader(str(extracted / args.layer)) as reader:
            geometry, record = shapefile_to_multipolygon(reader, transformer)
    except Exception as exc:
        print(f"error: could not read the Shapefile: {exc}", file=sys.stderr)
        return 1

    rings = [ring for polygon in geometry["coordinates"] for ring in polygon]
    vertices = sum(len(ring) for ring in rings)
    points = [point for ring in rings for point in ring]
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]

    fixture = {
        "type": "FeatureCollection",
        "name": "nrw_boundary_dvg2",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": record.get("GN", "Nordrhein-Westfalen"),
                    "iso_3166_2": "DE-NW",
                    "regional_key": record.get("KN"),
                    "source": (
                        f"Geobasis NRW, Digitale Verwaltungsgrenzen DVG2, "
                        f"layer {args.layer}"
                    ),
                    "source_url": args.url,
                    "source_product_url": PRODUCT_URL,
                    "licence": LICENCE,
                    "attribution": ATTRIBUTION,
                    "attribution_required": False,
                    "retrieved": date.today().isoformat(),
                    "data_status": record.get("STAND"),
                    "authoritative": True,
                    "source_epsg": SOURCE_EPSG,
                    "epsg": TARGET_EPSG,
                    "reprojected_by": f"pyproj, EPSG:{SOURCE_EPSG} -> EPSG:{TARGET_EPSG}",
                    "coordinate_decimals": COORDINATE_DECIMALS,
                    "generalisation": {
                        "variant": "DVG2 (low vertex density)",
                        "boundary_length_original_km": record.get("LAENGE_ORI"),
                        "boundary_length_generalised_km": record.get("LAENGE_GEN"),
                        "note": (
                            "Figures published by the provider. The finer DVG1 "
                            "variant is available at the same site."
                        ),
                    },
                    "note": (
                        "GeoJSON coordinate order is [longitude, latitude] per "
                        "RFC 7946 - not [lat, lon]."
                    ),
                    "supersedes": "nrw_boundary_ne10m.geojson",
                    "supersedes_reason": (
                        "The Natural Earth 10m polygon placed station HOE "
                        "(Osnabrueck-Eversburg) 1.3 km outside NRW; this boundary "
                        "puts it 117 m inside, matching the source attribute and "
                        "reverse geocoding."
                    ),
                    "rings": len(rings),
                    "vertices": vertices,
                    "extracted_by": "scripts/fetch_nrw_boundary.py",
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
        f"wrote {args.output} | MultiPolygon, {len(geometry['coordinates'])} part(s), "
        f"{len(rings)} ring(s), {vertices:,} vertices, {size_kb:.1f} KB"
    )
    print(
        f"bbox lon {min(lons):.4f}..{max(lons):.4f} | "
        f"lat {min(lats):.4f}..{max(lats):.4f}"
    )
    print(f"licence: {LICENCE} | data status {record.get('STAND')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
