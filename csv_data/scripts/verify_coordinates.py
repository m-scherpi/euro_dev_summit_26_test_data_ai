#!/usr/bin/env python3
"""Verify the coordinate columns of a generated geo test data CSV.

Two data sets in this use case need checking, and for opposite reasons:

* `nrw_points_llm_raw.csv` was written directly by a language model, including
  the EPSG:3857 columns. Web Mercator's forward transform contains a logarithm
  of a tangent, which an LLM cannot evaluate reliably by hand, so those values
  are expected to be wrong. This script quantifies the error and writes a
  corrected copy in which *only* `x_3857` and `y_3857` are replaced.
* `germany_points_10k.csv` comes from `generate_points.py`, which computes the
  projection in code. Here the expected deviation is zero, and a non-zero
  result would mean one of the two implementations is broken.

That second case is why this script implements Web Mercator as
`y = R * atanh(sin(phi))` while the generator uses the equivalent
`y = R * ln(tan(pi/4 + phi/2))`. The two formulas are mathematically identical
but independently coded, so this file is a real check on the generator instead
of a second call into the same function. Only the plane geometry is shared, via
`geo.py`, which carries no projection maths.

Standard library only, on purpose: the script has to run on a conference stage
without a virtualenv or an install step. `pyproj` would be the production
choice; the spherical Web Mercator formula is two lines and exact enough for
test data.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from geo import Boundary, load_boundary  # noqa: E402  (needs the path above)

# EPSG:3857 uses a sphere of the WGS 84 semi-major axis radius.
EARTH_RADIUS_M = 6378137.0

# Fallback bounding box (EPSG:4326) when no boundary polygon is available.
FALLBACK_BBOX = (5.87, 9.46, 50.32, 52.53)  # lon_min, lon_max, lat_min, lat_max

COORD_COLUMNS = ("x_3857", "y_3857")
BOOLEAN_VALUES = {"true", "false"}


def lonlat_to_web_mercator(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Project EPSG:4326 decimal degrees to EPSG:3857 metres.

    Uses `y = R * atanh(sin(phi))`. That is the same function as the more
    familiar `R * ln(tan(pi/4 + phi/2))`, deliberately written differently: the
    generator uses the other form, so agreement between the two is evidence and
    not a tautology.

    Note the argument order: longitude first, then latitude. That matches the
    x/y order of the projected result and GeoJSON's [lon, lat] convention -
    unlike the `latitude,longitude` column order of the CSV, which follows the
    geographic convention. Mixing the two up is the single most common source
    of points landing in the wrong hemisphere.
    """
    x = math.radians(lon_deg) * EARTH_RADIUS_M
    y = EARTH_RADIUS_M * math.atanh(math.sin(math.radians(lat_deg)))
    return x, y


def percentile(sorted_values: list[float], fraction: float) -> float:
    """Nearest-rank percentile of an already sorted list."""
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round(fraction * (len(sorted_values) - 1))))
    return sorted_values[index]


