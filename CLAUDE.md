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
(`csv_data`, `opensearch`, `portal_publish`).

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
best-looking option more than once, which is the point. **And a notice that was never
shown is not different from one that was cropped.** ArcGIS Pro does not burn the
basemap attribution into the map at all: it lives in a dockable **Service Layer
Credits** panel, closed by default. Measured in `egdb_import`: a capture of the
entire application window contained no provider notice whatsoever, with nothing
having been cut off. Open that panel before capturing. Then **record the notice
as text in the README as well**, because an image can be resized, re-exported or
replaced and the obligation cannot - here it reads *"Sources: Esri, TomTom,
Garmin, FAO, NOAA, USGS, © OpenStreetMap contributors, and the GIS User
Community, Esri, USGS"*, which is also the confirmation that the Esri basemap
carries OSM data and therefore that the ODbL Produced-Work attribution applies.
Do not look for the notice at the bottom edge and conclude it is missing; look
for where the client keeps it.

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

**An artifact that names something the target system assigns must carry a
placeholder, not a value.** `output/` has to be regenerable from `input/` plus
the documented command, and a portal item id does not exist until the item is
created and changes on every run. So the committed artifact carries
`{{FEATURE_SERVICE_URL}}` and the substituted body goes to `build/`. Two
consequences, both measured in `portal_publish`. The substitution must be
**asserted**, because an unsubstituted token is the quiet failure: the portal
accepts the item, the viewer opens it, the frame draws, the legend lists four
layers and not one feature appears - no error anywhere. And the assertion must
grep for the **marker** rather than for a list of known token names: a
one-character typo (`{{FEATURE_SERVICE_UR}}`) passes a whitelist and is caught
by the marker. The price of the stricter check is that it also catches your own
prose - the first run aborted on a token sitting inside a note that *explained
the check* - so keep the marker out of the payload's documentation and write it
in words. Pay that price; the whitelist is the version that lets the real
failure through.

**A clamp counter that fires often has stopped being a counter and become the
distribution.** CLAUDE.md already says to derive a distribution's parameter
from the measured spread rather than guessing it. The same mistake has a second
shape when a bound is physical rather than a guard: measured in
`portal_publish`, an average household size drawn as a Gaussian with mean 1.6
against a hard floor of 1.0 clamped **37 of 500** rows onto exactly 1.0 - 7 %
of the data piled on one value, invisible on a map and glaring in a pop-up. A
gamma variate above the floor has the bound built into the distribution instead
and took it to 2. So: build a hard bound into the draw, keep the clamp as a
guard, set the guard wide enough that a normal run barely reaches it, and
**print every clamp count** - the count is only useful while it is still
reporting an anomaly rather than describing the data.

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
  component that fails is the one with no dialog to show. **And the trust anchor
  is usually reachable from the connection that fails.** Measured in
  `portal_publish`: `unable to get local issuer certificate` reads like a server
  fault, and the server is in fact sending a correct chain - leaf plus issuing
  CA - that simply ends below any anchor `certifi` knows. The issuing
  certificate's *Authority Information Access* extension names the root's
  download URL, so the bundle can be assembled from the failing host itself
  rather than requested from whoever runs the CA. Anchor on the root, not on the
  issuing certificate: OpenSSL will happily stop at either, so a green result
  with the issuer as anchor proves less than it looks. **And two libraries in
  one process are two consumers.** Measured in `portal_publish`: exporting
  `REQUESTS_CA_BUNDLE` makes `requests.get(portal_url)` return 200 and leaves
  `GIS(portal_url)` raising `CERTIFICATE_VERIFY_FAILED` in the same
  interpreter, because `arcgis` 2.4.1.1 mounts an adapter whose
  `init_poolmanager` supplies its own `ssl.SSLContext` (truststore plus
  `certifi.where()`), and a connection built from an explicit context never
  consults requests' `verify`. The supported route was a keyword argument
  documented only in the class docstring **inside the wheel**
  (`GIS(ca_bundles=...)`). So do not conclude that a certificate is installed
  because one library in the process accepted it, and when an environment
  variable appears to be ignored, read the library's own session construction
  before blaming the certificate.
