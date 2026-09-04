#!/usr/bin/env python3
"""Check the feature class in the geodatabase against the contract and the source.

Stage three. It reads the feature class back out of PostgreSQL through arcpy
and compares it with two things: the schema contract, which says what should
have been built, and the source file, which says what the values should be. It
shares no code with `import_to_egdb.py` beyond arcpy itself - its own CSV
reader, its own field-type vocabulary (`egdb_checks.KEYWORD_OF_FIELD_TYPE`,
transcribed from Esri's documentation rather than derived from `schema.py`) - so
agreement between the two halves is evidence and not a shared assumption.

Verification depth was agreed up front at "plausible is enough" (CLAUDE.md
section 12): the data here is generated test data destined for a database, not
a published claim about the world, so this does not adjudicate individual
records the way `open_data_search` does. What it does still insist on is the
part that is cheap and catches the silent failures:

* **The spatial reference.** A feature class created with the wrong EPSG code
  relative to its actual coordinate values does not error at write time. The
  numbers go in, the geodatabase is content, and the layer draws - somewhere
  else. Nothing but a bounding box notices.

* **The axis order.** This data set makes the check matter rather than
  decorating it. NRW is latitude 50-52 and longitude 5-9, so *both* values are
  valid latitudes: a swapped load is accepted by the geodatabase without a
  murmur and lands the points around 7.5 N 51.3 E, in the Somali Sea. The
  transposed bounding box is the only thing in the pipeline that sees it.
  (Contrast the airports in
  `opensearch`, where swapping got 550 of 880 documents rejected outright by
  the engine. Nothing in the code differed - the geometry did.)

* **The values, for every feature, not a sample.** At a hundred rows a sample
  saves nothing and gives up the strongest available claim: that no coordinate
  was recomputed on the way in.

  That claim turned out to need a qualifier. Nothing in this pipeline projects
  or rounds, so "the double in the CSV is the double in the geometry" looked
  like it should hold exactly. Measured against the real geodatabase, the worst
  disagreement across 100 features is **8.53e-14 degrees - about 9.5
  nanometres**, roughly 12 ULP of the stored latitude. The round trip through an
  enterprise geodatabase is not the identity. The tolerance below is therefore
  not decoration; without it this check would fail on correct data.

Needs arcpy: run it in ArcGIS Pro's `arcgispro-py3` environment via propy.bat.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from egdb_checks import (  # noqa: E402  (path shim first)
    GEODATABASE_OWNED_TYPES,
    KEYWORD_OF_FIELD_TYPE,
    Check,
    inside,
    render_check_table,
    transpose,
)

DEFAULT_CONTRACT = Path("output/nrw_points_schema.json")
DEFAULT_SDE = Path("build/egdb.sde")

# Nothing in this pipeline projects or rounds, so the stored geometry ought to
# equal the source value bit for bit. It does not. Measured against a real
# PostgreSQL geodatabase: worst disagreement 8.53e-14 degrees across 100
# features - about 9.5 nanometres, roughly 12 ULP of the stored latitude. So a
# geodatabase round trip is not the identity, and which mechanism is responsible
# has not been established here: a geodatabase quantises geometry to the
# coordinate grid its spatial reference defines, and arcpy converts between the
# stored representation and a Python tuple, and either could account for it.
#
# The tolerance is 1e-9 degrees, about 0.1 mm - four orders of magnitude above
# what was measured and four below the 1.1 m that five decimal degrees resolves.
# **Do not tighten it to the measurement.** That is the same mistake as
# calibrating a rounding margin to one artifact (CLAUDE.md section 10): 9.5 nm on
# this spatial reference, on this release, is not a promise about the next one,
# and a check tuned that finely fails for a reason that is not an error.
COORDINATE_TOLERANCE = 1e-9


def read_source_rows(path: Path, delimiter: str | None, encoding: str) -> tuple[list[str], list[dict[str, str]]]:
    """Read the source CSV. Deliberately not `sources.read_csv`.

    Eleven lines, and they buy independence: the comparison below is then
    between the geodatabase and the file, rather than between the geodatabase
    and a second call to the same reader the loader used.
    """
    text = path.read_text(encoding=encoding)
    if delimiter is None:
        delimiter = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|").delimiter
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    rows = [dict(row) for row in reader]
    return list(reader.fieldnames or []), rows


def pick_key_field(contract: dict[str, Any], override: str | None) -> str:
    """A field that identifies a row, so geometry can be matched to its source.

    Refuses to invent one. CLAUDE.md section 4: an identifier column is not an
    identifier - `objectid` and `ESRI_OID` in one export were both 1..N, both
    unique, and equal in zero rows. So the key has to be a field the *contract*
    measured as unique and complete, or one the caller names explicitly.
    """
    if override:
        for field in contract["fields"]:
            if field["name"] == override:
                return override
        raise SystemExit(f"error: --key-field {override!r} is not a field in the contract")
    for field in contract["fields"]:
        evidence = field.get("evidence", {})
        if evidence.get("distinct") == evidence.get("rows") and evidence.get("nulls") == 0:
            return field["name"]
    raise SystemExit(
        "error: no field in the contract was measured as unique and non-null, so rows cannot "
        "be matched to their source. Pass --key-field explicitly."
    )


def resolve_feature_class(
    sde: Path, name: str, database: str | None, schema: str | None
) -> tuple[str, str]:
    """Find the feature class in the geodatabase instead of guessing its name.

    An enterprise geodatabase addresses objects as `database.schema.table`, and
    the schema is not derivable from anything this script is told: it is the
    schema of the login the connection was made with. The first version of this
    code defaulted it to the database name, which produced
    `agsdb.agsdb.nrw_points` against a real `agsdb.sde.nrw_points` and an error
    that named the dataset rather than the guess - "Dataset ... does not exist
    or is not supported", pointing at the data when the fault was in the path.

    So it is looked up. `--database` and `--schema` remain as filters for the
    case where the same table name appears in more than one schema, which is the
    only case where a human has to decide. Returns `(path, qualified_name)`.
    """
    import arcpy  # noqa: PLC0415

    sde_path = str(sde)

    if database and schema:
        qualified = f"{database}.{schema}.{name}".lower()
        candidate = str(Path(sde_path) / qualified)
        if arcpy.Exists(candidate):
            return candidate, qualified
        raise SystemExit(
            f"error: {qualified} does not exist in {sde_path}.\n"
            f"       Present: {', '.join(_list_feature_classes(sde_path)) or '(none)'}"
        )

    found = _list_feature_classes(sde_path)
    matches = [f for f in found if f.split(".")[-1].lower() == name.lower()]
    if database:
        matches = [f for f in matches if f.split(".")[0].lower() == database.lower()]
    if schema:
        matches = [f for f in matches if f.split(".")[-2].lower() == schema.lower()]

    if len(matches) == 1:
        return str(Path(sde_path) / matches[0]), matches[0]
    if not matches:
        raise SystemExit(
            f"error: no feature class called {name!r} in {sde_path}.\n"
            f"       Present: {', '.join(found) or '(none)'}\n"
            "       Load it first with import_to_egdb.py, or check --sde."
        )
    raise SystemExit(
        f"error: {name!r} exists in more than one schema: {', '.join(matches)}.\n"
        "       Pass --database and --schema to say which one."
    )


def _list_feature_classes(sde_path: str) -> list[str]:
    """Every feature class the connection can see, as qualified names."""
    import arcpy  # noqa: PLC0415

    previous = arcpy.env.workspace
    try:
        arcpy.env.workspace = sde_path
        return sorted(arcpy.ListFeatureClasses() or [])
    except Exception:  # pragma: no cover - environment dependent
        return []
    finally:
        arcpy.env.workspace = previous


def verify(
    fc_path: str,
    contract: dict[str, Any],
    source_path: Path,
    key_field: str,
) -> list[Check]:
    import arcpy  # noqa: PLC0415

    checks: list[Check] = []
    declared = {f["name"]: f for f in contract["fields"]}
    geometry = contract["geometry"]
    expected_wkid = contract["spatial_reference"]["wkid"]
    source_columns, source_rows = read_source_rows(
        source_path, contract["source"]["delimiter"], contract["source"]["encoding"]
    )
    key_source = declared[key_field]["source"]
    by_key = {row[key_source]: row for row in source_rows}

    # 1 - document count
    count = int(arcpy.management.GetCount(fc_path)[0])
    expected_count = len(source_rows)
    checks.append(
        Check(
            "Feature count matches the source",
            count == expected_count,
            f"{count} features, {expected_count} rows in `{source_path.name}`",
        )
    )

    described = arcpy.Describe(fc_path)
    fields = {f.name.lower(): f for f in arcpy.ListFields(fc_path)}

    # 2 - every declared field exists with the declared type and length
    problems: list[str] = []
    for name, field in declared.items():
        found = fields.get(name.lower())
        if found is None:
            problems.append(f"`{name}` missing")
            continue
        keyword = KEYWORD_OF_FIELD_TYPE.get(found.type, found.type)
        if keyword != field["type"]:
            problems.append(f"`{name}` is {found.type} ({keyword}), contract says {field['type']}")
        if field.get("length") is not None and found.length != field["length"]:
            problems.append(f"`{name}` length {found.length}, contract says {field['length']}")
    checks.append(
        Check(
            "Field types and lengths match the contract",
            not problems,
            "; ".join(problems) if problems else f"all {len(declared)} declared fields agree",
        )
    )

    # 3 - nothing beyond the declared fields and the geodatabase's own two
    extra = [
        f.name
        for f in fields.values()
        if f.name.lower() not in {n.lower() for n in declared}
        and f.type not in GEODATABASE_OWNED_TYPES
    ]
    owned = sorted(f.name for f in fields.values() if f.type in GEODATABASE_OWNED_TYPES)
    checks.append(
        Check(
            "No unexpected fields",
            not extra,
            (
                f"geodatabase-managed: {', '.join(owned)}"
                if not extra
                else f"unexpected: {', '.join(extra)}"
            ),
        )
    )

    # 4 - spatial reference
    actual_wkid = described.spatialReference.factoryCode
    checks.append(
        Check(
            "Spatial reference is the one the contract names",
            actual_wkid == expected_wkid,
            (
                f"EPSG:{actual_wkid} (`{described.spatialReference.name}`), contract says "
                f"EPSG:{expected_wkid}. A wrong code here does not error at write time."
            ),
        )
    )

    # Read everything back once; checks 5-8 all work off this.
    stored: dict[str, tuple[float, float, dict[str, Any]]] = {}
    attribute_names = [n for n in declared if n != key_field]
    cursor_fields = ["SHAPE@XY", key_field] + attribute_names
    with arcpy.da.SearchCursor(fc_path, cursor_fields) as reader:
        for row in reader:
            (x, y) = row[0]
            key = row[1]
            stored[str(key)] = (x, y, dict(zip(attribute_names, row[2:])))

    xs = [v[0] for v in stored.values()]
    ys = [v[1] for v in stored.values()]
    actual_box = {"x_min": min(xs), "x_max": max(xs), "y_min": min(ys), "y_max": max(ys)}
    expected_box = geometry["source_bounds"]

    # 5 - extent equals the source's own measured extent
    deltas = [abs(actual_box[k] - expected_box[k]) for k in actual_box]
    checks.append(
        Check(
            "Extent equals the source's measured extent",
            max(deltas) <= COORDINATE_TOLERANCE,
            (
                f"x {actual_box['x_min']:.5f}..{actual_box['x_max']:.5f}, "
                f"y {actual_box['y_min']:.5f}..{actual_box['y_max']:.5f}; "
                f"largest disagreement with the source {max(deltas):.2e} degrees"
            ),
        )
    )

    # 6 - the transposed box must match nothing
    swapped = transpose(expected_box)
    if swapped is None:
        checks.append(
            Check(
                "Transposed bounding box matches nothing",
                None,
                (
                    "the transposed box is not a valid box, so the check cannot be posed - "
                    "reported rather than counted as a pass"
                ),
            )
        )
    else:
        hits = sum(1 for (x, y, _) in stored.values() if inside(x, y, swapped))
        checks.append(
            Check(
                "Transposed bounding box matches nothing",
                hits == 0,
                (
                    f"{hits} of {len(stored)} features inside x "
                    f"{swapped['x_min']:.3f}..{swapped['x_max']:.3f}, y "
                    f"{swapped['y_min']:.3f}..{swapped['y_max']:.3f}. This is the only check "
                    "that sees an axis swap here: both NRW coordinate ranges are valid "
                    "latitudes, so the geodatabase accepts a swapped load without complaint "
                    "and puts every point in the Somali Sea at a perfectly valid coordinate."
                ),
            )
        )

    # 7 - every geometry equals its source coordinate pair
    missing_keys = sorted(set(by_key) - set(stored))
    worst = 0.0
    worst_key = ""
    for key, (x, y, _) in stored.items():
        source = by_key.get(key)
        if source is None:
            missing_keys.append(key)
            continue
        for value, column in ((x, geometry["x_column"]), (y, geometry["y_column"])):
            delta = abs(value - float(source[column]))
            if delta > worst:
                worst, worst_key = delta, key
    checks.append(
        Check(
            "Every geometry equals its source coordinate pair",
            not missing_keys and worst <= COORDINATE_TOLERANCE,
            (
                f"{len(stored)} features matched on `{key_field}`; worst disagreement "
                f"{worst:.2e} degrees (`{worst_key}`). Nothing is projected or rounded in this "
                "pipeline, so the comparison is exact rather than tolerant."
                + (f" Unmatched keys: {missing_keys[:5]}" if missing_keys else "")
            ),
        )
    )

    # 8 - the coordinate pair that did not become geometry survived as attributes
    carried = [n for n in ("x_3857", "y_3857") if n in declared]
    if not carried:
        checks.append(
            Check(
                "The second coordinate pair survived as attributes",
                None,
                "the source carried only one coordinate pair, so there is nothing to carry",
            )
        )
    else:
        wrong: list[str] = []
        for key, (_, _, attributes) in stored.items():
            source = by_key.get(key)
            if source is None:
                continue
            for name in carried:
                expected = float(source[declared[name]["source"]])
                if abs(attributes[name] - expected) > 1e-6:
                    wrong.append(f"{key}.{name}: {attributes[name]} != {expected}")
        checks.append(
            Check(
                "The second coordinate pair survived as attributes",
                not wrong,
                (
                    f"{', '.join(carried)} agree with the source in all {len(stored)} features"
                    if not wrong
                    else "; ".join(wrong[:5])
                ),
            )
        )

    # Informational: the boolean substitution is invisible in the attribute table
    booleans = [
        name for name, f in declared.items() if f.get("evidence", {}).get("boolean_as_short")
    ]
    if booleans:
        checks.append(
            Check(
                "Boolean columns are SHORT, and the table cannot say so",
                None,
                (
                    f"{', '.join('`' + b + '`' for b in booleans)} held true/false in the source "
                    "and hold 1/0 here, because an Enterprise Geodatabase has no boolean type. "
                    "The attribute table shows a number with no way to indicate what it was."
                ),
            )
        )

    checks.append(
        Check(
            "Field name limit",
            None,
            (
                "the longest declared field name is "
                f"{max(len(n) for n in declared)} characters against the geodatabase's limit of "
                f"{contract['name_limits']['field_name_chars']}. PostgreSQL itself allows 63, so "
                "a name between 32 and 63 would be stored by the database and unaddressable "
                "through ArcGIS."
            ),
        )
    )

    return checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_featureclass.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Read the feature class back out of the Enterprise Geodatabase and check it "
            "against the schema contract and the source file. Needs arcpy."
        ),
        epilog=(
            "Example, on the Windows machine:\n"
            "\n"
            "  propy scripts\\verify_featureclass.py `\n"
            "      --contract output\\nrw_points_schema.json `\n"
            "      --sde build\\egdb.sde `\n"
            "      --report output\\verification_report.md\n"
            "\n"
            "The feature class is looked up in the connection, so --database and --schema are\n"
            "only needed when the same table name exists in more than one schema.\n"
            "\n"
            "--report has no default on purpose: a verifier whose output path is convenient\n"
            "is a verifier that overwrites the wrong report (CLAUDE.md section 4).\n"
        ),
    )
    parser.add_argument(
        "--contract",
        metavar="PATH",
        type=Path,
        default=DEFAULT_CONTRACT,
        help="schema contract the feature class was built from (default: %(default)s)",
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        type=Path,
        default=None,
        help="source data file (default: the path recorded in the contract)",
    )
    parser.add_argument(
        "--sde",
        metavar="PATH",
        type=Path,
        default=DEFAULT_SDE,
        help="database connection file written by import_to_egdb.py (default: %(default)s)",
    )
    parser.add_argument(
        "--database",
        metavar="NAME",
        default=None,
        help=(
            "database name. Optional: the feature class is looked up in the connection rather "
            "than addressed by a guessed name. Only needed to disambiguate."
        ),
    )
    parser.add_argument(
        "--schema",
        metavar="NAME",
        default=None,
        help=(
            "schema holding the feature class. Optional, same reason as --database - the schema "
            "is the connecting login's and cannot be derived from anything passed here."
        ),
    )
    parser.add_argument(
        "--key-field",
        metavar="NAME",
        default=None,
        help=(
            "field used to match a feature to its source row (default: the first field the "
            "contract measured as unique and non-null)"
        ),
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        type=Path,
        required=True,
        help="write the Markdown report here. Required: there is no default.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    source_path = args.source or Path(contract["source"]["path"])
    key_field = pick_key_field(contract, args.key_field)
    if not args.sde.exists():
        raise SystemExit(
            f"error: connection file not found: {args.sde}. Run import_to_egdb.py first, or "
            "pass --sde."
        )
    fc_path, qualified = resolve_feature_class(
        args.sde, contract["feature_class"]["name"], args.database, args.schema
    )
    print(f"resolved  {qualified}")

    checks = verify(fc_path, contract, source_path, key_field)
    failures = [c for c in checks if c.passed is False]

    lines = [
        f"# Verification: `{qualified}`",
        "",
        f"Feature class read back from the Enterprise Geodatabase via `{args.sde}` and compared",
        f"against `{args.contract}` and `{source_path}`.",
        "",
        f"Verification depth: **plausible is enough** (agreed up front, CLAUDE.md section 12).",
        f"Rows matched on `{key_field}`.",
        "",
        f"**{len(checks) - len(failures)} of {len(checks)} checks passed"
        f"{', all green' if not failures else f', {len(failures)} FAILED'}.**",
        "",
        *render_check_table(checks),
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))

    for check in checks:
        print(f"{check.verdict:<8} {check.name}")
        print(f"         {check.detail}")
    print(f"\nreport -> {args.report}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
