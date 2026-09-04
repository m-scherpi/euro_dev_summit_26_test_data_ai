#!/usr/bin/env python3
"""Measure a CSV or JSON file and write the schema contract for a feature class.

This is stage one of three, and the only one that runs anywhere. It touches no
database, imports no ArcGIS, and produces a single reviewable artifact: a JSON
document saying what feature class should be built, with which fields, of which
types and lengths, in which spatial reference - and, for every one of those
decisions, the measurement behind it.

Splitting the pipeline here is the point. The importer needs Windows and a
licensed ArcGIS Pro; the *decisions* it acts on do not. So the contract can be
generated, read, argued with and corrected on a laptop, and the half that needs
the VM becomes a mechanical transcription of a document somebody already looked
at. It is also the "universal" interface the use case was asked for: any other
script - a jq one-liner, a hand edit, a different generator - can produce a
contract, and `import_to_egdb.py` neither knows nor cares where the data came
from.

Two refusals are deliberate, and both exist because the alternative failure is
silent:

* **The CRS is never guessed.** Column names decide it: `latitude`/`longitude`
  means EPSG:4326, `x_3857`/`y_3857` means EPSG:3857. A bare `x`/`y` pair means
  the file did not say, so `--wkid` becomes mandatory rather than defaulted -
  CLAUDE.md section 4, "coordinates" is not a specification. And when a file
  carries *both* pairs, as `csv_data/output/nrw_points.csv` does,
  `--geometry-from` becomes mandatory too. A feature class has exactly one
  spatial reference and picking it by column order would be a coin flip whose
  result looks fine.

* **An Esri JSON FeatureSet is asserted, not converted.** `geometryType` must
  be `esriGeometryPoint` and the spatial reference must be stated, or the run
  aborts. A FeatureSet in some other projected CRS is still metres, just of a
  different grid, and converting whatever turned up would produce plausible,
  wrong output.

By default the coordinate columns stay in the field list as ordinary numbers,
even though the geometry is built from them. They are redundant for drawing,
and that is exactly why they are kept: they are what `verify_featureclass.py`
compares the stored geometry against. `--drop-geometry-columns` removes them for
anyone who wants the lean table instead.

Stdlib only. Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date as date_cls
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources import SourceError, read_csv, read_json  # noqa: E402  (path shim first)
from schema import (  # noqa: E402
    DEFAULT_TEXT_HEADROOM,
    MAX_FIELD_NAME_LEN,
    MAX_TABLE_NAME_LEN,
    SchemaError,
    build_fields,
    sanitize_name,
)

DEFAULT_INPUT = Path("../csv_data/output/nrw_points.csv")
DEFAULT_OUTPUT = Path("output/nrw_points_schema.json")

# Geographic column pairs, most explicit first. `lat`/`lon` are accepted for
# universality but recorded as what matched, because CLAUDE.md section 4 is
# clear that a projected coordinate must never be called lat/lon - so a file
# using those names is asserting it is geographic, and the contract says so.
# A bare x/y pair is deliberately absent here and handled by find_xy instead.
# Treating it as geographic would mean assuming degrees, and the whole point of
# the x/y branch is that such a file has not said what its units are.
LATLON_PAIRS = (
    ("latitude", "longitude"),
    ("lat", "lon"),
    ("lat", "long"),
)

X_SUFFIXED = re.compile(r"^x_(\d{4,6})$")


# ---------------------------------------------------------------------------
# Geometry resolution
# ---------------------------------------------------------------------------


def find_latlon(columns: list[str]) -> tuple[str, str, str] | None:
    """Return `(y_column, x_column, matched_pair)` for a geographic pair."""
    lowered = {c.lower(): c for c in columns}
    for lat_name, lon_name in LATLON_PAIRS:
        if lat_name in lowered and lon_name in lowered:
            return lowered[lat_name], lowered[lon_name], f"{lat_name}/{lon_name}"
    return None


def find_xy(columns: list[str]) -> tuple[str, str, int | None] | None:
    """Return `(y_column, x_column, wkid)` for a projected pair.

    `wkid` is `None` when the columns are a bare `x`/`y` - the file has metres
    (or degrees, or feet) of an unstated grid, and `--wkid` is then required.
    """
    lowered = {c.lower(): c for c in columns}
    for name, match in ((n, X_SUFFIXED.match(n)) for n in lowered):
        if not match:
            continue
        epsg = match.group(1)
        partner = f"y_{epsg}"
        if partner in lowered:
            return lowered[partner], lowered[name], int(epsg)
    if "x" in lowered and "y" in lowered:
        return lowered["y"], lowered["x"], None
    return None


def resolve_geometry(
    columns: list[str], hint: dict[str, Any], geometry_from: str | None, wkid: int | None
) -> dict[str, Any]:
    """Decide which columns carry the geometry and in which CRS, or refuse."""
    if hint:
        # The file said so itself. A --wkid that disagrees is a mistake worth
        # stopping for, not an override: the coordinates are what they are.
        if wkid is not None and wkid != hint["wkid"]:
            raise SourceError(
                f"--wkid {wkid} contradicts the source file, which states EPSG:{hint['wkid']} "
                f"({hint['wkid_source']}). Fix the flag or the file; this tool will not "
                "reinterpret coordinates."
            )
        return dict(hint)

    latlon = find_latlon(columns)
    xy = find_xy(columns)

    if latlon and xy and geometry_from is None:
        raise SourceError(
            f"the source carries two coordinate pairs - {latlon[2]} and "
            f"{xy[1]}/{xy[0]} - and a feature class has exactly one spatial reference. "
            "Pass --geometry-from latlon or --geometry-from xy. Picking one silently would be "
            "a coin flip whose result looks correct either way."
        )

    choice = geometry_from
    if choice is None:
        choice = "latlon" if latlon else "xy" if xy else None
    if choice is None:
        raise SourceError(
            "no coordinate columns found. Expected a geographic pair "
            "(latitude/longitude, lat/lon) or a projected pair (x_<epsg>/y_<epsg>, or x/y "
            "together with --wkid)."
        )

    if choice == "latlon":
        if not latlon:
            raise SourceError("--geometry-from latlon, but no geographic column pair was found")
        y_col, x_col, matched = latlon
        if wkid is not None and wkid != 4326:
            raise SourceError(
                f"--wkid {wkid} contradicts the column names {matched}, which name a "
                "geographic pair and therefore decimal degrees (EPSG:4326). A projected "
                "coordinate must never be called lat/lon (CLAUDE.md section 4), so either "
                "the flag or the column names are wrong."
            )
        resolved = 4326
        why = (
            f"column names {matched}: a geographic pair is decimal degrees, EPSG:4326. "
            "Note that 'decimal degrees' and 'EPSG:3857' are mutually exclusive - "
            "EPSG:3857 is metres."
        )
        return {
            "from": "latlon",
            "x_column": x_col,
            "y_column": y_col,
            "wkid": resolved,
            "wkid_source": why,
        }

    if not xy:
        raise SourceError("--geometry-from xy, but no projected column pair was found")
    y_col, x_col, suffix_wkid = xy
    if suffix_wkid is None:
        if wkid is None:
            raise SourceError(
                f"columns {x_col}/{y_col} carry no EPSG code, so the file does not say which "
                "grid they are metres of. Pass --wkid."
            )
        resolved, why = wkid, f"--wkid, because {x_col}/{y_col} carry no EPSG code"
    else:
        resolved = suffix_wkid
        why = f"the EPSG code in the column names {x_col}/{y_col}"
        if wkid is not None and wkid != suffix_wkid:
            raise SourceError(
                f"--wkid {wkid} contradicts the column names {x_col}/{y_col}, which state "
                f"EPSG:{suffix_wkid}."
            )
    return {
        "from": "xy",
        "x_column": x_col,
        "y_column": y_col,
        "wkid": resolved,
        "wkid_source": why,
    }


def measure_bounds(rows: list[dict[str, Any]], x_col: str, y_col: str) -> dict[str, float]:
    """The source's own extent, carried into the contract as the expected box.

    The verifier compares the feature class extent against this rather than
    against a hand-written region box, so the expectation is a measurement of
    the input instead of somebody's memory of where the data should be.
    """
    xs: list[float] = []
    ys: list[float] = []
    for index, row in enumerate(rows):
        try:
            xs.append(float(row[x_col]))
            ys.append(float(row[y_col]))
        except (TypeError, ValueError, KeyError) as exc:
            raise SourceError(
                f"row {index}: coordinate columns {x_col}/{y_col} do not both hold a number "
                f"({row.get(x_col)!r}, {row.get(y_col)!r})"
            ) from exc
    return {
        "x_min": min(xs),
        "y_min": min(ys),
        "x_max": max(xs),
        "y_max": max(ys),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analyze_source.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Measure a CSV or JSON source file and write the schema contract that "
            "import_to_egdb.py builds a feature class from. Touches no database and imports "
            "no ArcGIS, so it runs anywhere."
        ),
        epilog=(
            "Example - the committed artifact, from the repository root:\n"
            "\n"
            "  cd egdb_import\n"
            "  python3 scripts/analyze_source.py \\\n"
            "      --input ../csv_data/output/nrw_points.csv \\\n"
            "      --geometry-from latlon \\\n"
            "      --feature-class nrw_points \\\n"
            "      --generated-date 2026-09-04 \\\n"
            "      --output output/nrw_points_schema.json\n"
            "\n"
            "--geometry-from is required for that file because it carries both\n"
            "latitude/longitude and x_3857/y_3857, and a feature class has exactly one\n"
            "spatial reference.\n"
        ),
    )
    parser.add_argument(
        "--input",
        metavar="PATH",
        type=Path,
        default=DEFAULT_INPUT,
        help="source CSV or JSON to measure (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="where to write the schema contract (default: %(default)s)",
    )
    parser.add_argument(
        "--feature-class",
        metavar="NAME",
        default=None,
        help="name of the feature class to create (default: the input file's stem, sanitised)",
    )
    parser.add_argument(
        "--geometry-from",
        metavar="WHICH",
        choices=("latlon", "xy"),
        default=None,
        help=(
            "which coordinate pair becomes the geometry: 'latlon' for a geographic pair, "
            "'xy' for a projected one. Required when the source carries both; there is no "
            "default, on purpose."
        ),
    )
    parser.add_argument(
        "--wkid",
        metavar="EPSG",
        type=int,
        default=None,
        help=(
            "EPSG code of the coordinates, required only when the source does not state it "
            "(a bare x/y pair). Contradicting what the source does state is an error."
        ),
    )
    parser.add_argument(
        "--delimiter",
        metavar="CHAR",
        default=None,
        help="CSV delimiter (default: sniffed from the first 8 kB)",
    )
    parser.add_argument(
        "--encoding",
        metavar="NAME",
        default="utf-8-sig",
        help="source text encoding; utf-8-sig also handles a BOM (default: %(default)s)",
    )
    parser.add_argument(
        "--text-headroom",
        metavar="FACTOR",
        type=float,
        default=DEFAULT_TEXT_HEADROOM,
        help=(
            "multiply the measured maximum text length by this before rounding up to a TEXT "
            "field length (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--drop-geometry-columns",
        action="store_true",
        help=(
            "leave the coordinate columns out of the field list. By default they are kept as "
            "ordinary numbers - redundant for drawing, which is why they are useful: they are "
            "what the verifier compares the stored geometry against."
        ),
    )
    parser.add_argument(
        "--rename",
        metavar="OLD=NEW",
        action="append",
        default=[],
        help=(
            "rename a source column, repeatable. Required when a column collides with a name "
            "the geodatabase manages itself - `objectid`, `shape`, `globalid`. `input/` is "
            "read-only, so the rename happens here and is recorded in the contract. A rename "
            "naming a column that does not exist is an error, not a no-op."
        ),
    )
    parser.add_argument(
        "--infer-types",
        action="store_true",
        help=(
            "measure the types instead of trusting a source that declares its own. Only an "
            "Esri JSON FeatureSet declares one; without this flag its `fields` block decides "
            "the types and lengths, and the measurement is recorded beside them."
        ),
    )
    parser.add_argument(
        "--generated-date",
        metavar="YYYY-MM-DD",
        default=None,
        help=(
            "date recorded in the contract (default: today). Pass the committed value to "
            "reproduce the committed artifact byte for byte."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    raw_bytes = args.input.read_bytes()
    suffix = args.input.suffix.lower()

    try:
        if suffix in (".json", ".geojson"):
            columns, rows, hint = read_json(args.input, args.encoding)
            source_format = hint.get("from", "json")
            delimiter = None
        else:
            columns, rows, hint = (*read_csv(args.input, args.delimiter, args.encoding), {})
            source_format = "csv"
            delimiter = args.delimiter
        geometry = resolve_geometry(columns, hint, args.geometry_from, args.wkid)
        bounds = measure_bounds(rows, geometry["x_column"], geometry["y_column"])
        exclude = (
            (geometry["x_column"], geometry["y_column"])
            if args.drop_geometry_columns or geometry["from"] in ("geojson", "esri_featureset")
            else ()
        )
        renames: dict[str, str] = {}
        for pair in args.rename:
            if "=" not in pair:
                raise SourceError(f"--rename expects OLD=NEW, got {pair!r}")
            old_name, _, new_name = pair.partition("=")
            renames[old_name.strip()] = new_name.strip()
        declared = None if args.infer_types else (hint.get("declared_fields") or None)
        fields = build_fields(
            columns,
            rows,
            exclude=exclude,
            headroom=args.text_headroom,
            renames=renames,
            declared=declared,
        )
        feature_class = sanitize_name(
            args.feature_class or args.input.stem, limit=MAX_TABLE_NAME_LEN
        )
    except (SourceError, SchemaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not fields:
        print("error: no attribute fields left after excluding the geometry columns", file=sys.stderr)
        return 1

    contract = {
        "_comment": [
            "Schema contract - what import_to_egdb.py builds in the Enterprise Geodatabase.",
            "Generated by analyze_source.py from the source named below; safe to edit by hand,",
            "which is the point: every field carries the measurement its type was chosen from,",
            "so disagreeing with the inference does not mean re-reading the data.",
            "",
            "Types are ArcGIS field types, not PostgreSQL ones. An Enterprise Geodatabase has",
            "no boolean type, so a boolean column appears here as SHORT with the substitution",
            "recorded in its evidence block rather than applied silently.",
        ],
        "generated": {
            "tool": "analyze_source.py",
            "date": args.generated_date or date_cls.today().isoformat(),
            "geometry_from": geometry["from"],
            "text_headroom": args.text_headroom,
            "types_from": (
                "the source's own fields block, with the measurement recorded beside it"
                if declared
                else "measurement, because the source declares no schema"
                if not hint.get("declared_fields")
                else "measurement, because --infer-types overrode the declared schema"
            ),
            "renames": renames or None,
        },
        "source": {
            "path": args.input.as_posix(),
            "format": source_format,
            "encoding": args.encoding,
            "delimiter": delimiter,
            "rows": len(rows),
            "columns": len(columns),
            "bytes": len(raw_bytes),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        },
        "feature_class": {
            "name": feature_class,
            "geometry_type": "POINT",
            "has_z": False,
            "has_m": False,
        },
        "spatial_reference": {
            "wkid": geometry["wkid"],
            "decided_by": geometry["wkid_source"],
            "note": (
                "A feature class holds exactly one spatial reference, and creating it with the "
                "wrong one does not error at write time - the coordinates are simply "
                "interpreted as the wrong grid. Only a bounding-box check notices."
            ),
        },
        "geometry": {
            "from": geometry["from"],
            "x_column": geometry["x_column"],
            "y_column": geometry["y_column"],
            "source_bounds": bounds,
            "note": (
                "x_column feeds the easting/longitude and y_column the northing/latitude. "
                "The contract names them separately rather than as a pair so that an axis "
                "swap is a visible edit rather than an ordering assumption."
            ),
        },
        "name_limits": {
            "field_name_chars": MAX_FIELD_NAME_LEN,
            "table_name_chars": MAX_TABLE_NAME_LEN,
            "note": (
                "Enterprise geodatabase limits, tighter than PostgreSQL's own 63 characters. "
                "ArcGIS does not delimit object names, so a name that would need quoting - "
                "mixed case, a space, a reserved word - is a name ArcGIS cannot address even "
                "though PostgreSQL stores it."
            ),
        },
        "fields": [spec.to_json() for spec in fields],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(contract, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(f"read      {args.input} ({source_format}, {len(rows)} rows, {len(columns)} columns)")
    print(f"geometry  {geometry['y_column']} / {geometry['x_column']} -> EPSG:{geometry['wkid']}")
    print(f"           {geometry['wkid_source']}")
    print(f"fields    {len(fields)}")
    for spec in fields:
        declared = f"{spec.type}({spec.length})" if spec.length else spec.type
        rename = f"  <- {spec.source}" if spec.name != spec.source else ""
        print(f"           {spec.name:<24} {declared:<12}{rename}")
    print(f"wrote     {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
