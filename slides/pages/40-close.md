---
layout: default
class: flex flex-col justify-center
---

# Four rules, and none of them are about prompting

<div class="text-2xl leading-relaxed mt-6">

<div v-click class="mb-5">

**1 · Never let a model own a number that has a formula behind it.**

<div class="text-base opacity-70 mt-1">One multiplication was correct to 6 cm. One logarithm was wrong by 490 m — in 100 of 100 rows, always in the same direction.</div>

</div>
<div v-click class="mb-5">

**2 · Licence before geometry.**

<div class="text-base opacity-70 mt-1">The best data set on the table can be unusable at any quality. ODbL share-alike does not fit a CC BY project.</div>

</div>
<div v-click class="mb-5">

**3 · Your reference data is data too.**

<div class="text-base opacity-70 mt-1">A generalised outline framed correct data as an error, by 1.3 km. When a check fails on exactly one record, suspect the check.</div>

</div>
<div v-click>

**4 · Verify against the consumer, not only against itself.**

<div class="text-base opacity-70 mt-1">Eleven of twelve checks green, and the layer does not open. The loud error is the harmless one.</div>

</div>

</div>

<!--
45s. No new information here, on purpose -- this is the slide people photograph.
Click through, one sentence each, do not re-tell the stories.

If time is short, this is the slide to slow down on and the previous ones to
speed up.
-->

---
layout: default
---

<div class="eyebrow">What I would keep</div>

# The verification is the deliverable, not the data

<div class="cols">
<div>

**The model was genuinely good at**

- prose, titles, descriptions, fixtures
- finding sources and triaging their licences
- reading two products' documentation *against each other*
- writing the verifier — including the one that caught it out

</div>
<div>

**What I had to add**

- an independent recomputation of every derived number
- reference data as good as the question being asked
- the consumer's format requirements, encoded as a check
- a decision, up front, on how deep to verify

</div>
</div>

<div v-click class="rule">
The data is disposable. The scripts that prove it is right are the thing worth keeping.
</div>

<!--
30s. Fast. The left column is why you would use a model at all; the right column
is the actual work.

The last line is the honest summary of the whole repository: `output/` can be
deleted and regenerated at any time. The verifiers cannot.

On the last bullet: it defaults to rigour, and rigour has a real cost -- one row
out of 449 consumed most of the elapsed time in act 2.
-->

---
layout: center
class: text-center
---

# Thank you

<div class="text-lg mt-2 opacity-80">
Every number in this talk comes out of a script in this repository —<br/>
including the prompts that produced the mistakes.
</div>

<div class="flex justify-center items-center gap-10 mt-8">
  <img src="/qr-repo.svg" class="w-40 h-40" />
  <div class="text-left text-sm leading-relaxed">
    <div class="font-semibold">github.com/m-scherpi/</div>
    <div class="font-semibold">euro_dev_summit_26_test_data_ai</div>
    <div class="mt-3 opacity-70"><code>slides/</code> — this deck, as Markdown</div>
    <div class="opacity-70"><code>PROMPT.md</code> — every prompt, verbatim</div>
    <div class="mt-3 opacity-70">M. Scherpinski · con terra</div>
    <div class="opacity-70">CC BY 4.0</div>
  </div>
</div>

<!--
Questions. Leave this slide up -- the QR is the point of it.

Backup slides follow, in this order:
  1. one feature, several positions (893 rows -> 449 stations, medoid)
  2. three CRS: which column is lying (1 mm vs 1.27 m)
  3. the expired demo TLS CA in a certified release
  4. the SQL plugin vs ArcGIS conflict
  5. two bugs of my own
  6. uniform in latitude is not uniform on the ground
  7. open-data portals rot
-->
