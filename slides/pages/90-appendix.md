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
