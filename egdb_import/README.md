# EGDB Import — generated data into an Enterprise Geodatabase

Turning a CSV or JSON into a real **FeatureClass in a PostgreSQL Enterprise
Geodatabase**, consumed afterwards in ArcGIS Pro 3.7 / ArcGIS Enterprise 12.1.
Part of [Test (Geo-)Data Generation with GenAI](../README.md).

The other use cases stop at a file or at a search index. This one closes the
loop to the system the audience actually works in, and it is the everyday task:
somebody hands you data and it has to become a feature class — schema and all —
without clicking through a wizard.

## The finding: the requested API cannot do this

The use case was asked for "using the ArcGIS API for Python". It cannot be done
that way, and *how* it cannot is the point.

The `arcgis` package is a REST client for a portal. It has no database
connectivity at all — no SDE connection object, no equivalent of `arcpy.da`.
The two routes its own documentation shows both **fail by succeeding**:

| Route | What it returns | Why that is wrong |
|---|---|---|
| `GIS.content.import_data()` | a working feature layer | *hosted*, in the ArcGIS Data Store. The rows are copied **out** of the customer's database — the opposite of the goal, with no signal that it happened. |
| `DataFrame.spatial.to_featureclass()` | a path | a **shapefile**, if arcpy is not in the interpreter. Same call, same arguments, different format, no error. |

Esri's guide says it plainly:

> Writing to file geodatabases requires the ArcPy site-package.

So the work is arcpy's, which means Windows and a licensed ArcGIS Pro. That is
the headline rather than a footnote — and it is the `opensearch` lesson
sharpened: **the loud error is the harmless one.**

`try_arcgis_api.py` measures this rather than asserting it, and the measurement
turned out richer than expected. Four distinct outcomes from one unchanged line
of code, depending only on what was importable:

| Environment | Outcome |
|---|---|
| `arcgis` alone | raises: *"Cannot Export the data without ArcPy, Shapely, or GDAL libraries. Please install one and try again."* |
| `arcgis` + **shapely** | raises the **same** message. The message names shapely; the code checks `USE_ARCPY`/`USE_PYSHP`/`USE_GDAL`. Following the error's own instruction does not fix the error. |
| `arcgis` + **pyshp 3.1.6** | writes `.shp`, `.shx`, `.dbf`, then dies inside pyshp on `DbfWriter.field() got an unexpected keyword argument 'fieldType'` — leaving three broken files behind. |
| `arcgis` + **pyshp 2.3.1** | **succeeds silently and writes a shapefile.** |

And the schema that silent success produced, against the schema the contract
asked for — see [`output/arcgis_api_attempt.md`](output/arcgis_api_attempt.md):

- **Four of ten field names were truncated to ten characters** by the DBF
  header limit. `description` → `descriptio`, `visitor_count` → `visitor_co`,
  `elevation_m` → `elevation_`, `is_enchanted` → `is_enchant`. Nothing reports
  it, and a downstream query on the original name finds no column.
- `TEXT(40)` and `TEXT(120)`, both measured from the data, both became
  `C(255)` — the format's maximum. The measurement was discarded, not used.
- Every `DOUBLE` became DBF type `F` (float), because a shapefile has no
  double.
- `is_enchanted` became DBF type `L` — a **boolean**. The contract had
  substituted `SHORT` because an Enterprise Geodatabase has no boolean type. The
  format that cannot be the target represents that column better than the target
  can.
- The spatial reference *did* survive, in the sidecar `.prj`. The substitution
  damaged the schema, not the projection.

`to_featureclass` accepts `location, overwrite, has_z, has_m,
sanitize_columns` — no field type, no length, no alias — and Esri publishes no
dtype mapping table. For an importer whose deliverable **is** the schema, that
is disqualifying. Hence explicit `CreateFeatureclass` + `AddField`, where every
type and length is stated by the caller.

### One documentation conflict, recorded and not resolved

The guide says shapefile-only without arcpy. The current API reference documents
`ARCGIS_IO_ENGINE` with options `'shapefile'`, `'gdal'`, `'arcpy'` and says *"the
first available library in the environment will be used"*. Neither page says
what the GDAL engine can write. Recorded as an open conflict — CLAUDE.md §4,
quote the whole sentence and do not turn a gap into a claim in either direction.

## Stack

**Python 3.12 stdlib for stage 1; arcpy for stages 2 and 3.**

This is the one use case in the repository that **cannot** isolate its
dependencies. arcpy is not installable from PyPI; it exists only inside ArcGIS
Pro's bundled `arcgispro-py3` conda environment, invoked through `propy.bat`. So
there is no `.venv` for the importer — the environment *is* the licence.

