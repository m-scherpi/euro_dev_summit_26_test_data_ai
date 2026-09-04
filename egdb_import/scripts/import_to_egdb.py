#!/usr/bin/env python3
"""Build a feature class in a PostgreSQL Enterprise Geodatabase and load it.

Stage two of three. This is the half that needs Windows and a licensed ArcGIS
Pro, and it does as little thinking as possible: every decision it acts on was
already made and written down by `analyze_source.py`, in a JSON contract a
human can read. What is left here is transcription - open a connection, create
the feature class, add the fields the contract names with the types and lengths
the contract states, insert the rows.

**Why arcpy and not the ArcGIS API for Python.** The use case was asked for
"using the ArcGIS API for Python", and that API cannot do this. The `arcgis`
package is a REST client for a portal; it has no database connectivity at all,
no SDE connection object and no equivalent of `arcpy.da`. The two routes that
look closest both fail by succeeding:

* `GIS.content.import_data()` returns a working feature layer - *hosted*, in
  the ArcGIS Data Store. It copies the data out of the database, which is the
  opposite of the goal.
* `DataFrame.spatial.to_featureclass()` accepts a path and, without arcpy in
  the interpreter, writes a **shapefile** instead. Esri's own guide: "Writing
  to file geodatabases requires the ArcPy site-package." Same call, same
  arguments, a different format on disk, no error.

`try_arcgis_api.py` in this folder runs both and records what came back. The
lesson is the `opensearch` lesson sharpened: the loud error is the harmless one.

**What this script does not do.** It does not project, convert, round or
recompute a single coordinate. The value in the source file is the value handed
to `SHAPE@XY`, as the same double. That is the strongest provenance claim
available - "nothing was recomputed" - and it is available here only because
the contract insisted the feature class be created in the CRS the source
already carries rather than a convenient one.

Note the boundary of that claim, because it is narrower than it looks: it covers
everything up to and including the call. What comes back *out* of the
geodatabase is not bit-identical - measured at 9.5 nanometres worst case across
100 features, see `verify_featureclass.py`. Nothing here rounds; the storage
does.

`--dry-run` writes the exact call sequence, with every argument, to a Markdown
file **without importing arcpy**, so the pipeline is reviewable and its artifact
is committed from a machine that has no ArcGIS at all. The password is redacted
there; it is the one argument that never appears.

Stdlib only for `--dry-run`. A real run needs arcpy, which means ArcGIS Pro's
bundled `arcgispro-py3` environment - invoke it through `propy.bat`, not a venv.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import is_absent  # noqa: E402  (path shim has to come first)
from sources import SourceError, read_csv, read_json  # noqa: E402

DEFAULT_CONTRACT = Path("output/nrw_points_schema.json")
DEFAULT_PLAN = Path("output/nrw_points_arcpy_plan.md")
DEFAULT_CONNECTION = Path("input/egdb_connection.example.json")
DEFAULT_SDE_DIR = Path("build")
DEFAULT_SDE_NAME = "egdb.sde"

PASSWORD_ENV = "EGDB_PASSWORD"
REDACTED = "<EGDB_PASSWORD>"

# Values the geodatabase manages; the loader never supplies them.
TRUE_LITERALS = {"true", "t", "yes", "y", "1"}
FALSE_LITERALS = {"false", "f", "no", "n", "0"}


class ImportError_(Exception):
    """A refusal to write something the contract does not justify."""


@dataclass
class Step:
    """One arcpy call, recorded before it runs so it can be reviewed or printed."""

    label: str
    target: str
    args: list[tuple[str, Any]]
    note: str = ""
    secret: frozenset[str] = dataclass_field(default_factory=frozenset)

    def rendered_args(self) -> list[tuple[str, str]]:
        out = []
        for name, value in self.args:
            out.append((name, REDACTED if name in self.secret else repr(value)))
        return out

    def render(self) -> str:
        lines = [f"{self.target}("]
        for name, value in self.rendered_args():
            lines.append(f"    {name}={value},")
        lines.append(")")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------


def coerce_value(raw: Any, field: dict[str, Any], row_index: int) -> Any:
    """Turn one source value into what the declared field type accepts.

    Every refusal here is a refusal to write something that would look right.
    A TEXT value longer than the declared length is the clearest case: left to
    the database it is either an error at insert time or, worse, a truncation,
    and a description silently cut off at 120 characters is indistinguishable
    from a description that was always that long.
    """
    name = field["name"]
    esri_type = field["type"]
    if is_absent(raw):
        if not field.get("nullable", True):
            raise ImportError_(
                f"row {row_index}: field {name!r} is empty but the contract declares it "
                "non-nullable. Either the source changed since the contract was written or "
                "the contract needs regenerating."
            )
        return None

    text = raw if isinstance(raw, str) else str(raw)

    if esri_type == "TEXT":
        # Written verbatim, never stripped. A value of `" "` is what the source
        # stores - 1,343 of them across three columns of the airports export -
        # and trimming it to `""` or to NULL is a silent edit to somebody
        # else's data (CLAUDE.md section 4).
        limit = field.get("length")
        if limit is not None and len(text) > limit:
            raise ImportError_(
                f"row {row_index}: field {name!r} holds {len(text)} characters but the contract "
                f"declares TEXT({limit}). Regenerate the contract - a longer value has appeared "
                "since it was measured - or raise --text-headroom. Truncating here would produce "
                "a value that looks complete."
            )
        return text

    if esri_type == "SHORT" and field.get("evidence", {}).get("boolean_as_short"):
        lowered = text.strip().lower()
        if lowered in TRUE_LITERALS:
            return 1
        if lowered in FALSE_LITERALS:
            return 0
        raise ImportError_(
            f"row {row_index}: field {name!r} was measured as a boolean column and holds "
            f"{text!r}, which is neither true nor false. The contract's SHORT substitution "
            "does not cover it."
        )

    if esri_type in ("SHORT", "LONG"):
        try:
            return int(text.strip())
        except ValueError as exc:
            raise ImportError_(
                f"row {row_index}: field {name!r} is declared {esri_type} and holds {text!r}"
            ) from exc

    if esri_type in ("DOUBLE", "FLOAT"):
        try:
            return float(text.strip())
        except ValueError as exc:
            raise ImportError_(
                f"row {row_index}: field {name!r} is declared {esri_type} and holds {text!r}"
            ) from exc

    if esri_type == "DATE":
        try:
            return datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise ImportError_(
                f"row {row_index}: field {name!r} is declared DATE and holds {text!r}, which is "
                "not ISO 8601"
            ) from exc

    raise ImportError_(f"field {name!r} has unsupported contract type {esri_type!r}")


def coerce_geometry(row: dict[str, Any], contract: dict[str, Any], row_index: int) -> tuple[float, float]:
    """The coordinate pair, as floats, unmodified.

    Nothing is projected or rounded. `SHAPE@XY` takes (x, y) - easting first -
    and the contract names the two columns separately precisely so that this
    line cannot quietly become (y, x).
    """
    geometry = contract["geometry"]
    try:
        return float(row[geometry["x_column"]]), float(row[geometry["y_column"]])
    except (KeyError, TypeError, ValueError) as exc:
        raise ImportError_(
            f"row {row_index}: coordinate columns {geometry['x_column']}/"
            f"{geometry['y_column']} do not both hold a number"
        ) from exc


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


def qualified_name(database: str, schema: str, feature_class: str) -> str:
    """`database.schema.table`, lowercase, as ArcGIS will address it."""
    return f"{database}.{schema}.{feature_class}".lower()


def build_plan(
    contract: dict[str, Any], connection: dict[str, Any], sde_dir: Path, sde_name: str, overwrite: bool
) -> list[Step]:
    feature_class = contract["feature_class"]["name"]
    wkid = contract["spatial_reference"]["wkid"]
    schema = connection.get("schema") or connection["username"]
    qualified = qualified_name(connection["database"], schema, feature_class)
    sde_path = (sde_dir / sde_name).as_posix()
    fc_path = f"{sde_path}/{qualified}"

    steps = [
        Step(
            label="Create the database connection file",
            target="arcpy.management.CreateDatabaseConnection",
            args=[
                ("out_folder_path", sde_dir.as_posix()),
                ("out_name", sde_name),
                ("database_platform", "POSTGRESQL"),
                ("instance", connection["instance"]),
                ("account_authentication", "DATABASE_AUTH"),
                ("username", connection["username"]),
                ("password", REDACTED),
                ("save_user_pass", "SAVE_USERNAME"),
                ("database", connection["database"].lower()),
                ("schema", connection.get("schema") or "#"),
                ("version_type", connection.get("version_type", "TRANSACTIONAL")),
            ],
            secret=frozenset({"password"}),
            note=(
                "`database` is required for PostgreSQL - unlike SQL Server, where it may be "
                "blank - and must be lowercase, because PostgreSQL folds unquoted identifiers "
                "and ArcGIS never quotes them. `SAVE_USERNAME` is not a convenience: ArcGIS Pro "
                "can hang opening a geodatabase from a connection file whose credentials were "
                "not saved. It is also why the resulting file goes to `build/` and is "
                "gitignored - it carries the credentials."
            ),
        ),
        Step(
            label="Create the feature class",
            target="arcpy.management.CreateFeatureclass",
            args=[
                ("out_path", sde_path),
                ("out_name", feature_class),
                ("geometry_type", contract["feature_class"]["geometry_type"]),
                ("has_m", "DISABLED" if not contract["feature_class"]["has_m"] else "ENABLED"),
                ("has_z", "DISABLED" if not contract["feature_class"]["has_z"] else "ENABLED"),
                ("spatial_reference", f"arcpy.SpatialReference({wkid})"),
            ],
            note=(
                f"EPSG:{wkid}, decided by: {contract['spatial_reference']['decided_by']} "
                "Creating a feature class through this tool registers it with the geodatabase, "
                "so the result is a real feature class rather than an unregistered table - "
                "which ArcGIS could only treat as a query layer, with a hand-supplied SRID and "
                "an ObjectID invented per session."
            ),
        ),
    ]

    for field in contract["fields"]:
        args: list[tuple[str, Any]] = [
            ("in_table", fc_path),
            ("field_name", field["name"]),
            ("field_type", field["type"]),
        ]
        if field.get("length") is not None:
            args.append(("field_length", field["length"]))
        args.append(
            ("field_is_nullable", "NULLABLE" if field.get("nullable", True) else "NON_NULLABLE")
        )
        note = field.get("evidence", {}).get("note", "")
        steps.append(
            Step(
                label=f"Add field {field['name']}",
                target="arcpy.management.AddField",
                args=args,
                note=note,
            )
        )

    steps.append(
        Step(
            label="Insert the rows",
            target="arcpy.da.InsertCursor",
            args=[
                ("in_table", fc_path),
                ("field_names", ["SHAPE@XY"] + [f["name"] for f in contract["fields"]]),
            ],
            note=(
                f"{contract['source']['rows']} rows from {contract['source']['path']}. "
                "`SHAPE@XY` takes (x, y): "
                f"x from {contract['geometry']['x_column']}, y from "
                f"{contract['geometry']['y_column']}. No projection, no rounding - the double in "
                "the source file is the double handed to the cursor."
            ),
        )
    )
    if overwrite:
        steps.insert(
            1,
            Step(
                label="Delete the existing feature class (--overwrite)",
                target="arcpy.management.Delete",
                args=[("in_data", fc_path)],
                note="Only reached when --overwrite was passed and the feature class exists.",
            ),
        )
    return steps


def render_plan(
    steps: list[Step],
    contract: dict[str, Any],
    connection: dict[str, Any],
    rehearsal: dict[str, Any] | None = None,
) -> str:
    source = contract["source"]
    lines = [
        f"# arcpy plan for `{contract['feature_class']['name']}`",
        "",
        "Generated by `import_to_egdb.py --dry-run`. This is the exact sequence of arcpy",
        "calls a real run makes, with every argument, produced **without importing arcpy** -",
        "so it is reviewable, and committable, from a machine that has no ArcGIS installed.",
        "",
        f"The password is never printed. It is read from `${PASSWORD_ENV}` or `--password`",
        "at run time and appears here only as a placeholder.",
        "",
        "## Source",
        "",
        f"| | |",
        f"|---|---|",
        f"| File | `{source['path']}` |",
        f"| Format | {source['format']} |",
        f"| Rows | {source['rows']} |",
        f"| SHA-256 | `{source['sha256']}` |",
        f"| Contract written | {contract['generated']['date']} |",
        "",
        "## Target",
        "",
        f"| | |",
        f"|---|---|",
        f"| Platform | PostgreSQL Enterprise Geodatabase |",
        f"| Instance | `{connection['instance']}` |",
        f"| Database | `{connection['database'].lower()}` |",
        f"| Login | `{connection['username']}` |",
        f"| Feature class | `{contract['feature_class']['name']}` |",
        f"| Spatial reference | EPSG:{contract['spatial_reference']['wkid']} |",
        "",
    ]
    if rehearsal is not None:
        lines += [
            "## Rehearsal",
            "",
            "Every row was coerced to its declared field type here, without a database. So this",
            "dry run is a check rather than a printout: a text value longer than the contract's",
            "declared length, a boolean column with a third value, or a non-numeric coordinate",
            "aborts on a laptop instead of part-way through an insert against a real geodatabase.",
            "",
            f"**{rehearsal['rows']} rows coerced without error.**",
            "",
        ]
        if rehearsal.get("text_headroom_left"):
            lines += [
                "| TEXT field | Declared | Widest value | Headroom left |",
                "|---|---|---|---|",
            ]
            for name, info in rehearsal["text_headroom_left"].items():
                spare = info["declared"] - info["widest_value"]
                lines.append(
                    f"| `{name}` | {info['declared']} | {info['widest_value']} | {spare} |"
                )
            lines.append("")
    lines += [
        "## Calls",
        "",
    ]
    for index, step in enumerate(steps, start=1):
        lines.append(f"### {index}. {step.label}")
        lines.append("")
        lines.append("```python")
        lines.append(step.render())
        lines.append("```")
        if step.note:
            lines.append("")
            lines.append(step.note)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def rehearse(contract: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Coerce every row without a database, so --dry-run is a check and not a printout.

    This is the half of the loader that does not need arcpy, and running it
    early is worth more than it looks: a TEXT value longer than the contract's
    declared length, a boolean column that has acquired a third value, a
    non-numeric coordinate - all of them abort here, on a laptop, rather than
    part-way through an insert against a real geodatabase.
    """
    summary: dict[str, Any] = {"rows": len(rows)}
    widest: dict[str, int] = {}
    for index, row in enumerate(rows):
        coerce_geometry(row, contract, index)
        for field in contract["fields"]:
            value = coerce_value(row.get(field["source"]), field, index)
            if field["type"] == "TEXT" and value is not None:
                widest[field["name"]] = max(widest.get(field["name"], 0), len(value))
    summary["text_headroom_left"] = {
        name: {
            "declared": next(f["length"] for f in contract["fields"] if f["name"] == name),
            "widest_value": width,
        }
        for name, width in sorted(widest.items())
    }
    return summary


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def preflight(sde_path: str, requirements: dict[str, Any] | None) -> list[str]:
    """Report what the machine actually is, next to what the docs claim it should be.

    Three of the numbers in `input/egdb_requirements.json` could not be verified
    from a fetchable Esri page while this use case was built - the Python
    version in Pro 3.7, the bundled `arcgis` version, and the certified
    PostgreSQL/PostGIS pairing for 12.1. So the claim is recorded with its
    status and the machine is asked directly. A documented requirement and a
    running instance are two different facts, and only one of them is here.
    """
    import arcpy  # noqa: PLC0415  (a dry run must not need it)

    lines: list[str] = []
    info = arcpy.GetInstallInfo()
    lines.append(f"product          {info.get('ProductName')} {info.get('Version')} (build {info.get('BuildNumber')})")
    lines.append(f"licence          {arcpy.ProductInfo()}")
    lines.append(f"python           {sys.version.split()[0]} ({sys.executable})")
    try:
        import arcgis  # noqa: PLC0415

        lines.append(f"arcgis package   {arcgis.__version__}")
    except Exception as exc:  # pragma: no cover - environment dependent
        lines.append(f"arcgis package   not importable ({exc.__class__.__name__})")

    if requirements:
        python_claim = requirements.get("python", {})
        lines.append(
            f"claimed          Python {python_claim.get('claimed_pro_37')} / arcgis "
            f"{python_claim.get('claimed_arcgis_package')} - {python_claim.get('verification_status', '')[:60]}..."
        )

    try:
        executor = arcpy.ArcSDESQLExecute(sde_path)
        server_version = executor.execute("select version()")
        lines.append(f"postgresql       {server_version}")
        for probe, label in (
            ("select postgis_full_version()", "postgis"),
            ("select sde.st_geometry_version()", "st_geometry"),
        ):
            try:
                lines.append(f"{label:<16} {executor.execute(probe)}")
            except Exception:
                lines.append(f"{label:<16} not present")
    except Exception as exc:  # pragma: no cover - environment dependent
        lines.append(f"server probe     failed: {exc}")

    return lines