- **A wrong spatial reference does not error at write time.** Measured in
  `egdb_import`: a feature class created as EPSG:3857 and fed decimal degrees
  accepts every row, satisfies the geodatabase, and draws - with all hundred
  points **within 52 metres of 0°N 0°E** in the Gulf of Guinea, because a
  longitude of 7.46 read as 7.46 metres is 0.000067°. There is no exception and
  no warning anywhere in the chain; a bounding box against the source's own
  measured extent is the only thing that notices. So create the feature class in
  the CRS the source already carries, state the code in the artifact that
  describes the schema, and check the extent afterwards.
- **Whether an axis swap is loud depends on the data, and it is worth saying
  which case you are in.** In `egdb_import` the transposed bounding box does
  real work: NRW is latitude 50-52 and longitude 5-9, so both ranges are valid
  latitudes, a swapped load is accepted without complaint, and every point lands
  around 7.5°N 51.3°E in the Somali Sea at a perfectly legal coordinate. That is
  the same silence the `opensearch` stations had, and the opposite of the
  airports, where the engine rejected 550 of 880. Never write "the axis check
  passes" without saying whether anything else would have caught a swap.
- **The geodatabase's name limits are tighter than the database's, and ArcGIS
  never quotes an identifier.** Esri: *"ArcGIS does not delimit object names. Do
  not create any tables, feature classes, indexes, databases, users, roles, or
  other object names that require delimiters if you will be using them with
  ArcGIS."* A field name may be **31** characters against PostgreSQL's own 63,
  so a name between 32 and 63 is stored happily by the database and
  unaddressable through ArcGIS. Mixed case is the same trap from the other
  side: PostgreSQL folds unquoted identifiers to lowercase, so a column created
  as `Latitude` *is* `latitude`, and code that remembers the capital is looking
  for a different column. Sanitise to the geodatabase's limit, lowercase, and
  record every rename in the artifact rather than performing it silently.
- **An Enterprise Geodatabase has no boolean type.** The whole list is SHORT,
  LONG, FLOAT, DOUBLE, TEXT, DATE, GUID, GLOBALID, BLOB. A `true`/`false`
  column has to become SHORT with 1/0, and the attribute table then shows a
  number with no way to indicate what it was. Record the substitution in the
  schema artifact; do not apply it silently. Measured in `egdb_import`, with an
  edge worth keeping: a shapefile *does* have a boolean (DBF type `L`), so the
  format that cannot be the target represents that one column better than the
  target can.
- **Never infer a decimal coordinate as FLOAT.** A 32-bit float carries about
  seven significant decimal digits; a latitude of 51.51264 needs seven and an
  EPSG:3857 metre value like 831034.51 needs eight. The rounding is silent and
  the result is a plausible coordinate in the wrong place. Everything decimal
  becomes DOUBLE.
- **A source that declares its own schema may beat your measurement — and a
  code that looks like a number is why.** The rest of this file says measure
  rather than trust; an Esri JSON FeatureSet exported from a geodatabase is the
  exception, because its `fields` block carries real types and real TEXT
  lengths. Measured in `egdb_import`: inferring types from the values alone
  would have made `state_fips` a `LONG`, and its values include `01` … `09` -
  after which `'01'` is `1` and `WHERE state_fips = '01'` finds nothing. The
  same run would have collapsed `acais` (only real value `Y`) into a boolean.
  No amount of measuring a column of digits reveals that it is a *code*. So
  where a declaration exists, let it decide the type, **record the measurement
  beside it**, and refuse the one case that is a defect rather than a
  difference of opinion: a declared TEXT length the source's own values exceed,
  which otherwise fails hundreds of rows into the insert.
- **"Empty" needs one definition, shared by everything that writes.** A
  geodatabase's blank may be `" "`, and this file already says to keep it
  verbatim - but that is only achievable if the code measuring nullability and
  the code writing values agree on what absent means. Measured in
  `egdb_import`: they did not, and the airports fixture aborted at row 0 with
  *"field 'field' is empty but the contract declares it non-nullable"* - the
  analyser counted 825 single spaces as present, the loader counted them as
  absent, one file and two answers. **1,343 values across three columns** were
  one release away from being written as `NULL`. The predicate is now a single
  public function imported by both. The general shape: code that has to
  **agree** should be shared; code that has to **check** must not be. Getting
  that backwards produces either a bug that passes both sides or a conflict at
  row 0.