Stage 1 is deliberately stdlib-only so the analysis half is not held hostage to
that. `requirements.txt` exists for one script only: `try_arcgis_api.py`, the
demonstration of the route that does not work.

## Pipeline

Three stages, separated because only the middle one needs Windows:

```
source file            schema contract               feature class
CSV / JSON      ──▶    output/*_schema.json     ──▶   EGDB (PostgreSQL)
 analyze_source.py         reviewable, editable       import_to_egdb.py
   stdlib, anywhere                                   verify_featureclass.py
                                                        arcpy, Windows
```

The **schema contract** is the universal interface. Any other script — a jq
one-liner, a hand edit, a different generator — can produce one, and the loader
neither knows nor cares where the data came from. It is also what makes the
arcpy half reviewable *before* it touches a database.

## Input

`input/` — read-only. Nothing here is data; the data comes from another use case.

| File | Description |
|---|---|
| `egdb_connection.example.json` | Connection template with placeholders. **No password field** — see [Credentials](#credentials). |
| `egdb_requirements.json` | What the client certifies for PostgreSQL/PostGIS, and separately what could actually be verified from a fetchable page. Every claim carries its URL, retrieval date and verification status. |
| `csv_to_egdb_pro.png` | ArcGIS Pro 3.7 showing `agsdb.sde.nrw_points` from the PostgreSQL geodatabase, with the pop-up of one feature. Made by hand, so it belongs in `input/` and not `output/` (CLAUDE.md §3). |
| `egdb_airports.png` | The same, for `agsdb.sde.synthetic_airports` — 880 features from the Esri JSON FeatureSet. Its pop-up shows three findings at once; see [Status](#status-2026-09-04). |

Source data: [`../csv_data/output/nrw_points.csv`](../csv_data/output/nrw_points.csv)
— the 100 points written directly by the LLM in `csv_data`. Chosen because it is
small enough to load live on stage and because it carries **both** coordinate
pairs, which forces a decision the tool must not make silently.

## Output

`output/` — generated, committed, reproducible from `input/` plus the commands
below. Safe to delete entirely.

| File | Description |
|---|---|
| `nrw_points_schema.json` | The schema contract: 10 fields with their Esri types, lengths and the measurement each was chosen from. |
| `nrw_points_arcpy_plan.md` | Every arcpy call a real run makes, with all arguments, produced **without importing arcpy**. Plus the rehearsal result. |
| `synthetic_airports_schema.json` | The second contract: 11 fields, types and lengths taken from the source's own `fields` block, geometry in EPSG:3857. |
| `synthetic_airports_arcpy_plan.md` | 14 arcpy calls for the second source, plus the 880-row rehearsal. |
| `verification_report.md` | The eight checks plus two INFO rows against the loaded `nrw_points`. All green. |
| `arcgis_api_attempt.md` | What the ArcGIS API for Python actually wrote, and what the schema lost on the way. |

`build/` is gitignored and holds the `.sde` connection file and whatever
`try_arcgis_api.py` writes. The `.sde` **carries saved credentials** and must
never be committed — see below.

## Setup

Stage 1 needs nothing:

```bash
cd egdb_import
python3 --version   # 3.10 or newer
```

For `try_arcgis_api.py` — the failing-route demonstration — a local venv:

```bash
cd egdb_import
python3 -m venv build/venv_api
build/venv_api/bin/pip install -r requirements.txt
```

For stages 2 and 3, ArcGIS Pro's own Python on the Windows machine. No install,
no venv:

```powershell
& "$env:ProgramFiles\ArcGIS\Pro\bin\Python\Scripts\propy.bat" -c "import arcpy; print(arcpy.ProductInfo())"
```

## Usage

### 1. Measure the source and write the contract

```bash
cd egdb_import
python3 scripts/analyze_source.py \
    --input ../csv_data/output/nrw_points.csv \
    --geometry-from latlon \
    --feature-class nrw_points \
    --generated-date 2026-09-04 \
    --output output/nrw_points_schema.json
```

`--geometry-from` is **required** for this file, and the refusal is deliberate:

```
error: the source carries two coordinate pairs - latitude/longitude and
x_3857/y_3857 - and a feature class has exactly one spatial reference. Pass
--geometry-from latlon or --geometry-from xy. Picking one silently would be a
coin flip whose result looks correct either way.
```

The pair not chosen stays in the field list as ordinary numbers. Redundant for
drawing, which is exactly why they are kept: they are what the verifier compares
the stored geometry against.

### 2. Rehearse, then build

```bash
python3 scripts/import_to_egdb.py --dry-run \
    --contract output/nrw_points_schema.json \
    --connection input/egdb_connection.example.json \
    --plan output/nrw_points_arcpy_plan.md
```

`--dry-run` imports no arcpy and touches no database, but it is a check rather
than a printout: **every row is coerced to its declared field type**. Proven to
fire, on three perturbed copies of the source:

| Perturbation | Result |
|---|---|
| one `description` grown to 130 characters | `row 42: field 'description' holds 130 characters but the contract declares TEXT(120)` |
| one `is_enchanted` set to `maybe` | `row 7: ... was measured as a boolean column and holds 'maybe', which is neither true nor false` |
| one `latitude` written with a German decimal comma | `row 3: coordinate columns longitude/latitude do not both hold a number` |

The real run, on the Windows machine:

```powershell
function propy { & "$env:ProgramFiles\ArcGIS\Pro\bin\Python\Scripts\propy.bat" @args }
$env:EGDB_PASSWORD = 'the data owner''s password'   # single quotes: see the runbook

propy scripts\import_to_egdb.py `
    --contract output\nrw_points_schema.json `
    --instance 127.0.0.1 --database devsummit --username devsummit `
    --overwrite
```

### 3. Verify

```powershell
propy scripts\verify_featureclass.py `
    --contract output\nrw_points_schema.json `
    --sde build\egdb.sde `
    --report output\verification_report.md
```

`--report` has no default on purpose: a verifier whose output path is convenient
is a verifier that overwrites the wrong report (CLAUDE.md §4).

### A second source: the airports FeatureSet

The same pipeline, a different shape of file, to show the source is
interchangeable. `opensearch/input/synthetic_airports.json` is an Esri JSON
FeatureSet: 880 point features, geometry as `{"x": …, "y": …}` in **EPSG:3857
metres**, and a `fields` block declaring its own schema.

```bash
cd egdb_import
python3 scripts/analyze_source.py \
    --input ../opensearch/input/synthetic_airports.json \
    --rename objectid=source_objectid \
    --rename globalid=source_globalid \
    --rename ESRI_OID=source_esri_oid \
    --rename type=airport_type \
    --feature-class synthetic_airports \
    --generated-date 2026-09-04 \
    --output output/synthetic_airports_schema.json

python3 scripts/import_to_egdb.py --dry-run \
    --contract output/synthetic_airports_schema.json \
    --plan output/synthetic_airports_arcpy_plan.md
```

Then on Windows, the same two commands as the CSV with the other contract. Note
that the geodatabase used here already contains a feature class called
`airports` — hence `synthetic_airports`, which is also the honest name.

**`--rename` is not a convenience, it is the only way in.** Two of the eleven
columns are called `objectid` and `globalid`, which the geodatabase manages
itself, and `input/` is read-only so the source cannot be edited. Without the
flag the analyser refuses and says what to pass:

```
error: column 'objectid' sanitises to 'objectid', which the geodatabase manages
itself. Pass --rename objectid=source_objectid - a source object id belongs in a
prefixed column so the attribute table stops inviting a join on it (CLAUDE.md
section 4). The rename happens here rather than in the source, because input/ is
read-only.
```

A rename naming a column that does not exist is an error rather than a no-op — a
mistyped rename that silently does nothing is worse than one that fails.

#### The declaration beats the measurement, and this is where it matters

A FeatureSet exported from a geodatabase carries its own schema, so the types
and lengths come from the file rather than from inference: `locid` is `TEXT(5)`,
`name` `TEXT(45)`, `state_fips` `TEXT(2)`, `acais` `TEXT(1)`. The measurement is
still taken and recorded beside the declaration, and it produced the finding:

| Field | Measured | Declared | Consequence |
|---|---|---|---|
| `state_fips` | `LONG` | `TEXT(2)` | The values include `01` … `09`. Inference would have made it `LONG`, turning `'01'` into `1` — after which `WHERE state_fips = '01'` finds nothing. |
| `acais` | would have been `SHORT` | `TEXT(1)` | Its only real value is `Y`, so the boolean heuristic would have fired and collapsed `Y` and the 65 blanks into 1/0. |

This inverts the rule the rest of the repository runs on. Everywhere else the
measurement is the thing to trust and the declaration is the thing to check;
here the declaration was right twice and measuring alone would have destroyed a
leading zero. The reason is that a FIPS code is a *code* — a string that looks
like a number — and no amount of measuring a column of digits reveals that.
`--infer-types` forces the measurement anyway, and the contract records which
route was taken.

One conflict is refused rather than reported: a declared TEXT length that the
source's own values exceed. Left alone it fails at insert time, hundreds of rows
in, so it aborts during analysis instead.

#### And a blank that is not blank

825 of 880 rows store `" "` — a single space — in `field`, 453 in `type`, 65 in
`acais`. **1,343 values that look empty and are not.** The first version of this
code treated a whitespace-only string as absent and would have written `NULL`,
which is a silent edit to somebody else's data (CLAUDE.md §4). They are now
carried through verbatim, counted in the contract as `whitespace_only_values`,
and every one of those three fields is correctly `nullable: false` — because no
row is actually null.

That bug was found by the `--dry-run` rehearsal, and by a specific mechanism
worth recording: the analyser and the loader had *two different definitions of
empty*, so the rehearsal aborted at row 0 with `field 'field' is empty but the
contract declares it non-nullable`. The predicate is now a single public
function, `schema.is_absent`, imported by both. This is the same reasoning as
the shared readers in `sources.py` and the opposite of the projection formulas
elsewhere: code that has to **agree** should be shared, code that has to
**check** must not be.

### The route that does not work

```bash
build/venv_api/bin/python scripts/try_arcgis_api.py \
    --report output/arcgis_api_attempt.md
```

## Running it on the Windows machine

Stages 2 and 3 have never been executed. This is the sequence, in order, with
the checks that make a failure legible instead of mysterious.

### 0. Get the repository there — clone it, do not copy it

```powershell
cd C:\work
git clone <repository-url> devsummit
cd devsummit\egdb_import
```

**Clone rather than copy, and the reason is in `.gitattributes`.** It declares
`* text=auto eol=lf`, so a checkout on Windows keeps LF newlines and the source
CSV keeps the SHA-256 the schema contract records. A hand copy through a share,
a zip or an editor is not protected by anything, and a rewritten newline changes
the hash without changing a value. Check it:

```powershell
(Get-FileHash ..\csv_data\output\nrw_points.csv -Algorithm SHA256).Hash.ToLower()
```

Expected: `d84a1b608652e57dca8807ed2b402ccb59ec4e63ec553a9ed10379db7c9e2bc5`
— the value in `output/nrw_points_schema.json` under `source.sha256`. If it
differs, the newlines were rewritten; nothing in the pipeline will *break*, but
the contract no longer describes the file it claims to.

The whole repository is needed, not just this folder: the contract points at
`../csv_data/output/nrw_points.csv`.

### 1. Confirm the environment

**These commands are PowerShell**, and every one of them below starts with
`propy`. In `cmd.exe` none of this works — variables, quoting and line
continuation share no syntax between the two shells.

`propy.bat` is ArcGIS Pro's own Python. Define it once as a **function**, so
nothing after this point needs PowerShell-specific punctuation:

```powershell
function propy { & "$env:ProgramFiles\ArcGIS\Pro\bin\Python\Scripts\propy.bat" @args }

propy -c "import arcpy, sys; print(sys.version); print(arcpy.ProductInfo())"
```

Adjust the path inside the function if Pro is not in the default location;
`Test-Path` it first if unsure.

**Why a function and not a variable.** The obvious form is
`$propy = "...\propy.bat"` followed by `$propy -c '...'`, and it does not work:
PowerShell treats a string held in a variable as *data*, not as a command, so it
parses the line as an expression and stops at the first flag —
`Unexpected token '-c' in expression or statement`. The fix is the call operator,
`& $propy -c '...'`, and that is a single leading character that looks like
decoration and is the easiest thing in the world to drop while copying. Putting
it inside a function once removes the trap from every later step instead of
repeating it eight times. `@args` forwards whatever it is given.

**If the inline `-c` fights you over quoting**, do not fix the quoting — skip
the probe. Step 2 is the same check with no inline code at all, only a file
path, and step 4's preflight prints the version, the licence level and the
server versions anyway. The probe is a convenience, not a gate.

There is also a second interpreter, if `propy.bat` itself misbehaves:

```powershell
function propy { & "$env:ProgramFiles\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" @args }
```

`propy.bat` activates the `arcgispro-py3` conda environment before running
Python; for a plain arcpy script the environment's own `python.exe` is normally
equivalent. Redefine the function and everything below keeps working unchanged.

Three things have to be true: the import succeeds, `ProductInfo()` reports
`ArcInfo` or `ArcEditor` — Advanced or Standard; **Basic is not enough** for the
enterprise-geodatabase tools — and the version is 3.7.

**Measured on the target machine, 2026-09-04:**

```
3.13.13 | packaged by Anaconda, Inc. | (main, Apr 22 2026, 16:49:16) [MSC v.1938 64 bit (AMD64)]
ArcEditor
```

The Python version was recorded as UNVERIFIED in
`input/egdb_requirements.json`, because Esri's own page returned HTTP 403 and
the number came from search results only. Claimed 3.13.13, measured 3.13.13 —
**confirmed**. `ArcEditor` is Standard, which is sufficient; `arcpy.ProductInfo()`
reports the historical names, so `ArcView` would have meant Basic and would not
have been.

The build string is worth keeping for one reason: this is **MSVC**, not glibc —
the C runtime whose `libm` returned different last bits in the `opensearch`
fixture (CLAUDE.md §10). It costs nothing here, because this pipeline projects
nothing. The doubles in the CSV go to `SHAPE@XY` unchanged, so no transcendental
function is ever called and there is no last bit to disagree about.

The `arcgis` package version is still unmeasured — it was only ever *inferred*
from Esri's conda channel metadata and appears in no release note. Step 4's
preflight prints it, so it resolves on the first real run.

### 2. Confirm the dry run works there too

Before touching the database, on Windows, with Windows paths:

```powershell
propy scripts\import_to_egdb.py --dry-run --plan build\plan_windows.md
```

It should end with `100 rows coerced to their declared types, no error`. This
imports no arcpy and needs no password, so a failure here is a path or encoding
problem and nothing more. Write to `build\`, not `output\`, so the committed
artifact is not overwritten by a run whose purpose was only to check paths.

### 3. Fill in the connection

You need three values from the existing geodatabase: the **instance**, the
**database name** (lowercase), and the **login** that should own the feature
class.

Esri's own advice is to keep user data out of the `sde` schema, which owns the
geodatabase's system tables. On the machine this was run against, the connection
was made as `sde` anyway and the result is `agsdb.sde.nrw_points` — it works, and
it is worth knowing that the qualified name follows the *connecting* login's
schema, because the verifier needs it:

```powershell
propy scripts\verify_featureclass.py --database agsdb --schema sde ...
```

If the login's schema name differs from the login name, pass `--schema`
explicitly. The examples below say `devsummit`; substitute what your geodatabase
actually reports in the Catalog pane.

### 4. Load

```powershell
$env:EGDB_PASSWORD = 'the data owner''s password'

propy scripts\import_to_egdb.py `
    --contract output\nrw_points_schema.json `
    --instance 127.0.0.1 `
    --database devsummit `
    --username devsummit `
    --overwrite
```

**Single quotes around the password, deliberately.** PowerShell interpolates
inside double quotes, so a password containing `$` or a backtick is silently
rewritten before it ever reaches the database — and the failure surfaces as a
plain authentication error with nothing in the log to explain it. Single quotes
pass the string through literally; a literal single quote inside it is doubled,
as above. This is the same class of failure as the `!` that `cmd.exe` stripped
out of the OpenSearch password (CLAUDE.md §5): the shell in the middle rewrote a
credential and every layer downstream reported the truth it was given.

Verify it arrived intact before blaming the database:

```powershell
$env:EGDB_PASSWORD.Length      # compare against what you typed
```

Substitute your values for `devsummit`. What the run prints first is the
preflight: the product version, the licence level, the Python version, the
`arcgis` package version, and the PostgreSQL and PostGIS/ST_Geometry versions
read **off the server**. Keep that output — it is what
`input/egdb_requirements.json` marks as UNVERIFIED, and this is the machine
answering.

Then it creates `build\egdb.sde`, creates the feature class in EPSG:4326, adds
ten fields, inserts 100 rows, and ends with a count it checks against the
source.

Notes on what may bite:

- **`build\egdb.sde` carries the saved password.** It is gitignored. Do not move
  it out of `build\`.
- **A non-default PostgreSQL port.** Esri's documented syntax for this could not
  be confirmed on a version-specific page. Try `--instance 127.0.0.1,5433` and
  check the result rather than assuming it worked.
- **This code has never run.** If it raises, send the traceback — the arcpy call
  signatures are transcribed from the tool references and a wrong positional
  argument is the likely first failure.

### 5. Verify

```powershell
propy scripts\verify_featureclass.py `
    --contract output\nrw_points_schema.json `
    --sde build\egdb.sde `
    --report output\verification_report.md
```

Eight checks and two informational rows, and a non-zero exit if any fails.

**No `--database` or `--schema`, on purpose.** An enterprise geodatabase
addresses objects as `database.schema.table`, and the schema is the *connecting
login's* — not derivable from anything passed on the command line. The first
version of this script defaulted it to the database name and produced:

```
ERROR 000732: Input Rows: Dataset build\egdb.sde\agsdb.agsdb.nrw_points
does not exist or is not supported
```

against a real `agsdb.sde.nrw_points`. The message names the dataset, so it
reads as "the load failed", when the fault was in the path this script built.
It now looks the feature class up in the connection and prints what it resolved
to. `--database` and `--schema` remain as filters for the one case a human has
to decide — the same table name in two schemas — and a miss lists what the
connection actually contains instead of only what was missing.

### 6. Prove the checks actually fire

A verifier that has never gone red has not been verified. Four runs, each
changing one thing, each expected to turn exactly one check red while the others
stay green:

| Change | Expected to fail |
|---|---|
| edit one row's `latitude` in a **copy** of the CSV, moving the point 40 km, and verify against that copy | 5 (extent) and 7 (geometry vs. source) |
| re-run the load from a contract whose `geometry.x_column` and `y_column` are swapped | 6 (transposed box) |
| re-run the load from a contract with `spatial_reference.wkid` set to 3857 | 4 (spatial reference), 5 (extent) |
| edit one contract field's `length` from 120 to 100 and verify | 2 (field types and lengths) |

Copy the contract to `build\` first and point `--contract` at the copy, so the
committed artifact stays as it was.

### 7. Open it in ArcGIS Pro

New project → Catalog pane → **Databases** → *Add Database* → point at
`egdb_import\build\egdb.sde` → drag `nrw_points` onto a map.

Before capturing, open **Map → Service Layer Credits** (a dockable panel, not a
control at the edge of the map frame). ArcGIS Pro does **not** burn the basemap
attribution into the map, so a capture of the whole application window can
contain no provider notice at all without anything having been cropped — which
for a published image is the same as cropping it. The notice for the World
Topographic Map names OpenStreetMap contributors, and the ODbL makes attribution
the condition for redistributing a map image.

Then screenshot it and save as `egdb_import/input/csv_to_egdb_pro.png`. It
belongs in `input/` and not `output/`, because it is made by hand and cannot be
regenerated from the documented command (CLAUDE.md §3).

### 8. Optional — the requested route, this time with arcpy

The four measurements in this README were all taken without arcpy. The fifth is
the interesting one, and only this machine can take it:

```powershell
propy scripts\try_arcgis_api.py `
    --location build\egdb.sde\devsummit.devsummit.nrw_points_api `
    --report build\arcgis_api_windows.md
```

With arcpy present, `to_featureclass()` should write into the geodatabase for
real. The question worth answering is what schema it produces there — whether
the ten-character truncation and the `C(255)` lengths were the shapefile's fault
or the API's. Write to `build\` so the committed report keeps the arcpy-free
measurement.

### What to send back

- the console output of steps 1, 4 and 5 (the preflight block especially)
- `output/verification_report.md`
- `egdb_import/input/csv_to_egdb_pro.png`
- any traceback, verbatim

## Example output

The contract, abbreviated — every field carries the measurement its type was
chosen from:

```json
{
  "spatial_reference": {
    "wkid": 4326,
    "decided_by": "column names latitude/longitude: a geographic pair is decimal degrees, EPSG:4326. Note that 'decimal degrees' and 'EPSG:3857' are mutually exclusive - EPSG:3857 is metres."
  },
  "fields": [
    {
      "name": "is_enchanted", "source": "is_enchanted", "type": "SHORT",
      "nullable": false,
      "evidence": {
        "rows": 100, "nulls": 0, "distinct": 2,
        "reason": "every value is a boolean literal",
        "boolean_as_short": true,
        "note": "An Enterprise Geodatabase has no boolean type. Stored as SHORT with 1/0; the attribute table shows a number and cannot show that it was a boolean."
      }
    }
  ]
}
```

## Verification

Depth agreed up front at **"plausible is enough"** (CLAUDE.md §12): this is
generated test data destined for a database, not a published claim about the
world, so it does not adjudicate individual records the way `open_data_search`
does. What it still insists on is the cheap part that catches silent failures.

`verify_featureclass.py` reads the feature class back through
`arcpy.da.SearchCursor` and runs eight checks plus two informational rows:

1. Feature count matches the source.
2. Every contract field exists with the declared type and length.
3. No unexpected field beyond the geodatabase's own `objectid`/`shape`.
4. The spatial reference is the EPSG code the contract names.
5. The extent equals the source's own measured extent.
6. The **transposed** bounding box matches nothing.
7. **Every** geometry equals its source coordinate pair — not a sample.
8. The second coordinate pair survived as attributes, unmodified.

Two of these deserve the space they take:

**Check 4 exists because a wrong spatial reference does not error.** Create the
feature class as EPSG:3857 and feed it degrees: the numbers go in, the
geodatabase is content, the layer draws — and every one of the hundred points
sits **within 52 metres of 0°N 0°E**, in the Gulf of Guinea, because a longitude
of 7.46 read as 7.46 metres is 0.000067°. Nothing but a bounding box notices.

**Check 6 does real work on this data set, and that is not luck this time.** NRW
is latitude 50–52 and longitude 5–9, so *both* values are valid latitudes. A
swapped load is accepted by the geodatabase without a murmur and lands the
points around 7.5°N 51.3°E, in the Somali Sea. Contrast `opensearch`, where
swapping the airports
got 550 of 880 documents rejected outright by the engine — nothing in the code
differed, the geometry did.

**Check 7 needed a correction, and it is the most interesting number in the
folder.** Nothing in this pipeline projects, converts or rounds a coordinate:
the double read from the CSV is the double handed to `SHAPE@XY`. So the
comparison was written as if it should hold bit for bit, and the README said so.

It does not. Measured against the real geodatabase, the worst disagreement
across 100 features is **8.53e-14 degrees — about 9.5 nanometres**, roughly 12
ULP of the stored latitude. The extent check shows the same order of magnitude
at 6.1 nm. **A geodatabase round trip is not the identity**, even when nothing
in your own code touches the value.

Which mechanism is responsible is not established here, and both candidates are
plausible: a geodatabase quantises geometry to the coordinate grid its spatial
reference defines, and arcpy converts between the stored representation and a
Python tuple. Saying "I have not measured which" is cheaper than picking one.

Two consequences worth keeping:

- **The tolerance was doing real work.** At 1e-9 degrees (~0.1 mm) it is four
  orders of magnitude above what was measured and four below the 1.1 m that five
  decimal degrees resolves. Without it, this check would fail on correct data.
- **Do not tighten it to the measurement.** That is the same mistake as
  calibrating a rounding margin to one artifact (CLAUDE.md §10): 9.5 nm on this
  spatial reference and this release is not a promise about the next one.

The pleasing symmetry: `opensearch` found a **1.9 nm** divergence from libm not
being standardised to the last bit. This is **9.5 nm** from a database storing a
number. Both invisible, both nanometre-scale, both fatal to an exact-equality
check — and in neither case did any code do arithmetic on the value.

The narrower claim survives intact: nothing was recomputed *on the way in*, and
that is available only because the contract insisted the feature class be
created in the CRS the source already carries.

The verifier shares no code with the importer: its own CSV reader (eleven lines,
deliberately not `sources.read_csv`) and its own field-type vocabulary
(`egdb_checks.KEYWORD_OF_FIELD_TYPE`, transcribed from Esri's documentation).
`schema.py` emits arcpy *tool keywords* — `SHORT`, `TEXT` — while arcpy's
`Field.type` reports *geodatabase type names* — `SmallInteger`, `String`. Two
vocabularies for one set of types, which is what makes the comparison
meaningful.

### Status, 2026-09-04

**Both sources ran end to end.** In the PostgreSQL geodatabase:

| Feature class | Source | Features | CRS | Verified |
|---|---|---|---|---|
| `agsdb.sde.nrw_points` | `csv_data/output/nrw_points.csv` | 100 | EPSG:4326 | **10 of 10 checks green** — [`output/verification_report.md`](output/verification_report.md) |
| `agsdb.sde.synthetic_airports` | `opensearch/input/synthetic_airports.json` | 880 | EPSG:3857 | not yet — see below |

Measured on that machine: Python 3.13.13, licence `ArcEditor` (Standard).

Both captures carry the basemap attribution, in ArcGIS Pro's *Service Layer
Credits* panel. Recorded here as text as well, so it survives the image being
resized or re-exported:

> Sources: Esri, TomTom, Garmin, FAO, NOAA, USGS, © OpenStreetMap contributors,
> and the GIS User Community, Esri, USGS

That notice names **OpenStreetMap contributors**, which is the point: the World
Topographic Map basemap includes OSM data, and the ODbL treats a map image as a
**Produced Work** — redistribution is fine, attribution is the condition
(CLAUDE.md §3). The first capture had the panel closed, so the window contained
no notice at all without anything having been cropped.

#### The airports pop-up shows three findings at once

`input/egdb_airports.png`, one feature, and every row of it earns its place:

- **`objectid 282` next to `source_objectid 305`.** They disagree, which is the
  *safe* version. The geodatabase assigned 282; 305 came from whichever
  geodatabase the source was exported from. Compare `nrw_points`, where
  `objectid 65` sits directly above the CSV's own `id 65` — they agree only
  because the rows were inserted in file order, and they diverge the first time
  anything is deleted and re-added. The two feature classes demonstrate the two
  halves of the same trap side by side, and the `--rename` to a `source_` prefix
  is what makes the airports version legible.
- **`state_fips 08`.** The leading zero survived, and that is the whole
  declaration-beats-measurement finding in one cell. Measuring the column alone
  chooses `LONG`, after which Colorado is `8` and `WHERE state_fips = '08'`
  returns nothing.
- **`field` renders as an empty cell and is not empty.** It holds `" "`, a
  single space, as it does in 825 of 880 rows. A filter on empty finds nothing
  and `IS NULL` finds nothing either. This is what the first version of the
  loader would have written as `NULL`.

#### Still open

- **The airports feature class has not been verified.** It loaded and it draws,
  which check 4 exists precisely to show is not enough. One command:

  ```powershell
  propy scripts\verify_featureclass.py `
      --contract output\synthetic_airports_schema.json `
      --sde build\egdb.sde `
      --report output\synthetic_airports_verification_report.md
  ```

  Two of the ten checks will not apply as written: check 8 looks for
  `x_3857`/`y_3857` attributes, which this source does not carry (it reports
  INFO), and the transposed-box check spans most of the globe here — the
  airports' EPSG:3857 extent is roughly −19.8 M … 18.6 M in x and −1.6 M … 11.5 M
  in y, so the transpose is a valid box and may well be empty for reasons of
  luck rather than correctness. That is the `opensearch` antimeridian lesson
  again, and it should be *reported* as luck rather than counted as a pass.
- **The perturbation runs** that prove each check fires on its own (step 6 of
  the runbook) have not been done. Ten green checks are worth less than one
  check proven to go red.

## Credentials

The password comes from `EGDB_PASSWORD` or `--password`, and from nowhere else.
There is no default and no committed value.

`opensearch` takes the narrow CLAUDE.md §10 exception and commits a throwaway
password. That exception is **not** taken here: an Enterprise Geodatabase is not
a folder deleted with `build/`, it is a database instance with a real login, and
one `$env:EGDB_PASSWORD = '...'` on stage costs less than getting that judgement
wrong.

Note what the generated `.sde` file *does* contain. ArcGIS Pro can hang when
opening a geodatabase from a connection file whose credentials were not saved,
so `import_to_egdb.py` creates it with `SAVE_USERNAME` — which means the file
carries the credentials. That is precisely why it is written to `build/` and
gitignored, never to `input/` or `output/`.

## Reproducibility

- **Seed:** none. Nothing here is random; the output is a function of the input
  file.
- **Model / date:** scripts and documentation written with Claude Opus 5,
  2026-09-04. The source data was generated in `csv_data`.
- **Exact commands that produced the committed output:** the three under
  [Usage](#usage), with `--generated-date 2026-09-04`. All three artifacts are
  byte-reproducible; verified by running each twice and comparing SHA-256.
- **`--generated-date` exists for that reason.** Without it the contract would
  carry today's date and stop being reproducible tomorrow.
- Version claims that could **not** be verified from a fetchable Esri page are
  recorded as such in `input/egdb_requirements.json`, each with its source, its
  retrieval date and a verification status. Status as of 2026-09-04:

  | Claim | Status |
  |---|---|
  | Python 3.13.13 in Pro 3.7 | **confirmed by measurement** on the target machine |
  | Licence level sufficient | **measured**: `ArcEditor` (Standard) |
  | `arcgis` package 2.4.3.1 | still unmeasured — inferred from conda channel metadata, in no release note |
  | PostgreSQL / PostGIS pairing for 12.1 | still unmeasured — the version-pinned page does not resolve |

  The last two are printed by the importer's preflight, so they resolve on the
  first real run. The point of the table is that "the documentation says" and
  "the instance reports" stay distinguishable until one of them has actually
  been checked.

## Notes for the talk

- **What worked.** The split into a measured, editable **schema contract** and a
  mechanical loader. The half of the work that needs a licence, a VM and a
  database turned into a transcription of a document reviewable on a laptop —
  and `--dry-run` plus the row rehearsal caught three planted defects without a
  database in sight. Type inference from *all* rows with the evidence written
  into the artifact also beat hand-writing a schema: `TEXT(120)` from a measured
  maximum of 76 is a decision somebody can disagree with, `TEXT(255)` is not.

- **What failed.** The API the request named. Not with an exception — with a
  shapefile, four silently truncated field names, and both measured TEXT lengths
  replaced by the format's maximum. The error message in the arcpy-free case
  names *shapely* as a remedy while the code checks *pyshp*, so following the
  message does not help. And one version of pyshp writes three files before
  dying inside the library. Four outcomes, one line of code, zero warnings —
  the difference was only ever what happened to be installed.

- **What surprised me.** Two things, both of which reversed a rule this
  repository runs on. The airports FeatureSet's **own declared schema beat the
  measurement** — `state_fips` measures as an integer and is `TEXT(2)` holding
  `01`…`09`, because a FIPS code is a code that looks like a number, and no
  amount of measuring digits reveals that. And "nothing was recomputed" turned
  out **not to survive the storage**: worst disagreement 9.5 nanometres across
  100 features, with no arithmetic anywhere in the pipeline. `opensearch` found
  1.9 nm from libm; this is 9.5 nm from a database keeping a number.

- **Lesson learned.** *Check what an API wrote, not whether it threw.* An
  interface that cannot reach your target may still hand you a path and a
  success, and the schema is where the damage lands.
