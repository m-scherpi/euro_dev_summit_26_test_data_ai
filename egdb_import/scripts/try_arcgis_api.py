#!/usr/bin/env python3
"""Run the route the request named - the ArcGIS API for Python - and record what happens.

This use case was asked for "using the ArcGIS API for Python". That API cannot
create a feature class in an Enterprise Geodatabase, and the interesting part is
*how* it cannot: not with an exception, but by doing something else and
returning a path. This script is the measurement behind that claim rather than
an assertion of it, which is why it exists next to a working importer instead of
being replaced by a sentence in the README.

Two routes, both documented as the way to get a DataFrame into ArcGIS:

**Route 1 - `GIS.content.import_data()`.** Not attempted, on purpose, and the
refusal is the finding. It produces a *hosted* feature layer in the ArcGIS Data
Store: the data is copied out of the customer's database into Esri's own
relational store. For a use case whose entire goal is a feature class *in* the
customer's PostgreSQL, that is not a partial success, it is the opposite
outcome - and it would also mean uploading the data to a portal, which is a side
effect no verification script should have.

**Route 2 - `DataFrame.spatial.to_featureclass()`.** Attempted for real. Esri's
guide says: "Writing to file geodatabases requires the ArcPy site-package." So
in an interpreter without arcpy the same call with the same arguments writes a
**shapefile** instead. Run this once in ArcGIS Pro's `arcgispro-py3` environment
and once in a plain `pip install arcgis` venv, and the difference between the
two reports is the whole point.

There is also a documentation conflict here, recorded rather than resolved
(CLAUDE.md section 4 - quote the whole sentence, do not turn a gap into a
claim): the guide says shapefile-only without arcpy, while the current API
reference documents `ARCGIS_IO_ENGINE` with options `'shapefile'`, `'gdal'` and
`'arcpy'` and says "the first available library in the environment will be
used". Neither page says what the GDAL engine can write. This script prints
which engine was in play and what landed on disk, so the report answers for the
machine it ran on and claims nothing beyond it.

Everything written goes to `build/` - a shapefile is not something to commit.
The report goes to `output/`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT = Path("output/nrw_points_schema.json")
DEFAULT_REPORT = Path("output/arcgis_api_attempt.md")
DEFAULT_WORKDIR = Path("build/arcgis_api")

IO_ENGINE_ENV = "ARCGIS_IO_ENGINE"

SHAPEFILE_SIDECARS = (".shp", ".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx")


def portable(path: str | Path) -> str:
    """A path fit for a committed artifact: relative, or home-anonymised.

    The report is committed and the repository is public, so an absolute path
    under somebody's home directory has no business in it.
    """
    text = str(path)
    cwd = Path.cwd().resolve()
    # Try the literal path before the resolved one: a venv's bin/python is a
    # symlink to the system interpreter, and resolving it first would report the
    # system path rather than the environment that actually ran.
    for candidate in (Path(text), Path(text).resolve()):
        try:
            return candidate.absolute().relative_to(cwd).as_posix()
        except ValueError:
            continue
    home = str(Path.home())
    return text.replace(home, "~") if text.startswith(home) else text


def probe_environment() -> dict[str, Any]:
    """What is importable here, which is what decides the outcome."""
    probes: dict[str, Any] = {
        "python": sys.version.split()[0],
        "executable": portable(sys.executable),
        IO_ENGINE_ENV: os.environ.get(IO_ENGINE_ENV) or "(unset - the API picks the first available)",
    }
    for module in ("arcpy", "arcgis", "pandas", "osgeo.gdal", "fiona", "shapefile"):
        try:
            imported = __import__(module)
            for part in module.split(".")[1:]:
                imported = getattr(imported, part)
            probes[module] = getattr(imported, "__version__", "present, no __version__")
        except Exception as exc:
            probes[module] = f"NOT importable ({exc.__class__.__name__})"
    return probes


def to_featureclass_attempt(
    contract: dict[str, Any], source: Path, location: str, workdir: Path
) -> dict[str, Any]:
    """Call the documented route and report what actually appeared on disk."""
    result: dict[str, Any] = {"location_requested": location}
    try:
        import pandas
        from arcgis.features import GeoAccessor, GeoSeriesAccessor  # noqa: F401  (registers .spatial)
    except Exception as exc:
        result["outcome"] = "NOT ATTEMPTED"
        result["detail"] = (
            f"the arcgis package or pandas is not importable here ({exc.__class__.__name__}: {exc})"
        )
        return result

    geometry = contract["geometry"]
    frame = pandas.read_csv(source, encoding=contract["source"]["encoding"])
    sdf = pandas.DataFrame.spatial.from_xy(
        frame,
        x_column=geometry["x_column"],
        y_column=geometry["y_column"],
        sr=contract["spatial_reference"]["wkid"],
    )
    result["rows"] = int(len(sdf))
    result["dtypes"] = {str(k): str(v) for k, v in frame.dtypes.items()}

    before = {p.name for p in workdir.glob("*")} if workdir.exists() else set()
    try:
        written = sdf.spatial.to_featureclass(location=location, overwrite=True)
        result["returned_path"] = portable(written)
        result["outcome"] = "RETURNED A PATH"
    except Exception as exc:
        result["outcome"] = "RAISED"
        result["detail"] = f"{exc.__class__.__name__}: {exc}"
        return result

    after = {p.name for p in workdir.glob("*")} if workdir.exists() else set()
    appeared = sorted(after - before)
    result["files_created"] = appeared
    suffixes = {Path(name).suffix.lower() for name in appeared}
    if suffixes & set(SHAPEFILE_SIDECARS):
        result["format_written"] = "SHAPEFILE"
        result["verdict"] = (
            "The call succeeded and wrote a shapefile. It was asked for a feature class. "
            "No exception, no warning - just a different format at the path it returned."
        )
    elif appeared:
        result["format_written"] = f"other ({', '.join(sorted(suffixes)) or 'no suffix'})"
        result["verdict"] = "Something was written; inspect files_created to see what."
    else:
        result["format_written"] = "nothing in the working directory"
        result["verdict"] = (
            "Nothing appeared beside the working directory, so the write went to the target "
            "the path named - the arcpy engine was in play."
        )

    result["schema_written"] = describe_written(str(written))

    # The one thing that did survive intact, and it is worth measuring rather
    # than assuming: a shapefile carries its CRS in a sidecar .prj, so the
    # spatial reference the contract named is not lost even though the format is
    # wrong. Recording it keeps the finding honest - the substitution damaged
    # the schema, not the projection.
    prj = next((Path(workdir) / name for name in appeared if name.lower().endswith(".prj")), None)
    if prj is not None and prj.is_file():
        text = prj.read_text(encoding="utf-8", errors="replace")
        result["prj_written"] = text.strip()[:120]
    return result


def describe_written(path: str) -> dict[str, str] | str:
    """The field types the API's own inference produced, if they can be read back."""
    try:
        import arcpy

        return {
            field.name: (
                f"{field.type}({field.length})" if field.type == "String" else field.type
            )
            for field in arcpy.ListFields(path)
        }
    except Exception:
        pass
    try:
        import shapefile

        with shapefile.Reader(path) as reader:
            return {f[0]: f"{f[1]}({f[2]},{f[3]})" for f in reader.fields if f[0] != "DeletionFlag"}
    except Exception as exc:
        return f"could not read the result back ({exc.__class__.__name__})"


