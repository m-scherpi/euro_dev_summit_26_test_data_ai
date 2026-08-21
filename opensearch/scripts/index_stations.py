#!/usr/bin/env python3
"""Turn the NRW railway station CSV into an OpenSearch index ArcGIS can read.

The data is not touched. Every coordinate written here is a value DB InfraGO
published, carried through `open_data_search/output/nrw_stations.csv` unchanged;
this script only reshapes rows into documents. What makes the use case
interesting is that the target is not OpenSearch in general but OpenSearch *as
seen by ArcGIS Pro 3.7 / ArcGIS Enterprise 12.1*, and that client is much
pickier than the search engine:

1. **The obvious geo_point format is the one that does not work.** Esri's own
   documentation says it plainly: "The geopoint format that uses an object with
   a latitude and longitude is not supported with ArcGIS." That is
   `{"lat": ..., "lon": ...}` - the form in every OpenSearch tutorial, the form
   an LLM writes unprompted, and the form OpenSearch itself documents first.
   It indexes fine, it answers geo queries fine, and ArcGIS will not read it.
   What remains: an array, a string, or WKT.

2. **The remaining three formats disagree about axis order.** Array is
   `[longitude, latitude]` (GeoJSON order, RFC 7946), string is
   `"latitude,longitude"`, WKT is `POINT (longitude latitude)`. Two out of
   three put longitude first, the odd one out is the one that reads most like
   prose. Hard-coding either order without a check is how stations end up in
   the Indian Ocean, so `--geo-format` is a real switch and
   `verify_index.py` re-derives the expected order per format from scratch.

3. **`latitude`/`longitude` stay in the document as plain doubles.** ArcGIS
   builds its geometry from `location` alone, so the two numeric columns are
   redundant for drawing - and that is exactly why they are kept: they are what
   the verifier compares the indexed geometry against.

4. **The mapping is explicit and `dynamic: strict`.** A search engine will
   happily invent a field type from the first document it sees; ArcGIS then
   inherits whatever guess that was. Declaring the mapping up front makes the
   ArcGIS-side field types a decision instead of an accident, and `strict`
   turns a typo into an error rather than a new field.

`--dry-run` writes the mapping and the bulk payload to `output/` without
touching a server, so the committed artifacts are reproducible from `input/`
plus one command even with no cluster running.

Stdlib only. Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from osclient import (  # noqa: E402  (path shim has to come first)
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_USER,
    OpenSearchClient,
    OpenSearchError,
)

# Column names of the source CSV, in source order.
SOURCE_COLUMNS = [
    "ds100",
    "name",
    "district",
    "latitude",
    "longitude",
    "x_3857",
    "y_3857",
    "source_rows",
    "position_spread_m",
]

# The index mapping, written as data so it can be dumped to output/ verbatim.
# The ArcGIS type each field turns into is in the comment - see
# https://doc.esri.com/en/arcgis-pro/latest/help/data/databases/dbms-data-types-supported.html
INDEX_MAPPING = {
    "settings": {
        "index": {
            # Single node: one shard, and zero replicas so cluster health is
            # green rather than yellow. A yellow cluster works but looks broken
            # on a slide.
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "dynamic": "strict",
        "properties": {
            "station_oid": {"type": "integer"},        # ArcGIS: Long Integer
            "ds100": {"type": "keyword"},              # ArcGIS: Text
            "name": {                                  # ArcGIS: Text
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "district": {"type": "keyword"},           # ArcGIS: Text
            "latitude": {"type": "double"},            # ArcGIS: Double
            "longitude": {"type": "double"},           # ArcGIS: Double
            "location": {"type": "geo_point"},         # ArcGIS: Geometry
            "x_3857": {"type": "double"},              # ArcGIS: Double
            "y_3857": {"type": "double"},              # ArcGIS: Double
            "source_rows": {"type": "integer"},        # ArcGIS: Long Integer
            "position_spread_m": {"type": "double"},   # ArcGIS: Double
        },
    },
}

GEO_FORMATS = ("array", "string", "wkt")


def format_location(latitude: float, longitude: float, geo_format: str):
    """Build the geo_point value in one of the three ArcGIS-readable formats.

    The object form `{"lat": ..., "lon": ...}` is intentionally not offered:
    OpenSearch accepts it, ArcGIS does not.
    """
    if geo_format == "array":
        return [longitude, latitude]           # GeoJSON order: lon, lat
    if geo_format == "string":
        return f"{latitude},{longitude}"       # OpenSearch string order: lat, lon
    if geo_format == "wkt":
        return f"POINT ({longitude} {latitude})"
    raise ValueError(f"unknown geo format: {geo_format!r}")


def read_stations(path: Path) -> list[dict[str, str]]:
    """Read the source CSV and check that its header is what we expect."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in SOURCE_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"error: {path} is missing expected column(s): {', '.join(missing)}"
            )
        return list(reader)


