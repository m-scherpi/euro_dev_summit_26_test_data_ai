# OpenSearch as an ArcGIS Data Source

The same 449 railway stations, one step further along: out of a CSV file and
into a search engine that ArcGIS Pro can connect to as a database. Part of
[Test (Geo-)Data Generation with GenAI](../README.md).

Since ArcGIS Pro 3.5 / ArcGIS Enterprise 12.0, Elasticsearch and OpenSearch are
natively supported "document databases": Pro builds a query layer over an index
and Enterprise can publish it as a web feature layer *by reference*, without
copying the data. This use case builds the OpenSearch side of that - downloaded
by script, no Docker, no installer, nothing checked into git except the data
artifacts - and documents the ArcGIS side.

The interesting part is not that it works. It is how many of the obvious
choices are wrong, and that the search engine is perfectly happy with every one
of them.

---

## Purpose

- Provision a local, single-node OpenSearch from a script: `.sh` and `.bat`, run
  straight from the file system, suitable for a throwaway VM.
- Build an index whose mapping and document shape are what ArcGIS requires,
  rather than what an OpenSearch tutorial suggests.
- Verify from the outside that the index is one a GIS client can actually draw -
  including a check that the coordinates are still the ones DB InfraGO
  published.
- Write down what ArcGIS Pro 3.7 and Enterprise 12.1 need on their side.

## Stack

**Shell + Batch for the server, Python 3.12 (standard library only) for the
data.** The provisioning was asked for as `.sh` / `.bat`, and starting a process
does not need a language. The indexer and verifier are Python because they have
to read a CSV and speak JSON over HTTPS - but with no dependencies at all, so
the whole use case comes up on a bare VM with a Python interpreter and nothing
else. Deliberately different from
[`open_data_search`](../open_data_search/README.md), which spends four
dependencies on independent verification; here the point is that there is
nothing to install.

`urllib` handles HTTPS against a private CA if you hand it the CA file, which is
exactly what a local cluster needs.

---

## Input

`input/` is read-only.

| File | Description |
|---|---|
| `opensearch_dist.json` | Pinned OpenSearch distribution: version 2.12.0, download URLs and sizes for linux-x64 / linux-arm64 / windows-x64, the SHA-512 OpenSearch publishes for each, licence (Apache-2.0) and the ArcGIS compatibility facts the pin is based on |

The station data is **not** copied here. It is read straight from
`../open_data_search/output/nrw_stations.csv` - the repository convention is
that a use case consumes the committed `output/` of an earlier one.

**Why the version is pinned to 2.12.0 rather than tracked:** ArcGIS Pro 3.7 and
ArcGIS Enterprise 12.1 certify *OpenSearch 2.12* - one minor release, not the
2.x line. "Service packs on this release are supported but not certified." A
GIS client pins its database support far harder than a database pins itself, so
"latest" here means "away from the only version the client supports".

The OpenSearch archives themselves are ~820 MB and go to `build/`, which is
gitignored. What is committed is the manifest: version, URL, size, checksum.

## Output

`output/` is generated but committed. Everything in it is reproducible from
`input/` plus the source CSV plus one command - and, thanks to `--dry-run`,
without a running cluster.

| File | Description |
|---|---|
| `nrw_stations_mapping.json` | The index mapping: 11 fields, explicit types, `dynamic: strict` |
| `nrw_stations_bulk.ndjson` | 898 lines - one bulk action and one document per station, 138 KB |
| `verification_report.md` | 12 checks against the running index, PASS/FAIL plus the field types as ArcGIS will see them |

---

## Findings

Five things were measured here that no amount of reading would have produced.

### 1. The `geo_point` format ArcGIS cannot read is the one everything else suggests

Esri's data-type documentation, verbatim:

> The geopoint format that uses an object with a latitude and longitude is not
> supported with ArcGIS.

That is `{"lat": 50.94647, "lon": 6.95523}` - the first form in the OpenSearch
documentation, the form in every tutorial, and the form a language model writes
unprompted. It indexes without complaint, answers `geo_bounding_box` and
`geo_distance` correctly, and ArcGIS will not read it.

