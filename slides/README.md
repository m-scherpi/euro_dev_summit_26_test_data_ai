# `slides/` — the talk, as code

The conference presentation for this repository. Not a use case: no `input/`,
no `output/`, nothing here is generated test data. It is the deck itself, in
Markdown, deployed to GitHub Pages by CI.

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
| `@slidev/theme-seriph` | serif theme, light background — projector contrast over aesthetics |
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
npx slidev export --format png --output build/png/slide --range 1-14
# or every slide, backup included, which is how the two overflow defects
# and one broken layout were found that the build reported as success:
npx slidev export --format png --output build/png
```

---

## Layout

```
slides/
├── slides.md              # entry: headmatter, cover, and `src:` includes
├── pages/
│   ├── 00-intro.md        # the constraint, and the setup
│   ├── 10-csv-data.md     # act 1  -> rule 1
│   ├── 20-open-data.md    # act 2  -> rules 2 and 3
│   ├── 30-consumer.md     # act 3  -> rule 4
│   ├── 40-close.md        # the four rules, what to keep, thanks
│   └── 90-appendix.md     # backup slides, not part of the talk
├── style.css              # ~60 lines, auto-loaded by Slidev
├── scripts/
│   ├── sync_assets.mjs    # screenshots -> public/img (runs via pre* hooks)
│   └── make_qr.mjs        # one-off, output committed
└── public/
    ├── qr-repo.svg        # committed: text, tiny, changes only on a rename
    └── img/               # generated, gitignored
