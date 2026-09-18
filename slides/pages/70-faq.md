<div class="kicker">Questions &middot; not part of the talk</div>

# Questions I expect

<div class="faq-index">

<div><b>1 &nbsp;Why an agent at all?</b></div>
<div><b>2 &nbsp;Can I trust the result?</b></div>
<div><b>3 &nbsp;Data, licences, privacy</b></div>
<div><b>4 &nbsp;ArcGIS specifics</b></div>

</div>

<div class="note">
<b>f</b> gets here from any slide and back again &middot; the four blocks are the next four slides.
</div>

<!--
Not shown during the talk. This is the Q&A jump target: press `f`, then page
forward to the block the question belongs to. Press `f` again and you are back on
the slide you came from.

Keep the number of these at five. They answer questions, they are not a place to
put findings that did not fit -- those live in the use-case READMEs.
-->

---
hideInToc: true
---

<div class="kicker">FAQ &middot; 1 / 4</div>

# Why an agent at all?

<div class="faq">

<div><b>Why not Faker, GeoPandas, or Create Random Points?</b><br/>
For 10,000 points in a box, use the tool. The agent wins where no tool exists:
measuring somebody else's schema, reading licence pages, standing up a search engine.</div>

<div><b>If I have to check everything, what did I save?</b><br/>
The checks are code too, and the agent wrote them. Honest ratio: verifying took
longer than generating.</div>

<div><b>How much work was this?</b><br/>
35 logged prompts over 6 working days. One model, Claude Opus 5. No cost or
token figures were recorded. (Roughly 200 $, if asked directly)</div>

</div>

<!--
The honest version of the first answer: use case 1 is the weakest argument for an
agent and use case 3 is the strongest. A script that scatters points in a
bounding box is a solved problem. Standing up OpenSearch 2.12 with certificates,
an index mapping and a layer ArcGIS can open is not, and there is no tutorial for
it -- the model read two vendors' documentation against each other.

Second answer, if pushed: in `open_data_search` the research was the expensive
half -- 7 candidates, 6 live HTTP checks, one dead host -- and writing the
transformation afterwards was the easy one.

Third answer, if pushed: 35 is a lower bound, meta-prompts about documentation
were deliberately not logged. Everything is in PROMPT.md, verbatim, including the
iterations that went nowhere.
-->

---
hideInToc: true
---

<div class="kicker">FAQ &middot; 2 / 4</div>

# Can I trust the result?

<div class="faq">

<div><b>Was it right the first time?</b><br/>
No. 100 of 100 rows had their Web Mercator value wrong, by up to 490 m &mdash;
all in the same direction, so no average would show it.</div>

<div><b>Who verifies the verifier?</b><br/>
A second, independent implementation. A third-party library against hand-written
math. And planted defects, until the check actually goes red.</div>

<div><b>Do green checks mean anything?</b><br/>
11 of 12 green, and the layer would not open. 4 of 4 green, and the layer drew
nothing. Every check was right about what it measured.</div>

</div>

<!--
The two formulas are the point of the second answer: the generator writes
`R*ln(tan(pi/4 + phi/2))`, the verifier writes `R*atanh(sin phi)`. Same value,
no shared line, so agreement is evidence instead of a tautology.

Tampering runs, if asked: three defects planted in the OpenSearch index, each
time exactly the responsible check went red and the other 17 stayed green. A
verifier that has never been red has not been verified.

And the one that argues against my own approach: the portal stored our web map
exactly as sent and rendered one layer as empty. "Does this draw" is not a
readable property of an item. Only the screenshot found it.
-->

---
hideInToc: true
---

<div class="kicker">FAQ &middot; 3 / 4</div>

# Data, licences, privacy

<div class="faq">

<div><b>What left the machine?</b><br/>
Public downloads, vendor documentation, and exactly one reverse-geocoding query.
No customer data at any point.</div>

<div><b>Why not OpenStreetMap?</b><br/>
It was the best of the seven sources we checked. Its share-alike licence does not
fit a CC BY repository &mdash; so we could not use it at any quality.</div>

<div><b>Could I run this on production data?</b><br/>
You do not have to. A test needs the structure, not the content. That is the
whole point.</div>

</div>

<!--
First answer, in detail if asked: DB InfraGO, Geobasis NRW, Natural Earth, the
OpenSearch distribution -- all public downloads. The single Nominatim query
settled one station near a state border, read-only, outside the pipeline, and
nothing from that answer is committed. Everything published went to our own
portal, and all of it is generated and marked as fictitious.

Second: the ODbL separates a Produced Work -- a map image, attribution only --
from a Derivative Database, which is what a filtered CSV of stations is, and
share-alike bites there. CC0 costs nothing, CC BY costs a sentence, ODbL costs
your project's licence.

Third: the CC BY carve-out, if somebody asks about reuse -- one file, the company
word mark on the cover and the closing slide. Everything else in the repository
is CC BY 4.0.
-->

---
hideInToc: true
---

<div class="kicker">FAQ &middot; 4 / 4</div>

# ArcGIS specifics

<div class="faq">

<div><b>Only points?</b><br/>
Only points here. Schema first carries over to lines and polygons; the geometry
checks get harder.</div>

<div><b>Domains, subtypes, relationship classes?</b><br/>
Not covered. The schema document a human reviews before anything is created is
exactly where they would go.</div>

<div><b>Can I do the geodatabase part without ArcGIS Pro?</b><br/>
No &mdash; arcpy is not on PyPI. That is why the pipeline is split at the licence
boundary: the analysis half is stdlib only.</div>

</div>

<!--
The story worth telling here is the third answer's neighbour: we asked for this
with the ArcGIS API for Python, and it has no database connectivity at all. One
unchanged line of code produced four outcomes depending only on which libraries
happened to be installed -- and the last one succeeded silently and wrote a
shapefile, with four field names cut to ten characters.

If asked about schema fidelity: the geodatabase honoured every declared field
length. The hosted feature layer discarded all of them and stored TEXT(8000),
and `updateDefinition` answered `{"success": true}` without changing anything.
-->
