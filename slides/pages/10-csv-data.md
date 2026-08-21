---
layout: default
---

<div class="eyebrow">Act 1 · the model writes the data</div>

# 100 geo points, straight from the model

<div class="cols-img">
<div>

**What it got right** — first try, no retries:

- 100 unique titles, 100 genuinely distinct descriptions
- correct CSV quoting, plausible value ranges
- `latitude` and `longitude` **never swapped**, in any of the 100 rows

<div v-click class="mt-5">

**And one bug you can just see.** I asked for North Rhine-Westphalia. It sampled
a *rectangle around* North Rhine-Westphalia.

<div class="metric mt-2">41 of 100</div>

points are in the Netherlands, Belgium or Hesse.

</div>
</div>
<div>

<img src="/img/nrw_points.png" class="shot" />

<div class="credit">ArcGIS Pro · basemap Esri, TomTom, Garmin, USGS, FAO, NOAA</div>

</div>
</div>

<!--
45s. Lead with the successes and mean them -- the prose is genuinely good and
that matters at the end. Then point at the dots in the Netherlands: first bug,
and it is the easy kind, because you can see it.

A bounding box is not a boundary. That is the throwaway rule of this slide; the
next two are the ones worth remembering.
-->

---
layout: default
---

<div class="eyebrow">Act 1 · the fix, and what it cost</div>

# Same request, 10,000 rows, a real polygon

<div class="cols-img">
<div>

A seeded generator instead of the model, rejection-sampling against a
licence-checked boundary of Germany.

<div class="metric mt-3">0 of 10,000</div>

outside the country. Price: **55 % more candidate draws**, in four lines of code.

<div v-click class="mt-5">

**The honest half of the trade:** 100 hand-written descriptions were 100 distinct
sentences. 10,000 templated ones are 9,947 distinct *strings* — and structurally
far more repetitive.

<div class="text-lg font-medium mt-2">100× the data, measurably worse writing.</div>

</div>
</div>
<div>

<img src="/img/germany_points_10k.png" class="shot" />

<div class="credit">ArcGIS Pro · basemap Esri, TomTom, Garmin, USGS, FAO, NOAA</div>

</div>
</div>

<!--
45s. The geometry got better and the language got worse. Say that plainly -- it
is the most useful sentence in act 1 for anybody deciding where to spend a model.

Prose and fixtures: model. Numbers with a formula behind them: code.
-->

---
layout: default
---

<div class="eyebrow">Act 1 · the bug you cannot see</div>

# Both files also carried Web Mercator

```python {1|3|all}
x_3857 = lon * 20037508.34 / 180

y_3857 = log(tan((90 + lat) * pi / 360)) / (pi / 180) * 20037508.34 / 180
```

<div class="cols mt-2">
<div v-click>

**`x_3857`** — one multiplication.

<div class="metric mt-1">6 cm</div>

off, across all 100 rows.

</div>
<div v-click>

**`y_3857`** — one logarithm.

<div class="metric mt-1">490 m</div>

off, across all 100 rows.

</div>
</div>

<div v-click class="mt-4">

The model did not compute that logarithm — it **interpolated between remembered
anchor latitudes**, and interpolating a convex function along a chord always
overshoots the same way. So the error is a *systematic northward bias in 100 of
100 rows*. It survives averaging, it survives spot-checking, and every point
still sat in the right region.

</div>

<div v-click class="rule">
Rule 1 — never let a model own a number that has a formula behind it.
</div>

<!--
75s. The most important slide of act 1. Take the clicks slowly.

The shape of the failure is the lesson, not the size: one multiplication is
fine, one logarithm is not, and the error is directional rather than random --
which is exactly why every cheap check misses it. An independent recomputation
found it, and nothing else did.

"Independent" means the verifier must not import the generator's formula. Here
both were hand-written, deliberately in different forms:
ln(tan(pi/4 + phi/2)) against atanh(sin phi).
-->
