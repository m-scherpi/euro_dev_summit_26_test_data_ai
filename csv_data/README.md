# CSV Test Data Generation

Part of [Test (Geo-)Data Generation with GenAI](../README.md).

Geographic point records as CSV, produced **two different ways** so the two can
be compared directly:

| | Method A — LLM writes the CSV | Method B — seeded generator |
|---|---|---|
| Output | `output/nrw_points_llm_raw.csv` → `nrw_points.csv` | `output/germany_points_10k.csv` |
| Rows | 100 | 10,000 |
| Region | North Rhine-Westphalia | Germany |
| Coordinates from | the model, token by token | `random.Random(seed)` + boundary polygon |
| Projection from | the model, mentally | `math`, in code |
| Prose from | the model, 100 hand-written sentences | LLM-authored component pool |
| Reproducible | **no** | **yes** (`--seed`) |

Both files carry the **same ten columns**, so downstream use cases
(`../opensearch/`, `../egdb_import/`) can read either.

## Purpose

Two things are being tested, and only the second is about data.

1. **Can an LLM produce usable tabular geodata?** Titles, descriptions, an
   INTEGER, a DOUBLE, a BOOLEAN — content accuracy is explicitly irrelevant,
   these are test data.
2. **Are the coordinates actually correct?** Not negotiable: a point in the
   wrong place makes the data set worthless, and a swapped latitude/longitude
   pair is the classic way to get there. So every coordinate is verified against
   a recomputation, and the result is reported rather than assumed.

