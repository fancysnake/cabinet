---
name: mkdocs-site
description: >-
  Set up a project's documentation site on MkDocs Material, or bring an
  existing one up to the standard: the mkdocs.yml, the palette, the pages,
  the dependency, the mise tasks and the GitHub Pages workflow. Use whenever
  the user asks to add docs, a manual, a docs site or MkDocs to a repo, to
  review, upgrade, modernise or standardise a mkdocs.yml, or to publish
  docs to Pages.
---

# MkDocs site skill

One standard, extracted from the sites that already exist, applied to a
repo that has none or to one that drifted. Commits nothing unless asked.

Three files under `templates/` are the standard's shape; the steps below are
what you do with them and the rules that decide each key. A rule that names
a **legacy** form is the upgrade path for that key: found, change it.

| template | copy to |
| --- | --- |
| `templates/mkdocs.yml` | `mkdocs.yml` at the repo root |
| `templates/site.yml` | `.github/workflows/site.yml` |
| `templates/theme.css` | `docs/stylesheets/<theme>.css`, with an own palette |

## 1. Read the repo

Before editing, establish:

- **Stack.** Two, equally common, and the site is the same in both; only
  where `mkdocs-material` is declared and how a task reaches it differ:
  - **Python**, `pyproject.toml` with poetry → an optional poetry group.
  - **JS**, `package.json` with aube/node → a mise `pipx:` tool; nothing
    in `package.json`, the site is not a node dependency.

  `mise.toml` holds the tasks in both. Absent → say so, do not add mise;
  steps 6 and 7 say what such a repo gets instead.
- **Existing site.** `mkdocs.yml`, `docs/`, a docs workflow under
  `.github/workflows/`, `site/` in `.gitignore`. Present → you are diffing
  the steps below against files that exist rather than writing them; the
  standard is the same either way.
- **Identity.** Name from the manifest; license from `LICENSE`; the site
  URL from the existing `site_url`, `docs/CNAME`, or the README's docs link.
  None of those and the owner's other repos follow `<repo>.<domain>` → use
  it and record it; otherwise ask, offering `https://<owner>.github.io/<repo>`.
- **Prose that already exists.** README sections a page would restate,
  `CHANGELOG.md`, an example config file, a CLI. These become snippets
  and guards (step 4), not copies.

## 2. The config

Copy `templates/mkdocs.yml` to the repo root and fill the placeholders.
Keys stay in the template's order. Keep a comment that explains a choice,
delete one that states the obvious for this repo.

What each block is for, and when it changes:

| key | rule |
| --- | --- |
| `site_url` | `<repo>.<domain>`, the hostname from the repo name, not the package name; no trailing slash. Legacy: a trailing slash, drop it |
| `repo_name`, `copyright` | both always. Legacy: either missing, add it |
| `strict` | in the file, not on the command line: `mkdocs serve` then fails the same way. Legacy: `--strict` in a task or workflow, move it into the yaml and drop the flag |
| `validation` | `{anchors: warn}` always. Legacy: no `validation:` key, add it |
| `exclude_docs` | files kept in `docs/` for the author (a plan, a runbook) and out of the build; one directory tree, not two |
| `theme.logo` / `favicon` | `docs/assets/logo.png` and `docs/assets/favicon.png`; no artwork → `theme.icon.logo: material/<icon>` instead |
| `theme.features` | the template's two always; `navigation.sections` when `nav` has groups; `navigation.footer` for prev/next links; nothing else without a page that needs it |
| `theme.custom_dir: overrides` | only for an `overrides/main.html` that fills `{% block announce %}` with a status banner |
| `extra.social` | github, then PyPI if published, then the owner's site; the site's own URL is not a social link |
| `markdown_extensions` | only what a page uses, plus the floor: `toc`, `pymdownx.superfences`, and `pymdownx.highlight`, which superfences needs. Every other one — `admonition`, `pymdownx.details`, `pymdownx.snippets`, `attr_list`, `md_in_html`, `def_list`, `pymdownx.keys`, `pymdownx.tabbed: {alternate_style: true}`, `pymdownx.inlinehilite` — goes in when a page uses its syntax and comes out with the last page that used it, the same deletion rule as `theme.features`. Never `tables` or `fenced_code`, MkDocs enables those itself |
| `pymdownx.highlight` | add `anchor_linenums: true` only when a block uses `linenums` |
| `plugins` | leave the key out; `search` is on by default and listing `plugins:` without it removes it. Adding a plugin means listing `search` too. Legacy: `plugins: [search]` alone, delete the key |
| `nav` | paths only, titles come from each page's H1; a `Title: file.md` entry only when the two must differ, so drop it where the title equals the H1. Every page listed. Seven flat entries is the most a sidebar reads well at; eight or more → groups, plus `navigation.sections`. A group with a landing page uses `<group>/index.md` and `navigation.indexes` |
| `edit_uri` + `content.action.edit` | optional; add both or neither |
| `docs_dir`, `theme.icon.repo`, `tables` | never; all three are defaults. Legacy: present, delete |

