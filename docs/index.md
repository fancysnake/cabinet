# cabinet

A cabinet is two things. It is the cupboard in the study where the tome and
the instruments are kept, and it is the body of people who do the work of
keeping a house in order. This repository is both.

**The tome** is a set of [vekna](https://vekna.fancysnake.dev) rituals for
pull request and issue maintenance, installed as a package and cast from any
repository on GitHub or GitLab, hosted or self-hosted. A pull request left open
overnight drifts: the base moves under it, CI goes red, a reviewer's questions
sit unanswered. A backlog drifts too: issues pile up untyped, unsized and
unlinked. The rituals do those chores, and each one is an ordinary program
whose loop, branches and stopping condition are code you can read. The agent
is handed one bounded piece of work at a time.

**The cabinet** is a Claude Code plugin marketplace of skills for the chores
around a repository that are not worth a ritual: filing an issue that will
still make sense in six months, cutting a release with a changelog someone can
act on. They run inside the agent session you already have open.

## The rituals

Each is named for a spell, and the school is that spell's.

- **`heal.mine`**, **`heal.this`** (Evocation): when you want to know what
  your pull requests need next.
- **`refresh`** (Transmutation): overnight, to bring your branches up to date.
- **`cover`** (Abjuration): overnight, after `refresh`, to fix coverage and
  a red suite.
- **`review`** (Divination): in the morning, to settle review threads.
- **`identify`** (Divination): when your backlog has piled up unrefined.
- **`labels`**, **`labels.pr`**, **`labels.identify`** (Conjuration): once,
  to set a project up.

[Rituals](rituals.md) has each one in full, with its flags.

## The skills

- **`issues`** — how issues are written, typed, sized and linked: files or
  updates an issue checked against the code and the open issues first, and is
  the knowledge `identify` hands its agent.
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
vekna cast labels
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