What remains, and how they disagree with each other:

| Format | Value for Köln Hbf | Axis order |
|---|---|---|
| array | `[6.95523, 50.94647]` | longitude first (GeoJSON, RFC 7946) |
| string | `"50.94647,6.95523"` | **latitude first** |
| WKT | `"POINT (6.95523 50.94647)"` | longitude first |

Two of three put longitude first; the odd one out is the one that reads most
like prose. `--geo-format` therefore is a real switch with `array` as the
default, and the verifier re-derives the expected order per format from the
specification rather than from the indexer's code.

### 2. Nothing that OpenSearch itself can tell you would have caught it

The measurement that makes the point. An index built with the object format was
run through all twelve checks:

| | Object format `{lat, lon}` | Axes swapped `[lat, lon]` |
|---|---|---|
| Checks failing | **1 of 12** | 5 of 12 |
| Document count | PASS | PASS |
| `geo_bounding_box` over NRW | PASS - 449 of 449 | FAIL - 0 of 449 |
| `geo_distance` vs. haversine | PASS - 62 = 62 | FAIL - 0 vs. 62 |
| Coordinate provenance | PASS | FAIL |
| ArcGIS-readable format | **FAIL** | PASS |

A swapped axis is loud: five checks fire, and the stations land in Somalia. The
object format is silent. Every geospatial test passes, the data is correct, the
queries work - and the layer will not open in ArcGIS. The only check that finds
it is the one that knows what the *client* needs. That is the lesson of this
folder: for a data set with a consumer, "is the data right?" and "can the
consumer read it?" are two different questions, and the second one needs the
consumer's documentation, not the database's.

### 3. There is no format both ArcGIS and the OpenSearch SQL plugin can read

ArcGIS query layers are written in SQL. OpenSearch ships a SQL plugin. Measured
against `SELECT * FROM nrw_stations LIMIT 1`:

| geo_point format | Indexes | DSL geo query | OpenSearch SQL plugin | ArcGIS (per Esri docs) |
|---|---|---|---|---|
| array `[lon, lat]` | yes | works | **fails** | supported |
| string `"lat,lon"` | yes | works | **fails** | supported |
| WKT `POINT (lon lat)` | yes | works | **fails** | supported |
| geohash | yes | works | **fails** | not documented |
| object `{lat, lon}` | yes | works | works | **not supported** |

The SQL plugin's error is explicit: `geo point must in format of {"lat":
number, "lon": number}`. Exactly one representation satisfies it, and it is
exactly the one Esri rules out.

Whether this actually bites depends on something the OpenSearch side cannot
determine: does ArcGIS delegate its SQL to the plugin, or does it parse the SQL
itself and issue DSL? The evidence leans towards the latter - Esri documents a
restricted SQL subset with no joins, while the plugin supports joins, which
suggests a separate translator. But it is inference, not knowledge. The verifier
therefore reports the SQL result as INFO and never fails on it. **If an ArcGIS
query layer over this index fails with a geometry error, this table is the first
place to look.**

### 4. The certified release ships a TLS configuration that expired in 2023

ArcGIS supports basic authentication only, so the sensible local setup is TLS
plus basic auth, and OpenSearch has a demo installer for exactly that. Running
it produces this:

```
root-ca.pem   notBefore = 2023-08-29   notAfter = 2023-09-28
esnode.pem    notBefore = 2023-08-29   notAfter = 2033-08-26
```

The demo **root CA has a 30-day validity** and expired on 28 September 2023. The
node certificate it signed is good until 2033, so the chain looks healthy until
a client tries to validate it and gets `certificate has expired`. The cluster
starts and serves happily; only clients notice. And the demo certificate covers
`localhost`, `127.0.0.1` and `node-0.example.com` - so it could never have
served a VM addressed by hostname anyway.

`setup_opensearch.sh` therefore generates its own CA and node certificate with
the `keytool` of OpenSearch's bundled JDK - no openssl, no external tool, same
code path on both platforms. `--demo-certs` keeps the expired configuration, for
showing the failure rather than working around it.

One detour on the way there: a single self-signed certificate with
`basicConstraints CA:true` fails with `No certificates found in http.p12 with
alias http`, because OpenSearch Security filters CA certificates out of the
server chain. It needs a real two-level chain - which is also what a Windows
trust store wants under *Trusted Root Certification Authorities*.

Only the HTTP layer gets the new certificate. Transport TLS keeps the demo
certificates: they run to 2033, and a single node never opens a transport
connection to a peer. The HTTP layer is the one ArcGIS validates.

### 5. `admin/admin` is gone, and the replacement has to pass a strength check

Since OpenSearch 2.12 the demo installer requires
`OPENSEARCH_INITIAL_ADMIN_PASSWORD` and runs it through a strength check.
`admin` is rejected. This repository therefore commits a fixed demo password
(see [Credentials](#credentials)).

---

## Setup

Nothing is installed system-wide, no root is needed, and no Docker is involved.
Everything lands in `build/`, which is gitignored - deleting that folder undoes
the entire installation.

Requirements: `bash`, `curl` or `wget`, `tar`, `sha512sum`, `python3` on Linux;
PowerShell 5.1+, `curl.exe` and `python` on Windows. Java comes with OpenSearch.

Budget: ~820 MB download, ~1.5 GB unpacked, 1 GB JVM heap, roughly a minute from
`start` to a cluster that answers.

```bash
cd opensearch

