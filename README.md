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
| [`opensearch/`](opensearch/) | The same 449 stations as an OpenSearch index a GIS client can draw — provisioned by script, no Docker, nothing but the data in git. The `geo_point` format every tutorial shows is the one ArcGIS cannot read, and only 1 of 12 checks notices | Shell + Batch, Python 3.12 stdlib only, OpenSearch 2.12.0 | ✅ done | [README](opensearch/README.md) |
| [`python_import/`](python_import/) | Importing / converting generated data via Python | tbd | 🕓 planned | [README](python_import/README.md) |

Status legend: 🕓 planned · 🚧 in progress · ✅ done

## The talk

| Folder | What | Stack | Status | Docs |
|---|---|---|---|---|
| [`slides/`](slides/) | The conference presentation as code — four named rules, each proven by one measured number and one screenshot, in a hard 15-minute slot | Slidev 52 (Markdown + Vue), GitHub Pages via Actions | ✅ first draft | [README](slides/README.md) |

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
  out: a core deck of four rules, and a backup section that new findings land in
  first. A new use case enters the core deck only by displacing a weaker one.
- Published screenshots keep their **basemap attribution** bar. That rules out
  full-bleed background images, which are cropped to fill.
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

Detailed, prompt-by-prompt history: [`PROMPT.md`](PROMPT.md).
