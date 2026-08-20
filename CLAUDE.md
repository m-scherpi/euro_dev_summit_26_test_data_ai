# CLAUDE.md — Working Instructions for This Repository

Read this before doing anything in this repository. It defines the purpose, the
layout, the conventions and — most importantly — the **documentation duties**
that apply to every single task.

---

## 1. Project purpose

**Overall topic: Test (Geo-)Data Generation with GenAI.**

This repository is a collection of independent sub-projects ("use cases"), each
demonstrating a different way to generate, transform or validate test data —
with a strong focus on geospatial data — using generative AI.

The material is the basis for a **conference talk**. This has a hard
consequence for how we work: *the process matters as much as the result.*
Every prompt, every iteration, every dead end must be traceable afterwards, so
the talk can show not only "look, it works" but "this is how we got there".

Audience of the talk: developers and geo-IT practitioners. Assume they are
technical but not familiar with this repository.

---

## 2. Repository layout

```
devsummit/
├── CLAUDE.md          # this file — instructions for Claude
├── README.md          # human-facing overview + index of all use cases
├── PROMPT.md          # chronological log of all prompts and work steps
├── .gitignore
└── <use-case>/        # one folder per sub-project
    ├── README.md      # detailed docs for this use case
    ├── input/         # read-only source data
    └── output/        # generated artifacts only
```

Optional inside a use case, when needed: `src/`, `scripts/`, `tests/`,
`prompts/` (for prompt templates used by the code itself).

**Every new use case follows exactly this pattern.** Create
`<name>/{input,output}` plus a `<name>/README.md` — no exceptions, no
alternative folder names.

Folder naming: lowercase, `snake_case`, descriptive of the use case
(`csv_data`, `opensearch`, `python_import`).

---

## 3. Data conventions

**`input/` is read-only.**
Source data, seeds, schemas, real-world samples, prompt fixtures. Code may read
from here but must never write, move or overwrite anything in `input/`. If a
transformation needs an intermediate file, it goes to `output/`.

**`output/` is disposable.**
Only generated artifacts. It must always be safe to delete the entire folder and
regenerate its contents from `input/` plus the documented command. Never edit
files in `output/` by hand — if the result is wrong, fix the generator.

**Large data sets.**
Keep a small, committed sample (a few hundred rows / features) so the repository
stays readable and demo-able. Full-size runs go to `output/` and may be
gitignored. Always state the sample size and the full size in the README.

---

## 4. Tech-stack policy

**There is no global default stack.** Each use case picks whatever fits best —
Python, Node/TypeScript, shell, SQL, a REST client, an MCP server, whatever the
scenario calls for. Showing this variety is deliberate and part of the talk.

Rules that do apply regardless of stack:

- **Isolate dependencies per use case**: Python → `.venv/` or `uv` inside the
  use-case folder; Node → a local `package.json`. Never install globally.
- **Document the choice**: the use-case README states the stack *and one
  sentence on why it was chosen*. That reasoning is talk material.
- **Every executable is self-describing**: a CLI must support `--help` and
  print a usable summary of its arguments.
- **Every executable has a copy-pasteable example command** in its README —
  including the exact input path and expected output path.
- **Prefer relative paths** inside the use case, so commands work regardless of
  where the repository is cloned.

---

## 5. Documentation duties — mandatory after every task

After finishing any piece of work, update all four in this order. Do not wait
to be asked; this is the standing instruction.

1. **`PROMPT.md`** — append an entry using the format in section 6: the
   prompt *verbatim* in German, an English translation, and what actually
   happened, including what failed. Skip this step only if the user explicitly
   asked for the prompt not to be logged (see section 6).
2. **`<use-case>/README.md`** — purpose, stack, input, output, setup, usage,
   example output, notes for the talk.
3. **`README.md` (root)** — keep the use-case index, the executables table and
   the progress log current.
4. **`CLAUDE.md` (this file)** — whenever a new convention, tool or constraint
   emerges, write it down here so it does not have to be repeated in a prompt.

If a task changes nothing user-visible (e.g. pure research), still log it in
`PROMPT.md` — an unproductive iteration is a valid finding for the talk. The one
exception stays the explicit "do not log this" instruction.

---

## 6. `PROMPT.md` entry format

Entries are appended chronologically, newest at the bottom, numbered
sequentially.

The user prompts in **German**. Each entry therefore carries the original prompt
*and* an English translation, so the log stays readable for an
English-speaking audience without losing the original evidence.

