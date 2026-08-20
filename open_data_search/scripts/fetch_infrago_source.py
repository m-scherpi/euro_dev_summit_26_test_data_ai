#!/usr/bin/env python3
"""One-off provisioning: fetch the DB InfraGO infrastructure data and slice out NRW.

This is NOT part of the build pipeline. It produced
`input/db_infrago_betriebsstellen_nrw.csv` and `input/db_infrago_source.json`
once; both are committed, so nobody needs to run this again.

Why the slice is committed instead of the download URL alone: open-data portals
rot. While researching this use case, the URL that every tutorial and every
GitHub mirror still names for DB station data -
`download-data.deutschebahn.com/static/datasets/haltestellen/...` - no longer
resolves at all, and `data.deutschebahn.com` is in the middle of migrating to
the Mobilithek. A documented download command is not reproducibility if the
document outlives the host. So the NRW rows are committed verbatim, together
with a manifest that records the URL, the retrieval date and the SHA-256 of the
exact ZIP they came from. The build and verify steps then run offline, which is
also what makes them safe to demo live.

"Verbatim" is meant literally: every column of the source is kept and every
field value is written back unchanged, German decimal commas and all. Parsing
and normalisation belong to `build_stations.py`, so that the delta between
`input/` and `output/` is entirely this repository's doing and can be audited.

Source: DB InfraGO AG / Deutsche Bahn AG, "Infrastrukturdaten der DB InfraGO",
published on the Mobilithek under CC BY 4.0.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import requests

INFRAGO_ZIP_URL = (
    "https://mobilithek.info/mdp-api/files/aux/922109165921083392/Infrastrukturdaten.zip"
)
OFFER_URL = "https://mobilithek.info/offers/922109165921083392"
CSV_MEMBER = "M1 Betriebsstellen.csv"
LICENCE = "CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)"
ATTRIBUTION = "DB InfraGO AG / Deutsche Bahn AG - Infrastrukturdaten der DB InfraGO"

# The source is a Windows-style export: UTF-8 with a BOM, semicolon separated,
# and every number written with a German decimal comma.
SOURCE_ENCODING = "utf-8-sig"
SOURCE_DELIMITER = ";"

BUNDESLAND_COLUMN = "Bundesland"
DOWNLOAD_CHUNK = 1 << 16


def download(url: str, destination: Path, timeout: int) -> tuple[int, str]:
    """Stream a URL to disk. Returns (bytes written, SHA-256 hex digest)."""
    digest = hashlib.sha256()
    written = 0
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK):
                if not chunk:
                    continue
                handle.write(chunk)
                digest.update(chunk)
                written += len(chunk)
    return written, digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fetch_infrago_source.py",
        description=(
            "Download the DB InfraGO infrastructure data set from the Mobilithek, "
            "extract the Betriebsstellen CSV and commit the rows of one federal "
            "state as a read-only input fixture, alongside a manifest recording "
            "URL, licence, retrieval date and the SHA-256 of the downloaded ZIP. "
            "One-off provisioning tool - the output is committed, so this normally "
            "does not need to be run."
        ),
        epilog=(
            "Example:\n"
            "  .venv/bin/python scripts/fetch_infrago_source.py \\\n"
            "      --output-csv      input/db_infrago_betriebsstellen_nrw.csv \\\n"
            "      --output-manifest input/db_infrago_source.json\n\n"
            "Requires network access and downloads ~28 MB into build/. The build "
            "and verify steps run offline from the committed fixture."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url", default=INFRAGO_ZIP_URL, metavar="URL",
        help="ZIP to download (default: the Mobilithek InfraGO offer)",
    )
    parser.add_argument(
        "--member", default=CSV_MEMBER, metavar="NAME",
        help="CSV inside the ZIP to slice (default: %(default)s)",
    )
    parser.add_argument(
        "--bundesland", default="Nordrhein-Westfalen", metavar="NAME",
        help="value of the source's Bundesland column to keep (default: %(default)s)",
    )
    parser.add_argument(
        "--output-csv", type=Path,
        default=Path("input/db_infrago_betriebsstellen_nrw.csv"), metavar="CSV",
        help="where to write the committed source slice (default: %(default)s)",
    )
    parser.add_argument(
        "--output-manifest", type=Path,
        default=Path("input/db_infrago_source.json"), metavar="JSON",
        help="where to write the provenance manifest (default: %(default)s)",
    )
    parser.add_argument(
        "--build-dir", type=Path, default=Path("build"), metavar="DIR",
        help="disposable directory for the downloaded ZIP and the full CSV "
        "(default: %(default)s)",
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
        zip_bytes, zip_sha256 = download(args.url, archive, args.timeout)
    except Exception as exc:  # network, TLS, HTTP status - all equally fatal here
        print(f"error: download failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {archive} | {zip_bytes / 1_048_576:.1f} MB | sha256 {zip_sha256}")

    try:
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.namelist()
            if args.member not in members:
                print(
                    f"error: {args.member!r} not in the archive. Members: "
                    f"{', '.join(members)}",
                    file=sys.stderr,
                )
                return 1
            raw = bundle.read(args.member)
    except Exception as exc:  # a truncated or moved archive
        print(f"error: could not read the archive: {exc}", file=sys.stderr)
        return 1

    full_csv = args.build_dir / args.member
    full_csv.write_bytes(raw)
    print(f"extracted {full_csv} | {len(raw) / 1_048_576:.1f} MB")

    text = raw.decode(SOURCE_ENCODING)
    reader = csv.DictReader(io.StringIO(text), delimiter=SOURCE_DELIMITER)
    fieldnames = list(reader.fieldnames or [])
    if BUNDESLAND_COLUMN not in fieldnames:
        print(
            f"error: the source has no {BUNDESLAND_COLUMN!r} column. Columns: "
            f"{', '.join(fieldnames)}",
            file=sys.stderr,
        )
        return 1

    rows = list(reader)
    kept = [row for row in rows if row.get(BUNDESLAND_COLUMN) == args.bundesland]
    if not kept:
        values = sorted({row.get(BUNDESLAND_COLUMN, "") for row in rows})
        print(
            f"error: no rows with {BUNDESLAND_COLUMN}={args.bundesland!r}. "
            f"Values present: {', '.join(v or '<empty>' for v in values)}",
            file=sys.stderr,
        )
        return 1

    # Same encoding, same delimiter, same field values - only rows are dropped.
    with args.output_csv.open("w", encoding=SOURCE_ENCODING, newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames,
            delimiter=SOURCE_DELIMITER, lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(kept)

    manifest = {
        "source": ATTRIBUTION,
        "source_offer_url": OFFER_URL,
        "source_url": args.url,
        "licence": LICENCE,
        "attribution_required": True,
        "attribution": (
            f"Data source: {ATTRIBUTION}, licensed under CC BY 4.0. "
            "Modified: filtered and reprojected, see ../README.md."
        ),
        "retrieved": date.today().isoformat(),
        "zip_bytes": zip_bytes,
        "zip_sha256": zip_sha256,
        "csv_member": args.member,
        "csv_encoding": SOURCE_ENCODING,
        "csv_delimiter": SOURCE_DELIMITER,
        "decimal_separator": ",",
        "csv_rows_total": len(rows),
        "filter_applied": f"{BUNDESLAND_COLUMN} == {args.bundesland!r}",
        "rows_kept": len(kept),
        "columns": fieldnames,
        "epsg_columns": {
            4326: [
                "Geographische Länge (EPSG 4326)",
                "Geographische Breite (EPSG 4326)",
                "WKT WGS84 (EPSG 4326)",
            ],
            25832: [
                "UTM Rechtswert (EPSG 25832)",
                "UTM Hochwert (EPSG 25832)",
                "WKT UTM 32N (EPSG 25832)",
            ],
            31467: [
                "GK Rechtswert (EPSG 31467)",
                "GK Hochwert (EPSG 31467)",
                "WKT GK (EPSG 31467)",
            ],
        },
        "note": (
            "Read-only fixture. Field values are byte-identical to the source, "
            "including German decimal commas; only rows outside the filter were "
            "dropped. The full download is disposable and lives in build/."
        ),
        "extracted_by": "scripts/fetch_infrago_source.py",
    }
    args.output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    size_kb = args.output_csv.stat().st_size / 1024
    print(
        f"wrote {args.output_csv} | {len(kept):,} of {len(rows):,} rows "
        f"({args.bundesland}), {len(fieldnames)} columns, {size_kb:.1f} KB"
    )
    print(f"wrote {args.output_manifest} | licence {LICENCE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
