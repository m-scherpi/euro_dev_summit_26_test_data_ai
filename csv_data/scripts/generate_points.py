#!/usr/bin/env python3
"""Generate geographic point test data as CSV - seeded and reproducible.

The counterpart to `output/nrw_points_llm_raw.csv`, which a language model wrote
directly. That file could not be regenerated and its EPSG:3857 columns were off
by up to 490 m. This script keeps the LLM where it is good and moves the maths
into code:

* the prose comes from `input/fantasy_places.json`, an LLM-authored component
  pool - 96,000 title combinations and several million description variants
* the coordinates, numbers and booleans come from a seeded `random.Random`, so
  the same `--seed` always produces byte-identical output
* the projection is computed, not remembered

Two geographic details worth knowing, both easy to get silently wrong:

1. **Uniform in latitude is not uniform on the ground.** A degree of longitude
   spans ~76 km at lat 47 and ~64 km at lat 55, so drawing latitude from a flat
   `uniform(lat_min, lat_max)` over-samples the north. This script draws
   `sin(latitude)` uniformly instead, which is equal-area on a sphere.
2. **A bounding box is not a boundary.** Sampling the box around Germany puts
   roughly 35 % of the points in eight neighbouring countries or at sea, so
   every candidate is rejection-tested against the boundary polygon.

Standard library only - no virtualenv, no install step.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from geo import load_boundary  # noqa: E402  (needs the path above)

# EPSG:3857 uses a sphere of the WGS 84 semi-major axis radius.
EARTH_RADIUS_M = 6378137.0

FIELDNAMES = [
    "id", "title", "description", "latitude", "longitude",
    "x_3857", "y_3857", "visitor_count", "elevation_m", "is_enchanted",
]

# Value ranges for the non-geographic columns. Deliberately plausible for
# Germany as a whole and deliberately NOT correlated with position - see the
# README: a point in Hamburg can carry an Alpine elevation. Fixing that needs a
# digital elevation model, which is out of scope for test data.
VISITOR_COUNT_RANGE = (0, 25_000)
ELEVATION_RANGE_M = (-5.0, 2962.0)  # Neuendorf-Sachsenbande .. Zugspitze
ENCHANTED_PROBABILITY = 0.5

# Guard against an unsatisfiable --count: rejection sampling and title
# uniqueness both retry, so a bad pool must fail loudly rather than spin.
MAX_TRIALS_PER_POINT = 200


def lonlat_to_web_mercator(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Project EPSG:4326 decimal degrees to EPSG:3857 metres.

    Uses the textbook form `y = R * ln(tan(pi/4 + phi/2))`. The verifier
    implements the equivalent `R * atanh(sin(phi))` independently, so that
    checking this output is evidence rather than a tautology.

    Longitude first, then latitude - matching the x/y order of the result.
    """
    x = math.radians(lon_deg) * EARTH_RADIUS_M
    y = EARTH_RADIUS_M * math.log(math.tan(math.pi / 4.0 + math.radians(lat_deg) / 2.0))
    return x, y


def load_places(path: Path) -> dict:
    """Read and validate the LLM-authored component pool."""
    pool = json.loads(path.read_text(encoding="utf-8"))
    required = (
        "title_prefixes", "title_cores", "title_suffixes",
        "description_templates", "description_fillers",
    )
    missing = [key for key in required if not pool.get(key)]
    if missing:
        raise ValueError(f"{path} is missing or has empty keys: {', '.join(missing)}")
    return pool


def title_capacity(pool: dict) -> int:
    return (
        len(pool["title_prefixes"]) * len(pool["title_cores"]) * len(pool["title_suffixes"])
    )


def make_title(rng: random.Random, pool: dict) -> str:
    return (
        f"{rng.choice(pool['title_prefixes'])}{rng.choice(pool['title_cores'])} "
        f"{rng.choice(pool['title_suffixes'])}"
    )


def make_description(rng: random.Random, pool: dict) -> str:
    """Fill one template. Every filler is drawn on every call, whether the
    chosen template uses it or not, so the random stream stays independent of
    which template came up - that keeps output stable if templates are
    reordered."""
    fillers = {key: rng.choice(values) for key, values in pool["description_fillers"].items()}
    return rng.choice(pool["description_templates"]).format(**fillers)


def sample_point(rng: random.Random, boundary, bounds) -> tuple[float, float, int]:
    """Draw one equal-area point inside the boundary. Returns (lat, lon, trials)."""
    lon_min, lon_max, lat_min, lat_max = bounds
    sin_min = math.sin(math.radians(lat_min))
    sin_max = math.sin(math.radians(lat_max))

    for trial in range(1, MAX_TRIALS_PER_POINT + 1):
        # Equal-area on a sphere: uniform in sin(latitude), not in latitude.
        lat = math.degrees(math.asin(rng.uniform(sin_min, sin_max)))
        lon = rng.uniform(lon_min, lon_max)
        if boundary is None or boundary.contains(lon, lat):
            return lat, lon, trial
    raise RuntimeError(
        f"no point inside {boundary.name if boundary else 'bounds'} after "
        f"{MAX_TRIALS_PER_POINT} attempts - is the boundary polygon degenerate?"
    )