# The DBF field-name limit. Not a number this repository chose - it is the
# shapefile format's, and it is the reason four of ten field names below come
# back shortened without anything having said so.
DBF_FIELD_NAME_LIMIT = 10


def pair_schemas(
    declared: dict[str, str], written: dict[str, str]
) -> tuple[list[tuple[str, str, str, str]], list[str]]:
    """Match contract fields to what was written, and name every difference.

    Matching has to allow for truncation, because that is one of the findings: a
    shapefile's DBF header allows ten characters, so `description` comes back as
    `descriptio`. Listing the two as unrelated missing/extra fields would hide
    exactly the thing worth seeing.
    """
    remaining = dict(written)
    pairs: list[tuple[str, str, str, str]] = []
    deltas: list[str] = []

    for name, contract_type in declared.items():
        match = next((k for k in remaining if k.lower() == name.lower()), None)
        if match is None:
            truncated = name[:DBF_FIELD_NAME_LIMIT].lower()
            match = next((k for k in remaining if k.lower() == truncated), None)
            if match is not None:
                deltas.append(
                    f"`{name}` was renamed to `{match}` - silently truncated to the DBF "
                    f"field-name limit of {DBF_FIELD_NAME_LIMIT} characters. Nothing in the call "
                    "reports it, and a downstream query on the original name finds no column."
                )
        if match is None:
            pairs.append((name, contract_type, "—", "not written"))
            deltas.append(f"`{name}` does not appear in the written schema at all.")
            continue
        written_type = remaining.pop(match)
        pairs.append((name, contract_type, match, written_type))

    for leftover, leftover_type in remaining.items():
        pairs.append(("—", "not in the contract", leftover, leftover_type))
        deltas.append(f"`{leftover}` ({leftover_type}) was written but the contract never asked for it.")

    # Type-level differences worth stating in words rather than leaving in a table.
    for name, contract_type, written_name, written_type in pairs:
        if contract_type.startswith("TEXT(") and written_type.startswith("C("):
            declared_len = contract_type[5:-1]
            actual_len = written_type[2:].split(",")[0]
            if declared_len != actual_len:
                deltas.append(
                    f"`{name}`: the contract measured TEXT({declared_len}) from the data; the "
                    f"API wrote C({actual_len}) - the format's maximum, so the measurement was "
                    "discarded rather than used."
                )
        if contract_type == "DOUBLE" and written_type.startswith("F("):
            deltas.append(
                f"`{name}`: DOUBLE became DBF type F (float). A shapefile has no double, so the "
                "geodatabase type the contract asked for does not exist in the format that was "
                "written instead."
            )
        if contract_type == "SHORT" and written_type.startswith("L("):
            deltas.append(
                f"`{name}`: the contract substituted SHORT for a boolean because an Enterprise "
                "Geodatabase has no boolean type - and the shapefile wrote DBF type L, which is "
                "a boolean. The format that cannot be the target represents this column better "
                "than the target can."
            )

    return pairs, deltas


