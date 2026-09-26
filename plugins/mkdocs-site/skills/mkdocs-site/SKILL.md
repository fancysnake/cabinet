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

## 1. Read the repo

Before editing, establish:

- **Stack.** Two, equally common, and the site is the same in both; only
  where `mkdocs-material` is declared and how a task reaches it differ:
  - **Python**, `pyproject.toml` with poetry → an optional poetry group.
  - **JS**, `package.json` with aube/node → a mise `pipx:` tool; nothing
    in `package.json`, the site is not a node dependency.

  `mise.toml` holds the tasks in both. Absent → say so, do not add mise.
- **Existing site.** `mkdocs.yml`, `docs/`, a docs workflow under
  `.github/workflows/`, `site/` in `.gitignore`. Present → this is an
  upgrade (step 8); absent → a setup (steps 2–7).
- **Identity.** Name from the manifest; license from `LICENSE`; the site
  URL from the existing `site_url`, `docs/CNAME`, or the README's docs link.
  None of those and the owner's other repos follow `<repo>.<domain>` → use
  it and record it; otherwise ask, offering `https://<owner>.github.io/<repo>`.
- **Prose that already exists.** README sections a page would restate,
  `CHANGELOG.md`, an example config file, a CLI. These become snippets
  and guards (step 4), not copies.

## 2. The config

`mkdocs.yml` at the repo root, keys in this order. Comments in the file
explain a choice that is not obvious; delete the ones below that are.

```yaml
site_name: <name>
site_url: https://<name>.<domain>          # no trailing slash
site_description: <one sentence, the README's tagline>
repo_url: https://github.com/<owner>/<repo>
repo_name: <owner>/<repo>
copyright: <SPDX id of LICENSE>           # MIT, BSD-3-Clause, …

# A link to a page that is not there is what rots first when a page is
# renamed, and from here it fails `site:dev` as well as `site:build`.
strict: true

# Under strict a warning is a failure; anchors are how cross-references
# between pages actually break, and MkDocs only logs them at info.
validation:
  anchors: warn

theme:
  name: material
  logo: assets/logo.png
  favicon: assets/favicon.png
  palette:                                 # step 3
    - media: "(prefers-color-scheme: light)"
      scheme: <light scheme>
      toggle: {icon: material/weather-night, name: Switch to dark mode}
    - media: "(prefers-color-scheme: dark)"
      scheme: <dark scheme>
      toggle: {icon: material/weather-sunny, name: Switch to light mode}
  features:
    - content.code.copy
    - navigation.top

extra:
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/<owner>/<repo>
    - icon: fontawesome/brands/python              # only if on PyPI
      link: https://pypi.org/project/<name>/
    - icon: fontawesome/solid/globe
      link: https://<domain>
      name: <domain>

extra_css:                                 # only with an own palette
  - stylesheets/<theme>.css

markdown_extensions:
  - admonition
  - toc: {permalink: true}
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.details
  # Shared prose lives in README.md and is included from there, so the two
  # cannot drift. base_path is the repo root, which is where mkdocs runs.
  - pymdownx.snippets: {base_path: ["."], check_paths: true}

nav:
  - index.md
  - getting-started.md
  - configuration.md
  - architecture.md
```

What each block is for, and when it changes:

| key | rule |
| --- | --- |
| `strict` | in the file, not on the command line: `mkdocs serve` then fails the same way |
| `exclude_docs` | files kept in `docs/` for the author (a plan, a runbook) and out of the build; one directory tree, not two |
| `theme.logo` / `favicon` | `docs/assets/logo.png` and `docs/assets/favicon.png`; no artwork → `theme.icon.logo: material/<icon>` instead |
| `theme.features` | these two always; `navigation.sections` when `nav` has groups; `navigation.footer` for prev/next links; nothing else without a page that needs it |
| `theme.custom_dir: overrides` | only for an `overrides/main.html` that fills `{% block announce %}` with a status banner |
| `extra.social` | github, then PyPI if published, then the owner's site; the site's own URL is not a social link |
| `markdown_extensions` | the five above always; `snippets` when a page includes another file; `attr_list`, `md_in_html`, `def_list`, `pymdownx.keys`, `pymdownx.tabbed: {alternate_style: true}`, `pymdownx.inlinehilite` only when a page uses the syntax; never `tables` or `fenced_code`, MkDocs enables those itself |
| `pymdownx.highlight` | add `anchor_linenums: true` only when a block uses `linenums` |
| `plugins` | leave the key out; `search` is on by default and listing `plugins:` without it removes it. Adding a plugin means listing `search` too |
| `nav` | paths only, titles come from each page's H1; a `Title: file.md` entry only when the two must differ. Every page listed. Six or more pages → groups, plus `navigation.sections`. A group with a landing page uses `<group>/index.md` and `navigation.indexes` |
| `edit_uri` + `content.action.edit` | optional; add both or neither |
| `docs_dir`, `theme.icon.repo` | never; both are the defaults |