- **An object id that agrees with a source column is more dangerous than one
  that does not.** Measured in `egdb_import`: the loaded feature class shows
  `objectid 65` directly above the source's own `id 65`. They match only because
  the rows were inserted in file order, and they diverge the first time anything
  is deleted and re-added - at which point every query that joined on the wrong
  one is quietly wrong. In `opensearch` the equivalent pair matched in **zero**
  rows and therefore announced itself. Prefer the loud version: prefix source
  identity columns (`source_objectid`) so the attribute table cannot invite the
  join, and never present an accidental agreement as a key.
- **Do not construct a qualified name you can look up.** An enterprise
  geodatabase addresses objects as `database.schema.table`, and the schema is
  the *connecting login's* - not derivable from a database name, a user name or
  anything else a script is passed. Measured in `egdb_import`: a verifier that
  defaulted the schema to the database name built
  `agsdb.agsdb.nrw_points` against a real `agsdb.sde.nrw_points` and failed with
  `ERROR 000732: Input Rows: Dataset ... does not exist or is not supported` -
  a message that names the *dataset*, so it reads as "the load failed" when the
  fault was in the path the checker built. Enumerate the workspace
  (`arcpy.ListFeatureClasses`) and match on the unqualified name instead; keep
  the explicit flags only for the one case a human must decide, the same name in
  two schemas. And when a lookup misses, print **what is there**, not only what
  was wanted - "does not exist" plus a listing is a different message from
  "does not exist".
- **"Nothing was recomputed" does not survive a database round trip, and the
  tolerance you thought was decoration is load-bearing.** Measured in
  `egdb_import`: a pipeline that projects nothing, converts nothing and rounds
  nothing - the double parsed from the CSV is the double handed to `SHAPE@XY` -
  reads back out of a PostgreSQL enterprise geodatabase differing by up to
  **8.53e-14 degrees, about 9.5 nanometres**, roughly 12 ULP of the stored
  latitude. A geodatabase quantises geometry to the coordinate grid its spatial
  reference defines, and arcpy converts between the stored form and a Python
  tuple; which of the two accounts for it was not established, and saying so is
  cheaper than picking one. Consequences: keep the provenance claim but state
  its boundary - nothing was recomputed *on the way in* - and **do not tighten
  the tolerance to the measured value**, which is the rounding-margin mistake
  from section 10 in a new costume. Note the symmetry with that finding: 1.9 nm
  there from libm not being standardised to the last bit, 9.5 nm here from a
  database storing a number. Neither involved any code doing arithmetic, both
  are invisible, and both are fatal to an exact-equality check.
- **A UI that offers the same label twice offers you the wrong one.** ArcGIS
  Pro's share pane has a check box called **Feature** under *Copy all data* and
  another called **Feature** under *Reference registered data*; for an
  OpenSearch layer only the second works, and the error names neither. When a
  documented capability fails, check whether the control you used is the control
  the documentation meant before concluding the capability is missing.
