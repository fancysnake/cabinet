# Configuration

The rituals read the `[cabinet]` section of the casting repository's
`.vekna.toml`. Every key has the default shown; a missing `[cabinet]` section
means all of them. A key that is not one of these is refused before anything
is checked out, so a misspelled key dies at the boundary. The values are not
checked against anything: a task name that does not exist fails when the
ritual runs it.

```toml
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
identify_skill = "~/.claude/skills/issues/SKILL.md"

[cabinet.labels]
reviewed = "pr::thermo"               # a review was posted; take it off to ask again
wait = "pr::wait"                     # hands off this pull request
qa = "v:guide:done"                   # the guide was posted; take it off to ask again
answered = "v:answer:done"            # the answer task left no review thread open

[cabinet.ci.jobs.checks]              # one table per CI job, keyed by a prefix of its check name
covering = false                      # red here is missing coverage
rerun = false                         # run it again once before fixing it
gate = ""                             # the command that reproduces it here; "" is none
fast = ""                             # re-run between repair rounds; "" is gate

[cabinet.ci.jobs.test]

[cabinet.ci.jobs."codecov/patch"]
covering = true

[cabinet.agent]
model = "opus"
effort = "high"
max_turns = 0                         # 0 is unbounded
may_not_run = []                      # slow tasks the prompt asks an agent to leave alone
```

## The keys

| key             | what it is                                                                  |
| --------------- | --------------------------------------------------------------------------- |
| `forge`         | `github` through `gh`, or `gitlab` through `glab`, hosted or self-hosted    |
| `base`          | the branch every pull request is merged from                                |
| `remote`        | pushed to and fetched from by name; must be https, see [the remote](#the-remote) |
| `gate`          | the command a merge has to pass before it is committed; the merge task repairs until it does |
| `coverage`      | the full diff coverage measurement a `covering` job runs, named to agents as a task to leave alone |
| `fast_coverage` | the same measurement without the slow suites, re-run between repair rounds  |
| `sign_commits`  | `false` commits with `commit.gpgsign=false`, for casts nobody can unlock a key for |
| `review_skill`  | the skill file the review task reviews with; see [the review skill](#the-review-skill) |
| `review_title`  | the heading its review comments open with                                   |
| `identify_skill`  | the skill file `identify` has its agent read; see [the issues skill](#the-issues-skill) |

### `[cabinet.labels]`

| key        | what it is                                                                    |
| ---------- | ----------------------------------------------------------------------------- |
| `reviewed` | on means a review was posted; take it off to ask for another                  |
| `wait`     | hands off: a pull request wearing it is never taken, touched or reported on   |
| `qa`       | on means the guide was posted; take it off to ask for it again                |
| `answered` | on means the answer task left no review thread open; it comes off when an answer task starts |

### `[cabinet.ci.jobs]`

One table per CI job the rituals may fix, keyed by a prefix of the check's
name as the forge reports it; where two keys match a check, the longer wins.
A red check no key matches is never a `ci` todo. Listing `jobs` replaces the
defaults, so a project lists every job it wants read. A job listed bare is
still read; every key is optional:

| key        | what it is                                                                     |
| ---------- | ------------------------------------------------------------------------------ |
| `covering` | red here is missing coverage, and the check's summary may name the patch coverage, "96.84% of diff hit" |
| `rerun`    | the job may be a flake: run it again, once per head, before anything is fixed |
| `gate`     | the command that reproduces the job here; the agent's fix is repaired until it passes |
| `fast`     | the narrower command re-run between repair rounds; empty runs `gate`           |

A red check on a listed job makes a `ci` todo in the survey, and so does a
green `covering` check whose summary names less than 100% of the diff. The
[ci](rituals.md#ci) task then fixes it:

- With `rerun`, the job runs again first, and the task ends for the next cast
  to read the result.
- With a `gate`, an agent reads the end of the job's log and fixes it, then
  the gate runs and is repaired until it passes, `fast` between rounds.
- Without a `gate`, the agent makes one attempt from the log and the ritual
  commits it. The next CI run checks it.
- With `covering`, coverage is measured here with `gate` and `fast`, or
  `coverage` and `fast_coverage` where they are empty, and the agent writes
  tests for the lines the report names.

A check some other app posts, such as Codecov's, has no job to rerun or log
to read: give it `covering`, not `rerun`.

### `[cabinet.agent]`

| key           | what it is                                                                     |
| ------------- | ------------------------------------------------------------------------------ |
| `model`       | the Claude model every agent call uses                                         |
| `effort`      | `low`, `medium`, `high`, `xhigh` or `max`                                      |
| `max_turns`   | the turn limit per agent call; `0` is unbounded                                |
| `may_not_run` | slow tasks the prompt asks an agent to leave alone, beside the gate and coverage commands; see [Agents](agents.md) |

## The review skill

The review task uses the thermo-nuclear code quality review, which is not
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

## The issues skill

`identify` has its agent read the `issues` skill, which lives in this
repository's [plugins](plugins.md). Put a copy where `identify_skill` points
before the first cast:

```bash
mkdir -p ~/.claude/skills/issues
curl -fsSL -o ~/.claude/skills/issues/SKILL.md \
  https://raw.githubusercontent.com/fancysnake/cabinet/refs/heads/main/plugins/issues/skills/issues/SKILL.md
```

Or point `identify_skill` at the copy the plugin install left, or at a skill of
your own that names the same labels. A repository that already carries the
skill in its own tree can name that path instead, which is what this one does:

```toml
[cabinet]
identify_skill = "plugins/issues/skills/issues/SKILL.md"
```

## The remote

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

A repository that wants to keep its ssh `origin` adds a second remote for the
rituals and names it in `remote`: both point at the same repository, so this
is a route and not a destination.

Signed commits stay with `gpg-agent`. A cast that runs unattended cannot type
a passphrase, so either keep the key unlocked for the night or set
`sign_commits = false`.
