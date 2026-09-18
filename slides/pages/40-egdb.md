<div class="eyebrow">Use case 4 / 5 · egdb_import</div>

# The one we need most: the Enterprise Geodatabase

<div class="lead">

The experiments stop here. An Enterprise Geodatabase is where we really need
test data — and where the schema matters as much as the rows.

</div>

<div class="steps">
<div><b>Measure</b> the source file and write down a schema: every field, its type, its length.</div>
<div><b>Review that document</b> — it is readable, and you can change it before anything is created.</div>
<div><b>Then load it</b>: create the FeatureClass and insert the rows, exactly as the schema says.</div>
</div>

<div class="note">
Our actual services are <b>Referenced</b> Feature Layers on an Enterprise Geodatabase —
published on a Portal, served by ArcGIS Server, secured via SOI. So the data has to be in there, and
writing it in is the step that decides everything after it.
</div>

<!--
35s. Say why this one matters at work: a CSV is easy, a geodatabase is where
colleagues actually ask for test data, and getting the schema right is most of
the job. The split is the useful idea — the decisions live in a document a human
can read and edit, and the part that needs a licence, a database and Windows
becomes a mechanical step.
-->

---
layout: default
---

<div class="eyebrow">Use case 4 / 5 · egdb_import</div>

# A FeatureClass, in a real EGDB

<div class="result">

<div class="shot-frame"><img src="/img/csv_to_egdb_pro.png" class="shot-big" /></div>
<div class="credit text-center">FeatureClass in a PostgreSQL geodatabase · ArcGIS Pro · Esri, TomTom, Garmin, FAO, NOAA, USGS, © OpenStreetMap contributors</div>

<div class="rule">
The library we assumed (ArcGIS API for Python) cannot do this — and does not
say so. It reported success and quietly wrote a shapefile instead, four field
names cut short.
</div>

</div>

<!--
55s. Four different outcomes from one unchanged line of code, and the only thing
that differed was which libraries happened to be installed. Nothing raised an
error in the last of them. So: check what an API wrote, not whether it threw.
That is the second takeaway, and it is the one that costs people days.
-->