- **A deprecated form the target version understands beats the current form it
  does not - and symbology fails silently either way.** The Web Map
  Specification says of `uniqueValueInfos`: *"Deprecated. Please see
  uniqueValueGroups."* For a target of ArcGIS Enterprise 12.1 the deprecated
  form is still the right choice, because a viewer that does not understand a
  renderer does **not** fall back to the older shape - it draws the
  `defaultSymbol` for every feature, which looks like a working map with a
  broken legend. Same shape as the `geo_point` finding one layer down: the
  consumer's constraint decides the representation, not the spec's preference.
  So pin the renderer to the *target's* version, quote the deprecation sentence
  where the choice is recorded so it does not read as ignorance, and have the
  verifier read the renderer back out of the stored item - a rendering choice
  that was silently dropped has no error message anywhere. **But reading it back
  proves storage, not rendering, and the two can disagree property by
  property.** Measured in `portal_publish`: of a heatmap's three deprecated
  Gaussian properties, Enterprise 12.1 stored all three and drew by exactly one.
  Raising `blurRadius` from 12 to 25 visibly enlarged the blobs; replacing
  `maxPixelIntensity` 19.28 with 38.82 and `minPixelIntensity` 0 with 9.02
  changed nothing, at the same extent and zoom, with the verifier reading the
  new values out of the live item. "Deprecated" turned out to mean **accepted**
  rather than supported. No check that reads an item back can see that
  difference - the screenshot is the only instrument that can, so capture the
  before and the after at the **same extent and zoom**; a pair of images is a
  controlled experiment and a single image is an illustration. Keeping them is a
  separate decision from taking them: measured in `portal_publish`, seven Map
  Viewer exports came to 49 MB against 1.6 MB for a typical committed
  screenshot, so the pair was read, written up and discarded, and only the one
  capture that carries an argument was committed. Write down what a discarded
  image established, and say plainly that the surviving evidence is weaker.
  **The newer form may not degrade but vanish, and the checks stay green while
  it does.** Publishing the same heatmap in the specification's *current*
  encoding (`radius`/`minDensity`/`maxDensity`) on the same 12.1 instance stored
  it intact and drew **nothing at all** - and the verifier reported **4 of 4**,
  because every check it has reads the stored item. So on this version
  "deprecated" marks the form that works and "current" the one that is merely
  accepted. Two duties follow. Encode the measurement as a check once it is
  known - the verifier now refuses the encoding that draws nothing, naming the
  publish that established it - and state plainly, wherever a folder claims its
  checks are strong, that "does this draw" is not a readable property of an
  item. A read-back verifier cannot find this class of defect; it can only
  remember it.
- **Two properties called "extent" may be in two different units.** Measured in
  `portal_publish`: an ArcGIS *item's* `extent` property is documented as
  decimal degrees (WGS84), while a web map's own viewpoint is in the map's
  spatial reference - EPSG:3857 metres, because `targetSR` defaults to 102100.
  Handing the viewpoint's metres to the item property yields an item whose
  extent is nonsense and whose map draws perfectly, and nothing anywhere
  complains. The Gulf-of-Guinea failure one level up: same shape, same silence,
  a property instead of a geometry. Carry both numbers explicitly, name each
  key after its unit, and never let one "extent" be assigned from another
  without a conversion you can point at.
- **Documentation written into a committed payload must not reach the payload's
  destination.** An artifact in `output/` is for a reader as much as for a
  machine, so annotate it - and then strip the annotation before uploading.
  Measured in `portal_publish`: the `_note` keys explaining the design were
  being sent as part of the live web map's `text`, where the portal tolerates
  them and nobody wants them. Prefix such keys consistently, strip them by
  prefix rather than by name, and have the verifier assert their **absence**
  from what the target stored - otherwise the strip is an intention rather than
  a fact.
- **Derive every renderer threshold from the data, and say which classification
  it is.** Hard-coded class breaks look fine and quietly put every feature in
  one class the first time a seed or a source changes. Two specifics, both
  measured in `portal_publish`: a `classBreakInfo` carries `classMaxValue` and
  **no** `classMinValue` - the breaks run contiguously from the renderer's own
  `minValue`, and per-class minima are how a legend ends up with gaps that
  swallow features - and **quantile** breaks rather than equal intervals,
  because equal intervals over a normal-ish distribution put almost everything
  in the middle two classes, which looks like a rendering bug and is arithmetic.
  Print the per-class counts (measured: 101/101/98/100/100 of 500) so the
  equal-count claim is checkable rather than asserted. A `simple` renderer
  carrying one visual variable needs the variable asserted separately: without
  it, it is still a valid `simple` renderer drawing every feature at the same
  size - finished-looking and proving nothing.
- **When a failing check has nothing left to fix, move the finding rather than
  the threshold.** A verifier tuned until it goes green stops being a verifier -
  and a check that can only ever be red stops carrying information, which is the
  same loss from the other side. Measured in `portal_publish`: a hosted feature
  layer stores every declared TEXT length as 8000 and the documented way to
  change it afterwards reports success and changes nothing, so the mismatch is a
  property of the platform rather than a defect in the payload. It became an
  explicit INFO finding printed next to the API's own success claim, while the
  part of the check that *is* a claim about our work - the field **types** -
  still fails. Demote deliberately, say in the artifact that the demotion is a
  measurement, and never demote something you could still fix.
