# Open Data Search — Real NRW Railway Stations

Part of [Test (Geo-)Data Generation with GenAI](../README.md).

The inverse of [`../csv_data/`](../csv_data/). There the LLM **wrote** the data
and the interesting part was catching where it lied. Here the LLM writes no data
at all: it does the web search, the licence triage and the transformation code,
and every coordinate that reaches `output/` was published by DB InfraGO.

| | `csv_data` | this use case |
|---|---|---|
| LLM's role | generator of values | researcher, licence reviewer, code author |
| Coordinates from | the model / a seeded RNG | DB InfraGO, unmodified |
| Data is | fictitious on purpose | real, and legally publishable |
| The hard part | is the maths correct? | is the source usable, and does it mean what it says? |
| Failure found | systematic 490 m projection bias in the data | a wrong *reference* polygon that framed correct data as wrong |

**Result:** `output/nrw_stations.csv` — 449 railway stations in North
Rhine-Westphalia, EPSG:4326 + EPSG:3857, every coordinate traceable to a source
row, CC BY 4.0.

## Purpose

"All railway stations in NRW, from open data" sounds like a download. It is not.
Three questions have to be answered before a single row is written, and only the
third is technical:

1. **Which source exists at all?** Web search, not memory — the URL that every
   tutorial still names for DB station data is dead (see
   [Source selection](#source-selection-and-licence-review)).
2. **May the result be published?** "Open data" is not one licence. The most
   complete source available is unusable in *this* repository for licence
   reasons alone, no matter how good its geometry (see
   [The OSM licence problem](#the-osm-licence-problem)).
3. **Does the data mean what the column names say — and does the yardstick?**
   The source turned out to be trustworthy. The boundary polygon used to check it
   did not (see [Notes for the talk](#notes-for-the-talk)).

## Source selection and licence review

Searched on 2026-08-20 with Claude Opus 5. Every candidate was checked live —
HTTP status, actual columns, actual row counts — not accepted from a search
snippet. The licence was checked **before** the geometry, per
[`../CLAUDE.md`](../CLAUDE.md) §3.

| Candidate | Licence | Live check | Verdict |
|---|---|---|---|
| **DB InfraGO, *Infrastrukturdaten*** ([Mobilithek offer 922109165921083392](https://mobilithek.info/offers/922109165921083392)) | **CC BY 4.0** | 200, 26.7 MB ZIP, `M1 Betriebsstellen.csv` = 10,632 rows, coordinates in 3 CRS | **chosen — station data** |
| **Geobasis NRW, *Digitale Verwaltungsgrenzen* DVG2** ([OpenGeodata.NRW](https://www.opengeodata.nrw.de/produkte/geobasis/vkg/dvg/dvg2/)) | **dl-de/zero-2-0** | 200, 2.5 MB Shapefile ZIP, EPSG:25832, state outline as one feature | **chosen — boundary** |
| OpenStreetMap via [Overpass API](https://overpass-api.de/) | ODbL 1.0 | 200, **534** `railway=station` inside the NRW relation | rejected — share-alike, see below |
| [Wikidata](https://query.wikidata.org/) SPARQL | CC0 1.0 | 200, 1,718 stations in the NRW bounding box; the `P131+` variant times out | rejected — community data, coverage unverifiable against an authority |
| Natural Earth 10m admin-1 | Public domain | 200, 40 MB GeoJSON, NRW = 1 ring, 1,245 vertices | **used first, then replaced** — see finding 1 |
| `download-data.deutschebahn.com/.../D_Bahnhof_2020_alle.CSV` | CC BY 4.0 | **DNS failure** — the host no longer resolves | dead |
| [`data.deutschebahn.com`](https://data.deutschebahn.com/opendata) portal | CC BY 4.0 | 200, but migrating to Mobilithek / GovData / Opendata-ÖPNV | superseded |

The licence ladder that decided it, shortest leash to longest:

| Licence | Attribution | Share-alike | Usable in this CC BY repository? |
|---|---|---|---|
| CC0 1.0 | no | no | yes |
| **dl-de/zero-2-0** | no | no | **yes — the boundary source** |
| Public domain (Natural Earth) | no | no | yes |
| **CC BY 4.0** | **yes** | no | **yes — the station source** |
| dl-de/by-2-0 | yes | no | yes |
| **ODbL 1.0** | yes | **yes** | **no** |

### The OSM licence problem

OpenStreetMap would have been the better data set on every technical axis: 534
stations inside the actual NRW relation, more current than any official export,
one HTTP POST, no ZIP, no deduplication. It was still rejected, and the reason is
worth more to this repository than the data would have been.

- OSM is licensed **ODbL 1.0**, which requires attribution *and* **share-alike**.
- The ODbL distinguishes two things you can make from a database:
  - a **Produced Work** — a map image, a printed atlas, aggregate statistics.
    Needs attribution only.
  - a **Derivative Database** — a filtered, extracted or enriched copy of the
    data itself. Triggers **share-alike**: it must be published under ODbL too.
- A CSV of NRW stations pulled out of OSM is squarely the second kind. It may
  absolutely be published on GitHub — that is what the licence is *for* — but it
  **cannot be relicensed as CC BY**. There is no version of "extract and
  attribute" that gets you out of the share-alike clause.
- Concretely for this repository: `LICENSE` would stay CC BY 4.0 while
  `open_data_search/output/*.csv` sat under ODbL, needing its own licence file
  and its own attribution notice. Legal, and common in the wild ("code MIT, data
  ODbL") — but a contradiction of [`../CLAUDE.md`](../CLAUDE.md) §3 and §11, which
  require everything added here to be CC BY-compatible.
- So the choice was never "which data is better". It was "which licence fits the
  container", and CC BY 4.0 fits while ODbL does not.

OSM was used once more, read-only and outside the pipeline: a single Nominatim
reverse-geocoding query settled finding 1. Asking a service a question is a
Produced Work at most, and nothing from that answer is committed.

What CC BY 4.0 *does* oblige, and what this use case therefore does: name the
source, mark that it was changed. See [Attribution](#attribution).

## Coordinate reference systems

The source ships **three** CRS for every row, which is unusual and turned out to
be useful — redundancy is what lets you find out which representation to
distrust:

| Source columns | CRS | Unit |
|---|---|---|
| `Geographische Länge/Breite (EPSG 4326)` | EPSG:4326 (WGS 84) | decimal degrees, **German decimal comma** |
| `UTM Rechtswert/Hochwert (EPSG 25832)` | EPSG:25832 (ETRS89 / UTM 32N) | metres |
| `GK Rechtswert/Hochwert (EPSG 31467)` | EPSG:31467 (DHDN / Gauß-Krüger 3) | metres |
| `WKT WGS84 / WKT UTM 32N / WKT GK` | the same three | WKT `POINT(...)` |

The boundary arrives in EPSG:25832 and is reprojected to EPSG:4326 during
provisioning, so nothing in the pipeline has to reproject anything.

The output keeps EPSG:4326 and adds EPSG:3857, matching
[`../csv_data/`](../csv_data/) so downstream use cases can read either file:

| Output columns | CRS | Unit | Typical consumer |
|---|---|---|---|
| `latitude`, `longitude` | EPSG:4326 (WGS 84) | decimal degrees | OpenSearch `geo_point`, GeoJSON, GPS |
| `x_3857`, `y_3857` | EPSG:3857 (Web Mercator) | metres | web map tiles, Leaflet/OpenLayers, MapLibre |

Conventions per [`../CLAUDE.md`](../CLAUDE.md) §4: `latitude` before `longitude`,
`x` before `y`, projected columns suffixed with their EPSG code, geographic
coordinates rounded to 5 decimals **before** the projection is derived from them.

## Stack

**Python 3.12 with a local `.venv` and four pinned dependencies** — a deliberate
contrast to `csv_data`, which is standard library only. The dependencies are not
convenience:

| Dependency | Used by | Why |
|---|---|---|
| `requests` 2.34.2 | the two current provisioning scripts | streams a 27 MB and a 2.5 MB ZIP to disk without ceremony |
| `shapely` 2.1.2 | `build_stations.py` | point-in-polygon via GEOS instead of hand-written geometry |
| `pyshp` 3.1.6 | `fetch_nrw_boundary.py` | the authoritative boundary ships as Shapefile only; pure Python, no GDAL needed on the machine |
| `pyproj` 3.7.2 | `fetch_nrw_boundary.py`, `verify_stations.py` | reprojects EPSG:25832 → EPSG:4326, and is **the independent projection implementation** |

That last row is the whole argument for having dependencies here. `csv_data`
satisfied "a verifier must not share its projection implementation with the
generator" by writing the same formula two different ways
(`ln(tan(π/4 + φ/2))` against `atanh(sin φ)`). This use case satisfies it
properly: the builder hand-writes spherical Web Mercator, and the verifier calls
PROJ — a different code base by different authors. Same rule, stronger evidence.
The verifier's containment check is hand-written ray casting for the same reason,
because the builder uses shapely.

`uv` works equally well and is faster if it is installed; the plain `venv`
command below is used because it is available everywhere.

## Input

`input/` is read-only. All fixtures were produced by one-off provisioning
scripts (see [Provisioning](#provisioning)) and are committed, so the pipeline
runs offline.

| File | Size | Description |
|---|---|---|
| `db_infrago_betriebsstellen_nrw.csv` | 658 KB | The 1,671 `Bundesland = Nordrhein-Westfalen` rows of `M1 Betriebsstellen.csv`, all 31 columns, **field values byte-identical to the source** — German decimal commas and all. Only rows were dropped. |
| `db_infrago_source.json` | 2.3 KB | Provenance manifest: source URL, licence, attribution text, retrieval date, SHA-256 and byte size of the exact ZIP, filter applied, row counts, and which columns carry which EPSG code. |
| `nrw_boundary_dvg2.geojson` | 146 KB | **The boundary the pipeline uses.** Authoritative NRW state outline from Geobasis NRW DVG2, data status 2025-11-12, reprojected EPSG:25832 → EPSG:4326, MultiPolygon, 6 parts, 7,130 vertices. |
| `nrw_boundary_ne10m.geojson` | 26 KB | The generalised Natural Earth boundary used **first**, kept as evidence. Off by 1.3 km at the Osnabrück border — see finding 1. Not used by any default; pass it explicitly to reproduce the false positive. |

Why the source slice is committed rather than just its URL: **open-data portals
rot.** The URL every mirror still names for DB station data
(`download-data.deutschebahn.com/...`) does not resolve any more, and
`data.deutschebahn.com` is mid-migration. A documented download command is not
reproducibility if the document outlives the host. The SHA-256 in the manifest is
what makes "we used *this* version" a checkable claim.

Why both boundaries are kept: the delta between them is the most valuable thing
in this folder, and deleting the wrong one would delete the finding with it.

## Output

| File | Rows | Size | Description |
|---|---|---|---|
| `nrw_stations.csv` | 449 | 37 KB | **The deliverable.** One row per station, deduplicated, inside NRW, EPSG:4326 + EPSG:3857. |
| `nrw_stations_raw_positions.csv` | 893 | 45 KB | Every source position before deduplication, with its distance to the station's mean and an `is_medoid` flag. Evidence for [finding 2](#notes-for-the-talk). |
| `verification_report.md` | — | 4 KB | Result of `verify_stations.py`, including the three informational measurements. |

### Schema — `nrw_stations.csv`

| Column | Type | Description |
|---|---|---|
| `ds100` | STRING | DS 100 code (`Kürzel`), the station's unique railway identifier |
| `name` | STRING | `Bezeichnung`, verbatim from the source |
| `district` | STRING | `Kreis`, verbatim from the source |
| `latitude` | DOUBLE | EPSG:4326, 5 decimals |
| `longitude` | DOUBLE | EPSG:4326, 5 decimals |
| `x_3857` | DOUBLE | EPSG:3857 easting in metres, derived from the rounded `longitude` |
| `y_3857` | DOUBLE | EPSG:3857 northing in metres, derived from the rounded `latitude` |
| `source_rows` | INTEGER | how many source rows describe this station (1–15) |
| `position_spread_m` | DOUBLE | maximum distance between those rows' positions, in metres |

`source_rows` and `position_spread_m` are not decoration. They are the station's
positional uncertainty, and a data set that drops them looks more precise than it
is.

### How 1,671 rows become 449 stations

| Step | Rows | Stations | Note |
|---|---|---|---|
| NRW slice of `M1 Betriebsstellen.csv` | 1,671 | — | 17 `Art lang` categories |
| `Art lang == "Bahnhof"` | 905 | 459 | excludes `Haltepunkt` (354), `Abzweigstelle` (194), `Bahnhofsteil` (65), … |
| `Betriebszustand == "in Betrieb"` | 893 | 449 | drops 11 `a.B.` (out of service) and 1 `ehemals` (former) |
| deduplicate by DS 100, medoid position | 449 | 449 | 185 stations had more than one source row |
| inside the authoritative NRW polygon | 449 | 449 | **0 dropped.** The generalised boundary dropped 1 — finding 1 |

**One deliberate exclusion worth knowing about.** The filter is an *exact* match
on `Bahnhof`, so the 8 rows labelled `Bahnhof Abzweigstelle` — a station that is
also a junction — are excluded too. That is 3 stations: `EGST` Geist, `ESMG`
Selmig (Abzw), `KDRA` Düsseldorf-Reisholz Bf Abzw. None of them appears under a
plain `Bahnhof` row, so they are genuinely missing from the 449. Include them
with `--kind "Bahnhof Abzweigstelle"` in a second run if the compound categories
are wanted; a substring match would be the wrong fix, because it would also pull
in the `Haltepunkt`-prefixed compounds.

## Setup

```bash
cd open_data_search
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

With `uv` instead: `uv venv && uv pip install -r requirements.txt`.

## Usage

The pipeline runs **offline** from the committed fixtures. This is the part to
demo live:

```bash
cd open_data_search

# Build the station CSV from the committed source slice
.venv/bin/python scripts/build_stations.py \
    --input      input/db_infrago_betriebsstellen_nrw.csv \
    --boundary   input/nrw_boundary_dvg2.geojson \
    --output     output/nrw_stations.csv \
    --raw-output output/nrw_stations_raw_positions.csv

# Verify it against the source and against the geometry
.venv/bin/python scripts/verify_stations.py \
    --input  output/nrw_stations.csv \
    --source input/db_infrago_betriebsstellen_nrw.csv \
    --report output/verification_report.md
```

All defaults match the paths above, so both commands also work bare. Both run in
about a second. Every script supports `--help`.

Reproduce finding 1 — the generalised boundary drops a station the authoritative
one keeps:

```bash
.venv/bin/python scripts/build_stations.py \
    --boundary   input/nrw_boundary_ne10m.geojson \
    --output     build/nrw_stations_ne10m.csv \
    --raw-output build/nrw_raw_ne10m.csv
# stations outside Nordrhein-Westfalen: 1
#   dropped: HOE Osnabrück-Eversburg at 52.30738, 7.98927
diff <(cut -d, -f1 output/nrw_stations.csv) <(cut -d, -f1 build/nrw_stations_ne10m.csv)
```

### Provisioning

These three need network access and **normally never run again** — their output
is committed. They are the documented [`../CLAUDE.md`](../CLAUDE.md) §3 exception
that may write into `input/`, and they are not part of the pipeline:

```bash
# Authoritative NRW boundary from Geobasis NRW (downloads 2.5 MB, keeps 146 KB)
.venv/bin/python scripts/fetch_nrw_boundary.py \
    --output input/nrw_boundary_dvg2.geojson

# DB InfraGO source slice + provenance manifest (downloads 27 MB into build/)
.venv/bin/python scripts/fetch_infrago_source.py \
    --output-csv      input/db_infrago_betriebsstellen_nrw.csv \
    --output-manifest input/db_infrago_source.json

# Superseded: the generalised Natural Earth boundary, kept to reproduce finding 1
.venv/bin/python scripts/fetch_nrw_boundary_ne10m.py \
    --output input/nrw_boundary_ne10m.geojson
```

### Example output

`scripts/build_stations.py`:

```
source: input/db_infrago_betriebsstellen_nrw.csv | 1,671 rows, 31 columns
filter Art lang == 'Bahnhof': 905 rows (of 17 categories in the source)
filter Betriebszustand == 'in Betrieb': 893 rows (12 dropped, states removed: a.B., ehemals)
distinct stations by Kürzel: 449
stations outside Nordrhein-Westfalen: 0
per-station position spread: median 0 m over all 449 stations, 326 m over the 185 with more than one source row | max 4,047 m
wrote output/nrw_stations.csv | 449 stations, 37.2 KB
wrote output/nrw_stations_raw_positions.csv | 893 source positions, 45.0 KB
```

`output/nrw_stations.csv`:

```csv
ds100,name,district,latitude,longitude,x_3857,y_3857,source_rows,position_spread_m
KA,Aachen Hbf,Kreis Städteregion Aachen,50.76756,6.09124,678073.74,6580280.31,3,632.1
KAW,Aachen West,Kreis Städteregion Aachen,50.78038,6.07104,675825.08,6582537.05,3,594.1
KARE,Aachen-Rothe Erde,Kreis Städteregion Aachen,50.76830,6.11329,680528.33,6580410.56,2,314.7
EAHS,Ahaus,Kreis Borken,52.08199,7.01647,781069.87,6814963.90,2,224.3
KKER,Köln-Ehrenfeld,Kreisfreie Stadt Köln,50.95034,6.90557,768724.54,6612514.14,6,4047.1
EWAN,Wanne-Eickel Hbf,Kreisfreie Stadt Herne,51.53007,7.16702,797829.02,6715598.04,12,3012.9
```

## Verification

`scripts/verify_stations.py` runs six structural checks that set the exit code,
plus three informational measurements.

| Check | Independent of the builder because | Result |
|---|---|---|
| Schema and column types | — | PASS, 0 violations |
| DS 100 uniqueness | — | PASS, 0 duplicates |
| **Provenance** — every coordinate exists in the source under the same DS 100 code | reads `input/`, not the builder | PASS, 0 untraceable |
| Axis order (latitude/longitude not swapped) | the NRW bands don't overlap: lat 50.32–52.53, lon 5.87–9.46 | PASS, 0 suspected swaps |
| Bounding box | derived from the boundary fixture | PASS, 0 violations |
| Polygon containment | hand-written ray casting vs. the builder's shapely | PASS, 0 outside |
| EPSG:3857 accuracy | **pyproj (PROJ)** vs. the builder's hand-written formula | PASS, max **0.007 m** |

| Informational measurement | Result |
|---|---|
| The source's EPSG:25832 columns recomputed from its own EPSG:4326 columns | agree to **1 mm** — the two are consistent |
| The source's numeric EPSG:4326 columns vs. its own `WKT WGS84` column | disagree by a median of **1.27 m**, max 1.86 m |
| Distance from each station to the state border | 99 of 449 close enough to measure; **1 within 250 m** (`HOE`, 117 m) |

The provenance check is the one that has no counterpart in `csv_data`, and it is
the one that matters most for a use case whose whole claim is "nothing was
invented". It asserts that every output coordinate is a coordinate DB InfraGO
published for that station, rounded to 5 decimals and otherwise untouched.

Both negative tests bite:

| Tampering | What catches it |
|---|---|
| Swap the `latitude` and `longitude` columns | provenance, axis order, bounding box, containment **and** the projection check — 449/449 rows, minimum deviation 7,383 km. Exit 1. |
| Change one coordinate to a plausible spot inside NRW | **provenance only.** Every geometric check still passes. Exit 1. |

That second row is the point: "is this point plausible?" and "did anyone actually
publish this point?" are different questions, and only the second one catches a
hallucination.

Reproducibility: deleting all of `output/` and re-running the builder produces
byte-identical files (verified by checksum).

## Attribution

CC BY 4.0 requires naming the source and marking changes. Both are recorded in
`input/db_infrago_source.json` and repeated here:

> Data source: **DB InfraGO AG / Deutsche Bahn AG — Infrastrukturdaten der DB
> InfraGO**, retrieved 2026-08-20 from the
> [Mobilithek](https://mobilithek.info/offers/922109165921083392), licensed under
> [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
> **Changed:** filtered to `Bundesland = Nordrhein-Westfalen`,
> `Art lang = Bahnhof` and `Betriebszustand = in Betrieb`; deduplicated to one
> position per station; coordinates rounded to 5 decimals; EPSG:3857 columns
> derived.

Boundary: **Land NRW / Geobasis NRW — Digitale Verwaltungsgrenzen (DVG2)**, data
status 2025-11-12, `Datenlizenz Deutschland – Zero – Version 2.0` (no conditions,
attribution given voluntarily). Superseded fixture: Natural Earth
`ne_10m_admin_1_states_provinces`, public domain.

Anyone reusing `output/nrw_stations.csv` inherits the CC BY attribution
obligation for the DB data.

## Reproducibility

- **Source data:** DB InfraGO `Infrastrukturdaten`, retrieved **2026-08-20**,
  ZIP SHA-256 `1fa5267cab954d8393878f7bb2396bf9ebb16f914701733c145c073f7e707f36`
  (27,944,910 bytes). Recorded in `input/db_infrago_source.json`.
- **Boundary:** Geobasis NRW DVG2, retrieved 2026-08-20, provider's data status
  2025-11-12. Recorded in the fixture's own properties.
- **GenAI involvement:** web search, licence assessment, source selection and all
  code in `scripts/` — **Claude Opus 5, 2026-08-20**. No data values.
- **Determinism:** no randomness anywhere. There is no `--seed` because there is
  nothing to seed; the same input files always produce the same output. The
  medoid tie-break is by source order, so even ties are deterministic.
- **Exact commands:** see [Usage](#usage). Both pipeline commands run offline.
- **Full downloads:** the 27 MB and 2.5 MB ZIPs and everything extracted from
  them land in `build/` and are gitignored. Committed are the 658 KB NRW slice
  and the 146 KB boundary.

## Notes for the talk

- **The LLM's contribution was research, not data — and it was the expensive
  part.** Finding a source that is current, complete enough, coordinate-bearing
  *and* licence-compatible took seven candidates, six live HTTP checks and one
  DNS failure. Writing the transformation afterwards was the easy half. That
  inversion is the story: for real geodata, the search and the licence review
  *are* the work.

- **"Open data" is not one licence, and the licence decides before the geometry
  does.** OSM was the best data set on every technical axis and was still
  unusable here, because ODbL share-alike does not fit a CC BY container. The
  distinction to remember is Derivative Database (share-alike bites) vs. Produced
  Work (attribution only). CC0, dl-de/zero-2-0 and public domain cost nothing;
  CC BY costs a sentence; ODbL costs your project's licence.

- **Finding 1: when a check fails, suspect the check.** The pipeline's job was to
  referee the source's `Bundesland` attribute against geometry, and it fired: one
  station, `HOE` **Osnabrück-Eversburg**, tagged `Nordrhein-Westfalen` /
  `Kreis Steinfurt` but 1.3 km outside the polygon. The name says Osnabrück,
  Lower Saxony. Every instinct said *found one — official data is wrong*, and
  that conclusion was written down. It was false. Reverse geocoding puts the
  coordinate in **Lotte, Kreis Steinfurt, NRW**; the authoritative Geobasis NRW
  boundary puts it **117 m inside** the state. The generalised Natural Earth
  outline was the thing that was wrong, by 1.3 km, and it framed correct data as
  an error. Switching to the authoritative boundary and re-running against the
  whole German data set: the source's `Bundesland` column and the geometry
  disagree **0 times in either direction** across all 5,367 in-service `Bahnhof`
  rows. The lesson is not "check your attributes against geometry" — that part
  worked. It is that **your reference data is data too**, and a 1:10 M outline is
  not a yardstick for a 100 m question.

- **Finding 2: a station has no single position.** The source is route-centric —
  one `Betriebsstelle` row per `Streckennummer` through it, each carrying that
  route's kilometre-marker coordinate. 893 rows describe 449 stations; 185 of
  them carry several positions, median spread 326 m, worst case **Köln-Ehrenfeld
  at 4,047 m** across 6 rows, and Köln-Mülheim has 15 rows. The obvious
  `dict[key] = row` deduplication silently picks a point up to ~2 km off and
  looks completely clean afterwards. The fix is a medoid — an actually published
  point, still traceable — plus carrying `position_spread_m` into the output so
  the uncertainty is visible instead of discarded.

- **Finding 3: redundancy tells you which column to distrust.** The source
  publishes every point in three CRS plus three WKT strings. Recomputing UTM 32N
  from its own EPSG:4326 columns with pyproj agrees to **1 mm** — so those two are
  consistent and trustworthy. But the numeric EPSG:4326 columns and the
  `WKT WGS84` column of the *same row* differ by a median of **1.27 m** (max
  1.86 m). Two derivations of one point, and the redundancy is what identifies
  the WKT column as the odd one out. Without the third representation you would
  only know they disagree, not which to believe.

- **The provenance check is the one worth stealing.** For generated data you ask
  "is this value plausible?". For sourced data that is the wrong question — the
  right one is "did anyone actually publish this?". Changing one coordinate to a
  perfectly plausible spot inside NRW passes the bounding box, the polygon, the
  axis check and the projection check. Only matching it back against the source
  fixture catches it. It is ~15 lines and it is what makes "we didn't invent
  anything" verifiable rather than asserted.

- **Real dependencies bought real independence.** `csv_data` had to verify its
  projection by writing the same formula a second way. Here the builder
  hand-writes Web Mercator and the verifier calls PROJ; agreement to 0.007 m
  across 449 rows is evidence from a genuinely separate implementation. Isolate
  dependencies per use case, and spend them where independence is the point.

- **How deep should verification go? That is a decision, not a default.** This
  use case ended up reverse-geocoding a single station, downloading an
  authoritative Shapefile, adding a fourth dependency and re-running a check
  across all of Germany — to adjudicate **one row out of 449**. For real,
  published, attributed geodata that was the right call, and it produced the best
  finding in the folder. For *test data* it would often be over-engineering:
  nobody needs a survey-grade boundary to populate a staging database. The
  problem is that the agent cannot tell which situation it is in, and defaults to
  rigour. So make it explicit — agree the tolerance up front ("plausible is
  enough" vs. "must be defensible in public"), and let that decide how far the
  checks go. Rigour has a cost, and here the cost was most of the elapsed time.

- **Lesson learned.** Let the LLM find the data and check the licence, then
  distrust everything — including the yardstick. The geometry has to referee the
  attributes, the reference geometry has to be as good as the question, the
  deduplication has to be measured before it is written, and every value that
  reaches `output/` has to be traceable back to a row somebody else published.
