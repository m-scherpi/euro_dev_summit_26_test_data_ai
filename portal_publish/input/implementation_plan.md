<!--
The reviewed implementation plan for this use case, committed as an input
document rather than kept outside the repository: the scripts below are meant to
be a transcription of a document somebody already read, so the document is part
of the source material.

Written 2026-09-04 with Claude Opus 5. Read-only, like everything in `input/`.
Where a later measurement contradicts a claim here, the claim stays and the
correction goes into `README.md` — the delta is the talk material.
-->

# Use case `portal_publish` — from a generated CSV to a Web Map on ArcGIS Enterprise

## Context

The repository has four finished use cases, and all four stop at the *data*
layer: a CSV written by an LLM, a researched open-data set, an OpenSearch index
consumed by ArcGIS Pro, and two FeatureClasses in a PostgreSQL Enterprise
Geodatabase. Every measured finding so far is a finding about data — axis order,
CRS, projection, provenance.

The user's redirection for this step is explicit: **breadth over rigour.** In
this scenario real data plays no role, so authenticity proofs and error classes
are of secondary interest. What the talk needs next is a case study of *how far
into the platform generated content can reach* — not another proof that a
coordinate is correct. This use case is therefore the intended **finale of the
talk**: one flow that ends in something the audience can look at.

```
seeded generator → CSV → Hosted Feature Layer → Web Map (4 layers, 4 renderers)
```

A fictional rent-price census for Münster: 500 points, each carrying rent per
square metre, median age, building type and household size, scattered around a
handful of Münster district centres so every thematic layer has visible spatial
structure. Nothing about it is real, and that is the point — it is the data set
nobody is allowed to have.

Two deliberate inversions of this repository's own findings, both of which must
be stated in the README or the repo appears to contradict itself:

- `opensearch` publishes a web feature layer that **references** registered data
  and copies nothing. This is the opposite: **copy-all-data**, rows living in the
  ArcGIS Data Store.
- `egdb_import` refused `import_data()` *because* it copies rows out of a
  database into a hosted layer. Here that copy is the deliverable. Same
  measurement, opposite verdict.

## Fixed scope

| Decision | Choice |
|---|---|
| Target | ArcGIS **Enterprise** Portal 12.1, no server extensions |
| Data origin | seeded Python generator, stdlib — the LLM writes the code, not the rows |
| Boundary | none; district centres as a committed, explicitly non-authoritative fixture |
| Themes / renderers | rent €/m² → heatmap · median age → classBreaks · building type → uniqueValue · living area → sizeInfo |
| Basemap | Esri online basemaps available → the web map ships a `baseMap` block |
| Sharing | **private** by default, `--share` to widen |
| Dashboard | **out of scope for this step** — planned as a separate follow-up |
| Verification depth | proportionate: 2 offline + 4 portal checks, not the 12-check apparatus of `opensearch` |

The obsolete `python_import/` stub is superseded by `egdb_import` and gets
removed as part of this change.

---

## Measured before planning (independently reproduced)

In the pinned `arcgis` 2.4.1.1 already installed at
`egdb_import/build/venv_api/`:

```
arcgis 2.4.1.1
FAIL arcgis.map        ModuleNotFoundError: No module named 'arcgis.map'
OK   arcgis.mapping    (a re-export shim: MapImageLayer, VectorTileLayer, SceneLayer)
FAIL WebMap            ImportError: cannot import name 'WebMap' from 'arcgis.mapping'
grep -c "arcgis/map/" arcgis-2.4.1.1.dist-info/RECORD → 0
```

**There is no Web Map class.** The widely-cited migration note "in 2.4
`arcgis.mapping.WebMap` became `arcgis.map.Map`" is half true: the old class is
removed, the new one is not in the wheel. Hand-built Web Map JSON via
`gis.content.add({"type": "Web Map", "text": ...})` is not a workaround, it is
the only route — which independently justifies the stdlib/portal split below.

Second measurement, from Esri's own installed code: the deprecated
`arcgis.apps.dashboard` builder emits `version 27` and its widget map contains
no `mapWidget`. It cannot build the dashboard we want — but it *is* a first-party
oracle for widget JSON shapes, which is why the dashboard is deferred rather
than abandoned.

---

## Folder layout

