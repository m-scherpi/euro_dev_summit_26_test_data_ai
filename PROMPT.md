# Prompt Log

Chronological record of every prompt issued in this repository and what came out
of it. Newest entries at the bottom.

Prompts are written in German and are quoted **verbatim** — they are evidence of
the process, not documentation. A faithful English translation follows each
original so the log stays readable for an English-speaking audience.

Meta-prompts that only concern documentation and conventions are excluded from
this log on request; the numbering stays continuous.

Entry format, conventions and documentation duties: see [`CLAUDE.md`](CLAUDE.md).

---

## [001] 2026-08-20 — Repository scaffolding & working conventions  ·  scope: root

**Prompt (original, DE)**
> In der vorliegenden Ordner-Struktur sollen verschiedenen Teilprojekte entstehen, die jeweils in einem Ordner liegen, in denen es noch einmal separat "Input" und "Output" geben soll. DAS generelle Oberthema lautet "Test(Geo-)daten Generierung per GenAI". Im folgenden werde ich in den einzelnen Unterordnern verschiedene Use-Cases abarbeiten. Was genau da drin passiert, soll in einer README.md auf Root Level festgehalten werden, auch die Nutzung von z.B. entstehenden Executables.. Schreibe dir selber eine Anweisungs-Datei (claude.md), in der du Generelle Infos und Anweisungen festhälst, sodass ich nicht für jeden Prompt Dinge wiederholen muss. Pflege diese auch weiter, wenn es änderungen gibt. Pflege auch die Readme. Beispielsweise möchte ich, dass du im Folgenden die Prompts, die ich Absetze in einer PROMPT.md protokollierst. Auch soll grob festgehalten werden, was genau passiert, sodass die einzelnen Arbeitsschritte und ein iteratives Vorgehen protokolliert wird. Am ende soll alles nachvollziehbar sein, da ich über das Thema einen Vortrag halten werde. Ich möchte über verschiedene Beispiele und Use Cases berichten, welche wir im folgenden entwickeln werden.

**Prompt (translation, EN)**
> In the present folder structure, several sub-projects are to be created, each located in a folder, in which there should again be a separate "Input" and "Output". THE general overarching topic is "Test (Geo-)data Generation via GenAI". In what follows, I will work through various use cases in the individual subfolders. What exactly happens in there should be recorded in a README.md at root level, including the usage of e.g. resulting executables.. Write yourself an instruction file (claude.md) in which you record general information and instructions, so that I do not have to repeat things for every prompt. Also keep this maintained if there are changes. Also maintain the Readme. For example, I want you to log the prompts that I issue in a PROMPT.md in what follows. It should also be roughly recorded what exactly happens, so that the individual work steps and an iterative approach are documented. In the end everything should be traceable, since I am going to give a talk on the topic. I want to report on various examples and use cases which we will develop in what follows.

**What happened**
- Inspected the starting point: three empty use-case folders (`csv_data/`,
  `opensearch/`, `python_import/`), each with empty `input/` and `output/`. No
  files, no git repository, no existing conventions.
- Clarified three open decisions with the user before writing anything:
  - **Tech stack**: no global default — chosen per use case and justified in
    that use case's README. Rationale: the variety itself is talk material.
  - **Documentation language**: English (chat communication stays German).
  - **Documentation granularity**: root README as index, plus one README per
    use case. Scales better as the number of use cases grows.
- Wrote the three control documents (`CLAUDE.md`, `README.md`, `PROMPT.md`),
  a `.gitignore` prepared for later versioning, and README stubs for the three
  known use cases.
- Named the instruction file `CLAUDE.md` rather than `claude.md`: on Linux the
  filename is case-sensitive and only the uppercase variant is auto-loaded as
  project context by Claude Code.
- Added `.gitkeep` files so the empty `input/`/`output/` folders survive a
  later `git init`.
- Model used: Claude Opus 5.

**Artifacts**
- `CLAUDE.md` — standing instructions: purpose, layout, data conventions,
  tech-stack policy, documentation duties, prompt-log format, language rules,
  reproducibility requirements
- `README.md` — overview, structure, use-case index, executables table,
  short-form conventions, progress log
- `PROMPT.md` — this log
- `.gitignore` — venv/node_modules/secrets ignored; bulk `output/` ignored while
  keeping the folder structure
- `csv_data/README.md`, `opensearch/README.md`, `python_import/README.md` —
  stubs with a uniform skeleton, status "not started yet"
- `.gitkeep` in all six `input/`/`output/` folders

**Result / Iteration**
- Scaffolding complete; no use case implemented yet — this step was deliberately
  setup only.
- Deferred by design: **no `git init`**. Version control would noticeably improve
  traceability for the talk, but the user did not ask for it. Flagged as an
  optional follow-up.
- The three use-case descriptions in the root index are placeholders. They get
  filled in when the respective use case is actually started, since the concrete
  scenario is not defined yet.
- Open question for the next iteration: which use case to start with, and
  whether the talk should follow a "simple → complex" progression (tabular CSV →
  geospatial → search index).

---

## [002] 2026-08-20 — Git repository initialised  ·  scope: root

**Prompt (original, DE)**
> lege ein git repository mit dem Namen "euro_dev_summit_26_test_data_ai" an. Dieses soll später auf meinem Github account veröffentlicht werden

**Prompt (translation, EN)**
> create a git repository with the name "euro_dev_summit_26_test_data_ai". This is to be published on my Github account later on

**What happened**
- Checked the environment: Git 2.43.0, `user.name` / `user.email` already
  configured globally, no existing repository. The `gh` CLI is **not installed**
  on this machine.
- `git init -b main` — explicit branch name to avoid the legacy `master`
  default, since `init.defaultBranch` was unset.
- Verified via `git add -An` and `git check-ignore` that the intended 13 files
  are tracked and that the `.gitignore` negation for `*/output/.gitkeep` works —
  the empty `input/`/`output/` folders survive without dragging in bulk output.
- Did **not** rename the working directory (`devsummit`) to the repository name.
  The name matters for the GitHub remote; renaming would break this session's
  working directory for no benefit.
- Documented publication constraints in `CLAUDE.md` (new section 10): English
  commit messages, commit history as talk material, and a hard rule that no
  credentials, customer data, production geodata or real personal data may be
  committed.
- Created the initial commit.

**Artifacts**
- `.git/` — repository, branch `main`
- `CLAUDE.md` — new section 10 "Git & publication"; former section 10
  "Working style" renumbered to 11
- `README.md` — new "Repository" section, progress log entry

**Result / Iteration**
- Local repository ready; **not** published yet. No remote configured, nothing
  pushed — publishing needs the user's GitHub account and an explicit go-ahead.
- Blocker for later: `gh` is not installed, so `gh repo create` is unavailable.
  Either install `gh`, or create the repository in the GitHub web UI and add the
  remote manually.
- Open point: no `LICENSE` file yet. A public talk repository should state a
  licence — worth deciding before publication.
- The commit author is the company address `m.scherpinski@conterra.de`. Fine for
  a conference repository, but it becomes publicly visible — flagged in case a
  different address is preferred.

---

## [003] 2026-08-20 — CSV geo test data, LLM-authored and code-verified  ·  scope: `csv_data`

**Prompt (original, DE)**
> Nun zum ersten Use Case. Im Ordner csv_data möchte ich eine CSV-Datei mit Testdaten generiert bekommen. Diese Datei soll geografische Punkte enthalten, repräsentiert durch latitude und longitude in Dezimalgrad im Referenzsystem 3857. Wichtig dabei, dass latitude und longitude nicht vertauscht werden, damit die punkte an der richtigen Stelle liegen. starte mit 100 Einträgen, welche grob im Bundesland NRW in Deutschland liegen. Zu jedem Punkt soll es eine Spalte mit Titel und Beschreibung geben. Zudem ein INTEGER Feld z.B. Anzahl, ein DOUBLE Feld, z.B. Höhe und ein Boolean Feld. Alle diese Spalten sollen mit zufälligen Werten belegt werden: da es sich um testdaten handelt ist der Inhalt nicht so wichtig. Vielleicht nutzen wir referenzen aus Fantasy-Franchises. lege das generierte File unter output ab, damit es später weiter verarbeitet werden kann. Entsprechend soll der output ordner auch im git verfügbar sein, stattdessen brauchen wir für anderen generierten Code, der vielleicht zukünftig nicht im git sein soll noch "build" ordner oder ähnliches

**Prompt (translation, EN)**
> Now to the first use case. In the folder csv_data I would like to get a CSV file with test data generated. This file should contain geographic points, represented by latitude and longitude in decimal degrees in the reference system 3857. Important here that latitude and longitude are not swapped, so that the points lie in the right place. start with 100 entries, which lie roughly in the federal state NRW in Germany. For each point there should be a column with title and description. In addition an INTEGER field e.g. count, a DOUBLE field, e.g. height and a Boolean field. All these columns should be filled with random values: since these are test data the content is not so important. Maybe we use references from fantasy franchises. put the generated file under output, so that it can be processed further later. Accordingly the output folder should also be available in git, instead we need for other generated code, which perhaps in future should not be in git, "build" folders or similar

**What happened**
- **Spotted a contradiction in the request before writing anything**: "decimal
  degrees" is EPSG:4326, "reference system 3857" is Web Mercator in metres.
  Both halves are sensible on their own, but not simultaneously. Raised it and
  asked instead of resolving it silently.
- Three decisions taken by the user:
  - **CRS**: emit *both* — `latitude`/`longitude` (EPSG:4326, decimal degrees)
    and `x_3857`/`y_3857` (EPSG:3857, metres) for the same point per row, so
    downstream use cases can pick the columns they need.
  - **Generation method**: the CSV is written **directly by the LLM**, no
    generator script, no seed. Deliberately the "purest GenAI" variant — and
    deliberately the non-reproducible one.
  - **Distribution**: uniform sampling of the NRW **bounding box**
    (`lat 50.32–52.53 / lon 5.87–9.46`), knowing the corners reach into
    neighbouring states and countries.
- Flagged the consequence of "LLM writes the CSV" up front: the Web Mercator
  forward transform contains `ln(tan(…))`, and an LLM cannot evaluate that
  reliably. The user chose to keep the raw output as evidence *and* have a
  verifier write a corrected, usable copy.
- Wrote `output/nrw_points_llm_raw.csv` by hand — 100 rows, 10 columns,
  including the EPSG:3857 values computed mentally (`x` by multiplication, `y`
  by interpolating between remembered anchor latitudes).
- Sketched a coarse 27-vertex NRW polygon as `input/nrw_boundary_approx.geojson`
  for the containment report. Explicitly non-authoritative.
- Wrote `scripts/verify_coordinates.py` — Python 3.12, **standard library
  only**, so it runs from a fresh clone with no setup. Four checks (axis order,
  bounding box, column types, EPSG:3857 accuracy) plus a point-in-polygon
  containment report.
- Switched `.gitignore` from ignoring `*/output/*` to versioning it, and
  introduced `build/` + `dist/` as the gitignored home for disposable generated
  code, as requested. Verified both with `git check-ignore`.
- Model used: Claude Opus 5 (`claude-opus-5[1m]`).

**Artifacts**
- `csv_data/output/nrw_points_llm_raw.csv` — the raw LLM output, unedited,
  wrong EPSG:3857 values included
- `csv_data/output/nrw_points.csv` — the usable file; identical except for
  recomputed `x_3857`/`y_3857`
- `csv_data/output/verification_report.md` — generated verification report
- `csv_data/input/nrw_boundary_approx.geojson` — coarse NRW polygon, for the
  containment check only
- `csv_data/scripts/verify_coordinates.py` — the verifier, `--help` included
- `csv_data/README.md` — full documentation, replaces the stub
- `.gitignore` — `output/` now versioned, `build/`/`dist/` ignored
- `CLAUDE.md` — new section 4 "Geodata conventions"; `output/`-is-committed and
  `build/`-is-disposable rules in section 3; sections 4–11 renumbered to 5–12
- `README.md` — use-case index, executables table, conventions, progress log

**Result / Iteration**
- **What the LLM got right**: everything structural. 100 unique titles, 100
  distinct descriptions, plausible value ranges, correct CSV quoting — and the
  one thing that was explicitly demanded, *latitude and longitude were never
  swapped*, in any of the 100 rows. The verifier's axis-order, bounding-box and
  type checks all pass with zero violations.
