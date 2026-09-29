# cabinet

A [vekna](https://vekna.fancysnake.dev) **tome**: pull request maintenance
rituals, installed as a package and cast from any repository on GitHub or
GitLab (hosted or self-hosted).

Documentation is at [cabinet.fancysnake.dev](https://cabinet.fancysnake.dev).

## The rituals

Grouped by school, the way a spellbook is.

### Transmutation

- **`refresh`** — the night's fast pass. Every open pull request of yours
  gets the base branch merged in, conflicts resolved, the gate made green, the
  work pushed and a quality review posted. Like *Purify Food and Drink*: what
  was there is still there, only fit to use.

### Abjuration

- **`cover`** — the night's slow pass. Where CI says the coverage or the
  suite is unhappy, it measures, writes the tests for what the branch left
  uncovered, repairs a red suite, and pushes. Building the defences up.

### Divination

- **`review`** — the morning after. Reads the review threads the night left,
  triages them with you at the terminal, answers every one, makes the gate
  green and ships the branch. Discovering what was found, and settling it.
- **`refine`** — the backlog, a page at a time. Takes your open issues that
  lack a type or a size, and an agent gives each one a type and a size, splits
  one too big for a pull request into an epic with sub-issues, and links the
  related ones. You say yes to each page first.

### Conjuration

- **`labels:pr`** — makes every label the pull request rituals read and
  write: the reviewed and wait labels and each ritual's `started`/`done`
  checkpoints, created where missing and refreshed where present. Cast it once
  before the first sweep, and again after changing `[cabinet.labels]`.
- **`labels:issue`** — makes the labels `refine` puts on issues: the types
  (`feature`, `edit`, `chore`, `spike`, `bug`), the sizes (`S`, `M`, `L`) and
  `epic`. Cast it once before the first `refine`.

<!-- --8<-- [start:cast] -->
```bash
vekna cast refresh [--bound N] [--attended true]
vekna cast cover [--bound N] [--attended true]
vekna cast review [--bound N] [--batch N]
vekna cast refine [--batch N]
vekna cast labels:pr
vekna cast labels:issue
```
<!-- --8<-- [end:cast] -->

`--bound` is how many times one step may be retried on one branch, 1 to 5,
default 3. `--attended true` says somebody is at the terminal: the sweep asks
before every repair attempt instead of letting the budget decide, and its
agents run in Claude's `auto` permission mode. `review` and `refine` are
always attended. `--batch` is how many open threads `review` reads and answers
in one round before fetching what is still open, default 7: a forty-thread
review is six triages you can hold in your head, and still one commit. On
`refine` it is how many issues go on one page, default 7.

## Install

cabinet is not on PyPI; it is installed straight from this repository, and
runs on Python 3.11 through 3.14. In the repository that wants the rituals:

```bash
poetry add --group dev git+https://github.com/fancysnake/cabinet.git
```

Pin a tag or a commit rather than riding `main`, so a cast tonight runs the
rituals you read yesterday:

```bash
poetry add --group dev git+https://github.com/fancysnake/cabinet.git#<tag-or-sha>
```

Either way the dependency lands in `pyproject.toml` as

```toml
[dependency-groups]
dev = ["cabinet @ git+https://github.com/fancysnake/cabinet.git@<tag-or-sha>"]
```

and `poetry install` brings `vekna` and its `trial` extra with it. Then tell
vekna where the rituals are and the rituals what the repository is:

<!-- --8<-- [start:vekna-toml] -->
```toml
# .vekna.toml
[rituals]
modules = ["cabinet.rituals"]

[cabinet]
forge = "github"                      # or "gitlab"
gate = "mise run pr-fix"
```
<!-- --8<-- [end:vekna-toml] -->

Every `[cabinet]` key has a default; the
[configuration reference](https://cabinet.fancysnake.dev/configuration/)
lists them all, with the review skill to fetch and the remote to set up before
the first cast. What an agent may do during one is at
[Agents](https://cabinet.fancysnake.dev/agents/).

## Claude Code plugins

The repository is also a Claude Code plugin marketplace, named `cabinet`.
Its plugins live under `plugins/`, each with its own manifest and skills.

| plugin         | what it adds                                 |
| -------------- | -------------------------------------------- |
| `issues`       | a skill for writing, typing, sizing and linking issues |
| `release-bump` | a skill that cuts a release                  |
| `mkdocs-site`  | a skill that sets up or upgrades a MkDocs site |
| `smoke-test`   | a skill that writes the fifteen-minute manual check for a web or CLI change |

<!-- --8<-- [start:plugins-install] -->
Add the marketplace once, then install what you want:

```bash
claude plugin marketplace add fancysnake/cabinet
claude plugin install issues@cabinet
```

Or from inside a session: `/plugin marketplace add fancysnake/cabinet`, then
`/plugin install issues@cabinet`.
<!-- --8<-- [end:plugins-install] -->

What each skill does, step by step, is at
[Plugins](https://cabinet.fancysnake.dev/plugins/).

## Layout

[GLIMPSE](https://glimpse.fancysnake.dev/) layering under `src/cabinet`,
enforced by import-linter; the
[architecture page](https://cabinet.fancysnake.dev/architecture/) draws it.

## Development

<!-- --8<-- [start:development] -->
```bash
mise run test:py       # the suite
mise run lint:py       # every linter
mise run fullcheck     # the gate before a commit
mise run site:dev      # the docs site, with live reload
mise run site:build    # the docs site, as the Pages workflow builds it
vekna rituals show refresh
```
<!-- --8<-- [end:development] -->