def build_documents(
    rows: list[dict[str, str]], index: str, geo_format: str
) -> list[tuple[dict, dict]]:
    """Turn CSV rows into (bulk action, document) pairs.

    The document `_id` is the DS100 code: it is the source's own identity key,
    so re-running the load overwrites instead of duplicating, and ArcGIS - which
    uses the system `_id` as its Object ID - gets a stable identifier.
    """
    documents: list[tuple[dict, dict]] = []
    for position, row in enumerate(rows, start=1):
        latitude = float(row["latitude"])
        longitude = float(row["longitude"])
        document = {
            # An integer alternative to the string `_id`, for the "an integer
            # field that contains unique values" option in the ArcGIS query
            # layer dialog.
            "station_oid": position,
            "ds100": row["ds100"],
            "name": row["name"],
            "district": row["district"],
            "latitude": latitude,
            "longitude": longitude,
            "location": format_location(latitude, longitude, geo_format),
            "x_3857": float(row["x_3857"]),
            "y_3857": float(row["y_3857"]),
            "source_rows": int(row["source_rows"]),
            "position_spread_m": float(row["position_spread_m"]),
        }
        action = {"index": {"_index": index, "_id": row["ds100"]}}
        documents.append((action, document))
    return documents


def render_ndjson(documents: list[tuple[dict, dict]]) -> str:
    """Render the bulk payload: one action line and one source line per document."""
    lines: list[str] = []
    for action, document in documents:
        lines.append(json.dumps(action, ensure_ascii=False, sort_keys=True))
        lines.append(json.dumps(document, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def chunked(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="index_stations.py",
        description=(
            "Reshape the NRW railway station CSV into OpenSearch documents, write "
            "the index mapping and the bulk payload to output/, and load them into "
            "a running cluster. The mapping is explicit and the geo_point format is "
            "selectable, because the format ArcGIS cannot read is the one everything "
            "else suggests. Coordinates are copied, never recomputed."
        ),
        epilog=(
            "Examples:\n"
            "  # write output/ artifacts only, no server needed\n"
            "  python3 scripts/index_stations.py --dry-run\n\n"
            "  # create and fill the index on a local TLS cluster\n"
            "  python3 scripts/index_stations.py --recreate \\\n"
            "      --host https://localhost:9200 \\\n"
            "      --ca-cert build/tls/root-ca.pem\n\n"
            "  # cluster started with --insecure (security plugin off)\n"
            "  python3 scripts/index_stations.py --recreate \\\n"
            "      --host http://localhost:9200 --no-auth\n\n"
            "Verify the result with scripts/verify_index.py."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("../open_data_search/output/nrw_stations.csv"),
        metavar="CSV",
        help="station CSV produced by the open_data_search use case. Read, never "
        "written (default: %(default)s)",
    )
    parser.add_argument(
        "--index",
        default="nrw_stations",
        metavar="NAME",
        help="OpenSearch index name; also names the output artifacts "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        metavar="DIR",
        help="where to write the mapping and bulk payload (default: %(default)s)",
    )
    parser.add_argument(
        "--geo-format",
        choices=GEO_FORMATS,
        default="array",
        metavar="FORMAT",
        help="how to write the geo_point value: array = [longitude, latitude], "
        "string = 'latitude,longitude', wkt = 'POINT (longitude latitude)'. Note "
        "the axis order differs between them. The object form {lat, lon} is not "
        "offered because ArcGIS does not support it. Choices: "
        f"{', '.join(GEO_FORMATS)} (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write the output/ artifacts and stop; no cluster is contacted",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="delete the index first if it exists. Required to change the mapping "
        "of an existing index - no default, because it destroys data",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        metavar="URL",
        help="cluster URL including scheme and port (default: %(default)s)",
    )
    parser.add_argument(
        "--user",
        default=DEFAULT_USER,
        metavar="NAME",
        help="basic auth user - the only authentication ArcGIS supports "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        default=None,
        metavar="PASSWORD",
        help="basic auth password. Defaults to the committed demo password of the "
        "local test cluster, or to $OPENSEARCH_PASSWORD if that is set",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="send no Authorization header, for a cluster started with --insecure",
    )
    parser.add_argument(
        "--ca-cert",
        type=Path,
        default=None,
        metavar="PEM",
        help="CA certificate that signed the cluster's HTTPS certificate, usually "
        "build/tls/root-ca.pem after setup_opensearch.sh",
    )
    parser.add_argument(
        "--insecure-tls",
        action="store_true",
        help="skip TLS certificate verification. For debugging a certificate "
        "problem, not for hiding one",
    )
    parser.add_argument(
        "--bulk-size",
        type=int,
        default=200,
        metavar="N",
        help="documents per bulk request (default: %(default)s)",
    )
    return parser


def resolve_password(args: argparse.Namespace) -> str:
    import os

    if args.password is not None:
        return args.password
    return os.environ.get("OPENSEARCH_PASSWORD", DEFAULT_PASSWORD)


def main() -> int:
    args = build_parser().parse_args()

    if not args.input.exists():
        print(f"error: input CSV not found: {args.input}", file=sys.stderr)
        print(
            "hint: run this from inside the opensearch/ folder, or pass --input",
            file=sys.stderr,
        )
        return 2

    rows = read_stations(args.input)
    print(f"read {args.input} | {len(rows):,} stations")

    documents = build_documents(rows, args.index, args.geo_format)
    sample = documents[0][1]["location"]
    print(f"geo_point format {args.geo_format!r} | first value: {json.dumps(sample)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    mapping_path = args.output_dir / f"{args.index}_mapping.json"
    bulk_path = args.output_dir / f"{args.index}_bulk.ndjson"

    mapping_text = json.dumps(INDEX_MAPPING, indent=2, ensure_ascii=False) + "\n"
    mapping_path.write_text(mapping_text, encoding="utf-8")
    print(
        f"wrote {mapping_path} | {len(INDEX_MAPPING['mappings']['properties'])} fields, "
        f"{len(mapping_text) / 1024:.1f} KB"
    )

    ndjson = render_ndjson(documents)
    bulk_path.write_text(ndjson, encoding="utf-8")
    print(
        f"wrote {bulk_path} | {len(documents):,} docs, {len(ndjson) / 1024:.1f} KB"
    )

    if args.dry_run:
        print("dry run: no cluster contacted")
        return 0

    client = OpenSearchClient(
        host=args.host,
        user=None if args.no_auth else args.user,
        password=None if args.no_auth else resolve_password(args),
        ca_cert=str(args.ca_cert) if args.ca_cert else None,
        verify_tls=not args.insecure_tls,
    )

    try:
        info = client.info()
        print(
            f"connected to {args.host} | "
            f"{info.get('version', {}).get('distribution', 'opensearch')} "
            f"{info.get('version', {}).get('number', '?')}"
        )

        if client.index_exists(args.index):
            if not args.recreate:
                print(
                    f"error: index {args.index!r} already exists. Pass --recreate to "
                    "drop and rebuild it",
                    file=sys.stderr,
                )
                return 3
            client.delete_index(args.index)
            print(f"deleted existing index {args.index!r}")

        client.create_index(args.index, INDEX_MAPPING)
        print(f"created index {args.index!r} with an explicit, strict mapping")

        loaded = 0
        for batch in chunked(documents, args.bulk_size):
            response = client.bulk(render_ndjson(batch))
            if response.get("errors"):
                failures = [
                    item["index"]
                    for item in response.get("items", [])
                    if item.get("index", {}).get("error")
                ]
                print(
                    f"error: bulk request reported {len(failures)} failure(s); "
                    f"first: {json.dumps(failures[0], ensure_ascii=False)[:500]}",
                    file=sys.stderr,
                )
                return 4
            loaded += len(batch)
            print(f"bulk loaded {loaded:,}/{len(documents):,}")

        client.refresh(args.index)
        count = client.count(args.index)
        print(f"index {args.index!r} holds {count:,} documents")
        if count != len(documents):
            print(
                f"error: expected {len(documents):,} documents, found {count:,}",
                file=sys.stderr,
            )
            return 5
    except OpenSearchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 6

    print("done. Verify with scripts/verify_index.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