- **What the LLM got wrong**: all 100 EPSG:3857 rows. Measured deviation
  min 18.47 m, median 393.87 m, mean 333.49 m, max **490.29 m**.
- **The instructive part is the shape of the error, not its size.** Split by
  axis: `x_3857` needs one multiplication → max error **0.06 m**. `y_3857`
  needs `ln(tan(…))` → max error **490.29 m**, and **positive in 100 of 100
  rows**. Interpolating a convex function along a chord always overshoots, so
  every single point landed too far north. A systematic directional bias
  survives averaging and spot-checking; the data looks entirely plausible.
  Only a recomputation finds it.
- Cross-checked the verifier against an independent formulation of the same
  projection (`R · atanh(sin φ)`): agrees with the corrected file to **7 mm**.
  So the 490 m is the model's error, not the script's. Re-running the verifier
  on the corrected file reports a maximum deviation of 0.01 m — the correction
  is idempotent.
- **The bounding box was not a boundary**: **41 of 100** points fall outside
  NRW — Netherlands, Belgium, Lower Saxony, Rhineland-Palatinate. Nothing was
  hallucinated; a rectangle around an irregular shape simply contains a lot
  that is not the shape. Reported, not quietly fixed, since the user chose bbox
  sampling knowingly.
- **Open for the next iteration**: a seeded generator that scales past 100 rows.
  The current data set cannot be regenerated at all — no seed, no script — which
  is exactly the trade-off the direct-LLM approach buys. Putting the two side by
  side is the natural follow-up.
- Not committed. Waiting for an explicit request, per `CLAUDE.md` section 11.

---

## [004] 2026-08-20 — Seeded generator, 10,000 points across Germany  ·  scope: `csv_data`

**Prompt (original, DE)**
> Jetzt erstelle ein seed-skript und benutze es, um mir 10000 punkte in ganz deutschland zu generieren. Eine Anmerkung: für meinen Use-Case zur Visualisierung habe ich gar keine x_3857 und y_3857 gebraucht. Genriere sie trotzdem, um die erkenntnisse zum umrechnen für den Vortrag festzuhalten

**Prompt (translation, EN)**
> Now create a seed script and use it to generate me 10000 points in all of germany. One remark: for my use case for visualisation I did not need x_3857 and y_3857 at all. Generate them anyway, in order to record the insights about converting for the talk

**What happened**
- This is the follow-up [003] flagged as open: the reproducible counterpart to
  the direct-LLM data set. Kept inside `csv_data` so both methods are documented
  against each other in one README.
- Three decisions taken by the user:
  - **Boundary from real open data** — Natural Earth 50m. Rejection sampling
    against the polygon instead of bounding-box sampling.
  - **Stay in `csv_data`** rather than opening a new use-case folder.
  - **Uniform density over the land area**, not clustered on metropolitan
    regions.
- **Rejected a data source on licence grounds before looking at its geometry.**
  `deutschlandGeoJSON` has the nicer outline (508 vertices) but is archived,
  states no licence, and derives from GADM, whose terms forbid commercial
  redistribution. Unusable for a CC BY repository. Natural Earth is public
  domain and says so, so it won on licence, not on quality.
- Wrote `scripts/fetch_germany_boundary.py` as a **one-off provisioning tool**:
  downloads the 3 MB world-wide Natural Earth file, keeps only the Germany
  feature, and writes source URL and licence into the fixture's properties.
  Output is 12.5 KB and committed, so the script normally never runs again.
- Wrote `input/fantasy_places.json` — the LLM's contribution this time is the
  *text fixture*, not the data: 60 prefixes × 40 cores × 40 suffixes = 96,000
  title combinations, plus 20 description templates and five filler lists.
- Extracted `scripts/geo.py` for the shared plane geometry (MultiPolygon
  loading, holes, per-ring bbox pre-filter, ray casting) and deliberately kept
  the **projection unshared**: the generator uses
  `y = R · ln(tan(π/4 + φ/2))`, the verifier now uses the equivalent
  `y = R · atanh(sin φ)`. Two independent implementations, so agreement between
  them is evidence rather than a tautology.
- Generalised `scripts/verify_coordinates.py` from NRW-only: bounding box
  derived from the boundary polygon, region label read from the feature, a guard
  that warns when the latitude and longitude bands overlap (in which case the
  axis-order check cannot detect a swap), and a `--max-listed` cap so a
  10,000-row report stays readable.
- **Regression-checked the refactor against the [003] data before continuing** —
  18.47 / 393.87 / 333.49 / 485.99 / 490.29 m and 41 outside NRW reproduced
  exactly, so the rewrite and the formula swap changed nothing.
- Validated the boundary machinery independently: a Monte-Carlo area estimate of
  the polygon gives 355,909 km² against Germany's actual 357,596 km² (−0.5 %),
  consistent with Natural Earth at 1:50 M dropping the East Frisian islands and
  clipping Sylt's northern tip.
- Model used: Claude Opus 5 (`claude-opus-5[1m]`).

**Artifacts**
- `csv_data/scripts/generate_points.py` — the seeded generator
- `csv_data/scripts/geo.py` — shared plane geometry, no projection maths
- `csv_data/scripts/fetch_germany_boundary.py` — one-off provisioning
- `csv_data/scripts/verify_coordinates.py` — generalised beyond NRW
- `csv_data/input/germany_boundary_ne50m.geojson` — Natural Earth 50m, public
  domain, MultiPolygon, 6 rings, 562 vertices, 12.5 KB
- `csv_data/input/fantasy_places.json` — LLM-authored component pool
- `csv_data/output/germany_points_10k.csv` — 10,000 rows, 1.94 MB
- `csv_data/output/verification_report_germany.md` — its verification report
- `csv_data/README.md` — rewritten around the two methods and their comparison
- `README.md`, `CLAUDE.md` — index, executables, conventions

**Result / Iteration**
- **10,000 points in 0.75 s**, all checks clean: 0 structural failures, max
  EPSG:3857 deviation **0.01 m** (two-decimal rounding), **0 of 10,000 points
  outside Germany**. Rejection sampling accepted 64.4 % of candidates (15,532
  draws), matching the Monte-Carlo prediction of 64.5 %.
- **Determinism verified in both directions**: the same seed twice produces
  byte-identical files, `--seed 1` produces a different one.
- **Equal-area sampling matters more than it looks.** Naive
  `uniform(lat_min, lat_max)` would have put **1.185×** more points per km² in
  northern Germany. Sampling `sin(latitude)` instead measures out at a
  north/south density ratio of **0.994**. The naive version would have passed
  every check in this repository.
- **Scaling fixed the maths and cost the prose.** 100 hand-written descriptions
  were 100 distinct sentences; 10,000 template-generated ones are 9,947 distinct
  strings that are structurally far more repetitive. 100× the data, measurably
  worse writing — the honest trade of this iteration.
- **The redundant columns, quantified as asked.** `x_3857`/`y_3857` cost
  **212 KB of 1,983 KB — 10.7 % of the file** and add a second source of truth.
  Method A's error in them was up to 490 m with a systematic northward bias;
  method B's is 0.01 m. For the visualisation use case they were never needed.
- **Two bugs of my own, both found by the verification rather than by reading
  the code**, and both more instructive than the successes:
  1. The verifier's `--output` defaulted to `output/nrw_points.csv`, so
     verifying the *Germany* file overwrote the *NRW* file. A convenient default
     turned a read-only operation into a destructive one. `--output` and
     `--report` now have no defaults; the NRW file was restored and re-checked.
  2. The generator projected the *unrounded* coordinates while writing 5
     decimals to the CSV, so every row disagreed with itself by up to **1.09 m**
     — exactly the rounding step. Rounding before projecting fixed it, and the
     file is now self-consistent for anyone recomputing the projection from it.
- **Open for the next iteration**: `elevation_m` is uncorrelated with position,
  so a Baltic-coast point can carry an Alpine elevation. Every column is
  individually valid and jointly nonsense. Correlating it needs a digital
  elevation model — a good candidate for a later use case, and a sharp
  illustration of why "valid test data" and "plausible test data" are different
  claims.
- Not committed. Waiting for an explicit request, per `CLAUDE.md` section 11.

---

## [005] 2026-08-20 — Real NRW railway stations from open data  ·  scope: `open_data_search`

**Prompt (original, DE)**
> Nun habe ich einen neuen Use Case, dessen output auch eine CSV-Datei ist (auch hier wieder die schon bekannten Koordinaten-Konventionen beachten). Allerdings machen wir das vielleicht lieber in einem extra ordner, der noch nicht vorbereitet ist. Hier soll es diesmal darum gehen, dass zwar auch ein LLM benutzt wird, aber die Daten vielleicht nicht generiert und damit erfunden sind. Vielmehr ist das Ziel nun, einen Datensatz zu bekommen, welche alle Bahnhöfe in NRW darstellt. Alternativ geht auch Flughäfen. Quelle soll dabei open data sein, entweder aus OSM oder aus freien Geoportalen. Die Daten sollen natürlich entsprechend lizensiert sein, open data, legal nutzbar, aber kostenlos.. Es soll also eine Websuche nach passenden Datensätzen durchgeführt und das ergebnis entsprechend aufgearbeitet werden.

**Prompt (translation, EN)**
> Now I have a new use case whose output is also a CSV file (here too, please observe the already known coordinate conventions). However, we should perhaps rather do this in an extra folder that has not been prepared yet. This time it should be about the fact that an LLM is used as well, but the data is perhaps not generated and therefore not invented. Rather, the goal is now to obtain a data set representing all railway stations in NRW. Airports work as an alternative. The source is to be open data, either from OSM or from free geoportals. The data must of course be licensed accordingly, open data, legally usable, but free of charge.. So a web search for suitable data sets is to be carried out and the result processed accordingly.

Two follow-up prompts arrived while the work was running:

> dokumentiere auch das lizenz-problem mit OSM, sodass ich das im vortrag erwähnen kann

> _(EN: also document the licence problem with OSM, so that I can mention it in the talk)_

> Halte als Erkenntnis fest, dass du sehr genau arbeitest, gerade hier in dem Use case: echte Daten für NRW und du im Zweifel einzelne Punkte auf die Genauigkeit oder die genaue Lage prüfst z.B. in Grenzfällen. Das ist nicht zwingend immer notwendig für den Testdaten-Fall und sollte möglicherweise bewusst abgefragt oder bestätigt werden. Erkenntnis für den Talk

> _(EN: Record as a finding that you work very precisely, especially here in this use case: real data for NRW, and when in doubt you check individual points for accuracy or their exact location, e.g. in border cases. That is not necessarily always required for the test-data case and should possibly be deliberately asked about or confirmed. Finding for the talk.)_

**Decisions taken with the user mid-task** (`AskUserQuestion`, verbatim answers):

- On the source, the user first asked back: _"OSM klingt gut, aber die lizenz sagt mir nichts. dürfte ich diese bzw. das generierte ergebnis im git repo hochladen?"_ — answered with the ODbL analysis below, after which the choice was _"Nur DB Infrago und in den Daten bewusstes filtern auf "Bahnhof", nicht "Haltepunkt" oder ähnliches"_.
- Boundary source: **Natural Earth 10m** (later replaced, see below).
- Stack: **Python + venv/uv with dependencies**, as a deliberate contrast to `csv_data`.

**What happened**

- **Web search, then live verification of every candidate** (Claude Opus 5). Seven
  candidates, six HTTP checks, one DNS failure. Nothing was accepted from a search
  snippet: the ZIP was downloaded, the CSV opened, the rows counted, the Overpass and
  SPARQL queries actually run.
- Chosen: **DB InfraGO `Infrastrukturdaten`** via the Mobilithek, CC BY 4.0, data status
  May 2026 — 10,632 `Betriebsstellen` with coordinates in EPSG:4326, 25832 *and* 31467.
- Rejected: **OSM/Overpass** (534 stations, best data, ODbL share-alike incompatible with
  the repository's CC BY), **Wikidata** (CC0, 1,718 hits in the bbox, coverage
  unverifiable), **`download-data.deutschebahn.com`** (the URL every tutorial still
  names — the host no longer resolves at all).
