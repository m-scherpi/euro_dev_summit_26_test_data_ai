<div class="eyebrow">Use case 2 / 5 · open_data_search</div>

# Finding the right data is the actual work

<div class="lead">

Sometimes generated points are not enough and you want real ones. 
<br/> Then the expensive part is not the transformation — it is the search.

</div>

<div class="steps">
<div><b>Search</b> open data portals for something current, complete and with coordinates.</div>
<div><b>Check the licence first</b> — before looking at the data quality at all.</div>
<div><b>Then</b> write the transformation, and prove every coordinate came from the source.</div>
</div>

<div class="note">
This one was an experiment, to see what is possible. The target format was a
CSV for a Hosted Feature Layer again.
</div>

<!--
35s. This inverts use case 1. The model does no inventing here at all: it
searches, reads licence pages, checks whether download links still work, and
writes the converter. That search is hours of clicking through portals, and it
is the half a model is genuinely good at.
-->

---
layout: default
---

<div class="eyebrow">Use case 2 / 5 · open_data_search</div>

# 449 real railway stations

<div class="result">

<div class="shot-frame"><img src="/img/nrw_stations.png" class="shot-big" /></div>
<div class="credit text-center">449 DB InfraGO stations · ArcGIS Pro · Esri, TomTom, Garmin, USGS, FAO, NOAA, Land NRW</div>

<div class="rule">
Seven sources were checked, one was usable. OpenStreetMap was the best of them
— and we still could not take it, because its licence does not fit our
repository.
</div>

</div>

<!--
55s. Name the ODbL point once and simply: OSM asks that anything derived from it
stays under the same licence, and this repository is CC BY, so the best data set
was out on legal grounds alone. That is why the licence check comes first: a
data set you may not use has no quality worth measuring.
-->
