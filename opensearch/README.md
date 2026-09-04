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

Seven things were measured here that no amount of reading would have produced.
The last two came out of the publish attempt, and both are corrections of what
this file previously claimed.

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

### 6. The unsupported option is the one that looks default

Publishing the working Pro layer fails with `Layer's Datasource is not
supported`. The *Share* > *Web Layer* pane offers a check box labelled
**Feature** in two places - under **Copy all data** and under **Reference
registered data** - and for OpenSearch exactly one of them works. The error
message names neither the check box nor OpenSearch.

An earlier version of this file recorded a contradiction in Esri's
documentation here. There is none, and the mistake is worth keeping. It quoted:

> Sharing query layers from Elasticsearch or OpenSearch is not supported

The sentence does not end there:

> Sharing query layers from Elasticsearch and OpenSearch as a map image layer or
> web feature layer **that copies all data**, a web tile layer, a vector tile, a
> web scene layer, or a map service is not supported.
>
> You can only publish data from Elasticsearch or OpenSearch as map image layers
> or web feature layers **that reference registered data** to ArcGIS Enterprise
> 12.0 or later.

It is an enumeration of what is excluded, and the supported route survives in
the half that was cut off. A shortened quote reads exactly like a vendor being
inconsistent - which is a comfortable conclusion, and it stops the search.