- Built `open_data_search/` with five scripts: two one-off provisioning fetchers, a
  builder and a verifier, plus the superseded Natural Earth fetcher kept as evidence.
- The source CSV is **sliced to NRW and committed** (658 KB, 1,671 rows, field values
  byte-identical) with a manifest carrying URL, licence, retrieval date and the ZIP's
  SHA-256 — because the portal that hosted the previous generation of this data set is
  already gone.
- Deduplication turned out to be the substantive problem: the source is route-centric, so
  893 rows describe 449 stations, 185 of them with several positions, spread up to
  **4,047 m** (Köln-Ehrenfeld). Implemented a **medoid** pick and carried
  `position_spread_m` into the output.
- **The main iteration.** The polygon check flagged one station as outside NRW — `HOE`
  Osnabrück-Eversburg — and it was written up as a genuine attribute error in official
  data. It was not. Nominatim reverse geocoding put the coordinate in *Lotte, Kreis
  Steinfurt, NRW*; the authoritative Geobasis NRW boundary put it **117 m inside** the
  state. The generalised Natural Earth outline was wrong by 1.3 km. Provisioned the
  authoritative **DVG2** boundary instead (dl-de/zero-2-0, Shapefile → GeoJSON, EPSG:25832
  → 4326, hence `pyshp` as a fourth dependency), re-ran the comparison across all of
  Germany, and found the source's `Bundesland` column and the geometry agree **0
  disagreements in either direction** over all 5,367 in-service `Bahnhof` rows.
- Verifier: six structural checks plus three informational measurements. Deliberate
  implementation independence — the builder hand-writes Web Mercator and calls shapely,
  the verifier calls **pyproj** and hand-writes ray casting.
- Added a **provenance check** with no counterpart in `csv_data`: every output coordinate
  must exist, unmodified, in a source row with the same DS 100 code.

**Artifacts**

- `open_data_search/README.md` — use-case documentation, incl. the candidate/licence table and the ODbL write-up
- `open_data_search/requirements.txt` — `requests`, `shapely`, `pyshp`, `pyproj`, pinned, each with its reason
- `open_data_search/scripts/fetch_infrago_source.py` — one-off provisioning: download, slice to NRW, write manifest
- `open_data_search/scripts/fetch_nrw_boundary.py` — one-off provisioning: authoritative DVG2 boundary, reprojected
- `open_data_search/scripts/fetch_nrw_boundary_ne10m.py` — the superseded Natural Earth fetcher, kept as evidence
- `open_data_search/scripts/build_stations.py` — filter, deduplicate by medoid, round, project
- `open_data_search/scripts/verify_stations.py` — provenance, axis order, bbox, containment, EPSG:3857, source quality
- `open_data_search/input/db_infrago_betriebsstellen_nrw.csv` — 1,671 source rows, verbatim
- `open_data_search/input/db_infrago_source.json` — provenance manifest incl. ZIP SHA-256
- `open_data_search/input/nrw_boundary_dvg2.geojson` — authoritative NRW outline, 7,130 vertices
- `open_data_search/input/nrw_boundary_ne10m.geojson` — the generalised outline that produced the false positive
- `open_data_search/output/nrw_stations.csv` — **the deliverable**, 449 stations
- `open_data_search/output/nrw_stations_raw_positions.csv` — 893 pre-dedup positions, evidence of the spread
- `open_data_search/output/verification_report.md` — all checks PASS

**Result / Iteration**

- **449 stations**, 0 outside NRW, 0 untraceable coordinates, max EPSG:3857 deviation
  **0.007 m**, pipeline runtime ~1 s, byte-identical on re-run after deleting `output/`.
- **The most valuable failure was mine, not the data's.** A generalised reference polygon
  made correct official data look wrong, and the first write-up said so. Two independent
  checks reversed it. "Your reference data is data too" is the finding — a 1:10 M outline
  is not a yardstick for a 100 m question. Both boundaries stay committed so the delta is
  reproducible.
- **The licence, not the geometry, picked the source.** OSM was better on every technical
  axis and unusable anyway. The ODbL distinction that decides it: a Derivative Database
  (the extracted rows) triggers share-alike; a Produced Work (a map, aggregate figures)
  needs attribution only. Written up in the use-case README for the talk, as requested.
- **The obvious deduplication would have been silently wrong.** `dict[ds100] = row` picks
  a point up to ~2 km off and leaves a data set that looks immaculate. Only measuring the
  intra-station spread before deduplicating exposes it.
- **Redundancy in the source identified which of its own columns to distrust.** Its
  EPSG:25832 columns agree with its EPSG:4326 columns to 1 mm; its `WKT WGS84` column
  disagrees with them by a median of 1.27 m. Two representations would only have shown a
  conflict; three showed which one to believe.
- **Verification depth is a decision that was never made explicitly** — the user's own
  observation, and a fair one. Adjudicating one row out of 449 cost a reverse-geocoding
  query, an authoritative Shapefile, a fourth dependency and a Germany-wide re-run. Right
  for real published geodata, likely over-engineering for staging test data. Recorded as a
  convention in `CLAUDE.md`: agree the tolerance up front rather than defaulting to rigour.
- **Deliberate gap, documented rather than papered over**: the exact `Art lang == "Bahnhof"`
  filter excludes 3 stations labelled `Bahnhof Abzweigstelle` (`EGST`, `ESMG`, `KDRA`). A
  substring match would have been the wrong fix, since it would also pull in the
  `Haltepunkt` compounds.
- Not committed. Waiting for an explicit request, per `CLAUDE.md` section 11.

---

## [006] 2026-08-21 — OpenSearch as an ArcGIS data source  ·  scope: `opensearch`

**Prompt (original, DE)**
> Jetzt zu einem weiteren Use Case. Ich möchte die Daten in einem anderen Format bereitstellen. ArcGIS Enterprise und ArcGIS Pro  unterstützen inzwischen das Darstellen von sogenannten View Layers mit OpenSearch bzw. ElasticSearch als Datenquelle. Ziel soll es sein, eine OpenSearch-Executable zu haben (kein Docker, per .sh bzw. .bat aus dem Dateisystem ausführbar für lokale Tests auf VMs), welche einen Index enthält, in dem die vorher in der CSV abgelegten Bahnhofsdaten abgelegt sind und als View Layer in ArcGIS Pro 3.7 dargestellt werden können und nach ArcGIS Enterprise 12.1 publiziert werden können. Ich kenne mich überhaupt nicht damit aus, und weiß nur, dass das gehen soll. Neben der Datenablage möchte ich OpenSearch nicht ins Git einchecken. Es soll Skripte geben, die eine Installation herunterladen und dann den Index erstellen und befüllen. Dann will ich OpenSearch per Skript ausführen können und die DB in ArcGIS Pro einbinden.

**Prompt (translation, EN)**
> Now on to another use case. I want to provide the data in a different format. ArcGIS Enterprise and ArcGIS Pro  now support displaying so-called view layers with OpenSearch or ElasticSearch as a data source. The goal is to have an OpenSearch executable (no Docker, runnable from the file system via .sh or .bat for local tests on VMs) which contains an index in which the station data previously stored in the CSV is stored and which can be displayed as a view layer in ArcGIS Pro 3.7 and published to ArcGIS Enterprise 12.1. I don't know anything about this at all, and only know that it is supposed to work. Besides the data storage I don't want to check OpenSearch into git. There should be scripts that download an installation and then create and fill the index. Then I want to be able to run OpenSearch via script and connect the DB in ArcGIS Pro.

**What happened**
- Research first, because "I only know that it is supposed to work" is the whole starting
  point. Esri's documentation for Pro 3.7 / Enterprise 12.1 produced five constraints that
  shaped every design decision: **only OpenSearch 2.12 is certified** (one minor release,
  not the 2.x line), the spatial reference is **fixed at EPSG:4326**, only **basic auth** is
  supported, the field-type mapping is a fixed table, and — the important one — *"The
  geopoint format that uses an object with a latitude and longitude is not supported with
  ArcGIS"*, i.e. `{"lat": …, "lon": …}`, the form in every OpenSearch tutorial.
- Four decisions agreed with the user up front: both platforms equally (`.sh` + `.bat`,
  Linux tested here, Windows written from documentation), TLS + basic auth as the default
  with `--insecure` as a flag, medium verification depth plus the axis-swap counter-test,
  and only the 449 NRW stations.
- Stack: shell/batch for provisioning, Python 3.12 **stdlib only** for indexing and
  verification — no venv, no `pip install`, so the use case comes up on a bare VM.
  Deliberately unlike `open_data_search`, which spends four dependencies on independence.
- Version, URLs and the OpenSearch-published SHA-512 for three platforms went into
  `input/opensearch_dist.json`; the ~820 MB archive goes to gitignored `build/`.
- Ran the whole chain on Linux: download, checksum, certificate generation, start, index,
  verify, stop. Then measured the negative cases on purpose — indices built with swapped
  axes and with the object format — to prove the checks fire.
- The user permitted committed demo credentials for this test cluster as an explicit
  exception. Turned out `admin/admin` is not available anyway: since 2.12 the demo
  installer runs the password through a strength check and rejects it.

**Artifacts**
- `opensearch/input/opensearch_dist.json` — pinned distribution manifest with checksums and the ArcGIS compatibility facts behind the pin
- `opensearch/scripts/setup_opensearch.sh` / `.bat` — download, verify, unpack, configure, generate CA + HTTPS certificate
- `opensearch/scripts/run_opensearch.sh` / `.bat` — start/stop/status/logs, waits for `_cluster/health`
- `opensearch/scripts/index_stations.py` — mapping + bulk payload + load, `--geo-format`, `--dry-run`
- `opensearch/scripts/verify_index.py` — 12 checks against the running index, Markdown report, exit code
- `opensearch/scripts/osclient.py` — stdlib REST client, HTTP/auth/TLS only, deliberately no geometry logic
- `opensearch/output/nrw_stations_mapping.json`, `nrw_stations_bulk.ndjson`, `verification_report.md`
- `opensearch/README.md` — five findings, setup, ArcGIS instructions

**Result / Iteration**
- Works: index `nrw_stations`, 449 documents, `green`, 12 of 12 checks passing, reachable
  over HTTPS with certificate verification on.
- **The finding of the folder, measured rather than argued.** An index built with the
  `{lat, lon}` object format fails **1 of 12** checks. Count, bounding box, `geo_distance`
  against an independent haversine, coordinate provenance — all green. Only the check that
  knows what the *client* needs catches it. Swapped axes, by comparison, fail 5 of 12 and
  put the stations in Somalia. The loud error is the harmless one.
- **Three failures on the way, all instructive.** (1) The demo TLS configuration of the
  certified release is expired: `root-ca.pem` was issued 2023-08-29 with a **30-day**
  validity and died 2023-09-28, while the node certificate it signed runs to 2033 — so the
  documented quick start is dead and every client says `certificate has expired`. Fixed by
  generating a CA with the bundled JDK's `keytool`. (2) The first fix, a single self-signed
  certificate with `CA:true`, failed with `No certificates found in http.p12 with alias
  http` — OpenSearch Security filters CA certificates out of the server chain, so a real
  two-level chain is required. (3) The OpenSearch **SQL plugin reads only** the object
  format (`geo point must in format of {"lat": number, "lon": number}`) for array, string,
  WKT and geohash alike — exactly the format Esri forbids. ArcGIS query layers are SQL, so
  if ArcGIS delegates to the plugin there is no working representation at all. Reported as
  INFO, never as a failure, because whether ArcGIS uses the plugin cannot be determined
  from this side.
- Honest gap: the ArcGIS side is **documented, not tested** — no ArcGIS installation here.
  Same for the `.bat` scripts, which are written from the Windows documentation. Both are
  marked as such in the README rather than implied to work.
- Cluster health is `yellow` and stays that way: the security plugin's system index wants a
  replica a single node never assigns. The station index itself is `green`.
- Not committed. Waiting for an explicit request, per `CLAUDE.md` section 11.

---

## [007] 2026-08-21 — The talk as code: Slidev deck and GitHub Pages  ·  scope: `slides`, root

