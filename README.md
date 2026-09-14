# Test (Geo-)Data Generation with GenAI

A collection of independent, self-contained use cases exploring how generative
AI can be used to produce, transform and validate **test data — with a focus on
geospatial data**.

This repository is the working basis for a conference talk. It is therefore
documented for traceability: every use case records not only its result but the
prompts and iterations that led there. See [`PROMPT.md`](PROMPT.md) for the full
work log and [`CLAUDE.md`](CLAUDE.md) for the conventions all use cases follow.

---

## Repository structure

```
devsummit/
├── CLAUDE.md          # working instructions & conventions
├── README.md          # this file — overview and index
├── PROMPT.md          # chronological log of prompts and work steps
├── slides/            # the conference talk itself, as code (not a use case)
└── <use-case>/
    ├── README.md      # detailed docs for this use case
    ├── input/         # read-only source data
    └── output/        # generated artifacts only
```

Each use case is independent: its own stack, its own dependencies, its own
README. There is no shared build and nothing to install at root level.

`slides/` is the one folder that is not a use case: it holds the presentation
built from these findings, in Markdown, deployed to GitHub Pages.

---

## Use cases

| Folder | Use case | Approach / stack | Status | Docs |
|---|---|---|---|---|
| [`csv_data/`](csv_data/) | Geo points as CSV, two ways: 100 written directly by the LLM vs. 10,000 from a seeded generator — coordinates verified by code either way | Python 3.12, stdlib only | ✅ done | [README](csv_data/README.md) |
| [`open_data_search/`](open_data_search/) | The inverse: the LLM searches, triages licences and writes code, but invents no data — 449 real NRW railway stations from DB InfraGO open data, every coordinate traceable to its source | Python 3.12 + venv (`requests`, `shapely`, `pyshp`, `pyproj`) | ✅ done | [README](open_data_search/README.md) |
| [`opensearch/`](opensearch/) | Two indexes in one cluster from two unrelated sources — the 449 stations from a CSV and 880 airports from an Enterprise Geodatabase export — published through ArcGIS Enterprise as a web feature layer that copies nothing. The `geo_point` format every tutorial shows is the one ArcGIS cannot read, and only 1 of 12 checks notices. The second source arrived as "a GeoJSON" in EPSG:3857 metres and without a licence, so only its structure survived | Shell + Batch, Python 3.12 stdlib only, OpenSearch 2.12.0 | ✅ done | [README](opensearch/README.md) |
| [`egdb_import/`](egdb_import/) | The everyday task: a CSV and an Esri JSON export become real FeatureClasses in a PostgreSQL Enterprise Geodatabase, schema and all, consumed in ArcGIS Pro. Asked for "using the ArcGIS API for Python", which cannot do it — and does not say so: the same call writes a **shapefile** instead, with four field names silently truncated to ten characters and both measured TEXT lengths replaced by the format's maximum. Four different outcomes from one line of code, depending only on what was importable. Two sources through one pipeline: a CSV, and an Esri JSON FeatureSet whose own declared schema beat the measurement — `state_fips` measures as an integer and is `TEXT(2)` holding `01`…`09` | Python 3.12 stdlib (analysis) + arcpy from ArcGIS Pro 3.7 (load & verify) | ✅ done | [README](egdb_import/README.md) |
| [`portal_publish/`](portal_publish/) | The finale: 500 generated Münster rent-census points reach ArcGIS Enterprise as a **Hosted Feature Layer** and a **Web Map with five layers and four renderer types on one service** — the deliberate inverse of `opensearch` (copy all data, not reference) and of `egdb_import` (where that same copy was the defect). Two inversions, same measurement, opposite verdict. The pinned client has **no Web Map class at all** — no `arcgis.map`, no `arcgis.mapping.WebMap`, 0 `arcgis/map/` entries in the wheel's `RECORD` — so the map is hand-built JSON, and every decision it carries is a committed artifact built with no portal in the room | Python 3.12 stdlib (generate, verify, build payloads) + `arcgis` 2.4.1.1 in a local venv (publish & verify) | ✅ published, verified and in the deck | [README](portal_publish/README.md) |

