---
layout: default
---

<div class="eyebrow">Act 3 · the same data, now with a consumer</div>

# Eleven of twelve checks green. The layer will not open.

<div class="cols checks">
<div>

**Axes swapped** — the loud mistake

| | |
|---|---|
| document count | <span class="verdict-pass">pass</span> |
| bounding box | <span class="verdict-fail">fail</span> |
| `geo_distance` vs haversine | <span class="verdict-fail">fail</span> |
| coordinate provenance | <span class="verdict-fail">fail</span> |
| format ArcGIS accepts | <span class="verdict-pass">pass</span> |

<div class="mt-3 text-xl">
<span class="verdict-fail">5 of 12 red.</span> Points in another hemisphere.
</div>

</div>
<div v-click>

**`{"lat": …, "lon": …}`** — the quiet one

| | |
|---|---|
| document count | <span class="verdict-pass">pass</span> |
| bounding box | <span class="verdict-pass">pass</span> |
| `geo_distance` vs haversine | <span class="verdict-pass">pass</span> |
| coordinate provenance | <span class="verdict-pass">pass</span> |
| format ArcGIS accepts | <span class="verdict-fail">fail</span> |

<div class="mt-3 text-xl">
<span class="verdict-fail">1 of 12 red.</span> Geometry perfect. Unusable.
</div>

</div>
</div>

<!--
75s. Put the two tables next to each other and let the audience read them. The
449 stations again, this time as an OpenSearch 2.12 index for ArcGIS Pro 3.7,
twelve automated checks, two builds of the same data.

The object form is the FIRST example in the OpenSearch data-type docs, and the
one a model writes unprompted. ArcGIS cannot read it -- that restriction is a
single sentence in an Esri table, and in nobody's tutorial.

So: right by every measure the database can offer, and the layer does not open.
Meanwhile the swapped-axis version screams.
-->

---
layout: default
---

<div class="eyebrow">Act 3 · the rule</div>

# The loud error is the harmless one

<div class="cols">
<div>

Correctness was **two** questions, and I had been asking one:

1. Is the geometry right?
2. **Can the consumer read it?**

Question 2 is answered by the *consumer's* documentation. No amount of testing
against the database substitutes for it — the database is happy with all of it.

</div>
<div v-click>

And where a spec allows several encodings, they disagree:

| ArcGIS-readable form | Axis order |
|---|---|
| array | `[lon, lat]` |
| bare string | `"lat,lon"` |
| WKT | `POINT (lon lat)` |

Two of three put longitude first. The odd one out reads most like prose — so
parameterise it and let the engine referee the axis order.

</div>
</div>

<div v-click class="rule">
Rule 4 — verify against the consumer, not only against itself.
</div>

<!--
75s. Land the rule, then the axis-order table as the practical takeaway: never
assume an encoding when the spec offers three. Expose it as a flag and check it.

If asked why this is not resolved cleanly: the OpenSearch SQL plugin accepts
ONLY the object form -- exactly the one ArcGIS forbids. ArcGIS query layers are
SQL. Neither side documents the overlap, so it is logged as an open finding
rather than guessed away.
-->
