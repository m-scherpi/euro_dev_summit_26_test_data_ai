---
layout: default
---

<div class="eyebrow">Act 2 · the model searches, and invents nothing</div>

# The licence check comes before the geometry check

<div class="cols">
<div>

Inverted setup: the model does the **research** and writes the **code**. Not one
coordinate comes from it.

The research was the expensive half — **7 candidate sources**, 6 live HTTP
checks, 1 dead domain — and it is work a model is genuinely good at.

<div v-click class="mt-4">

OpenStreetMap won on every technical axis, and was still unusable here. A CSV of
rows *extracted* from OSM is a **Derivative Database**, not a Produced Work — so
share-alike bites, and it cannot be relicensed as CC BY.

</div>
</div>
<div>

| Licence | Attribution | Share-alike | CC BY repo |
|---|---|---|---|
| CC0, dl-de/zero | no | no | ✅ |
| CC BY 4.0, dl-de/by | yes | no | ✅ |
| **ODbL** (OSM) | yes | **yes** | ❌ |

<div v-click class="rule text-lg">
Rule 2 — licence before geometry. The best data set on the table can be unusable at any quality.
</div>

</div>
</div>

<!--
60s. Two things to land.

One: "open data" is not one licence, it is a ladder, and the rung decides before
quality does. CC0 is free, CC BY costs a sentence, ODbL costs your project's
licence.

Two: Derivative Database vs Produced Work is the part people get wrong. A map
image rendered from OSM is fine. A CSV of extracted rows is not. Publishing that
CSV on GitHub is perfectly legal -- putting it in a CC BY repository is not.
-->

---
layout: default
---

<div class="eyebrow">Act 2 · the result</div>

# 449 real stations, every coordinate traceable

<div class="cols-img">
<div>

**DB InfraGO** infrastructure register, CC BY 4.0. Built by a script the model
wrote, from a slice of the source committed next to it — URL, retrieval date,
licence, SHA-256.

<div v-click class="mt-4">

For *sourced* data, "is this value plausible?" is the wrong question:

```python
assert (lat, lon) in source_rows[station_id]
```

A single coordinate moved to a plausible spot inside the state passes the
bounding box, the polygon, the axis check **and** the projection check. Only
provenance catches it — in about fifteen lines.

</div>
</div>
<div>

<img src="/img/nrw_stations.png" class="shot" />

<div class="credit">ArcGIS Pro · basemap Land NRW, Esri, TomTom, Garmin, USGS, FAO, NOAA</div>

</div>
</div>

<!--
40s. Note the popup in the screenshot: position_spread_m = 93.3, source_rows = 6.
One station published at six different positions -- backup slide 1 if anyone
asks, and the reason the output carries its own uncertainty as a column.

The line to say out loud: for data somebody else published, plausibility is not
the test. "Did anyone actually publish this value?" is.
-->

---
layout: default
---

<div class="eyebrow">Act 2 · the finding I got wrong first</div>

# One station out of 449 failed the check

<div class="cols">
<div>

`HOE` **Osnabrück-Eversburg** — tagged *Nordrhein-Westfalen*, *Kreis Steinfurt*,
but **1.3 km outside** the state polygon. And the name says Osnabrück, which is
Lower Saxony.

<div v-click class="mt-3">

"Found one — the official data is wrong." I wrote that down.

</div>
<div v-click class="mt-3">

It was false.

- reverse geocoding: **Lotte, Kreis Steinfurt, NRW**
- authoritative Geobasis NRW boundary: **117 m inside**
- the generalised 1:10 M outline was the thing that was wrong

</div>
</div>
<div v-click>

Re-run with the authoritative boundary, across **all of Germany**:

<div class="metric mt-2">0 of 5,367</div>

in-service stations where the source's `Bundesland` attribute and the geometry
disagree — in either direction.

The attribute-versus-geometry check worked perfectly. The **yardstick** was
broken.

<div v-click class="rule text-lg">
Rule 3 — your reference data is data too. When a check fails on exactly one record, suspect the check.
</div>

</div>
</div>

<!--
75s. The best story in the repository, so give it room and tell it in order: the
check fires, the conclusion is obvious, the conclusion is wrong.

A 1:10 M generalised outline cannot answer a 100 m question. Match the precision
of the reference to the precision of the question.

Cost, if asked: adjudicating this ONE row took a reverse-geocoding lookup, an
authoritative Shapefile download, a fourth dependency and a Germany-wide re-run.
For published data that was right. For a staging database it would be
over-engineering -- so agree the depth up front instead of defaulting to rigour.
-->
