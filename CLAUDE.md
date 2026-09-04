# CLAUDE.md — Working Instructions for This Repository

Read this before doing anything in this repository. It defines the purpose, the
layout, the conventions and — most importantly — the **documentation duties**
that apply to every single task.

---

## 1. Project purpose

**Overall topic: Test (Geo-)Data Generation with GenAI.**

This repository is a collection of independent sub-projects ("use cases"), each
demonstrating a different way to generate, transform or validate test data —
with a strong focus on geospatial data — using generative AI.

The material is the basis for a **conference talk**. This has a hard
consequence for how we work: *the process matters as much as the result.*
Every prompt, every iteration, every dead end must be traceable afterwards, so
the talk can show not only "look, it works" but "this is how we got there".

Audience of the talk: developers and geo-IT practitioners. Assume they are
technical but not familiar with this repository.

---

## 2. Repository layout

```
devsummit/
├── CLAUDE.md          # this file — instructions for Claude
├── README.md          # human-facing overview + index of all use cases
├── PROMPT.md          # chronological log of all prompts and work steps
├── .gitignore
└── <use-case>/        # one folder per sub-project
    ├── README.md      # detailed docs for this use case
    ├── input/         # read-only source data
    └── output/        # generated artifacts only — committed
```

Optional inside a use case, when needed: `src/`, `scripts/`, `tests/`,
`prompts/` (for prompt templates used by the code itself), and `build/` for
generated artifacts that stay out of git (see section 3).

**Every new use case follows exactly this pattern.** Create
`<name>/{input,output}` plus a `<name>/README.md` — no exceptions, no
alternative folder names.

Folder naming: lowercase, `snake_case`, descriptive of the use case
(`csv_data`, `opensearch`, `python_import`).

**`slides/` is the one exception, and it is not a use case.** It holds the
conference presentation itself (Slidev, Markdown, deployed to GitHub Pages), so
it has no `input/` and no `output/` and generates no test data. Treat it as
documentation infrastructure: it *reads* from the use cases and never writes to
them. Do not create further non-use-case folders without asking.

---

## 3. Data conventions

**`input/` is read-only.**
Source data, seeds, schemas, real-world samples, prompt fixtures. Code may read
from here but must never write, move or overwrite anything in `input/`. If a
transformation needs an intermediate file, it goes to `output/`.

The one exception is a **documented one-off provisioning script** that creates an
input fixture (downloading an open-data boundary, for example). It must be named
as such in the README, must not be part of the generation pipeline, and must
write source URL and licence into the fixture itself so the file carries its own
attribution. Its output is committed, so it normally never runs again.

**External data must carry an explicit, CC BY-compatible licence.**
Check the licence *before* the geometry. An archived repository with no stated
licence is unusable no matter how good its data is, and "derived from a
well-known source" is not a licence. Record the source, the licence and the
rejected alternatives in the use-case README — the rejection is talk material.

"Open" is not one licence. The ladder, shortest leash to longest:

| Licence | Attribution | Share-alike | Usable here |
|---|---|---|---|
| CC0 1.0, dl-de/zero-2-0, public domain | no | no | yes |
| CC BY 4.0, dl-de/by-2-0 | yes | no | yes — record the attribution notice |
| **ODbL 1.0** (OpenStreetMap) | yes | **yes** | **no** |

**ODbL is the trap, and it is worth understanding rather than just avoiding.**
OpenStreetMap is usually the best data available, and it cannot go into this
repository. The ODbL distinguishes a **Produced Work** (a map image, aggregate
statistics — attribution only) from a **Derivative Database** (extracted,
filtered or enriched rows — share-alike bites). A CSV of features pulled out of
OSM is the second kind, so it must itself be ODbL and cannot be relicensed as
CC BY. Publishing it on GitHub is perfectly legal; putting it in a CC BY
repository is not. Querying an OSM-backed *service* for a one-off answer that
never gets committed (a reverse-geocoding lookup to settle a single case) is
fine — nothing is redistributed.

If a source is rejected purely on licence grounds, say so explicitly in the
README, including what it would have been good at. "The best data set was
unusable for legal reasons" is one of the more useful things this repository has
to say.