**Prompt (original, DE)**
> Den letzten Use Case (opensearch) habe ich noch nicht getestet. Ich möchte jedoch schon an einer anderen Stelle weiter machen. Es geht um die Präsentation für den Talk und einen ersten Wurf dazu. Mir schwebt vor, statt klassischer Powerpoint irgendein JS / HTML basiertes Präsentationsformat zu wählen und die Präsentation dann auch "as Code" im repository zu haben. Da es ja auf Github gehostet ist, könnte ich mir eine Variante über Github Pages oder ähnliches vorstellen. Helfe mir dabei, ein Setup aufzusetzen und lass uns schon einen ersten Entwurf mit den bisherigen Erkenntnissen machen (die gewünschte Visualisierung für die CSV-Daten hat funktioniert. In den jeweiligen Input Ordnern habe ich Screenshots mit den Ergebnissen abgelegt)

**Prompt (translation, EN)**
> I have not tested the last use case (opensearch) yet. But I would like to move on somewhere else already. It is about the presentation for the talk and a first draft of it. What I have in mind is choosing some JS / HTML based presentation format instead of classic PowerPoint and then also having the presentation "as code" in the repository. Since it is hosted on GitHub, I could imagine a variant via GitHub Pages or similar. Help me set up a setup and let us do a first draft with the findings so far (the desired visualisation for the CSV data worked. In the respective input folders I have put screenshots with the results)

**Follow-up answer that reshaped the task (original, DE)**
> Ich habe mit Fragen leider nur 15 minuten zeit. es kann also wirklich nicht sehr umfangreich werden. und neben den 3 fertigen usecases kommen vermutlich noch 1-2 dazu. vermutlich wird es keine live demo geben, screenshots als proof müssen vermutlich ausreichen. wir müssen also fokussieren

**Follow-up answer (translation, EN)**
> Unfortunately I only have 15 minutes including questions. So it really cannot be very extensive. And besides the 3 finished use cases there will probably be 1-2 more. There will probably be no live demo, screenshots as proof will probably have to be enough. So we have to focus.

**What happened**
- Clarified four decisions up front via a question round: framework (**Slidev**,
  recommended over reveal.js and Marp for its code presentation), deck language
  (**English**), scope, and narrative shape (**chronological, thematically
  clamped** — the use-case journey as backbone, each act ending on a named rule).
- The scope answer changed the whole design: **15 minutes including questions**
  is ~12 minutes of speaking, i.e. ~14 slides, for three finished use cases and
  one or two more coming. So the deck was designed as a mechanism for *leaving
  things out*: a core deck of **four named rules**, each proven by one measured
  number and one image, plus a **backup section** written out but not shown.
- Set up `slides/` with Slidev 52, theme `seriph`, local dependencies only.
  Entry `slides.md` plus six `pages/*.md` includes, one per act. `style.css` is
  ~60 lines.
- Wrote `scripts/sync_assets.mjs` (no dependencies) to copy the three ArcGIS
  screenshots out of the use-case `input/` folders into `public/img/`, which is
  gitignored — Vite cannot serve assets from outside the project root, and there
  is no reason for a second copy of 4.8 MB of PNG in git. Wired to `predev` /
  `prebuild`, so it cannot be forgotten.
- `scripts/make_qr.mjs` generates the closing slide's QR code once; the 1.9 kB
  SVG is committed.
- Added `.github/workflows/deploy-slides.yml`: builds `slides/` on every push to
  `main` touching the deck or a screenshot, `--base` derived from the repository
  name, publishes `slides/dist` to Pages.
- Verified visually, not just by exit code: no browser was available, so the
  deck was rendered to PNG with `playwright-chromium` (installed
  `--no-save`, so CI never downloads it) and every slide was inspected.

**Artifacts**
- `slides/slides.md`, `slides/pages/*.md` — 22 slides: 14 core, 8 backup
- `slides/style.css` — `.rule`, `.metric`, `.cols`, `.checks`, `.cover-bg`
- `slides/scripts/sync_assets.mjs`, `slides/scripts/make_qr.mjs`
- `slides/public/qr-repo.svg` — committed, regenerated only on a rename
- `slides/README.md` — stack, commands, time budget per slide, house rule
- `.github/workflows/deploy-slides.yml` — Pages deploy from a subfolder
- `.gitignore`, `README.md`, `CLAUDE.md` — updated

**Result / Iteration**
- **The first build was green and three slides were broken.** Rendering to PNG
  and looking at them found: the act-3 comparison slide cut its own punchline
  ("5 of 12 red" / "1 of 12 red") off the bottom edge; the rule-4 slide cut the
  last word of the rule; and Slidev's `two-cols-header` layout let a long left
  column run *underneath* the screenshot in the right column, clipping words
  mid-sentence. Fixed by replacing that layout with an explicit CSS grid, by
  cutting text, and by a modest global font reduction. Same lesson as act 3 of
  the talk itself: verify against the consumer, and the consumer here is a
  projector.
- **The repository's own licence rule killed its prettiest slide.** The obvious
  cover is the 10,000-point map full-bleed behind the title. A background image
  is cropped to fill, and the first thing cropped off an ArcGIS capture is the
  `Esri | TomTom | Garmin | USGS | FAO | NOAA` attribution bar. Replaced with a
  plain gradient; the screenshots now appear only as `object-contain` images with
  the bar intact. Written into `CLAUDE.md` as a convention.
- Open, and deliberately not resolved here: the deck is a **first draft** and has
  not been rehearsed against a clock. The per-slide budgets sum to ~11 minutes on
  paper only.
- Not yet verifiable: the Pages deployment. Actions-based Pages needs a public
  repository, so the workflow cannot be proven until publication — the build job
  will succeed and the deploy job will fail until then.
- Unchanged: no use-case folder was touched. Code snippets in the deck are inline
  rather than imported with Slidev's `<<< @/path` syntax, because the useful form
  of that would require adding `#region` markers to existing use-case scripts.

---

## [008] 2026-09-04 — Publishing the OpenSearch layer: the wrong "Feature" check box  ·  scope: `opensearch`

**Prompt (original, DE)**
> Das Aufsetzen des Opensearch-Clusters hat funktioniert. Auch das einladen in ArcGIS Pro. Unter @opensearch/input/nrw_stations_opensearch_viewlayer.png habe ich einen Screenshot mit dem Ergebnis abgelegt. Wie aber zu erwarten war, kann dieser Layer nicht publiziert werden. in ArcGIS Pro wird gesagt: Layers Datasource is not supportet. Gibt es noch einen anderen Weg, die Daten als FeatureService zu publizieren?

**Prompt (translation, EN)**
> Setting up the OpenSearch cluster worked. Loading it into ArcGIS Pro as well. Under @opensearch/input/nrw_stations_opensearch_viewlayer.png I have put a screenshot with the result. But as was to be expected, this layer cannot be published. In ArcGIS Pro it says: Layers Datasource is not supportet. Is there another way to publish the data as a FeatureService?

**What happened**
- The user had done what [006] left open: installed the cluster on Windows,
  indexed the stations, connected ArcGIS Pro 3.7 over the private CA and drawn
  all 449 stations. The screenshot shows the `.dbconn` in the Catalog pane, the
  pop-up with real attributes, and the automatic feature binning the README had
  predicted from Esri's documentation.
- Research against Esri's current documentation, three pages, quoted to the full
  stop this time: analyzer message **24078**, *Manage registered data stores*,
  and *Connect to OpenSearch from ArcGIS* (Server 12.0).
- **The "contradiction" [006] recorded does not exist.** That entry quoted
  *"Sharing query layers from Elasticsearch or OpenSearch is not supported"* and
  could not reconcile it with the *Reference registered data → Feature* workflow
  documented right next to it. The sentence does not end there. It continues
  *"…as a map image layer or web feature layer that copies all data, a web tile
  layer, a vector tile, a web scene layer, or a map service"* — an enumeration
  of what is excluded, and the reference-registered-data route is not in it.
- So the answer to the prompt is yes, and it is one route rather than another
  way: the *Share → Web Layer* pane offers a check box labelled **Feature**
  twice, under *Copy all data* and under *Reference registered data*. The first
  is unsupported for OpenSearch; the error names neither.
- Derived, not quoted, and flagged as such: because Esri requires the server
  database connection to be **identical** to the publisher connection for
  OpenSearch, a `.dbconn` pointing at `https://localhost:9200` cannot work — the
  federated server would resolve that on its own machine. The cluster has to be
  reachable under one name from both, which is what `--host` / `--san` are for.
- Considered and not built, at the user's decision: a Koop server
  (`@koopjs/provider-elasticsearch`, Apache-2.0, OpenSearch support in beta) in
  front of the index, which would serve a genuine FeatureServer without any
  Enterprise at all. Recorded in the README as the fallback.

**Artifacts**
- `opensearch/input/nrw_stations_opensearch_viewlayer.png` — the working Pro
  layer; the evidence that the connection side is done
- `opensearch/README.md` — new finding 6, "Connecting from ArcGIS" rewritten
  from documented-not-tested to tested-in-part, publishing section replaced by
  the support matrix and the corrected procedure
- `README.md`, `CLAUDE.md` — progress log and the new quoting convention

**Result / Iteration**
- **The best finding is a retraction.** [006] predicted a contradiction in
  Esri's documentation and was pleased with it. The contradiction was a
  truncated quote in our own notes. A shortened quote reads exactly like a
  vendor being inconsistent, which is a comfortable conclusion and stops the
  search — the sentence has to be read to the full stop before it can be called
  a contradiction. Written into `CLAUDE.md`.
- **The unsupported option is the one that looks default.** Two identically
  labelled check boxes in one pane, one of which works, and an error message
  (`Layer's Datasource is not supported`) that mentions neither the check box
  nor the word OpenSearch. Same shape as finding 2 of this folder in reverse:
  there the harmless error was loud, here the fatal choice is quiet.
- **Resolved later the same day.** The corrected check box was right: with the
  data store registered and *Reference registered data — Feature* selected, the
  layer publishes. Two certificate problems stood in between, see [009] and
  [010]. The `localhost` worry in this entry was wrong — server and cluster turned
  out to be co-located, which [009] establishes from the shape of the next
  error.
- Open point on the screenshot: it carries an Esri World Topographic basemap
  with no attribution bar — ArcGIS Pro does not paint one into the map view. A
  caption naming the sources was added under the image in the README rather than
  recapturing it. The later Map Viewer capture of the published service does
  carry the full bar (`Land NRW | LGLN | Esri | TomTom | Garmin | USGS | FAO |
  NOAA`), so the repository has a compliant capture either way.

---

## [009] 2026-09-04 — WinINet 12045: one machine, one certificate, two trust stores  ·  scope: `opensearch`

**Prompt (original, DE)**
> beim Publizieren fliegt noch folgender Fehler im ArcGIS Server Log: The certificate authority is invalid or incorrect (WinINet ERROR_INTERNET_INVALID_CA, 12045), URL = https://localhost:9200

**Prompt (translation, EN)**
> when publishing the following error still comes up in the ArcGIS Server log: The certificate authority is invalid or incorrect (WinINet ERROR_INTERNET_INVALID_CA, 12045), URL = https://localhost:9200

Followed mid-turn by:

> Der ArcGIS Server wurde aber seit dem Import in den Truststore beim aufsetzen des Clusters noch nicht neu gestartet

> But the ArcGIS Server has not been restarted since the import into the trust store during the setting up of the cluster

**What happened**
- Checked the certificate before the client: `openssl x509` on the generated
  files shows `CN=localhost`, SAN `DNS:localhost, IP:127.0.0.1, IP:::1`, root
  `CA:TRUE, pathlen:0`, leaf `CA:FALSE`, both valid to 2036. Nothing wrong with
  it, so the error is about trust, not about the artifact.
- Distinguished the WinINet codes: 12045 is `ERROR_INTERNET_INVALID_CA`, and a
  hostname mismatch would be 12038. That narrows it to the chain and rules out
  the `localhost` name.
- **Retracted part of [008].** That entry warned that a `.dbconn` on `localhost`
  would send the federated server to its own machine. A TLS *rejection* proves a
  TLS *handshake* happened, so ArcGIS Server and OpenSearch are co-located here
  and the warning did not apply. Kept in the README, marked as predicted and
  measured not to bite.
- **Found the actual cause in our own documentation.** The README told the user
  to import the CA with `certmgr.msc`. That is *Certificates, Current User*.
  ArcGIS Pro runs as the interactive user and was satisfied; ArcGIS Server runs
  as a service account and reads *Certificates, Local Computer* (`certlm.msc`).
  Corroborated by Esri knowledge base 000013244, which resolves the identical
  error by importing the root into the Local Computer store.