```
portal_publish/
├── README.md
├── requirements.txt                     # arcgis==2.4.1.1, setuptools==80.9.0 — one reason per pin
├── input/
│   ├── muenster_districts.json          # district centres, "authoritative": false
│   ├── rent_census_fixtures.json        # building types, street-name parts, per-district levels
│   └── portal_connection.example.json   # NO password field
├── output/
│   ├── muenster_rent_census.csv
│   ├── verification_report_coordinates.md
│   ├── publish_parameters.json          # what we declare
│   ├── layer_definition.json            # fields + the one service-level renderer
│   ├── webmap.json                      # 4 operational layers, placeholder-tokenised
│   ├── analyze_publish_parameters.json  # what the PORTAL guessed (real run)
│   └── verification_report_portal.md    # real run, host redacted
└── scripts/
    ├── census.py                        # only what generator & item builder must AGREE on
    ├── generate_census.py               # stdlib → CSV
    ├── verify_census.py                 # stdlib → coordinate report
    ├── build_portal_items.py            # stdlib → the JSONs
    ├── publish_to_portal.py             # needs arcgis; --dry-run rehearses
    └── verify_portal.py                 # needs arcgis; queries back
```

**Where the boundary sits.** Stages 1–3 are stdlib-only, so the entire design —
field types, four renderers, web map layout — is reviewable and diffable **with
no portal in the room**. `publish_to_portal.py` is then a transcription of
documents somebody already read. Same shape as `egdb_import`'s schema contract →
arcpy plan, and it holds better here because the JSON is not a plan, it is the
payload.

`census.py` holds only the shared *agreements* (district ordering, field-name
list, seed default) per CLAUDE.md §4: code that must **agree** is shared, code
that must **check** is not. Neither verifier imports it. Do **not** copy
`csv_data/scripts/geo.py` — there is no polygon here, so `Boundary.contains`
would be dead weight. What carries over is the discipline: round lat/lon to five
decimals **then** project, and the verifier writes `atanh(sin φ)` against the
generator's `ln(tan(π/4 + φ/2))`.

**Placeholder tokens are load-bearing.** `build_portal_items.py` emits
`{{FEATURE_SERVICE_URL}}`, `{{FEATURE_LAYER_ITEM_ID}}`, `{{PORTAL_URL}}`; item
ids do not exist until publish and change on every run, so writing them into
`output/` would break the "regenerable from `input/` plus the command" rule and
churn a committed artifact on every demo. `publish_to_portal.py` substitutes and
then **asserts zero unresolved `{{` remain** before any `content.add` — an
unsubstituted token yields an item that loads, renders its frame and shows no
data. Substituted bodies go to `build/`.

---

## Implementation, in order

### 1. `generate_census.py` (stdlib)

Adapt `csv_data/scripts/generate_points.py`: one `random.Random(seed)` stream,
Gaussian scatter around each district centre (no rejection sampling), lat/lon
rounded to 5 decimals then projected to EPSG:3857 with `R·ln(tan(π/4+φ/2))`,
CSV written with `lineterminator="\n"`.

Columns: `id, address, district, latitude, longitude, x_3857, y_3857,
rent_eur_sqm, living_area_sqm, rooms, median_age, household_size, building_type,
year_built`.

Per-district price and age levels come from `input/rent_census_fixtures.json` so
the heatmap and the class breaks both have structure; noise on top.

```bash
python3 scripts/generate_census.py --count 500 --seed 20260904 \
    --districts input/muenster_districts.json \
    --fixtures input/rent_census_fixtures.json \
    --output output/muenster_rent_census.csv
```

### 2. `verify_census.py` (stdlib) — 2 checks

1. **Axis order and range.** Latitude 51.90…52.00, longitude 7.55…7.72, and the
   transposed box matches nothing. State the sentence CLAUDE.md §4 requires: the
   Münster bands do **not** overlap, so a swap here is loud — unlike the NRW
   stations that loaded silently into the Somali Sea.
2. **Independent 3857 recomputation**, tolerance ~1 mm, deliberately not
   tightened to the observed value.

`--report` and `--output` have no defaults (§4, destructive arguments).

### 3. `build_portal_items.py` (stdlib)

Writes `publish_parameters.json`, `layer_definition.json`, `webmap.json`.

`publishParameters` for the CSV (verified against the REST *Publish Item*
reference): `name`, `locationType: "coordinates"`, `latitudeFieldName:
"latitude"`, `longitudeFieldName: "longitude"`, `sourceSR {"wkid": 4326}`,
`targetSR {"wkid": 102100}` **stated explicitly**, `columnDelimiter: ","`,
`maxRecordCount: 2000`, and `layerInfo.fields` with every type declared —
`esriFieldTypeDouble` for every decimal (never `Single`: seven significant
digits do not cover a latitude, §4), `esriFieldTypeInteger` for counts,
`esriFieldTypeString` with explicit `length` for `district`, `building_type`,
`address`. `columnNames` is omitted because `layerInfo.fields` overrides it —
that is the hook that turns a guess into a declaration.

Note the CRS consequence: `targetSR` defaults to 102100, so the hosted layer
stores **Web Mercator metres** even though the CSV is degrees. Name both codes
in the README, and make the extent check say which unit it measured.

