# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

## [8.1.0] - 2026-11-28

### Changed

- The `heal.*` rituals and `merge` merge the base into every branch that is
  behind it, not only into a branch that conflicts, then run the gate and
  push; `heal.mine` queues a `heal.pr` for every such branch.

- The `heal.*` rituals fast-forward your local base branch, with no checkout,
  when they take a branch or `heal.main` cuts its fix branch; a base that a
  worktree stands on, or that has commits of its own, is left as it is.

### Fixed

- The `heal.*` rituals take a branch that two remotes hold, from the one on
  `[cabinet] remote`, where git refused to choose and the branch was blocked.

- The triage card of `answer` shows the command the reading ran on a line of
  its own, never wrapped, so it can be copied from the card.

- The `heal.*` rituals read every page of a branch's checks, so `heal.main`
  and the survey see a red check past the first hundred.

## [8.0.0] - 2026-11-25

### Added

- `answer` takes `ok` as it takes the return key: at a triage card for the
  reading's proposal, at a drafted reply to post it. Discord, where vekna
  3.1.0 can ask, sends no empty reply.

### Changed

- **Breaking:** the `heal.*` rituals and `identify` need the `heal` plugin
  installed for the agent: `claude plugin install heal@cabinet`. Their prompts
  name its skills (`heal:resolve-conflict`, `heal:fix-gate`,
  `heal:cover-diff`, `heal:untrusted-threads`). A cast without the plugin
  stops at the first agent call and names the missing skill.
- **Breaking:** cabinet needs vekna 3.0.0 or later. vekna 3 reads the
  repository's `.vekna.toml` ahead of your `[projects.<name>.cabinet]` table.
  A key set in both takes the repository's value: remove the duplicate from
  the one you want to lose.
- `heal.mine` ends without waiting for the `heal.pr` casts it queued, so it
  holds no place on the daemon while they run. It reports which cast took
  which branch; each `heal.pr` reports its own branch. `vekna cast heal.mine`
  typed at a terminal still follows them and exits `1` where one failed. The
  `heal.mine` result lists the casts in `queued` and no `checked` rows.
- Every prompt names the long tasks the agent leaves to the ritual. The
  triage, redraft, review, guide and `identify` prompts did not.
- The `heal:untrusted-threads` skill covers what the agent fetches itself.
- A heal cast's step budget is 1,003 steps, down from 1,004.

### Fixed

- A `heal.*` cast fails when it cannot check out a branch, for example one
  that another worktree stands on. It reported the branch as left alone and
  ended green. The report heading counts only the branches the cast worked.

## [7.3.0] - 2026-11-22

### Added

- cabinet accepts vekna 3.x as well as 1.3.0 and later. Under vekna 3 a
  `vekna cast heal.mine` typed at a terminal heals its pull requests one at a
  time; `vekna cast --queue heal.mine` heals them side by side.
- `bots` in `[cabinet]` names more logins whose review threads `answer`
  resolves after it replies, beside yours and the ones a GitHub app opened.
- `approve_replies = true` in `[cabinet]` puts each drafted reply to you
  before `answer` posts it. Press return to post it, or say what to change
  and the agent redrafts it.

### Changed

- `answer` no longer resolves a review thread another person opened. It
  replies and leaves the thread open for them, and the thread makes an answer
  todo again only when they write under the reply.
- A `heal.*` cast surveys a branch again when its tasks run out and works
  what it finds, until a survey finds nothing new. An attended cast answers
  the review it posted, and a branch with nothing else left gets its guide. A
  task already worked on the branch in this cast is not worked again.
- A reply to a review thread is written for the comment's author. It no
  longer mentions what the operator said at the triage or what the agent
  could not run or verify.
- The review task runs before the answer task, so one triage takes the
  review's comments with the threads already open.

## [7.2.0] - 2026-11-20

### Added

- cabinet accepts vekna 2.x as well as 1.3.0 and later.

### Changed

