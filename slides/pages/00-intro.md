---
layout: default
---

# I am not allowed to use the data I have

<v-clicks>

- **Customer data** — obviously not.
- **Production geodata** — licensed to somebody else.
- **Internal systems** — not publishable, ever.

</v-clicks>

<div v-click class="mt-6">

So the data has to be invented. And invented *geodata* is a harder ask than
invented names: every row has to be **somewhere** — in a stated CRS, inside a
real boundary, readable by a real client.

</div>

<div v-click class="rule">
A language model will produce all of that in seconds. And it will look right.
</div>

<!--
45s. The point of this slide is that the constraint is not a nuisance, it IS the
reason generated test data is worth a talk. Land on the last line and pause --
"it will look right" is the thread for the next ten minutes.
-->

---
layout: default
---

<div class="eyebrow">The setup</div>

# One repository, and a paper trail

<div class="grid grid-cols-2 gap-8 mt-4">
<div>

- **Four use cases**, three finished, each self-contained: own stack, own
  dependencies, own README.
- **`PROMPT.md`** — every prompt, verbatim, in the language I typed it, plus
  what actually happened. Including the dead ends.
- **Everything CC BY 4.0**, so every external source had to be licence-clean
  before it was allowed in.

</div>
<div>

- **`output/` is committed**, because the next use case reads it as input.
- Raw LLM artifact kept **next to** the corrected one. The delta is the
  interesting file.
- **These slides are in the same repository** — Markdown, built by CI, no
  `.pptx` anywhere.

</div>
</div>

<div v-click class="rule">
Nothing in this talk is a recollection. Every number comes out of a script that still runs.
</div>

<!--
30s. Deliberately fast -- this is credentials, not content. The one line worth
saying out loud is the last one: everything you are about to see is measured,
not remembered.

If someone asks in Q&A: the deck is a Slidev project in `slides/`, deployed to
GitHub Pages by an Actions workflow on every push to main.
-->