def generate(count: int, seed: int, boundary, pool: dict) -> tuple[list[dict], dict]:
    """Generate `count` rows. Returns (rows, statistics)."""
    capacity = title_capacity(pool)
    if capacity < count:
        raise ValueError(
            f"the title pool yields {capacity:,} unique combinations, which cannot "
            f"fill --count {count:,}. Add prefixes, cores or suffixes to "
            f"input/fantasy_places.json."
        )

    rng = random.Random(seed)
    bounds = boundary.bounds if boundary is not None else None
    rows: list[dict] = []
    seen_titles: set[str] = set()
    point_trials = 0
    title_trials = 0

    for row_id in range(1, count + 1):
        lat, lon, trials = sample_point(rng, boundary, bounds)
        point_trials += trials

        for attempt in range(1, MAX_TRIALS_PER_POINT + 1):
            title = make_title(rng, pool)
            title_trials += 1
            if title not in seen_titles:
                break
        else:
            raise RuntimeError(
                f"could not find an unused title after {MAX_TRIALS_PER_POINT} "
                f"attempts at row {row_id} - the pool is too small for --count"
            )
        seen_titles.add(title)

        # Round FIRST, then project. The CSV stores 5 decimals (~1.1 m), so
        # projecting the unrounded value would leave x_3857/y_3857 disagreeing
        # with the latitude/longitude in the same row by up to ~1 m. Anyone
        # recomputing the projection from this file must get these numbers back.
        lat = round(lat, 5)
        lon = round(lon, 5)
        x, y = lonlat_to_web_mercator(lon, lat)
        rows.append(
            {
                "id": row_id,
                "title": title,
                "description": make_description(rng, pool),
                "latitude": f"{lat:.5f}",
                "longitude": f"{lon:.5f}",
                "x_3857": f"{x:.2f}",
                "y_3857": f"{y:.2f}",
                "visitor_count": rng.randint(*VISITOR_COUNT_RANGE),
                "elevation_m": f"{rng.uniform(*ELEVATION_RANGE_M):.1f}",
                "is_enchanted": "true" if rng.random() < ENCHANTED_PROBABILITY else "false",
            }
        )

    statistics = {
        "count": count,
        "point_trials": point_trials,
        "acceptance": count / point_trials if point_trials else 0.0,
        "title_trials": title_trials,
        "title_capacity": capacity,
        "unique_titles": len(seen_titles),
    }
    return rows, statistics


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_points.py",
        description=(
            "Generate geographic point test data as CSV. Coordinates are sampled "
            "equal-area inside a boundary polygon and projected to EPSG:3857 in "
            "code; titles and descriptions are combined from an LLM-authored "
            "component pool. Same --seed, same input files, byte-identical output."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/generate_points.py --count 10000 --seed 20260820 \\\n"
            "      --boundary input/germany_boundary_ne50m.geojson \\\n"
            "      --places   input/fantasy_places.json \\\n"
            "      --output   output/germany_points_10k.csv\n\n"
            "Columns match output/nrw_points.csv exactly, so downstream code can "
            "read either file."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--count", type=int, default=10_000, metavar="N",
        help="number of points to generate (default: %(default)s)",
    )
    parser.add_argument(
        "--seed", type=int, default=20260820, metavar="INT",
        help="random seed; the same value reproduces the same file "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--boundary", type=Path, default=Path("input/germany_boundary_ne50m.geojson"),
        metavar="GEOJSON",
        help="boundary polygon to sample inside; its bounding box is the "
        "sampling domain (default: %(default)s)",
    )
    parser.add_argument(
        "--places", type=Path, default=Path("input/fantasy_places.json"),
        metavar="JSON",
        help="LLM-authored component pool for titles and descriptions "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output/germany_points_10k.csv"),
        metavar="CSV", help="where to write the CSV (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.count < 1:
        print("error: --count must be at least 1", file=sys.stderr)
        return 1
    for path in (args.boundary, args.places):
        if not path.is_file():
            print(f"error: input file not found: {path}", file=sys.stderr)
            return 1

    boundary = load_boundary(args.boundary)
    pool = load_places(args.places)

    lon_min, lon_max, lat_min, lat_max = boundary.bounds
    print(
        f"boundary: {boundary.name} | {boundary.ring_count} ring(s), "
        f"{boundary.vertex_count} vertices | "
        f"lat {lat_min:.3f}..{lat_max:.3f} / lon {lon_min:.3f}..{lon_max:.3f}"
    )
    print(f"pool: {title_capacity(pool):,} unique title combinations")

    try:
        rows, statistics = generate(args.count, args.seed, boundary, pool)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_csv(args.output, rows)
    size_mb = args.output.stat().st_size / 1_048_576
    print(
        f"wrote {args.output} | {statistics['count']:,} rows, {size_mb:.2f} MB | "
        f"seed {args.seed}"
    )
    print(
        f"rejection sampling: {statistics['point_trials']:,} candidates for "
        f"{statistics['count']:,} points ({statistics['acceptance']:.1%} accepted) | "
        f"{statistics['unique_titles']:,} unique titles"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
