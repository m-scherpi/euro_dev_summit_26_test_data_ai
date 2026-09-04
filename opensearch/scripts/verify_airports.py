#!/usr/bin/env python3
"""Verify the reprojected airport index against its source and against ArcGIS.

The sibling `verify_index.py` checks an index built from published WGS84
coordinates, where the strongest possible claim is "nothing was recomputed".
Here something *was* recomputed - the source carries EPSG:3857 metres and the
index carries EPSG:4326 degrees - so the provenance question changes shape and
two new checks have to carry the weight:

**1. The transformation is recomputed by independent code, backwards.**
`index_airports.py` writes the inverse Web Mercator by hand. This script does
not check that inverse against a second inverse; it takes the degrees that came
out of the index, projects them *forward* with `webmercator.py`, and compares
against the source metres. Different function, opposite direction, no shared
line. CLAUDE.md section 4: never trust an LLM with a projection formula,
because the failure mode is a systematic directional bias that survives
averaging, spot-checks and eyeballing, and looks entirely plausible in a table.

**2. Provenance moves from the coordinate to the source coordinate.**
`x_3857`/`y_3857` in every document must be bit-identical to the fixture row
with the same `locid`. The derived degrees are covered by (1). Together the two
say: nothing was invented, and the one thing that was computed is reproducible
from outside this pipeline. A single metre value quietly changed to a plausible
spot passes the bounding box, the axis test and the geo query; only this
catches it.

Everything on the reference side of this script - region boxes, the dateline
count, the expected geo_distance set - is derived from the fixture's own metres
using the **forward** projection only. The inverse formula under test therefore
appears nowhere in the reference computation, not even indirectly.

The rest of the checklist is `verify_index.py`'s, and it earns its place again
for a different data set:

- **Field types against the ArcGIS table**, `dynamic: strict`, and `location`
  declared `geo_point`.
- **The geo_point is not the object format.** Esri: "The geopoint format that
  uses an object with a latitude and longitude is not supported with ArcGIS."
  The index looks perfect and the layer will not open.
- **Axis order refereed by the search engine.** The union of the regional boxes
  must match every document and its transpose must match none. Measured here:
  the transpose matches zero, and it does so because no airport happens to sit
  at longitude -14..71 - luck, and worth stating as luck.
- **A bounding box that spans the antimeridian**, because this data set does.
  The naive envelope of the whole set is 344 degrees wide: it passes, and it
  proves nothing. Reported as INFO next to the regional boxes that do.
- **geo_distance against an independent haversine.**
- **The SQL plugin**, reported and never enforced.

Plus three INFO findings this source produces and the station data did not:
attribute-versus-geometry disagreement, a FIPS code with two state names, and
"empty" values that are a single space.

Reads the fixture and the cluster; writes only the report. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from arcgis_checks import (  # noqa: E402
    ARCGIS_TYPE_OF,
    Check,
    decode_location,
    flatten_properties,
    haversine_m,
    render_check_table,
)
from osclient import (  # noqa: E402  (path shim has to come first)
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_USER,
    OpenSearchClient,
    OpenSearchError,
)
from webmercator import to_web_mercator  # noqa: E402

# How far the forward reprojection of an indexed coordinate may sit from the
# source metres.
#
# The fixture stores its metres rounded to four decimals, because storing the
# raw double made the file unreproducible across platforms (libm differs in the
# last bit; see METRE_DECIMALS in make_airports_fixture.py). So the round trip
# cannot close at zero any more: it closes at **half a rounding step, 0.05 mm**,
# which is exactly what it measures. One millimetre leaves a factor of 20 for
# that plus headroom for a real export rounded differently - measured on the
# original geodatabase export, whose metres were not derived from rounded
# degrees, the same trip closed to 0.2 mm.
#
# The tolerance is deliberately not tightened to 0.06 mm. A check calibrated to
# the current artifact's exact rounding would fail on the next source for a
# reason that is not an error.
REPROJECTION_TOLERANCE_M = 0.001

# The longitude at which the dateline-spanning box starts and ends. A box with
# top_left.lon > bottom_right.lon is how OpenSearch is told to wrap.
DATELINE_LON = 160.0

# Fields that carry a single space instead of NULL in the source. Counted, not
# corrected: the space is what the geodatabase stores.
BLANK_CANDIDATE_FIELDS = ("field", "airport_type", "acais")
BLANK = " "


# US postal abbreviation -> FIPS state code. A US government standard in the
# public domain, transcribed here rather than derived: "HI" is not the first
# two letters of "Hawaii" and no rule turns one into the other, so guessing the
# expansion from the name is exactly the mistake this check exists to catch.
#
# The check it enables: a two-letter `state` value whose postal code names a
# *different* FIPS code than the row's own `state_fips` is not an abbreviation,
# it is wrong. That separates the two cases this source mixes - one value is
# merely abbreviated where the rest are spelled out, the other points at the
# wrong place entirely.
POSTAL_TO_FIPS = {
    "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06", "CO": "08",
    "CT": "09", "DE": "10", "DC": "11", "FL": "12", "GA": "13", "HI": "15",
    "ID": "16", "IL": "17", "IN": "18", "IA": "19", "KS": "20", "KY": "21",
    "LA": "22", "ME": "23", "MD": "24", "MA": "25", "MI": "26", "MN": "27",
    "MS": "28", "MO": "29", "MT": "30", "NE": "31", "NV": "32", "NH": "33",
    "NJ": "34", "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
    "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VT": "50", "VA": "51", "WA": "53",
    "WV": "54", "WI": "55", "WY": "56", "AS": "60", "GU": "66", "MP": "69",
    "PR": "72", "UM": "74", "VI": "78",
}

def load_fixture(path: Path) -> dict[str, dict]:
    """Read the Esri JSON FeatureSet, keyed by its business key.

    Returns `{locid: {"x": float, "y": float, "attributes": {...}}}`. The x/y
    are the source's own numbers and are compared bit-for-bit later, so they
    are not rounded, scaled or otherwise touched on the way in.
    """
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    features: dict[str, dict] = {}
    for feature in document.get("features", []):
        attributes = feature["attributes"]
        geometry = feature["geometry"]
        features[attributes["locid"]] = {
            "x": float(geometry["x"]),
            "y": float(geometry["y"]),
            "attributes": attributes,
        }
    return features


def load_manifest(path: Path) -> dict:
    """Read the fixture manifest for the region boxes and the state mapping."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def box_in_metres(box) -> tuple[float, float, float, float]:
    """Project a (lat_min, lat_max, lon_min, lon_max) box to metre bounds.

    Web Mercator is monotonic in both axes, so a containment test in metres is
    equivalent to one in degrees - and doing it this way keeps the inverse
    formula, the thing actually under test, out of the reference computation
    entirely.
    """
    lat_min, lat_max, lon_min, lon_max = box
    x_min, y_min = to_web_mercator(lon_min, lat_min)
    x_max, y_max = to_web_mercator(lon_max, lat_max)
    return x_min, x_max, y_min, y_max


