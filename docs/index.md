# cabinet

A cabinet is two things. It is the cupboard in the study where the tome and
the instruments are kept, and it is the body of people who do the work of
keeping a house in order. This repository is both.

**The tome** is a set of [vekna](https://vekna.fancysnake.dev) rituals for
pull request maintenance, installed as a package and cast from any repository
on GitHub or GitLab, hosted or self-hosted. A pull request left open overnight
drifts: the base moves under it, CI goes red, a reviewer's questions sit
unanswered. The rituals do those chores, and each one is an ordinary program
whose loop, branches and stopping condition are code you can read. The agent
is handed one bounded piece of work at a time.

**The cabinet** is a Claude Code plugin marketplace of skills for the chores
around a repository that are not worth a ritual: filing an issue that will
still make sense in six months, cutting a release with a changelog someone can
act on. They run inside the agent session you already have open.

## The rituals

Grouped by school, the way a spellbook is.

- **`refresh`** (Transmutation) — the night's fast pass. Every open pull
  request of yours gets the base branch merged in, conflicts resolved, the
  gate made green, the work pushed and a quality review posted.
- **`cover`** (Abjuration) — the night's slow pass. Where CI says the coverage
  or the suite is unhappy, it measures, writes the tests for what the branch
  left uncovered, repairs a red suite, and pushes.
- **`review`** (Divination) — the morning after. Reads the review threads the
  night left, triages them with you at the terminal, answers every one, makes
  the gate green and ships the branch.
- **`refine`** (Divination) — your open issues, a page at a time: each gets a
  type and a size, one too big becomes an epic with sub-issues, related ones
  get linked.
- **`labels:pr`** and **`labels:issue`** (Conjuration) — make the labels the
  pull request rituals and `refine` wear. Cast each once before first use.

[Rituals](rituals.md) has each one in full, with its flags.

## The skills

- **`issues`** — how issues are written, typed, sized and linked: files or
  updates an issue checked against the code and the open issues first, and is
  the knowledge `refine` hands its agent.
- **`release-bump`** — cuts a release: the version by semver from what
  changed since the last tag, the changelog compacted, the docs and skills
  brought in line. Commits and tags nothing unless asked.
- **`mkdocs-site`** — sets a repository's manual up on MkDocs Material, or
  brings one that drifted back to the standard: the config, the palette, the
  pages, the dependency, the tasks and the Pages workflow.

[Plugins](plugins.md) has what each does, step by step.

## Install

### The tome

cabinet is not on PyPI; it is installed straight from the repository, into the
repository that wants the rituals:

```bash
poetry add --group dev git+https://github.com/fancysnake/cabinet.git#<tag-or-sha>
```

Then a `.vekna.toml` names the rituals and tells them what the repository is:

--8<-- "README.md:vekna-toml"

Every `[cabinet]` key has a default; [Configuration](configuration.md) lists
them all. With that in place:

```bash
vekna cast labels:pr
vekna cast refresh
```

### The cabinet

The skills come from the marketplace in this repository; [Plugins](plugins.md)
has the two commands that add it and install a skill, and what each one does.

## Where to go next

- [Rituals](rituals.md) — what each one does, its flags, and loading only some
  of them.
- [Configuration](configuration.md) — the `[cabinet]` section, the review
  skill, and the remote.
- [Agents](agents.md) — what an agent may and may not do during a cast. Worth
  reading before the first unattended one.
- [Plugins](plugins.md) — the skills, what triggers each, and what it needs.
- [Architecture](architecture.md) — the layout, for anyone sending a patch.
- [Changelog](changelog.md) — what each release changed.