def render(
    contract: dict[str, Any], environment: dict[str, Any], attempt: dict[str, Any]
) -> str:
    lines = [
        "# The ArcGIS API for Python, and what it actually writes",
        "",
        "Produced by `try_arcgis_api.py`. This is a measurement of one machine, not a claim",
        "about every machine - which is the point, because the outcome depends entirely on",
        "what is importable in the interpreter.",
        "",
        "## Environment",
        "",
        "| | |",
        "|---|---|",
    ]
    for key, value in environment.items():
        lines.append(f"| `{key}` | {value} |")

    lines += [
        "",
        "## Route 1 - `GIS.content.import_data()`",
        "",
        "**Not attempted, deliberately.** It produces a *hosted* feature layer in the ArcGIS",
        "Data Store: the rows are copied out of the customer's database into Esri's own",
        "relational store. The goal here is a feature class *in* PostgreSQL, so this route does",
        "not fall short of the goal, it inverts it - and running it would upload the data to a",
        "portal, which is not a side effect a verification script should have.",
        "",
        "It is worth naming precisely because it is the route the API's own tutorials show, and",
        "it succeeds. A reader following the documentation gets a working layer and no signal",
        "that the data left the database.",
        "",
        "## Route 2 - `DataFrame.spatial.to_featureclass()`",
        "",
        "Esri's guide, verbatim:",
        "",
        "> Writing to file geodatabases requires the ArcPy site-package.",
        "",
        "<https://developers.arcgis.com/python/latest/guide/introduction-to-the-spatially-enabled-dataframe/>",
        "",
        "| | |",
        "|---|---|",
    ]
    for key in ("location_requested", "rows", "outcome", "returned_path", "format_written", "files_created", "prj_written", "detail"):
        if key in attempt:
            value = attempt[key]
            if isinstance(value, list):
                value = ", ".join(f"`{v}`" for v in value) or "(none)"
            lines.append(f"| {key.replace('_', ' ')} | {value} |")
    if "verdict" in attempt:
        lines += ["", f"**{attempt['verdict']}**"]

    written = attempt.get("schema_written")
    if isinstance(written, dict):
        declared = {
            f["name"]: (f"{f['type']}({f['length']})" if f.get("length") else f["type"])
            for f in contract["fields"]
        }
        pairs, deltas = pair_schemas(declared, written)
        lines += [
            "",
            "### Schema: what the contract asked for, and what the API produced",
            "",
            "`to_featureclass` takes `location, overwrite, has_z, has_m, sanitize_columns` and",
            "nothing else. There is no parameter for a field type, a TEXT length or an alias, and",
            "Esri publishes no dtype mapping table. For an importer whose deliverable *is* the",
            "schema, that is disqualifying - which is why `import_to_egdb.py` calls",
            "`CreateFeatureclass` and `AddField` and states every type and length itself.",
            "",
            "| Contract field | Contract type | Written as | Written type |",
            "|---|---|---|---|",
        ]
        for contract_name, contract_type, written_name, written_type in pairs:
            flag = " **renamed**" if written_name not in ("", contract_name) and written_name != "—" and written_name != contract_name else ""
            lines.append(
                f"| `{contract_name}` | {contract_type} | `{written_name}`{flag} | {written_type} |"
            )
        if deltas:
            lines += ["", "**What the schema lost on the way:**", ""]
            lines += [f"- {d}" for d in deltas]
    elif isinstance(written, str):
        lines += ["", f"Schema could not be read back: {written}"]

    lines += [
        "",
        "## The documentation conflict, unresolved",
        "",
        "The guide says shapefile-only without arcpy. The current API reference documents an",
        "`ARCGIS_IO_ENGINE` variable with options `'shapefile'`, `'gdal'` and `'arcpy'`, and says",
        "\"the first available library in the environment will be used\". Neither page says what",
        "the GDAL engine can write.",
        "",
        "<https://developers.arcgis.com/python/latest/api-reference/arcgis.features.toc.html>",
        "",
        "Recorded as an open conflict rather than settled by guessing. The environment table",
        "above says which libraries were present, so this report answers for this machine and",
        "claims nothing beyond it.",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="try_arcgis_api.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Attempt the route the request named - the ArcGIS API for Python - and record what "
            "it actually wrote. Writes data to build/ and a report to output/."
        ),
        epilog=(
            "In ArcGIS Pro's own Python, where arcpy is present:\n"
            "\n"
            "  \"%PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\Scripts\\propy\" ^\n"
            "      scripts\\try_arcgis_api.py ^\n"
            "      --location build\\egdb.sde\\devsummit.devsummit.nrw_points_api ^\n"
            "      --report output\\arcgis_api_attempt.md\n"
            "\n"
            "In a plain venv with `pip install arcgis` and no arcpy - the run that shows the\n"
            "finding:\n"
            "\n"
            "  python3 scripts/try_arcgis_api.py \\\n"
            "      --location build/arcgis_api/nrw_points_api \\\n"
            "      --report output/arcgis_api_attempt.md\n"
        ),
    )
    parser.add_argument(
        "--contract",
        metavar="PATH",
        type=Path,
        default=DEFAULT_CONTRACT,
        help="schema contract, used for the comparison table (default: %(default)s)",
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        type=Path,
        default=None,
        help="source CSV (default: the path recorded in the contract)",
    )
    parser.add_argument(
        "--location",
        metavar="PATH",
        default=None,
        help=(
            "what to pass to to_featureclass as `location`. Default: a path inside --workdir, "
            "which is where a shapefile lands if arcpy is missing."
        ),
    )
    parser.add_argument(
        "--workdir",
        metavar="PATH",
        type=Path,
        default=DEFAULT_WORKDIR,
        help="gitignored working directory for whatever gets written (default: %(default)s)",
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
    source = args.source or Path(contract["source"]["path"])
    args.workdir.mkdir(parents=True, exist_ok=True)
    location = args.location or str(args.workdir / f"{contract['feature_class']['name']}_api")

    environment = probe_environment()
    attempt = to_featureclass_attempt(contract, source, location, args.workdir)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render(contract, environment, attempt))

    print(f"outcome: {attempt.get('outcome')}  format: {attempt.get('format_written', 'n/a')}")
    print(f"report -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