def bounding_box_query(box) -> dict:
    """A geo_bounding_box clause for a (lat_min, lat_max, lon_min, lon_max) box."""
    lat_min, lat_max, lon_min, lon_max = box
    return {
        "geo_bounding_box": {
            "location": {
                "top_left": {"lat": lat_max, "lon": lon_min},
                "bottom_right": {"lat": lat_min, "lon": lon_max},
            }
        }
    }


def any_of(clauses: list[dict]) -> dict:
    """Union of geo clauses, as a bool query with minimum_should_match 1."""
    return {"bool": {"should": clauses, "minimum_should_match": 1}}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_airports.py",
        description=(
            "Verify the synthetic airport index against the Esri JSON fixture "
            "and against what ArcGIS Pro requires: document count, "
            "ArcGIS-compatible field types, a geo_point format ArcGIS can read, "
            "axis order refereed by the search engine, the EPSG:3857 -> EPSG:4326 "
            "transformation recomputed by independent code in the opposite "
            "direction, coordinate provenance against the source metres, a "
            "bounding box that spans the antimeridian, and a geo_distance query "
            "cross-checked with an independent haversine. Writes a Markdown "
            "report and exits non-zero on any failure."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/verify_airports.py \\\n"
            "      --host https://localhost:9200 \\\n"
            "      --ca-cert build/tls/root-ca.pem \\\n"
            "      --report output/synthetic_airports_verification_report.md\n\n"
            "The --report path has no default on purpose: a verifier that writes "
            "somewhere by default eventually overwrites the wrong report."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        metavar="MD",
        help="where to write the Markdown report (required, no default)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("input/synthetic_airports.json"),
        metavar="JSON",
        help="Esri JSON FeatureSet the index was built from (default: %(default)s)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("input/synthetic_airports_source.json"),
        metavar="JSON",
        help="fixture manifest holding the region boxes and the state-to-region "
        "mapping (default: %(default)s)",
    )
    parser.add_argument(
        "--index",
        default="synthetic_airports",
        metavar="NAME",
        help="index to verify (default: %(default)s)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=0,
        metavar="N",
        help="documents to check for reprojection and provenance; 0 checks all "
        "of them, which is the default here because the reprojection is the "
        "point of this index and a sample would only fail probably "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--distance-center",
        default=None,
        metavar="LOCID",
        help="locid the geo_distance query is centred on (default: the busiest "
        "airport in the fixture, by tot_enp)",
    )
    parser.add_argument(
        "--distance-km",
        type=float,
        default=300.0,
        metavar="KM",
        help="radius of the geo_distance query. Larger than the station "
        "verifier's 30 km because this data set is continental "
        "(default: %(default)s)",
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
        help="basic auth user (default: %(default)s)",
    )
    parser.add_argument(
        "--password",
        default=None,
        metavar="PASSWORD",
        help="basic auth password; defaults to the committed demo password or to "
        "$OPENSEARCH_PASSWORD",
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
        help="CA certificate of the cluster, usually build/tls/root-ca.pem",
    )
    parser.add_argument(
        "--insecure-tls",
        action="store_true",
        help="skip TLS certificate verification",
    )
    return parser