- **A renderer parameter that looks like a data value is usually in another
  unit.** Measured in `portal_publish`: a heatmap's `maxPixelIntensity` was set
  to the 95th percentile of the weighting column, 19.28 EUR/m2, as though a
  pixel intensity were a rent. It is the sum of the kernel-weighted
  contributions of the points near a pixel, so the two share no unit and only
  happen to be the same order of magnitude - which is exactly what makes it
  survive review. The arithmetic that makes it fatal is independent of zoom: an
  **isolated** point peaks at exactly its own weight, so a ceiling at or below
  the largest weight lets every lone feature reach the top colour alone. All
  500 features drew as saturated blobs, nothing in the stack reported anything,
  and the map looked like a density surface while being a dot map. Third of
  that shape here after the Gulf of Guinea and the two "extent" properties. So
  derive such a parameter by **simulating** what the client will compute -
  kernel over a pixel grid at a reference resolution taken from the map's own
  extent, ramp anchored on percentiles of the occupied pixels - and have the
  verifier assert the ceiling sits clear of the largest single weight. State
  what the simulation assumes: the vendor publishes no kernel shape, and the
  deprecated Gaussian form has no `referenceScale`, so the calibration holds at
  one scale only.
- **Ask what a renderer can express before tuning it.** Calibration was
  necessary and not sufficient in the same case. A field-weighted heatmap draws
  density x weight, so it cannot separate "many features" from "high-valued
  features": measured, its intensity correlates with plain point density at
  rho 0.774 and with the local value level at 0.786 - both, about equally, and
  a viewer has no way to tell which one a red patch means. The data's own
  structure was dramatic (district medians 17.86 down to 6.61) and invisible in
  that renderer. Measure that correlation rather than arguing about it, and when
  it comes out like that, answer the question with a second renderer on the same
  column instead of a better-tuned first one - the pair is more honest than
  either alone, and the comparison is the finding.
- **A declared field length is a request, not a contract - and which it is
  depends on the target.** Measured in `portal_publish`: a hosted feature layer
  published from CSV with an explicit `layerInfo.fields` stored every declared
  `TEXT(80)`/`TEXT(40)` column as `TEXT(8000)`. The types survived exactly; the
  lengths were discarded without a warning, while the portal's own `analyze`
  guess agreed with the declaration in 0 of 14 fields - guess right,
  declaration right, stored schema matching neither. The contrast is the point:
  `egdb_import`'s geodatabase honoured every declared length. So verify the
  stored schema field by field against the declaration rather than against the
  guess, keep the check red when it fails, and where the vendor's reference says
  only *"not all of these properties may be updated"* without saying which, ask
  the instance and record the answer - a refusal is as much a finding as a
  success.

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
  set it. **Every shell in the chain gets its own turn at this.**
  Measured again in `egdb_import`: the runbook was first written in `cmd.exe`
  syntax and handed to PowerShell, where `set VAR=x` sets nothing, `%VAR%`
  expands to nothing, and a string in a variable is data rather than a command
  until the call operator `&` is put in front of it - so the first three
  commands failed for three different reasons, none of them the tool's. And
  PowerShell has the same credential trap as cmd with the characters reversed:
  it interpolates inside **double** quotes, so `$env:PWD_VAR = "a$bc"` silently
  loses `$bc`. Use single quotes for a credential, and check
  `$env:VAR.Length` against what was typed before blaming the server for a 401.
  When a runbook targets Windows, say which shell it is written for in the first
  line - the two share no syntax for variables, quoting or line continuation,
  and a mixed one fails in a way that looks like the program is broken. **And do not
  put a bare call operator in a copy-pasteable command.** `& $tool args` is the
  correct PowerShell form, and the `&` is one leading character that reads as
  decoration; dropped while copying, it turns into
  `Unexpected token '-c' in expression or statement`, which names the flag and
  not the missing operator. Measured: it was dropped on the first attempt.
  Define the tool once as a function - `function tool { & "C:\...\tool.bat"
  @args }` - so every later command is a bare `tool ...` with no shell-specific
  punctuation to lose. The general rule: when a command's correctness depends on
  a single easily-lost character, move that character into a definition rather
  than repeating it in every step.

