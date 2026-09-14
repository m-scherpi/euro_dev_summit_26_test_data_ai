#!/usr/bin/env python3
"""Generate a fictitious rent-price census for Munster as CSV - seeded and reproducible.

This is the first stage of `portal_publish`, and the only stage that invents
anything. Every later stage transports what this one wrote: into a CSV item,
into a hosted feature layer, into a web map with four renderers.

Nothing in the output is real. There is no rent index, no register and no
census behind it, and that is the point of the use case rather than a
limitation of it - CLAUDE.md section 11: real data may not be published here,
which is exactly why generated test data is needed. The consequence for
verification is stated in the README and worth repeating in the code: "is this
value plausible?" is the wrong question about invented data. What gets verified
is the geometry and the schema, not the realism.

Three geographic details this script gets right on purpose, each of which is
easy to get silently wrong:

1. **Round first, then project.** The CSV stores five decimals of latitude and
   longitude (~1.1 m). Projecting the unrounded value would leave `x_3857` and
   `y_3857` disagreeing with the `latitude`/`longitude` in their own row by up
   to a metre, and nothing but an independent recomputation would notice.
2. **A degree of longitude is shorter than a degree of latitude.** A circular
   scatter on the ground needs a longitude sigma of `sigma / cos(latitude)` -
   at Munster's 51.96 degrees that is a factor of 1.62. Using the same sigma
   for both axes produces districts that are visibly squashed east-west, which
   in a heatmap reads as structure that is not there.
3. **A hash-pinned artifact must not store a raw float that came out of libm.**
   `random.gauss` runs through `log`, `sqrt` and `cos`, and C transcendental
   functions are not standardised to the last bit - measured in `opensearch`,
   where 30 of 880 projected values differed by up to 2 ULP between Linux and
   Windows and changed the file's SHA-256. Every value written here is
   therefore rounded, and the rounding only helps while no unrounded value sits
   near a rounding boundary. So the margin is **measured on the unrounded
   values** and the script refuses to write a file whose reproducibility would
   be luck. Measuring it on the rounded values would prove nothing, because
   rounding puts them on the grid by definition.

Standard library only - no virtualenv, no install step. The whole design of
this use case is meant to be reviewable with no portal in the room.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from census import (  # noqa: E402  (needs the path above)
    COORD_DECIMALS,
    DEFAULT_COUNT,
    DEFAULT_SEED,
    EARTH_RADIUS_M,
    FIELDNAMES,
    METRE_DECIMALS,
)

# Guard against an unsatisfiable request: the bounding-box rejection and the
# address-uniqueness retry both loop, so a bad fixture must fail loudly rather
# than spin.
MAX_TRIALS_PER_ROW = 500

# How close an unrounded value may come to a rounding boundary before the run
# is refused, expressed as a multiple of the value's own ULP. Measured in
# `opensearch`: the observed cross-platform divergence was up to 2 ULP, so 16
# is eight times the worst case seen and still small enough to be reachable -
# at five decimals of latitude the boundary is ~15x the divergence away, at six
# decimals rounding would not have helped at all.
MIN_MARGIN_ULP = 16

# How many draws to fingerprint. The Mersenne Twister is specified bit for bit
# and survives Python minor versions, so a matching fingerprint rules the RNG
# out as the cause of a differing hash before anybody looks at the values -
# CLAUDE.md section 10, "rule out the boring causes first".
RNG_FINGERPRINT_DRAWS = 32


class FixtureError(Exception):
    """A fixture this generator refuses to guess about."""


def lonlat_to_web_mercator(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """Project EPSG:4326 decimal degrees to EPSG:3857 metres.

    The textbook form `y = R * ln(tan(pi/4 + phi/2))`. `verify_census.py`
    implements the algebraically identical `R * atanh(sin phi)` independently,
    so agreement between the two is evidence rather than a tautology. Neither
    formula lives in `census.py`, which is the whole reason the check means
    anything.

    Longitude first, then latitude - matching the x/y order of the result, and
    the opposite of the CSV's latitude-before-longitude column order. Mixing
    the two up is the single most common way points end up in another
    hemisphere.
    """
    x = math.radians(lon_deg) * EARTH_RADIUS_M
    y = EARTH_RADIUS_M * math.log(math.tan(math.pi / 4.0 + math.radians(lat_deg) / 2.0))
    return x, y


# ---------------------------------------------------------------------------
# Rounding margin
# ---------------------------------------------------------------------------


class MarginTracker:
    """How close did the unrounded values come to a rounding boundary?

    Every value written to the CSV is rounded, which is what makes the file's
    hash reproducible across platforms whose libm disagrees in the last bit.
    That only works while no value sits on a boundary: a value of `x.xxxx5`
    rounds one way with one libm and the other way with another, and a
    single such value changes the file.

    So for each rounded value this records the distance from the unrounded
    value to the nearest boundary, divided by the value's own ULP. The
    reported minimum is the margin the artifact's reproducibility actually
    rests on. It is measured on the **unrounded** value on purpose - the same
    check against the rounded value always passes, because rounding puts the
    value on the grid by definition, which is how the first version of this
    check in `opensearch` was written.
    """

    def __init__(self) -> None:
        self.worst_ratio = math.inf
        self.worst: tuple[str, float, int] | None = None
        self.samples = 0

    def track(self, label: str, value: float, decimals: int) -> float:
        """Record one value's margin and return the rounded value."""
        scale = 10.0**decimals
        scaled = value * scale
        # Distance to the nearest .5 boundary of the scaled value.
        margin_scaled = abs(abs(scaled - math.floor(scaled)) - 0.5)
        ulp = math.ulp(scaled) if scaled else math.ulp(1.0)
        ratio = margin_scaled / ulp
        self.samples += 1
        if ratio < self.worst_ratio:
            self.worst_ratio = ratio
            self.worst = (label, value, decimals)
        return round(value, decimals)

    def track_int(self, label: str, value: float) -> int:
        """Record the margin of a round-to-integer and return the integer."""
        return int(self.track(label, value, 0))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def load_districts(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    districts = data.get("districts")
    if not districts:
        raise FixtureError(f"{path} carries no districts")
    box = data.get("bounding_box")
    for key in ("latitude_min", "latitude_max", "longitude_min", "longitude_max"):
        if box is None or key not in box:
            raise FixtureError(f"{path} is missing bounding_box.{key}")
    for district in districts:
        for key in ("key", "name", "latitude", "longitude", "sigma_deg", "weight"):
            if key not in district:
                raise FixtureError(f"{path}: district {district.get('key')!r} is missing {key!r}")
    return data


def load_fixtures(path: Path, district_keys: list[str]) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        levels = data["district_levels"]["levels"]
        types = data["building_types"]["types"]
        parts = data["street_name_parts"]
        ranges = data["value_ranges"]
    except KeyError as exc:
        raise FixtureError(f"{path} is missing key {exc}") from None

    # A missing level must abort rather than fall back to a default. A silent
    # default would flatten exactly the spatial structure the four renderers
    # exist to show, and it would look like real data doing something dull.
    missing = [k for k in district_keys if k not in levels]
    extra = [k for k in levels if k not in district_keys]
    if missing or extra:
        raise FixtureError(
            f"{path}: district_levels.levels does not match the districts fixture. "
            f"missing: {missing or 'none'} | unknown: {extra or 'none'}"
        )

    type_names = {t["name"] for t in types}
    for key, level in levels.items():
        weights = level.get("building_type_weights", {})
        if set(weights) != type_names:
            raise FixtureError(
                f"{path}: building_type_weights for {key!r} lists {sorted(weights)}, "
                f"but the declared building types are {sorted(type_names)}"
            )
    for name in ("cores", "suffixes"):
        if not parts.get(name):
            raise FixtureError(f"{path}: street_name_parts.{name} is empty")
    for name in ("rent_eur_sqm", "median_age", "household_size", "rooms"):
        if name not in ranges:
            raise FixtureError(f"{path}: value_ranges.{name} is missing")
    return data


def address_capacity(parts: dict) -> int:
    span = parts["number_max"] - parts["number_min"] + 1
    return len(parts["cores"]) * len(parts["suffixes"]) * span


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def weighted_key(rng: random.Random, weights: dict[str, float]) -> str:
    """Draw one key with the given relative weights.

    Written out rather than using `random.choices`, so the number of `random()`
    calls per draw is one and visibly so - the RNG fingerprint that rules the
    generator out as the cause of a differing hash is only useful if the call
    pattern is predictable.
    """
    total = sum(weights.values())
    target = rng.random() * total
    running = 0.0
    for key, weight in weights.items():
        running += weight
        if target < running:
            return key
    return next(reversed(weights))  # pragma: no cover - float tail


def clamp(value: float, low: float, high: float, counter: dict[str, int], label: str) -> float:
    """Clamp and count. A clamp that fires often means the distribution is
    wrong, not that the clamp is working - so the counts are printed."""
    if value < low:
        counter[label] = counter.get(label, 0) + 1
        return low
    if value > high:
        counter[label] = counter.get(label, 0) + 1
        return high
    return value


def sample_position(
    rng: random.Random, district: dict, box: dict, margins: MarginTracker
) -> tuple[float, float, int]:
    """Draw one scattered position inside the bounding box.

    Gaussian around the district centre, with the longitude sigma widened by
    `1 / cos(latitude)` so the scatter is circular on the ground rather than in
    degrees. Candidates outside the box are rejected: the box is what the
    offline verifier checks against, so the generator has to guarantee it
    rather than hope the tail stays inside. The district centres are chosen
    four sigma clear of every edge, so rejection is rare by construction and
    the count is printed to prove it.
    """
    sigma_lat = float(district["sigma_deg"])
    sigma_lon = sigma_lat / math.cos(math.radians(float(district["latitude"])))

    for trial in range(1, MAX_TRIALS_PER_ROW + 1):
        lat_raw = rng.gauss(float(district["latitude"]), sigma_lat)
        lon_raw = rng.gauss(float(district["longitude"]), sigma_lon)
        if not (box["latitude_min"] <= lat_raw <= box["latitude_max"]):
            continue
        if not (box["longitude_min"] <= lon_raw <= box["longitude_max"]):
            continue
        lat = margins.track("latitude", lat_raw, COORD_DECIMALS)
        lon = margins.track("longitude", lon_raw, COORD_DECIMALS)
        return lat, lon, trial
    raise RuntimeError(
        f"no position inside the bounding box for district {district['key']!r} after "
        f"{MAX_TRIALS_PER_ROW} attempts - is sigma_deg larger than the box?"
    )


def generate(count: int, seed: int, districts: dict, fixtures: dict) -> tuple[list[dict], dict]:
    """Generate `count` rows. Returns (rows, statistics)."""
    parts = fixtures["street_name_parts"]
    capacity = address_capacity(parts)
    if capacity < count:
        raise FixtureError(
            f"the street-name pool yields {capacity:,} distinct addresses, which cannot fill "
            f"--count {count:,}. Add cores or suffixes to the fixtures file."
        )

    box = districts["bounding_box"]
    by_key = {d["key"]: d for d in districts["districts"]}
    district_weights = {d["key"]: float(d["weight"]) for d in districts["districts"]}
    levels = fixtures["district_levels"]["levels"]
    types = {t["name"]: t for t in fixtures["building_types"]["types"]}
    area_min = float(fixtures["building_types"]["area_min_sqm"])
    area_max = float(fixtures["building_types"]["area_max_sqm"])
    ranges = fixtures["value_ranges"]
    household_floor = float(ranges["household_size"][0])

    rng = random.Random(seed)
    margins = MarginTracker()
    clamps: dict[str, int] = {}
    rows: list[dict] = []
    seen_addresses: set[str] = set()
    position_trials = 0
    address_trials = 0
    per_district: dict[str, int] = {key: 0 for key in by_key}
    per_type: dict[str, int] = {name: 0 for name in types}

    for row_id in range(1, count + 1):
        district_key = weighted_key(rng, district_weights)
        district = by_key[district_key]
        level = levels[district_key]
        per_district[district_key] += 1

        lat, lon, trials = sample_position(rng, district, box, margins)
        position_trials += trials
        # Round first, then project - so anybody recomputing the projection
        # from this file gets these exact numbers back.
        x_raw, y_raw = lonlat_to_web_mercator(lon, lat)
        x = margins.track("x_3857", x_raw, METRE_DECIMALS)
        y = margins.track("y_3857", y_raw, METRE_DECIMALS)

        for _ in range(MAX_TRIALS_PER_ROW):
            address = (
                f"{rng.choice(parts['cores'])}{rng.choice(parts['suffixes'])} "
                f"{rng.randint(parts['number_min'], parts['number_max'])}"
            )
            address_trials += 1
            if address not in seen_addresses:
                break
        else:  # pragma: no cover - guarded by the capacity check above
            raise RuntimeError(f"no unused address after {MAX_TRIALS_PER_ROW} attempts")
        seen_addresses.add(address)

        type_name = weighted_key(rng, level["building_type_weights"])
        building = types[type_name]
        per_type[type_name] += 1

        year_built = rng.randint(int(building["year_min"]), int(building["year_max"]))

        area_raw = clamp(
            rng.gauss(float(building["area_mean"]), float(building["area_sigma"])),
            area_min, area_max, clamps, "living_area_sqm",
        )
        living_area = margins.track("living_area_sqm", area_raw, 1)

        rooms_raw = clamp(
            area_raw / float(building["sqm_per_room"]),
            float(ranges["rooms"][0]), float(ranges["rooms"][1]), clamps, "rooms",
        )
        rooms = max(int(ranges["rooms"][0]), margins.track_int("rooms", rooms_raw))

        rent_raw = clamp(
            rng.gauss(
                float(level["rent_base_eur_sqm"]) * float(building["rent_factor"]),
                float(level["rent_sigma"]),
            ),
            float(ranges["rent_eur_sqm"][0]), float(ranges["rent_eur_sqm"][1]),
            clamps, "rent_eur_sqm",
        )
        rent = margins.track("rent_eur_sqm", rent_raw, 2)

        age_raw = clamp(
            rng.gauss(float(level["age_mean"]), float(level["age_sigma"])),
            float(ranges["median_age"][0]), float(ranges["median_age"][1]),
            clamps, "median_age",
        )
        median_age = margins.track("median_age", age_raw, 1)

        household_raw = clamp(
            draw_household_size(rng, float(level["household_mean"]), floor=household_floor),
            household_floor, float(ranges["household_size"][1]),
            clamps, "household_size",
        )
        household_size = margins.track("household_size", household_raw, 1)

        rows.append(
            {
                "id": row_id,
                "address": address,
                "district": district["name"],
                "latitude": f"{lat:.{COORD_DECIMALS}f}",
                "longitude": f"{lon:.{COORD_DECIMALS}f}",
                "x_3857": f"{x:.{METRE_DECIMALS}f}",
                "y_3857": f"{y:.{METRE_DECIMALS}f}",
                "rent_eur_sqm": f"{rent:.2f}",
                "living_area_sqm": f"{living_area:.1f}",
                "rooms": rooms,
                "median_age": f"{median_age:.1f}",
                "household_size": f"{household_size:.1f}",
                "building_type": type_name,
                "year_built": year_built,
            }
        )

    statistics = {
        "count": count,
        "seed": seed,
        "position_trials": position_trials,
        "rejected_positions": position_trials - count,
        "address_trials": address_trials,
        "address_capacity": capacity,
        "unique_addresses": len(seen_addresses),
        "per_district": per_district,
        "per_type": per_type,
        "clamps": clamps,
        "margin_samples": margins.samples,
        "margin_ratio": margins.worst_ratio,
        "margin_worst": margins.worst,
    }
    return rows, statistics


# The shape parameter of the household-size distribution. A fixture value would
# be better, and it is not one because the same shape applies to every district
# - a per-district column of identical numbers reads as measured when it is a
# constant. Stated here where it can be seen.
HOUSEHOLD_SHAPE = 2.5


def draw_household_size(rng: random.Random, mean: float, *, floor: float) -> float:
    """Draw one district's average household size.

    Not a Gaussian, and the reason is the clamp counter. A household cannot
    hold fewer than one person, so `floor` is a hard physical bound rather than
    a guard against a fixture typo - and a Gaussian with a mean of 1.6 puts
    roughly a fifth of its mass below it. The first version of this generator
    did exactly that and clamped **37 of 500 rows**, which piles 7 % of the data
    onto the single value 1.0 and would show up in the popup as a suspiciously
    popular number.

    A gamma variate above the floor has the bound built in instead: it is
    positive by construction, right-skewed the way household sizes are, and its
    mean is the fixture's mean by choice of scale. The clamp counter then reports
    what it is for - a distribution that does not fit - rather than the shape of
    the distribution itself. Same lesson as the log-normal tail in `opensearch`,
    from the other end: derive the parameter from the intended spread instead of
    guessing one and absorbing the error in a clamp.
    """
    return floor + rng.gammavariate(HOUSEHOLD_SHAPE, (mean - floor) / HOUSEHOLD_SHAPE)


def rng_fingerprint(seed: int) -> str:
    """A hash of the first draws of the seeded stream.

    Cheap triage for the failure that already happened once in this
    repository: a committed artifact whose SHA-256 differs on another machine.
    If this fingerprint matches and the file's hash does not, the random
    sequence is innocent and the divergence is in the values - which is where
    it was, both times.
    """
    rng = random.Random(seed)
    draws = "".join(float.hex(rng.random()) for _ in range(RNG_FINGERPRINT_DRAWS))
    return hashlib.sha256(draws.encode("ascii")).hexdigest()[:16]


def render_csv(rows: list[dict]) -> str:
    """Render the CSV to a string, so its hash can be taken before it is written.

    Comparing the hash of this string against the hash of the file on disk
    rules out newline translation as the cause of a mismatch - the first of the
    boring causes CLAUDE.md section 10 says to eliminate before suspecting the
    values.
    """
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_census.py",
        description=(
            "Generate a fictitious rent-price census for Munster as CSV. Points are "
            "scattered Gaussian around district centres, rounded to five decimals and "
            "then projected to EPSG:3857 in code; every attribute comes from a seeded "
            "random stream over a committed component pool. Same --seed and same input "
            "files produce a byte-identical file."
        ),
        epilog=(
            "Example:\n"
            "  python3 scripts/generate_census.py --count 500 --seed 20260904 \\\n"
            "      --districts input/muenster_districts.json \\\n"
            "      --fixtures  input/rent_census_fixtures.json \\\n"
            "      --output    output/muenster_rent_census.csv\n\n"
            "Nothing in the output is real. Verify the geometry and the schema with\n"
            "verify_census.py; do not verify the realism - see the README."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT, metavar="N",
        help="number of census points to generate (default: %(default)s)",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, metavar="INT",
        help="random seed; the same value reproduces the same file (default: %(default)s)",
    )
    parser.add_argument(
        "--districts", type=Path, default=Path("input/muenster_districts.json"),
        metavar="JSON",
        help="district centres, sigmas, weights and the sampling bounding box "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--fixtures", type=Path, default=Path("input/rent_census_fixtures.json"),
        metavar="JSON",
        help="building types, street-name parts and per-district levels "
        "(default: %(default)s)",
    )
    parser.add_argument(
        "--output", type=Path, default=None, metavar="CSV",
        help="where to write the CSV. No default on purpose (CLAUDE.md section 4: no "
        "convenient defaults on destructive arguments) - a generator whose --output "
        "defaults to a committed path overwrites one data set while producing another",
    )
    parser.add_argument(
        "--min-margin-ulp", type=float, default=MIN_MARGIN_ULP, metavar="ULP",
        help="refuse to write the file if any unrounded value comes closer than this "
        "many ULP to a rounding boundary, because its hash would then be "
        "reproducible only by luck (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.count < 1:
        print("error: --count must be at least 1", file=sys.stderr)
        return 1
    if args.output is None:
        print(
            "error: --output is required. It has no default so that verifying or "
            "regenerating one data set can never overwrite another.",
            file=sys.stderr,
        )
        return 1
    for path in (args.districts, args.fixtures):
        if not path.is_file():
            print(f"error: input file not found: {path}", file=sys.stderr)
            return 1

    try:
        districts = load_districts(args.districts)
        fixtures = load_fixtures(args.fixtures, [d["key"] for d in districts["districts"]])
    except (FixtureError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    box = districts["bounding_box"]
    print(
        f"districts: {len(districts['districts'])} centres | "
        f"box lat {box['latitude_min']}..{box['latitude_max']} / "
        f"lon {box['longitude_min']}..{box['longitude_max']} | "
        f"authoritative: {districts.get('authoritative')}"
    )
    print(
        f"fixtures: {len(fixtures['building_types']['types'])} building types | "
        f"{address_capacity(fixtures['street_name_parts']):,} distinct addresses"
    )
    print(f"rng fingerprint (seed {args.seed}): {rng_fingerprint(args.seed)}")

    try:
        rows, statistics = generate(args.count, args.seed, districts, fixtures)
    except (FixtureError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    ratio = statistics["margin_ratio"]
    if ratio < args.min_margin_ulp:
        label, value, decimals = statistics["margin_worst"]
        print(
            f"error: {label}={value!r} rounds to {decimals} decimals with a margin of only "
            f"{ratio:.1f} ULP to the rounding boundary. Below --min-margin-ulp "
            f"{args.min_margin_ulp:g} the file's SHA-256 is reproducible by luck rather than "
            f"by construction: libm is not standardised to the last bit, so another platform "
            f"may round this value the other way. Change --seed, or store fewer decimals.",
            file=sys.stderr,
        )
        return 1

    text = render_csv(rows)
    in_memory = hashlib.sha256(text.encode("utf-8")).hexdigest()
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    on_disk = hashlib.sha256(args.output.read_bytes()).hexdigest()

    size_kb = args.output.stat().st_size / 1024
    print(
        f"wrote {args.output} | {statistics['count']:,} rows, {size_kb:.1f} KB | "
        f"seed {statistics['seed']}"
    )
    print(f"sha256: {on_disk}")
    if on_disk != in_memory:
        print(
            "warning: the file's hash differs from the hash of the string that was written "
            "- newline translation is happening somewhere. See .gitattributes.",
            file=sys.stderr,
        )
    print(
        f"rounding margin: worst {ratio:,.1f} ULP over {statistics['margin_samples']:,} "
        f"rounded values (threshold {args.min_margin_ulp:g})"
    )
    print(
        "positions: "
        f"{statistics['rejected_positions']} of {statistics['position_trials']:,} candidates "
        f"rejected outside the box | {statistics['unique_addresses']:,} unique addresses"
    )
    print(
        "per district: "
        + ", ".join(f"{k}={v}" for k, v in sorted(statistics["per_district"].items()))
    )
    print(
        "per building type: "
        + ", ".join(f"{k}={v}" for k, v in sorted(statistics["per_type"].items()))
    )
    print(
        "clamped values: "
        + (", ".join(f"{k}={v}" for k, v in sorted(statistics["clamps"].items())) or "none")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
