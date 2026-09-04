---
layout: section
---

# Backup

<div class="text-base opacity-70 mt-2">
Findings that did not fit into fifteen minutes. Kept written out, because the
question usually comes.
</div>

<!--
Not part of the talk. Reachable with the arrow key during questions, and
readable in the repository.

House rule for the coming use cases: a new one lands HERE first. It enters the
main deck only by displacing a rule whose finding is weaker. The slot does not
grow, so the deck must not either.
-->

---
layout: default
---

<div class="eyebrow">Backup 1 · open_data_search</div>

# One real-world feature, several published positions

The source is route-centric: one row per railway line through a station, each
carrying that line's own kilometre-marker coordinate.

<div class="grid grid-cols-2 gap-8 mt-4">
<div>

- **893 rows** describe **449 stations**
- **185** of them carry more than one position
- median spread among those: **326 m**
- worst case **Köln-Ehrenfeld: 4,047 m** across 6 rows
- Köln-Mülheim: **15 rows**

</div>
<div>

`dict[key] = row` silently keeps whichever row came last — a point up to ~2 km
off — and leaves a data set that looks immaculate.

**Fix:** pick the **medoid**, so the coordinate is one somebody actually
published and stays traceable. Then carry `position_spread_m` into the output,
because dropping the uncertainty is how it gets forgotten.

</div>
</div>

---
layout: default
---

<div class="eyebrow">Backup 2 · open_data_search</div>

# Redundant coordinate columns tell you which one to distrust

The source publishes every point in three CRS plus three WKT strings.

<div class="mt-4">

| Comparison | Disagreement |
|---|---|
| EPSG:25832 columns vs EPSG:4326 columns, recomputed with PROJ | **1 mm** |
| EPSG:4326 columns vs the `WKT WGS84` column of the *same row* | **1.27 m** median, 1.86 m max |

</div>

<div class="rule mt-6">
Two representations would only have shown a conflict. Three showed which one to believe.
</div>

---
layout: default
---

<div class="eyebrow">Backup 3 · opensearch</div>

# An old pinned version ships expired material

**Why 2.12.0 and not the latest?** Because ArcGIS Pro 3.7 and Enterprise 12.1
certify OpenSearch **2.12** — one minor release, not the 2.x line. A GIS client
pins its database support far harder than the database pins itself.

<div v-click class="mt-4">

The demo TLS **root CA** shipped with that release was issued in August 2023
with a **30-day validity**. The node certificate it signed runs to 2033.

So: the server starts, the chain looks plausible, and every client fails with
`certificate has expired`. The documented quick start is dead.

</div>

<div v-click class="mt-3">

Fixing it with a single self-signed certificate then hit an **undocumented**
filter: OpenSearch Security drops `CA:true` certificates from the server chain.

</div>

<div v-click class="rule">
When a pinned release is years old, check the expiry dates of what it ships before believing its quick start.
</div>

---
layout: default
---

<div class="eyebrow">Backup 4 · opensearch</div>

# Two subsystems of one product, incompatible formats

<div class="grid grid-cols-2 gap-8 mt-4">
<div>

**ArcGIS** reads a `geo_point` as
array, bare string or WKT.
It **cannot** read `{"lat": …, "lon": …}`.

</div>
<div>

The **OpenSearch SQL plugin** accepts
**only** `{"lat": …, "lon": …}`.
It rejects array, string, WKT and geohash alike.

</div>
</div>

<div class="mt-6">

ArcGIS query layers are SQL. Whether that makes this fatal depends on something
neither vendor documents.

</div>

<div class="rule">
Reported as an open finding with the measurement attached — not resolved by guessing, and not hidden because it did not break the current path.
</div>

---
layout: default
---

<div class="eyebrow">Backup 5 · csv_data</div>

# Two bugs of my own, worth more than the successes

<div class="mt-4">

**1 · A convenient default turned a read-only tool destructive.**
The verifier's `--output` defaulted to one data set's path. Verifying the *other*
file therefore overwrote the first one. There is no default now: if a flag writes
a file, it requires the path.

</div>

<div class="mt-6">

**2 · Round before projecting, not after.**
The generator projected unrounded coordinates and stored rounded ones, so every
row disagreed with itself by up to **1.09 m**. Invisible until an independent
recomputation compared the two.

</div>

<div class="rule">
Both were found by the verification, not by reading the code.
</div>

---
layout: default
---