- **Check what an API wrote, not whether it threw.** An interface that cannot
  reach your target may still hand you a path and a success. Measured in
  `egdb_import`, where the API the request named was run four times with nothing
  changed but what was importable: it raised; it raised the *same* message with
  the library the message recommends installed, because the message names
  shapely and the code checks pyshp; it wrote three files and then died inside
  the library; and it succeeded silently and wrote a **shapefile** where a
  feature class was asked for. The silent success truncated four of ten field
  names to the DBF limit of ten characters and replaced both measured TEXT
  lengths with the format's maximum. So assert the format, the field names and
  the field types of what actually landed - the return value is not the
  deliverable. **A success message is not a write, either.** Measured in
  `portal_publish`: `updateDefinition`, asked to set three declared TEXT
  lengths on a hosted feature layer, answered `{"success": true}` - and the
  service still reports the old lengths afterwards. The vendor's own reference
  says only *"When updating field properties, note that not all of these
  properties may be updated"* without saying which, so there was nothing to read
  that would have predicted it. Read the property back from the target after
  every write you care about, and when a confirmation and a measurement
  disagree, publish both rather than the one that reads better.
- **A convenience writer that infers a schema is not an importer.** Where field
  types and lengths *are* the deliverable, state them explicitly.
  `to_featureclass` accepts `location, overwrite, has_z, has_m,
  sanitize_columns` - no type, no length, no alias - and Esri publishes no dtype
  mapping table, so the schema becomes whatever pandas guessed. Prefer the
  verbose route (`CreateFeatureclass` + `AddField` per field) and let the
  measurement decide the length.
- **Say when a use case cannot isolate its dependencies, and why.** arcpy is not
  installable from PyPI; it exists only inside ArcGIS Pro's bundled
  `arcgispro-py3` conda environment, invoked through `propy.bat`. So
  `egdb_import` has no venv for its loader - the environment *is* the licence.
  Keep the half that does not need it stdlib-only on purpose, so the analysis is
  not held hostage to the licence, and pin a `requirements.txt` only for what
  genuinely comes from PyPI. Every pin gets its reason: `pyshp` is held at 2.x
  there because `arcgis` 2.4.1.1 calls it with a keyword 3.x removed, and
  `setuptools` is pinned because Python 3.12 dropped `distutils` and the
  library still imports it.
- **Split a pipeline where the licence boundary is, not where the code is
  convenient.** Measured in `egdb_import`: the decisions (which fields, which
  types, which CRS) went into a reviewable JSON contract produced by
  stdlib-only code, and the half that needs Windows, a licence and a database
  became a transcription of a document somebody had already read. A `--dry-run`
  that also *rehearses* the work - coercing every row to its declared type
  without importing the licensed library - caught three planted defects with no
  database in sight. A dry run that only prints calls is worth much less.
- **A pinned client library may be missing the module its own migration notes
  name. Ask the wheel, not the release notes.** Measured in `portal_publish`:
  the widely-repeated note *"in 2.4, `arcgis.mapping.WebMap` became
  `arcgis.map.Map`"* is half true for `arcgis` 2.4.1.1 - the old class is gone
  and the new one is **not in the wheel**. `import arcgis.map` raises
  `ModuleNotFoundError`, `from arcgis.mapping import WebMap` raises
  `ImportError`, and `grep -c '^arcgis/map/' …dist-info/RECORD` returns **0**.
  The `RECORD` file is the authoritative inventory of what was actually
  installed, and it answers in one command a question release notes and
  migration guides answer wrongly. Consequence for the design rather than just
  for the import: hand-built JSON handed to `content.add` is then **the only
  route, not a workaround**, and saying so is the difference between a decision
  and an apology.