# Linux
./scripts/setup_opensearch.sh --host localhost
./scripts/run_opensearch.sh start
```

```bat
rem Windows
cd opensearch
scripts\setup_opensearch.bat --host localhost
scripts\run_opensearch.bat start
```

If ArcGIS Pro runs on a *different* machine than OpenSearch, pass that machine's
hostname or address so it ends up in the certificate:

```bash
./scripts/setup_opensearch.sh --host gis-vm-01.example.lan
# or, for an address, plus extra names:
./scripts/setup_opensearch.sh --host 192.168.10.20 --san dns:gis-vm-01
```

**`vm.max_map_count` on Linux.** OpenSearch wants 262144; the setup script
checks and reports. Raising it needs root:

```bash
sudo sysctl -w vm.max_map_count=262144
```

Without root, `--no-mmap` configures the node to do without memory mapping.
449 documents do not need it.

**Cluster health is `yellow`, and that is expected.** The security plugin's
system index asks for one replica, which a single node never assigns. The
station index itself is `green` - it is created with `number_of_replicas: 0`.

### Credentials

This is a deliberate, documented exception to the repository rule that no
credentials are committed:

| | |
|---|---|
| User | `admin` |
| Password | `DevSummit#2026os` |

A throwaway single-node cluster on a test VM holding public open data is not a
secret worth an environment variable, and a demo that needs a manual export
before the first command is a demo that fails on stage. Both are overridable -
`--password`, `$OPENSEARCH_INITIAL_ADMIN_PASSWORD` for setup and
`$OPENSEARCH_PASSWORD` for the clients - and nothing else in this repository
follows this pattern.

Two things about that password are not cosmetic, and both were found while
verifying the Windows path.

**It contains no `!`, because `cmd.exe` would eat it.** `setup_opensearch.bat`
runs under `setlocal EnableDelayedExpansion` - it has to, the certificate SANs
are built up in a loop - and there cmd strips an unmatched `!` out of every
`set "VAR=..."`. The original default `DevSummit#2026!os` therefore reached the
demo installer as `DevSummit#2026os`: setup succeeded, the cluster started, and
`run_opensearch.bat status` reported `green`, because that script mangles the
password in exactly the same way. Everything that did *not* go through a batch
file - the browser login, `osclient.py`, `curl` typed by hand - used the
documented password and got **401**. The password the node has and the password
the documentation names differed by one character, and every component that
could have noticed was on the wrong side of the same bug.

**The password can only be set once per data directory.** The admin user lives
in the `.opendistro_security` index, which is initialised exactly once - on the
first start against an empty `build/data`. Re-running setup rewrites
`internal_users.yml`, and the running cluster ignores it. Worse, the installer
only rewrites that file if it still carries the *default* hash it ships with
(it does a literal string replacement of `$2a$12$VcCDgh2NDk07JGN0rjGbM...`), so
a second attempt is a no-op on both ends. `--force` promised to wipe the data
directory and did not; it now does, and a setup run that finds an initialised
`build/data` says so instead of leaving a changed `--password` to fail as a 401
later.