- The user's follow-up reorders the diagnosis: the service has not been
  restarted since the import, and the service process does not pick up a store
  change made while it was running. So restart first, verify the store scope
  second - documented in that order, with a PowerShell pair that reads
  `Cert:\LocalMachine\Root` against `Cert:\CurrentUser\Root` so the scope is
  measured rather than assumed.
- Fixed the misleading hint at its source: both `setup_opensearch.sh` and
  `setup_opensearch.bat` printed the `certmgr.msc`-shaped advice on every run.

**Artifacts**
- `opensearch/README.md` — finding 7, the corrected Pro step 1, the server-side
  trust procedure, the marked retraction of the `localhost` prediction
- `opensearch/scripts/setup_opensearch.sh`, `.bat` — corrected closing hint
- `README.md`, `CLAUDE.md` — progress log, new convention

**Result / Iteration**
- **Two consumers of one certificate, and only one of them has a dialog.** This
  is finding 2 of the folder in a new costume: the loud failure (Pro refusing to
  connect) was the one everybody would have caught, and the silent one is that a
  successful Pro connection says nothing about a service on the same machine.
  "I imported the certificate" is not a statement about the machine.
- **The documentation caused the bug it then had to explain.** `certmgr.msc` was
  written into this repository from Windows documentation, in the same pass that
  described the ArcGIS side without an ArcGIS installation. It is correct for
  the client it was tested against and wrong for the one it was not.
- **Resolved: both were needed.** The import went into the Local Computer store
  *and* the service was restarted, and the WinINet error disappeared. So the
  `certmgr.msc` advice this repository gave was not harmless luck — it was the
  bug. It did not end the matter, though: a third trust store was waiting behind
  it, see [010].

---

## [010] 2026-09-04 — The same product, the same certificate, a second trust store  ·  scope: `opensearch`

**Prompt (original, DE)**
> ich hab das cert in die local maschine importiert und den server neu gestartet. nun bekomme ich aber trotzdem noch 0 : javax.net.ssl.SSLHandshakeException: (certificate_unknown) PKIX path building failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to find valid certification path to requested target See https://opensearch.org/docs/latest/clients/java/ for troubleshooting.

**Prompt (translation, EN)**
> i imported the cert into the local machine and restarted the server. but now i still get 0 : javax.net.ssl.SSLHandshakeException: (certificate_unknown) PKIX path building failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to find valid certification path to requested target See https://opensearch.org/docs/latest/clients/java/ for troubleshooting.

**What happened**
- Read the change in the error rather than the error: `WinINet 12045` is gone.
  The fix from [009] worked; what is left is a different runtime. `PKIX` and
  `sun.security.provider.certpath` are the JVM, and a JVM does not consult the
  Windows certificate store - it reads its own `cacerts`.
- **So ArcGIS Server needs the same certificate imported twice.** It is part
  native and part Java, and it reaches OpenSearch through the OpenSearch Java
  client (the URL in the error message is Esri handing through that client's own
  troubleshooting link). Two unrelated trust stores in one product.
- Documented the supported route rather than the working one: Server
  Administrator Directory → `machines` → *<MACHINE>* → `sslcertificates` →
  `importRootOrIntermediate` (POST, `alias` + `rootCACertificate`), then restart
  the machine. Explicitly warned *against* `keytool` on
  `Server\framework\runtime\jre\lib\security\cacerts` — it works, and an upgrade
  replaces that JRE and silently removes the trust again.
- Added Portal for ArcGIS as the fourth store on the list (own `cacerts`, own
  admin-directory import, own restart), flagged as not measured — publishing
  runs Pro → Portal → Server, so it is where the Java error goes next if it
  moves.
- Renamed finding 7 to cover the cascade and gave it the table of four
  consumers, four stores, four mechanisms.

**Artifacts**
- `opensearch/README.md` — finding 7 extended and retitled, steps 3 and 4 added
  to the publishing procedure, status and talk notes updated
- `README.md`, `CLAUDE.md` — progress log, sharpened convention

**Result / Iteration**
- **Every fix in this chain was a successful verification that proved nothing
  about the next consumer.** Pro connected — that was real, and said nothing
  about the service. The Local Computer store validated and WinINet went quiet —
  also real, and said nothing about the JVM in the same process tree. Three
  green results in a row, three more failures behind them. This is the
  strongest version of the folder's own rule so far, because it needs no
  contrived example: the *same product on the same machine reading the same
  file* answers differently depending on which half of itself is asking.
- Sharpened the `CLAUDE.md` rule accordingly: a trust store is per **runtime**,
  not merely per principal, and one product can appear on the consumer list more
  than once.
- **Resolved, and with it the whole chain.** The admin-directory import into the
  ArcGIS Server JVM was the last step: the layer publishes as a web feature layer
  referencing the index, opens in Map Viewer and answers its pop-ups out of
  OpenSearch with no copy of the data anywhere. Portal's truststore turned out
  not to be needed on this deployment — it stays documented as the next place to
  look, not as a step. Evidence:
  `opensearch/input/nrw_stations_opensearch_service.png`.
- Two predictions from [006], written without an ArcGIS installation in the
  room, are visible in that screenshot and both hold: `_id` became the Object ID
  (it shows as `EMST`, the DS100 code), and `x_3857` / `y_3857` arrive as plain
  attributes while the geometry is drawn from `location` alone.

---

## [011] 2026-09-04 — A second index from a geodatabase export  ·  scope: `opensearch`

**Prompt (original, DE)**
> Nun ein weiterer Use Case: das Setup für den open Search cluster steht, ich konnte die Daten anzeigen und auch publizieren. nun habe ich unter @opensearch/input/ eine GeoJSON abgelegt, welche einem Export aus einer bestehenden Featureclass aus einer Enterprise Geodatabase entspricht. diese soll nun als weiterer Index im Opensearch-Cluster erscheinen und von da aus verwendet werden. Ziel dabei ist zu zeigen, dass auch unterschiedliche Datenquellen dafür herhalten können. Vermutlich ein etwas kleinerer Use Case mit weniger Änderungen, aber eine nette ergänzung

**Prompt (translation, EN)**
> Now another use case: the setup for the open Search cluster is in place, I was able to display the data and also publish it. now I have placed a GeoJSON under @opensearch/input/ which corresponds to an export from an existing feature class from an Enterprise Geodatabase. this should now appear as a further index in the Opensearch cluster and be used from there. The goal is to show that different data sources can also serve for this. Probably a somewhat smaller use case with fewer changes, but a nice addition.

Follow-up, after the plan was presented:

> da ich den cluster durch kopieren des opensearch-ordner auf einen anderen (Windows)-Rechner aufgebaut habe, brauche ich noch eine "um den 2. Index aufzubauen, kopiere und ersetze folgende Dateien" Anleitung

> since I built the cluster by copying the opensearch folder onto another (Windows) machine, I still need a "to build the 2nd index, copy and replace the following files" instruction

**What happened**

- Profiled `input/airports.json` before touching anything, which produced four
  facts that reshaped the task:
  1. **It is not GeoJSON.** It is an Esri JSON FeatureSet (`query?f=json`):
     `geometryType: "esriGeometryPoint"`, geometry as `{"x","y"}`,
     `spatialReference {"wkid": 102100, "latestWkid": 3857}` — Web Mercator in
     **metres**, where RFC 7946 GeoJSON is always EPSG:4326.
  2. It therefore has to be **reprojected**, the exact operation
     `index_stations.py` refuses to perform.
  3. It **crosses the antimeridian** (lon −177.37 … +166.64), so its naive
     bounding box is 344° × 86° and useless as a check.
  4. It carries **no licence statement**.
- Asked four questions rather than guessing: licence/provenance, verification
  depth (CLAUDE.md section 12 requires asking), permission to refactor the
  existing scripts, and stdlib-vs-`pyproj` for the projection. Answers: the file
  is an internal export of unknown licence and only its *structure* may be
  copied, with that reason recorded explicitly; full public-grade verification;
  new scripts with shared helpers; stdlib with two separate computation paths.
- Gitignored `opensearch/input/airports.json` with the reason in the ignore file
  itself, then extracted only its schema and its measured distributions.
- Wrote `make_airports_fixture.py`, a one-off provisioning script (the
  CLAUDE.md section 3 exception) producing `input/synthetic_airports.json`:
  structure identical, every value generated, `sin(latitude)` sampled uniformly,
  rounded to 6 decimals before projecting, self-checking, and carrying its own
  `_provenance` block plus a manifest with SHA-256.
- Move-only refactor into `geopoint.py` (indexer side) and `arcgis_checks.py`
  (verifier side), plus `webmercator.py` holding **only the forward
  projection**. The inverse lives in `index_airports.py` alone, so the verifier
  checks it by running the opposite direction with code the indexer cannot
  import.
- Regression-proved the refactor before continuing: re-ran
  `index_stations.py --dry-run` and `git diff` on the committed artifacts was
  empty; the existing verifier stayed 12/12 green against the live cluster.
- Checked Esri's documentation for reserved field names in query layers over
  document databases. **It names none** — only `_id` as the default unique
  identifier and "an integer field that contains unique values" as the
  alternative. Recorded that as "not documented" instead of inventing a
  conflict, and prefixed `source_objectid` / `source_esri_oid` /
  `source_globalid` for a different, measurable reason.
- Built `index_airports.py` (aborts on an unexpected `geometryType` or `wkid`
  rather than converting) and `verify_airports.py` (19 checks).
- Proved the verifier fails, three times, on a document moved 40 km inside
  Kansas.
- Added `.gitattributes` (`* text=auto eol=lf`, `*.bat` excepted) so a Windows
  clone cannot break the fixture's SHA-256, and wrote the file-copy instruction
  the follow-up prompt asked for.

**Artifacts**
- `opensearch/scripts/make_airports_fixture.py` — one-off fixture generator
- `opensearch/scripts/index_airports.py` — Esri JSON → OpenSearch, hand-written
  inverse Mercator
- `opensearch/scripts/verify_airports.py` — 19 checks
- `opensearch/scripts/diagnose_fixture.py` — locates why a rebuilt fixture's
  hash differs: environment, RNG fingerprints, libm hex floats, field-level diff
- `opensearch/scripts/webmercator.py` — forward projection only, never imported
  by an indexer
- `opensearch/scripts/geopoint.py`, `opensearch/scripts/arcgis_checks.py` —
  move-only extractions shared by the two script pairs
- `opensearch/input/synthetic_airports.json` — 880 features, 248 KB
- `opensearch/input/synthetic_airports_source.json` — manifest, SHA-256,
  region boxes
- `opensearch/output/synthetic_airports_{mapping.json,bulk.ndjson}` — 17 fields,
  415 KB
- `opensearch/output/synthetic_airports_verification_report.md` — 19 checks,
  0 failed
- `opensearch/input/synthetic_airports_opensearch_viewlayer.png` — ArcGIS Pro
  3.7 query layer over the second index, both indexes in one connection
- `.gitignore`, `.gitattributes` — the licence exclusion and the LF pin
- `opensearch/README.md` — findings 8–11, second schema table, transfer
  instruction; `README.md`, `CLAUDE.md` — index, executables, progress,
  conventions

**Result / Iteration**

- **The licence stopped the use case as designed, and the replacement is
  better.** A real export handed over to prove a second source works, and it
  could not be used — not for the geometry but because nobody could say what the
  licence was ("I think it's the FAA data set, but I don't know for sure"). The
  file is gitignored and its structure rebuilt with generated values. That is
  this repository's thesis happening rather than being asserted, and it is the
  best story the folder has produced. What no rebuild restores is the one
  property that made the original evidence: that somebody else published it.
- **"It's a GeoJSON" was wrong in the one way with no error message.** Metres
  read as degrees are out of range; a library that clamps rather than raises
  puts every point on the antimeridian, consistently, so the data looks
  systematic instead of broken. The reader now asserts and aborts.
- **Two fixture properties were wrong on the first attempt**, and both looked
  plausible. `type` came out uniform (86/86/85/85/85) where the source has a 6:1
  skew, because the generator filled it round-robin. `tot_enp` topped out at 3.7
  million against the source's 38.9 million, because the first sigma was
  guessed; it is now derived from the measured spread. Neither would have
  surfaced without the original still sitting there to measure against — an
  argument for measuring the thing you are about to replace *before* replacing
  it.