- **Where a vendor publishes no specification, the vendor's own code is a better
  oracle than the vendor's documentation - including deprecated code.** There is
  no published ArcGIS Dashboard specification, and that absence is itself worth a
  paragraph. What exists is `arcgis/apps/dashboard/dashboard.py`, deprecated and
  shipped in the wheel: it establishes that the item type is exactly
  `"Dashboard"` with the config in `text`, and it emits `version 27` with no
  `mapWidget` - so it cannot build the widget such a dashboard needs most, and
  remains a first-party reference for the shapes of the ones it can. Cheaper
  still where an instance is available: configure one by hand, pull its JSON
  with `get_data()`, commit it as the reference and build against that. Ground
  truth from the exact instance beats any amount of doc-reading where no spec
  exists.
- **A check that greps a serialised payload as text will catch the payload's own
  documentation.** See section 3 on placeholder markers for the measurement. The
  general rule: a textual assertion has no idea which occurrences are data and
  which are prose, so keep the pattern out of the prose rather than narrowing
  the pattern. Narrowing it is how the real failure gets through.

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
speaking. The repository grows; the slot does not. `slides/` is therefore
**two slides per use case** — an *idea* slide (why this use case exists, and its
workflow in three steps) and a *result* slide (one screenshot, exactly **one**
finding) — plus an opening, an overview, two takeaway slides and a close.

**Splitting a dense slide into two sparse ones costs no speaking time.** It is
the same words with half of them off screen while the other half is being said.
Measured here: ten slides became seventeen at an unchanged budget, and the thing
that fitted into the new space was the part that had been missing — *why* a use
case exists. `egdb_import`'s reason is not a number, it is the sentence "this is
where we really need test data", and it had nowhere to go while the slide was
also carrying a result. When a slide feels tight, add a slide before cutting a
sentence.

**Pick the shape of the talk before writing a slide, and know that the slot
decides it.** Measured here: the first deck was four named rules with the use
cases as evidence for them, and it read as a talk about how much goes wrong. The
rebuild is the same repository and the same measurements with the use cases as
the subject and one finding each as the closing line — and it answers the
question the audience arrived with, which was *what can I do with this*. Twelve
minutes is enough for five things told once or one thing told five ways; that
choice is not a formatting detail.

**The abstract is a consumer; check the deck against it.** A conference talk is
submitted months before it exists, so the deck and the abstract drift apart
silently. Reading them against each other, sentence by sentence, is the same
move as checking data against its target - and measured here it found three gaps
in a deck that already looked finished: the abstract promised a CSV *for a
hosted feature service* and the deck never named the target, promised a view
layer *in ArcGIS Pro* from *a GeoJSON* and the deck mentioned neither, and named
*Claude Code* where the deck named no tool at all. Note also which way the
promise runs: an abstract selling *how easy it is* against a repository whose
instinct is to lead with what went wrong. Resolve that by **order** - the result
first, the finding as the closing line - not by hiding either one.

**And state the motivation the speaker actually has.** The first two drafts
opened on *"I am not allowed to use real data"*, which is true and is not the
reason. The reason is that a product has to work with **any** customer's data,
so what a test needs is the *structure* — schema, coordinate system, volume —
and the structure can be made. Data protection is then a consequence, not the
argument. Get this wrong and every use case afterwards reads as a workaround
rather than as a capability.

**Say how the work was made, once, at the front.** A deck built by an agent
needs one slide stating that: the tool, that every prompt is logged verbatim,
where the effort actually went (verifying, not generating), and what ran locally
versus what left the machine. It costs 40 seconds, it is the honest version of
the claim the rest of the talk makes, and without it the audience spends the
first use case wondering rather than listening.

**Write the deck for the speaker, not for the reader.** The talk is given in a
non-native language. Words that need a moment of thought on stage (*prose*,
*triage*, *yardstick*) were removed even where they were the better word, and a
number that has to be explained before it means anything was cut — a quantile
class count is a fine README fact and dead weight on a slide. Keep a number only
where the number *is* the point.

**Do not write a backup section.** The first deck had fifteen written-out
backup slides and a documented rule for which finding may displace which. It was
an elaborate way of refusing to cut, it cost real maintenance, and nobody ever
saw a slide of it. Findings belong in the use-case README, which is where a
question during Q&A gets answered properly anyway. Never leave a finding
undocumented because it did not fit the deck — but the deck is not where it goes.