## 3. The palette

Three forms, by how much of a look the project has. Do not mix them.

| the project has | do |
| --- | --- |
| no colours of its own | `scheme: default` / `scheme: slate` with a named Material `primary` and `accent` on each; no CSS |
| a palette (a brand colour, a logo) | own scheme names, see below |
| `primary: custom` / `accent: custom` with `[data-md-color-primary="custom"]` CSS | legacy; migrate to own scheme names |

An own palette is two schemes named for the theme (`tower` / `tower-night`,
`eldritch` / `eldritch-dark`), no `primary` or `accent` in the yaml: those
generate their own rules, and two sources for one colour is one more than
the number that can be right. The stylesheet is `docs/stylesheets/<theme>.css`,
named for the theme, not `extra.css`, and holds, in this order:

1. A header comment: the metaphor in two lines, then the constraint: every
   pairing clears WCAG AA against the surface it sits on, measured, with the
   tightest ratio stated.
2. `:root` with the named colours (`--<theme>-ink`, `--<theme>-paper`, …).
3. `[data-md-color-scheme="<light>"]` and `[data-md-color-scheme="<dark>"]`,
   each starting with `color-scheme: light|dark`, then the Material
   variables: `--md-default-bg/fg-color` and its `--light/--lighter/--lightest`
   steps, `--md-primary-fg-color` and `--light/--dark`, `--md-primary-bg-color`,
   `--md-accent-fg-color` and `--transparent`, `--md-typeset-a-color`,
   `--md-typeset-mark-color`, `--md-code-bg/fg-color`, `--md-footer-bg-color`
   and `--dark`.
4. The `--md-code-hl-*-color` set for both schemes; Material's default does
   not agree with a palette it has never heard of, and a code block is most
   of what these pages are.
5. Small chrome, each with a one-line comment: a `.md-typeset .headerlink::before`
   glyph, a ruled `h1` border, a header gradient. Nothing that restyles a
   component wholesale.

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

Prose that also lives elsewhere is included, never copied:

- README sections are fenced with `<!-- --8<-- [start:<name>] -->` /
  `<!-- --8<-- [end:<name>] -->` and pulled by `--8<-- "README.md:<name>"`.
  `check_paths: true` makes a missing file fail the build.
- An example config is included inside a code fence with its own path.
- A page that names what the code exposes (a CLI reference, a settings
  table) gets a test that walks the code and the page and fails on a
  difference; it runs in the code's CI and the site's, since either side
  can be the one that drifts.

Assets in `docs/assets/`, stylesheets in `docs/stylesheets/`.

## 5. The dependency

`mkdocs-material` alone; `mkdocs` comes with it, a separate pin is a
second version to keep in step.

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

`pip install` in a workflow step is not a dependency declaration; move it
to one of the above.

## 6. The tasks

Two, named `site:*`. `site:serve` / `site:check`, `docs:serve` /
`docs:build` and a bare `docs` are the older names.

**Python** — each task installs first, because the enter hook's plain
`poetry install` skips an optional group.

```toml
# `--only docs` because mkdocs.yml declares no plugins: nothing here imports
# the package, so the package and the dev group are not worth installing.
[tasks."site:dev"]
description = "Serve the documentation site with live reload"
run = "poetry install --only docs --quiet && mkdocs serve"

[tasks."site:build"]
description = "Build the documentation site into site/"
run = "poetry install --only docs --quiet && mkdocs build"
```

`--with docs` instead of `--only docs` when a plugin imports the package
(mkdocstrings and the like).

**JS** — the tool is on the path once `mise install` has run, so the tasks
are the bare commands.

```toml
[tasks."site:dev"]
description = "Serve the documentation site with live reload"
run = "mkdocs serve"

[tasks."site:build"]
description = "Build the documentation site into site/"
run = "mkdocs build"
```

No `--strict` flag in either: it is in the file. No `--site-dir` variable:
a workflow that wants the output elsewhere moves `site/` after. `/site`
goes in `.gitignore`.

## 7. The workflow

`.github/workflows/site.yml`, named `Site`. Copy this shape; it is the
one every current site uses.

