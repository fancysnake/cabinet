---
name: release-bump
description: >-
  Cut a release: bump the version by semver from what changed since the last
  tag, rewrite the Unreleased changelog section into tight entries, and bring
  docs and skills in line with the code. Use whenever the user asks to bump,
  release, tag, cut a version, or update the changelog.
---

# Release bump skill

Reads the diff since the last release, decides the version, writes the
changelog, fixes the docs. Commits nothing and tags nothing unless asked.

## 1. Find the last release

- Last tag: `git describe --tags --abbrev=0`. No tag → every commit counts:
  the log range is `HEAD` and the diff is against the empty tree,
  `git diff $(git hash-object -t tree /dev/null) HEAD`.
- The unit of release is one manifest: the one the request names, else the
  repo root's (`pyproject.toml`, `package.json`, `Cargo.toml`, …). Its
  version files are that manifest plus whatever mirrors its version (an
  `__init__.py`, a `version.py`); all of them get the new version. Nothing
  else changes: a plugin or package elsewhere in the repo is its own
  release, and `CHANGELOG.md` is touched only in step 4.
- Changelog: `CHANGELOG.md` in [Keep a Changelog] form. No changelog →
  say so and stop; do not invent one.

## 2. Read what changed

`git log <tag>..HEAD` and `git diff <tag>..HEAD --stat` (the no-tag range
from step 1 otherwise), then the diff of anything the log leaves unclear.
Sort every change into one of:

| bucket | what it is |
| --- | --- |
| **break** | a caller, config key, CLI flag, or output format that worked before and does not now |
| **feature** | something a user can do or see that they could not |
| **fix** | behaviour that was wrong and is now right |
| **internal** | refactor, tests, CI, tooling, docs; a user notices nothing |

A change that touches only `Unreleased` already has an entry; check it
against the diff, it is often stale.

## 3. Choose the version

[Semantic Versioning], strictly:

- any **break** → major (`X+1.0.0`)
- else any **feature** → minor (`X.Y+1.0`)
- else any **fix** → patch (`X.Y.Z+1`)
- only **internal** → patch, or ask whether a release is wanted at all

State the bump and its reason in one line before editing anything:
`0.1.0 → 0.2.0: labels ritual is a new capability`. A break the diff hides
(a renamed config key, a dropped default) is worth a second look at the diff,
not a guess.

## 4. Write the changelog

Move `## [Unreleased]` into `## [<version>] - <today>` and leave an empty
`## [Unreleased]` above it. Sections in this order, only those with content:
`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`. Update the
link block at the bottom: `[unreleased]` compares the new tag to `HEAD`,
the new version gets its own compare or release link, matching the existing
ones.

Then compact every entry. Rules are deletions only; the worst case is an
entry unchanged.

- Delete entries for **internal** changes unless the repo lists tooling in
  its changelog already.
- Merge entries that describe one feature from two commits into one.
- Delete the mechanism when the entry already names the effect
  (`refuses ssh remotes before the first fetch`, not how it inspects the
  URL).
- Delete words that survive substitution: if swapping the noun keeps the
  sentence true, the noun was decoration.
- Delete `now`, `new`, `support for`, `the ability to`, `in order to`,
  `various`, `improved` without what improved.
- Delete puffery: robust, seamless, comprehensive, powerful, enhanced.
- Delete restatement: an entry whose next entry says the same thing.
- Keep the concrete handle the user will grep for: the flag, the config key,
  the command, the ritual name, in backticks.

Each entry is one sentence in active voice, positive form, past or present
tense as the file already uses, ending on the word that matters. A reader
who missed the release should know what to change in their setup.

## 5. Bring docs and skills in line

For every **break**, **feature** and user-facing **fix**, check that the
prose still matches:

- `README.md` and any `docs/`: commands, flags, config keys, defaults,
  tables of what exists.
- Skill files (`SKILL.md`, anything under `skills/`, `.claude/`,
  `plugins/`): a step that names a command, path, or option the release
  changed.
- Help text and docstrings the diff left behind.

Edit what is wrong. Add nothing the release did not add. A doc gap that
predates this release is a line in the report, not an edit.

## 6. Report

One line per file touched, the version line from step 3, and any change
you could not classify with the question it raises. Leave staging, commit
and tag to the user unless the request said otherwise.

[keep a changelog]: https://keepachangelog.com/en/1.1.0/
[semantic versioning]: https://semver.org/spec/v2.0.0.html