- A heal cast's step budget is 1,004 steps, down from 8,303: sized for
  `heal.mine` queuing the thousand pull requests GitHub lists. A branch whose
  `--bound` and CI jobs do not fit is reported as
  `out of steps at this --bound and CI jobs, not reached`. GitLab's merge
  request listing stops at a thousand, as GitHub's does, and the report says
  when it is cut short.

## [7.1.0] - 2026-11-19

### Changed

- The `smoke-test` skill answers a change no user meets (dead code removed,
  a rename, docs, tests, CI config) with one line saying no manual check is
  needed, and never writes a step for what CI runs.
- The triage card of `answer` has two titled halves, the thread and what the
  reading would do, and wraps long values under their label at 80 columns.
  The second title names the action a return key takes.

### Fixed

- `answer` picks up a review item that the review posted as a plain comment
  because the forge refused its line. The comment counts as an open thread
  until a reply of yours links to it.

## [7.0.0] - 2026-11-19

### Changed

- `heal.mine` stays until every `heal.pr` it queued has ended and reports
  their rows as its own, the way `heal.this` does. A `heal.pr` that failed
  blocks its branch, and a blocked branch fails `heal.mine`. A `heal.pr` that
  did not reach its branch leaves it in `not_reached`.
- vekna 1.3.0 is the lowest supported.

### Removed

- `queued` from the `heal.mine` result.

## [6.0.0] - 2026-11-18

### Added

- A `fix` call escalates to `[cabinet.agent.models] escalated`, default
  `opus`, when the merge left 5 or more files conflicted, 3 or more checks
  are red, 10 or more review threads are open, or the step is retrying.
- The `heal` plugin: the heal rituals' rules as four skills for work done by
  hand, `resolve-conflict`, `fix-gate`, `cover-diff` and `untrusted-threads`.
  Install with `claude plugin install heal@cabinet`.
- `[cabinet]` is read from the vekna user config as well as `.vekna.toml`,
  merged key by key. A repository with no `.vekna.toml` casts the rituals
  from the user config alone.

### Changed

- A ritual checks only the `[cabinet]` keys it reads. A misspelled key is
  still refused by every ritual, and a refused value names the tables that
  set `[cabinet]`.
- `answer` puts each triaged thread to you as one card, most urgent first:
  the thread and who raised it, what it asks, what happens if it is left, the
  proposed action, how the reading knows, and what the action costs. The
  tally of priorities is gone.
- vekna 1.2.0 is the lowest supported.

### Removed

- **Breaking:** the `--attended` flag; `vekna cast --unattended` is the one
  switch. vekna refuses to cast a ritual while `.vekna.toml` sets `attended`
  under `[defaults."cabinet:<ritual>"]`: remove the key, and pass
  `--unattended` where nobody is there to answer.

## [5.1.0] - 2026-11-13

### Added

- `heal.main`: where a configured CI job is red on the base and no fix of
  yours is open, it cuts a branch from the base, fixes each red job as `ci`
  does, pushes, and opens a pull request. It never pushes to the base.
- `[cabinet] main_fix_branch`, default `fix/main-{sha}`: the branch
  `heal.main` works on. It must hold `{sha}`, the base's head commit, once.

### Changed

- A cast that leaves a branch blocked fails, once the other branches are
  worked and the report is printed.
- An attended cast no longer asks before a repair attempt; the review threads
  of the answer task are the only question a cast asks.

### Fixed

- A gate, coverage or CI job task shows its lines in the vekna window while it
  runs, so a hung task shows where it stopped.
