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
review_skill = "thermo-nuclear-code-quality-review"
review_title = "Thermo-nuclear code quality review"
identify_skill = "issues:issues"
stories_skill = "lean-stories:lean-stories"

[cabinet.labels]
reviewed = "pr::thermo"               # a review was posted; take it off to ask again
wait = "pr::wait"                     # hands off this pull request
qa = "v:guide:done"                   # the guide was posted; take it off to ask again
marker = "v"                          # checkpoints: v:refresh:started, v:cover:done, ...

[cabinet.ci.jobs.checks]              # one table per CI job, keyed by a prefix of its check name
covering = false                      # red here is missing coverage

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
| `gate`          | the command that has to pass before a push; `refresh` and `review` repair until it does |
| `coverage`      | the full diff coverage measurement `cover` runs once at the end             |
| `fast_coverage` | the same measurement without the slow suites, re-run between repair rounds  |
| `sign_commits`  | `false` commits with `commit.gpgsign=false`, for casts nobody can unlock a key for |
| `review_skill`  | the skill `refresh` reviews with, by name; see [skills](#skills)           |
| `review_title`  | the heading its review comments open with                                   |
| `identify_skill`  | the skill `identify` has its agent invoke, by name; see [skills](#skills) |
| `stories_skill`   | the skill a feature issue's body is written by, in `identify` and `review`; see [skills](#skills) |

### `[cabinet.labels]`

| key        | what it is                                                                    |
| ---------- | ----------------------------------------------------------------------------- |
| `reviewed` | on means a review was posted; take it off to ask for another                  |
| `wait`     | hands off: a pull request wearing it is never taken, touched or reported on   |
| `qa`       | on means the guide was posted; take it off to ask for it again                |
| `marker`   | the prefix of every checkpoint label, `<marker>:<ritual>:started` and `:done` |

### `[cabinet.ci.jobs]`

One table per CI job the rituals may fix, keyed by a prefix of the check's
name as the forge reports it; where two keys match a check, the longer wins.
A red check no key matches is never a `ci` todo. Listing `jobs` replaces the
defaults, so a project lists every job it wants read. A job listed bare is
still read; its one key is optional:

| key        | what it is                                                                     |
| ---------- | ------------------------------------------------------------------------------ |
| `covering` | red here is missing coverage, and the check's summary may name the patch coverage, "96.84% of diff hit" |

`refresh` reads the jobs that are not `covering` to decide whether CI already
ran the gate green; `cover` reads every listed job, and the patch coverage off
the `covering` ones.

### `[cabinet.agent]`

| key           | what it is                                                                     |
| ------------- | ------------------------------------------------------------------------------ |
| `model`       | the Claude model every agent call uses                                         |
| `effort`      | `low`, `medium`, `high`, `xhigh` or `max`                                      |
| `max_turns`   | the turn limit per agent call; `0` is unbounded                                |
| `may_not_run` | slow tasks the prompt asks an agent to leave alone, beside the gate and coverage commands; see [Agents](agents.md) |

## Skills

The agents invoke three skills by name, so each resolves wherever the casting
repository's Claude finds skills: user scope (`~/.claude/skills/<name>`),
project scope (`.claude/skills/<name>`), or an installed plugin, named
`<plugin>:<skill>`. A name that resolves nowhere leaves the agent without its
rules.

| key              | default                              | where it comes from |
| ---------------- | ------------------------------------ | ------------------- |
| `review_skill`   | `thermo-nuclear-code-quality-review` | Cursor's [cursor-team-kit](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review), not this tome |
| `identify_skill` | `issues:issues`                      | the [`issues`](plugins.md#issues) plugin, from this tome's [marketplace](plugins.md) |
| `stories_skill`  | `lean-stories:lean-stories`          | the [`lean-stories`](plugins.md#lean-stories) plugin, from the same marketplace |

`identify` follows `identify_skill`. A feature issue an agent writes, an
`identify` sub-issue or an issue `review` files for a thread, gets its body
from `stories_skill`. `review_title` is the heading `review_skill`'s comments
open with; point both at another review skill to swap it.

The review skill is not a Claude plugin; copy it into user scope:

```bash
mkdir -p ~/.claude/skills/thermo-nuclear-code-quality-review
curl -fsSL -o ~/.claude/skills/thermo-nuclear-code-quality-review/SKILL.md \
  https://raw.githubusercontent.com/cursor/plugins/refs/heads/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review/SKILL.md
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
