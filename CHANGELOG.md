# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

### Added

- The `mkdocs-site` plugin: a skill that sets up a MkDocs Material site or
  brings an existing `mkdocs.yml`, its tasks and its Pages workflow up to one
  standard.

## [0.3.1] - 2026-09-20

### Added

- The manual at [cabinet.fancysnake.dev](https://cabinet.fancysnake.dev),
  served locally by `mise run site:dev`.

## [0.3.0] - 2026-09-19

### Changed

- Runs on Python 3.11 through 3.14; 3.14 alone was required before.

## [0.2.0] - 2026-09-18

### Added

- The repository is a Claude Code plugin marketplace, `cabinet`: add it with
  `claude plugin marketplace add fancysnake/cabinet`. Plugins live under
  `plugins/` as skills only and carry no version; an install tracks the
  marketplace commit.
- `issue-maker` plugin: a skill that files or updates a GitHub issue, checking
  the task against the code and hunting duplicates first.
- `release-bump` plugin: a skill that cuts a release, bumping the version by
  semver from the changes since the last tag and compacting the changelog.

## [0.1.0] - 2026-09-17

### Added

- Four rituals, cast through `[rituals] modules = ["cabinet.rituals"]`:
  `refresh` (Transmutation) merges the base into every open pull request,
  makes the gate green, pushes and posts a quality review; `cover`
  (Abjuration) measures diff coverage where CI is unhappy and writes the
  missing tests; `review` (Divination) triages the review threads with you
  at the terminal, answers them, and ships the branch; `labels`
  (Conjuration) creates or refreshes every label the others use. `--batch N`
  on `review` reads, answers and settles the threads in rounds of N (default
  7), and the gate runs once after the last round.
- A `[cabinet]` section in the consuming repository's `.vekna.toml` for
  everything that used to be a constant: the gate and coverage tasks, base
  branch, remote, labels, CI check names, review skill, agent model, effort,
  turn limit and the commands an agent may run.
- GitHub through `gh` and GitLab (hosted or self-hosted) through `glab`,
  behind one forge protocol.
- Agents run under Claude's `dontAsk` permission mode with per-role
  allowlists (reader, writer, resolver). Every forge write, commit, push and
  task run is the ritual's, through `shell`.
- `--attended true` on `refresh` and `cover`: the sweep asks before every
  repair attempt and its agents run in `auto` permission mode; `review` is
  always attended.
- One facade per ritual under `cabinet.rituals`, so a project loads only the
  rituals it can run.
- Pushes go over https with the forge CLI as the credential helper; an ssh
  remote is refused before the first fetch. `sign_commits = false` commits
  with `commit.gpgsign=false` for casts that run unattended.
- GLIMPSE layering under `src/cabinet`, enforced by import-linter, with a
  `trial` test suite over every step and adapter.
- Tooling: mise tasks from shared-configs, hk as the pre-commit hook, a CI
  workflow with Codecov upload, tingle for the debt budget.

<!-- Links -->
[keep a changelog]: https://keepachangelog.com/en/1.0.0/
[semantic versioning]: https://semver.org/spec/v2.0.0.html

<!-- Versions -->
[unreleased]: https://github.com/fancysnake/cabinet/compare/v0.3.1...HEAD
[0.3.1]: https://github.com/fancysnake/cabinet/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/fancysnake/cabinet/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fancysnake/cabinet/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fancysnake/cabinet/releases/tag/v0.1.0