`--insecure` turns the security plugin off entirely: plain HTTP, no credentials,
no TLS. Useful for `curl`, and *not* what ArcGIS is documented against, since it
needs basic auth. Note that the middle ground - security on, HTTP TLS off - is
an unsupported upstream configuration since 2.12, so there is no third option.

---

## Usage

### Generate the artifacts without a server

```bash
cd opensearch
python3 scripts/index_stations.py --dry-run
```

Writes `output/nrw_stations_mapping.json` and `output/nrw_stations_bulk.ndjson`
and stops. This is the command that makes `output/` reproducible.

### Create and fill the index

```bash
cd opensearch
python3 scripts/index_stations.py --recreate \
    --host https://localhost:9200 \
    --ca-cert build/tls/root-ca.pem
```

```
read ../open_data_search/output/nrw_stations.csv | 449 stations
geo_point format 'array' | first value: [6.09124, 50.76756]
wrote output/nrw_stations_mapping.json | 11 fields, 0.9 KB
wrote output/nrw_stations_bulk.ndjson | 449 docs, 138.2 KB
connected to https://localhost:9200 | opensearch 2.12.0
created index 'nrw_stations' with an explicit, strict mapping
bulk loaded 200/449
bulk loaded 400/449
bulk loaded 449/449
index 'nrw_stations' holds 449 documents
done. Verify with scripts/verify_index.py
```

On a cluster started with `--insecure`, use
`--host http://localhost:9200 --no-auth` instead.

### Verify

```bash
cd opensearch
python3 scripts/verify_index.py \
    --host https://localhost:9200 \
    --ca-cert build/tls/root-ca.pem \
    --report output/verification_report.md
```

Exits non-zero if any check fails. `--report` has no default on purpose: a
verifier that writes somewhere by default eventually overwrites the wrong
report.

Twelve checks, all currently passing:

| Check | What it protects against |
|---|---|
| Document count | a partial bulk load |
| Field types against Esri's mapping table | a type ArcGIS renders as an unusable text column |
| `location` is `geo_point` | no geometry at all |
| `dynamic: strict` | schema drift after publishing |
| Not the object format | the silent failure from finding 1 |
| Value decodes per the spec | a malformed geometry |
| Geometry agrees with the `latitude`/`longitude` fields | a document disagreeing with itself |
| Coordinate provenance against the CSV | a coordinate quietly moved to another plausible spot |
| `geo_bounding_box` over NRW matches all 449 | axis order, refereed by the search engine |
| Axis-swapped box matches nothing | the same, from the other side |
| `geo_distance` vs. an independent haversine | a `geo_point` that is stored but not indexed |
| SQL plugin (INFO) | finding 3 |

Two of these are cross-checks in the sense the repository means it: the axis
order is decided by OpenSearch answering two queries rather than by our own
code, and `geo_distance` is compared against a haversine written in the
verifier. The provenance check is the one that makes "nothing was invented"
verifiable - it asserts that every sampled coordinate coming back out of the
index is byte-identical to the CSV row with the same DS100 code.

### Stop it again

```bash
./scripts/run_opensearch.sh stop      # or: status, logs
rm -rf build/                          # removes the installation entirely
```

---

## The index

Index `nrw_stations`, 449 documents, 120 KB on disk, `green`.

| Field | OpenSearch type | ArcGIS type | Note |
|---|---|---|---|
| `_id` | system | Object ID | the DS100 code; makes reloading idempotent |
| `station_oid` | `integer` | Long Integer | 1…449, for the "integer field with unique values" option in Pro |
| `ds100` | `keyword` | Text | |
| `name` | `text` (+ `.keyword`) | Text | full-text searchable, which is the reason to use a search engine |
| `district` | `keyword` | Text | |
| `latitude`, `longitude` | `double` | Double | EPSG:4326; redundant for drawing, which is why they are kept - the verifier compares against them |
| `location` | `geo_point` | **Geometry** | `[longitude, latitude]` |
| `x_3857`, `y_3857` | `double` | Double | carried over as attributes; ArcGIS projects from 4326 itself |
| `source_rows` | `integer` | Long Integer | how many source rows this station had |
| `position_spread_m` | `double` | Double | the positional uncertainty from `open_data_search`, not dropped |

