# Prompt Log

Chronological record of every prompt issued in this repository and what came out
of it. Newest entries at the bottom.

Prompts are written in German and are quoted **verbatim** — they are evidence of
the process, not documentation. A faithful English translation follows each
original so the log stays readable for an English-speaking audience.

Meta-prompts that only concern documentation and conventions are excluded from
this log on request; the numbering stays continuous.

Entry format, conventions and documentation duties: see [`CLAUDE.md`](CLAUDE.md).

---

## [001] 2026-08-20 — Repository scaffolding & working conventions  ·  scope: root

**Prompt (original, DE)**
> In der vorliegenden Ordner-Struktur sollen verschiedenen Teilprojekte entstehen, die jeweils in einem Ordner liegen, in denen es noch einmal separat "Input" und "Output" geben soll. DAS generelle Oberthema lautet "Test(Geo-)daten Generierung per GenAI". Im folgenden werde ich in den einzelnen Unterordnern verschiedene Use-Cases abarbeiten. Was genau da drin passiert, soll in einer README.md auf Root Level festgehalten werden, auch die Nutzung von z.B. entstehenden Executables.. Schreibe dir selber eine Anweisungs-Datei (claude.md), in der du Generelle Infos und Anweisungen festhälst, sodass ich nicht für jeden Prompt Dinge wiederholen muss. Pflege diese auch weiter, wenn es änderungen gibt. Pflege auch die Readme. Beispielsweise möchte ich, dass du im Folgenden die Prompts, die ich Absetze in einer PROMPT.md protokollierst. Auch soll grob festgehalten werden, was genau passiert, sodass die einzelnen Arbeitsschritte und ein iteratives Vorgehen protokolliert wird. Am ende soll alles nachvollziehbar sein, da ich über das Thema einen Vortrag halten werde. Ich möchte über verschiedene Beispiele und Use Cases berichten, welche wir im folgenden entwickeln werden.

**Prompt (translation, EN)**
> In the present folder structure, several sub-projects are to be created, each located in a folder, in which there should again be a separate "Input" and "Output". THE general overarching topic is "Test (Geo-)data Generation via GenAI". In what follows, I will work through various use cases in the individual subfolders. What exactly happens in there should be recorded in a README.md at root level, including the usage of e.g. resulting executables.. Write yourself an instruction file (claude.md) in which you record general information and instructions, so that I do not have to repeat things for every prompt. Also keep this maintained if there are changes. Also maintain the Readme. For example, I want you to log the prompts that I issue in a PROMPT.md in what follows. It should also be roughly recorded what exactly happens, so that the individual work steps and an iterative approach are documented. In the end everything should be traceable, since I am going to give a talk on the topic. I want to report on various examples and use cases which we will develop in what follows.

**What happened**
- Inspected the starting point: three empty use-case folders (`csv_data/`,
  `opensearch/`, `python_import/`), each with empty `input/` and `output/`. No
  files, no git repository, no existing conventions.
- Clarified three open decisions with the user before writing anything:
  - **Tech stack**: no global default — chosen per use case and justified in
    that use case's README. Rationale: the variety itself is talk material.
  - **Documentation language**: English (chat communication stays German).
  - **Documentation granularity**: root README as index, plus one README per
    use case. Scales better as the number of use cases grows.
- Wrote the three control documents (`CLAUDE.md`, `README.md`, `PROMPT.md`),
  a `.gitignore` prepared for later versioning, and README stubs for the three
  known use cases.
- Named the instruction file `CLAUDE.md` rather than `claude.md`: on Linux the
  filename is case-sensitive and only the uppercase variant is auto-loaded as
  project context by Claude Code.
- Added `.gitkeep` files so the empty `input/`/`output/` folders survive a
  later `git init`.
- Model used: Claude Opus 5.

**Artifacts**
- `CLAUDE.md` — standing instructions: purpose, layout, data conventions,
  tech-stack policy, documentation duties, prompt-log format, language rules,
  reproducibility requirements
- `README.md` — overview, structure, use-case index, executables table,
  short-form conventions, progress log
- `PROMPT.md` — this log
- `.gitignore` — venv/node_modules/secrets ignored; bulk `output/` ignored while
  keeping the folder structure
- `csv_data/README.md`, `opensearch/README.md`, `python_import/README.md` —
  stubs with a uniform skeleton, status "not started yet"
- `.gitkeep` in all six `input/`/`output/` folders

**Result / Iteration**
- Scaffolding complete; no use case implemented yet — this step was deliberately
  setup only.
- Deferred by design: **no `git init`**. Version control would noticeably improve
  traceability for the talk, but the user did not ask for it. Flagged as an
  optional follow-up.
- The three use-case descriptions in the root index are placeholders. They get
  filled in when the respective use case is actually started, since the concrete
  scenario is not defined yet.
- Open question for the next iteration: which use case to start with, and
  whether the talk should follow a "simple → complex" progression (tabular CSV →
  geospatial → search index).

---

## [002] 2026-08-20 — Git repository initialised  ·  scope: root

**Prompt (original, DE)**
> lege ein git repository mit dem Namen "euro_dev_summit_26_test_data_ai" an. Dieses soll später auf meinem Github account veröffentlicht werden

**Prompt (translation, EN)**
> create a git repository with the name "euro_dev_summit_26_test_data_ai". This is to be published on my Github account later on

**What happened**
- Checked the environment: Git 2.43.0, `user.name` / `user.email` already
  configured globally, no existing repository. The `gh` CLI is **not installed**
  on this machine.
- `git init -b main` — explicit branch name to avoid the legacy `master`
  default, since `init.defaultBranch` was unset.
- Verified via `git add -An` and `git check-ignore` that the intended 13 files
  are tracked and that the `.gitignore` negation for `*/output/.gitkeep` works —
  the empty `input/`/`output/` folders survive without dragging in bulk output.
- Did **not** rename the working directory (`devsummit`) to the repository name.
  The name matters for the GitHub remote; renaming would break this session's
  working directory for no benefit.
- Documented publication constraints in `CLAUDE.md` (new section 10): English
  commit messages, commit history as talk material, and a hard rule that no
  credentials, customer data, production geodata or real personal data may be
  committed.
- Created the initial commit.

**Artifacts**
- `.git/` — repository, branch `main`
- `CLAUDE.md` — new section 10 "Git & publication"; former section 10
  "Working style" renumbered to 11
- `README.md` — new "Repository" section, progress log entry

**Result / Iteration**
- Local repository ready; **not** published yet. No remote configured, nothing
  pushed — publishing needs the user's GitHub account and an explicit go-ahead.
- Blocker for later: `gh` is not installed, so `gh repo create` is unavailable.
  Either install `gh`, or create the repository in the GitHub web UI and add the
  remote manually.
- Open point: no `LICENSE` file yet. A public talk repository should state a
  licence — worth deciding before publication.
- The commit author is the company address `m.scherpinski@conterra.de`. Fine for
  a conference repository, but it becomes publicly visible — flagged in case a
  different address is preferred.