def execute(
    steps: list[Step],
    contract: dict[str, Any],
    connection: dict[str, Any],
    password: str,
    rows: list[dict[str, Any]],
    sde_dir: Path,
    sde_name: str,
    overwrite: bool,
    requirements: dict[str, Any] | None,
) -> int:
    import arcpy  # noqa: PLC0415

    feature_class = contract["feature_class"]["name"]
    schema = connection.get("schema") or connection["username"]
    qualified = qualified_name(connection["database"], schema, feature_class)

    sde_dir.mkdir(parents=True, exist_ok=True)
    sde_file = sde_dir / sde_name
    if sde_file.exists():
        sde_file.unlink()

    print("creating connection file ...")
    arcpy.management.CreateDatabaseConnection(
        str(sde_dir),
        sde_name,
        "POSTGRESQL",
        connection["instance"],
        "DATABASE_AUTH",
        connection["username"],
        password,
        "SAVE_USERNAME",
        connection["database"].lower(),
        connection.get("schema") or "#",
        connection.get("version_type", "TRANSACTIONAL"),
    )
    sde_path = str(sde_file)

    for line in preflight(sde_path, requirements):
        print(f"  {line}")

    fc_path = str(Path(sde_path) / qualified)

    if arcpy.Exists(fc_path):
        if not overwrite:
            print(
                f"error: {qualified} already exists. Pass --overwrite to replace it.",
                file=sys.stderr,
            )
            return 1
        print(f"deleting existing {qualified} ...")
        arcpy.management.Delete(fc_path)

    print(f"creating feature class {qualified} in EPSG:{contract['spatial_reference']['wkid']} ...")
    arcpy.management.CreateFeatureclass(
        sde_path,
        feature_class,
        contract["feature_class"]["geometry_type"],
        None,
        "DISABLED" if not contract["feature_class"]["has_m"] else "ENABLED",
        "DISABLED" if not contract["feature_class"]["has_z"] else "ENABLED",
        arcpy.SpatialReference(contract["spatial_reference"]["wkid"]),
    )

    for field in contract["fields"]:
        print(f"  add field {field['name']} {field['type']}"
              + (f"({field['length']})" if field.get("length") else ""))
        arcpy.management.AddField(
            fc_path,
            field["name"],
            field["type"],
            None,
            None,
            field.get("length"),
            None,
            "NULLABLE" if field.get("nullable", True) else "NON_NULLABLE",
        )

    field_names = ["SHAPE@XY"] + [f["name"] for f in contract["fields"]]
    print(f"inserting {len(rows)} rows ...")
    with arcpy.da.InsertCursor(fc_path, field_names) as cursor:
        for index, row in enumerate(rows):
            values: list[Any] = [coerce_geometry(row, contract, index)]
            for field in contract["fields"]:
                values.append(coerce_value(row.get(field["source"]), field, index))
            cursor.insertRow(values)

    count = int(arcpy.management.GetCount(fc_path)[0])
    print(f"done. {count} features in {qualified}")
    if count != len(rows):
        print(
            f"error: inserted {len(rows)} rows but the feature class reports {count}",
            file=sys.stderr,
        )
        return 1
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_connection(path: Path | None, args: argparse.Namespace) -> dict[str, Any]:
    connection: dict[str, Any] = {}
    if path is not None:
        if not path.is_file():
            raise ImportError_(f"connection file not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        connection = {k: v for k, v in raw.items() if not k.startswith("_")}
    for key in ("instance", "database", "username", "schema", "version_type"):
        override = getattr(args, key, None)
        if override is not None:
            connection[key] = override
    missing = [k for k in ("instance", "database", "username") if not connection.get(k)]
    if missing:
        raise ImportError_(
            f"connection is missing {', '.join(missing)}. Supply them in --connection or as flags."
        )
    return connection


def load_rows(path: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    """Read the source rows the way the contract says the file is shaped."""
    if path.suffix.lower() in (".json", ".geojson"):
        _, rows, _ = read_json(path, contract["source"]["encoding"])
        return rows
    _, rows = read_csv(path, contract["source"]["delimiter"], contract["source"]["encoding"])
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="import_to_egdb.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Create the feature class a schema contract describes in a PostgreSQL Enterprise "
            "Geodatabase and load the source rows into it. Needs arcpy for a real run; "
            "--dry-run needs nothing but the standard library."
        ),
        epilog=(
            "Dry run - what the committed artifact was produced by, from any machine:\n"
            "\n"
            "  cd egdb_import\n"
            "  python3 scripts/import_to_egdb.py --dry-run \\\n"
            "      --contract output/nrw_points_schema.json \\\n"
            "      --connection input/egdb_connection.example.json \\\n"
            "      --plan output/nrw_points_arcpy_plan.md\n"
            "\n"
            "Real run, on the Windows machine, in ArcGIS Pro's own Python:\n"
            "\n"
            "  set EGDB_PASSWORD=...\n"
            "  \"%PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\Scripts\\propy\" ^\n"
            "      scripts\\import_to_egdb.py ^\n"
            "      --contract output\\nrw_points_schema.json ^\n"
            "      --instance 127.0.0.1 --database devsummit --username devsummit ^\n"
            "      --overwrite\n"
            "\n"
            "The password is never a flag default and never read from a file in the\n"
            "repository. It comes from $EGDB_PASSWORD or --password, nowhere else.\n"
        ),
    )
    parser.add_argument(
        "--contract",
        metavar="PATH",
        type=Path,
        default=DEFAULT_CONTRACT,
        help="schema contract written by analyze_source.py (default: %(default)s)",
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        type=Path,
        default=None,
        help="source data file (default: the path recorded in the contract)",
    )
    parser.add_argument(
        "--connection",
        metavar="PATH",
        type=Path,
        default=DEFAULT_CONNECTION,
        help="connection template; individual flags override it (default: %(default)s)",
    )
    parser.add_argument("--instance", metavar="HOST", default=None, help="PostgreSQL host")
    parser.add_argument("--database", metavar="NAME", default=None, help="database name (lowercase)")
    parser.add_argument("--username", metavar="NAME", default=None, help="data owner login")
    parser.add_argument("--schema", metavar="NAME", default=None, help="schema (default: the user's own)")
    parser.add_argument(
        "--version-type",
        metavar="TYPE",
        default=None,
        choices=("TRANSACTIONAL", "HISTORICAL", "POINT_IN_TIME", "BRANCH"),
        help="geodatabase version type (default: TRANSACTIONAL)",
    )
    parser.add_argument(
        "--password",
        metavar="VALUE",
        default=None,
        help=f"database password; defaults to ${PASSWORD_ENV}. Never stored in this repository.",
    )
    parser.add_argument(
        "--sde-dir",
        metavar="PATH",
        type=Path,
        default=DEFAULT_SDE_DIR,
        help=(
            "where to write the .sde connection file. Default %(default)s, which is gitignored - "
            "the file carries saved credentials."
        ),
    )
    parser.add_argument(
        "--sde-name", metavar="NAME", default=DEFAULT_SDE_NAME, help="connection file name (default: %(default)s)"
    )
    parser.add_argument(
        "--requirements",
        metavar="PATH",
        type=Path,
        default=Path("input/egdb_requirements.json"),
        help="claimed client/DBMS requirements, reported next to the measured ones (default: %(default)s)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="delete the feature class first if it already exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "write the arcpy call sequence to --plan and exit without importing arcpy or "
            "touching a database"
        ),
    )
    parser.add_argument(
        "--plan",
        metavar="PATH",
        type=Path,
        default=DEFAULT_PLAN,
        help="where --dry-run writes the call transcript (default: %(default)s)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.contract.is_file():
        print(f"error: contract not found: {args.contract}", file=sys.stderr)
        return 2
    contract = json.loads(args.contract.read_text(encoding="utf-8"))

    try:
        connection = load_connection(args.connection, args)
    except ImportError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    steps = build_plan(contract, connection, args.sde_dir, args.sde_name, args.overwrite)

    source_path = args.source or Path(contract["source"]["path"])

    if args.dry_run:
        rehearsal = None
        if source_path.is_file():
            try:
                rows = load_rows(source_path, contract)
                rehearsal = rehearse(contract, rows)
            except (SourceError, ImportError_) as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
        else:
            print(f"note: source {source_path} not readable here; rows were not rehearsed")
        args.plan.parent.mkdir(parents=True, exist_ok=True)
        with args.plan.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_plan(steps, contract, connection, rehearsal))
        print(f"dry run: {len(steps)} arcpy calls -> {args.plan}")
        if rehearsal:
            print(f"          {rehearsal['rows']} rows coerced to their declared types, no error")
        print("no arcpy imported, no database touched.")
        return 0

    password = args.password or os.environ.get(PASSWORD_ENV)
    if not password:
        print(
            f"error: no password. Set ${PASSWORD_ENV} or pass --password. It is deliberately "
            "not stored in this repository (CLAUDE.md sections 10 and 11).",
            file=sys.stderr,
        )
        return 2

    if not source_path.is_file():
        print(f"error: source not found: {source_path}", file=sys.stderr)
        return 2

    try:
        rows = load_rows(source_path, contract)
    except SourceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if len(rows) != contract["source"]["rows"]:
        print(
            f"error: the contract was written against {contract['source']['rows']} rows and "
            f"{source_path} now has {len(rows)}. Regenerate the contract rather than loading "
            "data it did not measure.",
            file=sys.stderr,
        )
        return 1

    try:
        return execute(
            steps,
            contract,
            connection,
            password,
            rows,
            args.sde_dir,
            args.sde_name,
            args.overwrite,
            json.loads(args.requirements.read_text(encoding="utf-8"))
            if args.requirements.is_file()
            else None,
        )
    except ImportError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
