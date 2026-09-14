#!/usr/bin/env python3
"""Verify the coordinate columns of the generated Munster rent census - offline.

Two checks, and the number is a decision rather than a shortfall. CLAUDE.md
section 12: agree the verification depth up front instead of defaulting to
rigour. The data here is **invented**, so the questions `open_data_search` and
`opensearch` had to answer do not exist: there is no source row to trace a
coordinate back to, no licence to defend, and no published position anybody
could check. What remains is the two failures that would be invisible in a
finished web map:

1. **Axis order and range.** A swapped pair is the classic silent failure.
2. **The projected columns agree with the geographic ones.** Web Mercator
   contains a logarithm of a tangent, and CLAUDE.md section 4 is blunt about
   that: never trust an LLM with a projection formula, and recompute anything
   containing a log, a tangent or a square root. The failure mode is a
   systematic directional bias, not noise, so it survives averaging and looks
   entirely plausible.

The recomputation is written as `y = R * atanh(sin phi)` while the generator
writes the algebraically identical `y = R * ln(tan(pi/4 + phi/2))`. Same
function, two independently coded forms, so agreement between them is evidence
instead of a tautology. This script deliberately imports **nothing** from
`census.py` - not the field list, not the radius, not the decimal count. A
checker that shares a constant with the thing it checks is checking the
constant against itself.

What is deliberately not checked here is listed in the README's "Deliberately
not checked" section, with a sentence per omission. The short version:
coordinate provenance cannot exist for data that has no source, and statistical
realism is the wrong question about a fictional census.

Standard library only. Requires Python 3.10+.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

# Not imported from census.py on purpose: the radius is restated here from the
# EPSG:3857 definition so that this file is a second reading of the spec rather
# than a second call into the generator.
EARTH_RADIUS_M = 6378137.0

# Tolerance for the recomputation, in metres. One millimetre is far below any
# error a wrong formula would produce (the `csv_data` LLM was off by 490 m) and
# far above the noise of double arithmetic. It is deliberately **not** tightened
# to whatever this artifact happens to achieve: CLAUDE.md section 4 - a check
# calibrated to the current file's exact rounding fails on the next source for a
# reason that is not an error. The measured value is reported so the margin is
# visible.
DEFAULT_TOLERANCE_M = 0.001

REQUIRED_COLUMNS = ("latitude", "longitude", "x_3857", "y_3857")


def lonlat_to_web_mercator(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Project EPSG:4326 decimal degrees to EPSG:3857 metres.

    `y = R * atanh(sin phi)`. The generator uses `R * ln(tan(pi/4 + phi/2))`,
    which is the same function written the other way round. Only the radius is
    common to both, and that is a constant of the coordinate system rather than
    a step of the computation.

    Longitude first, then latitude - the x/y order of the result, and the
    opposite of the CSV's latitude-before-longitude column order.
    """
    x = math.radians(lon_deg) * EARTH_RADIUS_M
    y = EARTH_RADIUS_M * math.atanh(math.sin(math.radians(lat_deg)))
    return x, y