```

---

## The 15-minute constraint is the architecture

The slot is **15 minutes including questions** — about 12 minutes of speaking.
Three finished use cases and one or two more to come do not fit, and the slot
will not grow. So the deck is built to *leave things out*:

- **Core deck, slides 1–14.** Four named rules, each proven by one measured
  number and one image. Nothing else survives the budget.
- **Backup, slides 15–29.** Written out, not shown. Reachable with the arrow key
  during questions and readable in the repository.

**House rule for new use cases:** a new one gets its own `pages/NN-*.md` and
lands in the **backup** first. It enters the core deck only by displacing a rule
whose finding is weaker.

### Core deck and time budget

Each slide's presenter notes repeat its budget, so overrun is visible while
rehearsing rather than on stage.

| # | Slide | Budget |
|---|---|---|
| 1 | Title | 10 s |
| 2 | I am not allowed to use the data I have | 45 s |
| 3 | One repository, and a paper trail | 30 s |
| 4 | Act 1 — 100 geo points, straight from the model | 45 s |
| 5 | Act 1 — same request, 10,000 rows, a real polygon | 45 s |
| 6 | **Rule 1** — both files also carried Web Mercator | 75 s |
| 7 | Act 2 — the licence check comes before the geometry check / **Rule 2** | 60 s |
| 8 | Act 2 — 449 real stations, every coordinate traceable | 40 s |
| 9 | **Rule 3** — one station out of 449 failed the check | 75 s |
| 10 | Act 3 — eleven of twelve checks green, the layer will not open | 75 s |
| 11 | **Rule 4** — the loud error is the harmless one | 75 s |
| 12 | The four rules | 45 s |
| 13 | The verification is the deliverable, not the data | 30 s |
| 14 | Thank you (QR stays up for questions) | — |

Total ≈ 11 minutes, which leaves air for one slide to run long.

### Backup slides

| # | Slide | Source |
|---|---|---|
| 15 | divider | — |
| 16 | One real-world feature, several published positions | `open_data_search` |
| 17 | Redundant coordinate columns tell you which one to distrust | `open_data_search` |
| 18 | An old pinned version ships expired material | `opensearch` |
| 19 | Two subsystems of one product, incompatible formats | `opensearch` |
| 20 | Two bugs of my own, worth more than the successes | `csv_data` |
| 21 | Uniform in latitude is not uniform on the ground | `csv_data` |
| 22 | Open-data portals rot — commit the slice, not just the URL | `open_data_search` |
| 23 | No licence. So we rebuilt the data set | `opensearch` |
| 24 | The same bug is loud or silent depending on where on Earth you are | `opensearch` |
| 25 | 1.9 nanometres broke the build | `opensearch` |
| 26 | The API in the request cannot do the job | `egdb_import` |
| 27 | Four outcomes, one unchanged line of code | `egdb_import` |
| 28 | What the silent success did to the schema | `egdb_import` |
| 29 | "Nothing was recomputed" — measured | `egdb_import` |

Slide 24 is the strongest candidate to displace a core-deck rule: it is the same
point as **Rule 4** (the loud error is the harmless one) with a second
measurement that makes it uncomfortable rather than merely true — the verifier
that caught the stations was luckier, not better. It stays in the backup for now
because Rule 4 already has an image and this has only numbers.

Slides 26-28 are the second candidate, and for the opposite reason: they are
**Rule 4** with the cleanest evidence in the repository — four outcomes from one
unchanged line of code, decided only by which libraries happened to be
installed, and a schema that came back with four field names silently shortened.
They stay in the backup because the finding is about an API rather than about
geodata, and because `egdb_import` has not yet been run against a real
geodatabase. When it has, and there is a screenshot of the layer in ArcGIS Pro,
slide 27 is the one to argue for.

Slide 29 is a third kind of candidate: it pairs with slide 25 rather than
competing with it. Both are nanometre-scale findings that break an exact
comparison — 1.9 nm from libm not being standardised to the last bit, 9.5 nm
from a geodatabase storing a number — and neither involved any code doing
arithmetic. Shown together they make a point neither makes alone. Shown alone,
25 is the stronger one, because its cause was hunted down and 29's was not.

---

## Input: the screenshots

The deck shows three ArcGIS Pro captures, referenced from where they already
live:

| Screenshot | Source | Shown on |
|---|---|---|
| `csv_data/input/nrw_points.png` | 100 LLM-written points | slide 4 |
| `csv_data/input/germany_points_10k.png` | 10,000 generated points | slide 5 |
| `open_data_search/input/nrw_stations.png` | 449 real DB InfraGO stations | slide 8 |

`scripts/sync_assets.mjs` copies them into `public/img/`, which is gitignored —
Vite only serves assets from inside the project root, and there is no reason for
a second copy of 4.8 MB of PNG in git.

**The basemap attribution stays visible.** Every capture carries its
`Esri | TomTom | Garmin | USGS | FAO | NOAA` bar (plus `Land NRW` on the
stations image) burnt into its bottom edge. Publishing the deck redistributes
those images, and the attribution is the condition. That is why every screenshot
is an `object-contain` `<img>` and never a `background-size: cover` — and why the
cover slide is a plain gradient rather than a full-bleed map. A background image
is cropped to fill, and the first thing cropped off is the attribution.

---

## Deployment

`.github/workflows/deploy-slides.yml` builds on every push to `main` that
touches `slides/**`, the workflow, or one of the three screenshots, and
publishes `slides/dist` to GitHub Pages. The base path is derived from the
repository name, so a rename does not break every asset URL.

Pages deployment from Actions requires the repository to be **public**. While it
is private, the build job succeeds and the deploy job fails — that is repository
visibility, not a broken workflow.

---

## Notes for the talk

- **Presentation as code was the cheap part.** Setup to first rendered slide was
  one `npm install` and one Markdown file. What actually took the work was
  cutting three use cases and roughly twenty measured findings down to four
  rules that fit twelve minutes.
- **The verification loop applies to slides too.** Building the deck once was not
  enough: rendering it to PNG and *looking* at every slide caught three real
  defects that the build reported as success — two slides overflowing past the
  bottom edge with the punchline cut off, and `two-cols-header` running a long
  left column underneath the screenshot. A green build is not a readable slide,
  which is the same lesson as act 3: verify against the consumer, and here the
  consumer is a projector.
- **A convention caught its own violation.** The obvious cover design is the
  10,000-point map full-bleed behind the title. It renders with the basemap
  attribution cropped off — so the repository's own licence rule ruled out its
  own prettiest slide. Documented rather than quietly cropped.
- **Lesson learned.** The slot size is a design constraint, not a formatting
  detail. Deciding *up front* that new findings land in the backup and only
  displace an incumbent is what keeps a growing repository from turning into an
  unpresentable deck.