The parallel to finding 2 is exact, and inverted. There the loud failure was the
harmless one. Here the fatal choice is the quiet one: two identical labels, no
warning, and an error that arrives one dialog too late to say which one was
meant. See [Publishing to ArcGIS Enterprise](#publishing-to-arcgis-enterprise-121)
for the corrected procedure.

### 7. One certificate, three trust stores, and two belong to the same product

With the right check box ticked, publishing gets further and stops in the
ArcGIS Server log:

```
The certificate authority is invalid or incorrect
(WinINet ERROR_INTERNET_INVALID_CA, 12045), URL = https://localhost:9200
```

Read it carefully, because it says three useful things at once.

**It is not a name mismatch.** WinINet has a separate code for that
(`ERROR_INTERNET_SEC_CERT_CN_INVALID`, 12038). 12045 means the chain was
rejected, and the certificate is fine: `CN=localhost`, SAN
`DNS:localhost, IP:127.0.0.1, IP:::1`, issued by a `CA:TRUE, pathlen:0` root and
valid to 2036. Only the trust is missing.

**It also retracts part of what this file predicted.** The section below warned
that a `.dbconn` pointing at `localhost` would send the federated server looking
for a cluster on its own machine. WinINet got far enough to *do a TLS handshake*
with something at `https://localhost:9200`, so in this deployment ArcGIS Server
and OpenSearch are on the same machine and the warning does not bite. It stands
for a split deployment; it was not the blocker here. Left in place, marked.

**And it is a Windows store scoping problem, which is why Pro was happy.**
ArcGIS Pro runs as the interactive user; ArcGIS Server runs as a service
account. `certmgr.msc` - which this file recommended - is *Certificates, Current
User*. It makes Pro trust the CA and leaves every service on the same machine
untrusting it. The machine-wide store is `certlm.msc`, *Certificates, Local
Computer*, and that is the one WinINet consults for a service. Esri's own
knowledge base entry for this exact error (000013244) resolves it the same way,
by importing the root into *Trusted Root Certification Authorities* of the
**Local Computer** store.

So one host, one certificate, two clients, two different answers - and the
component that failed is the one that never showed a dialog. The trust store is
per-principal, and "I imported the certificate" is not a statement about the
machine.

**Then it happens a second time, to the same product.** With the root in the
Local Computer store and the service restarted, WinINet is satisfied and the
error changes:

```
javax.net.ssl.SSLHandshakeException: (certificate_unknown) PKIX path building
failed: sun.security.provider.certpath.SunCertPathBuilderException: unable to
find valid certification path to requested target
```

That is not Windows any more. `PKIX` and `sun.security.provider` are the JVM,
and **a JVM does not read the Windows certificate store** - it reads its own
`cacerts`. ArcGIS Server is part native and part Java, it opens this connection
through the OpenSearch Java client, and so the same product needs the same
certificate imported **twice, into two unrelated stores**. Fixing the first one
is what makes the second one visible.

The score, then, for one self-signed CA on one machine:

| Consumer | Trust store | How it is fed |
|---|---|---|
| ArcGIS Pro | Windows, **Current User** | `certmgr.msc` |
| ArcGIS Server, native stack (WinINet) | Windows, **Local Computer** | `certlm.msc` + service restart |
| ArcGIS Server, **JVM** | its own `cacerts` | Server Admin Directory → `importRootOrIntermediate` |
| Portal for ArcGIS, JVM | *another* `cacerts` | Portal Admin → *Import Root or Intermediate Certificate* |

Four stores, four mechanisms, three error messages, and each one only becomes
observable once the previous is fixed. Every step of that cascade was a
*successful* verification of something - Pro connected, the machine store
validated - and none of them was evidence about the next consumer in the line.

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

**Tested end to end on 2026-09-04**, against a real ArcGIS Pro 3.7 and ArcGIS
Enterprise 12.1 on Windows. The database connection validates over the private
CA, the index drags onto the map as a query layer, all 449 stations draw, the
attributes and pop-ups are correct, and the automatic feature binning this
section predicted from the documentation is there. **The layer then publishes to
Enterprise as a web feature layer referencing the index** - it opens in Map
Viewer and serves its own pop-ups without a copy of the data existing anywhere.

It took three attempts to get there, and the three failures are
[finding 6](#6-the-unsupported-option-is-the-one-that-looks-default) and
[finding 7](#7-one-certificate-three-trust-stores-and-two-belong-to-the-same-product) -
the wrong check box, then two of the four trust stores.

![nrw_stations from OpenSearch as a query layer in ArcGIS Pro 3.7 - all 449
stations drawn over a topographic basemap, with the pop-up for Münster (Westf)
Hbf showing the indexed attributes and the Contents pane showing the automatic
feature binning](input/nrw_stations_opensearch_viewlayer.png)

*Basemap: World Topographic Map - Esri, TomTom, Garmin, FAO, NOAA, USGS. ArcGIS
Pro does not render the attribution bar into the map view, so it is named here
instead; the capture itself is uncropped.*

And the same index once more, three steps later - published out of Pro, served
by Enterprise, opened in the browser. Nothing here is a copy: every attribute in
the pop-up is read out of OpenSearch on demand.

![The published web feature layer 'Nrw stations' open in the ArcGIS Enterprise
Map Viewer, all 449 stations drawn, with the pop-up for Münster (Westf) Hbf
showing name, _id EMST, district, latitude, longitude, position_spread_m,
source_rows, station_oid and the EPSG:3857 coordinates](input/nrw_stations_opensearch_service.png)

*Basemap: Esri World Topographic Map, attribution bar intact at the bottom edge -
`Land NRW | LGLN | Esri | TomTom | Garmin | USGS | FAO | NOAA`.*

Two details in that pop-up are worth a second look, because both were predicted
in writing before anyone could test them. `_id` is `EMST`, the DS100 code - the
index's document id became the Object ID, exactly as
[the Pro notes](#arcgis-pro-37) said it would. And `x_3857` / `y_3857` come
through as plain attributes (`850,026.73` / `6,792,265.72`) while the geometry
is drawn from `location` alone, which is the whole point of keeping the
projected values as data rather than as geometry.

### ArcGIS Pro 3.7

1. Import `build/tls/root-ca.pem` into the Windows certificate store under
   *Trusted Root Certification Authorities*. **Use `certlm.msc`, not
   `certmgr.msc`** - see [finding 7](#7-one-certificate-three-trust-stores-and-two-belong-to-the-same-product).
   `certmgr.msc` writes into the *current user's* store, which is enough for Pro
   and not enough for anything running as a service. Action → All Tasks →
   Import. Skipping this gives a TLS error, not a login error.
   Be aware that ArcGIS Pro has been reported not to honour the Windows store in
   every case - if the connection still fails after a correct import, that is a
   known class of problem rather than a mistake in the setup.
2. *Catalog* pane → right-click **Databases** → **New Database Connection**.
3. *Database Platform*: **OpenSearch**. *Host URL*: `https://localhost:9200`
   (append `:port` only if it is not 443/80 - here it always is). If this
   connection is later meant to be published, `localhost` will not do - see
   [the `localhost` problem](#publishing-to-arcgis-enterprise-121).
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

**This works, and it took three attempts.** There is exactly one supported
route, the pane offers the unsupported one right next to it under the same
label, and two of the four certificate trust stores involved have to be fed by
hand. The procedure below is the one that succeeded on 2026-09-04; the first
attempt failed with `Layer's Datasource is not supported`. What can and cannot
be published from an OpenSearch query layer:

| Target | Supported |
|---|---|
| Web feature layer, **reference registered data** | yes, Enterprise 12.0+ |
| Map image layer, **reference registered data** | yes, Enterprise 12.0+ |
| Web feature layer, **copy all data** | no |
| Map image layer copy-all-data, web tile, vector tile, web scene, map service | no |
| Hosted feature layer on ArcGIS Online | no - that is copy-all-data |

Registering the data store has to come first. Esri describes the second box as
an *"additional Feature option"* that *"may be available"* under *Reference
registered data* when publishing from Elasticsearch or OpenSearch to Enterprise
12.0+ - so if only one *Feature* box is visible, the registration is the thing
that is missing, and the analyzer will say so as **00231** (*layer's data source
must be registered with the server*) rather than as the 24078/00134 above.

1. In Pro: *Share* tab → **Data Stores** → **Add** → **Database**, give it a
   title and select the connection from above. For OpenSearch the *server*
   database connection must be **the same** as the publisher connection - the
   option to give a separate one is disabled. Select the federated server and
   validate.
2. *Share* → **Web Layer**. **Clear the *Feature* check box under *Copy all
   data*** - that is the default-looking one and the one that produces the
   error. Check the *Feature* box under **Reference registered data** instead.
   This publishes a web feature layer that references the index rather than
   copying it.
3. Known limits: **Save As SD is not supported** for layers published from
   OpenSearch; only the *Server* drop-down is available, so no custom folder;
   basic authentication is mandatory. Enterprise must be **12.0 or later** -
   registering an Elasticsearch or OpenSearch database is not supported before
   that.

**Then the ArcGIS Server has to trust the CA too, and separately - twice.** This
is [finding 7](#7-one-certificate-three-trust-stores-and-two-belong-to-the-same-product),
and it is where the remaining two attempts went. Publishing stops first with
`The certificate authority is invalid or incorrect (WinINet
ERROR_INTERNET_INVALID_CA, 12045)` in the server log, and then, once that is
fixed, with a Java error instead. All four steps below were needed. Do step 1
before step 2, because a service restart is disruptive and the query that
decides whether it can help is free:

1. **The root must be in the *Local Computer* store**, not the current user's.
   Measure it - the two are indistinguishable in the Pro client's behaviour:

   ```powershell
   # what a service sees - this one must return the certificate
   Get-ChildItem Cert:\LocalMachine\Root | Where-Object { $_.Subject -like '*DevSummit Local Test CA*' }
   # what certmgr.msc writes to - Pro is happy with only this
   Get-ChildItem Cert:\CurrentUser\Root  | Where-Object { $_.Subject -like '*DevSummit Local Test CA*' }
   ```

   If only the second returns something, import `build/tls/root-ca.pem` again
   via `certlm.msc` → *Trusted Root Certification Authorities* → *Certificates*
   → Action → All Tasks → Import.
2. **Restart the ArcGIS Server Windows service.** The service process does not
   pick up a certificate added to the store while it was running, so an import
   done during cluster setup has no effect on a server that has been up since
   before it. Necessary whether or not step 1 changed anything - which is also
   what makes the two hard to tell apart afterwards, so note which one was
   actually wrong.
3. **Import the root into the ArcGIS Server JVM as well.** When steps 1 and 2
   are done the WinINet error is replaced by a Java one:
   `javax.net.ssl.SSLHandshakeException: (certificate_unknown) PKIX path
   building failed`. Same certificate, same URL, different runtime - the JVM
   ignores the Windows store entirely. Use the **Server Administrator
   Directory**, not `keytool`:

   `https://<server>:6443/arcgis/admin` → **machines** → *<MACHINE.DOMAIN>* →
   **sslcertificates** → **importRootOrIntermediate** → `alias` e.g.
   `devsummit-ca`, `rootCACertificate` = `build/tls/root-ca.pem` → *Import*.
   Then restart the machine's ArcGIS Server service once more.

   Do **not** run `keytool` against
   `...\ArcGIS\Server\framework\runtime\jre\lib\security\cacerts` even
   though it works. An upgrade replaces that JRE, the trust disappears with it,
   and the failure resurfaces months later with no connection to the change that
   caused it. The admin-directory import is the route Esri supports.
4. **Portal for ArcGIS has its own truststore**, fed the same way from the
   portal admin directory (*Security* → *SSLCertificates* → *Import Root or
   Intermediate Certificate*), followed by a Portal restart. Publishing runs
   Pro → Portal → Server, so this is where the Java error goes next if it moves
   from the server log to the portal log.

With those done, *Share* → *Web Layer* → **Reference registered data** →
**Feature** publishes, and the layer opens in Map Viewer. Nothing is copied:
the pop-ups are answered out of the OpenSearch index at request time.

Turning TLS off is not an escape route here: ArcGIS needs basic authentication,
`--insecure` removes authentication along with TLS, and security-on-with-plain-
HTTP has been an unsupported OpenSearch configuration since 2.12. The
certificate has to be trusted; there is no third option. That is the same wall
as in [finding 4](#4-the-certified-release-ships-a-tls-configuration-that-expired-in-2023).

**The `localhost` problem - predicted, and measured not to apply here.**
Inference from two documented rules rather than a quoted statement: the server
database connection cannot differ from the publisher connection, so the
federated ArcGIS Server receives the literal string the `.dbconn` carries and
resolves it on *its own* machine. A connection to `https://localhost:9200` would
then point the server at a cluster that is not there.

It did not bite. The 12045 in
[finding 7](#7-one-certificate-three-trust-stores-and-two-belong-to-the-same-product)
is a *TLS* rejection, which means WinINet completed a handshake with something
at `https://localhost:9200` - ArcGIS Server and OpenSearch are on the same
machine in this deployment. The warning is kept because it is correct for a
split one, where the cluster has to answer to one name from both machines:

```bash
./scripts/setup_opensearch.sh --host gis-vm-01.example.lan --force
```

`--force` because the certificate and the SANs are written at setup time, and
because the admin password lives in `build/data` after the first start - see
[Credentials](#credentials). Two more things then have to be true: the node must
bind beyond loopback (`network.host` / `http.host` in
`build/opensearch-2.12.0/config/opensearch.yml`), and `build/tls/root-ca.pem`
must be trusted **on the
ArcGIS Server machine as well** - the OS/JVM trust store there, not the Windows
store the Pro client uses.

**If the Enterprise route stays blocked**, the one option that produces a real
FeatureServer without any Enterprise is a [Koop](https://koopjs.github.io/)
server in front of the index -
[`@koopjs/provider-elasticsearch`](https://github.com/koopjs/koop-provider-elasticsearch),
Apache-2.0, with OpenSearch connections supported in beta via an `osConnections`
block. It translates the index into the GeoServices REST API that Pro, Portal
and ArcGIS Online all speak. Not built here; noted so the option is on record.
Its SQL-based sibling, `koop-provider-elastic-sql`, would run straight into
[finding 3](#3-there-is-no-format-both-arcgis-and-the-opensearch-sql-plugin-can-read)
and is the wrong one for this index.

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
  start and the admin login are confirmed working on Windows**.
- **What is confirmed on the ArcGIS side, 2026-09-04**: ArcGIS Pro 3.7 connects
  over the private CA, the index draws as a query layer, attributes and pop-ups
  are correct, feature binning is automatic. Evidence:
  `input/nrw_stations_opensearch_viewlayer.png`.
- **Publishing to Enterprise 12.1 is confirmed too**, after three failures: the
  wrong *Feature* check box, the ArcGIS Server service not trusting the private
  CA in the Windows Local Computer store (WinINet 12045), and its JVM not
  trusting it either (PKIX path building failed). Evidence:
  `input/nrw_stations_opensearch_service.png`. The procedure that worked is in
  [Publishing to ArcGIS Enterprise](#publishing-to-arcgis-enterprise-121). The
  research behind it was done with Claude Opus 5 on 2026-09-04, against Esri's
  analyzer message 24078, *Share a web feature layer*, *Manage registered data
  stores*, *Connect to OpenSearch from ArcGIS* (Server 12.0), the *Import Root
  or Intermediate Certificate* admin operation and Esri knowledge base entries
  000013244 and 000031906.
- **Not reproducible from this repository, and deliberately so**: the ArcGIS
  half needs a licensed Pro and a federated Enterprise 12.1. The OpenSearch half
  - download, checksum, certificates, index, verify - runs from a bare VM with
  nothing installed, and `verify_index.py` is what stands in for the client when
  no client is available.
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
- **The retraction is the best thing in this folder.** The previous pass
  recorded a contradiction in Esri's documentation and was rather pleased with
  it. There was none: our own quote had been cut off before the enumeration that
  resolves it, and the supported publishing route was in the half that went
  missing. A shortened quote is indistinguishable from a vendor being
  inconsistent, and "the documentation contradicts itself" is a comfortable
  place to stop looking.
- **"It works in the client" is not a test of the server.** The private CA was
  imported once and ArcGIS Pro connected, which made the certificate look
  settled. ArcGIS Server on the *same machine*, against the *same URL*, with the
  *same certificate*, rejected it - because a Windows trust store belongs to a
  principal, and the tool the documentation named (`certmgr.msc`) writes to the
  one the interactive user reads. The component that failed is the one with no
  dialog to show.
- **It works, and the four slides' worth of material is in how.** The finished
  result is one screenshot of a map in a browser, and behind it: one wrong check
  box that looks like the right one, and two of four trust stores that had to be
  found one at a time because each fix only revealed the next. Three failures,
  none of them in the data, all of them in the seam between two products.
- **One product, two trust stores.** The best version of that point, because it
  removes the excuse. Pro and Server being different programs is easy to
  believe. ArcGIS Server needing the *same* certificate imported twice - once
  into the Windows Local Computer store for its native stack, once into its JVM
  through the admin directory - is not something a mental model of "the machine
  trusts this CA" survives. And each import only made the next failure visible;
  every step of the cascade was a successful verification of something.
- **Lesson learned.** Verify against the consumer - and note that "the consumer"
  is a list, not a thing, and that one product can appear on it more than once.
  Pro, the server's native stack, the server's JVM and Portal are four consumers
  of one certificate; the SQL plugin and ArcGIS are two consumers of one
  geometry. In every case the next consumer had a requirement the previous one
  never surfaced. Quote each of them to the full stop.
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
