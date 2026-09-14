# `slides/` — the talk, as code

The presentation for the **Esri European Developer & Technology Summit 2026**,
built from this repository. Not a use case: no `input/`, no `output/`, nothing
here is generated test data. It is the deck itself, in Markdown, deployed to
GitHub Pages by CI.

**Live:** https://m-scherpi.github.io/euro_dev_summit_26_test_data_ai/

---

## Stack, and why

**[Slidev](https://sli.dev) 52** (Vue/Vite underneath), local dependencies only.

Chosen for two reasons. First, the slides are Markdown under version control, so
the deck reviews like the rest of the repository and there is no `.pptx` to
diff. Second, Slidev is the only common option with first-class *code*
presentation — per-line highlighting, click-stepped reveals — and most of this
talk is code and measured numbers.

Presenter notes double as the speaking script, so each slide's time budget lives
in the same file as the slide it applies to.

| Dependency | Why |
|---|---|
| `@slidev/cli` | the presentation engine |
| `@slidev/theme-seriph` | light background — projector contrast over aesthetics; its serif headings are overridden, see *Corporate look* |
| `vue` | Slidev peer dependency |
| `qrcode` | one-off generator for the closing slide's QR code |

`npm audit` reports findings in this build tooling. They are all in dev-only
dependencies of the build chain — nothing here serves traffic — and fixing them
would mean unpinning Slidev. Noted rather than hidden.

---

## Setup

```bash
cd slides
npm install
npm run dev          # opens http://localhost:3030
```

`npm run dev` and `npm run build` both run `sync-assets` first via npm's
`predev` / `prebuild` hooks, so the screenshots are always in place.

---

## Usage

| Command | Purpose |
|---|---|
| `npm run dev` | live deck with hot reload; `o` for overview, `p` for presenter mode |
| `npm run build` | static SPA into `dist/` (gitignored) |
| `npm run build -- --base /euro_dev_summit_26_test_data_ai/` | production build as CI does it — a wrong base path only ever fails in the deployed build, never in `dev` |
| `npm run sync-assets` | copy the result screenshots into `public/img/` |
| `npm run export` | PDF into `build/slides.pdf` — the fallback for the conference laptop |

PDF and PNG export need a browser that is deliberately **not** a dependency, so
CI does not download it on every build:

```bash
npm install --no-save playwright-chromium
npm run export
# every slide, then look at every one -- this is how five slides with their
# finding box running off the bottom edge were found, on a build that reported
# success:
npx slidev export --format png --output build/png
```

---

## Layout

```
slides/
├── slides.md              # entry: headmatter, cover, and `src:` includes
├── pages/
│   ├── 05-disclaimer.md   # how all of this was made -- agent, prompt log, local
│   ├── 00-intro.md        # why we generate at all, and the chain
│   ├── 10-csv-data.md     # use case 1 -- idea slide + result slide
│   ├── 20-open-data.md    # use case 2 -- idea slide + result slide
│   ├── 30-opensearch.md   # use case 3 -- idea slide + result slide
│   ├── 40-egdb.md         # use case 4 -- idea slide + result slide
│   ├── 50-portal.md       # use case 5 -- idea slide + result slide
│   └── 60-close.md        # six takeaways, the closing line, thanks
├── style.css              # palette and typography, auto-loaded by Slidev
├── global-bottom.vue      # footer on every slide but the cover
├── scripts/
│   ├── sync_assets.mjs    # screenshots -> public/img (runs via pre* hooks)
│   ├── make_qr.mjs        # one-off, output committed
│   └── make_close_grid.mjs # one-off, seeded, output committed
├── public/
│   ├── qr-repo.svg        # committed: text, tiny, changes only on a rename
│   ├── cover-deco.svg     # low-poly corner graphic, drawn from the palette
│   ├── close-grid.svg     # grid structure of the closing slide, generated
│   └── img/               # generated, gitignored
└── input/                 # gitignored: the corporate .potx, never committed
```

---

## Corporate look

The deck follows the company's PowerPoint master
(`con terra_Folienmaster_en.potx`, theme `con terra`) closely enough to be
recognisable, without pretending to be PowerPoint.

**What was taken, and what was not.** Taken: the colour scheme and the
typography, both read out of the template's own XML
(`ppt/theme/theme1.xml`, `ppt/slideMasters/slideMaster1.xml`). Not taken: the
file and its images. The `.potx` is a corporate template, not ours to publish
under CC BY, so `slides/input/` is **gitignored** and nothing in `public/` comes
out of it. The corner graphic on the cover is drawn here from the same palette;
it is an imitation of the master's low-poly motif, not a copy of it.

| From the master | Used for |
|---|---|
| `dk2` **#005587** | every title, and the body text — the master sets body copy in the same dark blue |
| `acc2` **#00B0B9** | the accent: subtitle, eyebrow label, the bold lead-in of a step, the finding box |
| `acc4` **#8BD3E6** | the left rule of a step or a card |
| `acc1` **#6CC24A**, `acc3` **#418FDE**, `acc5` **#F2695C** | available in `style.css` as variables; unused so far |
| Arial, major and minor font alike | the whole deck — `fonts.provider: none`, so nothing is fetched at render time |
| title 28 pt bold, left aligned, 90 % line spacing | `h1`, at 2.1 rem — a projected deck gets a little more than a printed one |
| copyright bottom left, slide number bottom right | `global-bottom.vue`, hidden on the cover |
| `Titelfolie_hell` | the cover: white, title block at the left edge, graphic top right |
| `Schlussfolie` | the closing slide: *Thank you very much!*, speaker and postal address at the template's own vertical positions (11.3 %, 40.6 %, 53 %), grid structure across the slide |

**The closing slide.** The master's `Schlussfolie` carries the full postal
address and a strip of logos bottom right. The address is reproduced; the logos
are not — they are the template's, and this deck puts the repository's QR code
there instead, which is what an audience actually needs. The grid structure
behind it (a 961-point freeform in the `.potx`) is likewise redrawn rather than
extracted: `scripts/make_close_grid.mjs` writes `public/close-grid.svg` from a
seeded PRNG, so re-running it produces a byte-identical file, and the output is
committed like the QR code:

```bash
node scripts/make_close_grid.mjs 20260914 public/close-grid.svg
```

Neither the cover nor the closing slide gets the footer, because the master's
`Titelfolie` and `Schlussfolie` carry none — the closing slide states the company
in full instead.

**One Slidev trap, measured.** The cover was first written as `layout: cover`,
which is seriph's own layout and paints its own background — the custom
background was set, the build reported success, and the slide rendered as a grey
gradient with the corner graphic nowhere to be seen. `layout: default` plus the
absolutely positioned `.cover-block` is what actually renders the master's title
slide. The same lesson as everywhere else in this repository: a green build says
nothing about what was drawn, so export the PNGs and look.

---

## The title and the abstract

The talk is submitted as:

> **Using Agentic AI to Easily Create Geospatial Test Data for Your Infrastructure**
>
> Agentic AI may be used to interact with ArcGIS Enterprise in different ways,
> e.g. for the generation of test data for different scenarios and environments.
> If the content of the data doesn't matter that much and a feature is considered
> just a geometry with attributes, it's very easy to generate a CSV with 10k
> points for a hosted feature service, build an OpenSearch-DB to get a view layer
> in ArcGIS Pro based on just a GeoJSON or import data into your EGDB with a
> vibe-coded Python script. In this talk, examples will be given to show you, how
> easy it is, to populate your testing infrastructure with e.g. Claude Code.

The abstract is a promise, so the deck is checked against it the way a data set
is checked against its consumer:

| The abstract says | Where the deck delivers it |
|---|---|
| interact with ArcGIS Enterprise in different ways | slide 3, the chain — hosted layer, referenced layer, index-backed layer, web map |
| the content doesn't matter, a feature is a geometry with attributes | slide 4, in those words |
| a CSV with 10k points for a hosted feature service | slides 5–6, with the hosted-feature-layer target named on the idea slide |
| an OpenSearch-DB … view layer in ArcGIS Pro … based on just a GeoJSON | slides 9–10: the index, ArcGIS Pro, and the source handed over as "a GeoJSON" |
| import data into your EGDB with a … Python script | slides 11–12 |
| with e.g. Claude Code | slide 2, the disclaimer slide — which also names Slidev as what the deck itself is written in |
| **how easy it is** | every result slide shows the thing working *first*; the finding is the closing line, not the subject |

That last row is the one worth re-reading before a rehearsal. The abstract sells
ease, and this repository's instinct is to lead with what went wrong. The deck
resolves it by order: the result, then the one thing to watch.

---

## The 15-minute constraint is the architecture

The slot is **15 minutes including questions** — about 12 minutes of speaking.
Five finished use cases do not fit as five deep dives, and the slot will not
grow. The deck's answer is **two slides per use case**, each carrying little:

- an **idea slide** — why this use case exists and the workflow in three steps,
- a **result slide** — one screenshot, and **one** finding in the teal box.

Splitting one dense slide into two sparse ones costs no time at all. It is the
same speaking budget with half the text competing for attention, and it is what
lets the workflow be said rather than read.

**The talk answers "what can you build with this", not "what did I measure".**
Every use case has a dozen findings; each slide shows one, and it is the one
that would cost a listener a day. The rest live in the use-case READMEs.

**There is no backup section.** An earlier version had fifteen backup slides and
a rule for which finding may displace which. It was a way of refusing to cut. A
question during Q&A is answered from the README, live, not from a slide nobody
has seen.

### Why each use case is in the deck

The reason a use case exists is the idea slide's job, and each one is different:

| Use case | The reason to show it |
|---|---|
| `csv_data` | volume — nobody clicks 10,000 points by hand, and a seed makes it repeatable |
| `open_data_search` | effort — searching portals and reading licences is the expensive half |
| `opensearch` | reach — test data for a service type we are new to, with support this young |
| `egdb_import` | relevance — the Enterprise Geodatabase is where we actually need test data |
| `portal_publish` | the whole flow, end to end, and something you can show someone |

### Time budget

Each slide's presenter notes repeat its budget, so overrun is visible while
rehearsing rather than on stage.

| # | Slide | Budget |
|---|---|---|
| 1 | Title | 10 s |
| 2 | How all of this was made — agent, prompt log, local | 40 s |
| 3 | We build products, not data sets | 40 s |
| 4 | Five use cases, one chain | 30 s |
| 5–6 | `csv_data` — nobody clicks 10,000 points by hand / 10,000 points, one command | 40 + 55 s |
| 7–8 | `open_data_search` — finding the data is the work / 449 real railway stations | 40 + 55 s |
| 9–10 | `opensearch` — test data for a technology we are new to / the index, live in ArcGIS | 40 + 55 s |
| 11–12 | `egdb_import` — the one we need most / a FeatureClass, in a real geodatabase | 40 + 55 s |
| 13–14 | `portal_publish` — all the way / a web map, published | 40 + 55 s |
| 15 | Take home, part 1 | 40 s |
| 16 | Take home, part 2 | 45 s |
| 17 | *Knowing that the content is valid still is* | 25 s |
| 18 | Thank you very much — address and QR, stays up for questions | — |

Total ≈ 11.5 minutes against ~12 available. The disclaimer slide is the one to
drop if a session overruns before the talk starts — it is the only slide whose
content is also on the closing slide.

### The seven takeaways

Written to be repeatable rather than precise — each one is a sentence someone
could say to a colleague the next morning.

| Takeaway | Comes from |
|---|---|
| There is more than one way to get to data. | all five — it is the talk in one line |
| Ask for the generator, not for the data. | `csv_data` |
| Let code own every number that has a formula. | `csv_data` |
| Finding the data costs more than converting it. | `open_data_search` |
| Not the data — the consumer decides. | `opensearch` |
| "Success" is not a result. | `egdb_import` |
| A green check cannot see a blank map. | `portal_publish` |

The first one leads because it answers the abstract's own claim: the agent is
not one trick that happens to fit one target, it is a way of working that fitted
five very different ones.

### The closing line

> Test data used to be the thing nobody had time for.
> Filling a test system is no longer the hard part.
> **Knowing that the content is valid still is.**

Three beats — the past, what changed, what is left — and the pauses between them
are the slide. The third line is the one to say slowest.

It took four attempts, and the rejected ones are instructive. *"The verification
is the deliverable, not the data"* and *"the deliverable was never the data — it
was the generator, the schema and the check"* were both true, both accurate
summaries of the repository, and both ended the talk on a lecture about
deliverables. They also worked against the abstract, which sells how *easy* this
is, by leaving the room with how *careful* you have to be.

What fixed it was order rather than content: say the easy part out loud first,
so the last line reads as what you now get to spend your time on instead of as a
warning. The version that stands separates that into its own line — *filling a
test system is no longer the hard part* — which is the abstract's own claim,
stated plainly, one beat before the qualification. An alternate last line for a
more sceptical room is in the slide's presenter notes.

One deliberate grammar choice: no comma before *still is*. A comma there is the
spoken pause, and the slide already has it as a line break, so the sentence can
stay clean for the reader while the speaker takes the pause anyway.

### Language

The talk is given by a non-native English speaker, and the deck is written for
that: short sentences, common words, no figurative vocabulary. Words like
*prose*, *triage* or *yardstick* were removed on purpose — a word the speaker
has to think about on stage costs more than it adds. Numbers are kept only where
the number *is* the point (490 m, 11 of 12, 4 of 4); anything that needs
explaining before it means something was cut.

## Input: the screenshots

The deck shows one capture per use case, on that use case's result slide,
referenced from where each already lives:

| Screenshot | Source | Shown on |
|---|---|---|
| `csv_data/input/germany_points_10k.png` | 10,000 generated points | slide 6 |
| `open_data_search/input/nrw_stations.png` | 449 real DB InfraGO stations | slide 8 |
| `opensearch/input/nrw_stations_opensearch_service.png` | web feature layer over the index | slide 10 |
| `egdb_import/input/csv_to_egdb_pro.png` | FeatureClass in the PostgreSQL geodatabase | slide 12 |
| `portal_publish/input/class_breaks.png` | published web map, class-breaks layer | slide 14 |

`scripts/sync_assets.mjs` copies them into `public/img/`, which is gitignored —
Vite only serves assets from inside the project root, and there is no reason for
a second copy of 4.8 MB of PNG in git.

**The basemap attribution stays visible.** Every capture carries its
`Esri | TomTom | Garmin | USGS | FAO | NOAA` bar (plus `Land NRW` on the
stations and rent-census images) burnt into its bottom edge — except the
geodatabase capture, where ArcGIS Pro keeps the notice in its *Service Layer
Credits* panel instead, opened before the capture and visible in the image. Publishing the deck redistributes
those images, and the attribution is the condition. That is why every screenshot
is an `object-contain` `<img>` and never a `background-size: cover` — and why the
cover slide is a plain gradient rather than a full-bleed map. A background image
is cropped to fill, and the first thing cropped off is the attribution.

---

## Deployment

`.github/workflows/deploy-slides.yml` builds on every push to `main` that
touches `slides/**`, the workflow, or one of the three screenshots, and
publishes `slides/dist` to GitHub Pages. The base path is derived from the
repository name, so a rename does not break every asset URL. The workflow's
path filter lists the screenshots it syncs, so it needs updating whenever the
set on the slides changes.

Pages deployment from Actions requires the repository to be **public**. While it
is private, the build job succeeds and the deploy job fails — that is repository
visibility, not a broken workflow.

---

## Notes for the talk

- **The abstract is a consumer, and the deck gets checked against it.** The talk
  was submitted before most of it existed, so the deck and the abstract could
  easily drift apart. Reading them against each other found three real gaps: the
  hosted feature layer was never named as the CSV's target, ArcGIS Pro and the
  "GeoJSON" were missing from the OpenSearch use case, and Claude Code itself
  appeared nowhere. Same move as the rest of the repository: verify against the
  consumer, and here the consumer is whoever read the programme and chose this
  room.
- **The stated motivation and the real one were not the same sentence, and the
  difference changes every slide after it.** Two drafts opened on "I am not
  allowed to use real data". The actual reason is that a product has to work with
  any customer's data, so what a test needs is structure. The first framing makes
  every use case sound like a workaround; the second makes it a capability.
- **Presentation as code was the cheap part.** Setup to first rendered slide was
  one `npm install` and one Markdown file. What takes the work is deciding what
  not to say.
- **The deck was rebuilt twice, and the second rebuild is the useful one.** Draft
  one was four named rules with the use cases as evidence — a talk about how much
  goes wrong. Draft two put the use cases first with one finding each. Draft three
  split every use case into *why it exists* and *what came out*, and that is the
  version that actually explains the workflow: the reason for `egdb_import` is
  not a number, it is the sentence "this is where we really need test data", and
  there was no room to say it while the slide was also carrying a result.
- **Splitting a dense slide is free.** Ten slides became seventeen and the
  speaking time did not change — the same words, laid out so that half of them
  are not on screen while the other half is being said.
- **Write for the speaker, not for the reader.** The talk is given in a
  non-native language, so words that need a moment of thought on stage were
  removed even where they were the better word. Same for numbers: a measurement
  that has to be explained before it means anything is a measurement for the
  README.
- **Cutting the backup section was the hard part and the right one.** Fifteen
  written-out slides nobody sees are fifteen slides of maintenance, and having
  them made it easy to avoid deciding. The findings did not disappear; they live
  in the use-case READMEs, which is where a question gets answered properly
  anyway.
- **The verification loop applies to slides too, and it caught something worse
  than a layout bug.** Rendering every slide to PNG found, on a green build:
  first all five finding boxes running off the bottom edge, and then — after the
  result slides were rebuilt around a large screenshot — an image scaled so far
  past the slide that **the basemap attribution was cropped off**. The cause was
  `max-height: 56vh` on the image: Slidev scales the whole slide with a CSS
  transform, so a viewport unit inside a slide is not a fraction of that slide.
  A licence obligation was broken by a unit conversion, and the build said
  success. Cap image height in pixels against Slidev's 980 × 552 canvas.
- **A convention caught its own violation.** The obvious cover design is the
  10,000-point map full-bleed behind the title. It renders with the basemap
  attribution cropped off — so the repository's own licence rule ruled out its
  own prettiest slide. Documented rather than quietly cropped.
- **Lesson learned.** The slot size decides the *shape* of the talk, not just its
  length — and the shape is not only how many slides, but how much is on each.
  Two sparse slides say more in the same minute than one dense one.