## 3. The palette

Three forms, by how much of a look the project has. Do not mix them.

| the project has | do |
| --- | --- |
| no colours of its own | `scheme: default` / `scheme: slate` with a named Material `primary` and `accent` on each; no CSS |
| a palette (a brand colour, a logo) | own scheme names, `templates/theme.css` |
| `primary: custom` / `accent: custom` with `[data-md-color-primary="custom"]` CSS | legacy; migrate to own scheme names |

An own palette is two schemes named for the theme (`tower` / `tower-night`,
`eldritch` / `eldritch-dark`), no `primary` or `accent` in the yaml: those
generate their own rules, and two sources for one colour is one more than
the number that can be right. `templates/theme.css` carries the order — the
metaphor and the measured WCAG AA line, `:root`, a block per scheme, the
`--md-code-hl-*` set for both, then small chrome. Legacy:
`docs/assets/extra.css` or `docs/stylesheets/extra.css`, rename to
`docs/stylesheets/<theme>.css` and update `extra_css`.

Toggle icons and names follow the metaphor (`material/candle`, "Let the
candles gutter"); the light scheme is listed first.

## 4. The pages

`docs/` is the manual; `README.md` stays the front door and says so in its
first lines: `Documentation is at [<url>](<url>).`, with deep links to the
site where a README section would otherwise grow.

| page | carries |
| --- | --- |
| `index.md` | what it is in a paragraph, install, a "Where to go next" list linking every page with one clause each |
| `getting-started.md` | the first run, end to end |
| `configuration.md` | every setting: key, type, default, what it does; the example file included by snippet |
| `cli.md` | one section per command, when there is a CLI |
| `architecture.md` | layout of the code, for contributors |
| `changelog.md` | `--8<-- "CHANGELOG.md"` and nothing else, when the repo keeps one |

Prose that also lives elsewhere is included, never copied; a page found
pasting README or CHANGELOG text becomes an include, markers added at the
source.

- README sections are fenced with `<!-- --8<-- [start:<name>] -->` /
  `<!-- --8<-- [end:<name>] -->` and pulled by `--8<-- "README.md:<name>"`.
  `check_paths: true` makes a missing file fail the build.
- An example config is included inside a code fence with its own path.
- A page that names what the code exposes (a CLI reference, a settings
  table) gets a test that walks the code and the page and fails on a
  difference. It lives with the code's unit tests, beside the model or
  command it guards, not under `docs/`, and it is one test named for the
  claim it makes. The shape: read the page, cut the first fenced block of
  the language in question, parse it, load it into the type the code
  already has — a settings model that refuses unknown keys, the command
  objects of the CLI — and assert it equals what the code defaults to or
  exposes. Parsing one into the other is what keeps them in step; a
  string comparison against the rendered page is not, it breaks on
  whitespace and passes on a wrong default. No such type to parse into →
  no guard: flag the page in the report instead of inventing one.

  It runs in the code's CI. It runs in the site's workflow only when that
  workflow has the `paths:` filter of step 7, since that is the case where
  a docs-only change never reaches the code's CI.

Assets in `docs/assets/`, stylesheets in `docs/stylesheets/`.

## 5. The dependency

`mkdocs-material` alone; `mkdocs` comes with it, a separate pin is a
second version to keep in step. Legacy: both pinned, or the dependency in
the dev group — one optional `docs` group with `mkdocs-material`.
`pip install mkdocs-material` in a workflow step is not a dependency
declaration either; move it here.

**Python** — one optional poetry group. Renovate bumps it with the rest of
the lock file.

```toml
# Only `site:*` and the site workflow install this one — nothing else needs a
# static-site generator to run the tests.
[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs-material = ">=9.6,<10.0"
```

Or the same group in `[project.optional-dependencies]` form if that is
what the manifest already uses.

**JS** — a mise tool in `[tools]`, next to `node` and `aube`, with the
comment; the version is exact and `mise upgrade --bump` (the repo's
`update` task) moves it.

```toml
pipx = "<version>"
# --include-deps: the `mkdocs` binary belongs to a dependency, not to
# mkdocs-material itself, and pipx will not expose it otherwise. uvx = false
# because mise prefers uvx wherever `uv` is installed, and there
# --include-deps is neither accepted nor equivalent.
"pipx:mkdocs-material" = { version = "<latest>", uvx = false, pipx_args = "--include-deps" }
```

## 6. The tasks

Two, named `site:*`. Legacy: `site:serve` / `site:check`, `docs:serve` /
`docs:build`, a bare `docs` — rename, and update every reference (README,
`CLAUDE.md`, the workflow).

```toml
[tasks."site:dev"]
description = "Serve the documentation site with live reload"
run = "mkdocs serve"

[tasks."site:build"]
description = "Build the documentation site into site/"
run = "mkdocs build"
```

**JS** takes those two as they stand: the tool is on the path once
`mise install` has run.

**Python** prefixes each `run` with `poetry install --only docs --quiet &&`,
because the enter hook's plain `poetry install` skips an optional group, and
carries the reason as a comment above the first task:

```toml
# `--only docs` because mkdocs.yml declares no plugins: nothing here imports
# the package, so the package and the dev group are not worth installing.
```

`--with docs` instead of `--only docs` when a plugin does import the package
(mkdocstrings and the like).

**No `mise.toml`** — no tasks to add and none to invent a runner for. The
two commands are `mkdocs serve` and `mkdocs build`, run after installing
the docs group the repo now declares (`poetry install --only docs`, or the
`[project.optional-dependencies]` equivalent); a JS repo without mise
installs `mkdocs-material` the way it installs its other CLI tools. Name
both commands in the README, since nothing else records them.

No `--site-dir` variable: a workflow that wants the output elsewhere moves
`site/` after. Legacy: `--site-dir ${SITE_DIR:-site}` in a task, plain
`mkdocs build`. `/site` goes in `.gitignore`.

## 7. The workflow

Copy `templates/site.yml` to `.github/workflows/site.yml`; it is the shape
every current site uses. Then:

- Every action pinned to a commit SHA, the tag it was in a trailing
  comment. Take the SHAs from another workflow in the repo or from the
  action's release page; never a bare `@v4`. Legacy: a tag, pin it.
- `pages: write` and `id-token: write` on the deploy job only; the pull
  request build must not hold them. Legacy: either at workflow level, move
  them down.
- `cancel-in-progress: false` and the `pages` group on the deploy;
  cancelling a publish halfway leaves the site on the old commit.
- `mise install` is the whole toolchain in both stacks: the Python
  version and poetry, or node, aube and the `pipx:` tool. No
  `setup-python`, no `setup-node`, no `pip install`. Legacy: any of those
  three, replaced by the dependency of step 5 plus `mise install` and
  `mise run site:build`.
- **No `mise.toml`** — the two mise steps become the stack's own setup:
  `setup-python` plus `poetry install --only docs` (or the manifest's
  optional-dependency equivalent), or `setup-node`, then `mkdocs build`.
  Everything else in the template is unchanged, `pip install
  mkdocs-material` as a step still is not a dependency declaration, and
  the dependency still belongs in the manifest per step 5.
- `paths:` filters on both triggers (`docs/**`, `mkdocs.yml`, the manifest,
  `mise.toml`, the workflow itself) only when the main CI workflow ignores
  `docs/**`; then this is the workflow a docs-only change runs, and it is
  also where step 4's drift guard has to run, since the code's CI no longer
  sees the change. Without that filter, leave the guard to the code's CI.
- A JS site that publishes the app beside the manual (a demo at
  `/demo/`) installs the node dependencies (`aube install`), builds the
  app with its base path set (`<APP>_BASE: /demo`), builds the docs, then
  moves the app build under `site/demo` before the upload step. The manual
  is still the artifact; the app is a directory in it.
- `mkdocs gh-deploy` onto a `gh-pages` branch with `contents: write` and
  `fetch-depth: 0` is the legacy route; migrate to the build and deploy
  jobs of the template. `docs/CNAME` matters only there: with
  `deploy-pages` the domain is set in the repository's Pages settings and
  a CNAME file is inert, so do not add one.
- The repository's Pages source must be "GitHub Actions"; say so in the
  report, it cannot be set from the repo.

## 8. Upgrading

An existing site is the same job: diff it against steps 2–7 and apply
every rule, the legacy forms included. Keep what no rule names — a comment
that explains a choice, a page, a feature or extension a page uses; one no
page uses is a deletion.

## 9. Verify and report

Run the build task (`mise run site:build`, or `mkdocs build` where there is
no mise). Strict means the output is the verdict: a warning is a failure,
and the fix is the page or the config, never `strict: false`. Then:

- README names the site and the build task; `CLAUDE.md` (if any) names the
  task and that strict fails a broken link; `CHANGELOG.md` gets an
  `Unreleased` line when the site is new or its URL or tasks changed.
- Report one line per file touched, the Pages setting the user has to
  flip, and anything from step 1 you had to assume.
