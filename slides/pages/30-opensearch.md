<div class="eyebrow">Use case 3 / 5 · opensearch</div>

# Test data for a technology we are new to

<div class="lead">

Test data is not only rows in a file. It is also the system that serves them —
and that system can be one we have barely used yet.

</div>

<div class="steps">
<div><b>Set up</b> a search engine from a script: download, certificates, users, index mapping.</div>
<div><b>Fill it</b> from two different sources — one of them handed over as “a GeoJSON”.</div>
<div><b>Publish it</b> as a layer that reads from the index and copies nothing — and opens in ArcGIS Pro.</div>
</div>

<div class="pt-4 text-sm opacity-80">
OpenSearch support in ArcGIS is young. A model reading two vendors' docs against
each other got us a working setup in one session.
</div>

<!--
40s. This is the "new technology" slide. The interesting part is not the data,
it is that the consumer is a service type we have little experience with, and
that support for it is recent enough that there are no tutorials to copy. That
is exactly the situation where reading documentation carefully is the whole job.
-->

---
layout: default
---

<div class="eyebrow">Use case 3 / 5 · opensearch</div>

# The index, live in ArcGIS

<img src="/img/nrw_stations_opensearch_service.png" class="shot-big" />
<div class="credit text-center">Web feature layer over OpenSearch · ArcGIS Enterprise · Land NRW, Esri, TomTom, Garmin, USGS, FAO, NOAA</div>

<div class="rule">
Our checks said 11 of 12 green — and the layer still would not open. The
coordinate format every tutorial shows is the one ArcGIS cannot read.
</div>

<!--
55s. The strongest measurement in the deck. Document count, bounding box,
distance search, source check: all green, and the layer is unusable. The data
was fine. The consumer was the thing we had not asked. Say the takeaway here
already, because it comes back at the end: check against the consumer, not
against the database.
-->
