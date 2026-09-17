# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

## [0.1.0] - 2026-09-17

### Added

- Three rituals, cast through `[rituals] modules = ["cabinet.rituals"]`:
  `refresh` (Transmutation) merges the base into every open pull request,
  makes the gate green, pushes and posts a quality review; `cover`
  (Abjuration) measures diff coverage where CI is unhappy and writes the
  missing tests; `review` (Divination) triages the review threads with you
  at the terminal, answers them, and ships the branch.
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
- `labels` (Conjuration) creates or refreshes every label the rituals use on
  either forge.
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
[unreleased]: https://github.com/fancysnake/cabinet/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/fancysnake/cabinet/releases/tag/v0.1.0