Method A answered (1) yes and (2) no. Method B is what (2) looks like when the
maths moves into code — see [Notes for the talk](#notes-for-the-talk).

## Coordinate reference systems

Both CSVs carry **both** CRS for the same point:

| Columns | CRS | Unit | Typical consumer |
|---|---|---|---|
| `latitude`, `longitude` | EPSG:4326 (WGS 84) | decimal degrees | OpenSearch `geo_point`, GeoJSON, GPS |
| `x_3857`, `y_3857` | EPSG:3857 (Web Mercator) | metres | web map tiles, Leaflet/OpenLayers, MapLibre |

This resolves a contradiction in the original request, which asked for "decimal
degrees in reference system 3857". Those are mutually exclusive: decimal degrees
are EPSG:4326, EPSG:3857 is metric.

The `_3857` columns turned out to be **unnecessary** for the actual
visualisation use case, and they are kept deliberately anyway, because what they
cost is one of the more useful findings here — see
[The redundant columns](#the-redundant-columns).

Column order is `latitude` before `longitude` (geographic convention) but `x`
before `y` (Cartesian convention). Both are deliberate; the verifier asserts the
former.

## Stack

**Python 3.12, standard library only** (`csv`, `math`, `random`, `argparse`,
`json`, `pathlib`, `urllib`). No virtualenv, no `pip install`, nothing to set up
— chosen so everything here can be run live during the talk from a fresh clone.
`pyproj` would be the production choice for reprojection, but the spherical Web
Mercator forward transform is two lines and exact to millimetres for this
purpose.

## Input

`input/` — read-only for the generation pipeline.

| File | Description |
|---|---|
| `fantasy_places.json` | LLM-authored component pool: 60 title prefixes × 40 cores × 40 suffixes = **96,000** unique title combinations, plus 20 description templates and five filler lists. This is the LLM's contribution to method B. |
| `germany_boundary_ne50m.geojson` | Germany from **Natural Earth 50m**, MultiPolygon, 6 rings, 562 vertices, 12.5 KB. **Public domain**, therefore compatible with this repository's CC BY licence. Produced once by `scripts/fetch_germany_boundary.py`; source and licence are recorded in the feature properties. |
| `nrw_boundary_approx.geojson` | Coarse 28-vertex NRW polygon, sketched by the LLM. Used **only** to report how many method-A points fall outside NRW. Explicitly **not** authoritative. |

### On the boundary data

`deutschlandGeoJSON` (508 vertices, a better-looking outline) was **rejected**:
the repository is archived, states no licence, and its data derives from GADM,
whose terms forbid commercial redistribution. For a repository published under
CC BY that is unusable regardless of how good the geometry is. Natural Earth is
public domain and says so.

Natural Earth at 1:50 M is generalised, and it shows: the East Frisian islands
are absent entirely, and Sylt's northern tip (List) is clipped away. An
independent Monte-Carlo area check puts the polygon at **355,909 km²** against
Germany's actual **357,596 km²** — 0.5 % low, consistent with those missing
islands. Fine for test data, not fine for anything cadastral.

## Output

`output/` — generated artifacts, committed on purpose (later use cases read
them). Safe to delete: everything except `nrw_points_llm_raw.csv` regenerates
from the commands below. That one file does **not** regenerate — it is a one-off
LLM artifact.

| File | Rows | Size | Description |
|---|---|---|---|
| `nrw_points_llm_raw.csv` | 100 | 16 KB | Method A, raw LLM output, unedited. Kept as evidence — its `x_3857`/`y_3857` values are wrong. |
| `nrw_points.csv` | 100 | 16 KB | Method A, usable. Identical to the raw file except that `x_3857`/`y_3857` were recomputed. |
| `germany_points_10k.csv` | 10,000 | 1.94 MB | **Method B.** Fully reproducible from `--seed 20260820`. |
| `verification_report.md` | — | — | Verification of method A. |
| `verification_report_germany.md` | — | — | Verification of method B. |

### Schema

Identical for both files.

| Column | Type | Method A range (NRW) | Method B range (Germany) |
|---|---|---|---|
| `id` | INTEGER | `1..100` | `1..10000` |
| `title` | TEXT | 100 unique | 10,000 unique |
| `description` | TEXT | 100 unique | 9,947 unique |
| `latitude` | DOUBLE | `50.325..52.530` | `47.377..54.893` |
| `longitude` | DOUBLE | `5.880..9.440` | `5.949..14.991` |
| `x_3857` | DOUBLE | `654,559..1,050,856` m | `662,191..1,668,843` m |
| `y_3857` | DOUBLE | `6,502,752..6,896,529` m | `6,003,786..7,341,127` m |
| `visitor_count` | INTEGER | `624..22,910` | `1..25,000` |
| `elevation_m` | DOUBLE | `7.6..724.6` | `-5.0..2,961.9` |
| `is_enchanted` | BOOLEAN | lowercase `true`/`false` | 5,051 true / 4,949 false |

UTF-8, comma-separated, `\n` line endings, `"` quoting only where a value
contains a comma. Coordinates carry 5 decimals (~1.1 m), projected values 2.

**`elevation_m` is uncorrelated with position.** A point on the Baltic coast can
carry an Alpine elevation. Correlating them needs a digital elevation model,
which is out of scope — this is a deliberate, documented limitation rather than
an oversight, and a good illustration of test data whose columns are each valid
and jointly nonsense.

### Point distribution

**Method A** sampled the NRW bounding box `lat 50.32–52.53 / lon 5.87–9.46`.
A bounding box is not a boundary: its corners reach into the Netherlands,
Belgium, Lower Saxony and Rhineland-Palatinate. Measured result — **41 of 100
points fall outside NRW**. Reported, not quietly fixed.

**Method B** rejection-samples against the Germany polygon: draw a candidate in
the bounding box, keep it only if it is inside the boundary. Measured acceptance
**64.4 %** (15,532 candidates for 10,000 points), and **0 of 10,000 points
outside Germany**.

It also samples **equal-area**, which naive code does not. A degree of longitude
spans ~76 km at lat 47 and ~64 km at lat 55, so drawing latitude from a flat
`uniform(lat_min, lat_max)` would have put **1.185×** more points per km² in the
north than in the south. Drawing `sin(latitude)` uniformly instead gives a
measured north/south density ratio of **0.994** — where 1.000 is perfect.

## Setup

None. Python 3.12 or newer, that is all. Only
`scripts/fetch_germany_boundary.py` needs network access, and its output is
committed, so it normally never runs.

## Usage

```bash
cd csv_data

# Generate 10,000 points across Germany (method B)
python3 scripts/generate_points.py --count 10000 --seed 20260820 \
    --boundary input/germany_boundary_ne50m.geojson \
    --places   input/fantasy_places.json \
    --output   output/germany_points_10k.csv

# Verify them - nothing to correct here, so no --output is passed
python3 scripts/verify_coordinates.py \
    --input    output/germany_points_10k.csv \
    --boundary input/germany_boundary_ne50m.geojson \
    --report   output/verification_report_germany.md

# Verify the LLM-written data and write a corrected copy (method A)
python3 scripts/verify_coordinates.py \
    --input  output/nrw_points_llm_raw.csv \
    --output output/nrw_points.csv \
    --report output/verification_report.md

# Report to stdout, write nothing
python3 scripts/verify_coordinates.py --input output/nrw_points.csv

# One-off: re-fetch the Germany boundary (needs network)
python3 scripts/fetch_germany_boundary.py --output input/germany_boundary_ne50m.geojson
```

Every script supports `--help`. `verify_coordinates.py` exits `0` if all
structural checks pass, `1` otherwise; an EPSG:3857 deviation is reported but
never fatal — for method A it is the expected finding.

`--output` and `--report` have **no defaults** on the verifier. That is
deliberate: with a default, verifying one data set silently overwrote another
(see [Notes for the talk](#notes-for-the-talk)).

### Example output

```
$ python3 scripts/generate_points.py
boundary: Germany | 6 ring(s), 562 vertices | lat 47.279..55.059 / lon 5.858..15.017
pool: 96,000 unique title combinations
wrote output/germany_points_10k.csv | 10,000 rows, 1.94 MB | seed 20260820
rejection sampling: 15,532 candidates for 10,000 points (64.4% accepted) | 10,000 unique titles

$ python3 scripts/verify_coordinates.py --input output/germany_points_10k.csv \
      --boundary input/germany_boundary_ne50m.geojson
10,000 rows checked | structural failures: 0 | max EPSG:3857 deviation: 0.01 m | outside Germany: 0
```

10,000 rows take **0.75 s** end to end.

First data row of `output/germany_points_10k.csv`:

```csv
id,title,description,latitude,longitude,x_3857,y_3857,visitor_count,elevation_m,is_enchanted
1,Greencrag Bridge,Visitors describe this drovers' shelter under a stand of nine poplars as unaccountably tidy; the guides add that the roof timbers came from somewhere considerably older.,54.33453,10.43638,1161772.51,7233768.58,17302,2884.8,true
```

## Verification

Four checks per row, plus one informational.

| Check | Method A (100 rows) | Method B (10,000 rows) |
|---|---|---|
| **Axis order** — `latitude` in the latitude band, `longitude` in the longitude band. The bands do not overlap, so a swap fails loudly. | **PASS**, 0 swaps | **PASS**, 0 swaps |
| **Bounding box** | **PASS**, 0 violations | **PASS**, 0 violations |
| **Column types** — INTEGER / DOUBLE / BOOLEAN parse | **PASS**, 0 violations | **PASS**, 0 violations |
| **EPSG:3857 accuracy** — recomputed and compared in metres | **FAIL**, 100/100 rows off | **PASS**, max 0.01 m |
| Boundary containment (informational) | 41 of 100 outside NRW | **0 of 10,000** outside Germany |

### The verifier is independent of the generator

The two implement the same projection **separately**, so agreement is evidence
rather than a tautology:

| File | Formula |
|---|---|
| `scripts/generate_points.py` | `y = R · ln(tan(π/4 + φ/2))` |
| `scripts/verify_coordinates.py` | `y = R · atanh(sin φ)` |

Only plane geometry is shared, via `scripts/geo.py`, which carries no projection
maths at all. Measured agreement on the 10,000-row file: **0.01 m**, which is
just the two-decimal rounding of the stored values.

### Method A's error, measured

| Metric | Deviation |
|---|---|
| min | 18.47 m |
| median | 393.87 m |
| mean | 333.49 m |
| p95 | 485.99 m |
| max | 490.29 m (row `id=1`) |

Split by axis, which is where it gets instructive:

| Axis | Formula | Max error, method A | Max error, method B |
|---|---|---|---|
| `x_3857` | `radians(lon) · R` — one multiplication | **0.06 m** | 0.01 m |
| `y_3857` | `R · ln(tan(π/4 + radians(lat)/2))` | **490.29 m** | 0.01 m |

The error sits almost entirely in `y`, and it is **positive in all 100 rows** —
every point landed too far north.

### The redundant columns

`x_3857`/`y_3857` are fully derivable from `latitude`/`longitude`. Keeping them
costs, measured on the 10,000-row file, **212 KB of 1,983 KB — 10.7 % of the
file** — and creates a second source of truth that can drift from the first.
It did drift, immediately: the generator initially projected the *unrounded*
coordinates while writing 5 decimals to the CSV, leaving every row internally
inconsistent by up to **1.09 m**. Rounding before projecting fixed it. Anyone
recomputing the projection from the committed file now gets the stored numbers
back.

For the actual visualisation use case these columns were never needed. They are
kept because 490 m of systematic error in columns nobody wanted is a better
story than a clean file.

## Reproducibility

**Method A is not reproducible, by design.** Direct LLM authorship means no seed
and no generator to re-run; a second prompt would produce 100 different rows.

**Method B is fully reproducible.** Verified in both directions: the same seed
twice produces byte-identical files (`cmp` clean), and `--seed 1` produces a
different file.

- **Model:** Claude Opus 5 (`claude-opus-5[1m]`), 2026-08-20 — method A's rows
  and method B's `input/fantasy_places.json`
- **Seed:** `20260820` (method B default), `--seed` to change; method A has none
- **Exact commands:** see [Usage](#usage) — the committed output came from those
  invocations verbatim
- **Determinism caveat:** guaranteed for the same Python major version and the
  same input files. `random.Random` is a Mersenne Twister and stable in
  practice, but a different `fantasy_places.json` changes everything downstream
  of it.
- **Corrected columns in `nrw_points.csv`:** `x_3857` and `y_3857` only. Every
  other value is byte-identical to the raw LLM output.

## Notes for the talk

- **What the LLM did well, both times.** Method A: 100 unique titles, 100
  distinct descriptions, plausible ranges, correct CSV quoting, and — the one
  thing explicitly demanded — latitude and longitude never swapped in any of the
  100 rows. Method B: the component pool is the part a script could never have
  written. Prose is where GenAI earns its place.

- **What it did badly, and how.** All 100 EPSG:3857 rows, by up to 490 m. The
  shape of the failure is the lesson: `x_3857` needs one multiplication and is
  correct to 6 cm; `y_3857` needs `ln(tan(…))`, so the model interpolated
  between remembered anchor latitudes instead. Interpolating a convex function
  along a chord always overshoots — hence a **systematic northward bias in 100
  of 100 rows**. A directional bias survives averaging and spot-checking. Every
  point still sat in NRW, nothing looked broken. Only recomputation found it.

- **Scaling fixed the maths and cost the prose.** 100 hand-written descriptions
  were 100 distinct sentences. 10,000 template-generated ones are 9,947 distinct
  strings that are *structurally* far more repetitive. Method B is 100× the data
  and measurably worse writing. That trade is the honest headline of this use
  case.

- **A bounding box is not a boundary — quantified twice.** Method A: 41 of 100
  points outside NRW. Method B rejection-samples against a real polygon and hits
  0 of 10,000 outside, at a cost of 55 % more candidate draws. The fix is four
  lines and one licence-checked input file.

- **Uniform is not uniform.** `uniform(lat_min, lat_max)` over Germany would
  have over-sampled the north by 18.5 %. It looks like uniform sampling, passes
  every check in this repository, and is wrong. Sampling `sin(latitude)`
  instead measures out at a 0.994 density ratio.

- **The licence is part of the data quality.** The better-looking German outline
  had no usable licence, so it could not be used at any quality. That check
  happens before the geometry check, not after.

- **Two bugs of my own, worth more than the successes.** (1) The verifier's
  `--output` defaulted to `output/nrw_points.csv`; verifying the *Germany* file
  therefore overwrote the *NRW* file. A convenient default turned a read-only
  operation into a destructive one. There is no default now. (2) The generator
  projected unrounded coordinates and stored rounded ones, so every row
  disagreed with itself by up to 1.09 m — invisible until an independent
  recomputation compared them. Both were found by the verification, not by
  reading the code.

- **Lesson learned.** Let the LLM write the prose and the fixtures; let code
  own every number that has a formula behind it — and have something
  independent recompute the numbers, because the errors that matter look
  entirely plausible in the data.