- **The axis-swap check degrades in two ways this data set exposed.** For five
  of seven regions the transposed box does not exist at all: Alaska's longitudes
  are −179.5…−129.5, and OpenSearch rejects the query with `top is below bottom
  corner: -129.5 vs. -90.0`. Where it does apply it passes only because no
  airport sits at longitude −14…71 — luck, and the report says so.
- **The same bug is loud here and silent there.** `--swap-axes` gets **550 of
  880 documents rejected** (`illegal latitude value [-97.302373]`) and the load
  aborts; 330 would have been silently misplaced. On the stations, latitude
  50-52 and longitude 5-9 are both valid latitudes, so all 449 loaded happily
  into the Indian Ocean. Nothing in the code differs. The verifier that caught
  the stations was luckier, not better — the most uncomfortable finding of the
  session.
- **Provenance for transformed data needs two checks, and they were proven to
  fire separately.** Moving one document 40 km inside Kansas: both red. Moving
  only the degrees: reprojection red, provenance green. Only the metres:
  the reverse. In all three cases the other 17 checks stayed green — bounding
  boxes, axis order, antimeridian, `geo_distance`, field types. Forward round
  trip across all 880 documents: **0.0500 mm**, exactly half the rounding step
  of the stored metres (0.2 mm on the original export, whose metres were not
  derived from rounded degrees at all). It closed at 0.0000 mm until the
  cross-platform fix below forced the metres to be stored rounded — a worse
  number and a reproducible file.
- **The naive bounding box is 344.63° wide** and passes. Replaced by seven
  regional boxes plus one that deliberately wraps the antimeridian and matches
  42 documents, the same 42 computed from the source.
- **The follow-up prompt caught a real hazard.** The move-only refactor makes
  `index_stations.py` and `verify_index.py` depend on the new modules, so a
  partial copy to the Windows machine yields a working second index and a first
  one dying with `ImportError`. The instruction says all-or-nothing, and
  `.gitattributes` now pins LF so a clone cannot invalidate the fixture's
  SHA-256 by rewriting newlines.
- **Confirmed in ArcGIS Pro 3.7 the same day**, with evidence:
  `opensearch/input/synthetic_airports_opensearch_viewlayer.png`. The query
  layer opens, the points draw, feature binning switched itself on, and the
  Catalog pane shows **both** indexes under one
  `OpenSearch-https_localhost_9200.dbconn` — the whole claim of this addition in
  one screenshot. The nineteen checks predicted the client correctly, which is
  the less informative of the two possible outcomes: a checklist that agrees
  with the consumer says less than one that disagrees, which is how finding 1
  was found in the first place.
- **The screenshot was cross-checked rather than admired.** All nine values the
  pop-up rendered for `ILD` / *Yarrowmead Mem* are byte-identical to
  `output/synthetic_airports_bulk.ndjson`. It also confirms two findings
  visually that were until then only measured: the row shows `airport_oid` 490,
  `source_objectid` 251 and `source_esri_oid` 50 — three different integers, and
  ArcGIS using none of them, because its Object ID is the string `_id` `ILD`.
  And `airport_type` and `field` render as **empty cells** while both hold
  `" "`, so a user filtering that attribute table for blanks finds nothing.
- **The cross-platform fixture hash did NOT match — finding 12, and the best
  thing the follow-up produced.** Rebuilding with the same seed on Windows
  Server 2025 / CPython 3.14.7 gave `4d180ba8…50d90b` against Linux / CPython
  3.12.7's `b798f3d9…2df7cb`, at identical file size (256.3 KB) and feature
  count (880). `scripts/diagnose_fixture.py` was written to locate it and ruled
  out the boring causes in order:
  - **newlines**: `Get-FileHash` agreed with the hash computed from the
    in-memory string, so the bytes on disk are what Python produced. This was
    the expected cause and it was wrong.
  - **the seed**: all six RNG fingerprints identical — across two Python minor
    versions, which is a quietly reassuring result of its own.
  - **attributes and ordering**: identical at all 880 positions.

  What remained was `y`: **30 of 880 values differing by up to 2 ULP, 1.9
  nanometres**, while `x` differed in **0 of 880**. `x = R·radians(lon)` is a
  multiplication and exact on any IEEE-754 machine; `y = R·log(tan(π/4 + φ/2))`
  passes through `libm` twice, and C transcendental functions are not
  standardised to the last bit. Stored as raw doubles, that bit reached
  `json.dumps` and changed the hash.
- **Two things about the fix were more instructive than the fix.** First, the
  five hex-float `libm` comparisons in the diagnostic were **bit-identical on
  both machines and still are** — the divergence rate is 3.4 %, so five samples
  had an 84 % chance of showing nothing. The fingerprint section reassures
  wrongly; the field-level diff answers. Second, rounding the metres only works
  while no value sits on a rounding boundary, and that is a property of the data
  rather than of the idea: measured, four decimals leave the closest value
  **15.6×** the divergence away, five decimals 1.3× and six decimals **0.5×** —
  at six, rounding would have changed nothing. So the generator now measures
  that margin on the *unrounded* values, records it in `_provenance` and the
  manifest, and refuses to write a fixture whose margin is under 1e-08 m. The
  first version of that check read the **rounded** values, which sit on the grid
  by definition and therefore always pass — a check proving nothing, found by
  asking what it would take to make it fail.
- **Resolved.** Projected metres are stored rounded to four decimals — a tenth
  of a millimetre, and the precision the original geodatabase export actually
  carried, so the fixture became *more* structurally faithful, not less. New
  hash `247e2d00…9efe283`, confirmed byte-identical on both platforms. The cost
  is finding 10's headline number: the forward round trip now closes at 0.05 mm
  instead of 0.0000 mm. The tolerance stays at 1 mm rather than being tightened
  to 0.06, because a check calibrated to this artifact's exact rounding would
  fail on the next source for a reason that is not an error.

---

## [012] 2026-09-04 — A universal importer into an Enterprise Geodatabase, and the API that cannot  ·  scope: `egdb_import`, root

**Prompt (original, DE)**
> Nun ein weiterer Use case, welcher tatsächlich einer der wichtigsten ist, da es sehr nahe an das herankommt, was wir im alltag sehr oft brauchen. Ich möchte einen Mechanismus entwickeln, welche unter nutzung der ArcGIS API for Python einen importer bereitstellt, welcher es ermöglich, auf einer Instanz einer Enterprise Geodatabase (EGDB) eine FeatureClass zu erzeugen und generierte oder recherchierte Daten (siehe die anderen use cases) in diese Importiert. Idealerweise auch so gestaltet, dass es universell nutzbar ist. Ich nehme mir daten, also csv oder json und das python programm analysiert diese, baut die featureclass entsprechend der struktur, legt diese in der Datenbank instanz an und importiert die dann. von da aus soll diese wieder in ArcGIS Pro genutzt werden. die bestehende EGDB soll auf einer maschine (im testfall wieder windows) unter localhost laufen, in der regel ist es eine postgresql instanz. Ziel ist ArcGIS Enterprise 12.1. Am anfang wäre es auch ok, wenn das transformieren der ausgangsdaten in ein lesbares format auch über irgendwelche anderen skripte möglich ist, je nachdem was einfach ist.

**Prompt (translation, EN)**
> Now another use case, which is actually one of the most important ones, because it comes very close to what we need very often in everyday work. I want to develop a mechanism which, using the ArcGIS API for Python, provides an importer that makes it possible to create a FeatureClass on an instance of an Enterprise Geodatabase (EGDB) and import generated or researched data (see the other use cases) into it. Ideally also designed so that it is universally usable. I take data, so csv or json, and the python program analyses it, builds the featureclass according to the structure, creates it in the database instance and then imports it. From there it should be used in ArcGIS Pro again. The existing EGDB should run on a machine (in the test case Windows again) on localhost, usually it is a postgresql instance. The target is ArcGIS Enterprise 12.1. At the beginning it would also be OK if transforming the source data into a readable format is possible via some other scripts, depending on what is easy.

**What happened**

- Four decisions agreed up front before any code (CLAUDE.md §12): new folder `egdb_import` rather than filling the `python_import` stub; the Windows VM with ArcGIS Pro 3.7 / Enterprise 12.1 and an existing PostgreSQL EGDB as the test environment; `csv_data/output/nrw_points.csv` as the committed demo source; verification depth **"plausible is enough"**. Credentials by environment variable only, connection template with placeholders, and no publishing to Enterprise (already shown in `opensearch`).
- Documentation research first, and it changed the architecture. **The ArcGIS API for Python cannot create a feature class in an Enterprise Geodatabase.** The `arcgis` package is a REST client for a portal with no database connectivity at all — no SDE connection object, no `arcpy.da` equivalent. `GIS.content.import_data()` produces a *hosted* layer in the ArcGIS Data Store, copying the rows out of the customer's database. So the work is arcpy's, which means Windows and a licence.
- Built three stages, split so only the middle one needs the VM: `analyze_source.py` (stdlib, anywhere) measures the source and writes an editable **schema contract**; `import_to_egdb.py` (arcpy) transcribes it into `CreateFeatureclass` + `AddField` + `InsertCursor`; `verify_featureclass.py` (arcpy) reads it back. The contract is the "universal" interface the prompt asked for — any other script can produce one.
- Then measured the requested route instead of just asserting it was wrong, with `try_arcgis_api.py`. This produced the best finding in the folder, and it took four environments to see it (see Result).
- Readers for CSV, a JSON array of objects, GeoJSON `FeatureCollection` and Esri JSON `FeatureSet`. The FeatureSet reader asserts `geometryType` and the spatial reference and aborts; smoke-tested against the real `opensearch` fixture, where it correctly refused because the file carries a column literally named `objectid` — the geodatabase manages that name itself.
- `--dry-run` was made a *check* rather than a printout: it coerces every row to its declared field type without importing arcpy. Proven to fire on three perturbed copies of the source.
- Documentation duties: this entry, `egdb_import/README.md`, root `README.md` (index, four executables rows, conventions bullet, progress log), `CLAUDE.md`, and three backup slides.

**Artifacts**

- `egdb_import/scripts/analyze_source.py` — measure a source, write the schema contract; refuses to guess a CRS
- `egdb_import/scripts/schema.py` — type inference with evidence, and the geodatabase's name rules
- `egdb_import/scripts/sources.py` — the three JSON shapes and CSV, shared by analyser and loader
- `egdb_import/scripts/import_to_egdb.py` — the arcpy loader, with a rehearsing `--dry-run`
- `egdb_import/scripts/verify_featureclass.py` — eight checks plus two INFO rows, read back independently
- `egdb_import/scripts/egdb_checks.py` — verifier-only: the Esri type vocabulary, transcribed not derived
- `egdb_import/scripts/try_arcgis_api.py` — the requested route, and what it actually writes
- `egdb_import/input/egdb_requirements.json` — claimed vs. verifiable client/DBMS requirements
- `egdb_import/input/egdb_connection.example.json` — connection template, deliberately no password field
- `egdb_import/output/nrw_points_schema.json` — the contract: 10 fields with the measurement behind each type
- `egdb_import/output/nrw_points_arcpy_plan.md` — 13 arcpy calls with every argument, plus the row rehearsal
- `egdb_import/output/arcgis_api_attempt.md` — the measurement of the requested route
- `egdb_import/requirements.txt` — pins for `try_arcgis_api.py` only, each pin with its reason

**Result / Iteration**