```yaml
---
name: Site

on:
  pull_request:
  push:
    branches: ["main"]

concurrency:
  group: site-${{ github.event.pull_request.number || github.run_id }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha> # v7
        with:
          persist-credentials: false
      - uses: jdx/mise-action@<sha> # v4
      - run: mise install
      - run: mise run site:build
      - uses: actions/upload-pages-artifact@<sha> # v5
        with:
          path: site/

  # Pages has no per-pull-request preview, so a pull request builds and stops
  # there. The build is the review; the deploy waits for main.
  deploy:
    if: github.event_name == 'push'
    needs: build
    runs-on: ubuntu-latest
    # Its own group, because a deploy wants the opposite policy to a build: a
    # publish cut off halfway leaves the site on the old commit, so two merges
    # queue here rather than cancel each other.
    concurrency:
      group: pages
      cancel-in-progress: false
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    permissions:
      pages: write
      id-token: write
    steps:
      - id: deployment
        uses: actions/deploy-pages@<sha> # v5
```

- Every action pinned to a commit SHA, the tag it was in a trailing
  comment. Take the SHAs from another workflow in the repo or from the
  action's release page; never a bare `@v4`.
- `pages: write` and `id-token: write` on the deploy job only; the pull
  request build must not hold them.
- `mise install` is the whole toolchain in both stacks: the Python
  version and poetry, or node, aube and the `pipx:` tool. No
  `setup-python`, no `setup-node`, no `pip install`.
- `paths:` filters on both triggers (`docs/**`, `mkdocs.yml`, the manifest,
  `mise.toml`, the workflow itself) only when the main CI workflow ignores
  `docs/**`; then this is the workflow a docs-only change runs, and it also
  runs any drift guard from step 4.
- A JS site that publishes the app beside the manual (a demo at
  `/demo/`) installs the node dependencies (`aube install`), builds the
  app with its base path set (`<APP>_BASE: /demo`), builds the docs, then
  moves the app build under `site/demo` before the upload step. The manual
  is still the artifact; the app is a directory in it.
- `mkdocs gh-deploy` onto a `gh-pages` branch with `contents: write` is the
  legacy route; migrate to the artifact deploy. `docs/CNAME` matters only
  there: with `deploy-pages` the domain is set in the repository's Pages
  settings and a CNAME file is inert, so do not add one.
- The repository's Pages source must be "GitHub Actions"; say so in the
  report, it cannot be set from the repo.

## 8. Upgrading

Diff the existing files against steps 2–7, then apply every row that
matches. Keep what the table does not name: a comment that explains a
choice, a page, a feature a page uses.

| found | change to |
| --- | --- |
| `--strict` in a task or workflow, no `strict:` in the yaml | `strict: true` in the yaml, flag removed |
| no `validation:` | `validation: {anchors: warn}` |
| `site_url` with a trailing slash | without |
| no `repo_name`, no `copyright` | add both |
| `docs_dir: docs`, `theme.icon.repo`, `tables`, `plugins: [search]` alone | delete; defaults |
| `primary: custom` / `accent: custom` | own scheme names and a `docs/stylesheets/<theme>.css` per step 3 |
| `docs/assets/extra.css`, `docs/stylesheets/extra.css` | `docs/stylesheets/<theme>.css`, `extra_css` updated |
| `Title: file.md` in `nav` where Title equals the page's H1 | `file.md` |
| a page that pastes README or CHANGELOG text | a snippet include, markers in the source |
| `mkdocs` and `mkdocs-material` both pinned, or in the dev group | one optional `docs` group with `mkdocs-material` |
| `pip install mkdocs-material`, `setup-python`, `setup-node` in the workflow | dependency per step 5, `mise install`, `mise run site:build` |
| `docs:serve` / `docs:build` / `docs` / `site:serve` / `site:check` tasks | `site:dev` / `site:build`; update every reference (README, CLAUDE.md, workflow) |
| `--site-dir ${SITE_DIR:-site}` in a task | plain `mkdocs build`; the workflow moves `site/` if it must |
| `gh-deploy`, `contents: write`, `fetch-depth: 0` | build + deploy jobs per step 7 |
| actions pinned to a tag | commit SHA with the tag as comment |
| `pages: write` at workflow level | on the deploy job |
| `cancel-in-progress: true` on the deploy | `false`, own `pages` group |

A feature or extension no page uses is a deletion; one a page uses stays
even if the table above does not list it.

## 9. Verify and report

Run the build task (`mise run site:build`, or `mkdocs build` where there is
no mise). Strict means the output is the verdict: a warning is a failure,
and the fix is the page or the config, never `strict: false`. Then:

- README names the site and the build task; `CLAUDE.md` (if any) names the
  task and that strict fails a broken link; `CHANGELOG.md` gets an
  `Unreleased` line when the site is new or its URL or tasks changed.
- Report one line per file touched, the Pages setting the user has to
  flip, and anything from step 1 you had to assume.
