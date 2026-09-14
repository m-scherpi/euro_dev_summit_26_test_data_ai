# Portal Publishing — a generated CSV becomes a Web Map on ArcGIS Enterprise

> **Status: stages 1–3 done and measured, offline. The portal run is open.**
> Everything that can be built without a portal is built, verified and
> committed; the two portal-facing scripts are written and rehearsed but have
> not yet met a real Enterprise Portal. Part of
> [Test (Geo-)Data Generation with GenAI](../README.md).

## Purpose

A fictional rent-price census for Münster — 500 generated points carrying rent
per square metre, median age, building type and living area — published to an
ArcGIS **Enterprise** Portal as a **Hosted Feature Layer**, and from there into
a **Web Map with five operational layers on that one layer**, each with its own
generated renderer:

```
seeded generator → CSV → Hosted Feature Layer → Web Map (5 layers, 4 renderer types)
```

This is the one use case in the repository whose subject is not the data. The
other four stop at the data layer; this one asks how far into the platform
generated content can reach — item, service, schema, symbology, map. The data is
fictitious by construction, which is the point: it is the data set nobody is
allowed to have.

The verification depth was **agreed up front** rather than defaulted to
(CLAUDE.md §12): breadth over rigour. Two offline checks and four against the
portal, not the twelve-check apparatus of `opensearch` — because nothing here is
real, so there is no source row to trace a coordinate back to and no licence to
defend. What *is* checked is what the platform did to a payload this repository
wrote. The four deliberate omissions are listed under
[Verification](#deliberately-not-checked), each with its sentence.

## The inversion

Two findings this repository made elsewhere are inverted here on purpose. Both
are stated so the repository does not read as though it contradicts itself.

| Elsewhere | Here |
|---|---|
| `opensearch` publishes a web feature layer that **references** registered data and copies nothing — that was the whole point of the folder. | **Copy all data.** The rows end up in the ArcGIS Data Store, and the CSV item that fed them is a separate item beside the service. |
| `egdb_import` **refused** `GIS.content.import_data()` *because* it copies rows out of a database into a hosted layer instead of writing to the database. | That copy is the deliverable. Same measurement, opposite verdict — the measurement was never wrong, the goal changed. |

`import_data()` is still not used, and now for reasons that are about the method
rather than the destination: it takes a DataFrame, it offers no control over
field types, and its documentation states a 1,000-row cap. `Item.publish()` with
explicit `publishParameters` is the route that lets the schema be *declared*.
`publish(overwrite=True)` is not used either — it is documented as incompatible
with `publish_parameters`, so overwriting would silently mean giving up the
declaration.

## There is no Web Map class

Measured before a line of code was written, and reproduced again in this use
case's own virtualenv:

```bash
build/venv_api/bin/python -c "import arcgis.map"
# ModuleNotFoundError: No module named 'arcgis.map'
build/venv_api/bin/python -c "from arcgis.mapping import WebMap"
# ImportError: cannot import name 'WebMap' from 'arcgis.mapping'
grep -c '^arcgis/map/' build/venv_api/lib/python3.12/site-packages/arcgis-2.4.1.1.dist-info/RECORD
# 0
```

`arcgis` 2.4.1.1 has **no Web Map class at all**. The widely-repeated migration
note — "in 2.4, `arcgis.mapping.WebMap` became `arcgis.map.Map`" — is half true:
the old class is gone and the new one is not in the wheel. `arcgis.mapping`
survives as a layer-class module (32 entries in `RECORD`: `MapImageLayer`,
`MapFeatureLayer`, `VectorTileLayer`, the scene layers) and exports no map.

So hand-built Web Map JSON handed to `content.add({"type": "Web Map", "text":
…})` is **not a workaround, it is the only route** — which independently
justifies the offline/portal split below. The lesson generalises past this
library: a pinned client may be missing the module its own migration notes name,
and the wheel's `RECORD` answers that question while the release notes do not.

## Coordinate reference systems

Two codes, and both are named because the pipeline changes one into the other:

- The CSV is **EPSG:4326** decimal degrees, five decimals (~1.1 m), with
  `latitude` before `longitude` per CLAUDE.md §4. It also carries `x_3857` /
  `y_3857`, derived from the *rounded* degrees.
- The hosted feature layer stores **EPSG:3857 metres**, because
  `publishParameters.targetSR` defaults to WKID 102100 — the deprecated Esri
  code for the same auxiliary sphere that `latestWkid` calls 3857. Both are
  stated explicitly in `publish_parameters.json` rather than left to the
  default, so the CRS change is a decision and not a surprise.

The consequence is load-bearing for the extent check: `verify_portal.py` reads
the layer's own reported spatial reference, projects the expected box from
degrees into the unit the layer actually stores, and **prints both bounds**. It
refuses outright if the layer reports a CRS it cannot express the box in. That
refusal is the `egdb_import` finding turned into code — a feature class created
as EPSG:3857 and fed decimal degrees accepts every row and puts all hundred
points within 52 metres of 0°N 0°E in the Gulf of Guinea, with no exception
anywhere in the chain.

## Why there is no boundary here

`csv_data` rejection-samples against a Germany polygon and `open_data_search`
adjudicates single stations against an authoritative NRW outline. This use case
deliberately does neither. There is no boundary, and
`input/muenster_districts.json` carries `"authoritative": false` in its second
line.

The reason is that the district centres were **typed in**, not extracted: eight
approximate points chosen so a Gaussian scatter produces visible spatial
structure. They are not a copy of anybody's data set, so they carry no licence
obligation and make no claim. Using the city's real Stadtteil geometry would
have made the fixture better-looking and the data set worse — a fictional census
snapped to real boundaries invites exactly the reading it must not have.

What replaces the polygon is a bounding box the generator *guarantees* by
rejection rather than hopes for: the centres sit four sigma clear of every edge,
and the generator prints the rejection count (**0 of 500 candidates** on the
committed run) so the guarantee is measured rather than asserted.

## Stack

Python 3.12, and the split is the design:

- **Stages 1–3 are standard library only.** No virtualenv, no install step, no
  licence, no credentials. The three JSON documents that reach ArcGIS
  Enterprise are built, reviewed and diffed with no portal in the room.
- **Stages 4–5 need `arcgis` 2.4.1.1** in a local venv (`requirements.txt`,
  one reason per pin). `publish_to_portal.py` imports it **lazily**, inside the
  function that connects, so `--dry-run` runs under a bare `python3`.

This is the same boundary `egdb_import` drew between its stdlib schema contract
and its arcpy loader, and it holds better here: there, the artifact was a *plan*
of what the licensed half would do. Here it is the **payload**. Everything worth
reviewing — which field is a Double, how many class breaks, which renderer on
which layer, what the popup shows — is a committed artifact rather than a
decision buried in a script that only runs on somebody else's machine.

`pyshp` is deliberately **not** pinned, unlike in `egdb_import`: it is only
needed by the shapefile writer inside `arcgis.features.GeoAccessor`, and nothing
here writes a local feature class. An inherited pin whose reason no longer
applies is how a requirements file stops being reviewable.

## Input

`input/` — read-only source data.

| File | Description |
|---|---|
| `implementation_plan.md` | the reviewed plan for this use case, incl. the measured API findings it rests on. Corrections to it live in this README — the delta is the talk material |
| `muenster_districts.json` | eight approximate district centres, per-district sigma and weight, and the sampling bounding box. `"authoritative": false`, stated in the file |
| `rent_census_fixtures.json` | five building types with their own year and area ranges, street-name parts, per-district rent/age/household levels, and the value guards. Every number in it is invented |
| `portal_connection.example.json` | connection template. **No password field**, and the file explains why |

## Output

`output/` — generated artifacts only, always reproducible from `input/` plus the
documented command. Safe to delete entirely.

| File | Size | Description |
|---|---|---|
| `muenster_rent_census.csv` | 55 KB | 500 census points, 14 columns. SHA-256 `f170410f8bd6c3ca01268d06e6e0cc44d5d84ec191961620e68ed7b52f73e1e4` |
| `verification_report_coordinates.md` | 3 KB | the two offline checks, 2/2 green |
| `publish_parameters.json` | 3.7 KB | **what we declare**: a type per column, `locationType: coordinates`, both spatial references named |
| `layer_definition.json` | 7.3 KB | the one service-level renderer (rent class breaks), the field-length retrofit body sent only with `--retrofit-field-lengths`, plus the declared fields as a reference copy that is never sent |
| `webmap.json` | 39 KB | the complete Web Map: five operational layers on one service, four renderer types, popups, basemap. Placeholder-tokenised. Its top-level `_note` and `_item` keys are documentation for a reader and are **stripped before upload** — `verify_portal.py` asserts their absence from the stored item |
| `analyze_publish_parameters.json` | 4.9 KB | **what the portal guessed.** Written verbatim by the real `publish` stage |
| `verification_report_portal.md` | 6 KB | the four portal checks, host redacted. The committed copy is the 4/4 run whose heatmap layer drew nothing — kept as evidence |

**Why the web map carries placeholders.** `webmap.json` contains
`{{FEATURE_SERVICE_URL}}` and `{{FEATURE_LAYER_ITEM_ID}}` rather than real
values, because a portal item id does not exist until the item is created and
changes on every run. Writing one into `output/` would break the rule that the
folder is regenerable from `input/` plus the documented command, and would churn
a committed artifact on every demo. Substituted bodies go to `build/`.

The tokens are load-bearing, not cosmetic: an unsubstituted token yields a web
map that **loads** — the portal accepts the item, the viewer opens it, the frame
draws, the legend lists five layers, and not one feature appears. No error
anywhere. So `publish_to_portal.py` asserts that no double-brace marker survives
before any `content.add`, and aborts rather than warns.

The implementation plan named *three* tokens; there are two. `{{PORTAL_URL}}`
was planned and turned out to have no use — the basemap is referenced by service
URL and nothing else in the payload needs the portal's own address. Recorded
rather than quietly dropped.

## Credentials

The password comes from `$PORTAL_PASSWORD` or `--password`. It has no default,
is committed nowhere, and appears in no log line — every script prints the
literal `<PORTAL_PASSWORD>` instead, as a constant rather than a `.replace()` at
print time.

CLAUDE.md §10 grants one narrow exception for a committed credential: a local
throwaway service holding nothing but public open data and deleted with its
`build/` folder. `opensearch` takes that exception. **This use case deliberately
does not**, and the reason is arithmetic rather than caution: an ArcGIS
Enterprise Portal is a real system with a real named account, its items outlive
any `build/` folder, and the same login usually reaches a federated server and a
data store. Nothing here is throwaway.

Two further notes, both inherited from `opensearch` and both about consumers
rather than about us:

- **A literal `localhost` in `--portal` is resolved by the federated server on
  its own machine**, not on yours. Use the host name the certificate names.
- **"The consumer" is a list — and `requests` and `arcgis` are two entries on it
  inside one process.** `--ca-cert` was first implemented as
  `REQUESTS_CA_BUNDLE`, set before the import, with a comment asserting that the
  order of those two lines was the thing that mattered. It does not work, and
  the correction is the finding: `arcgis` 2.4.1.1 mounts an
  `EsriTrustStoreAdapter` whose `init_poolmanager` hands urllib3 its **own**
  `ssl.SSLContext` — a `truststore.SSLContext` loaded with `certifi.where()` —
  and a connection built from an explicit context never consults requests'
  `verify`, so the variable is read by nothing. Measured in one interpreter:

  ```
  requests.get(portal_url)   with REQUESTS_CA_BUNDLE set  ->  200
  GIS(portal_url)            same process, same variable   ->  CERTIFICATE_VERIFY_FAILED
  ```

  The supported route is `GIS(ca_bundles=...)`, documented in the class's own
  docstring **in the wheel** — *"Users can pass verify_cert a path to a
  CA_BUNDLE file or directory with certificates of trusted CAs as well. This
  will use these certificates over the system's certificates."* Both scripts now
  pass it, and `--ca-cert` works. The `arcgis.map` lesson again: ask the wheel,
  not the notes.

  That satisfies this Python client and says nothing about ArcGIS Pro (Current
  User store), an ArcGIS Server service (Local Computer store) or that server's
  JVM (its own `cacerts`). Five consumers of one private CA now, five
  mechanisms, and each fix only makes the next failure observable.
- **Building the bundle: take the anchor from the chain, not from a colleague.**
  The server sends its own certificate plus the issuing CA and stops there, so
  `certifi` cannot close the chain and `requests` reports
  `unable to get local issuer certificate` — which reads like a server fault and
  is not one. The issuing certificate's *Authority Information Access* extension
  names the root, so the bundle can be assembled from the connection itself:

  ```bash
  openssl s_client -connect <host>:443 -showcerts </dev/null 2>/dev/null \
      | awk '/BEGIN CERT/,/END CERT/' > build/chain.pem
  awk '/BEGIN CERT/{n++} n==2' build/chain.pem > build/issuing_ca.pem
  openssl x509 -in build/issuing_ca.pem -noout -text | grep -A2 'Authority Information Access'
  curl -sS -o build/root_ca.crt <the CA Issuers URI printed above>
  openssl x509 -in build/root_ca.crt -inform DER -out build/root_ca.pem
  cat build/root_ca.pem build/issuing_ca.pem > build/ca_bundle.pem  # --ca-cert points here
  openssl s_client -connect <host>:443 -CAfile build/ca_bundle.pem </dev/null 2>&1 \
      | grep 'Verify return code'   # must print 0 (ok)
  ```

  Two things worth stating. The bundle belongs in `build/` — it is fetched, not
  authored, and a copy in `input/` would rot with the next CA rotation. And the
  issuing certificate alone would also verify (OpenSSL stops at any anchor it is
  handed), which is a weaker claim than anchoring on the root: prefer the root,
  and verify before believing the download.

## Setup

Stages 1–3 need nothing at all:

```bash
cd portal_publish
python3 --version   # 3.10+
```

Stages 4–5 need a local virtualenv:

```bash
cd portal_publish
python3 -m venv build/venv_api
build/venv_api/bin/pip install -r requirements.txt
build/venv_api/bin/python -c "import arcgis; print(arcgis.__version__)"   # 2.4.1.1
```

## Usage

### 1. Generate the census (stdlib)

```bash
cd portal_publish
python3 scripts/generate_census.py --count 500 --seed 20260904 \
    --districts input/muenster_districts.json \
    --fixtures  input/rent_census_fixtures.json \
    --output    output/muenster_rent_census.csv
```

### 2. Verify the coordinates (stdlib)

```bash
python3 scripts/verify_census.py \
    --input     output/muenster_rent_census.csv \
    --districts input/muenster_districts.json \
    --report    output/verification_report_coordinates.md
```

### 3. Build the portal payloads (stdlib)

```bash
python3 scripts/build_portal_items.py \
    --input        output/muenster_rent_census.csv \
    --service-name muenster_rent_census \
    --output-dir   output/
```

### 4. Rehearse the publish — no portal, no `arcgis`

```bash
python3 scripts/publish_to_portal.py --dry-run \
    --csv output/muenster_rent_census.csv --items-dir output/ \
    --plan build/publish_plan.md
```

### 5. Publish, for real

```bash
export PORTAL_PASSWORD=...
build/venv_api/bin/python scripts/publish_to_portal.py \
    --portal https://portal.example.com/portal --user devsummit \
    --csv output/muenster_rent_census.csv --items-dir output/ \
    --stage all --recreate --run-record build/portal_run.json
```

Stages are cumulative and each leaves a working deliverable:
`--stage csv|publish|layerdef|webmap|all`. Sharing defaults to **PRIVATE**;
`--share ORGANIZATION` or `--share EVERYONE` widens it deliberately.
`--retrofit-field-lengths` adds the field-length experiment described under
[Verification](#the-declaration-was-accepted-and-its-lengths-discarded).

**A portal behind a private CA.** Both portal-facing scripts take `--ca-cert`,
which sets `REQUESTS_CA_BUNDLE` *before* `arcgis` is imported — the only order
that works, because the library builds its session at import time. Build the
bundle from the connection itself with the recipe under
[Credentials](#credentials); prefer it over
`--no-verify-cert`, which silences the question rather than answering it.

### 6. Verify what the portal stored

```bash
build/venv_api/bin/python scripts/verify_portal.py \
    --portal https://portal.example.com/portal --user devsummit \
    --ca-cert build/ca_bundle.pem \
    --run-record build/portal_run.json \
    --report output/verification_report_portal.md
```

Then open the web map in the portal's Map Viewer, switch through the five
layers, and capture one screenshot with the basemap attribution intact.

### Running it twice — idempotency

A live demo runs more than once, so every item created carries the fixed tag
`devsummit-portal-publish` and `--recreate` deletes this use case's own items
before publishing. Three details in that path are deliberate:

- **Deletion order is Web Map → Feature Service → CSV.** The feature service
  holds a `Service2Data` relationship back to the CSV item and the publish path
  reads it; deleting the CSV first can leave that dangling.
- **`Item.delete(dry_run=True)` runs first** and its answer is logged. That is
  the API asking the portal whether anything depends on the item, and a blocked
  deletion deserves a line in the record rather than an exception mid-demo.
- **`content.search` is called with an explicit `max_items`.** The default is
  10, which is a silent truncation — after three demo runs `--recreate` would
  quietly leave items behind.

And one thing `--recreate` cannot promise: `permanent=True` is documented as
ArcGIS Online only, so on Enterprise a deleted item may keep its service name.
`is_service_name_available()` is therefore asked separately afterwards, and it
can legitimately say *no* right after a successful delete —
`publish_to_portal.py` aborts with that sentence rather than a traceback.

## Example output

`output/muenster_rent_census.csv`, first two rows:

```
id,address,district,latitude,longitude,x_3857,y_3857,rent_eur_sqm,living_area_sqm,rooms,median_age,household_size,building_type,year_built
1,Bohlwegweg 126,Altstadt,51.95691,7.63253,849649.3531,6792337.9765,15.82,70.9,3,39.8,1.4,Altbau,1887
2,Muhlenallee 176,Gievenbeck,51.96846,7.60944,847078.9860,6794424.6257,15.30,127.9,5,22.4,1.2,Altbau,1914
```

What the generator reported on the committed run:

```
rng fingerprint (seed 20260904): bb6a8bb4aed5d45a
wrote output/muenster_rent_census.csv | 500 rows, 54.5 KB | seed 20260904
sha256: f170410f8bd6c3ca01268d06e6e0cc44d5d84ec191961620e68ed7b52f73e1e4
rounding margin: worst 96.0 ULP over 4,500 rounded values (threshold 16)
positions: 0 of 500 candidates rejected outside the box | 500 unique addresses
per district: altstadt=60, berg_fidel=62, coerde=48, gievenbeck=68,
              gremmendorf=48, hansaviertel=70, kreuzviertel=91, mauritz=53
per building type: Altbau=118, Nachkriegsbau=145, Neubau=94, Plattenbau=84,
                   Reihenhaus=59
clamped values: living_area_sqm=2, median_age=2, rent_eur_sqm=2
```

### Schema

| Column | Declared Esri type | Note |
|---|---|---|
| `id` | `esriFieldTypeInteger` | 1…500 |
| `address` | `esriFieldTypeString(80)` | longest generated value: 24 characters |
| `district` | `esriFieldTypeString(40)` | longest: 12 |
| `latitude`, `longitude` | `esriFieldTypeDouble` | EPSG:4326, 5 decimals |
| `x_3857`, `y_3857` | `esriFieldTypeDouble` | EPSG:3857 metres, 4 decimals |
| `rent_eur_sqm` | `esriFieldTypeDouble` | heatmap **and** class-breaks field — rendered twice on purpose |
| `living_area_sqm` | `esriFieldTypeDouble` | `sizeInfo` field |
| `rooms` | `esriFieldTypeInteger` | derived from area, not drawn independently |
| `median_age` | `esriFieldTypeDouble` | the second class-breaks field |
| `household_size` | `esriFieldTypeDouble` | popup only, on purpose |
| `building_type` | `esriFieldTypeString(40)` | `uniqueValue` field; longest: 13 |
| `year_built` | `esriFieldTypeInteger` | drawn inside its building type's own range |

**Everything decimal is `Double`, never `Single`** — including `rent_eur_sqm`,
which would fit. A 32-bit float carries about seven significant decimal digits; a
latitude of 51.96253 needs seven and an EPSG:3857 metre value like 849649.3531
needs ten. The rounding is silent and the result is a plausible coordinate in the
wrong place, and stating "which decimals were special" is worse documentation
than making them all the same.

**`columnNames` is omitted**, because `layerInfo.fields` overrides it. Sending
both would leave a reader guessing which one the portal used — and that omission
is the hook that turns a guess into a declaration.

### The five layers, four renderer types

All five operational layers carry the **same** `url` and the **same** `itemId`
and differ only in `layerDefinition.drawingInfo`. That is the architecture in one
sentence: one copy of the data in the ArcGIS Data Store, five ways of reading it.

| Layer id | Renderer | Field | Derived from the data |
|---|---|---|---|
| `rent_heatmap` | `heatmap` | `rent_eur_sqm` | `minPixelIntensity` **9.02** (p75), `maxPixelIntensity` **38.82** (p99) of the simulated pixel intensities, `blurRadius` 25 px |
| `rent_breaks` | `classBreaks` | `rent_eur_sqm` | quantile breaks ≤8.4, ≤11.1, ≤13.7, ≤16.7, ≤23 €/m² — **98 / 101 / 99 / 98 / 104** features |
| `age_breaks` | `classBreaks` | `median_age` | quantile breaks ≤29.5, ≤34.6, ≤39.1, ≤44.1, ≤65 — **101 / 101 / 98 / 100 / 100** features |
| `building_type` | `uniqueValue` | `building_type` | five categories in descending frequency, counts in the legend labels |
| `area_size` | `simple` + one `sizeInfo` | `living_area_sqm` | `minDataValue` 24.0, `maxDataValue` 170.6 m² |

Every threshold is measured from the CSV rather than typed in. A renderer with
hard-coded breaks looks fine and quietly puts every feature in one class the
first time the seed changes.

**`rent_eur_sqm` is rendered twice, and that pair is the finding.** The first
version of this map had one rent layer, the heatmap, and it answered a different
question than it appeared to — see *A heatmap is a density surface* below. The
class-breaks layer is the readable counterpart on the same column; both are
visible by default, the heatmap underneath.

Details in that JSON that are deliberate, and most of them traps:

- **`classBreakInfo` carries `classMaxValue` and no `classMinValue`.** Breaks run
  contiguously upward from the renderer's own `minValue`; adding per-class minima
  is how a legend ends up with gaps that swallow features silently.
- **Quantile breaks, not equal intervals.** Equal intervals over a normal-ish
  distribution put almost everything in the middle two classes, which looks like
  a rendering bug and is arithmetic. The per-class counts above are printed so
  the equal-count claim is checkable, and they are counted against the **rounded**
  break edges the renderer actually carries, not against the unrounded quantiles.
- **`uniqueValueInfos`, not `uniqueValueGroups`** — and the specification says of
  the former: *"Deprecated. Please see uniqueValueGroups."* The deprecated form
  is used anyway, deliberately. The target is Enterprise **12.1**, not current
  ArcGIS Online, and a renderer a 12.1 viewer does not understand does not fall
  back — it draws the `defaultSymbol` for every feature, which looks like a
  working map with a broken legend. Same reasoning as `opensearch`'s `geo_point`
  finding one layer up: the consumer's constraint decides the representation,
  not the spec's preference.
- **The heatmap's properties are deprecated too, for the same reason.** The
  specification marks `blurRadius`, `maxPixelIntensity` and `minPixelIntensity`
  deprecated — *"Only used for heatmaps calculated with Gaussian blur"* — in
  favour of the kernel-density form (`radius`, `maxDensity`, `minDensity`,
  `referenceScale`). The Gaussian form is what this 12.1 instance demonstrably
  draws, which the first capture proved, wrong calibration and all.
  The cost is real: `referenceScale` belongs to the current form, so the
  calibration below holds at one scale and fades as you zoom in.
- **The `simple` layer has exactly one visual variable.** `household_size` was the
  obvious second one and goes into the popup instead, so that layer demonstrates
  one renderer type rather than two at once. `verify_portal.py` asserts the
  `sizeInfo` separately, because a `simple` renderer whose visual variables were
  dropped is still a valid `simple` renderer drawing all 500 points at the same
  size — finished-looking and proving nothing.

Colours are chosen for colour-vision deficiency: sequential five-class ramps for
the class breaks — YlOrRd for rent, so it can be compared against the heatmap at
a glance, blue for median age — and the Okabe-Ito qualitative palette for the
categories. A renderer an audience cannot read is a renderer that proves nothing
on a projector.

### A heatmap is a density surface, and its ceiling is not in the data's unit

Two separate defects, one screenshot. The first real publish looked like this: every one of the 500 dwellings is a saturated red blob and the map says
nothing about anything.

**The unit confusion.** `maxPixelIntensity` was set to the 95th percentile of
`rent_eur_sqm`, **19.28 €/m²**. A pixel's intensity is not a rent — it is the sum
of the kernel-weighted contributions of the points near it, and the two share no
unit. The arithmetic that makes it fatal is independent of zoom: the peak
intensity of an **isolated** point is exactly its own weight. Rents run to
**22.75**, so every lone dwelling reached 100 % of the colour ramp by itself and
overlap could add nothing on top. Nothing errored; the map drew; it was a dot map
rendered expensively. The colour ramp made it worse by reaching alpha 140 at
ratio 0.01 and its second colour at 0.40.

The ceiling is now **measured**. `heatmap_calibration()` evaluates a Gaussian
kernel over a pixel grid at a reference resolution derived from the map's own
extent (**13.25 m/px** at a 1280 px window, σ = **110 m**) and anchors the ramp on
percentiles of the occupied pixels: floor at p75 = **9.02**, ceiling at p99 =
**38.82**. A lone point at the maximum rent reaches 46 % of that ramp; the top
colour requires overlap. Esri does not publish the kernel's shape, so a Gaussian
truncated at 3σ is an *assumption* and the calibration approximates the client's
arithmetic rather than reproducing it.

**And then the instance did not draw by those numbers.** The second publish, at
the same extent and the same zoom as the first, was still saturated and if
anything redder. The verifier reads `blurRadius 25`,
`minPixelIntensity 9.02`, `maxPixelIntensity 38.82` back out of the live web map,
so the payload arrived intact. Comparing the two captures separates which
property did what:

| Property | Before | After | Effect on the drawn map |
|---|---|---|---|
| `blurRadius` | 12 | 25 | **visible** — the blobs grew |
| `minPixelIntensity` | 0 | 9.02 | none |
| `maxPixelIntensity` | 19.28 | 38.82 | none |

One of the three deprecated properties is honoured and two are not. That is a
more useful reading of *"Deprecated"* than the one this README started with: it
does not mean "still works", it means **"still accepted"** — and storage is not
rendering. A verifier that can only read the item back cannot tell those apart;
only a screenshot could, which is why the pair was taken at a matched extent and
zoom rather than casually.

**Then the current encoding was published, and the layer disappeared.**
`--heatmap-form density` writes the specification's current form —
`radius` / `minDensity` / `maxDensity` — and ArcGIS Enterprise 12.1 stored it
exactly as sent and drew nothing whatsoever. That completes the matrix:

| Encoding | Stored | Drawn |
|---|---|---|
| `gaussian` — `blurRadius`, `minPixelIntensity`, `maxPixelIntensity` (deprecated) | yes | yes, but only `blurRadius` has any effect |
| `density` — `radius`, `minDensity`, `maxDensity` (current) | yes | **nothing at all** |

So on this version, *"deprecated"* marks the only form that works, and the
current one is the one that is merely accepted. Same shape as
`uniqueValueInfos` over `uniqueValueGroups` and as `geo_point` in `opensearch` —
the consumer's constraint decides the representation — except that here the
newer form does not degrade, it vanishes.

### The verifier reported 4 of 4 on a map with an invisible layer

This is the sharpest thing this folder has measured, and it is a criticism of
the verifier rather than of the portal. Every check in `verify_portal.py` reads
the **stored** item: field types, feature count, extent, renderer types, the
heatmap ramp, item metadata. All of them were satisfied by a web map whose first
layer drew nothing, because storage and rendering are different facts and no
amount of reading an item back distinguishes them. The committed
`output/verification_report_portal.md` is that run — kept deliberately, green
and wrong.

What a read-back verifier *can* carry is the measurement itself, and it now
does: `check_heatmap_ramp` refuses the `density` encoding for a 12.1 target and
names the publish that established it. That turns a screenshot into a check
once — the screenshot is still what found it, and nothing in the automated pass
would have.

The default is therefore `gaussian` **by measurement, not by caution**;
`--heatmap-form density` is kept because it is the right choice against a target
that draws it, and because it reproduces the finding in one command.

The renderer also carries **`referenceScale` 1:50,093** — the scale the ramp was
computed for, and the only property that can stop a client renormalising at every
zoom level. Published together with the gaussian encoding it is **harmless**: the
heatmap draws. It changes nothing visible either, which is consistent with the
row above — the two intensity bounds it would pin are the two properties this
version ignores. `--no-reference-scale` remains, as the isolation switch that
established this.

**The deeper problem, which calibration does not fix.** A heatmap weighted by a
field shows density × weight. Measured on this data set, the heatmap's intensity
correlates with plain point density at **ρ = 0.774** and with the local rent
level at **ρ = 0.786** (Spearman, at the point positions) — it carries both
signals about equally, and a viewer cannot tell which one a red patch means. The
district medians are dramatic (Altstadt 17.86, Kreuzviertel 16.51 … Coerde 7.90,
Berg Fidel 6.61 €/m²) and the heatmap simply is not the instrument that shows
them. That is why `rent_breaks` exists next to it, on the same column, with a
rank correlation of 1.0 with the rent by construction.

`verify_portal.py` now asserts the ramp: `maxPixelIntensity` must sit at least
1.5× above the largest weight in the source column. That check fails on the
shipped configuration and passes on the calibrated one.

### Screenshots from the portal

**One capture is committed, and six were deliberately not.** The Map Viewer
exports at 3979 x 2247 and about 7 MB each; seven of them would have added 49 MB
to a public repository's history permanently, against 1.6 MB for each screenshot
the earlier use cases contribute. So the one that carries an argument is here and
the rest were discarded after they had done their job.

| File | Layer | Shows |
|---|---|---|
| `input/class_breaks.png` | `rent_breaks` | the layer that answers the question — Altstadt and Kreuzviertel red, the outer districts yellow and orange. The one capture this use case contributes to the talk |

It is an external artifact made by hand, which is why it sits in `input/` and not
in `output/` (CLAUDE.md §3: `output/` must be safe to delete and rebuild from the
documented command, and a screenshot is not).

The basemap attribution is visible and uncropped, burnt into the bottom edge by
the Map Viewer, and it is recorded here as text as well because an image can be
resized, re-exported or replaced and the obligation cannot:

> Land NRW | Esri | HERE | Garmin | INCREMENT P | USGS | METI/NASA | Generated
> test data. Nothing in this item is real.

The last clause is this map's own copyright text, set on the item — worth
noticing that the provider notice and the "nothing here is real" disclaimer end
up in the same strip.

### What the discarded captures established, and what is left of it

Three heatmap captures were the **instrument** that produced this folder's best
finding, and they are gone. That is worth stating rather than glossing, because
it is a real cost:

- `heatmap.png` — the uncalibrated heatmap, 500 saturated red blobs,
  `maxPixelIntensity` 19.28, `blurRadius` 12.
- `heatmap2.png` — the calibrated one at the **same extent and zoom**: still
  saturated, blobs larger. The pair is what separated the properties —
  `blurRadius` reached the renderer, the two intensity bounds did not.
- `heatmap3.png` — the gaussian encoding with `referenceScale`, zoomed out: one
  continuous red surface. Third publish, third confirmation.

Plus three from the four-layer version — `median.png`, `unique.png`,
`graduated.png` — showing the other renderers, which never changed.

What survives is the measurement written down here, in the scripts' docstrings
and in the run record, plus a check that refuses the encoding that draws nothing.
That is weaker evidence than the images and it is the honest trade: the finding
is reproducible in one publish, and the live web map can be opened during
questions. A repository is not an archive of everything that was looked at.

## What the portal guessed

This is the central measurement of the use case, and it is **taken**: the portal's
guess differs from the declaration in **0 of 14 fields**. Every decimal column
came back `esriFieldTypeDouble` and every integer `esriFieldTypeInteger` — the
guess was right, and it is only knowable that it was right because it was
captured before being overruled. The one thing the guess does not carry is a
TEXT length, which is also the one thing the publish discarded from ours.

What the code does is fixed:
`gis.content.analyze(item=csv_item, file_type="csv", location_type="coordinates")`
asks the portal what it *would* have chosen, the answer is dumped verbatim to
`output/analyze_publish_parameters.json`, and then the publish proceeds with
**ours**. `verify_portal.py` renders the three columns side by side — what we
declared, what the portal stored, what the portal would have guessed — and marks
every row where the guess differs.

The two failures worth watching for, both drawn from measurements elsewhere in
this repository, are already encoded as checks:

- a decimal column coming back `esriFieldTypeSingle`, which silently rounds a
  coordinate; and
- a **code-like** column coming back numeric. `egdb_import` measured what that
  costs: `state_fips` holding `01`…`09` measures as an integer, becomes `1`…`9`
  as a `LONG`, and `WHERE state_fips = '01'` then finds nothing. No amount of
  measuring a column of digits reveals that it is a code. This data set has no
  such column today; the check is there because the next CSV will.

Neither fired. What did fire was the third possibility nobody had encoded: the
declaration was accepted in full and its **lengths** were discarded anyway. See
*The declaration was accepted and its lengths discarded* below — the guess and
the declaration agreed, and the stored schema matched neither.

## Verification

Six checks in total, and six is a decision rather than a shortfall.

**Offline — `verify_census.py`, 2/2 green:**

| # | Check | Result |
|---|---|---|
| 1 | Axis order, column order and range | PASS — 0 swaps, 0 out of range, 0 transposed-box hits |
| 2 | EPSG:3857 columns recomputed independently | PASS — max deviation **0.000069 m** against a 0.001 m tolerance |

**Against the portal — `verify_portal.py`, three runs:** 3/4, 3/4, then 4/4.
The third one is the interesting one, because it was green on a web map whose
heatmap layer drew nothing — see
[The verifier reported 4 of 4 on a map with an invisible layer](#the-verifier-reported-4-of-4-on-a-map-with-an-invisible-layer).
The committed `output/verification_report_portal.md` is that run, kept as
evidence rather than refreshed away.

Run by run: the first failed check 3 because the TEXT lengths counted as
failures; the second failed it again because they were still wrong after
`updateDefinition` had reported success; the third passed everything, with the
lengths demoted to INFO and the heatmap silently empty. Every one of those three
results was correct about what it measured and wrong about whether the map
worked.


| # | Check | What it settles | Second run |
|---|---|---|---|
| 3 | Field types survived the publish | ours vs. stored vs. the portal's guess, per field | types PASS; the discarded TEXT lengths are reported as **3 INFO findings** |
| 4 | Count and extent | 500 features, extent inside a Münster box **in the unit the layer stores**, both bounds printed | PASS |
| 5 | Five operational layers, four renderer types, one service | whether a renderer was silently dropped, and whether the heatmap ramp saturates on a single feature | PASS |
| 6 | Items exist, typed, tagged, shared as intended | including the sharing level, which is the one property other people can see | PASS |

### The declaration was accepted and its lengths discarded

Check 3 failed on the first real publish, identically on all three TEXT columns:
declared `TEXT(80)` / `TEXT(40)` / `TEXT(40)`, stored **`TEXT(8000)`** in every
case. The types survived — `Integer` stayed `Integer`, every `Double` stayed a
`Double` — so the central measurement of this use case still holds. The
**lengths** did not, and nothing said so: the portal accepted the
`layerInfo.fields` body without a warning and sized every string column at its
maximum.

Esri's `updateDefinition` reference says only *"When updating field properties,
note that not all of these properties may be updated"* and does not say which,
so the instance was asked rather than the document. `--retrofit-field-lengths`
POSTed the three declared lengths after the publish, and the answer is the best
part of this section:

```json
{"success": true}
```

**After which the service still reports `TEXT(8000)`.** The API confirmed a
write it did not perform. That is CLAUDE.md's *check what an API wrote, not
whether it threw*, one notch sharper — not whether it said it did either. It is
also the same shape as the heatmap one section up: something was accepted, and
acceptance is not the thing you wanted.

So the finding moved rather than being fixed or hidden. The **types** still fail
check 3 — that is the claim this use case makes about declaring a schema. The
**lengths** are reported as INFO next to the API's own success claim, because
there is nothing left on this side to repair: the platform sizes hosted string
columns itself, and a check that can only ever be red carries no information.
The demotion is a measurement, not a convenience, and the run record keeps the
raw response.

A declared TEXT length is therefore a *request* here, not a contract — a real
difference from `egdb_import`, where the geodatabase honoured every declared
length exactly.

### The verifier shares nothing with what it checks

`verify_census.py` implements Web Mercator as `y = R · atanh(sin φ)` while the
generator writes the algebraically identical `y = R · ln(tan(π/4 + φ/2))`. Same
function, two independently coded forms, so agreement is evidence rather than a
second call into the same code. Neither verifier imports `scripts/census.py`.

That module holds only the things the *writers* must **agree** on — the column
list, the declared field type per column, the seed and service-name defaults, the
placeholder tokens. CLAUDE.md §4: code that has to agree should be shared, code
that has to check must not be. Both halves of that rule have already cost this
repository something — `csv_data` only found a 490 m projection error because the
verifier wrote the formula a second way, and `egdb_import` aborted at row 0
because the analyser and the loader held two different definitions of "empty".

`verify_portal.py` goes further: it reads its expectations as **data** (the
declared schema from `output/publish_parameters.json`, the bounding box from
`input/muenster_districts.json`) or restates them from a second reading of the
Web Map Specification, which is what it does with the renderer types — as a count per type, not a
set, because `classBreaks` now legitimately appears twice and a set cannot tell a
missing second class-breaks layer from a present one.

### Is a swap loud or silent here?

The report says so explicitly, because CLAUDE.md §4 forbids writing "the axis
check passes" without it. The answer has two halves pointing opposite ways:

- The bands are **disjoint** — latitude 51.90…52.00 against longitude 7.55…7.72
  — so the bounding-box check catches a swap on **every** row. Measured: a
  transposed copy of the committed CSV produces 1,000 suspected swaps and 500
  transposed-box hits.
- And every swapped value is still a **legal** coordinate: 7.6 is a valid
  latitude and 51.9 a valid longitude. No database, no service and no GIS client
  would refuse the load; the points would draw silently at 7.6°N 51.9°E in the
  Somali Sea.

That is the same silence as the NRW stations in `opensearch` and `egdb_import`,
and the opposite of the 880 airports, where the engine rejected 550 of 880
documents outright. **This check is load-bearing precisely because nothing
downstream would fire.**

### The checks were proven to fire, separately

Cheap here, so it was done for the offline pair and for the rehearsal — four
planted defects, each hitting only what it should:

| Planted defect | Effect |
|---|---|
| `latitude`/`longitude` transposed in every row | check 1 FAIL (1,000 swaps + 500 transposed hits), check 2 FAIL (max deviation **7,736,302 m**) |
| one `y_3857` value nudged by 5 cm | check 1 **PASS**, check 2 FAIL — 1 of 500 rows, 0.050026 m |
| `{{FEATURE_SERVICE_UR}}` — one character short | the rehearsal aborts, exit 1, nothing uploaded. A whitelist of known token names would have passed it; the check greps for the marker instead |
| one 90-character address, one `rooms` value of `drei` | the row rehearsal names both, by line number and column, exit 1 |

The one that matters is the second row: the nudge trips check 2 and leaves check
1 green. A verifier whose checks always go red together has one check wearing
several hats.

### Deliberately not checked

Four omissions, each a decision rather than a gap:

- **Coordinate provenance.** `opensearch` asserts that every coordinate in
  `output/` exists unmodified in a source row with the same identity key, and it
  is the check that catches a value changed to a plausible spot. It cannot exist
  here: there is no source. Nothing was sourced, so nothing can be traced.
- **A per-feature reprojection round trip through the portal.** The portal
  reprojects degrees to metres with its own code. Checking that would be testing
  Esri, not us. What *is* checked is that the extent lands in the right place in
  the right unit — the failure that has actually happened.
- **Statistical realism.** "Is this value plausible?" is the wrong question about
  invented data. The fixture says `"fictitious": true` in its second line and
  the layer's `accessInformation` says *"Generated test data. Nothing in this
  item is real."*
- **The full perturbation matrix over all six checks.** Six checks over
  synthetic data do not earn what `opensearch`'s twelve did. The four planted
  defects above were the cheap subset; the portal-side three were not
  perturbation-tested. Recorded as a decision, not an omission.

## Reproducibility

- **Seed:** `20260904`, exposed as `--seed`. Same seed and same input files
  produce a byte-identical CSV.
- **Model / date:** plan written with Claude Opus 5, 2026-09-04; implemented
  with Claude Opus 5, 2026-09-07. The model wrote the code, the fixtures and
  this README — it wrote none of the 500 rows.
- **Exact command that produced the committed output:** the four commands in
  [Usage](#usage) steps 1–4, in order, from `portal_publish/`.
- **RNG fingerprint:** `bb6a8bb4aed5d45a` for seed 20260904. Printed on every
  run so a differing file hash can be triaged before anybody looks at the
  values — the Mersenne Twister is specified bit for bit and survives Python
  minor versions.
- **The rounding margin is measured, not assumed.** `random.gauss` runs through
  `log`, `sqrt` and `cos`, and C transcendental functions are not standardised
  to the last bit — `opensearch` measured 30 of 880 values differing by up to
  2 ULP between Linux and Windows, which changed a committed file's SHA-256 at
  identical size and content. Every value written here is therefore rounded, and
  the generator measures how close each **unrounded** value came to a rounding
  boundary and refuses to write the file below `--min-margin-ulp` (default 16).
  Measured on the committed run: **worst margin 96.0 ULP** across 4,500 rounded
  values, six times the threshold. Measuring the margin on the *rounded* values
  would prove nothing — rounding puts them on the grid by definition, which is
  how the first version of that check was written in `opensearch`.
- **Line endings are pinned.** The CSV is written with an explicit
  `newline="\n"`, its hash is taken from the in-memory string as well as from
  the file so newline translation is ruled out before the values are, and
  `.gitattributes` declares `* text=auto eol=lf` for the clone. A hash-pinned
  artifact rewritten by `core.autocrlf=true` fails its provenance check for a
  reason that has nothing to do with the data.
- **Non-determinism:** none in this pipeline. No LLM is called at runtime — the
  language model wrote the generator and the fixtures, and the generator is
  seeded. That is the same shape as `csv_data`'s second method, and the
  deliberate opposite of its first.

## Notes for the talk

**In the deck.** One slide, `slides/pages/50-portal.md`, with
`class_breaks.png` as its screenshot. Its single finding is *four of four green,
and the layer was empty* — chosen over the other four because it argues against
the deck's own thesis that checks beat inspection. Everything else measured here
stays in this README; the deck has no backup section for it to land in.

**What worked.**

- The offline/portal split paid for itself immediately. Four renderers, a
  declared schema and a complete Web Map were designed, argued about and
  verified without a portal, a licence or a password anywhere near the loop —
  and the portal-facing script shrank to a transcription of documents already
  read.
- **The declaration beat the guess before the guess was even taken.** Every
  decimal is a `Double` and every text field has a measured length with
  headroom, and the builder *refuses* to write a declaration the committed CSV
  already exceeds — the same refusal as `egdb_import`'s schema contract, and for
  the same reason: a declared length the data exceeds fails hundreds of rows
  into the insert, on the other side, with an error about a row.
- Deriving every renderer threshold from the data rather than typing it in.
  Quantile breaks came out at 101 / 101 / 98 / 100 / 100 features, which is a
  legend an audience can read, and it survives a change of seed.

**What failed.**

- **The placeholder check tripped on its own documentation.** The very first
  `--dry-run` aborted with *"1 unresolved placeholder"* — and the offending
  token was inside a `_note` in `webmap.json` explaining what the check does.
  The assertion greps the serialised payload as text, so a note that spells the
  marker out is indistinguishable from a real unsubstituted token. The note now
  says "double-brace marker" in words. A check strict enough to be useful is
  strict enough to catch your prose, and the alternative — a whitelist of known
  token names — would have let the *real* failure through: a one-character typo,
  `{{FEATURE_SERVICE_UR}}`, which is exactly what the marker grep does catch.
- **The first household-size distribution was a clamp in disguise.** A Gaussian
  with a mean of 1.6 and a hard floor of 1.0 piled **37 of 500** rows onto
  exactly 1.0 — 7 % of the data on one value, invisible in a map and obvious in
  a popup. The clamp counter existed to report a bad distribution and instead
  became the distribution. Replaced by a gamma variate above the floor, which
  has the bound built in: 37 clamps down to 2. Same lesson as `opensearch`'s
  log-normal tail from the other end — derive the parameter from the intended
  spread instead of guessing one and absorbing the error in a clamp.
- **Two units for two properties that are both called "extent".** Found while
  re-reading the finished publisher: an ArcGIS *item's* `extent` property is
  documented as decimal degrees (WGS84), while this map's own viewpoint is
  EPSG:3857 metres because `targetSR` defaults to 102100. The first version
  handed the viewpoint's metres to the item property — which would have produced
  an item whose extent is nonsense and whose map draws perfectly, with nothing
  anywhere complaining. The Gulf-of-Guinea failure from `egdb_import`, one level
  up: same shape, same silence, different property. `webmap.json` now carries
  both numbers explicitly, in a key named after its unit.
- **The commentary would have shipped.** The same reading found that the
  `_note` keys written into `output/webmap.json` for a human reader were being
  uploaded as part of the live web map's `text`. The portal would have tolerated
  them and nobody would have wanted them. Underscore-prefixed top-level keys are
  now stripped before `content.add`, and `verify_portal.py` asserts they are
  absent from what the portal stored — so the strip is measured rather than
  intended.
- **The heatmap's ceiling was set in the wrong unit, and the map still drew.**
  `maxPixelIntensity` was the 95th percentile of `rent_eur_sqm` — 19.28 €/m² —
  as if a pixel intensity were a rent. It is a sum of kernel weights, so an
  isolated point peaks at exactly its own weight, and rents reach 22.75: every
  single dwelling hit the top of the colour ramp alone. The published map was
  500 red blobs, and no part of the stack complained. Same family as the two
  `extent` properties above and the Gulf of Guinea in `egdb_import`: a number
  assigned across a unit boundary nobody was watching. The ceiling is now
  simulated rather than borrowed — floor 9.02, ceiling 38.82 — and
  `verify_portal.py` asserts it sits at least 1.5× above the largest weight.
- **…and the corrected numbers were stored and not drawn by.** The second
  capture, same extent and same zoom, is still saturated. The verifier reads the
  new bounds back out of the live web map, so the payload arrived; comparing the
  two screenshots shows `blurRadius` took effect and neither intensity bound
  did. One of three deprecated properties honoured. *"Deprecated"* turned out to
  mean **accepted**, not supported — and no verifier that reads an item back can
  see that difference. The screenshot is the only instrument that can, which is
  an uncomfortable thing to have learnt in a repository built on automated
  checks.
- **An API confirmed a write it did not perform.** `updateDefinition` answered
  `{"success": true}` to the field-length retrofit, and the service still
  reports `TEXT(8000)`. The run record keeps the response next to the
  measurement that contradicts it.
- **The specification's current heatmap encoding stores and draws nothing on
  12.1, and the verifier called that run 4 of 4.** The layer was empty, every
  check was green, and every check was right about what it measured — they all
  read the *stored* item. It took a screenshot to notice, in a folder whose
  whole argument is that checks beat inspection. The honest version of that
  argument is narrower: a check can only see what it can read, and "does this
  draw" is not a readable property. The measurement is now encoded — the
  verifier refuses that encoding for a 12.1 target — but encoding it required
  finding it first, and only a human looking at a map could.
- **And calibration was not enough, because the renderer answers a different
  question.** A weighted heatmap shows density × weight. Measured here: its
  intensity correlates with plain point density at ρ = 0.774 and with the local
  rent level at ρ = 0.786 — about equally, so a red patch cannot be read. The
  rent structure in the data is dramatic (district medians 17.86 down to 6.61
  €/m²) and the heatmap was the wrong instrument for it. The fix was not a
  better heatmap but a second layer on the same column, `classBreaks`, which
  answers the question by construction. The pair is now the point: the same
  data, two renderers, one of which cannot say what it appears to say.
- **The plan was wrong in one small way and it is recorded rather than
  smoothed over:** it named three placeholder tokens, and only two have a use.
- The library route the request would naturally take does not exist. There is
  no Web Map class in the pinned client, in either the old place or the new one
  its own migration notes name.

**Lesson learned.**

> Generated content can reach much further into a GIS platform than the data
> layer — schema, symbology, item, map — but the platform decides how much of it
> survives, and it does not say which parts it dropped. A declared TEXT length,
> a heatmap's intensity bounds and an entire renderer were each accepted in full
> and each silently ignored, with an automated check reporting green over all
> three. So write the *decisions* down somewhere a human can read before
> anything is uploaded, and then go and look at the result: the half of this use
> case that needs a portal is two scripts that decide nothing, the half that
> decides everything runs on a laptop with no credentials and no network — and
> the only instrument that caught what the platform dropped was a screenshot.

**Closed.** A heatmap on ArcGIS Enterprise 12.1 cannot be calibrated from the
payload: the current encoding draws nothing, the deprecated one honours only its
blur radius, and `referenceScale` is accepted without changing anything it could
change. The two intensity bounds are unreachable from here. So the answer to
*"where are the rents high"* is the class-breaks layer, and that is also the one
screenshot this use case contributes to the talk —
`input/class_breaks.png`, synced into the deck by `slides/scripts/sync_assets.mjs`
and shown on this use case's slide.

The three heatmap captures were the instrument that established the *stored but
not drawn* finding and are deliberately not in the repository — 49 MB of Map Viewer exports against
one screenshot that carries an argument. If a question comes, the live web map
answers it better than a still would. The committed capture carries its basemap
attribution **visible and uncropped** (CLAUDE.md §3 —
and note that ArcGIS Pro keeps that notice in a closed *Service Layer Credits*
panel rather than burnt into the map, so a capture of the whole window can
contain no notice at all with nothing having been cut off; the browser Map Viewer
used here puts it along the bottom edge, which is easier). The notice is recorded
as text under *Screenshots from the portal* as well, because an image can be
resized, re-exported or replaced and the obligation cannot.
