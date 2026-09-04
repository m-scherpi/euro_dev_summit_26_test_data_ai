#!/usr/bin/env python3
"""Locate why a regenerated fixture does not match the committed one.

Written because it happened: rebuilding `input/synthetic_airports.json` on
Windows produced a different SHA-256 than the same seed produced on Linux, at
identical file size and feature count. `Get-FileHash` on the written file
agreed with the hash the generator computed from the string in memory, which
rules out newline translation - so the difference is in the values.

This script answers which values, and why. Run it next to a rebuilt fixture:

    python scripts/diagnose_fixture.py \\
        --committed input/synthetic_airports.json \\
        --rebuilt build/fixture_check.json

It reports the environment, whether the random number sequence is identical
(it should be - the Mersenne Twister is specified bit-for-bit), whether the
libm results are identical (they need not be - C library transcendental
functions are not standardised to the last bit), and then the exact fields that
differ, with the worst deviation in metres.

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import sys
from pathlib import Path

# Reference values measured on Linux x86-64, glibc, CPython 3.12.7 - the
# environment the committed fixture was built in.
LINUX_RNG = {
    "getrandbits": "874904417c869f47",
    "random": "b3a44f022e6c50fe",
    "uniform": "50493d50dc2aea33",
    "shuffle": "91cbcab7a615f439",
    "sample": "2d21b9503f6b9dbc",
    "lognormvariate": "3b72e87e428c5f37",
}

# The libm calls make_airports_fixture.py depends on, as hex floats so the
# comparison is exact rather than "looks the same when printed".
LINUX_LIBM = {
    "sin(radians(51.3))": "0x1.8f949308a4e84p-1",
    "asin(0.7)": "0x1.8d00e692afd95p-1",
    "log(tan(pi/4+radians(39.443626)/2))": "0x1.80254d225a044p-1",
    "log(6291.0)": "0x1.17e66711f7c54p+3",
    "exp(1.234567)": "0x1.b7ec0328d9ebdp+1",
}

SEED = 20260904


def rng_fingerprints() -> dict[str, str]:
    def digest(value) -> str:
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]

    out = {}
    r = random.Random(SEED)
    out["getrandbits"] = digest([r.getrandbits(32) for _ in range(50)])
    r = random.Random(SEED)
    out["random"] = digest([r.random() for _ in range(50)])
    r = random.Random(SEED)
    out["uniform"] = digest([r.uniform(-1e7, 1e7) for _ in range(50)])
    r = random.Random(SEED)
    values = list(range(50))
    r.shuffle(values)
    out["shuffle"] = digest(values)
    r = random.Random(SEED)
    out["sample"] = digest(r.sample(range(50), 10))
    r = random.Random(SEED)
    out["lognormvariate"] = digest(
        [r.lognormvariate(math.log(6291.0), 1.9) for _ in range(50)]
    )
    return out


def libm_fingerprints() -> dict[str, str]:
    return {
        "sin(radians(51.3))": math.sin(math.radians(51.3)).hex(),
        "asin(0.7)": math.asin(0.7).hex(),
        "log(tan(pi/4+radians(39.443626)/2))": math.log(
            math.tan(math.pi / 4 + math.radians(39.443626) / 2)
        ).hex(),
        "log(6291.0)": math.log(6291.0).hex(),
        "exp(1.234567)": math.exp(1.234567).hex(),
    }


def compare_featuresets(committed: Path, rebuilt: Path) -> int:
    left = json.loads(committed.read_text(encoding="utf-8"))
    right = json.loads(rebuilt.read_text(encoding="utf-8"))

    lf, rf = left["features"], right["features"]
    print(f"  features: {len(lf)} committed, {len(rf)} rebuilt")
    if len(lf) != len(rf):
        print("  -> different feature counts; the seed or the count differs")
        return 1

    # Keyed by position, because a differing shuffle would show up as a
    # different order rather than different values.
    order_differs = [
        i
        for i, (a, b) in enumerate(zip(lf, rf))
        if a["attributes"]["locid"] != b["attributes"]["locid"]
    ]
    print(f"  locid order differs at: {len(order_differs)} of {len(lf)} positions")
    if order_differs:
        print(
            "  -> the RANDOM SEQUENCE differs, not just arithmetic. Suspect the "
            "Python version, not libm"
        )

    differing_attributes: dict[str, int] = {}
    geometry_diffs: dict[str, list] = {"x": [], "y": []}
    for a, b in zip(lf, rf):
        for key in a["attributes"]:
            if a["attributes"][key] != b["attributes"][key]:
                differing_attributes[key] = differing_attributes.get(key, 0) + 1
        for axis in ("x", "y"):
            if a["geometry"][axis] != b["geometry"][axis]:
                geometry_diffs[axis].append(
                    (
                        a["attributes"]["locid"],
                        a["geometry"][axis],
                        b["geometry"][axis],
                    )
                )

    print()
    print("  attributes that differ:")
    if differing_attributes:
        for key, count in sorted(differing_attributes.items(), key=lambda kv: -kv[1]):
            print(f"    {key:16s} {count:4d} of {len(lf)}")
    else:
        print("    none - every attribute is identical")

    print()
    print("  geometry that differs:")
    for axis in ("x", "y"):
        rows = geometry_diffs[axis]
        if not rows:
            print(f"    {axis}: none of {len(lf)} - identical")
            continue
        worst = max(abs(one - two) for _locid, one, two in rows)
        locid, one, two = max(rows, key=lambda row: abs(row[1] - row[2]))
        ulps = abs(one - two) / math.ulp(one) if one else float("nan")
        print(f"    {axis}: {len(rows):4d} of {len(lf)}, worst |delta| = {worst:.3e} m")
        print(f"       {locid}: {one!r}")
        print(f"           vs {two!r}")
        print(f"       = {ulps:.1f} ULP, i.e. the last bit(s) of the double")

    print()
    nothing_differs = (
        not geometry_diffs["x"]
        and not geometry_diffs["y"]
        and not differing_attributes
        and not order_differs
    )
    if nothing_differs:
        print("  VERDICT: the two files are identical. Same seed, same bytes.")
        return 0
    only_y = geometry_diffs["y"] and not geometry_diffs["x"]
    if only_y and not differing_attributes and not order_differs:
        print("  VERDICT: only y differs, and only in its final bits.")
        print("  y = R * log(tan(pi/4 + phi/2)) goes through libm twice;")
        print("  x = R * radians(lon) is a multiplication and is exact.")
        print("  The C library's transcendental functions are not standardised")
        print("  to the last bit, so MSVC and glibc disagree there. Since x/y are")
        print("  stored unrounded, that bit survives into the file and the hash.")
        return 0
    print("  VERDICT: not the simple libm case - see the breakdown above.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="diagnose_fixture.py",
        description=(
            "Explain why a rebuilt Esri JSON fixture differs from the committed "
            "one: environment, random sequence, libm results, and a field-level "
            "diff with the worst deviation in metres and in ULPs."
        ),
        epilog=(
            "Example:\n"
            "  python scripts/diagnose_fixture.py \\\n"
            "      --committed input/synthetic_airports.json \\\n"
            "      --rebuilt build/fixture_check.json"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--committed",
        type=Path,
        default=Path("input/synthetic_airports.json"),
        metavar="JSON",
        help="the fixture as committed (default: %(default)s)",
    )
    parser.add_argument(
        "--rebuilt",
        type=Path,
        default=None,
        metavar="JSON",
        help="a freshly generated fixture to compare against. Optional: without "
        "it only the environment and fingerprint sections run",
    )
    args = parser.parse_args()

    print("=== environment ===")
    print(f"  python      {sys.version.split()[0]}")
    print(f"  platform    {platform.system()} {platform.release()} {platform.machine()}")
    print(f"  float repr  {sys.float_repr_style}")
    print(f"  libm        {platform.libc_ver() if hasattr(platform, 'libc_ver') else '?'}")

    print()
    print("=== random sequence (Mersenne Twister: specified bit-for-bit) ===")
    rng_ok = True
    for name, value in rng_fingerprints().items():
        expected = LINUX_RNG[name]
        same = value == expected
        rng_ok &= same
        print(f"  {'same ' if same else 'DIFFER'} {name:16s} {value}"
              + ("" if same else f"  (linux: {expected})"))
    print("  -> the random number sequence is "
          + ("identical, so the seed reproduces" if rng_ok
             else "DIFFERENT - suspect the Python version"))

    print()
    print("=== libm results (NOT standardised to the last bit) ===")
    libm_ok = True
    for name, value in libm_fingerprints().items():
        expected = LINUX_LIBM[name]
        same = value == expected
        libm_ok &= same
        print(f"  {'same ' if same else 'DIFFER'} {name}")
        print(f"         {value}")
        if not same:
            print(f"  linux: {expected}")
    print("  -> the C library's transcendental functions are "
          + ("bit-identical here" if libm_ok else "NOT bit-identical here"))

    if args.rebuilt is None:
        print()
        print("no --rebuilt given; skipping the field-level diff")
        return 0

    for path in (args.committed, args.rebuilt):
        if not path.exists():
            print(f"error: not found: {path}", file=sys.stderr)
            return 2

    print()
    print("=== field-level diff ===")
    return compare_featuresets(args.committed, args.rebuilt)


if __name__ == "__main__":
    sys.exit(main())
