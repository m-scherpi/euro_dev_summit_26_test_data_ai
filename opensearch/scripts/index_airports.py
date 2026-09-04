#!/usr/bin/env python3
"""Turn a synthetic Esri JSON FeatureSet into a second OpenSearch index.

The point of this script is that the *source shape* is completely different
from `index_stations.py`'s and the *target* is identical. Same cluster, same
ArcGIS constraints, same geo_point question - a CSV of published WGS84
coordinates on one side, an Enterprise Geodatabase export on the other. If the
two indexes both open in ArcGIS Pro, the claim "the source can be anything" has
been demonstrated rather than asserted.

**What the source actually is, and why that matters.** The file was handed over
as "a GeoJSON". It is not. It is an **Esri JSON FeatureSet** - the shape an
ArcGIS REST `query?f=json` returns:

    {"geometryType": "esriGeometryPoint",
     "spatialReference": {"wkid": 102100, "latestWkid": 3857},
     "fields": [{"name": ..., "type": "esriFieldType...", "length": ...}],
     "features": [{"attributes": {...}, "geometry": {"x": ..., "y": ...}}]}

Two differences from GeoJSON, and the second one is the dangerous one:

1. Geometry is `{"x": ..., "y": ...}`, not `"coordinates": [...]`.
2. **The coordinates are metres, not degrees.** RFC 7946 GeoJSON is always
   EPSG:4326. This is EPSG:3857 - `wkid` 102100 is the deprecated Esri code for
   the same Web Mercator auxiliary sphere that `latestWkid` calls 3857. A value
   of -13055594.63 read as a longitude is nonsense; read as a longitude that
   some library silently clamps to -180, it is a point in the Pacific that
   looks like data.

So this script has to **reproject**, which is exactly what `index_stations.py`
refuses to do ("coordinates are copied, never recomputed"). CLAUDE.md section 4
is blunt about the risk: never trust an LLM with a projection formula, because
the failure mode is a systematic directional bias that survives averaging and
looks entirely plausible. Three consequences, all deliberate:

- The inverse Web Mercator below is **the only inverse in this repository**,
  hand-written here, imported from nowhere. `verify_airports.py` checks it by
  projecting the indexed degrees *forward* again with `webmercator.py` and
  comparing against the source metres. Different function, different direction,
  no shared line.
- The source `x`/`y` are carried into the index **unchanged**, as `x_3857` and
  `y_3857`. They are the provenance anchor: the verifier asserts that every
  indexed metre value exists byte-identically in the source row with the same
  `locid`. For sourced data "is this plausible?" is the wrong question.
- Degrees are **rounded to 6 decimals** before `location` is built, matching
  the rounding the fixture applied before it projected. Round before
  projecting, or every row disagrees with itself by the rounding step.

**Field naming.** The Esri documentation for query layers over document
databases was checked for reserved field names and does not name any: it
states only that "All features in the map must have a unique identifier" with
`_id` as the default, and offers "an integer field that contains unique
values" as an alternative. So `source_objectid` is not a workaround for a
documented conflict - it is a rename for a documented *lie*. The source's
`objectid` is not the object id: it and `ESRI_OID` are both 1..N, both unique,
and equal in zero rows, while ArcGIS builds its own Object ID from `_id`. Three
things called an ID, none of them the one ArcGIS uses. Prefixing the two that
came from the source keeps that visible in the attribute table.

`--dry-run` writes the mapping and the bulk payload to `output/` without
touching a server, so the committed artifacts are reproducible from `input/`
plus one command even with no cluster running.

Stdlib only. Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from geopoint import GEO_FORMATS, format_location  # noqa: E402
from osclient import (  # noqa: E402  (path shim has to come first)
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_USER,
    OpenSearchClient,
    OpenSearchError,
)

# What the reader insists on finding. A FeatureSet that says something else is
# an error, never a conversion: silently accepting another wkid is how metres
# become degrees.
EXPECTED_GEOMETRY_TYPE = "esriGeometryPoint"
ACCEPTED_WKIDS = (102100, 3857)  # the same Web Mercator, old and current code

# Attribute names the source uses, and what they become in the index. Renames
# are deliberate and few; everything else keeps the source's name so the two
# can be compared without a lookup table.
FIELD_RENAMES = {
    "objectid": "source_objectid",
    "ESRI_OID": "source_esri_oid",
    "globalid": "source_globalid",
    "type": "airport_type",
}

SOURCE_ATTRIBUTES = [
    "objectid",
    "locid",
    "name",
    "field",
    "state",
    "state_fips",
    "acais",
    "tot_enp",
    "type",
    "globalid",
    "ESRI_OID",
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
            "airport_oid": {"type": "integer"},        # ArcGIS: Long Integer
            "locid": {"type": "keyword"},              # ArcGIS: Text
            "name": {                                  # ArcGIS: Text
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "field": {"type": "keyword"},              # ArcGIS: Text
            "state": {"type": "keyword"},              # ArcGIS: Text
            # keyword, never numeric: 289 of 880 FIPS codes start with a zero,
            # and "06" parsed as an integer is California turning into 6.
            "state_fips": {"type": "keyword"},         # ArcGIS: Text
            "acais": {"type": "keyword"},              # ArcGIS: Text
            "airport_type": {"type": "keyword"},       # ArcGIS: Text
            # esriFieldTypeDouble in the source schema, and every value is
            # integral. The source's declared type wins over what the values
            # happen to look like.
            "tot_enp": {"type": "double"},             # ArcGIS: Double
            "source_objectid": {"type": "integer"},    # ArcGIS: Long Integer
            "source_esri_oid": {"type": "integer"},    # ArcGIS: Long Integer
            "source_globalid": {"type": "keyword"},    # ArcGIS: Text
            "latitude": {"type": "double"},            # ArcGIS: Double
            "longitude": {"type": "double"},           # ArcGIS: Double
            "location": {"type": "geo_point"},         # ArcGIS: Geometry
            "x_3857": {"type": "double"},              # ArcGIS: Double
            "y_3857": {"type": "double"},              # ArcGIS: Double
        },
    },
}

# WGS 84 semi-major axis, used as a sphere radius - that is what makes
# EPSG:3857 the "auxiliary sphere" variant.
EPSG_3857_RADIUS_M = 6378137.0

# Degrees kept in the document. Six decimals is ~11 cm at the equator, well
# below any positional accuracy a geodatabase export carries, and it is the
# precision the fixture rounded to before projecting.
COORDINATE_DECIMALS = 6


def from_web_mercator(x: float, y: float) -> tuple[float, float]:
    """Inverse spherical Web Mercator: EPSG:3857 metres -> EPSG:4326 degrees.

    Hand-written here and imported from nowhere. `webmercator.py` holds the
    forward direction and is the module the verifier uses, so the check on this
    function comes from separate code running the other way (CLAUDE.md section
    4: a verifier must not share its projection implementation with the
    generator it checks).

    The latitude term is written as `2*atan(exp(y/R)) - pi/2`. The equivalent
    `asin(tanh(y/R))` would be a second form of the same thing - useful as a
    fallback, but agreement between two of your own lines is weaker evidence
    than agreement with the inverse operation.

    Returns (longitude, latitude), longitude first, matching the argument order
    of the forward function and the array form of a geo_point.
    """
    longitude = math.degrees(x / EPSG_3857_RADIUS_M)
    latitude = math.degrees(
        2.0 * math.atan(math.exp(y / EPSG_3857_RADIUS_M)) - math.pi / 2.0
    )
    return longitude, latitude


def read_featureset(path: Path) -> list[dict]:
    """Read the Esri JSON FeatureSet and refuse anything unexpected.

    Every check here aborts rather than adapts. A FeatureSet in another CRS is
    not a FeatureSet this script can reproject - the numbers would still be
    metres, just of a different grid, and the result would be plausible and
    wrong.
    """
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)

    geometry_type = document.get("geometryType")
    if geometry_type != EXPECTED_GEOMETRY_TYPE:
        raise SystemExit(
            f"error: {path} has geometryType {geometry_type!r}, expected "
            f"{EXPECTED_GEOMETRY_TYPE!r}. Only point features are handled here"
        )

    reference = document.get("spatialReference") or {}
    wkid = reference.get("latestWkid") or reference.get("wkid")
    if wkid not in ACCEPTED_WKIDS:
        raise SystemExit(
            f"error: {path} declares spatialReference {reference!r}. This script "
            f"only converts EPSG:3857 (wkid {' or '.join(map(str, ACCEPTED_WKIDS))}) "
            "and will not guess at another CRS"
        )

    names = {field["name"] for field in document.get("fields", [])}
    missing = [name for name in SOURCE_ATTRIBUTES if name not in names]
    if missing:
        raise SystemExit(
            f"error: {path} is missing expected field(s): {', '.join(missing)}"
        )

    features = document.get("features") or []
    if not features:
        raise SystemExit(f"error: {path} contains no features")
    return features


def build_documents(
    features: list[dict], index: str, geo_format: str
) -> list[tuple[dict, dict]]:
    """Turn FeatureSet entries into (bulk action, document) pairs.

    The document `_id` is `locid`, the source's own business key: unique across
    all features, stable, and the only one of the three identifier-looking
    columns that means anything. Re-running the load therefore overwrites
    instead of duplicating, and ArcGIS - which uses the system `_id` as its
    Object ID - gets a stable identifier.
    """
    documents: list[tuple[dict, dict]] = []
    for position, feature in enumerate(features, start=1):
        attributes = feature["attributes"]
        geometry = feature.get("geometry") or {}
        if "x" not in geometry or "y" not in geometry:
            raise SystemExit(
                f"error: feature {attributes.get('locid', position)!r} has no "
                "x/y geometry"
            )
        x = float(geometry["x"])
        y = float(geometry["y"])
        longitude, latitude = from_web_mercator(x, y)
        latitude = round(latitude, COORDINATE_DECIMALS)
        longitude = round(longitude, COORDINATE_DECIMALS)

        document = {
            # An integer alternative to the string `_id`, for the "an integer
            # field that contains unique values" option in the ArcGIS query
            # layer dialog. Note this is a third integer id, and the only one
            # of the three that is guaranteed to line up with document order.
            "airport_oid": position,
            "latitude": latitude,
            "longitude": longitude,
            "location": format_location(latitude, longitude, geo_format),
            # Carried through untouched. Everything above is derived from these
            # two numbers; these two are the source's own.
            "x_3857": x,
            "y_3857": y,
        }
        for source_name in SOURCE_ATTRIBUTES:
            target = FIELD_RENAMES.get(source_name, source_name)
            document[target] = attributes[source_name]

        action = {"index": {"_index": index, "_id": attributes["locid"]}}
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
        prog="index_airports.py",
        description=(
            "Reshape a synthetic Esri JSON point FeatureSet into OpenSearch "
            "documents, write the index mapping and the bulk payload to output/, "
            "and load them into a running cluster. The source carries its "
            "geometry as {x, y} in EPSG:3857 metres, so this indexer reprojects "
            "to EPSG:4326 - the source metres are kept verbatim as the "
            "provenance anchor and verify_airports.py recomputes the "
            "transformation with independent code."
        ),
        epilog=(
            "Examples:\n"
            "  # write output/ artifacts only, no server needed\n"
            "  python3 scripts/index_airports.py --dry-run\n\n"
            "  # create and fill the index on a local TLS cluster\n"
            "  python3 scripts/index_airports.py --recreate \\\n"
            "      --host https://localhost:9200 \\\n"
            "      --ca-cert build/tls/root-ca.pem\n\n"
            "  # cluster started with --insecure (security plugin off)\n"
            "  python3 scripts/index_airports.py --recreate \\\n"
            "      --host http://localhost:9200 --no-auth\n\n"
            "Verify the result with scripts/verify_airports.py. The fixture is "
            "rebuilt by scripts/make_airports_fixture.py, which normally never "
            "needs to run."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("input/synthetic_airports.json"),
        metavar="JSON",
        help="Esri JSON FeatureSet to index. Read, never written "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--index",
        default="synthetic_airports",
        metavar="NAME",
        help="OpenSearch index name; also names the output artifacts. The name "
        "says the data is synthetic, because the ArcGIS layer inherits it "
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
        "--swap-axes",
        action="store_true",
        help="write latitude and longitude the wrong way round. For proving the "
        "verifier actually fails - a check that never goes red is not a check. "
        "Never use for real output",
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
        print(f"error: input FeatureSet not found: {args.input}", file=sys.stderr)
        print(
            "hint: run this from inside the opensearch/ folder, or pass --input. "
            "The fixture is committed; rebuild it with "
            "scripts/make_airports_fixture.py only if it is missing",
            file=sys.stderr,
        )
        return 2

    features = read_featureset(args.input)
    print(
        f"read {args.input} | {len(features):,} features, "
        f"esriGeometryPoint in EPSG:3857 metres"
    )

    documents = build_documents(features, args.index, args.geo_format)

    if args.swap_axes:
        print(
            "warning: --swap-axes is on. The geometry is deliberately wrong; "
            "this exists to prove verify_airports.py fails",
            file=sys.stderr,
        )
        for _action, document in documents:
            document["location"] = format_location(
                document["longitude"], document["latitude"], args.geo_format
            )

    sample = documents[0][1]
    print(
        f"geo_point format {args.geo_format!r} | first value: "
        f"{json.dumps(sample['location'])}"
    )
    print(
        f"reprojected {sample['x_3857']:.4f}, {sample['y_3857']:.4f} m -> "
        f"{sample['latitude']}, {sample['longitude']} deg "
        f"({sample['locid']}, {sample['state']})"
    )

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
    print(f"wrote {bulk_path} | {len(documents):,} docs, {len(ndjson) / 1024:.1f} KB")

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

    print("done. Verify with scripts/verify_airports.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