<div class="eyebrow">Backup 6 · csv_data</div>

# Uniform in latitude is not uniform on the ground

A degree of longitude shortens towards the poles, so `uniform(lat_min, lat_max)`
over-samples the higher latitudes.

<div class="grid grid-cols-2 gap-8 mt-6">
<div>

Over Germany, that would have put

<div class="metric mt-2">18.5 %</div>

too many points in the north.

</div>
<div>

Sampling `sin(latitude)` uniformly instead measures out at a north/south density
ratio of

<div class="metric mt-2">0.994</div>

</div>
</div>

<div class="rule">
It looks like uniform sampling, it passes every check in the repository, and it is wrong. State which one you used.
</div>

---
layout: default
---

<div class="eyebrow">Backup 7 · open_data_search</div>

# Open-data portals rot — commit the slice, not just the URL

The download URL that every tutorial and every GitHub mirror still names for
German station data **no longer resolves at all**, and its successor portal is
mid-migration.

<div class="mt-4">

A documented command is not reproducibility if the document outlives the host.
So the repository commits:

- the **subset actually used**, verbatim
- a manifest with source URL, retrieval date, licence, attribution text and the
  **SHA-256** of the exact file it came from

</div>

<div class="rule">
That turns "we used this version" into a checkable claim — and it lets the pipeline run offline, on stage.
</div>

---
layout: default
---

<div class="eyebrow">Backup 8 · opensearch</div>

# No licence. So we rebuilt the data set.

A real export from a real Enterprise Geodatabase, handed over to prove a second
data source works — with **no licence statement**. Probably FAA-derived, and
*probably is not a licence*. Gitignored; only its **measured structure** was
rebuilt.

<div class="grid grid-cols-2 gap-6 mt-4">
<div>

Carried over: 880 features · a 6:1 category skew · `tot_enp` from 100 to
38,893,670 · 3 duplicate names · two unique object ids that agree in **no** row
· 825 "empty" values that are a single space

</div>
<div>

Two properties were wrong on the first attempt and **both looked plausible**: a
skew flattened to five equal buckets, a log-normal tail an order of magnitude
short.

<div class="metric mt-2">0</div>

values copied from the original

</div>
</div>

<div class="rule">
Not being allowed to use real data is why generated test data exists. Measure the original <em>before</em> you replace it.
</div>

---
layout: default
---

<div class="eyebrow">Backup 9 · opensearch</div>

# The same bug is loud or silent depending on where on Earth you are

Swap latitude and longitude in the index. Identical code, two data sets.

<div class="grid grid-cols-2 gap-6 mt-4">
<div>

**449 NRW stations**<br>
lat 50–52, lon 5–9 — both are valid latitudes

<div class="metric mt-2">449 / 449</div>

loaded happily, and landed in the Indian Ocean

</div>
<div>

**880 US airports**<br>
lon −178 … +167 — mostly *not* valid latitudes

<div class="metric mt-2">550 / 880</div>

rejected by the engine, load aborted

</div>
</div>

<div class="mt-3">

```
illegal latitude value [-97.302373] for location
```

</div>

<div class="rule">
The verifier that caught the stations was not better. It was luckier. Geography decided whether the bug had an error message.
</div>

---
layout: default
---

<div class="eyebrow">Backup 10 · opensearch</div>

# 1.9 nanometres broke the build

The committed fixture is pinned by SHA-256. Rebuilt on Windows with the **same
seed**: different hash, identical size, identical feature count.

<div class="grid grid-cols-2 gap-6 mt-4">
<div>

**Ruled out, in order**

Newlines — `Get-FileHash` matched the in-memory hash<br>
The seed — six RNG fingerprints identical, across CPython 3.12 and 3.14<br>
Attributes and ordering — identical

</div>
<div>

**What remained**

`x = R·radians(lon)` → **0 of 880** differ<br>
`y = R·log(tan(π/4+φ/2))` → **30 of 880**, up to 2 ULP

<div class="metric mt-2">1.9 nm</div>

libm is not standardised to the last bit

</div>
</div>

<div class="mt-3">

Fixed by storing **4 decimals** — the precision the real export had. At six,
rounding would not have helped, so the generator measures that margin and
refuses to write a fixture whose hash is reproducible by luck.

</div>

<div class="rule">
Five hex-float samples of <code>log</code>/<code>tan</code> were bit-identical on both machines. At a 3.4% divergence rate, five samples miss it 84% of the time.
</div>