The mapping is explicit and `dynamic: strict`. A search engine will happily
infer a field type from the first document it sees, and ArcGIS then inherits
that guess; declaring the mapping makes the field types a decision, and `strict`
turns a typo into an error instead of a new field.

One example document:

```json
{"station_oid": 1, "ds100": "KA", "name": "Aachen Hbf",
 "district": "Kreis Städteregion Aachen",
 "latitude": 50.76756, "longitude": 6.09124,
 "location": [6.09124, 50.76756],
 "x_3857": 678073.74, "y_3857": 6580280.31,
 "source_rows": 3, "position_spread_m": 632.1}
```

### Try a query

```bash
# full text, the reason for a search engine
curl -s --cacert build/tls/root-ca.pem -u "admin:DevSummit#2026os" \
  "https://localhost:9200/nrw_stations/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"size":3,"query":{"match":{"name":"Hbf"}}}'

# everything within 30 km of Köln Hbf
curl -s --cacert build/tls/root-ca.pem -u "admin:DevSummit#2026os" \
  "https://localhost:9200/nrw_stations/_count" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"geo_distance":{"distance":"30km",
       "location":{"lat":50.94647,"lon":6.95523}}}}'
```

---

## Connecting from ArcGIS

**Not tested here.** There is no ArcGIS installation in this environment, so
everything in this section is derived from Esri's documentation for Pro 3.7 /
Enterprise 12.1 rather than from a working connection. The OpenSearch side is
tested; this side is documented. Verifying it is the obvious next step.

### ArcGIS Pro 3.7

1. Import `build/tls/root-ca.pem` into the Windows certificate store under
   *Trusted Root Certification Authorities* (`certmgr.msc` → Action → All Tasks
   → Import). Skipping this gives a TLS error, not a login error.
   Be aware that ArcGIS Pro has been reported not to honour the Windows store in
   every case - if the connection still fails after a correct import, that is a
   known class of problem rather than a mistake in the setup.
2. *Catalog* pane → right-click **Databases** → **New Database Connection**.
3. *Database Platform*: **OpenSearch**. *Host URL*: `https://localhost:9200`
   (append `:port` only if it is not 443/80 - here it always is).
4. *User Name* `admin`, *Password* `DevSummit#2026os`. Basic authentication is
   the only kind ArcGIS supports for this platform.
5. **Validate**, then name the connection and click **OK** - this writes a
   `.dbconn` file into the project.
6. Drag `nrw_stations` from the connection onto the map, or use *New Query
   Layer* for a subset. Notes that matter:
   - The spatial reference is **always SRID 4326 / GCS WGS 1984**, not
     configurable. No z, no m values.
   - Only **one** geometry field per layer, and nested geometry fields are not
     supported.
   - ArcGIS takes the geometry type from the **first row**, so a mixed index
     would be read as whatever it happened to see first. Here every document is
     a point.
   - `_id` becomes the Object ID automatically; `station_oid` is there if an
     integer ID is wanted instead.
   - Only a SQL subset works: comparisons, `AND`/`OR`/`NOT`, `LIKE`, `IN`,
     `BETWEEN`, `IS NULL` - no joins, no relates.
   - Feature binning is enabled automatically for document databases.
   - Fields cannot be created in an OpenSearch index from ArcGIS. The mapping
     is the schema, and it comes from `index_stations.py`.

### Publishing to ArcGIS Enterprise 12.1

1. In Pro: *Share* tab → **Data Stores** → **Add** → **Database**, give it a
   title and select the connection from above. For OpenSearch the *server*
   database connection must be **the same** as the publisher connection - the
   option to give a separate one is disabled. Select the federated server and
   validate.
2. *Share* → **Web Layer** → under **Reference registered data** choose
   **Feature**. This publishes a web feature layer that references the index
   instead of copying it.
