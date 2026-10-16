# We build products, not data sets

<div class="lead">

<b>con terra </b>builds software products: <br/>
<b>map.apps</b>: a Web Mapping Framework (based on the
ArcGIS Maps SDK for JS)<br/>
<b>security.manager</b>: Access Control via ArcGIS Enterprise SOIs.

</div>

<div class="steps">
<div>Our software has to work with <b>any</b> customer's data.</div>
<div>So a test does not need real data — it needs the <b>structure</b>: 
<br/>the right schema, the right coordinate system, enough rows.</div>
<div>And most of the time, a feature is just a <b>geometry with attributes</b>.</div>
</div>

<!--
30s. This is the frame for the whole talk. Say it plainly: we are not looking
for a way around a data protection rule. We build universal software, so what we
actually need is shape and volume, and both can be made.

Split off the "where does it come from" part on purpose -- this slide answers
*what* a test needs, the next one answers *where it comes from*. Both fitted on
one slide and neither was readable.
-->

---

# So where does that data come from?

<div class="steps">
<div><b>Real data</b> is often not allowed to leave the building — and it is also not the point.</div>
<div><b>Hand-made data</b> is fine for five rows and hopeless for ten thousand.</div>
<div><b>Generate it.</b> That is what everybody does today.</div>
</div>

<div class="note">
The question this talk answers: <b>How much of that can a LLM actually build for us?</b>
</div>

<!--
30s. Three options, and the third one is where the talk starts. Do not defend
GenAI here -- just land the question, because the next ten minutes are five
concrete answers to it.
-->

---

# Five use cases, one chain

<div class="steps">
<div><b>1 · csv_data</b> — the model writes the data itself</div>
<div><b>2 · open_data_search</b> — the model finds real data instead</div>
<div><b>3 · opensearch</b> — the data gets a new kind of consumer</div>
<div><b>4 · egdb_import</b> — the data lands in an Enterprise Geodatabase</div>
<div><b>5 · portal_publish</b> — the data becomes a published Web Map</div>
</div>

<div class="note">
Each one is a folder with its own stack, a runnable command and a check.<br/>
Every prompt is written down. Everything is documented.
</div>

<!--
30s. Say the chain out loud once, then move. This slide exists so nobody has to
wonder where we are later. Two slides per use case from here: what it is for,
then what came out.
-->