- A forge call refused for a rate limit waits and tries again for about 15
  minutes before it fails the cast.
  ([#132](https://github.com/fancysnake/cabinet/issues/132))

## [5.0.0] - 2026-11-08

### Added

- `heal.mine` and `heal.this` act: after the survey they merge a conflicting
  branch, post the quality review, push what they committed and report each
  branch. Both take `--bound` and `--attended`.
- `heal.pr --number N`: one pull request of yours, healed in a worktree from
  vekna's pool.
- `ci`: the red CI jobs in `[cabinet.ci.jobs]`, rerun once where `rerun` is
  set, otherwise fixed from the job's log against its `gate` or covered with
  tests where it is `covering`, one commit per job and one fixed check per
  job per cast. `heal.mine` and `heal.this` work it on a branch they did not
  merge, and leave it to the next cast where they did.
- `[cabinet.ci.jobs.<prefix>]` takes `rerun`, `gate` and `fast`.
- `answer`: the review threads on your branch, attended only. An agent
  triages them, you decide each item, another agent fixes what you said to
  fix, and the ritual files the issues, posts the replies, settles the
  threads and commits the fixes once the gate is green. `heal.pr` and
  `heal.this` work it after ci when attended; an unattended cast reports how
  many threads wait for you. `--batch` sets how many threads one round
  takes, three rounds a cast. A branch it leaves with no thread open wears
  `[cabinet.labels] answered`, default `v:answer:done`.
- `merge` and `review`: `heal.this` with that one task, on the branch at the
  cwd.
- `guide`: once a branch has nothing else to do, an agent writes its manual
  smoke test, and the ritual posts it as a plain comment and puts
  `[cabinet.labels] qa` on. Taking the label off asks again, and the comment
  is edited in place. `heal.pr` and `heal.this` work it last.
- `[cabinet] smoke_skill`, default `~/.claude/skills/smoke-test/SKILL.md`: the
  skill the guide is written with.
- `labels.heal` makes the reviewed, wait, qa and answered labels.
- `[defaults."cabinet:<ritual>"]` in `.vekna.toml` sets a ritual's flags per
  repository, `attended = false` among them.
- Each release carries its sdist and wheel, and its notes are the changelog
  section.
- `release-bump` plugin: where a workflow publishes the release on a tag push,
  the report names pushing the tag as the last step.

### Changed

- **Breaking:** casts are attended by default. `--attended false`, or vekna's
  own `vekna cast --unattended`, turns a cast down, and `--unattended` wins
  over `--attended true`. A cron job that never passed `--unattended` runs its
  agents in `auto` mode and asks before each repair; add the flag.
  ([#109](https://github.com/fancysnake/cabinet/issues/109))
- **Breaking:** `heal.mine` queues a `heal.pr` on the vekna daemon for each
  pull request with work, and the branches heal side by side, each in a
  pooled worktree. Your own checkout never moves. With no daemon it prints
  the survey and fails. A verdict a gate gave up on is no longer carried from
  one pull request to the next.
- **Breaking:** a merge happens only where the branch conflicts with its base;
  a branch that is merely behind is left alone.
- **Breaking:** `review` posts the quality review on your branch; `answer`
  answers review threads.
- The heal rituals fetch the remote and read the base as the remote has it,
  without checking it out or updating your local base branch.
- cabinet accepts vekna 1.x, and requires 0.15 or later.
- `mkdocs-site` plugin: the site it sets up gets an `overrides/main.html` head
  with Open Graph and JSON-LD tags, a description on every page, `robots.txt`
  on a root-hosted site, and a check of the built head.
  `theme.custom_dir: overrides` is always set (an existing site without it
  gets it), and the site workflow's `paths:` filter includes `overrides/**`.
  Pages make no claim the code does not back, and a diagram gets alt text and
  is checked against the code it names.

### Removed

- **Breaking:** `[cabinet.agent] model`. Each agent call names its job, and
  `[cabinet.agent.models]` sets a model per job: `plan`, `build` and `review`
  default to `opus`, `fix` and `doc` to `sonnet`. A `.vekna.toml` that sets
  `model` is refused. Repairs, conflict resolution, review-thread fixes and
  replies, and the smoke-test guide run on `sonnet`; triaging review threads
  runs on `opus`, unless you set otherwise.
  ([#82](https://github.com/fancysnake/cabinet/issues/82))
- **Breaking:** `refresh` and `cover`; `heal.mine` replaces `refresh`, and
  the `ci` task's `covering` jobs replace `cover`.
- **Breaking:** `labels.pr`, replaced by `labels.heal`.
- **Breaking:** the `started`/`done` checkpoint labels and
  `[cabinet.labels] marker`. A `.vekna.toml` that sets `marker` is refused.
- `issues` plugin: filing an issue no longer asks for a priority or sets
  `backlog`, a priority label, or issue or Project fields; it sets only the
  type, size and links.
  ([#116](https://github.com/fancysnake/cabinet/issues/116))

### Fixed

- A rate-limited `gh` or `glab` call waits and tries again, doubling the pause
  from 15 seconds, so a short spell of limiting no longer costs a cast. Still
  limited after about 15 minutes, the cast fails saying so. Anchored review
  comments stay anchored through a limit, and a limited GitLab label is no
  longer taken for a duplicate.
  ([#132](https://github.com/fancysnake/cabinet/issues/132))
- The heal rituals see every open pull request of yours, not the first
  hundred: GitLab's listing is paged to the end, and GitHub's goes to the
  thousand its search returns. A listing cut short says so in the report.
  ([#127](https://github.com/fancysnake/cabinet/issues/127))

### Security

- On GitLab, a line opening with `/` in a note, reply or issue description
  cabinet posts is escaped, so agent text cannot run a quick action such as
  `/close`.

## [4.0.0] - 2026-10-24

### Added

- `modern-python` plugin: writes Python with the newest idioms the project's
  minimum Python version allows, 3.11 to 3.15, and avoids the APIs it removed.
- `heal.mine` and `heal.this`, cast with `--plan-only true`, print what each
  pull request needs next and change nothing: merge, ci, answer, review or
  guide.
- `[cabinet.labels] qa`, default `v:guide:done`, marks a pull request that
  needs no guide.

### Changed

- **Breaking:** `[cabinet.ci]` lists jobs as `[cabinet.ci.jobs.<prefix>]`
  tables with an optional `covering` key, replacing `gate_checks`,
  `cover_checks` and `patch_check`. `refresh` reads the jobs that are not
  `covering`; `cover` reads every job, and the patch coverage off the
  `covering` ones.
- cabinet runs on Python 3.11 to 3.15 and requires vekna 0.14.
- `issues` skill: an issue body is a STAGE (Status, Target, Assets, Guards,
  Ellipsis) when it ships on its own, or a Slice (a STAGE cut down to its
  Target) when it does not, never a plan.

### Removed

- **Breaking:** the `spike` issue type; type an investigation by what it
  explores: `feature`, `edit`, `chore` or `bug`. `labels.identify` leaves an
  existing `spike` label in place and creates none; `identify` types an issue
  wearing only `spike` again.

### Fixed

- `review` finishes a cut-short round only from marks you wrote: a thread
  whose last reply someone else marked is read again, and an issue only
  assigned to you no longer counts as filed for a thread.

## [3.0.0] - 2026-10-09

### Changed

- **Breaking:** `labels:pr` and `labels:identify` are renamed `labels.pr` and
  `labels.identify`, and cabinet requires vekna 0.13, which reserves `:` for a
  tome's namespace.
- **Breaking:** `review`'s result lists the branches it did not take under
  `left`, replacing `not_polled`.
- `release-bump` writes the new version everywhere the old one stood, mirrors
  and lockfile included, and bumps each versioned plugin that changed.
- `release-bump` documents what the release added and updates every skill,
  agent and command in the repository.

### Fixed

- `refresh`, `cover` and `review` stop before their step budget runs out and
  leave the remaining branches for the next cast, keeping the report; `review`
  gives each branch one round per batch. The sweep budget fits a hundred
  branches at the default `--bound`.
- `review` finishes a round an earlier cast's forge failure cut short instead
  of reading its threads again: an answered thread is settled, and one with an
  issue filed gets the reply naming it, not a second issue. A forge that will
  not list every open issue ends the cast.
- `cover`, `refresh` and `review` read every review thread and every comment on
  it, past the first page.

## [2.0.0] - 2026-10-03

### Changed

- Every agent role has a shell with no command denied; run every cast in a
  sandbox.
- **Breaking:** `agent.may_not_run` replaces `agent.may_run` and names slow
  tasks the prompt asks an agent to leave alone; a `.vekna.toml` still setting
  `may_run` is refused.

## [1.0.1] - 2026-10-03

### Changed

- `identify` takes each page unasked.

### Fixed

- `identify` reports a write the forge refuses under its issue and goes on;
  only a page on which the forge refused every write stops the cast.
- `identify` leaves a sub-issue or blocker link that already exists alone
  instead of having the forge refuse the duplicate.

## [1.0.0] - 2026-10-02

### Added

- `identify` ritual: your open issues that lack a type or a size, a page of
  `--batch` at a time, each page asked about first. One agent session per cast
  says what each is — a type and a size, or an epic with the sub-issues to
  split it into, plus what is part of it and what blocks it — following the
  skill at the `identify_skill` setting; the ritual puts that
  on the forge. The report says when the forge would not list your whole
  backlog.
- `labels:identify` ritual: makes the `feature`, `edit`, `chore`, `spike`,
  `bug`, `S`, `M`, `L` and `epic` labels `identify` uses.
- `labels:pr` ritual: makes the pull request rituals' labels alone.
- `issues` plugin: a skill for how issues are written, typed, sized and
  linked, which `identify` hands its agent.

### Changed

- `labels` makes every label cabinet uses, the issue labels as well as the
  pull request ones.

### Removed

- `issue-maker` plugin, folded into `issues`.

## [0.5.0] - 2026-09-29

### Added

- `smoke-test` plugin: a skill that writes the fifteen-minute manual check
  for a change where users meet it (staging, a production preview or the
  installed CLI), plus the untouched features it could have broken.

### Changed

- Requires vekna 0.10; `vekna rituals show` draws each ritual's graph from
  the exits every step declares.
- `review` ends with the rows it reviewed rather than the payload it carried
  between branches, and a stopped review raises `RitualError`.

## [0.4.0] - 2026-09-27

### Added

- `mkdocs-site` plugin: a skill that sets up a MkDocs Material site, or
  brings an existing `mkdocs.yml`, its tasks and its Pages workflow up to one
  standard.
- The manual carries this changelog at
  [cabinet.fancysnake.dev/changelog](https://cabinet.fancysnake.dev/changelog/).

### Changed

- The pre-commit hook, `hk.pkl`, targets hk 2.

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
[unreleased]: https://github.com/fancysnake/cabinet/compare/v8.1.0...HEAD
[8.1.0]: https://github.com/fancysnake/cabinet/compare/v8.0.0...v8.1.0
[8.0.0]: https://github.com/fancysnake/cabinet/compare/v7.3.0...v8.0.0
[7.3.0]: https://github.com/fancysnake/cabinet/compare/v7.2.0...v7.3.0
[7.2.0]: https://github.com/fancysnake/cabinet/compare/v7.1.0...v7.2.0
[7.1.0]: https://github.com/fancysnake/cabinet/compare/v7.0.0...v7.1.0
[7.0.0]: https://github.com/fancysnake/cabinet/compare/v6.0.0...v7.0.0
[6.0.0]: https://github.com/fancysnake/cabinet/compare/v5.1.0...v6.0.0
[5.1.0]: https://github.com/fancysnake/cabinet/compare/v5.0.0...v5.1.0
[5.0.0]: https://github.com/fancysnake/cabinet/compare/v4.0.0...v5.0.0
[4.0.0]: https://github.com/fancysnake/cabinet/compare/v3.0.0...v4.0.0
[3.0.0]: https://github.com/fancysnake/cabinet/compare/v2.0.0...v3.0.0
[2.0.0]: https://github.com/fancysnake/cabinet/compare/v1.0.1...v2.0.0
[1.0.1]: https://github.com/fancysnake/cabinet/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/fancysnake/cabinet/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/fancysnake/cabinet/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/fancysnake/cabinet/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/fancysnake/cabinet/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/fancysnake/cabinet/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fancysnake/cabinet/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fancysnake/cabinet/releases/tag/v0.1.0