**When the licence cannot be established, take the structure and generate the
data — and record that this was the reason.** "Probably derived from a public
source" is the same as no licence. Measured in `opensearch`: an export from a
real Enterprise Geodatabase, handed over to prove a second data source works,
turned out to carry no licence statement and a maybe ("I think it's the FAA data
set, but I don't know for sure"). The file was gitignored — not merely left
untracked, because the surrounding `input/` is committed in full and one
`git add` would take it along — and what was reused is its schema plus its
*measured* distributions and quirks, rebuilt with generated values. This is
better than a substitute source, because the shape of real data is the part
nobody invents correctly. **Measure the original before replacing it**: two
properties of the rebuild were wrong on the first attempt and both looked
entirely plausible — a 6:1 category skew flattened to five equal buckets by a
round-robin fill, and a log-normal tail an order of magnitude short because the
sigma was guessed instead of derived from the measured spread. Neither would
have been found without the original still sitting there to compare against.
State plainly what the rebuild cannot restore: that somebody else published it.
A synthetic set proves the pipeline, not the world.

**Open-data portals rot — commit the slice, not just the URL.**
Measured in `open_data_search`: the download URL that every tutorial and every
GitHub mirror still names for DB station data no longer resolves at all, and its
successor portal is mid-migration. A documented command is not reproducibility if
the document outlives the host. Commit the subset actually used, verbatim, plus a
manifest recording source URL, retrieval date, licence, attribution text and the
**SHA-256** of the exact file it came from. That is what turns "we used this
version" into a checkable claim, and it lets the pipeline run offline on stage.

**A screenshot of a result belongs in `input/`, not `output/`.**
Counter-intuitive but forced by the rules above: a capture from ArcGIS Pro or a
similar client is made by hand and cannot be regenerated from the documented
command, so `output/` — which must always be safe to delete and rebuild — is the
wrong place for it. It is an external artifact the use case consumes, like any
other fixture. Name it after the data set it shows
(`csv_data/input/nrw_points.png`), and let anything that displays it read from
there rather than keeping a second copy.

**Never crop the attribution out of a published screenshot.**
A basemap capture carries its provider notice burnt into the bottom edge
(`Esri | TomTom | Garmin | USGS | FAO | NOAA`, plus the state agency for an
official basemap). Publishing the image redistributes it, and that notice is the
condition. Practically: always `object-fit: contain` in an `<img>`, never
`background-size: cover` — a background image is cropped to fill, and the first
thing cropped off a map capture is exactly that bar. This rules out the
best-looking option more than once, which is the point.

**`output/` is generated, but committed.**
Only generated artifacts. It must always be safe to delete the entire folder and
regenerate its contents from `input/` plus the documented command. Never edit
files in `output/` by hand — if the result is wrong, fix the generator.

`output/` **is** under version control: the generated result is what a use case
is about, and later use cases consume it as input. Keep committed artifacts
small enough to stay readable.

**`build/` and `dist/` are disposable and gitignored.**
Generated code, scratch files, intermediate build products — anything that
should not be versioned goes here, not into `output/`. Regenerable from the
documented command, never referenced by another use case.

**Third-party binaries go to `build/`; git gets a manifest.**
A use case may need a server, not just a library — a search engine, a database,
a runtime. The archive never enters the repository. What is committed is
`input/<product>_dist.json`: version, download URL, size, the checksum **the
vendor publishes** (prefer that over one computed locally — it is a claim about
the artifact, not about our download), licence, and the reason for the version
choice. The setup script reads that manifest, and a checksum mismatch aborts
rather than warns.

**Pin the version the *client* certifies, not the newest one.** Measured in
`opensearch`: ArcGIS Pro 3.7 and Enterprise 12.1 support OpenSearch **2.12** —
one minor release, not the 2.x line. A GIS client pins its database support far
harder than the database pins itself, so tracking "latest" means tracking away
from the only version that works. State the certified pairing in the manifest so
the pin does not look like neglect.

**Old pinned versions carry expired material.** The demo TLS root CA shipped
with OpenSearch 2.12.0 was issued with a **30-day** validity in August 2023 and
expired a month later, while the node certificate it signed runs to 2033. The
server starts, the chain looks plausible, and every client fails with
`certificate has expired`. When a pinned release is years old, check the
expiry dates of anything it ships (`openssl x509 -dates`) before believing its
quick-start path, and generate your own credentials rather than working around
the broken ones.

**Keep LLM output raw next to any corrected version.**
When generated data has to be corrected to be usable, commit both: the
unedited LLM artifact (`<name>_llm_raw.csv`) as evidence, and the corrected
file that downstream use cases actually read. State in the README exactly which
columns or fields were corrected, and leave everything else byte-identical.
The delta between the two files is the most valuable thing in the repository.

**Large data sets.**
Commit the real output as long as it stays in the low single-digit megabytes —
a 10,000-row CSV at ~2 MB belongs in git, because the next use case needs the
volume. Beyond that, commit a sample of a few hundred rows and send the full run
to `build/`. Always state the committed size and the full size in the README.

---

## 4. Geodata conventions

Learned the hard way in `csv_data`. These apply to every use case that touches
coordinates.

- **An Esri JSON FeatureSet is not GeoJSON, and the difference is the CRS.**
  A file described as "a GeoJSON export from a feature class" is often the
  output of an ArcGIS REST `query?f=json`: `geometryType: "esriGeometryPoint"`,
  geometry as `{"x": …, "y": …}`, and
  `spatialReference {"wkid": 102100, "latestWkid": 3857}` — Web Mercator in
  **metres**, where RFC 7946 GeoJSON is always EPSG:4326. (`wkid` 102100 is the
  deprecated Esri code for the same auxiliary sphere `latestWkid` calls 3857,
  which is why the file names it twice.) The `{"x","y"}` shape fails loudly in
  any GeoJSON reader; the CRS does not fail at all. A value of `-13055594.63`
  read as a longitude is out of range, and a library that clamps rather than
  raises puts every point on the antimeridian — inside the valid domain,
  plotted without complaint, and systematic rather than broken-looking. So a
  reader must **assert `geometryType` and `latestWkid` and abort**, never
  convert what it happens to be handed: a FeatureSet in another projected CRS
  would still be metres, just of a different grid, and the output would be
  plausible and wrong.
- **Name the EPSG code explicitly**, in the README and in the column names.
  "Coordinates" is not a specification. Note that "decimal degrees" and
  "EPSG:3857" are mutually exclusive — decimal degrees are EPSG:4326, EPSG:3857
  is metres. If a request mixes them, say so and resolve it explicitly instead
  of picking one silently.
- **Column naming follows the CRS**: `latitude`/`longitude` for a geographic
  CRS, `x`/`y` (optionally suffixed, e.g. `x_3857`) for a projected one. Never
  call a projected coordinate "lat"/"lon".
- **Column order**: `latitude` before `longitude`, `x` before `y`. GeoJSON is
  the exception and always `[longitude, latitude]` per RFC 7946 — flag that
  wherever both appear.
- **Every generated coordinate set ships a verification step**, and the
  verification is code, not inspection. At minimum: axis order (a swap must
  fail loudly), value range, and — if more than one CRS is present — a
  recomputation of the projected values from the geographic ones.
- **Never trust an LLM with a projection formula.** Anything containing a
  logarithm, tangent or square root gets recomputed. The failure mode is a
  systematic directional bias, not random noise, so it survives averaging and
  spot-checks and looks entirely plausible in the data.
- **A data set that crosses the antimeridian turns the bounding-box check into
  a prop, and the axis-swap check into a coin flip.** Measured in `opensearch`:
  880 airports spanning longitude −178.0 … +166.6 have a naive envelope of
  **344.63° × 85.46°** — it matches every document and discriminates nothing.
  Replace it with regional boxes tight enough to mean something, each checked
  against a count computed from the source, plus one box that deliberately
  **spans** the dateline (`top_left.lon` > `bottom_right.lon` is how OpenSearch
  is told to wrap). Two further consequences, both measured: for five of seven
  regions the *transposed* box does not exist — Alaska's longitudes are
  −179.5…−129.5, and asking for those as latitudes is rejected outright
  (`top is below bottom corner`) — and where the transposed test does apply it
  passes only because no feature happens to sit at longitude −14…71. Say that
  it is luck. **And the same geometry decides whether a swapped axis is loud or
  silent**: swapping here gets **550 of 880** documents rejected by the engine
  (`illegal latitude value [-97.302373]`) and aborts the load, while swapping
  the NRW stations — latitude 50-52, longitude 5-9, both valid latitudes —
  loaded all 449 happily into the Indian Ocean. Nothing in the code differs.
  The verifier that caught the stations was luckier, not better.
- **A bounding box is not a boundary.** Sampling a rectangle around an
  irregular region places a substantial share of the points outside it. Either
  sample against a polygon, or measure and document the share that falls
  outside. Measured in `csv_data`: 41 % outside NRW with a box, 0 % outside
  Germany with rejection sampling against a polygon.
- **Uniform in latitude is not uniform on the ground.** A degree of longitude
  shortens towards the poles, so `uniform(lat_min, lat_max)` over-samples the
  higher latitudes. Sample `sin(latitude)` uniformly for equal-area coverage,
  and state which one was used.
- **Round before projecting.** Store rounded geographic coordinates, then derive
  projected values from the rounded numbers. Projecting first leaves every row
  disagreeing with itself by the rounding step, and nothing but an independent
  recomputation will notice.
- **A verifier must not share its projection implementation with the generator
  it checks.** Share plane geometry if useful, never the formula under test —
  otherwise a bug passes both. Write the two forms differently on purpose
  (`ln(tan(pi/4 + phi/2))` against `atanh(sin phi)`), so agreement is evidence.
- **No convenient defaults on destructive arguments.** A verifier's
  `--output` default once made checking one data set overwrite another. If a
  flag writes a file, require the path.
- **Your reference data is data too.** Boundaries, gazetteers and lookup tables
  get verified with the same suspicion as the payload. In `open_data_search` a
  generalised 1:10 M outline placed a station 1.3 km outside its own federal
  state; the authoritative boundary put it 117 m inside. The check fired
  correctly and the conclusion drawn from it was wrong. **When a cross-check
  fails on exactly one record, suspect the check before the data.** Match the
  precision of the reference to the precision of the question — a generalised
  outline cannot answer a 100 m question — and prefer the authoritative source
  when the answer has to hold up in public.
- **An identifier column is not an identifier, and a two-letter code is not
  the abbreviation it looks like.** Measured in `opensearch`, in one geodatabase
  export: `objectid` and `ESRI_OID` are both 1…N, both unique, and **equal in
  zero rows**, while the GIS client builds its own Object ID from the document
  `_id` — three columns that look like an object id and none of them the one
  that is used. The stable key was the business key (`locid`). Prefix such
  columns (`source_objectid`) so the attribute table stops inviting a join on
  them. In the same file, `state` carried `HI` with `state_fips` **74** (US
  Minor Outlying Islands) while Hawaii is FIPS 15 — so `WHERE state = 'HI'`
  returns points ~2,000 km from Hawaii and `WHERE state = 'Hawaii'` silently
  drops them. Neither query is wrong; the attribute is. Check a code against the
  published standard rather than against the first two letters of a name, and
  distinguish the two cases: `MP` in the same file is the *correct*
  abbreviation, merely inconsistently formatted.
- **A geodatabase's "empty" may be a single space.** Measured: `" "` and not
  `NULL`, on 825 of 880 rows of one column. In a search engine that is a real
  keyword term; in a GIS client the cell looks empty and is not, so a filter on
  empty finds nothing and `IS NULL` finds nothing either. Count it, report it,
  and keep the value verbatim — the space is what the source stores, and
  tidying it away is a silent edit to somebody else's data.
- **An attribute filter is not a spatial filter, and the cross-check is worth
  keeping even when it finds nothing.** Filter on `Bundesland`/`region`/`country`
  if the column exists, then have the geometry referee it. Measured: across all
  5,367 in-service stations of the German DB InfraGO data set, the attribute and
  the authoritative polygon disagree zero times in either direction — and "zero"
  is only a result because it was measured.
- **One real-world feature may carry several source positions.** Route-centric
  data sets emit one row per route through a station, each with that route's
  own coordinate. Measured in `open_data_search`: 893 rows for 449 stations,
  median spread 326 m among the multi-row ones, worst case 4,047 m, up to 15
  rows for one station. `dict[key] = row` therefore picks an arbitrary point up
  to ~2 km off and leaves a data set that looks immaculate. **Measure the
  intra-feature spread before deduplicating**, pick the **medoid** (a position
  somebody actually published, still traceable) rather than the first row or a
  computed mean, and carry the spread into the output as a column — dropping the
  uncertainty is how it gets forgotten.
- **Redundant coordinate columns tell you which one to distrust.** When a source
  publishes the same point in several CRS, recompute them against each other.
  Measured: the DB InfraGO EPSG:25832 columns agree with its EPSG:4326 columns
  to 1 mm, while its `WKT WGS84` column disagrees with both by a median of
  1.27 m. Two representations would only have shown a conflict; three showed
  which one to believe.
- **When the data has to be reprojected, provenance splits in two — and both
  halves need their own check.** "Nothing was recomputed" is the strongest claim
  available and it is unavailable the moment a source in a projected CRS has to
  become `geo_point` degrees. So: carry the **source coordinate through
  bit-identically** (`x_3857`/`y_3857` asserted `==`, the same double, against
  the source row with the same identity key), and prove the **computed
  coordinate reproducible by code that shares nothing with the code that
  computed it** — take the degrees back out of the index and project them
  *forward* again from a module the indexer cannot import. Different function,
  opposite direction, no shared line; weaker evidence than a third-party
  library, and it survives a use case that must run without dependencies.
  Measured in `opensearch`: the forward round trip closes at **0.05 mm** across
  880 documents - half the rounding step of the stored metres - and at
  **0.2 mm** on a real export whose metres were not derived from rounded
  degrees. Do not tighten the tolerance to the current artifact's exact
  rounding; a check calibrated that finely fails on the next source for a
  reason that is not an error. **Then prove each half fires
  on its own**: move one document 40 km inside its own state and both go red;
  move only the degrees and only the reprojection does; move only the metres and
  only the provenance does. In all three cases the other seventeen checks stay
  green — bounding boxes, axis order, distance queries, field types. A verifier
  that never goes red has not been verified, and one whose checks always go red
  together has one check wearing three hats.
- **For sourced data, verify provenance, not plausibility.** "Is this value
  plausible?" is the wrong question about data somebody else published. Assert
  instead that every coordinate in `output/` exists, unmodified, in a source row
  with the same identity key. A single coordinate changed to a plausible spot
  inside the region passes the bounding box, the polygon, the axis check and the
  projection check; only the provenance check catches it. It is about fifteen
  lines, and it is what makes "nothing was invented" verifiable rather than
  asserted.
- **Prefer a genuinely independent implementation over a second formula.** Two
  hand-written forms of the same projection are the fallback when a use case must
  run without dependencies. When a use case may have dependencies, spend one on
  this: let the generator hand-write the maths and the verifier call a
  third-party library (`pyproj`/PROJ), and do the same for containment
  (`shapely` on one side, ray casting on the other). Agreement between separate
  code bases is stronger evidence than agreement between two of your own lines.
- **When the data has a consumer, verify against the consumer — not only against
  itself.** "Is the geometry correct?" and "can the target system read it?" are
  two questions, and the second one is answered by the *consumer's*
  documentation. Measured in `opensearch`: ArcGIS cannot read a `geo_point`
  written as `{"lat": …, "lon": …}` — the first form in the OpenSearch docs and
  the one an LLM writes unprompted. An index built that way failed **1 of 12**
  checks. Document count, bounding box, `geo_distance` against an independent
  haversine, coordinate provenance: all green, and the layer will not open. By
  comparison a swapped axis fails 5 of 12 and puts the points in another
  hemisphere. **The loud error is the harmless one.** So: read the target's field
  and format requirements before designing the schema, encode them as a check,
  and let the target's constraint — not the database's tolerance — decide the
  representation.
- **Where a spec allows several encodings, parameterise and verify — never
  assume.** The three ArcGIS-readable `geo_point` forms disagree about axis
  order: array is `[lon, lat]`, a bare string is `"lat,lon"`, WKT is
  `POINT (lon lat)`. Two of three put longitude first and the odd one out reads
  most like prose. Expose the choice as a flag, decode it in the verifier from a
  second reading of the spec, and let the engine referee the axis order (a
  bounding box that must match everything, plus its transpose that must match
  nothing).
- **Two subsystems of one product can demand incompatible formats.** The
  OpenSearch SQL plugin accepts *only* `{"lat": …, "lon": …}` — the one form
  ArcGIS forbids — and rejects array, string, WKT and geohash alike. ArcGIS query
  layers are SQL, so whether this is fatal depends on something neither side
  documents. Report such a conflict as an explicit INFO finding with the
  measurement behind it; do not resolve it by guessing, and do not hide it
  because it did not break the current path.
- **Quote the whole sentence, especially when it looks like a contradiction.**
  Two vendor statements that seem to conflict are usually one statement read
  twice, once too short. Measured in `opensearch`: Esri's *"Sharing query layers
  from Elasticsearch or OpenSearch is not supported"* was recorded here as an
  unresolvable contradiction against the publishing workflow documented next to
  it. The sentence continues *"...as a map image layer or web feature layer that
  copies all data, a web tile layer, ..."* - an enumeration of exclusions, with
  the one supported route surviving in the half that had been cut. A truncated
  quote is indistinguishable from an inconsistent vendor, and "the documentation
  contradicts itself" is a comfortable place to stop looking. Before recording a
  contradiction, re-fetch the source and quote it to the full stop. When the
  correction lands, keep the wrong reading visible and mark it corrected - the
  delta is the talk material, deleting it is not.
- **"The consumer" is a list, not a thing — and a credential or certificate has
  more consumers than the data does.** Verifying against one client proves
  nothing about the next. Measured in `opensearch`: the private CA was imported
  once, ArcGIS Pro connected, and the certificate looked settled — then ArcGIS
  Server, on the *same machine*, against the *same URL*, rejected it with
  `WinINet ERROR_INTERNET_INVALID_CA (12045)`. A Windows trust store belongs to
  a **principal**: `certmgr.msc` is the interactive user's store and satisfies a
  desktop client, while a service account reads the Local Computer store
  (`certlm.msc`). A service also will not see a certificate added while it was
  running, so a restart is part of the import. **And a trust store is per
  runtime, not merely per principal — one product can appear on the consumer
  list twice.** With the Local Computer store fixed, the same ArcGIS Server
  failed again with `PKIX path building failed`: it is part native and part
  Java, and a JVM reads its own `cacerts`, never the Windows store. Four
  consumers of one self-signed CA on one machine — Pro (Current User), the
  server's native stack (Local Computer), the server's JVM (admin directory
  `importRootOrIntermediate`), Portal's JVM (its own admin directory) — four
  mechanisms, and **each fix only makes the next failure observable**. Three
  green results in a row were each real and each said nothing about the next
  consumer. So enumerate every process *and every runtime* that will open the
  connection, and say which store each one reads, rather than writing "import it
  into the Windows certificate store" as though there were one. Prefer the
  vendor's supported import over the one that works: editing a bundled JRE's
  `cacerts` directly is undone by the next upgrade, silently and months later.
  The same shape as the projection-formula and same-language-checker rules: the
  component that fails is the one with no dialog to show.
- **A UI that offers the same label twice offers you the wrong one.** ArcGIS
  Pro's share pane has a check box called **Feature** under *Copy all data* and
  another called **Feature** under *Reference registered data*; for an
  OpenSearch layer only the second works, and the error names neither. When a
  documented capability fails, check whether the control you used is the control
  the documentation meant before concluding the capability is missing.

---

## 5. Tech-stack policy

**There is no global default stack.** Each use case picks whatever fits best —
Python, Node/TypeScript, shell, SQL, a REST client, an MCP server, whatever the
scenario calls for. Showing this variety is deliberate and part of the talk.

Rules that do apply regardless of stack:

- **Isolate dependencies per use case**: Python → `.venv/` or `uv` inside the
  use-case folder; Node → a local `package.json`. Never install globally.
- **Document the choice**: the use-case README states the stack *and one
  sentence on why it was chosen*. That reasoning is talk material.
- **Every executable is self-describing**: a CLI must support `--help` and
  print a usable summary of its arguments.
- **Every executable has a copy-pasteable example command** in its README —
  including the exact input path and expected output path.
- **Prefer relative paths** inside the use case, so commands work regardless of
  where the repository is cloned.
- **A ported script is a second implementation, so it can disagree with the
  first — and a shared literal is where it happens.** Measured in `opensearch`:
  the demo password `DevSummit#2026!os` reached OpenSearch as `DevSummit#2026os`
  from `setup_opensearch.bat`, because `cmd.exe` under
  `setlocal EnableDelayedExpansion` strips an unmatched `!` from every
  `set "VAR=..."`. Setup reported success, the cluster came up, and the status
  command said `green` — that command is a batch file too and mangled the
  password the same way. Only the browser, the Python client and hand-typed
  `curl` saw the 401. **A checker written in the same language as the thing it
  checks shares its bugs**, which is the projection-formula rule from section 4
  in a different costume. Keep values that any shell in the chain can rewrite
  (`!`, `%`, `$`, `^`, backticks) out of shared constants rather than escaping
  them per platform, and prove a credential from outside the script family that
  set it.

---

## 6. Documentation duties — mandatory after every task

After finishing any piece of work, update all four in this order. Do not wait
to be asked; this is the standing instruction.

1. **`PROMPT.md`** — append an entry using the format in section 7: the
   prompt *verbatim* in German, an English translation, and what actually
   happened, including what failed. Skip this step only if the user explicitly
   asked for the prompt not to be logged (see section 7).
2. **`<use-case>/README.md`** — purpose, stack, input, output, setup, usage,
   example output, notes for the talk.
3. **`README.md` (root)** — keep the use-case index, the executables table and
   the progress log current.
4. **`CLAUDE.md` (this file)** — whenever a new convention, tool or constraint
   emerges, write it down here so it does not have to be repeated in a prompt.

If a task changes nothing user-visible (e.g. pure research), still log it in
`PROMPT.md` — an unproductive iteration is a valid finding for the talk. The one
exception stays the explicit "do not log this" instruction.

---

## 7. `PROMPT.md` entry format

Entries are appended chronologically, newest at the bottom, numbered
sequentially.

The user prompts in **German**. Each entry therefore carries the original prompt
*and* an English translation, so the log stays readable for an
English-speaking audience without losing the original evidence.

```markdown
## [NNN] YYYY-MM-DD — <short title>  ·  scope: <folder or "root">

**Prompt (original, DE)**
> <original prompt, verbatim, unedited>

**Prompt (translation, EN)**
> <faithful English translation of the prompt above>

**What happened**
- <steps taken, decisions made, tools/models used>

**Artifacts**
- `path/to/file` — <purpose>

**Result / Iteration**
- <outcome; what did not work; follow-up needed>
```

Guidelines:
- The **original prompt is verbatim** — same language, same wording, including
  typos, abbreviations and inconsistent capitalisation. It is evidence, not
  documentation. Never clean it up.
- The **translation is faithful, not polished**: translate what was written,
  including its vagueness. Do not fix, expand or interpret the request in the
  translation. If a phrase is genuinely ambiguous in German, keep the ambiguity
  and, if needed, add a short `[note: ...]` marker.
- If a prompt happens to be written in English, keep a single
  `**Prompt**` block instead of the DE/EN pair.
- "What happened" is a summary, not a transcript — a handful of bullets.
- Be honest in "Result / Iteration". Failed attempts and course corrections are
  the most interesting part of the talk.

### Prompts excluded from the log

The user may explicitly ask for a prompt **not** to be logged (e.g. "logge
diesen Prompt nicht", "nicht protokollieren"). In that case:

- Do **not** add an entry to `PROMPT.md` for that prompt.
- Still apply everything else the prompt asks for, including any resulting
  updates to `CLAUDE.md`, `README.md` or existing `PROMPT.md` entries.
- Do not leave a placeholder, a gap in the numbering or a "redacted" note —
  the log simply continues with the next number.

This typically applies to meta-prompts about documentation and conventions,
which are noise for the talk narrative.

---

## 8. Notes for the talk

**The slot is a hard constraint, and the deck is built around leaving things
out.** The talk is **15 minutes including questions** — about 12 minutes of
speaking, so roughly fourteen slides. The repository grows; the slot does not.
`slides/` therefore has two tiers:

- a **core deck** of four named rules, each proven by *one* measured number and
  *one* image, and
- a **backup section** after the end, written out but not shown — reachable by
  arrow key during questions and readable in the repository.

**A new use case lands in the backup first.** It enters the core deck only by
displacing a rule whose finding is weaker. Never widen the core deck to
accommodate new material, and never leave a finding undocumented because it did
not make the cut — the backup is where it goes.

**Verify a deck the way you verify data: against its consumer.** A green Slidev
build says nothing about whether a slide is readable. Render the slides to PNG
(`npm install --no-save playwright-chromium`, then
`slidev export --format png`) and look at every one. Measured while building the
first draft: three real defects that the build reported as success — two slides
overflowing past the bottom edge with the punchline cut off, and Slidev's
`two-cols-header` layout running a long left column underneath the image in the
right column. Prefer an explicit CSS grid over that layout, and keep dense
slides under test.

Each use-case README ends with a `Notes for the talk` section capturing:

- **What worked** — where GenAI was clearly faster or better than hand-writing.
- **What failed** — hallucinated values, invalid geometries, broken CRS,
  schema drift, non-determinism, cost/latency surprises.
- **Lesson learned** — the one sentence a listener should take away.

Write these down *while working*, not afterwards. Details get lost.

---

## 9. Language rules

- **Documentation, code, comments, identifiers, CLI texts, log output, commit
  messages: English.**
- **Chat communication with the user: German.**
- German umlauts and special characters must be written correctly wherever
  German text appears — never ASCII substitutions.

---

## 10. Reproducibility

Generated test data is only useful for a talk if it can be regenerated live.

- **Fix random seeds** and expose them as a CLI argument with a documented
  default.
- **Record the model and date** used for any GenAI-assisted generation (e.g.
  "generated with Claude Opus 5, 2026-08-20") in the use-case README.
- **Record the exact command** that produced the committed output.
- **Note non-determinism explicitly** where it exists — LLM output that varies
  between runs is a finding, not a bug to hide.
- **A hash-pinned artifact must not store a raw float that came out of `libm`.**
  C transcendental functions - `log`, `tan`, `sin`, `asin`, `exp` - are **not
  standardised to the last bit**, so glibc and MSVC may each return either of
  the two nearest doubles. Measured in `opensearch`: rebuilding a committed
  fixture with the same seed on Windows Server 2025 / CPython 3.14.7 against
  Linux / CPython 3.12.7 gave a different SHA-256 at identical file size and
  feature count, because **30 of 880 `y` values differed by up to 2 ULP - 1.9
  nanometres**. `y = R·log(tan(π/4 + φ/2))` passes through libm twice; the
  matching `x = R·radians(lon)` is a multiplication and was identical
  everywhere. Fix it by **storing rounded values**, and pick the precision the
  real source carries rather than the maximum the double offers - here four
  decimals, a tenth of a millimetre, which also made the fixture structurally
  closer to the export it imitates. Rule out the boring causes first, in this
  order: newline translation (compare the file's hash against the hash of the
  string before writing - if they agree, newlines are innocent), then the random
  sequence (fingerprint the generator's RNG calls; the Mersenne Twister is
  specified bit-for-bit and survives Python minor versions), then the values.
  **Two traps in the fix itself.** Rounding only helps while no value sits on a
  rounding boundary: measured, four decimals left the closest value 15.6× the
  divergence away, five decimals 1.3× and six decimals 0.5× - at six, rounding
  would have changed nothing. So *measure that margin on the unrounded values*
  and refuse to write an artifact whose margin is too small, rather than
  assuming the idea works. And measuring it on the **rounded** values proves
  nothing, because rounding puts them on the grid by definition - a check that
  always passes, which is how the first version of it was written. **And do not
  trust a spot check whose sample rate you have not measured**: five hex-float
  comparisons of `sin`/`log`/`tan` were bit-identical on both machines and still
  are, because the divergence rate is 3.4 % and five samples had an 84 % chance
  of showing nothing. Diff the artifact field by field; the fingerprint
  reassures, the diff answers.
- **If a committed file is pinned by its hash, pin its line endings too.**
  A manifest recording the SHA-256 of a committed artifact is only checkable
  while the bytes survive the trip. A checkout on Windows with
  `core.autocrlf=true` rewrites every newline and changes the hash without
  changing a single value — the provenance check then fails for a reason that
  has nothing to do with the data. Declare it in `.gitattributes`
  (`* text=auto eol=lf`, with `*.bat text eol=crlf` as the exception, because
  `cmd.exe` needs CRLF) rather than hoping every clone is configured correctly.
  Write the file with an explicit `newline="\n"`, and say in the README that a
  hand copy between machines must be verbatim — `.gitattributes` protects a
  clone, and nothing protects a folder someone copied.
- **Never commit secrets.** API keys and endpoints come from environment
  variables; document the variable names, not the values.
- **State where a credential is actually stored, and whether it can be changed
  twice.** A password handed to a setup script is often copied into state on
  first use and read from there afterwards: OpenSearch initialises the admin
  user into the `.opendistro_security` index on the first start against an empty
  data directory, and every later run of the installer is a no-op — it rewrites
  `internal_users.yml` only while that file still carries the default hash it
  ships with. So a re-setup with a new password silently keeps the old one and
  fails as a 401 with nothing in the log. A `--force` that re-installs must wipe
  the state directory too, or it is not a reset; and if it does not, say so in
  the run rather than leaving it to be discovered.
- **One narrow exception, and only when the user grants it: the credentials of a
  local throwaway service.** A single-node test cluster on a VM, holding nothing
  but public open data and deleted with its `build/` folder, is not a secret —
  and a live demo that needs a manual `export` before the first command is a demo
  that fails on stage. Such a password may be committed if it is stated as an
  exception in the use-case README, overridable by flag and environment variable,
  and confined to that use case. Note also that the obvious value may be
  unavailable anyway: OpenSearch 2.12 runs the initial admin password through a
  strength check and rejects `admin`. Anything reaching a real system, a real
  account or real data stays out of git without exception.

---

## 11. Git & publication

This repository is version-controlled with Git and is **intended for public
release on GitHub** under the name `euro_dev_summit_26_test_data_ai`.

- Licence: **CC BY 4.0** (`LICENSE`, full official legal code — do not edit it,
  or GitHub will stop detecting the licence). Attribution notice lives in
  `README.md`. Anything added to this repository must be compatible with
  publication under CC BY.
- Default branch: `main`. Work directly on `main` unless asked otherwise.
- **Commit messages in English**, imperative mood, one logical change per
  commit (`Add CSV generator for address test data`).
- The commit history is part of the talk material: it should read as a
  comprehensible sequence of work steps. Prefer several meaningful commits over
  one bulk commit.
- **Commit only when asked.** Never push without an explicit request.

Because the repository will be public, the following must never be committed:

- API keys, tokens, endpoints of internal systems, `.env` files.
- Real customer data, internal company data, or any production geodata.
  Everything in `input/` must be synthetic, public (e.g. open data), or
  explicitly cleared for publication. If in doubt, ask before adding it.
- Personal data — generated person records must be obviously fictitious.

Note: this is exactly the point the talk makes. Not being allowed to use real
data is the very reason generated test data is needed.

---

## 12. Working style

- **Agree the verification depth up front — do not default to rigour.** This is
  a real cost, observed in `open_data_search`: adjudicating *one row out of 449*
  consumed a reverse-geocoding query, an authoritative Shapefile download, a
  fourth dependency and a Germany-wide re-run. For data that is real, published
  and attributed, that was the right call and produced the best finding in the
  folder. For test data destined for a staging database it would be
  over-engineering. The two situations look identical from inside the task, so
  **ask which one it is** — "plausible is enough" versus "must be defensible in
  public" — and let the answer decide how far the checks go. When in doubt,
  state the assumption and the cost rather than silently picking either one.
- Ask before restructuring existing use cases; new use cases can be created
  freely following the layout above.
- Keep sub-project READMEs skimmable — the root README is the index, details
  live locally.
- No unrequested extras: build the use case that was asked for, then document it.
