<div class="eyebrow">Use case 5 / 5 · portal_publish</div>

# All the way: data to finished map

<div class="lead">

A bonus round. The next step is not <b>more</b> data — it is the whole flow, and a
demo you can put in front of someone.

</div>

<div class="steps">
<div><b>Generate</b> a small city data set with fake values that make a map worth looking at.</div>
<div><b>Build the portal content offline</b>: the layer, the symbols, the map — all as files.</div>
<div><b>Publish</b> it, then read it back and check what the portal actually stored.</div>
</div>

<div class="note">
Everything up to the upload was built and reviewed without a portal, a licence
or a password in the loop. <br/> All this data is a fake census for our home town.
</div>

<!--
35s. This is the "think further" slide. It is the same pipeline as before with
one more step, and suddenly the output is not a file but something a colleague
can open in a browser. Worth saying: the map, the symbols and the classification
were designed as plain files, so the whole design could be reviewed before any
system was involved.
-->

---
layout: default
---

<div class="eyebrow">Use case 5 / 5 · portal_publish</div>

# A Web Map, published to a Portal

<div class="result">

<div class="shot-frame"><img src="/img/muenster_rent_class_breaks.png" class="shot-big" /></div>
<div class="credit text-center">Rent per m², five classes · ArcGIS Enterprise · Land NRW, Esri, TomTom, Garmin, USGS, FAO, NOAA</div>

<div class="rule">
All checks were green — on a map layer that drew nothing at all. Our checks
read what the portal stored. Whether it <b>draws</b> is not something you can read.
You have to look.
</div>

</div>

<!--
55s. This one argues against my own approach, which is why it is in the talk.
The portal stored our map exactly as we sent it and rendered one layer as empty.
Every check was right about what it measured, and none of them could see it.
Looking at the map was the only way. So: automated checks beat looking, almost
everywhere, and "almost" is doing work in that sentence.
-->