def check_rows(
    rows: list[dict[str, str]],
    boundary: Boundary | None,
    bbox: tuple[float, float, float, float],
) -> dict:
    """Run every check over all rows and collect the findings."""
    lon_min, lon_max, lat_min, lat_max = bbox
    findings: dict = {
        "axis_order_errors": [],
        "bbox_errors": [],
        "type_errors": [],
        "deviations": [],
        "outside_boundary": [],
    }

    for number, row in enumerate(rows, start=2):  # line 1 is the header
        row_id = row.get("id", f"line {number}")

        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            findings["type_errors"].append(f"row {row_id}: unparseable coordinates ({exc})")
            continue

        # (1) Axis order. A swapped pair puts latitude into the longitude band.
        if not lat_min <= lat <= lat_max:
            if lon_min <= lat <= lon_max:
                findings["axis_order_errors"].append(
                    f"row {row_id}: latitude {lat} lies in the longitude band "
                    f"- latitude and longitude look swapped"
                )
            else:
                findings["bbox_errors"].append(
                    f"row {row_id}: latitude {lat} outside {lat_min}..{lat_max}"
                )
        if not lon_min <= lon <= lon_max:
            findings["bbox_errors"].append(
                f"row {row_id}: longitude {lon} outside {lon_min}..{lon_max}"
            )

        # (2) EPSG:3857 deviation of the values written into the file.
        exact_x, exact_y = lonlat_to_web_mercator(lon, lat)
        try:
            written_x = float(row["x_3857"])
            written_y = float(row["y_3857"])
        except (KeyError, TypeError, ValueError) as exc:
            findings["type_errors"].append(f"row {row_id}: unparseable 3857 columns ({exc})")
            written_x, written_y = exact_x, exact_y

        dx = written_x - exact_x
        dy = written_y - exact_y
        findings["deviations"].append(
            {
                "id": row_id,
                "dx": dx,
                "dy": dy,
                "distance": math.hypot(dx, dy),
                "exact_x": exact_x,
                "exact_y": exact_y,
            }
        )

        # (3) Containment in the boundary polygon.
        if boundary is not None and not boundary.contains(lon, lat):
            findings["outside_boundary"].append(
                f"row {row_id}: {lat}, {lon} - inside the bounding box, "
                f"outside {boundary.name}"
            )

        # (4) Declared types of the non-geographic columns.
        for column, caster in (("id", int), ("visitor_count", int), ("elevation_m", float)):
            try:
                caster(row[column])
            except (KeyError, TypeError, ValueError):
                findings["type_errors"].append(
                    f"row {row_id}: {column}={row.get(column)!r} is not a valid "
                    f"{caster.__name__}"
                )
        if row.get("is_enchanted") not in BOOLEAN_VALUES:
            findings["type_errors"].append(
                f"row {row_id}: is_enchanted={row.get('is_enchanted')!r} is not "
                f"one of {sorted(BOOLEAN_VALUES)}"
            )

    return findings


def write_corrected_csv(
    path: Path, fieldnames: list[str], rows: list[dict[str, str]], findings: dict
) -> None:
    """Write a copy in which only the two EPSG:3857 columns are replaced."""
    by_id = {d["id"]: d for d in findings["deviations"]}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            deviation = by_id.get(row.get("id"))
            if deviation is not None:
                row = dict(row)
                row["x_3857"] = f"{deviation['exact_x']:.2f}"
                row["y_3857"] = f"{deviation['exact_y']:.2f}"
            writer.writerow(row)


