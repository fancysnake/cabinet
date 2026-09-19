# cabinet

A [vekna](https://vekna.fancysnake.dev) **tome**: pull request maintenance
rituals, installed as a package and cast from any repository on GitHub or
GitLab (hosted or self-hosted).

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

### Conjuration

- **`labels`** — makes every label the other rituals read and write: the
  reviewed and wait labels and each ritual's `started`/`done` checkpoints,
  created where missing and refreshed where present. Cast it once before the
  first sweep, and again after changing `[cabinet.labels]`.

```bash
vekna cast refresh [--bound N] [--attended true]
vekna cast cover [--bound N] [--attended true]
vekna cast review [--bound N] [--batch N]
vekna cast labels
```

`--bound` is how many times one step may be retried on one branch, 1 to 5,
default 3. `--attended true` says somebody is at the terminal: the sweep asks
before every repair attempt instead of letting the budget decide, and its
agents run in Claude's `auto` permission mode (see below). `review` is always
attended. `--batch` is how many open threads `review` reads and answers in one
round before fetching what is still open, default 7: a forty-thread review is
six triages you can hold in your head, and still one commit.

### Using only some of them

Each ritual has a facade of its own under `cabinet.rituals`, so a project
names the ones it wants. A repository with no coverage task casts `refresh`
and `review` and never sees `cover`:

```toml
[rituals]
modules = ["cabinet.rituals.refresh", "cabinet.rituals.review"]
```

`modules = ["cabinet.rituals"]` loads all four.

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

```toml
# .vekna.toml
[rituals]
modules = ["cabinet.rituals"]

[cabinet]
forge = "github"                      # or "gitlab"
base = "main"
remote = "origin"
gate = "mise run pr-fix"
coverage = "mise run diff-cover"
fast_coverage = "mise run test:py:cov:diff"
sign_commits = true
review_skill = "~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md"
review_title = "Thermo-nuclear code quality review"

[cabinet.labels]
reviewed = "pr::thermo"               # a review was posted; take it off to ask again
wait = "pr::wait"                     # hands off this pull request
marker = "v"                          # checkpoints: v:refresh:started, v:cover:done, ...

[cabinet.ci]
gate_checks = ["checks", "test"]      # prefixes of the jobs the gate reruns
cover_checks = ["codecov/", "test"]   # prefixes of the jobs the slow pass reads
patch_check = "codecov/patch"         # whose summary says "N% of diff hit"

[cabinet.agent]
model = "opus"
effort = "high"
max_turns = 0                         # 0 is unbounded
may_run = []                          # command prefixes an agent may run itself
```

Every key has the default shown; a missing `[cabinet]` section means all of
them. A key that is not one of these is refused before anything is checked
out.

### The review skill

`refresh` reviews with the thermo-nuclear code quality review, which is not
part of this tome: it is Cursor's, from the
[cursor-team-kit](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review)
plugin. Put it where `review_skill` points before the first cast:

```bash
mkdir -p ~/.claude/skills/thermo-nuclear-code-quality-review
curl -fsSL -o ~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md \
  https://raw.githubusercontent.com/cursor/plugins/refs/heads/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md
```

Or point `review_skill` at any other skill file and `review_title` at the
heading its comments should open with.

### The remote

Pushes go over https with the forge CLI as the credential helper. A cast has
no terminal for ssh to ask a passphrase on, so an ssh remote is refused before
the first fetch.

```bash
# GitHub
gh auth login && gh auth setup-git
git remote set-url origin https://github.com/<owner>/<repo>.git

# GitLab, hosted or self-hosted
glab auth login --hostname gitlab.example.com
git config --global credential.helper '!glab auth git-credential'
git remote set-url origin https://gitlab.example.com/<group>/<repo>.git
```

Signed commits stay with `gpg-agent`. A cast that runs unattended cannot
type a passphrase, so either keep the key unlocked for the night or set
`sign_commits = false`, which commits with `commit.gpgsign=false`.

### What an agent may do

Unattended, every agent call runs under Claude's `dontAsk` permission mode with
an explicit allowlist, so a cast at 3am never hangs on a prompt and nothing
outside the list happens whatever the prompt says. Attended — `review` always,
the sweeps with `--attended true` — the mode is `auto`: the allowlist still
approves what it names, and what falls outside it is judged rather than
refused. Run attended casts inside a sandbox such as fence, where an approved
mistake cannot reach anything that matters.

| role       | may use                                                                     |
| ---------- | --------------------------------------------------------------------------- |
| reader     | `Read`, `Grep`, `Glob`, `git diff/log/show/status/blame`                    |
| writer     | reader + `Edit`, `Write`, `MultiEdit` + every prefix in `agent.may_run`     |
| resolver   | writer + `git add` (staging is how a conflict is reported resolved)         |

No agent commits, pushes, runs a linter or a sweep, or speaks to the forge. The
ritual does all of that itself through `shell`, and after every repair attempt
it re-runs the task the runner named as broken and hands the agent the output.
`may_run` is for the narrow, quick commands you want an agent to check itself
with — a single test, say — and the prompt quotes exactly that list.

## Claude Code plugins

The repository is also a Claude Code plugin marketplace, named `cabinet`.
Its plugins live under `plugins/`, each with its own manifest and skills.

| plugin         | what it adds                                 |
| -------------- | -------------------------------------------- |
| `issue-maker`  | a skill that files or updates a GitHub issue |
| `release-bump` | a skill that cuts a release                  |

Add the marketplace once, then install what you want:

```bash
claude plugin marketplace add fancysnake/cabinet
claude plugin install issue-maker@cabinet
```

Or from inside a session: `/plugin marketplace add fancysnake/cabinet`, then
`/plugin install issue-maker@cabinet`.

## Layout

[GLIMPSE](https://glimpse.fancysnake.dev/) layering under `src/cabinet`,
enforced by import-linter:

```text
pacts/     contracts: payloads, the Project config, the forge/scm/tasks/agent protocols
specs.py   the numbers only a rule reads
mills/     pure logic: which pull requests, what a task said, what the agent is told
links/     adapters: forge/github, forge/gitlab, scm/git, tasks/mise, agent/claude, config
gates/     the @ritual and @step bodies, reaching everything through pacts
inits/     the one place the adapters are chosen and bound
rituals/   what vekna sweeps: one module per ritual, re-exporting its steps
```

## Development

```bash
mise run test:py       # the suite
mise run lint:py       # every linter
mise run fullcheck     # the gate before a commit
vekna rituals show refresh
```