3. Known limits: **Save As SD is not supported** for layers published from
   OpenSearch; only the *Server* drop-down is available, so no custom folder;
   basic authentication is mandatory.

**One contradiction to expect**, straight out of Esri's own documentation:
*"Sharing query layers from Elasticsearch or OpenSearch is not supported"* sits
next to the *Reference registered data → Feature* workflow above. The most
likely reading is that a hand-written query layer cannot be shared while a table
added from the connection can - but the two statements are not reconciled
anywhere, and the drag-a-table path also produces a query layer. Worth finding
out on the first publish attempt.

---

## Reproducibility

- **Model / date**: scripts and documentation written with Claude Opus 5,
  2026-08-21. The web research that produced the findings above (Esri's
  documentation for Pro 3.7 / Enterprise 12.1, the OpenSearch 2.12 release
  notes) was done in the same session.
- **No randomness anywhere**: the index is a deterministic transform of the CSV.
  Same input, same 898 NDJSON lines. No seed to fix.
- **OpenSearch 2.12.0**, SHA-512 pinned in `input/opensearch_dist.json`
  (linux-x64: `02af3abe…afca90`), verified on every download.
- **Commands that produced the committed output**:

  ```bash
  cd opensearch
  python3 scripts/index_stations.py --dry-run
  ./scripts/setup_opensearch.sh --host localhost
  ./scripts/run_opensearch.sh start
  python3 scripts/index_stations.py --recreate \
      --host https://localhost:9200 --ca-cert build/tls/root-ca.pem
  python3 scripts/verify_index.py \
      --host https://localhost:9200 --ca-cert build/tls/root-ca.pem \
      --report output/verification_report.md
  ```

- **Tested on Linux** (x86-64, Python 3.12), end to end: download, checksum,
  certificate generation, start, index, verify, stop. The `.bat` scripts were
  written from the Windows documentation, and running them on Windows turned up
  the two credential defects described under [Credentials](#credentials) - the
  swallowed `!` and the un-wiped data directory. With those fixed, **setup,
  start and the admin login are confirmed working on Windows**. The ArcGIS side
  is still untested.
- **Attribution** for the data carried through this use case: DB InfraGO AG /
  Deutsche Bahn AG, licensed CC BY 4.0 - see
  [`../open_data_search/README.md`](../open_data_search/README.md). OpenSearch
  itself is Apache-2.0 and is not redistributed here.

---

## Notes for the talk

- **What worked.** The research, and it is the part that matters. Not one of the
  five findings above is in a tutorial: the format restriction is a single
  sentence in a data-type table, the expired demo CA is only visible in
  `openssl x509 -dates`, the SQL-plugin conflict only exists if you ask both
  sides the same question. Reading two products' documentation *against each
  other* and then measuring the overlap is work a language model is genuinely
  good at, and it turned "I only know that it is supposed to work" into a
  documented setup in one session.
- **What failed.** Four times, and each one was informative. The demo TLS
  configuration of the certified release is expired, so the documented quick
  start is dead. Fixing it with one self-signed certificate hit an undocumented
  filter in OpenSearch Security (`CA:true` certificates are dropped from the
  server chain). The format the SQL plugin demands is precisely the one ArcGIS
  forbids - a contradiction with no clean resolution from this side. And the
  Windows port of the setup script chose a demo password containing `!`, which
  `cmd.exe` silently removes - so the node and the documentation disagreed by
  one character, while the status check agreed with the node because it was
  written in the same language and mangled it identically.
- **The measurement to show.** The object-format index passes eleven of twelve
  checks. Document count, bounding box, distance query, provenance - all green,
  and the layer will not open in ArcGIS. Put the two verification tables side by
  side: the loud failure (swapped axes, five checks red) next to the silent one
  (wrong container, one check red). Same data, same engine, same queries.
- **Lesson learned.** When generated data has a consumer, correctness is two
  questions, not one: is the data right, and can the consumer read it? The
  second one is answered by the consumer's documentation, and no amount of
  testing against the database will substitute for it - the database is happy
  with all of it.
