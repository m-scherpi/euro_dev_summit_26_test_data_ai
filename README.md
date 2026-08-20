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
└── <use-case>/
    ├── README.md      # detailed docs for this use case
    ├── input/         # read-only source data
    └── output/        # generated artifacts only
```

Each use case is independent: its own stack, its own dependencies, its own
README. There is no shared build and nothing to install at root level.

---

## Use cases

| Folder | Use case | Approach / stack | Status | Docs |
|---|---|---|---|---|
| [`csv_data/`](csv_data/) | Geo points as CSV, two ways: 100 written directly by the LLM vs. 10,000 from a seeded generator — coordinates verified by code either way | Python 3.12, stdlib only | ✅ done | [README](csv_data/README.md) |
| [`open_data_search/`](open_data_search/) | The inverse: the LLM searches, triages licences and writes code, but invents no data — 449 real NRW railway stations from DB InfraGO open data, every coordinate traceable to its source | Python 3.12 + venv (`requests`, `shapely`, `pyshp`, `pyproj`) | ✅ done | [README](open_data_search/README.md) |
| [`opensearch/`](opensearch/) | Test data for OpenSearch (indexing / geo queries) | tbd | 🕓 planned | [README](opensearch/README.md) |
| [`python_import/`](python_import/) | Importing / converting generated data via Python | tbd | 🕓 planned | [README](python_import/README.md) |

Status legend: 🕓 planned · 🚧 in progress · ✅ done

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

Detailed, prompt-by-prompt history: [`PROMPT.md`](PROMPT.md).