def resolve_password(args: argparse.Namespace) -> str:
    import os

    if args.password is not None:
        return args.password
    return os.environ.get("OPENSEARCH_PASSWORD", DEFAULT_PASSWORD)


def main() -> int:  # noqa: C901  (a checklist is a checklist)
    args = build_parser().parse_args()

    for path, label in ((args.input, "fixture"), (args.manifest, "manifest")):
        if not path.exists():
            print(f"error: {label} not found: {path}", file=sys.stderr)
            return 2

    fixture = load_fixture(args.input)
    manifest = load_manifest(args.manifest)
    region_boxes = manifest["region_boxes"]
    state_regions = manifest["state_regions"]
    print(f"read {args.input} | {len(fixture):,} features")
    print(f"read {args.manifest} | {len(region_boxes)} region boxes")

    client = OpenSearchClient(
        host=args.host,
        user=None if args.no_auth else args.user,
        password=None if args.no_auth else resolve_password(args),
        ca_cert=str(args.ca_cert) if args.ca_cert else None,
        verify_tls=not args.insecure_tls,
    )

    checks: list[Check] = []
    field_table: list[tuple[str, str, str]] = []
    distance_table: list[tuple[str, str, float, float]] = []
    region_table: list[tuple[str, int, int]] = []
    reprojection_worst = 0.0

    try:
        info = client.info()
        version = info.get("version", {}).get("number", "?")
        print(f"connected to {args.host} | OpenSearch {version}")

        # -- 1. document count ------------------------------------------------
        count = client.count(args.index)
        checks.append(
            Check(
                "Document count matches the source FeatureSet",
                count == len(fixture),
                f"{count:,} documents, {len(fixture):,} features",
            )
        )
        print(f"documents in index: {count:,}")

        # -- 2. field types against the ArcGIS table --------------------------
        mapping = client.get_mapping(args.index)[args.index]["mappings"]
        flat = flatten_properties(mapping.get("properties", {}))
        unsupported = []
        for field, field_type in sorted(flat.items()):
            arcgis_type = ARCGIS_TYPE_OF.get(field_type)
            field_table.append((field, field_type, arcgis_type or "**unsupported**"))
            if arcgis_type is None:
                unsupported.append(f"{field} ({field_type})")
        checks.append(
            Check(
                "Every field type maps to an ArcGIS type",
                not unsupported,
                f"{len(flat)} fields, {len(unsupported)} unsupported"
                + (f": {', '.join(unsupported)}" if unsupported else ""),
            )
        )
        checks.append(
            Check(
                "`location` is a geo_point (ArcGIS: Geometry)",
                flat.get("location") == "geo_point",
                f"declared as {flat.get('location', 'missing')!r}",
            )
        )
        checks.append(
            Check(
                "Mapping is `dynamic: strict` (no schema drift after publishing)",
                mapping.get("dynamic") == "strict",
                f"dynamic = {mapping.get('dynamic', 'true (default)')!r}",
            )
        )

        # -- 3./5. format, reprojection and provenance ------------------------
        size = len(fixture) if args.sample_size == 0 else args.sample_size
        hits = client.search(
            args.index,
            {"size": size, "query": {"match_all": {}}, "sort": [{"locid": "asc"}]},
        )["hits"]["hits"]

        object_format: list[str] = []
        decode_errors: list[str] = []
        internal_mismatch: list[str] = []
        reprojection_off: list[str] = []
        provenance_mismatch: list[str] = []
        attribute_conflicts: list[str] = []
        blank_counts = dict.fromkeys(BLANK_CANDIDATE_FIELDS, 0)

        for hit in hits:
            source = hit["_source"]
            locid = source["locid"]
            raw = source.get("location")
            if isinstance(raw, dict):
                object_format.append(locid)
                continue
            try:
                latitude, longitude = decode_location(raw)
            except ValueError as exc:
                decode_errors.append(f"{locid}: {exc}")
                continue

            # the geometry against the document's own numeric columns
            if (round(latitude, 6), round(longitude, 6)) != (
                round(float(source["latitude"]), 6),
                round(float(source["longitude"]), 6),
            ):
                internal_mismatch.append(locid)

            row = fixture.get(locid)
            if row is None:
                provenance_mismatch.append(f"{locid}: not in the FeatureSet at all")
                continue

            # Provenance: the source metres, bit-identical. Not "close to" -
            # these are the same double that came out of the file.
            if (source["x_3857"], source["y_3857"]) != (row["x"], row["y"]):
                provenance_mismatch.append(
                    f"{locid}: index {source['x_3857']}/{source['y_3857']} vs "
                    f"source {row['x']}/{row['y']}"
                )

            # The transformation, recomputed forward by independent code.
            x, y = to_web_mercator(longitude, latitude)
            offset = max(abs(x - row["x"]), abs(y - row["y"]))
            reprojection_worst = max(reprojection_worst, offset)
            if offset > REPROJECTION_TOLERANCE_M:
                reprojection_off.append(f"{locid}: {offset * 1000:.3f} mm")

            # Attribute against geometry: does the point sit in the regional
            # envelope of the state its own attribute claims?
            region = state_regions.get(source["state"])
            if region is None:
                attribute_conflicts.append(
                    f"{locid}: state {source['state']!r} has no region"
                )
            else:
                x_min, x_max, y_min, y_max = box_in_metres(region_boxes[region])
                if not (x_min <= row["x"] <= x_max and y_min <= row["y"] <= y_max):
                    attribute_conflicts.append(
                        f"{locid}: state {source['state']!r} -> region "
                        f"{region!r}, but the point is outside it"
                    )

            for field in BLANK_CANDIDATE_FIELDS:
                if source.get(field) == BLANK:
                    blank_counts[field] += 1

        checks.append(
            Check(
                "geo_point is not the object format ArcGIS rejects",
                not object_format,
                f"{len(object_format)} of {len(hits)} documents use "
                "{lat, lon}"
                + (f": {', '.join(object_format[:5])}" if object_format else ""),
            )
        )
        checks.append(
            Check(
                "geo_point value decodes per the OpenSearch specification",
                not decode_errors,
                f"{len(decode_errors)} of {len(hits)} undecodable"
                + (f": {decode_errors[0]}" if decode_errors else ""),
            )
        )
        checks.append(
            Check(
                "Geometry agrees with the document's latitude/longitude fields",
                not internal_mismatch,
                f"{len(internal_mismatch)} of {len(hits)} disagree"
                + (
                    f": {', '.join(internal_mismatch[:5])}"
                    if internal_mismatch
                    else ""
                ),
            )
        )
        checks.append(
            Check(
                "Provenance: indexed EPSG:3857 metres are the source's, bit-identical",
                not provenance_mismatch,
                f"{len(provenance_mismatch)} of {len(hits)} not traceable"
                + (f": {provenance_mismatch[0]}" if provenance_mismatch else ""),
            )
        )
        checks.append(
            Check(
                "Reprojection recomputed forward by independent code",
                not reprojection_off,
                f"worst offset {reprojection_worst * 1000:.4f} mm over "
                f"{len(hits)} documents, tolerance "
                f"{REPROJECTION_TOLERANCE_M * 1000:.0f} mm"
                + (f"; {len(reprojection_off)} over: {reprojection_off[0]}"
                   if reprojection_off else ""),
            )
        )

        # -- 4. axis order and the antimeridian, refereed by OpenSearch -------
        # Regional boxes rather than one envelope. This is a consistency check
        # against the fixture generator's own definition, not an independent
        # one - the independent checks are the reprojection and the provenance
        # above, and locating the independence honestly beats claiming it here.
        used_regions = sorted({state_regions[row["attributes"]["state"]]
                               for row in fixture.values()})
        for region in used_regions:
            box = region_boxes[region]
            x_min, x_max, y_min, y_max = box_in_metres(box)
            expected = sum(
                1
                for row in fixture.values()
                if x_min <= row["x"] <= x_max and y_min <= row["y"] <= y_max
            )
            found = client.count(args.index, bounding_box_query(box))
            region_table.append((region, expected, found))

        union_clauses = [bounding_box_query(region_boxes[r]) for r in used_regions]
        inside = client.count(args.index, any_of(union_clauses))
        checks.append(
            Check(
                f"Union of {len(used_regions)} regional bounding boxes matches "
                "every document",
                inside == len(fixture),
                f"{inside:,} of {len(fixture):,} inside the union of "
                f"{', '.join(used_regions)}",
            )
        )

        # The same boxes with latitude and longitude exchanged. If the indexer
        # had swapped the axes, this is where the points would have landed.
        #
        # Except that for most of these regions **the transposed box does not
        # exist**. A latitude is only valid in [-90, 90], and Alaska's
        # longitudes run -179.5..-129.5 - transposing that region asks for a
        # box whose latitudes are off the planet, and OpenSearch rejects the
        # query outright ("top is below bottom corner"). So the transposed test
        # is built only for the regions where it is geometrically possible, and
        # the rest are counted and named rather than silently dropped.
        #
        # The absence is the more interesting result: for a data set whose
        # longitudes exceed +/-90, a swapped axis is not a wrong point, it is an
        # unindexable one - OpenSearch refuses the document. Compare the
        # station index, where a swap put every station in the Indian Ocean and
        # everything still loaded. The loud failure is the harmless one, and
        # here the failure is loud. `index_airports.py --swap-axes` provokes it
        # on demand.
        transposable = []
        untransposable = []
        for region in used_regions:
            lat_min, lat_max, lon_min, lon_max = region_boxes[region]
            new_lat_min = max(-90.0, lon_min)
            new_lat_max = min(90.0, lon_max)
            if new_lat_min >= new_lat_max:
                untransposable.append(region)
                continue
            transposable.append(
                bounding_box_query((new_lat_min, new_lat_max, lat_min, lat_max))
            )
        if transposable:
            swapped = client.count(args.index, any_of(transposable))
        else:
            swapped = 0
        checks.append(
            Check(
                "Axis-transposed boxes match nothing",
                swapped == 0,
                f"{swapped:,} documents found in the {len(transposable)} "
                f"transposable region box(es). {len(untransposable)} region(s) "
                f"have no transposed box at all - their longitudes lie outside "
                f"[-90, 90], so a swapped latitude would be invalid rather than "
                f"merely wrong"
                + (f" ({', '.join(untransposable)})" if untransposable else "")
                + ". Where the test does apply it passes because no airport sits "
                "at longitude -14..71 - luck, not design, and worth knowing "
                "before relying on this check for another data set",
            )
        )

        # A box that deliberately spans the antimeridian: top_left.lon is east
        # of bottom_right.lon, which is how OpenSearch is told to wrap. This
        # data set needs it - the naive envelope below is 344 degrees wide.
        dateline_box = {
            "geo_bounding_box": {
                "location": {
                    "top_left": {"lat": 90.0, "lon": DATELINE_LON},
                    "bottom_right": {"lat": -90.0, "lon": -DATELINE_LON},
                }
            }
        }
        x_east, _ = to_web_mercator(DATELINE_LON, 0.0)
        x_west, _ = to_web_mercator(-DATELINE_LON, 0.0)
        expected_dateline = sum(
            1 for row in fixture.values() if row["x"] >= x_east or row["x"] <= x_west
        )
        found_dateline = client.count(args.index, dateline_box)
        checks.append(
            Check(
                f"Antimeridian-spanning box (lon {DATELINE_LON:g} .. "
                f"{-DATELINE_LON:g}) matches the expected set",
                found_dateline == expected_dateline,
                f"OpenSearch {found_dateline:,}, computed from the source "
                f"metres {expected_dateline:,}",
            )
        )

        # The naive envelope: it passes, and it says nothing. In on purpose.
        # Computed from the source metres, so it does not lean on the inverse
        # formula either - the radius here is EPSG:3857's, not a mean radius.
        x_values = [row["x"] for row in fixture.values()]
        envelope_hits = client.count(
            args.index,
            bounding_box_query((-85.0, 85.0, -180.0, 180.0)),
        )
        span = math.degrees((max(x_values) - min(x_values)) / 6378137.0)
        checks.append(
            Check(
                "Naive whole-set bounding box (informational)",
                None,
                f"{envelope_hits:,} of {len(fixture):,} documents inside a box "
                f"spanning the world. The source's own longitude envelope is "
                f"{span:.2f} degrees wide because the set crosses the "
                f"antimeridian - it contains everything and discriminates "
                f"nothing, which is why the regional boxes above exist",
            )
        )

        # -- 6. geo_distance against an independent haversine -----------------
        if args.distance_center:
            center_locid = args.distance_center
        else:
            center_locid = max(
                fixture, key=lambda key: fixture[key]["attributes"]["tot_enp"]
            )
        center = fixture.get(center_locid)
        if center is None:
            checks.append(
                Check(
                    "geo_distance query",
                    None,
                    f"skipped: locid {center_locid!r} is not in the FeatureSet",
                )
            )
        else:
            center_doc = client.search(
                args.index,
                {
                    "size": 1,
                    "query": {"term": {"locid": center_locid}},
                    "_source": ["latitude", "longitude", "name", "state"],
                },
            )["hits"]["hits"]
            if not center_doc:
                checks.append(
                    Check(
                        "geo_distance query",
                        None,
                        f"skipped: locid {center_locid!r} is not in the index",
                    )
                )
            else:
                center_source = center_doc[0]["_source"]
                center_lat = float(center_source["latitude"])
                center_lon = float(center_source["longitude"])
                radius_m = args.distance_km * 1000.0
                response = client.search(
                    args.index,
                    {
                        "size": len(fixture),
                        "_source": ["locid", "latitude", "longitude", "name"],
                        "query": {
                            "geo_distance": {
                                "distance": f"{args.distance_km}km",
                                "location": {"lat": center_lat, "lon": center_lon},
                            }
                        },
                    },
                )
                engine = {
                    hit["_source"]["locid"]: hit["_source"]
                    for hit in response["hits"]["hits"]
                }
                own = {}
                for hit_locid, source in (
                    (h["_source"]["locid"], h["_source"]) for h in hits
                ):
                    distance = haversine_m(
                        center_lat,
                        center_lon,
                        float(source["latitude"]),
                        float(source["longitude"]),
                    )
                    if distance <= radius_m:
                        own[hit_locid] = distance
                # Points within 0.5 % of the radius may fall either way between
                # two distance implementations; anything further out is a real
                # disagreement.
                margin = radius_m * 0.005
                disputed = []
                for code in set(engine).symmetric_difference(own):
                    row = fixture[code]["attributes"]
                    reference = engine.get(code) or next(
                        h["_source"] for h in hits if h["_source"]["locid"] == code
                    )
                    distance = haversine_m(
                        center_lat,
                        center_lon,
                        float(reference["latitude"]),
                        float(reference["longitude"]),
                    )
                    if abs(distance - radius_m) > margin:
                        disputed.append(
                            f"{code} ({row['name']}) at {distance / 1000:.3f} km"
                        )
                checks.append(
                    Check(
                        f"geo_distance {args.distance_km:g} km around "
                        f"{center_source['name']} matches an independent haversine",
                        not disputed,
                        f"OpenSearch {len(engine)}, haversine {len(own)}, "
                        f"{len(disputed)} outside the {margin:.0f} m margin"
                        + (f": {', '.join(disputed[:5])}" if disputed else ""),
                    )
                )
                for code in sorted(engine)[:10]:
                    source = engine[code]
                    distance = haversine_m(
                        center_lat,
                        center_lon,
                        float(source["latitude"]),
                        float(source["longitude"]),
                    )
                    distance_table.append(
                        (code, source["name"], distance / 1000.0, args.distance_km)
                    )

        # -- 7. what this source has that the station data did not ------------
        checks.append(
            Check(
                "Attribute agrees with geometry (state vs. its region)",
                None,
                f"{len(attribute_conflicts)} of {len(hits)} documents place a "
                "point outside the region of the state its own attribute names"
                + (
                    f". First: {attribute_conflicts[0]}"
                    if attribute_conflicts
                    else ". Zero here is weaker evidence than it looks: the "
                    "fixture generator picks the state first and then samples "
                    "inside that state's own boxes, so this check exercises the "
                    "indexer and the reprojection rather than the source data. "
                    "The disagreement this source really carries is in the next "
                    "two rows. For comparison, on the station source - real, "
                    "published data - the same check found zero across all "
                    "5,367 in-service rows in either direction, and there "
                    "'zero' was a measurement"
                ),
            )
        )

        fips_names: dict[str, set[str]] = {}
        for row in fixture.values():
            attributes = row["attributes"]
            fips_names.setdefault(attributes["state_fips"], set()).add(
                attributes["state"]
            )
        ambiguous = {
            fips: sorted(names) for fips, names in fips_names.items() if len(names) > 1
        }
        code_like = sorted(
            {
                row["attributes"]["state"]
                for row in fixture.values()
                if len(row["attributes"]["state"]) == 2
            }
        )
        checks.append(
            Check(
                "State attribute is internally consistent",
                None,
                f"{len(ambiguous)} FIPS code(s) carry more than one state value"
                + (f" ({ambiguous})" if ambiguous else "")
                + f"; {len(code_like)} state value(s) are two-letter codes where "
                f"the rest are spelled out ({', '.join(code_like)}). Filtering "
                "on the attribute alone is therefore not the same question as "
                "filtering on the geometry",
            )
        )

        # The attribute conflict that does bite, measured rather than asserted.
        # A two-letter `state` value is only a problem when its postal code
        # names a different FIPS code than the row's own `state_fips`. That
        # distinction matters: one of the two codes in this source is merely an
        # abbreviation where the rest are spelled out, and the other points at
        # the wrong place entirely.
        code_findings: list[str] = []
        for code in code_like:
            rows = [
                row for row in fixture.values() if row["attributes"]["state"] == code
            ]
            own_fips = {row["attributes"]["state_fips"] for row in rows}
            postal_fips = POSTAL_TO_FIPS.get(code)
            if postal_fips is None:
                code_findings.append(f"{code!r} is not a US postal abbreviation")
                continue
            if postal_fips in own_fips:
                code_findings.append(
                    f"{code!r} is the correct abbreviation for FIPS "
                    f"{postal_fips} - inconsistent formatting, not a wrong value"
                )
                continue
            # The code names another FIPS. How far away is that other place?
            targets = [
                row
                for row in fixture.values()
                if row["attributes"]["state_fips"] == postal_fips
            ]
            detail = (
                f"{code!r} carries FIPS {'/'.join(sorted(own_fips))} but the "
                f"postal code {code!r} means FIPS {postal_fips}"
            )
            if targets:
                worst = max(
                    min(
                        math.dist((row["x"], row["y"]), (target["x"], target["y"]))
                        for target in targets
                    )
                    for row in rows
                )
                detail += (
                    f", whose airports are up to {worst / 1000:,.0f} km away "
                    f"(Web Mercator plane distance, inflated at these latitudes; "
                    f"the order of magnitude is the point)"
                )
            code_findings.append(detail)
        if code_findings:
            checks.append(
                Check(
                    "Two-letter state values checked against the postal standard",
                    None,
                    "; ".join(code_findings)
                    + ". So `WHERE state = 'HI'` returns points nowhere near "
                    "Hawaii while `WHERE state = 'Hawaii'` silently drops them. "
                    "Neither query is wrong - an attribute filter is not a "
                    "spatial filter, and this attribute is actively misleading",
                )
            )

        blank_detail = ", ".join(
            f"{field} {blank_counts[field]}/{len(hits)}"
            for field in BLANK_CANDIDATE_FIELDS
        )
        checks.append(
            Check(
                "'Empty' values that are a single space",
                None,
                f"{blank_detail}. The geodatabase stores ' ', not NULL and not "
                "''. In OpenSearch that is a real keyword term; in ArcGIS the "
                "cell looks empty and is not, so a filter on empty finds nothing "
                "and `IS NULL` finds nothing either",
            )
        )

        # -- 8. the SQL plugin, informational --------------------------------
        try:
            response = client.request(
                "POST",
                "/_plugins/_sql",
                json.dumps({"query": f"SELECT * FROM {args.index} LIMIT 1"}),
            )
            sql_detail = (
                "reads this geo_point format"
                if response.get("datarows")
                else "answered, but returned no rows"
            )
        except OpenSearchError as exc:
            reason = exc.body
            try:
                reason = json.loads(exc.body)["error"]["details"]
            except (ValueError, KeyError, TypeError):
                pass
            sql_detail = f"cannot read this geo_point format: {reason[:120]}"
        checks.append(
            Check(
                "OpenSearch SQL plugin (ArcGIS query layers are SQL)",
                None,
                sql_detail,
            )
        )
    except OpenSearchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 6

    failed = [check for check in checks if check.passed is False]

    lines = [
        "# OpenSearch index verification report",
        "",
        f"- Index: `{args.index}`",
        f"- Cluster: `{args.host}` (OpenSearch {version})",
        f"- Source FeatureSet: `{args.input}` (Esri JSON, esriGeometryPoint, "
        "EPSG:3857 metres)",
        f"- Manifest: `{args.manifest}`",
        f"- Features in the source: {len(fixture):,}",
        f"- Documents checked for reprojection and provenance: {len(hits):,}",
        f"- geo_distance centre: `{center_locid}`, radius {args.distance_km:g} km",
        f"- Worst reprojection offset: {reprojection_worst * 1000:.4f} mm "
        f"(tolerance {REPROJECTION_TOLERANCE_M * 1000:.0f} mm)",
        "",
        "Generated by `scripts/verify_airports.py`. The source carries EPSG:3857",
        "metres, so the index carries a *computed* geographic coordinate - and",
        "the two checks that matter reflect that: the source metres are asserted",
        "bit-identical, and the transformation is recomputed from the indexed",
        "degrees in the opposite direction by `webmercator.py`, which the indexer",
        "does not import. The geo_point value is decoded from the OpenSearch",
        "specification independently of the indexer's formatting function, and",
        "axis order is refereed by the search engine itself. Regenerate with the",
        "command in [`../README.md`](../README.md).",
        "",
        "## Summary",
        "",
    ]
    lines += render_check_table(checks)

    lines += [
        "",
        "## Field types as ArcGIS will see them",
        "",
        "Transcribed from Esri's data-type table for document databases, not from",
        "the index mapping, so a wrong type here is a finding rather than a shared",
        "assumption.",
        "",
        "| Field | OpenSearch type | ArcGIS type |",
        "|---|---|---|",
    ]
    for field, field_type, arcgis_type in field_table:
        lines.append(f"| `{field}` | `{field_type}` | {arcgis_type} |")

    if region_table:
        lines += [
            "",
            "## Regional bounding boxes",
            "",
            "One `geo_bounding_box` query per region, against the count computed",
            "from the source metres with the forward projection only. Regions",
            "rather than one envelope because the set crosses the antimeridian:",
            "the whole-set box is 344 degrees wide and matches everything.",
            "",
            "| Region | Expected from source | OpenSearch |",
            "|---|---|---|",
        ]
        for region, expected, found in region_table:
            marker = "" if expected == found else " **mismatch**"
            lines.append(f"| `{region}` | {expected:,} | {found:,}{marker} |")

    if distance_table:
        lines += [
            "",
            "## geo_distance sample (informational)",
            "",
            "The ten nearest airports OpenSearch returned, with the distance this",
            "script computed for the same pair of coordinates.",
            "",
            "| locid | Airport | Haversine (km) | Radius (km) |",
            "|---|---|---|---|",
        ]
        for code, name, distance, radius in distance_table:
            lines.append(f"| `{code}` | {name} | {distance:.3f} | {radius:g} |")

    lines += [
        "",
        "## Verdict",
        "",
        (
            f"**{len(failed)} check(s) failed.**"
            if failed
            else "**All checks passed.**"
        ),
        "",
    ]

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.report} | {len(checks)} checks, {len(failed)} failed")

    for check in checks:
        print(f"  {check.verdict:4} {check.name} - {check.detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
