# We build products, not data sets

<div class="lead">

Our software has to work with **any** customer's data. To test it, we do not
need their data — we need the **structure**: the right schema, the right
coordinate system, and enough rows. Most of the time a feature is just a
geometry with attributes.

</div>

<div class="steps">
<div><b>Real data</b> is often not allowed to leave the building — and it is also not the point.</div>
<div><b>Hand-made data</b> is fine for five rows and hopeless for ten thousand.</div>
<div><b>So: generate it.</b> The question is how much of that a language model can build for us.</div>
</div>

<!--
40s. This is the frame for the whole talk. Say it plainly: we are not looking
for a way around a data protection rule. We build universal software, so what we
actually need is shape and volume, and both can be made. Do not defend GenAI
here — just set up that the next ten minutes are five concrete things that
worked.
-->

---

# Five use cases, one chain

<div class="steps">
<div><b>1 · csv_data</b> — the model writes the data itself</div>
<div><b>2 · open_data_search</b> — the model finds real data instead</div>
<div><b>3 · opensearch</b> — the data gets a new kind of consumer</div>
<div><b>4 · egdb_import</b> — the data lands in an Enterprise Geodatabase</div>
<div><b>5 · portal_publish</b> — the data becomes a published web map</div>
</div>

<div class="pt-6 text-sm opacity-80">
Each one is a folder with its own stack, a runnable command and a check. Every
prompt is written down.
</div>

<!--
30s. Say the chain out loud once, then move. This slide exists so nobody has to
wonder where we are later. Two slides per use case from here: what it is for,
then what came out.
-->
