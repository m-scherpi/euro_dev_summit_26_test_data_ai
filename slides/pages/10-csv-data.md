<div class="eyebrow">Use case 1 / 5 · csv_data</div>

# Nobody clicks 10,000 points by hand

<div class="lead">

Sometimes a test needs volume. Drawing points in a map client is fine for ten
of them, but nobody does it for ten thousand.

</div>

<div class="steps">
<div><b>Ask</b> for geo points as a CSV — with names, descriptions and values that look real, in a small batch.</div>
<div><b>Then ask for the generator instead</b>: a small script with a fixed seed.</div>
<div><b>Run it</b> for 10,000 rows, and again tomorrow for the same 10,000 rows.</div>
</div>

<div class="note">
A CSV is what a Hosted Feature Layer in the portal may get published from — so
this was the target format.
</div>

<!--
35s. The point of this use case is volume and repeatability, not the points
themselves. The model's first answer is data; the better answer is the script
that makes the data, because a script can be run again with a different number.
The seed is what makes a demo survive to the next rehearsal.
-->

---
layout: default
---

<div class="eyebrow">Use case 1 / 5 · csv_data</div>

# 10,000 points, one command

<div class="result">

<div class="shot-frame"><img src="/img/germany_points_10k.png" class="shot-big" /></div>
<div class="credit text-center">10,000 generated points · ArcGIS Pro · Esri, TomTom, Garmin, USGS, FAO, NOAA</div>

<div class="rule">
The model also wrote the Web Mercator values — and every single one was wrong,
by up to 490 m. Every point still landed in the right region. Nothing looked
broken.
</div>

</div>

<!--
55s. This is the slide to slow down on. The text the model wrote was good. The
numbers it computed were not, and the error was the same direction in every row,
so an average or a spot check would never show it. Only recomputing the value
with code found it. Rule of thumb from this: let the model write the text and
the script, and let code own anything with a formula in it.
-->
