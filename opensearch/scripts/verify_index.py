#!/usr/bin/env python3
"""Verify that the OpenSearch index is one ArcGIS can actually draw.

An index that answers `_count` correctly can still be useless to a GIS client,
and the ways it fails are quiet ones. This script asks the running cluster the
questions ArcGIS Pro will ask it, and writes a PASS/FAIL report.

What it checks, and why each check exists:

1. **Document count** against the source CSV. The cheap one.

2. **Field types against the ArcGIS mapping table.** Every property of the
   index has to land on a type ArcGIS understands, and `location` has to be
   `geo_point`. A field that OpenSearch inferred as `text` where a number was
   meant shows up in ArcGIS as a string column that cannot be classified.
   `dynamic: strict` is asserted too, because a mapping that can still grow is
   a mapping that can drift after publishing.

3. **The geo_point is not in the object format.** Esri: "The geopoint format
   that uses an object with a latitude and longitude is not supported with
   ArcGIS." `_source.location` therefore must not be a JSON object. This is the
   single check most likely to fail on an index somebody built from the
   OpenSearch documentation alone, and nothing about the index looks wrong
   until ArcGIS refuses it.

4. **Axis order, decided by the search engine rather than by us.** The verifier
   decodes `location` from the spec a second time, independently of the
   indexer's formatting function - array is `[lon, lat]`, a bare string is
   `"lat,lon"`, WKT is `POINT (lon lat)` - and cross-checks the result against
   the `latitude`/`longitude` fields of the same document. Then it lets
   OpenSearch referee: a `geo_bounding_box` over North Rhine-Westphalia must
   match every station, and the same box with the two axes swapped must match
   none. A swap at index time cannot pass both.

5. **Provenance, not plausibility.** For a sample of documents, the coordinates
   that come back out of the index have to be byte-identical to the CSV row
   with the same DS100 code. A coordinate quietly moved to another plausible
   spot inside NRW passes the bounding box, the axis test and the geo query;
   only this catches it.

6. **`geo_distance` against an independent haversine.** The set of stations
   OpenSearch returns within a radius of Köln Hbf is compared against the set
   computed here from the CSV. Agreement means the `geo_point` is genuinely
   indexed, not just stored - which is the difference between a layer that
   draws and a layer that draws *and* filters.

7. **The SQL plugin, reported but not enforced.** ArcGIS query layers are
   written in SQL, and OpenSearch ships a SQL plugin. Measured here: that
   plugin reads *only* the object format - `geo point must in format of
   {"lat": number, "lon": number}` - for array, string, WKT and geohash alike.
   That is precisely the one format Esri rules out. So if ArcGIS delegates its
   SQL to the plugin, no representation satisfies both, and if it translates SQL
   itself, the plugin is irrelevant. Which of the two is true cannot be
   determined from this side, so this check reports and never fails.

Reads the CSV and the cluster; writes only the report. Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import json
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

# North Rhine-Westphalia, from the bounding box of the source CSV plus a margin.
NRW_BOX = {"lat_min": 50.20, "lat_max": 52.60, "lon_min": 5.80, "lon_max": 9.50}


def read_stations(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["ds100"]: row for row in csv.DictReader(handle)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_index.py",
        description=(
            "Verify a station index against the source CSV and against what "
            "ArcGIS Pro requires: document count, ArcGIS-compatible field types, a "
            "geo_point format ArcGIS can read, axis order refereed by the search "
            "engine itself, coordinate provenance, and a geo_distance query "
            "cross-checked with an independent haversine. Writes a Markdown report "
            "and exits non-zero on any failure."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/verify_index.py \\\n"
            "      --host https://localhost:9200 \\\n"
            "      --ca-cert build/tls/root-ca.pem \\\n"
            "      --report output/verification_report.md\n\n"
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
        default=Path("../open_data_search/output/nrw_stations.csv"),
        metavar="CSV",
        help="source CSV the index was built from (default: %(default)s)",
    )
    parser.add_argument(
        "--index",
        default="nrw_stations",
        metavar="NAME",
        help="index to verify (default: %(default)s)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=25,
        metavar="N",
        help="documents to check for coordinate provenance; 0 checks all of them "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--distance-center",
        default="KK",
        metavar="DS100",
        help="DS100 code the geo_distance query is centred on (default: %(default)s)",
    )
    parser.add_argument(
        "--distance-km",
        type=float,
        default=30.0,
        metavar="KM",
        help="radius of the geo_distance query (default: %(default)s)",
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

    if not args.input.exists():
        print(f"error: source CSV not found: {args.input}", file=sys.stderr)
        return 2
    stations = read_stations(args.input)
    print(f"read {args.input} | {len(stations):,} stations")

    client = OpenSearchClient(
        host=args.host,
        user=None if args.no_auth else args.user,
        password=None if args.no_auth else resolve_password(args),
        ca_cert=str(args.ca_cert) if args.ca_cert else None,
        verify_tls=not args.insecure_tls,
    )

    checks: list[Check] = []
    distance_table: list[tuple[str, str, float, float]] = []
    field_table: list[tuple[str, str, str]] = []

    try:
        info = client.info()
        version = info.get("version", {}).get("number", "?")
        print(f"connected to {args.host} | OpenSearch {version}")

        # -- 1. document count ------------------------------------------------
        count = client.count(args.index)
        checks.append(
            Check(
                "Document count matches the source CSV",
                count == len(stations),
                f"{count:,} documents, {len(stations):,} CSV rows",
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

        # -- 3./5. geo_point format and coordinate provenance -----------------
        size = len(stations) if args.sample_size == 0 else args.sample_size
        hits = client.search(
            args.index,
            {"size": size, "query": {"match_all": {}}, "sort": [{"ds100": "asc"}]},
        )["hits"]["hits"]

        object_format = []
        decode_errors = []
        internal_mismatch = []
        provenance_mismatch = []
        for hit in hits:
            source = hit["_source"]
            ds100 = source["ds100"]
            raw = source.get("location")
            if isinstance(raw, dict):
                object_format.append(ds100)
                continue
            try:
                latitude, longitude = decode_location(raw)
            except ValueError as exc:
                decode_errors.append(f"{ds100}: {exc}")
                continue
            # the geometry against the document's own numeric columns
            if (round(latitude, 5), round(longitude, 5)) != (
                round(float(source["latitude"]), 5),
                round(float(source["longitude"]), 5),
            ):
                internal_mismatch.append(ds100)
            # the document against the CSV row it came from
            row = stations.get(ds100)
            if row is None:
                provenance_mismatch.append(f"{ds100}: not in the CSV at all")
            elif f"{latitude:.5f}" != row["latitude"] or (
                f"{longitude:.5f}" != row["longitude"]
            ):
                provenance_mismatch.append(
                    f"{ds100}: index {latitude:.5f}/{longitude:.5f} vs CSV "
                    f"{row['latitude']}/{row['longitude']}"
                )

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
                + (f": {', '.join(internal_mismatch[:5])}" if internal_mismatch else ""),
            )
        )
        checks.append(
            Check(
                "Provenance: indexed coordinates are the CSV's, unmodified",
                not provenance_mismatch,
                f"{len(provenance_mismatch)} of {len(hits)} not traceable"
                + (f": {provenance_mismatch[0]}" if provenance_mismatch else ""),
            )
        )

        # -- 4. axis order, refereed by OpenSearch ----------------------------
        inside = client.count(
            args.index,
            {
                "geo_bounding_box": {
                    "location": {
                        "top_left": {
                            "lat": NRW_BOX["lat_max"],
                            "lon": NRW_BOX["lon_min"],
                        },
                        "bottom_right": {
                            "lat": NRW_BOX["lat_min"],
                            "lon": NRW_BOX["lon_max"],
                        },
                    }
                }
            },
        )
        checks.append(
            Check(
                "geo_bounding_box over NRW matches every station",
                inside == len(stations),
                f"{inside:,} of {len(stations):,} inside "
                f"lat {NRW_BOX['lat_min']}..{NRW_BOX['lat_max']} / "
                f"lon {NRW_BOX['lon_min']}..{NRW_BOX['lon_max']}",
            )
        )
        # The same box with latitude and longitude exchanged. If the indexer had
        # swapped the axes, this is the box the stations would have landed in.
        swapped = client.count(
            args.index,
            {
                "geo_bounding_box": {
                    "location": {
                        "top_left": {
                            "lat": NRW_BOX["lon_max"],
                            "lon": NRW_BOX["lat_min"],
                        },
                        "bottom_right": {
                            "lat": NRW_BOX["lon_min"],
                            "lon": NRW_BOX["lat_max"],
                        },
                    }
                }
            },
        )
        checks.append(
            Check(
                "Axis-swapped bounding box matches nothing",
                swapped == 0,
                f"{swapped:,} stations found in the transposed box "
                f"(lat {NRW_BOX['lon_min']}..{NRW_BOX['lon_max']} / "
                f"lon {NRW_BOX['lat_min']}..{NRW_BOX['lat_max']})",
            )
        )

        # -- 6. geo_distance against an independent haversine -----------------
        center = stations.get(args.distance_center)
        if center is None:
            checks.append(
                Check(
                    "geo_distance query",
                    None,
                    f"skipped: DS100 {args.distance_center!r} is not in the CSV",
                )
            )
        else:
            center_lat = float(center["latitude"])
            center_lon = float(center["longitude"])
            radius_m = args.distance_km * 1000.0
            response = client.search(
                args.index,
                {
                    "size": len(stations),
                    "_source": ["ds100"],
                    "query": {
                        "geo_distance": {
                            "distance": f"{args.distance_km}km",
                            "location": {"lat": center_lat, "lon": center_lon},
                        }
                    },
                },
            )
            engine_hits = {h["_source"]["ds100"] for h in response["hits"]["hits"]}
            own_hits = {
                code
                for code, row in stations.items()
                if haversine_m(
                    center_lat, center_lon, float(row["latitude"]), float(row["longitude"])
                )
                <= radius_m
            }
            # Stations sitting within 0.5 % of the radius may fall either way
            # between two distance implementations; anything further out is a
            # real disagreement.
            margin = radius_m * 0.005
            disputed = []
            for code in engine_hits.symmetric_difference(own_hits):
                row = stations[code]
                distance = haversine_m(
                    center_lat,
                    center_lon,
                    float(row["latitude"]),
                    float(row["longitude"]),
                )
                if abs(distance - radius_m) > margin:
                    disputed.append(f"{code} at {distance / 1000:.3f} km")
            checks.append(
                Check(
                    f"geo_distance {args.distance_km:g} km around "
                    f"{center['name']} matches an independent haversine",
                    not disputed,
                    f"OpenSearch {len(engine_hits)}, haversine {len(own_hits)}, "
                    f"{len(disputed)} outside the {margin:.0f} m margin"
                    + (f": {', '.join(disputed[:5])}" if disputed else ""),
                )
            )
            for code in sorted(engine_hits)[:10]:
                row = stations[code]
                distance = haversine_m(
                    center_lat,
                    center_lon,
                    float(row["latitude"]),
                    float(row["longitude"]),
                )
                distance_table.append(
                    (code, row["name"], distance / 1000.0, args.distance_km)
                )
        # -- 7. the SQL plugin, informational --------------------------------
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

    failed = [c for c in checks if c.passed is False]

    lines = [
        "# OpenSearch index verification report",
        "",
        f"- Index: `{args.index}`",
        f"- Cluster: `{args.host}` (OpenSearch {version})",
        f"- Source CSV: `{args.input}`",
        f"- Stations in the CSV: {len(stations):,}",
        f"- Documents sampled for provenance: {len(hits):,}",
        f"- geo_distance centre: `{args.distance_center}`, radius "
        f"{args.distance_km:g} km",
        "",
        "Generated by `scripts/verify_index.py`. The geo_point value is decoded",
        "from the OpenSearch specification independently of the indexer's",
        "formatting function, axis order is refereed by the search engine itself",
        "through a pair of bounding-box queries, and the geo_distance result is",
        "cross-checked against a haversine computed here. Regenerate with the",
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

    if distance_table:
        lines += [
            "",
            "## geo_distance sample (informational)",
            "",
            "The ten nearest stations OpenSearch returned, with the distance this",
            "script computed for the same pair of coordinates.",
            "",
            "| DS100 | Station | Haversine (km) | Radius (km) |",
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