```markdown
## [NNN] YYYY-MM-DD — <short title>  ·  scope: <folder or "root">

**Prompt (original, DE)**
> <original prompt, verbatim, unedited>

**Prompt (translation, EN)**
> <faithful English translation of the prompt above>

**What happened**
- <steps taken, decisions made, tools/models used>

**Artifacts**
- `path/to/file` — <purpose>

**Result / Iteration**
- <outcome; what did not work; follow-up needed>
```

Guidelines:
- The **original prompt is verbatim** — same language, same wording, including
  typos, abbreviations and inconsistent capitalisation. It is evidence, not
  documentation. Never clean it up.
- The **translation is faithful, not polished**: translate what was written,
  including its vagueness. Do not fix, expand or interpret the request in the
  translation. If a phrase is genuinely ambiguous in German, keep the ambiguity
  and, if needed, add a short `[note: ...]` marker.
- If a prompt happens to be written in English, keep a single
  `**Prompt**` block instead of the DE/EN pair.
- "What happened" is a summary, not a transcript — a handful of bullets.
- Be honest in "Result / Iteration". Failed attempts and course corrections are
  the most interesting part of the talk.

### Prompts excluded from the log

The user may explicitly ask for a prompt **not** to be logged (e.g. "logge
diesen Prompt nicht", "nicht protokollieren"). In that case:

- Do **not** add an entry to `PROMPT.md` for that prompt.
- Still apply everything else the prompt asks for, including any resulting
  updates to `CLAUDE.md`, `README.md` or existing `PROMPT.md` entries.
- Do not leave a placeholder, a gap in the numbering or a "redacted" note —
  the log simply continues with the next number.

This typically applies to meta-prompts about documentation and conventions,
which are noise for the talk narrative.

---

## 7. Notes for the talk

Each use-case README ends with a `Notes for the talk` section capturing:

- **What worked** — where GenAI was clearly faster or better than hand-writing.
- **What failed** — hallucinated values, invalid geometries, broken CRS,
  schema drift, non-determinism, cost/latency surprises.
- **Lesson learned** — the one sentence a listener should take away.

Write these down *while working*, not afterwards. Details get lost.

---

## 8. Language rules

- **Documentation, code, comments, identifiers, CLI texts, log output, commit
  messages: English.**
- **Chat communication with the user: German.**
- German umlauts and special characters must be written correctly wherever
  German text appears — never ASCII substitutions.

---

## 9. Reproducibility

Generated test data is only useful for a talk if it can be regenerated live.

- **Fix random seeds** and expose them as a CLI argument with a documented
  default.
- **Record the model and date** used for any GenAI-assisted generation (e.g.
  "generated with Claude Opus 5, 2026-08-20") in the use-case README.
- **Record the exact command** that produced the committed output.
- **Note non-determinism explicitly** where it exists — LLM output that varies
  between runs is a finding, not a bug to hide.
- **Never commit secrets.** API keys and endpoints come from environment
  variables; document the variable names, not the values.

---

## 10. Git & publication

This repository is version-controlled with Git and is **intended for public
release on GitHub** under the name `euro_dev_summit_26_test_data_ai`.

- Licence: **CC BY 4.0** (`LICENSE`, full official legal code — do not edit it,
  or GitHub will stop detecting the licence). Attribution notice lives in
  `README.md`. Anything added to this repository must be compatible with
  publication under CC BY.
- Default branch: `main`. Work directly on `main` unless asked otherwise.
- **Commit messages in English**, imperative mood, one logical change per
  commit (`Add CSV generator for address test data`).
- The commit history is part of the talk material: it should read as a
  comprehensible sequence of work steps. Prefer several meaningful commits over
  one bulk commit.
- **Commit only when asked.** Never push without an explicit request.

Because the repository will be public, the following must never be committed:

- API keys, tokens, endpoints of internal systems, `.env` files.
- Real customer data, internal company data, or any production geodata.
  Everything in `input/` must be synthetic, public (e.g. open data), or
  explicitly cleared for publication. If in doubt, ask before adding it.
- Personal data — generated person records must be obviously fictitious.

Note: this is exactly the point the talk makes. Not being allowed to use real
data is the very reason generated test data is needed.

---

## 11. Working style

- Ask before restructuring existing use cases; new use cases can be created
  freely following the layout above.
- Keep sub-project READMEs skimmable — the root README is the index, details
  live locally.
- No unrequested extras: build the use case that was asked for, then document it.