def render_report(
    findings: dict,
    source: Path,
    corrected: Path | None,
    tolerance: float,
    row_count: int,
    region: str,
    bbox: tuple[float, float, float, float],
    bands_overlap: bool,
    max_listed: int,
) -> str:
    """Render the verification result as Markdown."""
    lon_min, lon_max, lat_min, lat_max = bbox
    distances = sorted(d["distance"] for d in findings["deviations"])
    off_tolerance = [d for d in findings["deviations"] if d["distance"] > tolerance]
    worst = max(findings["deviations"], key=lambda d: d["distance"], default=None)
    outside = findings["outside_boundary"]

    def status(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    lines = [
        "# Coordinate verification report",
        "",
        f"- Source: `{source}`",
        f"- Corrected copy: {f'`{corrected}`' if corrected else '_not written (--check-only)_'}",
        f"- Rows checked: {row_count:,}",
        f"- Region: {region}",
        f"- Bounding box: lat {lat_min}..{lat_max} / lon {lon_min}..{lon_max}",
        f"- Tolerance: {tolerance:g} m",
        "",
        "Generated by `scripts/verify_coordinates.py`. Regenerate with the command in",
        "[`../README.md`](../README.md).",
        "",
    ]

    if bands_overlap:
        lines += [
            "> **Warning:** the latitude and longitude bands of this bounding box",
            "> overlap, so a swapped coordinate pair can still fall inside both.",
            "> The axis-order check below cannot be trusted for this region.",
            "",
        ]

    lines += [
        "## Summary",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
        f"| Axis order (latitude/longitude not swapped) | "
        f"{status(not findings['axis_order_errors'])} | "
        f"{len(findings['axis_order_errors'])} suspected swaps |",
        f"| Inside sampling bounding box | {status(not findings['bbox_errors'])} | "
        f"{len(findings['bbox_errors'])} violations |",
        f"| Column types (INTEGER / DOUBLE / BOOLEAN) | "
        f"{status(not findings['type_errors'])} | "
        f"{len(findings['type_errors'])} violations |",
        f"| EPSG:3857 values within tolerance | {status(not off_tolerance)} | "
        f"{len(off_tolerance):,} of {len(findings['deviations']):,} rows off |",
        f"| Inside {region} | INFO | "
        f"{len(outside):,} of {row_count:,} points outside |",
        "",
        "## EPSG:3857 deviation",
        "",
        "Distance between the value written into the CSV and the value recomputed",
        "from `latitude`/`longitude`. This script uses `R * atanh(sin(phi))`; the",
        "generator uses the equivalent `R * ln(tan(pi/4 + phi/2))`, so the two are",
        "independent implementations of the same projection.",
        "",
        "| Metric | Metres |",
        "|---|---|",
    ]
    if distances:
        lines += [
            f"| min | {distances[0]:,.2f} |",
            f"| median | {percentile(distances, 0.5):,.2f} |",
            f"| mean | {sum(distances) / len(distances):,.2f} |",
            f"| p95 | {percentile(distances, 0.95):,.2f} |",
            f"| max | {distances[-1]:,.2f} |",
        ]
    else:
        lines.append("| _no rows_ | - |")
    lines.append("")

    if worst is not None:
        lines += [
            f"Worst row: `id={worst['id']}` - off by {worst['distance']:,.2f} m "
            f"(dx {worst['dx']:+,.2f} m, dy {worst['dy']:+,.2f} m).",
            "",
        ]

    top = sorted(findings["deviations"], key=lambda d: d["distance"], reverse=True)[:10]
    if top and top[0]["distance"] > tolerance:
        lines += [
            "### Ten largest deviations",
            "",
            "| id | dx (m) | dy (m) | distance (m) |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| {d['id']} | {d['dx']:+,.2f} | {d['dy']:+,.2f} | {d['distance']:,.2f} |"
            for d in top
        ]
        lines.append("")

    sections = (
        ("Suspected axis swaps", "axis_order_errors", "Structural failure - blocks a pass."),
        ("Bounding box violations", "bbox_errors", "Structural failure - blocks a pass."),
        ("Type violations", "type_errors", "Structural failure - blocks a pass."),
        (
            f"Points outside {region}",
            "outside_boundary",
            "Informational. A bounding box is not a boundary: its corners reach "
            "into neighbouring regions, so uniform sampling of the box places a "
            "share of the points outside. Sampling against the polygon instead "
            "drives this to zero. The polygon is generalised, so treat borderline "
            "rows as indicative only.",
        ),
    )
    for title, key, note in sections:
        lines += [f"## {title}", "", note, ""]
        entries = findings[key]
        if entries:
            lines += [f"- {entry}" for entry in entries[:max_listed]]
            if len(entries) > max_listed:
                lines.append(
                    f"- _... and {len(entries) - max_listed:,} more, not listed "
                    f"(raise `--max-listed` to see them all)_"
                )
        else:
            lines.append("_none_")
        lines.append("")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_coordinates.py",
        description=(
            "Verify the coordinate columns of a generated geo test data CSV: "
            "latitude/longitude axis order, bounding box, EPSG:3857 accuracy, "
            "boundary containment and column types. Optionally writes a copy "
            "with corrected EPSG:3857 values."
        ),
        epilog=(
            "Examples:\n"
            "  # Report to stdout, write nothing\n"
            "  python3 scripts/verify_coordinates.py --input output/nrw_points.csv\n\n"
            "  # LLM-written data: quantify the error, write a corrected copy\n"
            "  python3 scripts/verify_coordinates.py \\\n"
            "      --input  output/nrw_points_llm_raw.csv \\\n"
            "      --output output/nrw_points.csv \\\n"
            "      --report output/verification_report.md\n\n"
            "  # Script-generated data: nothing to correct, expect ~0 deviation\n"
            "  python3 scripts/verify_coordinates.py \\\n"
            "      --input    output/germany_points_10k.csv \\\n"
            "      --boundary input/germany_boundary_ne50m.geojson \\\n"
            "      --report   output/verification_report_germany.md\n\n"
            "Exit code 0 if all structural checks pass, 1 otherwise. An EPSG:3857 "
            "deviation is reported but never fatal - for LLM-written data it is "
            "the expected finding."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", type=Path, default=Path("output/nrw_points_llm_raw.csv"), metavar="CSV",
        help="CSV to verify (default: %(default)s)",
    )
    parser.add_argument(
        "--output", type=Path, default=None, metavar="CSV",
        help="write a copy with corrected EPSG:3857 columns to this path. "
        "No default on purpose - without it nothing is written, so verifying "
        "one data set can never overwrite another",
    )
    parser.add_argument(
        "--report", type=Path, default=None, metavar="MD",
        help="write the Markdown report to this path; without it the report "
        "goes to stdout",
    )
    parser.add_argument(
        "--boundary", type=Path, default=Path("input/nrw_boundary_approx.geojson"),
        metavar="GEOJSON",
        help="boundary polygon for the containment check; the bounding box is "
        "derived from it. Pass a non-existent path to skip the check "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--bbox", nargs=4, type=float, metavar=("LON_MIN", "LON_MAX", "LAT_MIN", "LAT_MAX"),
        help="override the bounding box instead of deriving it from --boundary",
    )
    parser.add_argument(
        "--tolerance", type=float, default=1.0, metavar="METRES",
        help="allowed EPSG:3857 deviation before a row counts as off "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--max-listed", type=int, default=200, metavar="N",
        help="maximum number of individual findings listed per report section "
        "(default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.input.is_file():
        print(f"error: input CSV not found: {args.input}", file=sys.stderr)
        return 1

    with args.input.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    missing = [c for c in ("latitude", "longitude", *COORD_COLUMNS) if c not in fieldnames]
    if missing:
        print(f"error: {args.input} is missing columns: {', '.join(missing)}", file=sys.stderr)
        return 1

    boundary = load_boundary(args.boundary) if args.boundary.is_file() else None
    if boundary is None:
        print(f"note: {args.boundary} not found - skipping the containment check")

    if args.bbox:
        bbox = tuple(args.bbox)  # type: ignore[assignment]
    elif boundary is not None:
        bbox = boundary.bounds
    else:
        bbox = FALLBACK_BBOX
        print(f"note: no boundary - falling back to bounding box {bbox}")

    lon_min, lon_max, lat_min, lat_max = bbox
    bands_overlap = lat_min <= lon_max and lon_min <= lat_max
    if bands_overlap:
        print(
            "warning: latitude and longitude bands overlap for this bounding box "
            "- the axis-order check cannot detect a swap here",
            file=sys.stderr,
        )

    region = boundary.name if boundary is not None else "the bounding box"
    findings = check_rows(rows, boundary, bbox)

    corrected_path = None
    if args.output is not None:
        if args.output.resolve() == args.input.resolve():
            print(
                f"error: --output would overwrite the input file {args.input}",
                file=sys.stderr,
            )
            return 1
        write_corrected_csv(args.output, fieldnames, rows, findings)
        corrected_path = args.output

    report = render_report(
        findings, args.input, corrected_path, args.tolerance, len(rows),
        region, bbox, bands_overlap, args.max_listed,
    )
    if args.report is None:
        print(report)
    else:
        args.report.write_text(report + "\n", encoding="utf-8")

    distances = [d["distance"] for d in findings["deviations"]]
    structural = (
        len(findings["axis_order_errors"])
        + len(findings["bbox_errors"])
        + len(findings["type_errors"])
    )
    print(
        f"{len(rows):,} rows checked | structural failures: {structural} | "
        f"max EPSG:3857 deviation: {max(distances, default=0.0):,.2f} m | "
        f"outside {region}: {len(findings['outside_boundary']):,}"
    )
    written = [str(p) for p in (corrected_path, args.report) if p is not None]
    if written:
        print(f"wrote {' and '.join(written)}")

    return 1 if structural else 0


if __name__ == "__main__":
    sys.exit(main())