**Verify a deck the way you verify data: against its consumer.** A green Slidev
build says nothing about whether a slide is readable. Render the slides to PNG
(`npm install --no-save playwright-chromium`, then
`slidev export --format png`) and look at every one. Measured twice, on two
different decks. First draft: two slides overflowing past the bottom edge with
the punchline cut off, and Slidev's `two-cols-header` layout running a long left
column underneath the image in the right column — prefer an explicit CSS grid
over that layout. Rebuild: **all five** use-case slides shipped with the finding
box running off the bottom edge, cut off mid-sentence, because a repeated layout
repeats its defect five times and the build reports success five times. A
recurring slide template is the one most worth exporting, not the least.

**And the worst of them was a licence violation caused by a unit.** Rebuilding
the result slides around a large screenshot, the image was capped with
`max-height: 56vh` — and Slidev scales the whole slide with a CSS transform, so
a viewport unit inside a slide is not a fraction of that slide. The image
rendered far past the bottom edge and **cropped the basemap attribution off**,
which is exactly the thing §3 says must never happen, on a build that reported
success. Cap image height in **pixels** against Slidev's 980 × 552 canvas, never
in `vh`. Note the shape: the rule was known, written down and still broken,
because it was broken by a unit conversion rather than by a decision — the same
family as the two "extent" properties in §4.

**A trademark in a CC BY repository needs a written carve-out, and it should be
exactly one file.** A logo is the one asset that cannot be reconstructed -
imitating it *is* the infringement - so where it is genuinely wanted it goes in
as itself, and the licence section then has to say plainly that it is not CC BY,
because a content licence cannot hand on somebody's mark. Measured here: with the
palette, the typography and both decorative graphics rebuilt from the theme
rather than extracted, the carve-out is a single PNG and the sentence "remove
this one file" is enough for a reuser. Had the template's own graphics been
lifted, the carve-out would have been a list nobody could act on.

**Imitating a corporate slide master: take the scheme, never the file.** A
company `.potx` is a template somebody else owns, and this repository publishes
under CC BY - so the template is gitignored and none of its images are used.
What does cross over is what a theme actually is: the colour scheme and the
typography, both readable straight out of the package (`.potx` is a zip;
`ppt/theme/theme1.xml` holds the scheme, `ppt/slideMasters/slideMaster1.xml` the
title and body text styles, and `ppt/slideLayouts/*.xml` carry their German
layout names). Measured here: the master sets *body* copy in the same dark blue
as the titles, which no eyeballed imitation would have guessed, and names Arial
as both major and minor font. Decorative motifs get redrawn from the palette
rather than extracted. And a theme layout can silently overrule the imitation:
`layout: cover` is the Slidev theme's own cover, painting its own background over
the custom one - the build succeeded, the slide rendered as a grey gradient, and
only the PNG export showed it. Fourth time that export has caught what a green
build reported as success.

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
- **Vendor documentation rots like an open-data portal, so record the
  verification status next to the claim.** Measured in `egdb_import`: the
  version-pinned `enterprise.arcgis.com/.../12.1/...` page for the PostgreSQL
  requirements did not resolve at all - 12.0 was the highest that did - and
  several `pro.arcgis.com/.../latest/...` URLs 301-redirect to `doc.esri.com`
  mid-migration. A requirements manifest therefore carries, per claim, the URL,
  the retrieval date, the quoted sentence and an explicit **VERIFIED /
  UNVERIFIED** marker, and the tool asks the machine rather than trusting the
  file: three numbers went in as UNVERIFIED, including a package version that
  could only be inferred from the vendor's conda channel metadata and is stated
  in no release note. "The documentation says" and "the instance reports" are
  two different facts, and a manifest that cannot tell them apart is a manifest
  that will be quoted on stage.
- **State where a credential is stored, and do not take an exception you have
  not earned.** `opensearch` commits a throwaway password under the narrow
  exception below; `egdb_import` deliberately does not, because an Enterprise
  Geodatabase is a database instance with a real login rather than a folder
  deleted with `build/`. Note also what a generated connection file contains:
  ArcGIS Pro can hang opening a geodatabase from a `.sde` whose credentials were
  not saved, so the file has to be written with `SAVE_USERNAME` - which is
  exactly why it belongs in `build/` and never in `input/` or `output/`.
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