- **The requested API does not fail, it substitutes.** `DataFrame.spatial.to_featureclass()` was run four times, changing nothing but what was importable: (1) `arcgis` alone raises *"Cannot Export the data without ArcPy, Shapely, or GDAL libraries. Please install one and try again."* (2) With **shapely** installed it raises the **same message** — the code checks `USE_ARCPY`/`USE_PYSHP`/`USE_GDAL` and shapely is not in the list. Following the error message's own instruction does not fix the error. (3) With **pyshp 3.1.6** it writes `.shp`, `.shx` and `.dbf`, then dies inside the library on `DbfWriter.field() got an unexpected keyword argument 'fieldType'`, leaving three broken files behind. (4) With **pyshp 2.3.1** it **succeeds silently and writes a shapefile**, returning its path.
- **What that silent success did to the schema**, against the contract: four of ten field names truncated to the DBF limit of ten characters (`description` → `descriptio`, `visitor_count` → `visitor_co`, `elevation_m` → `elevation_`, `is_enchanted` → `is_enchant`); `TEXT(40)` and `TEXT(120)`, both measured from the data, both replaced by `C(255)`, the format's maximum; every `DOUBLE` written as DBF type `F`. And one inversion worth the whole exercise: `is_enchanted` became DBF type `L`, a **boolean** — the contract had substituted `SHORT` because an Enterprise Geodatabase has no boolean type, so the format that cannot be the target represents that column *better* than the target can. The spatial reference did survive, in the sidecar `.prj`.
- **A correction made mid-task.** The first claim written down was "without arcpy it silently writes a shapefile". That is only true for one of the four environments; with no writer library at all it raises loudly and correctly. The nuance is the finding, and the wrong first reading is kept here rather than deleted.
- **A documentation conflict recorded, not resolved.** Esri's guide says shapefile-only without arcpy; the current API reference documents `ARCGIS_IO_ENGINE` with `'shapefile' | 'gdal' | 'arcpy'` and *"the first available library in the environment will be used"*. Neither says what the GDAL engine can write. After [008], the rule is to quote to the full stop and leave a gap as a gap.
- **Esri's own documentation rots like an open-data portal.** The version-pinned `enterprise.arcgis.com/.../12.1/...` path for the PostgreSQL requirements does not resolve — 12.0 was the highest that did — and several `pro.arcgis.com/.../latest/...` URLs 301-redirect to `doc.esri.com`. So `input/egdb_requirements.json` records each claim with its URL, retrieval date and an explicit **verification status**, and three numbers are marked UNVERIFIED: the Python version in Pro 3.7, the bundled `arcgis` version (inferred from Esri's conda channel metadata, never stated in release notes) and the certified PostgreSQL/PostGIS pairing for 12.1. The importer's preflight asks the machine instead.
- **`--dry-run` earns its place.** Three planted defects each aborted with the right row number: a `description` grown to 130 characters against `TEXT(120)`, an `is_enchanted` set to `maybe`, and a `latitude` written with a German decimal comma. No database was involved in catching any of them.
- **Two refusals that are features.** `nrw_points.csv` carries *both* `latitude`/`longitude` and `x_3857`/`y_3857`, and a feature class has exactly one spatial reference — so `--geometry-from` is mandatory rather than defaulted. And `--wkid 3857` alongside `latitude`/`longitude` columns is an error, not an override.
- **Not finished.** Stages 2 and 3 have **not** been run against a real geodatabase. The arcpy code is written from the tool references and is unproven; `output/verification_report.md` and the ArcGIS Pro screenshot do not exist yet. Next iteration is the Windows VM: the real load, the verifier, the perturbation runs that prove each check fires on its own, and the layer in Pro.

---

## [013] 2026-09-04 — A runbook for the Windows half  ·  scope: `egdb_import`

**Prompt (original, DE)**
> ich brauche noch eine schritt für schritt anleitung, was ich jetzt wohin kopieren soll und was ich ausführen soll

**Prompt (translation, EN)**
> i still need a step by step guide, what i should copy where now and what i should run

**What happened**

- Added a *Running it on the Windows machine* section to `egdb_import/README.md`
  rather than a separate document, so there is one source of truth for the
  commands. Nine steps: get the repository there, confirm the environment,
  confirm the dry run, fill in the connection, load, verify, prove the checks
  fire, open it in ArcGIS Pro, and optionally run the requested API route with
  arcpy present.
- Checked `.gitattributes` before writing step 0, and it changed the
  instruction. It declares `* text=auto eol=lf`, so a **clone** on Windows keeps
  LF newlines and the source CSV keeps the SHA-256 the schema contract records —
  while a hand copy through a share, a zip or an editor is protected by nothing.
  Step 0 therefore says clone, not copy, and gives the `certutil -hashfile`
  command plus the expected digest.
- Wrote step 6 as a table of four perturbations, each with the check it must
  turn red, and told the reader to point `--contract` at a copy in `build/` so
  the committed artifact survives being tampered with.
- Named the likely failures in advance instead of leaving them to be discovered:
  a Basic licence is not enough, the non-default-port syntax is unconfirmed, the
  `.sde` carries the saved password and must stay in `build/`, and the arcpy code
  has never run so a wrong positional argument is the likeliest first error.

**Artifacts**

- `egdb_import/README.md` — new *Running it on the Windows machine* section

**Result / Iteration**

- No code changed; this is the missing half of the instructions rather than a
  new capability.
- The useful part was step 0. "Copy the folder to the VM" was the obvious
  wording and it is wrong: the hash the contract pins is only protected inside a
  git checkout, which is exactly the distinction CLAUDE.md §10 already
  records — `.gitattributes` protects a clone and nothing protects a folder
  someone copied. Verified the expected digest against the file rather than
  transcribing it from the contract.
- Step 1 also asks for a number back: the README states Python 3.13.13 for Pro
  3.7 on the strength of a page that could not be fetched, and the run replaces
  the claim with a measurement.

---

## [014] 2026-09-04 — The runbook was written for the wrong shell  ·  scope: `egdb_import`, root

**Prompt (original, DE)**
> in windows powershell funktioniert bei mir das set propy nicht richtig. er kann das nicht als command ausführen

**Prompt (translation, EN)**
> in windows powershell the set propy does not work properly for me. he cannot execute that as a command

**What happened**

- The runbook from [013] was written in `cmd.exe` syntax and run in PowerShell,
  where none of it works: `set PROPY=...` sets nothing, `%PROPY%` expands to
  nothing, `%PROGRAMFILES%` is not a variable, and `^` is not a line
  continuation. Converted every command in `egdb_import/README.md` to
  PowerShell: `$propy = "$env:ProgramFiles\..."`, backtick continuations, and
  `Get-FileHash` in place of `certutil`.
- The reported symptom - "cannot execute that as a command" - has its own cause
  beyond the assignment syntax. PowerShell treats a string held in a variable as
  *data*, so `$propy args` prints the path rather than running it; the call
  operator `&` is what makes it a command. Documented at the point of use rather
  than as a footnote.
- Added a second route for the same step: ArcGIS Pro's
  `envs\arcgispro-py3\python.exe`, which sidesteps the batch-file argument layer
  when `propy.bat` fights over quoting. `propy.bat` only activates the conda
  environment first, so for a plain arcpy script the two are equivalent.
- Added a `Test-Path $propy` line before anything else, so a wrong install path
  is one `False` rather than a confusing error later.

**Artifacts**

- `egdb_import/README.md` — every Windows command converted to PowerShell, with
  the shell named in the first line of the runbook
- `CLAUDE.md` — §5, the "a shared literal is where two implementations disagree"
  bullet extended with the PowerShell half
- `README.md` (root) — the executables table row for `verify_featureclass.py`

**Result / Iteration**

- My mistake, and an instructive one: `opensearch` shipped `.bat` files, so cmd
  syntax was the habit, and this use case has no `.bat` files at all. Nothing in
  the runbook said which shell it was for, which is exactly why it read as
  plausible and produced three failures for three different reasons - none of
  them the tool's.
- The finding worth keeping is the credential one, because it is the `!`-stripped
  OpenSearch password again with the characters reversed. PowerShell interpolates
  inside **double** quotes, so `$env:EGDB_PASSWORD = "a$bc"` silently loses
  `$bc` and the database answers with an ordinary authentication failure. The
  runbook now uses single quotes and asks the reader to check
  `$env:EGDB_PASSWORD.Length` against what they typed before blaming the server.
- Still not run against a real geodatabase. This iteration removed an obstacle
  to trying, it did not test anything.

---

## [015] 2026-09-04 — A leading `&` is a bad interface  ·  scope: `egdb_import`, root

**Prompt (original, DE)**
> PS C:\data\opensearch_devsummit\egdb_import> $propy = "$env:ProgramFiles\ArcGIS\Pro\bin\Python\Scripts\propy.bat"
> PS C:\data\opensearch_devsummit\egdb_import> Test-Path $propy
> True
> PS C:\data\opensearch_devsummit\egdb_import> $propy -c 'import arcpy, sys; print(sys.version); print(arcpy.ProductInfo()); print(arcpy.GetInstallInfo()["Version"])'
> At line:1 char:8
> + $propy -c 'import arcpy, sys; print(sys.version); print(arcpy.Product ...
> +        ~~
> Unexpected token '-c' in expression or statement.
> [... second identical failure for $py ...]

**Prompt (translation, EN)**
> (A PowerShell transcript: the variable is set, `Test-Path` returns True, and
> invoking it fails with `Unexpected token '-c' in expression or statement` —
> twice, once for `propy.bat` and once for the environment's `python.exe`.)

**What happened**

- Checked the README first rather than answering from the transcript: it does
  carry `& $propy` and `& $py`. The call operator was lost in the copy, which is
  the whole finding.
- Replaced the variable-plus-call-operator pattern with a **function**:
  `function propy { & "...\propy.bat" @args }`. Every subsequent step in the
  runbook is now a bare `propy scripts\...` with no PowerShell-specific
  punctuation at all, and the alternative interpreter is a one-line redefinition
  of the same function rather than a second variable to substitute everywhere.
- Added an out for the inline probe: if `-c` quoting fights, skip it. Step 2 is
  the same check with only a file path, and step 4's preflight prints the
  version, licence level and server versions anyway. The probe was a convenience
  presented as a gate.
- Recorded the rule in `CLAUDE.md` §5.

**Artifacts**

- `egdb_import/README.md` — step 1 rewritten around a function; ten call sites
  simplified
- `CLAUDE.md` — §5, extended
- `README.md` (root) — executables table row

**Result / Iteration**

- The error message is the interesting part. `Unexpected token '-c'` names the
  flag, so it reads as "this tool does not accept `-c`" when the actual cause is
  a missing operator three characters earlier. That is the same shape as the
  findings this repository keeps collecting: the diagnostic points at the wrong
  component. Here it pointed at Python's flag when the parser had never got as
  far as running Python.
- The design lesson is mine, not PowerShell's. I documented `&` in prose
  *underneath* the code block - "The `&` is not decoration" - which is precisely
  where a reader who is copying a command will not look. A command whose
  correctness depends on one easily-lost leading character should not be
  copy-pasted eight times; the character belongs in a definition.
- Still nothing run against a real geodatabase. Two iterations in a row have now
  been spent on the shell rather than on the database.

---

## [016] 2026-09-04 — Two claims become measurements  ·  scope: `egdb_import`

**Prompt (original, DE)**
> mit der function funktioniert es. Version ist: 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 22 2026, 16:49:16) [MSC v.1938 64 bit (AMD64)]
> ArcEditor

**Prompt (translation, EN)**
> with the function it works. Version is: 3.13.13 | packaged by Anaconda, Inc. | (main, Apr 22 2026, 16:49:16) [MSC v.1938 64 bit (AMD64)]
> ArcEditor

**What happened**

- Step 1 of the runbook passed. Recorded both numbers in
  `input/egdb_requirements.json` as `measured_*` fields beside the existing
  `claimed_*` ones, and flipped the Python entry's verification status.
- **Python 3.13.13 for ArcGIS Pro 3.7 is confirmed.** It was recorded as
  UNVERIFIED because Esri's own page returned HTTP 403 and the number came from
  search results alone. Claimed 3.13.13, measured 3.13.13.
- **`ArcEditor` is Standard, and sufficient.** `arcpy.ProductInfo()` reports the
  historical product names, so the check the runbook asks for is meaningful:
  `ArcView` would have meant Basic and would not have been enough for the
  enterprise-geodatabase tools.
- Replaced the runbook's "write down the version it prints" with the actual
  output, and turned the reproducibility section's prose about unverified claims
  into a four-row status table.

**Artifacts**

- `egdb_import/input/egdb_requirements.json` — `python` block rewritten with
  claim *and* measurement; new `licence` block
- `egdb_import/README.md` — step 1 carries the measured output; reproducibility
  section now a claim/status table

**Result / Iteration**