def load_box(path: Path) -> tuple[dict, dict]:
    """Read the sampling bounding box out of the districts fixture.

    The box comes from `input/` rather than from a constant in this file,
    because the generator samples inside it and the verifier has to check
    against the same declaration. It is read as **data**, though: this script
    never imports the generator's code.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    box = data.get("bounding_box")
    if not box:
        raise ValueError(f"{path} carries no bounding_box")
    for key in ("latitude_min", "latitude_max", "longitude_min", "longitude_max"):
        if key not in box:
            raise ValueError(f"{path} is missing bounding_box.{key}")
    return data, box


def percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round(fraction * (len(sorted_values) - 1))))
    return sorted_values[index]


def check(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    box: dict,
    tolerance: float,
) -> dict:
    """Run both checks over every row and collect the findings."""
    lat_min = float(box["latitude_min"])
    lat_max = float(box["latitude_max"])
    lon_min = float(box["longitude_min"])
    lon_max = float(box["longitude_max"])

    findings: dict = {
        "column_order": [],
        "axis_swaps": [],
        "range_errors": [],
        "transposed_hits": [],
        "unparseable": [],
        "deviations": [],
    }

    # Column order is part of check 1 rather than a check of its own: a file
    # whose header says longitude before latitude will pass every numeric test
    # and be read wrongly by the next tool along. CLAUDE.md section 4 - latitude
    # before longitude for a geographic CRS, x before y for a projected one.
    order = [c for c in fieldnames if c in REQUIRED_COLUMNS]
    if order != ["latitude", "longitude", "x_3857", "y_3857"]:
        findings["column_order"].append(
            f"coordinate columns appear as {order}, expected "
            f"['latitude', 'longitude', 'x_3857', 'y_3857']"
        )

    for number, row in enumerate(rows, start=2):  # line 1 is the header
        row_id = row.get("id", f"line {number}")
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            written_x = float(row["x_3857"])
            written_y = float(row["y_3857"])
        except (KeyError, TypeError, ValueError) as exc:
            findings["unparseable"].append(f"row {row_id}: {exc}")
            continue

        # (1) Range, and the axis-order reading of a range failure.
        in_lat_band = lat_min <= lat <= lat_max
        in_lon_band = lon_min <= lon <= lon_max
        if not in_lat_band:
            if lon_min <= lat <= lon_max:
                findings["axis_swaps"].append(
                    f"row {row_id}: latitude {lat} lies in the longitude band "
                    f"{lon_min}..{lon_max} - the pair looks swapped"
                )
            else:
                findings["range_errors"].append(
                    f"row {row_id}: latitude {lat} outside {lat_min}..{lat_max}"
                )
        if not in_lon_band:
            if lat_min <= lon <= lat_max:
                findings["axis_swaps"].append(
                    f"row {row_id}: longitude {lon} lies in the latitude band "
                    f"{lat_min}..{lat_max} - the pair looks swapped"
                )
            else:
                findings["range_errors"].append(
                    f"row {row_id}: longitude {lon} outside {lon_min}..{lon_max}"
                )

        # The transposed box has to match nothing. With disjoint bands that is
        # implied by the range check above, and it is asserted separately
        # anyway: it is the form that keeps working when a later data set's
        # bands overlap, where the range check alone stops discriminating.
        if lat_min <= lon <= lat_max and lon_min <= lat <= lon_max:
            findings["transposed_hits"].append(
                f"row {row_id}: ({lat}, {lon}) satisfies the transposed box as well"
            )

        # (2) Independent recomputation of the projected pair.
        exact_x, exact_y = lonlat_to_web_mercator(lon, lat)
        dx = written_x - exact_x
        dy = written_y - exact_y
        findings["deviations"].append(
            {"id": row_id, "dx": dx, "dy": dy, "distance": math.hypot(dx, dy)}
        )

    findings["off_tolerance"] = [
        d for d in findings["deviations"] if d["distance"] > tolerance
    ]
    return findings


def swap_verdict(box: dict) -> tuple[bool, str]:
    """Is a swapped coordinate pair loud or silent for this data set?

    CLAUDE.md section 4 forbids writing "the axis check passes" without saying
    whether anything else would have caught a swap. For this data set the answer
    has two halves and they point in opposite directions, which is exactly why
    it has to be spelled out:

    * The two bands are **disjoint** - latitude 51.90..52.00 against longitude
      7.55..7.72 - so the bounding-box check catches a swap on every single row.
    * And every swapped value is still a **legal** coordinate: 7.6 is a valid
      latitude and 51.9 a valid longitude, so no database, no service and no
      GIS client would refuse the load. The points would sit at 7.6 N 51.9 E in
      the Somali Sea and draw without a warning.

    That is the same silence as the NRW stations in `opensearch` and
    `egdb_import`, and the opposite of the 880 airports, where the engine
    rejected 550 of 880 documents outright. So this check is load-bearing here
    precisely because nothing downstream would fire.
    """
    lat_min = float(box["latitude_min"])
    lat_max = float(box["latitude_max"])
    lon_min = float(box["longitude_min"])
    lon_max = float(box["longitude_max"])
    disjoint = lat_min > lon_max or lon_min > lat_max
    engine_would_reject = not (-90.0 <= lon_min and lon_max <= 90.0)

    if not disjoint:
        return False, (
            "The latitude and longitude bands **overlap**, so a swapped pair can fall "
            "inside both and this check cannot detect it. Do not read a PASS as evidence."
        )
    if engine_would_reject:
        return True, (
            "The bands are disjoint **and** the longitude range leaves the legal "
            "latitude domain, so a swap would additionally be rejected by any engine "
            "that validates coordinates."
        )
    return True, (
        "The bands are **disjoint**, so this check catches a swap on every row. But "
        f"every swapped value stays legal: {lon_min}..{lon_max} are valid latitudes and "
        f"{lat_min}..{lat_max} are valid longitudes, so no database, service or GIS "
        "client would refuse the load - the points would draw silently at "
        f"{lon_min:.1f} N {lat_min:.1f} E in the Somali Sea. Same case as the NRW "
        "stations in `opensearch` and `egdb_import`; the opposite of the 880 airports, "
        "where the engine rejected 550 of 880 documents. This check is load-bearing "
        "here because nothing downstream would fire."
    )


def render_report(
    findings: dict,
    source: Path,
    districts_path: Path,
    districts: dict,
    box: dict,
    tolerance: float,
    row_count: int,
    max_listed: int,
) -> str:
    def status(ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    distances = sorted(d["distance"] for d in findings["deviations"])
    worst = max(findings["deviations"], key=lambda d: d["distance"], default=None)
    check_1_ok = not (
        findings["column_order"]
        or findings["axis_swaps"]
        or findings["range_errors"]
        or findings["transposed_hits"]
        or findings["unparseable"]
    )
    check_2_ok = not findings["off_tolerance"] and not findings["unparseable"]
    loud, verdict = swap_verdict(box)

    lines = [
        "# Coordinate verification report - Munster rent census",
        "",
        f"- Source: `{source}`",
        f"- Rows checked: {row_count:,}",
        f"- Bounding box: `{districts_path}` "
        f"(`authoritative: {districts.get('authoritative')}`)",
        f"  - latitude {box['latitude_min']}..{box['latitude_max']} "
        f"/ longitude {box['longitude_min']}..{box['longitude_max']}",
        f"- Tolerance for the projected columns: {tolerance:g} m",
        "",
        "Generated by `scripts/verify_census.py`, standard library only. Regenerate with",
        "the command in [`../README.md`](../README.md#usage).",
        "",
        "Two checks, and that number is a decision - see the README's *Verification*",
        "section for the depth this data earns and the four omissions it does not.",
        "",
        "## Summary",
        "",
        "| # | Check | Result | Detail |",
        "|---|---|---|---|",
        f"| 1 | Axis order, column order and range | {status(check_1_ok)} | "
        f"{len(findings['axis_swaps'])} suspected swaps, "
        f"{len(findings['range_errors'])} out of range, "
        f"{len(findings['transposed_hits'])} transposed-box hits, "
        f"{len(findings['column_order'])} column-order faults |",
        f"| 2 | EPSG:3857 columns recomputed independently | {status(check_2_ok)} | "
        f"{len(findings['off_tolerance']):,} of {len(findings['deviations']):,} rows "
        f"beyond {tolerance:g} m |",
        "",
        "## 1. Axis order, column order and range",
        "",
        "Every row's `latitude` must sit inside the latitude band and every `longitude`",
        "inside the longitude band; the **transposed** box must match nothing; and the",
        "header must list `latitude` before `longitude` and `x_3857` before `y_3857`",
        "(CLAUDE.md section 4 - column order follows the CRS).",
        "",
        f"**Is a swap loud or silent here?** {verdict}",
        "",
    ]

    sections = (
        ("Suspected axis swaps", "axis_swaps"),
        ("Out of range", "range_errors"),
        ("Transposed-box hits", "transposed_hits"),
        ("Column order", "column_order"),
        ("Unparseable rows", "unparseable"),
    )
    for title, key in sections:
        entries = findings[key]
        lines.append(f"- **{title}:** {len(entries):,}")
        for entry in entries[:max_listed]:
            lines.append(f"  - {entry}")
        if len(entries) > max_listed:
            lines.append(
                f"  - _... and {len(entries) - max_listed:,} more (raise `--max-listed`)_"
            )
    lines += [
        "",
        "## 2. EPSG:3857 recomputed independently",
        "",
        "Distance between the `x_3857`/`y_3857` written in the file and the values",
        "recomputed from `latitude`/`longitude`. This script uses",
        "`y = R * atanh(sin phi)`; the generator uses the algebraically identical",
        "`y = R * ln(tan(pi/4 + phi/2))`. Two independently coded forms of one",
        "function, so agreement is evidence and not a second call into the same code.",
        "",
        "The generator rounds the geographic pair to five decimals **before** projecting,",
        "so these numbers also prove the ordering: had it projected first and rounded",
        "afterwards, every row would disagree with itself by up to ~1 m and nothing but",
        "this recomputation would notice.",
        "",
        "| Metric | Metres |",
        "|---|---|",
    ]
    if distances:
        lines += [
            f"| min | {distances[0]:.6f} |",
            f"| median | {percentile(distances, 0.5):.6f} |",
            f"| p95 | {percentile(distances, 0.95):.6f} |",
            f"| max | {distances[-1]:.6f} |",
            f"| tolerance | {tolerance:.6f} |",
        ]
    else:
        lines.append("| _no rows_ | - |")
    lines.append("")
    if worst is not None:
        lines += [
            f"Worst row: `id={worst['id']}` - off by {worst['distance']:.6f} m "
            f"(dx {worst['dx']:+.6f} m, dy {worst['dy']:+.6f} m).",
            "",
            "The tolerance is **not** tightened to that number. CLAUDE.md section 4: a",
            "check calibrated to the current artifact's exact rounding fails on the next",
            "source for a reason that is not an error. The margin between the measured",
            "maximum and the tolerance is the point of printing both.",
            "",
        ]
    if findings["off_tolerance"]:
        top = sorted(findings["off_tolerance"], key=lambda d: d["distance"], reverse=True)
        lines += ["### Rows beyond tolerance", "", "| id | dx (m) | dy (m) | distance (m) |", "|---|---|---|---|"]
        lines += [
            f"| {d['id']} | {d['dx']:+.4f} | {d['dy']:+.4f} | {d['distance']:.4f} |"
            for d in top[:max_listed]
        ]
        lines.append("")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_census.py",
        description=(
            "Verify the coordinate columns of the generated Munster rent census: axis "
            "order, column order, bounding box, and an independent recomputation of the "
            "EPSG:3857 columns. Standard library only, no portal needed. Exit code 0 if "
            "both checks pass, 1 otherwise."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/verify_census.py \\\n"
            "      --input     output/muenster_rent_census.csv \\\n"
            "      --districts input/muenster_districts.json \\\n"
            "      --report    output/verification_report_coordinates.md\n\n"
            "There is no --output flag. CLAUDE.md section 4 requires a path on any flag\n"
            "that writes a file, and the only file this script writes is --report, which\n"
            "has no default for that reason. Unlike csv_data's verifier it writes no\n"
            "corrected copy: nothing here is corrected, because the generator computes\n"
            "the projection rather than remembering it. If a row were wrong, the fix\n"
            "would be the generator - never an edit in output/."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", type=Path, default=Path("output/muenster_rent_census.csv"), metavar="CSV",
        help="CSV to verify (default: %(default)s)",
    )
    parser.add_argument(
        "--districts", type=Path, default=Path("input/muenster_districts.json"),
        metavar="JSON",
        help="districts fixture; its bounding_box is read as data and used as the "
        "expected range (default: %(default)s)",
    )
    parser.add_argument(
        "--report", type=Path, default=None, metavar="MD",
        help="write the Markdown report here. No default on purpose (CLAUDE.md "
        "section 4: no convenient defaults on destructive arguments) - without it the "
        "report goes to stdout and nothing is written",
    )
    parser.add_argument(
        "--tolerance", type=float, default=DEFAULT_TOLERANCE_M, metavar="METRES",
        help="allowed deviation of the EPSG:3857 columns (default: %(default)s)",
    )
    parser.add_argument(
        "--max-listed", type=int, default=50, metavar="N",
        help="maximum individual findings listed per section (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    for path in (args.input, args.districts):
        if not path.is_file():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 1

    try:
        districts, box = load_box(args.districts)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    with args.input.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
    if missing:
        print(
            f"error: {args.input} is missing columns: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1

    findings = check(rows, fieldnames, box, args.tolerance)
    report = render_report(
        findings, args.input, args.districts, districts, box,
        args.tolerance, len(rows), args.max_listed,
    )
    if args.report is None:
        print(report)
    else:
        args.report.write_text(report + "\n", encoding="utf-8")

    check_1_failures = (
        len(findings["column_order"])
        + len(findings["axis_swaps"])
        + len(findings["range_errors"])
        + len(findings["transposed_hits"])
        + len(findings["unparseable"])
    )
    check_2_failures = len(findings["off_tolerance"])
    passed = 2 - (1 if check_1_failures else 0) - (1 if check_2_failures else 0)
    worst = max((d["distance"] for d in findings["deviations"]), default=0.0)
    loud, _ = swap_verdict(box)

    print(
        f"{len(rows):,} rows | checks passed: {passed}/2 | "
        f"axis+range failures: {check_1_failures} | "
        f"max EPSG:3857 deviation: {worst:.6f} m (tolerance {args.tolerance:g} m)"
    )
    print(
        "axis-order check "
        + ("discriminates: the bands are disjoint" if loud else "CANNOT discriminate: the bands overlap")
        + " - but a swapped pair here would still be a legal coordinate, so nothing "
        "downstream would refuse it"
    )
    if args.report is not None:
        print(f"wrote {args.report}")
    return 0 if passed == 2 else 1


if __name__ == "__main__":
    sys.exit(main())