Status legend: 🕓 planned · 🚧 in progress · ✅ done

## The talk

Given at the **Esri European Developer & Technology Summit 2026** as
*Using Agentic AI to Easily Create Geospatial Test Data for Your Infrastructure*.

| Folder | What | Stack | Status | Docs |
|---|---|---|---|---|
| [`slides/`](slides/) | *Using Agentic AI to Easily Create Geospatial Test Data for Your Infrastructure* — the conference presentation as code: two slides per use case (why it exists, then what came out with one finding), seven takeaways, in a hard 15-minute slot | Slidev 52 (Markdown + Vue), GitHub Pages via Actions | ✅ checked against the submitted abstract | [README](slides/README.md) |

Live deck: **https://m-scherpi.github.io/euro_dev_summit_26_test_data_ai/**
(available once the repository is public).

---

## Usage / executables

Central index of everything runnable produced in this repository. Details
always live in the use-case README.

| Tool | Use case | Example command | Docs |
|---|---|---|---|
| `generate_points.py` | `csv_data` | `cd csv_data && python3 scripts/generate_points.py --count 10000 --seed 20260820` | [README](csv_data/README.md#usage) |
| `verify_coordinates.py` | `csv_data` | `cd csv_data && python3 scripts/verify_coordinates.py --input output/nrw_points.csv` | [README](csv_data/README.md#usage) |
| `fetch_germany_boundary.py` | `csv_data` | `cd csv_data && python3 scripts/fetch_germany_boundary.py` (one-off, needs network) | [README](csv_data/README.md#input) |
| `build_stations.py` | `open_data_search` | `cd open_data_search && .venv/bin/python scripts/build_stations.py` | [README](open_data_search/README.md#usage) |
| `verify_stations.py` | `open_data_search` | `cd open_data_search && .venv/bin/python scripts/verify_stations.py --report output/verification_report.md` | [README](open_data_search/README.md#verification) |
| `fetch_infrago_source.py` | `open_data_search` | `cd open_data_search && .venv/bin/python scripts/fetch_infrago_source.py` (one-off, needs network) | [README](open_data_search/README.md#provisioning) |
| `fetch_nrw_boundary.py` | `open_data_search` | `cd open_data_search && .venv/bin/python scripts/fetch_nrw_boundary.py` (one-off, needs network) | [README](open_data_search/README.md#provisioning) |
| `fetch_nrw_boundary_ne10m.py` | `open_data_search` | `cd open_data_search && .venv/bin/python scripts/fetch_nrw_boundary_ne10m.py` (one-off, superseded, kept as evidence) | [README](open_data_search/README.md#provisioning) |
| `setup_opensearch.sh` / `.bat` | `opensearch` | `cd opensearch && ./scripts/setup_opensearch.sh --host localhost` (needs network, ~820 MB) | [README](opensearch/README.md#setup) |
| `run_opensearch.sh` / `.bat` | `opensearch` | `cd opensearch && ./scripts/run_opensearch.sh start` (also `stop`, `status`, `logs`) | [README](opensearch/README.md#setup) |
| `index_stations.py` | `opensearch` | `cd opensearch && python3 scripts/index_stations.py --recreate --host https://localhost:9200 --ca-cert build/tls/root-ca.pem` | [README](opensearch/README.md#usage) |
| `verify_index.py` | `opensearch` | `cd opensearch && python3 scripts/verify_index.py --host https://localhost:9200 --ca-cert build/tls/root-ca.pem --report output/verification_report.md` | [README](opensearch/README.md#verify) |
| `make_airports_fixture.py` | `opensearch` | `cd opensearch && python3 scripts/make_airports_fixture.py --output input/synthetic_airports.json --manifest input/synthetic_airports_source.json` (one-off, output committed) | [README](opensearch/README.md#rebuild-the-fixture-normally-never-needed) |
| `index_airports.py` | `opensearch` | `cd opensearch && python3 scripts/index_airports.py --recreate --host https://localhost:9200 --ca-cert build/tls/root-ca.pem` | [README](opensearch/README.md#create-and-fill-the-airport-index) |
| `verify_airports.py` | `opensearch` | `cd opensearch && python3 scripts/verify_airports.py --host https://localhost:9200 --ca-cert build/tls/root-ca.pem --report output/synthetic_airports_verification_report.md` | [README](opensearch/README.md#verify) |
| `diagnose_fixture.py` | `opensearch` | `cd opensearch && python3 scripts/diagnose_fixture.py --rebuilt build/fixture_check.json` (why a rebuilt fixture's hash differs) | [README](opensearch/README.md#12-the-fixture-was-not-reproducible-across-platforms-and-libm-was-the-reason) |
| `analyze_source.py` | `egdb_import` | `cd egdb_import && python3 scripts/analyze_source.py --input ../csv_data/output/nrw_points.csv --geometry-from latlon --output output/nrw_points_schema.json` | [README](egdb_import/README.md#usage) |
| `import_to_egdb.py` | `egdb_import` | `cd egdb_import && python3 scripts/import_to_egdb.py --dry-run --plan output/nrw_points_arcpy_plan.md` (real run needs arcpy on Windows) | [README](egdb_import/README.md#2-rehearse-then-build) |
| `verify_featureclass.py` | `egdb_import` | `propy scripts\verify_featureclass.py --database devsummit --report output\verification_report.md` (PowerShell, needs arcpy) | [README](egdb_import/README.md#3-verify) |
| `try_arcgis_api.py` | `egdb_import` | `cd egdb_import && build/venv_api/bin/python scripts/try_arcgis_api.py --report output/arcgis_api_attempt.md` | [README](egdb_import/README.md#the-route-that-does-not-work) |
| `generate_census.py` | `portal_publish` | `cd portal_publish && python3 scripts/generate_census.py --count 500 --seed 20260904 --output output/muenster_rent_census.csv` | [README](portal_publish/README.md#1-generate-the-census-stdlib) |
| `verify_census.py` | `portal_publish` | `cd portal_publish && python3 scripts/verify_census.py --input output/muenster_rent_census.csv --report output/verification_report_coordinates.md` | [README](portal_publish/README.md#2-verify-the-coordinates-stdlib) |
| `build_portal_items.py` | `portal_publish` | `cd portal_publish && python3 scripts/build_portal_items.py --input output/muenster_rent_census.csv --output-dir output/` | [README](portal_publish/README.md#3-build-the-portal-payloads-stdlib) |
| `publish_to_portal.py` | `portal_publish` | `cd portal_publish && python3 scripts/publish_to_portal.py --dry-run --plan build/publish_plan.md` (real run needs a portal and `$PORTAL_PASSWORD`) | [README](portal_publish/README.md#4-rehearse-the-publish--no-portal-no-arcgis) |
| `verify_portal.py` | `portal_publish` | `cd portal_publish && build/venv_api/bin/python scripts/verify_portal.py --portal https://portal.example.com/portal --user devsummit --report output/verification_report_portal.md` | [README](portal_publish/README.md#6-verify-what-the-portal-stored) |
| `npm run dev` | `slides` | `cd slides && npm install && npm run dev` | [README](slides/README.md#usage) |
| `npm run build` | `slides` | `cd slides && npm run build -- --base /euro_dev_summit_26_test_data_ai/` | [README](slides/README.md#usage) |
| `sync_assets.mjs` | `slides` | `cd slides && npm run sync-assets` (runs automatically before dev/build) | [README](slides/README.md#input-the-screenshots) |

---

## Conventions (short version)

- `input/` is **read-only** — source data, seeds, schemas. Code never writes here.
- `output/` is **generated but committed** — artifacts only, reproducible from
  `input/` plus the documented command, never edited by hand. Committed because
  later use cases consume them as input.
- `build/` and `dist/` are **disposable and gitignored** — the place for
  generated code and scratch artifacts that should not be versioned.
- Dependencies are **isolated per use case** (local venv / local `package.json`).
- Every executable supports `--help` and ships a copy-pasteable example command.
- Seeds are fixed and configurable; model and date of any GenAI-assisted
  generation are recorded.
- External data needs an explicit, CC BY-compatible licence, recorded in the
  use-case README — the licence check comes before the quality check. CC0,
  dl-de/zero-2-0 and public domain are free; CC BY costs an attribution notice;
  **ODbL is out**, because its share-alike clause does not fit a CC BY
  repository.
- Reference data — boundaries, gazetteers, lookup tables — is data too, and gets
  checked as such. A generalised outline is not a yardstick for a question asked
  in metres.
- How far verification goes is agreed up front, not defaulted to. "Plausible is
  enough" and "must be defensible in public" lead to very different amounts of
  work.
- Data with a consumer is checked **against the consumer**, not only against
  itself. A correct data set the target system cannot read passes every test the
  database can offer — measured in `opensearch`: 1 failing check out of 12.
- Third-party server binaries live in `build/`; git gets the manifest with
  version, URL and checksum. Pin the version the *client* certifies, not the
  latest one.
- The talk has a **hard 15-minute slot**, so the deck is built to leave things
  out: two slides per use case — why it exists, then what came out with exactly
  **one** finding. Splitting a dense slide into two sparse ones costs no speaking
  time. The other findings live in the use-case READMEs, which is where a
  question gets answered properly anyway. There is no backup section.
- Published screenshots keep their **basemap attribution** bar. That rules out
  full-bleed background images, which are cropped to fill.
- An API that cannot reach your target may still return a **success**. Check what
  it wrote, not whether it threw — measured in `egdb_import`, where the requested
  API wrote a shapefile and truncated four field names without a word.
- Documentation language is English.

Full details: [`CLAUDE.md`](CLAUDE.md).

---

## Repository

Git repository `euro_dev_summit_26_test_data_ai`, default branch `main`,
intended for public release on GitHub.

Everything in this repository is synthetic or publicly available data. No
customer data, no internal data, no credentials — which is precisely the
constraint that makes generated test data worth talking about.

---

## License

© 2026 M. Scherpinski

This work is licensed under the
[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/)
(CC BY 4.0) — see [`LICENSE`](LICENSE). You may share and adapt the material for
any purpose, including commercially, as long as you give appropriate credit.

Note that CC BY is a content licence. It covers the documentation, examples and
generated data sets in this repository; it is not a typical software licence, so
code fragments are best treated as illustrative material rather than a library
to depend on.

---

## Progress log

| Date | Step |
|---|---|
| 2026-08-20 | Repository scaffolding: conventions (`CLAUDE.md`), overview (`README.md`), prompt log (`PROMPT.md`), use-case README stubs |
| 2026-08-20 | Git repository initialised (`main`), publication conventions documented |
| 2026-08-20 | CC BY 4.0 licence added |
| 2026-08-20 | Use case `csv_data`: 100 geo points written directly by the LLM; coordinate verifier found a systematic 490 m EPSG:3857 error, `output/` switched to versioned, `build/` introduced |
| 2026-08-20 | Use case `csv_data`, iteration 2: seeded generator, 10,000 points across Germany with a public-domain boundary; reproducible, 0 points outside Germany, projection exact — the LLM's contribution moved from the data to the text fixtures |
| 2026-08-20 | Use case `open_data_search`: LLM-driven web search and licence triage across seven open-data candidates; 449 real NRW railway stations built from DB InfraGO (CC BY 4.0), OSM rejected on ODbL share-alike grounds, a generalised boundary caught misclassifying correct data and replaced by the authoritative Geobasis NRW outline |
| 2026-08-21 | `slides/`: the talk as code — Slidev deck deployed to GitHub Pages by Actions, first draft of the 12-minute narrative (four rules, three screenshots) plus eight backup slides. Rendering every slide to PNG found two overflowing slides and one broken layout that the build reported as success |
| 2026-08-21 | Use case `opensearch`: the 449 stations as a script-provisioned OpenSearch 2.12 index for ArcGIS Pro 3.7 / Enterprise 12.1. The `geo_point` format ArcGIS cannot read is the one every tutorial shows, and an index using it fails only 1 of 12 checks; the certified release's demo TLS root CA expired in 2023; the OpenSearch SQL plugin accepts only the format Esri forbids |
| 2026-09-04 | `opensearch` verified against a real ArcGIS Pro 3.7: the connection holds and all 449 stations draw. Publishing failed, and the reason was a truncated quote in our own notes — the "contradiction" recorded in Esri's documentation was one sentence read too short, and the supported route (*Reference registered data → Feature*, not the identically labelled box under *Copy all data*) was in the half that had been cut off |
| 2026-09-04 | `opensearch`, second index: 880 airports from an Enterprise Geodatabase export, to show the source is interchangeable. Two findings paid for the folder. The file was described as GeoJSON and was Esri JSON in **EPSG:3857 metres** — the one wrong reading with no error message, since a clamped longitude lands on the antimeridian and looks systematic. And it had **no licence**: probably FAA-derived, and "probably" is not a licence, so the file is gitignored and only its measured structure was rebuilt with generated values — twelve properties carried over, including the antimeridian span and a `state` value of `HI` that means FIPS 74, not Hawaii. Reprojection provenance splits in two and both halves fire separately (0.0000 mm forward round trip; three tampering runs prove it). The naive bounding box is **344° wide** and worthless, and a swapped axis here is rejected by the engine for 550 of 880 documents where the stations all loaded silently into the Indian Ocean — the earlier verifier was luckier, not better |
| 2026-09-04 | `opensearch`, second index confirmed in ArcGIS Pro 3.7 with both indexes under one database connection, and the pop-up cross-checked field by field against the committed artifact — it also confirms two findings visually: three different integer "object ids" of which ArcGIS uses none, and attribute cells that render empty while holding a single space. Then its own reproducibility claim failed on a second machine, which is the better finding. Rebuilding the committed fixture on Windows Server 2025 / CPython 3.14.7 gave a different SHA-256 than Linux / CPython 3.12.7, at identical size and feature count. Not newlines (`Get-FileHash` matched the in-memory hash), not the seed (the Mersenne Twister fingerprinted identically across both Python versions), not the attributes. It was **30 of 880 `y` values differing by up to 2 ULP — 1.9 nanometres** — because `y = R·log(tan(π/4+φ/2))` goes through libm twice and C transcendental functions are not standardised to the last bit, while `x = R·radians(lon)` is a multiplication and was identical everywhere. Storing raw doubles carried that bit into the file. Fixed by rounding the projected metres to four decimals — the precision the original export had, so the fixture got *more* faithful. The instructive part: at six decimals rounding would not have helped, so the generator now measures the distance to the rounding boundary on the unrounded values and refuses to write a fixture whose hash would be reproducible by luck |
| 2026-09-04 | `opensearch` complete: the layer publishes to ArcGIS Enterprise 12.1 as a web feature layer referencing the index — no copy of the data anywhere, pop-ups answered out of OpenSearch. Getting there cost two certificate failures, and both were the same mistake at a different scale: a trust store belongs to a **runtime**, not to a machine. `certmgr.msc`, which this repository recommended, writes to the interactive user's store — enough for Pro, not for a service (`WinINet 12045`). Fixing that revealed a third store, because ArcGIS Server is part native and part Java and its JVM ignores Windows entirely (`PKIX path building failed`). Four consumers of one self-signed CA, and each fix only makes the next failure visible |
| 2026-09-04 | Use case `egdb_import`: a universal importer that measures a CSV or JSON, writes an editable **schema contract**, and builds the matching FeatureClass in a PostgreSQL Enterprise Geodatabase. The request named the ArcGIS API for Python, and that API has no database connectivity at all — the finding is that it does not say so. `import_data()` returns a working layer that is a *copy* in the ArcGIS Data Store; `to_featureclass()` returns a path to a **shapefile**. Measured four outcomes from one unchanged line, decided only by what was importable: raises · raises the *same* message with shapely installed, because the message names shapely and the code checks pyshp · writes three files then dies inside pyshp 3.x · succeeds silently. That silent success truncated four of ten field names to the DBF limit of ten characters, replaced both measured TEXT lengths (40 and 120) with the format's maximum 255, turned every DOUBLE into a DBF float — and stored the boolean as a boolean, which the geodatabase itself cannot do. Stages 2 and 3 are written but not yet run against a real geodatabase; `--dry-run` rehearses every row and was proven on three planted defects |
| 2026-09-04 | `egdb_import` runs: `agsdb.sde.nrw_points` exists in the PostgreSQL geodatabase and draws in ArcGIS Pro 3.7, all ten declared fields in the pop-up. Two claimed version numbers became measurements (Python 3.13.13 confirmed; licence `ArcEditor` = Standard). Then a **second source** through the same pipeline — the 880-feature Esri JSON FeatureSet from `opensearch`, in EPSG:3857 metres — and it inverted this repository's usual rule: the file's own declared `fields` block beat the measurement twice. `state_fips` measures as an integer and is `TEXT(2)` holding `01`…`09`, which `LONG` would silently strip to `1`…`9`; `acais` would have tripped the boolean heuristic. A code that looks like a number cannot be recognised by measuring it. Two bugs found in the process, both by the row rehearsal: **1,343 single-space values** across three columns were being read as absent and would have been written as `NULL` — a silent edit to somebody else's data — and the cause was the analyser and the loader holding *two different definitions of empty*, now one shared public predicate. Also visible in the screenshot: `objectid` and the CSV's own `id` are equal, which is worse than the `opensearch` case where they matched in zero rows — this version invites the join it should discourage |
| 2026-09-04 | `egdb_import` complete: both sources are FeatureClasses in the PostgreSQL geodatabase and draw in ArcGIS Pro — 100 points in EPSG:4326 and 880 airports in EPSG:3857, from a CSV and an Esri JSON export through one pipeline. `nrw_points` verifies **10 of 10 green**, and one of those numbers refutes a claim this repository made: check 7 was written as an exact comparison because nothing in the pipeline projects, converts or rounds — and the values read back differ by up to **9.5 nanometres** (8.53e-14°, ~12 ULP). A geodatabase round trip is not the identity even when no code touches the value, so the tolerance that looked like decoration was load-bearing. Symmetric to the `opensearch` libm finding: 1.9 nm from a maths library there, 9.5 nm from a database storing a number here. The airports pop-up carries three findings in one feature: `objectid 282` beside `source_objectid 305` (the *safe* disagreement, against `nrw_points` where objectid and the CSV's `id` agree by accident), `state_fips 08` with its leading zero intact, and a `field` cell that renders empty while holding a single space. Still open: the airports verification run and the perturbation runs that prove each check goes red |
| 2026-09-07 | Use case `portal_publish`, stages 1-3: 500 fictitious Münster rent-census points, a declared hosted-layer schema, a service-level renderer and a complete four-renderer Web Map — all built, verified and committed **with no portal in the room**. Measured first, before any code: `arcgis` 2.4.1.1 has **no Web Map class**, in neither the old place nor the new one its own migration notes name — 0 `arcgis/map/` entries in the wheel's `RECORD` — so hand-built JSON is the only route. Two of this repository's own findings are deliberately inverted here (copy-all-data, and `import_data()`'s copy as the deliverable rather than the defect). The best failure was self-inflicted: the first dry run aborted on an unresolved placeholder that was **inside a note explaining the placeholder check**, because the assertion greps the payload as text — and the tempting fix, matching only known token names, would have let a planted one-character typo through. Second finding, the same shape from the other side: a clamp counter written to police a bad distribution *became* the distribution, piling 37 of 500 household sizes onto exactly 1.0 until a gamma variate with the floor built in took it to 2. 2/2 offline checks green, max EPSG:3857 deviation 0.000069 m, 7,000 values coerced against 14 declared field types with 0 problems. Open: the portal run, and with it the central measurement — the diff between our declaration and the portal's own `analyze` guess |
| 2026-09-14 | `portal_publish` reaches the portal, and the two most useful findings came out of the published map rather than the code. The declared schema survived as **types** and not as **lengths**: `TEXT(80)`/`TEXT(40)` were accepted without a warning and stored as `TEXT(8000)`, while the portal's own `analyze` guess agreed with the declaration in **0 of 14** fields — the guess was right, the declaration was right, and the stored schema matched neither. And the heatmap's `maxPixelIntensity` had been set to a percentile of the **rent column**, 19.28 EUR/m², as though a pixel intensity were a rent: an isolated point peaks at exactly its own weight, rents reach 22.75, so all 500 dwellings drew as saturated red blobs with nothing anywhere reporting an error. The ceiling is now simulated from a Gaussian kernel at a reference resolution (floor 9.02, ceiling 38.82) and the verifier asserts it sits 1.5x above the largest weight. Calibration was not enough: a weighted heatmap correlates with plain point density at rho 0.774 and with the local rent level at 0.786, so it cannot say which one a red patch means — a fifth layer, `classBreaks` on the same column, now answers the question the heatmap only appeared to. 3/4 portal checks green |
| 2026-09-14 | `portal_publish`, second portal run: three assumptions measured and three of them wrong. A private CA reached `requests` and not `arcgis` **in the same interpreter** - 200 against `CERTIFICATE_VERIFY_FAILED` - because the library mounts an adapter with its own `ssl.SSLContext`; the supported route is `GIS(ca_bundles=...)`, documented only in the class docstring inside the wheel. `updateDefinition`, asked to set the three declared TEXT lengths, answered `{"success": true}` and the service still reports `TEXT(8000)` - a confirmed write that never happened, so the mismatch became an INFO finding printed next to the API's own claim while the field **types** still fail the check. And the calibrated heatmap was stored exactly as sent and drawn as though it had not been: at identical extent and zoom, `blurRadius` 12 to 25 visibly enlarged the blobs while `maxPixelIntensity` 19.28 to 38.82 changed nothing. One of three deprecated properties honoured - "deprecated" means accepted, not supported. The uncomfortable part: no check that reads an item back can see that difference, only the pair of screenshots can |
| 2026-09-14 | `portal_publish`, third portal run: **four of four checks green over a web map whose heatmap layer drew nothing.** Published in the Web Map Specification's *current* encoding (`radius`/`minDensity`/`maxDensity`), ArcGIS Enterprise 12.1 stored it intact and rendered nothing at all; the deprecated form it replaces draws, but honours only `blurRadius` and ignores both intensity bounds. On this version "deprecated" marks the form that works and "current" the one that is merely accepted. The finding is about the verifier rather than the portal: every check reads the **stored** item, so all four were satisfied and all four were right about what they measured - "does this draw" is not a readable property. A screenshot was the only instrument that could see it, in a folder whose argument is that checks beat inspection; the claim is now stated narrowly and the measurement encoded, so the verifier refuses that encoding for a 12.1 target. Three platform behaviours here now share one shape: a declared TEXT length, a heatmap's bounds and a whole renderer, each accepted in full and each silently ignored |
| 2026-09-14 | `portal_publish` closed, and into the deck. `referenceScale` alongside the deprecated heatmap encoding is harmless and changes nothing visible - consistent, since the bounds it would pin are the ones 12.1 ignores - so the finding stands: a heatmap there cannot be calibrated from the payload, and the class-breaks layer is the answer. Four backup slides (30-33) and **one** screenshot, the class-breaks map. Slide 31, *four of four green and the layer was empty*, is the strongest candidate in the backup to displace a core rule precisely because it argues against the deck's thesis that verification beats inspection. The PNG export caught two defects the Slidev build called success - a metric that wrapped into two enormous lines, and a slide promising three findings while showing two |
| 2026-09-14 | The deck rebuilt from scratch, now that all five use cases are finished. The old shape — four named rules with the use cases as evidence — was thrown away along with its fifteen backup slides, and the Slidev setup kept. The new deck is **10 slides**: the constraint, the chain, one slide per use case, four lessons learned. Each use-case slide carries the idea, what actually worked with its numbers, one screenshot and exactly **one** finding; the other eleven findings per folder stay in the READMEs. The centre of gravity moves from "here is what goes wrong" to "here is what you can do", and the failures become each slide's punchline rather than its subject. The PNG export earned its place again: all five use-case slides shipped with the finding box running off the bottom edge, cut off mid-sentence, on a build that reported success |
| 2026-09-14 | The deck rebuilt again after a read-through, and the second rebuild is the one that works. Ten slides became **17**: every use case now gets an *idea* slide saying why it exists — volume for `csv_data`, search effort for `open_data_search`, a service type we are new to for `opensearch`, "this is where we actually need test data" for `egdb_import`, the whole flow for `portal_publish` — before its result slide. Splitting them cost no speaking time, and what fitted into the new space was the part that had been missing. Two other corrections: the opening no longer claims the motivation is *not being allowed* to use real data, but that a product must work with **any** customer's data, so what a test needs is structure; and the deck is now written for a non-native speaker, with words like *prose* and numbers that need explaining removed. The PNG export earned its keep for the third time and found the worst defect yet — an image capped in `vh` inside a slide Slidev scales by transform, rendering far past the bottom edge and **cropping the basemap attribution off**. A licence rule this repository wrote down, broken by a unit conversion, on a green build |
| 2026-09-14 | The deck carries the submitted title and gets read against its own abstract — the same move as checking data against its consumer, and it found three gaps in a deck that already looked finished: the abstract promises a CSV *for a hosted feature service* and no slide named the target, promises a view layer *in ArcGIS Pro* from *a GeoJSON* and the OpenSearch slides mentioned neither, and names *Claude Code* where the deck named no tool at all. All three fixed, plus a new **disclaimer slide** at the front saying how everything was made: an agent in a local repository, every prompt logged verbatim, the effort in verifying rather than generating, nothing leaving the machine until something was published. `egdb_import` now states the reason it matters most — our services are **referenced** feature layers on the geodatabase, so the portal reads through to the database and the write is what decides everything after it. Takeaways tightened to one line each and led by the one that is the whole talk: *there is more than one way to get to data*. 18 slides, ≈ 11.5 minutes |
| 2026-09-14 | The deck takes on the corporate look of the company's PowerPoint master. Palette and typography were read out of the template's own XML - titles and body copy in **#005587**, turquoise **#00B0B9** as the single accent, light blue **#8BD3E6** for the rules, Arial throughout - and the cover follows `Titelfolie_hell`: white, title block at the left edge, a low-poly graphic top right. The `.potx` itself is **gitignored**: a corporate template is not ours to publish under CC BY, so what crossed over is the scheme, not the file, and the corner graphic is drawn here from the same colours rather than lifted. One measured trap: `layout: cover` is seriph's own layout and paints its own background, so the custom cover rendered as a grey gradient on a build that reported success - found, as three times before, only by exporting the PNGs and looking |
| 2026-09-14 | The closing slide takes the master's `Schlussfolie` shape - *Thank you very much!*, speaker and full postal address at the template's own vertical positions, the grid structure across the slide - with the QR code where the template puts its logo strip, since the logos are the template's and the repository link is what the room actually needs. The grid is generated by a seeded script (`make_close_grid.mjs`, byte-identical on re-run) rather than extracted from the `.potx`. Cover and closing slide carry no footer, as in the master. The disclaimer slide now also names **Slidev** as what the deck itself is written in. One defect found by the PNG export again: the address blocks were positioned in per cent inside a zero-height container and collapsed onto the title, and in the fix "Germany" printed on top of the phone number |

Detailed, prompt-by-prompt history: [`PROMPT.md`](PROMPT.md).