- Two of four version claims are now settled. The `arcgis` package version
  (2.4.3.1, inferred from Esri's conda channel metadata and stated in no release
  note) and the certified PostgreSQL/PostGIS pairing for 12.1 are still
  unmeasured; both are printed by the importer's preflight, so they resolve on
  the first real run.
- The build string turned out worth keeping for a reason unrelated to versions:
  it is **MSVC**, not glibc — the C runtime whose `libm` returned different last
  bits in the `opensearch` fixture. It costs nothing here, and the reason is
  worth stating rather than assuming: this pipeline projects nothing, so the
  doubles from the CSV reach `SHAPE@XY` unchanged, no transcendental function is
  ever called, and there is no last bit to disagree about. The immunity is a
  consequence of the design decision to build the feature class in the CRS the
  source already carries.
- Stages 2 and 3 still not run. Next: the dry run on Windows, then the load.

---

## [017] 2026-09-04 — A second source, and the declaration that beat the measurement  ·  scope: `egdb_import`, root

**Prompt (original, DE)**
> Es hat funktioniert. Ich habe den passenden Screenshot hinzugefügt. Was muss ich tun, um jetzt z.B. aus der synthetischen Airports JSON auch eine FeatureClass zu machen?

**Prompt (translation, EN)**
> It worked. I added the matching screenshot. What do I have to do to now also make a FeatureClass from the synthetic airports JSON, for example?

**What happened**

- Read the screenshot rather than taking "it worked" at face value, and it
  confirmed the load: `agsdb.sde.nrw_points`, points across NRW, all ten
  declared fields in the pop-up, `is_enchanted` showing `0`. It also showed
  that the connection was made as `sde`, so the qualified name is
  `agsdb.sde.nrw_points` and the verifier needs `--database agsdb --schema sde`.
  Recorded both in the runbook.
- The airports FeatureSet could not be analysed at all: two of its eleven
  columns are called `objectid` and `globalid`, which the geodatabase manages
  itself, and `input/` is read-only. Added `--rename OLD=NEW`, repeatable, with
  an unused rename treated as an error rather than a no-op.
- Then found the source **declares its own schema** in a `fields` block - real
  Esri types and real TEXT lengths, because it came out of a geodatabase. Made
  the declaration decide the type, with the measurement recorded beside it and
  `--infer-types` to force the measurement instead. One case is refused rather
  than reported: a declared TEXT length the source's own values exceed.
- Two bugs found, both by the row rehearsal, both fixed.
- Regenerated all five committed artifacts and re-verified byte reproducibility.

**Artifacts**

- `egdb_import/output/synthetic_airports_schema.json` — 11 fields, declared
  types, EPSG:3857
- `egdb_import/output/synthetic_airports_arcpy_plan.md` — 14 calls, 880-row
  rehearsal
- `egdb_import/scripts/schema.py` — `--rename` support, `declared_field()`,
  `is_absent()` made public
- `egdb_import/scripts/sources.py` — the FeatureSet's `fields` block carried out
- `egdb_import/input/csv_to_egdb_pro.png` — the user's ArcGIS Pro capture
- `CLAUDE.md` — four new conventions

**Result / Iteration**

- **The declaration beat the measurement, twice, and that inverts this
  repository's usual rule.** `state_fips` measures as integers and is declared
  `TEXT(2)`; its values include `01` … `09`, so `LONG` would have turned `'01'`
  into `1` and `WHERE state_fips = '01'` would find nothing. `acais` has one
  real value, `Y`, so the boolean heuristic would have fired and collapsed it
  into 1/0. A FIPS code is a *code* - a string that looks like a number - and no
  amount of measuring a column of digits reveals that. Everywhere else in this
  repository the measurement is the thing to trust; here it was wrong and the
  file was right.
- **1,343 values that look empty and are not.** `" "` - a single space - in 825
  rows of `field`, 453 of `type`, 65 of `acais`. The first version treated a
  whitespace-only string as absent and would have written `NULL`, which is a
  silent edit to somebody else's data. Now carried verbatim, counted as
  `whitespace_only_values`, and all three fields correctly `nullable: false`.
- **The mechanism that exposed it is the finding.** The analyser and the loader
  held *two different definitions of empty*, so the rehearsal aborted at row 0
  with "field 'field' is empty but the contract declares it non-nullable" - one
  file, two answers. The predicate is now a single public function imported by
  both. Code that has to **agree** should be shared; code that has to **check**
  must not be. Getting that backwards produces either a bug that passes both
  sides or a conflict at row 0, and this was the second kind, which is the lucky
  one.
- **Two things still open, both worth naming.** `verify_featureclass.py` has not
  been run - the layer draws, which is exactly what check 4 exists to prove is
  not enough. And the screenshot's basemap attribution is **collapsed**: ArcGIS
  Pro hides the provider notice behind a small control in the map frame's
  bottom-right corner, so a capture of the entire application window contains no
  notice at all without anything having been cropped. For a published image that
  is the same as cropping it, and the World Topographic Map includes
  OpenStreetMap, whose ODbL makes attribution the condition for redistributing a
  map image. Needs one click and a re-capture.
- The screenshot also settled a question nobody asked: the pop-up shows
  `objectid 65` above the CSV's own `id 65`. They agree, which is worse than the
  `opensearch` case where the equivalent pair matched in zero rows - an accidental
  agreement invites the join that will break the first time a row is deleted.

---

## [018] 2026-09-04 — A qualified name I built instead of looking up  ·  scope: `egdb_import`, root

**Prompt (original, DE)**
> Screenshot aktualisiert. Verify läuft nicht: PS C:\data\opensearch_devsummit\egdb_import> propy scripts\verify_featureclass.py --contract output\nrw_points_schema.json --sde build\egdb.sde --database agsdb --report output\verification_report.md
> [... Traceback ...]
> arcgisscripting.ExecuteError: Failed to execute. Parameters are not valid.
> ERROR 000732: Input Rows: Dataset build\egdb.sde\agsdb.agsdb.nrw_points does not exist or is not supported
> Failed to execute (GetCount).

**Prompt (translation, EN)**
> Screenshot updated. Verify does not run: [PowerShell transcript of
> `verify_featureclass.py`, failing with `ERROR 000732: Input Rows: Dataset
> build\egdb.sde\agsdb.agsdb.nrw_points does not exist or is not supported`.]

**What happened**

- The path in the error is the bug: `agsdb.agsdb.nrw_points` against a real
  `agsdb.sde.nrw_points`. My verifier defaulted the schema to the database name
  when `--schema` was not given, so it *constructed* a qualified name rather
  than finding one.
- Replaced the construction with a lookup: `resolve_feature_class()` enumerates
  the workspace with `arcpy.ListFeatureClasses()` and matches on the unqualified
  name, prints what it resolved to, and keeps `--database`/`--schema` as filters
  for the one case a human must decide - the same table name in two schemas. A
  miss now lists what the connection actually contains.
- `--database` and `--schema` are no longer required, so the command is three
  flags shorter and has nothing left to guess wrong.
- Checked the updated screenshot rather than taking it on trust, and found the
  attribution - in the **Service Layer Credits** panel, not at the map's bottom
  edge where I had told the user to look. Corrected the instruction, and
  recorded the notice as text in the README as well, because an image can be
  resized or replaced and the obligation cannot.

**Artifacts**

- `egdb_import/scripts/verify_featureclass.py` — `resolve_feature_class()`,
  `_list_feature_classes()`, both positional flags made optional
- `egdb_import/input/csv_to_egdb_pro.png` — re-captured with the credits panel open
- `egdb_import/README.md` — verify command simplified, the error documented,
  step 7 corrected
- `CLAUDE.md` — two rules

**Result / Iteration**

- **The error message named the wrong component, again.** `ERROR 000732: Input
  Rows: Dataset ... does not exist or is not supported` points at the *dataset*,
  so it reads as "the load failed" or "this feature class type is unsupported".
  The load was fine; the checker had invented a path. This is the third time in
  this use case that the diagnostic has pointed one layer away from the cause -
  after `Unexpected token '-c'` naming Python's flag for a missing PowerShell
  operator, and `to_featureclass` returning a success for a shapefile.
- **The rule: do not construct a qualified name you can look up.** The schema in
  `database.schema.table` belongs to the connecting login and is not derivable
  from anything the script is told. A default that is wrong half the time is
  worse than a required flag, and a lookup is better than both.
- **The attribution was there, and my instruction was not.** ArcGIS Pro does not
  burn the basemap notice into the map; it keeps it in a dockable panel that is
  closed by default. I had written "expand the control in the bottom-right of the
  map frame", looked for it at the bottom edge of the first capture, and
  concluded it was absent - correct conclusion, wrong reason. The notice reads
  *"Sources: Esri, TomTom, Garmin, FAO, NOAA, USGS, © OpenStreetMap
  contributors, and the GIS User Community, Esri, USGS"*, which also confirms
  the guess that the Esri basemap carries OSM data and that ODbL Produced-Work
  attribution is what is being satisfied.
- Still no verification report: the fix is untested, like the rest of the arcpy
  code. Next run either produces eight results or a fourth misdirecting error.

---

## [019] 2026-09-04 — Both sources loaded, and a claim of mine refuted by its own check  ·  scope: `egdb_import`, root

**Prompt (original, DE)**
> Airports waren auch erfolgreich. Screenshot ergänzt. Commit fertig machen

**Prompt (translation, EN)**
> Airports were also successful. Screenshot added. Finish the commit

**What happened**

- Read what had actually landed rather than taking "successful" at face value:
  `output/verification_report.md` had appeared (10 of 10 green for `nrw_points`)
  and a second capture, `input/egdb_airports.png`, showing
  `agsdb.sde.synthetic_airports` with 880 features and the credits panel open.
- **One number in that report refutes something this repository asserted.**
  Check 7 was written as an exact comparison, on the reasoning that nothing in
  the pipeline projects, converts or rounds - the double parsed from the CSV is
  the double handed to `SHAPE@XY`. Measured: the worst disagreement on read-back
  is **8.53e-14 degrees, about 9.5 nanometres**, roughly 12 ULP of the stored
  latitude; the extent check shows 6.1 nm. Corrected the claim in the README,
  both script docstrings and `CLAUDE.md`, and kept the wrong reading visible
  rather than deleting it.
- Added the finding as backup slide 29. The first render **overflowed the bottom
  edge and cut off the punchline** - the exact defect CLAUDE.md §8 says to look
  for by rendering to PNG, found by rendering to PNG. Trimmed and re-checked.
- Marked the use case done in the root README, wrote the progress-log entry, and
  prepared the commits.

**Artifacts**

- `egdb_import/output/verification_report.md` — 10 of 10, from the real geodatabase
- `egdb_import/input/egdb_airports.png` — the second capture
- `egdb_import/README.md` — status table, the corrected check-7 section, the
  three findings visible in the airports pop-up
- `slides/pages/90-appendix.md` — backup slide 29
- `CLAUDE.md` — the round-trip rule

**Result / Iteration**

- **A geodatabase round trip is not the identity, even when no code touches the
  value.** Which mechanism is responsible was not established: a geodatabase
  quantises geometry to the coordinate grid its spatial reference defines, and
  arcpy converts between the stored form and a Python tuple, and either could
  account for 12 ULP. Saying "not measured which" is cheaper than picking one.
  Two consequences: the tolerance that looked like decoration was load-bearing,
  and it must **not** be tightened to the measured value - the rounding-margin
  mistake from §10 in a new costume.
- **The symmetry is the talk material.** `opensearch`: 1.9 nm, because libm is
  not standardised to the last bit. `egdb_import`: 9.5 nm, because a database
  stored a number. Same units, unrelated causes, no arithmetic in either, both
  fatal to an exact-equality check.
- **The airports pop-up carries three findings in one feature.** `objectid 282`
  beside `source_objectid 305` - they disagree, which is the *safe* version,
  against `nrw_points` where `objectid 65` and the CSV's own `id 65` agree by
  accident and will diverge on the first delete. `state_fips 08`, leading zero
  intact, which is the declaration-beats-measurement finding in one cell.
  And a `field` cell that renders empty while holding a single space.
- **Still open, and stated in the README rather than quietly dropped:** the
  airports feature class has not been verified (it loaded and it draws, which is
  what check 4 exists to show is not enough), and the perturbation runs that
  prove each check goes red have not been done. Ten green checks are worth less
  than one check proven to fail.