The web map references the **same service URL four times** with different
`layerDefinition.drawingInfo` — verified as supported by the Web Map
Specification, and it is the whole architecture in one sentence. Operational
layer ids are set explicitly (`rent_heatmap`, `age_breaks`, `building_type`,
`area_size`) because a later dashboard binds to them. Renderer JSON per the
spec, with two traps avoided: `classBreakInfo` has `classMaxValue` and **no**
`classMinValue` (breaks run contiguously from the renderer's `minValue`), and
`uniqueValueInfos` is used rather than the newer `uniqueValueGroups`, with the
spec's deprecation sentence quoted in the README so the choice reads as
deliberate. The fourth layer is one `simple` renderer with a single
`sizeInfo` visual variable on `living_area_sqm`; `household_size` goes into the
popup rather than adding a second visual variable, so each layer demonstrates
exactly one renderer type. Popups (`popupInfo`) are generated per layer.
`baseMap` ships an Esri basemap block, overridable with `--basemap-url`.

### 4. `publish_to_portal.py` (needs `arcgis`)

Venv at `build/venv_api`, `requirements.txt` mirroring `egdb_import`'s pins with
their reasons (`setuptools` because arcgis imports the removed `distutils`).

Stages, cumulative, each leaving a working deliverable —
`--stage csv|publish|layerdef|webmap|all`:

1. `gis.content.add({"type": "CSV", ...}, data=csv)`
2. `gis.content.analyze(item=csv_item, file_type="csv", location_type="coordinates")`
   → dump `result["publishParameters"]` to
   `output/analyze_publish_parameters.json`, **then publish with ours**. The
   diff between the two files is this use case's central measurement: it shows,
   per column, what the portal would have guessed, including a renderer it
   suggests unasked.
3. `csv_item.publish(publish_parameters=ours, file_type="csv")`. Not
   `import_data()` (DataFrame-only, no type control, documented 1,000-row cap)
   and not `overwrite=True` (documented as incompatible with
   `publish_parameters`).
4. one `FeatureLayerManager.update_definition()` pushing the classBreaks
   renderer onto the service, so a client opening the layer directly does not
   get the portal's suggestion.
5. `gis.content.add({"type": "Web Map", "text": json.dumps(webmap), "extent": ...})`.

Idempotency, because a live demo runs twice: fixed tag
`devsummit-portal-publish` on every item; `--recreate` searches with an
**explicit `max_items`** (the default is 10 — a silent truncation), calls
`Item.delete(dry_run=True)` first and logs any blocking dependents, then deletes
**Web Map → Feature Service → CSV** in that order (deleting the CSV first can
orphan the `Service2Data` relationship the publish path reads). Then
`gis.content.is_service_name_available(name, "featureService")` aborts with a
message instead of a traceback — `permanent=True` is documented as ArcGIS Online
only, so on Enterprise a deleted item may still hold its service name.

Credentials per `egdb_import`: `PORTAL_PASSWORD` or `--password`, no default, no
committed value, a `REDACTED` constant in every log line, and
`input/portal_connection.example.json` with no password field explaining why the
`opensearch` throwaway exception is *not* taken. TLS: `--ca-cert` sets
`REQUESTS_CA_BUNDLE` before importing `arcgis`, `--no-verify-cert` maps to
`GIS(verify_cert=False)`, and the README repeats that a literal `localhost` in
`--portal` is resolved by the federated server on its own machine. Sharing via
`item.sharing` (`Item.share` is deprecated), default **private**.

`--dry-run` rehearses everything reachable offline: token substitution, the
zero-unresolved assertion, JSON validity, row coercion against the declared
types, and a written plan — no portal in sight.

### 5. `verify_portal.py` — 4 checks

3. **Field types survived the publish.** Read `FeatureLayer.properties.fields`
   back and compare per field against our declaration *and* the portal's
   `analyze` guess. Assert no decimal came back `Single` and no code-like column
   came back numeric. This is the one measurement worth having.
4. **Count and extent.** 500 features; extent inside a Münster box, computed in
   the unit the layer actually stores, with both bounds printed — "inside the
   box" in the wrong unit is the Gulf-of-Guinea failure again.
5. **Four operational layers, four renderer types.** From
   `webmap_item.get_data()`: renderer types exactly
   `{heatmap, classBreaks, uniqueValue, simple}`, the fourth carrying
   `visualVariables[0].type == "sizeInfo"`, all four `url`s on one service. This
   is where a silently-dropped heatmap becomes visible — heatmap support on
   12.1 specifically is **UNVERIFIED** (no version-pinned page resolves), so the
   instance is asked rather than the document.
6. **Items exist, typed, tagged, shared as intended.**

**Deliberately not checked**, each with its sentence in the README: coordinate
provenance (there is no source), per-feature reprojection round trip (the
portal's own code, testing Esri rather than us), statistical realism
(plausibility is the wrong question about invented data), and perturbation runs
proving each check fires (six checks over synthetic data do not earn what
`opensearch`'s twelve did — recorded as a decision, not an omission).

One screenshot of the web map in the portal's Map Viewer goes to `input/` (a
hand-made capture cannot be regenerated), with the Esri basemap attribution
**visible and uncropped**, and quoted as text in the README.

---

## Deferred: the Dashboard

Planned as a separate follow-up step, at the user's request. Recorded now so the
groundwork is not lost:

- Item type is exactly `"Dashboard"` with the config in `text` — verified from
  Esri's own `arcgis/apps/dashboard/dashboard.py::_publish`, not from docs.
- The deprecated builder emits `version 27` and has **no** `mapWidget`, so the
  central widget must be hand-built; the builder remains usable offline as an
  oracle for indicator, serial-chart and pie-chart widget bodies.
- There is no published dashboard specification — that absence is itself a
  finding worth a README paragraph.
- The cheapest path when we get there: configure one dashboard by hand in the
  portal, pull its JSON with `get_data()`, commit it as a reference and build the
  generated version against it. Ground truth from the exact instance beats any
  amount of doc-reading where no spec exists — and the delta is talk material of
  the same species as `csv_data`'s raw-versus-corrected CSV pair.

---

## Documentation duties (CLAUDE.md §6)

1. **`portal_publish/README.md`** mirroring `csv_data/README.md`'s heading
   order, plus three sections this folder earns: *The inversion*
   (`import_data()` was the defect in `egdb_import` and is the goal here),
   *There is no WebMap class* (the reproduced `ModuleNotFoundError` and the
   `RECORD` grep, with the command to re-measure), and *What the portal guessed*
   (the `analyze` diff).
2. **Root `README.md`**: replace the `python_import/` index row with
   `portal_publish/`; five new rows in the executables table; a progress-log row
   leading with the measured `WebMap` absence and the type-guess diff.
3. **`PROMPT.md`**: entries per §7 — the brainstorming prompt is already logged
   as `[020]`; this planning/implementation round gets its own.
4. **`CLAUDE.md`**: at least three new conventions — a pinned client library may
   be missing the module its own migration notes name (check the wheel's
   `RECORD`, not the release notes); where a vendor publishes no specification,
   the vendor's own deprecated builder code is a better oracle than the
   documentation; a committed item artifact must be placeholder-tokenised
   because portal item ids are not derivable from `input/`.

**Removing `python_import/`:**

| File | Reference | Action |
|---|---|---|
| `README.md:44` | index row | replace with the `portal_publish/` row |
| `CLAUDE.md:50` | folder-naming examples `(csv_data, opensearch, python_import)` | → `(csv_data, opensearch, portal_publish)` |
| `csv_data/README.md:19` | "`../opensearch/`, `../python_import/` can read either" | → `../egdb_import/`, which genuinely does read that CSV |
| `PROMPT.md` (5 places) | historical entries | **leave untouched** — the log is evidence (§7); the new entry records the removal and why |

Then `git rm -r python_import/`.

---

## Verification, end to end

```bash
cd portal_publish
python3 scripts/generate_census.py --count 500 --seed 20260904 \
    --districts input/muenster_districts.json \
    --fixtures input/rent_census_fixtures.json \
    --output output/muenster_rent_census.csv
python3 scripts/verify_census.py --input output/muenster_rent_census.csv \
    --report output/verification_report_coordinates.md          # 2/2 green, offline

python3 scripts/build_portal_items.py --input output/muenster_rent_census.csv \
    --districts input/muenster_districts.json \
    --service-name muenster_rent_census --output-dir output/

python3 -m venv build/venv_api && build/venv_api/bin/pip install -r requirements.txt
build/venv_api/bin/python scripts/publish_to_portal.py --dry-run \
    --csv output/muenster_rent_census.csv --items-dir output/ \
    --plan build/publish_plan.md                                # no portal needed

# real run — needs the portal and $PORTAL_PASSWORD
build/venv_api/bin/python scripts/publish_to_portal.py \
    --portal https://portal.example.com/portal --user devsummit \
    --csv output/muenster_rent_census.csv --items-dir output/ \
    --stage all --recreate --run-record build/portal_run.json
build/venv_api/bin/python scripts/verify_portal.py \
    --portal https://portal.example.com/portal --user devsummit \
    --run-record build/portal_run.json \
    --report output/verification_report_portal.md               # 4/4 green
```

Then open the web map in the portal's Map Viewer, switch through the four
layers, and capture one screenshot with the attribution intact.

I will implement stages 1–3 and the `--dry-run` path here; the real run needs
your portal and your password, so that step is yours to execute, and I will fix
whatever it reports.
