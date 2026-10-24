# cabinet

A [vekna](https://vekna.fancysnake.dev) **tome**: pull request and issue
maintenance rituals, installed as a package and cast from any repository on GitHub or
GitLab (hosted or self-hosted).

Documentation is at [cabinet.fancysnake.dev](https://cabinet.fancysnake.dev).

## The rituals

Grouped by school, the way a spellbook is.

### Evocation

- **`heal.mine`** and **`heal.this`**: take each pull request as far as it
  goes. `heal.mine` takes every open pull request of yours not wearing the
  wait label, oldest-modified first; `heal.this` takes the one for the branch
  at the cwd. Each pull request is surveyed into its todos (merge, ci, answer,
  review, guide) and printed on one line; then the merge, ci, answer and review
  tasks are worked, and what was committed is pushed. Threads are answered
  only with `--attended true`. `--plan-only true` stops after the
  survey and changes nothing.

### Transmutation

- **`merge`**: `heal.this` with the merge task alone. Where your branch
  conflicts with its base, it merges the base in, has an agent resolve the
  conflicts, makes the gate green, and pushes. Like *Mending*: what was split
  is joined.

### Abjuration

- **`ci`**: `heal.this` with the ci task alone. Reruns a flaky job once, or
  has an agent fix each red job from its log, against the job's own `gate`
  where it has one, and covers the lines a coverage job names with tests.
  Like *Lesser Restoration*: one condition ended at a time.

### Enchantment

- **`answer`**: `heal.this` with the answer task alone, attended only. An
  agent triages the open review threads, you decide each item, another agent
  fixes what you said to fix, and the ritual posts the replies, files the
  issues, settles the threads, and commits and pushes the fixes once the gate
  is green. Like *Command*: one word to each listener.

### Divination

- **`review`**: `heal.this` with the review task alone. Posts the quality
  review as inline comments and puts the reviewed label on.
- **`identify`**: the backlog, a page at a time. Takes your open issues that
  lack a type or a size; an agent reads each one and says what it is, and the
  ritual puts that on the forge: a type and a size, or an epic split into
  sub-issues, and the links between them. A write the forge refuses is
  reported on its issue, and the cast goes on unless the forge refused
  every write on a page.

### Conjuration

- **`labels`**: makes every label cabinet uses: what `labels.heal` and
  `labels.identify` make, in one cast. Cast it once to set a project up.
- **`labels.heal`**: makes the labels `heal` reads and puts on: reviewed,
  wait and qa. Cast it again after changing `[cabinet.labels]`.
- **`labels.identify`**: makes the labels `identify` puts on issues: the types
  (`feature`, `edit`, `chore`, `bug`), the sizes (`S`, `M`, `L`) and
  `epic`.

Every label ritual creates what is missing and refreshes what is there, so
casting one twice is as safe as once.

<!-- --8<-- [start:cast] -->
```bash
vekna cast heal.mine [--plan-only true] [--bound N] [--attended true] [--batch N]
vekna cast heal.this [--plan-only true] [--bound N] [--attended true] [--batch N]
vekna cast merge [--plan-only true] [--bound N] [--attended true]
vekna cast ci [--plan-only true] [--bound N] [--attended true]
vekna cast answer [--plan-only true] [--bound N] --attended true [--batch N]
vekna cast review [--plan-only true] [--attended true]
vekna cast identify [--batch N]
vekna cast labels
vekna cast labels.heal
vekna cast labels.identify
```
<!-- --8<-- [end:cast] -->

`--bound` is how many times one step may be retried on one branch, 1 to 5,
default 3. `--attended true` says somebody is at the terminal: the cast answers
review threads with you, asks before every repair attempt instead of letting
the budget decide, and runs its agents in Claude's `auto` permission mode.
`identify` asks you about every page. `--batch` is how many issues go on one
page, or how many open threads one round of answers takes, default 7.

## Install

cabinet is not on PyPI; it is installed straight from this repository, and
runs on Python 3.11 through 3.15. In the repository that wants the rituals:

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
the first cast.

Run every cast in a sandbox, attended or not. Every agent has a shell and can
read any file you can; nothing in cabinet keeps it to the repository. The
[Agents](https://cabinet.fancysnake.dev/agents/#the-sandbox-is-the-only-boundary)
page says why the sandbox is the only boundary.

## Claude Code plugins

The repository is also a Claude Code plugin marketplace, named `cabinet`.
Its plugins live under `plugins/`, each with its own manifest and skills.

<!-- --8<-- [start:plugins] -->
| plugin          | what it does                                                            |
| --------------- | ----------------------------------------------------------------------- |
| `issues`        | writes, types, sizes and links issues; what `identify` follows          |
| `release-bump`  | cuts a release: the version, the changelog, the docs                    |
| `mkdocs-site`   | sets up a MkDocs site, or upgrades one to the standard                  |
| `smoke-test`    | writes the fifteen-minute manual check for a web or CLI change          |
| `modern-python` | writes Python with the newest idioms the project's floor version allows |
<!-- --8<-- [end:plugins] -->

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
vekna rituals show heal.mine
```
<!-- --8<-- [end:development] -->
