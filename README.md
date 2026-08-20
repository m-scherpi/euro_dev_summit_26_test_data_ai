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
| [`csv_data/`](csv_data/) | Generating tabular test data (CSV) | tbd | 🕓 planned | [README](csv_data/README.md) |
| [`opensearch/`](opensearch/) | Test data for OpenSearch (indexing / geo queries) | tbd | 🕓 planned | [README](opensearch/README.md) |
| [`python_import/`](python_import/) | Importing / converting generated data via Python | tbd | 🕓 planned | [README](python_import/README.md) |

Status legend: 🕓 planned · 🚧 in progress · ✅ done

---

## Usage / executables

Central index of everything runnable produced in this repository. Empty until
the first use case is implemented — details always live in the use-case README.

| Tool | Use case | Example command | Docs |
|---|---|---|---|
| _none yet_ | — | — | — |

---

## Conventions (short version)

- `input/` is **read-only** — source data, seeds, schemas. Code never writes here.
- `output/` is **disposable** — generated artifacts only, always reproducible
  from `input/` plus the documented command. Never edited by hand.
- Dependencies are **isolated per use case** (local venv / local `package.json`).
- Every executable supports `--help` and ships a copy-pasteable example command.
- Seeds are fixed and configurable; model and date of any GenAI-assisted
  generation are recorded.
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

Detailed, prompt-by-prompt history: [`PROMPT.md`](PROMPT.md).
