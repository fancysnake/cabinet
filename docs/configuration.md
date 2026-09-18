# Configuration

The rituals read the `[cabinet]` section of the casting repository's
`.vekna.toml`. Every key has the default shown; a missing `[cabinet]` section
means all of them. A key that is not one of these is refused before anything
is checked out, so a typo in a task name dies at the boundary.

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
| `review_skill`  | the skill file `refresh` reviews with; see [the review skill](#the-review-skill) |
| `review_title`  | the heading its review comments open with                                   |

### `[cabinet.labels]`

| key        | what it is                                                                    |
| ---------- | ----------------------------------------------------------------------------- |
| `reviewed` | on means a review was posted; take it off to ask for another                  |
| `wait`     | hands off: a pull request wearing it is never taken, touched or reported on   |
| `marker`   | the prefix of every checkpoint label, `<marker>:<ritual>:started` and `:done` |

### `[cabinet.ci]`

Prefixes, matched against the check's name as the forge reports it.

| key            | what it is                                                          |
| -------------- | ------------------------------------------------------------------- |
| `gate_checks`  | red here means the gate is worth running                            |
| `cover_checks` | red here means the coverage pass is worth its hour                  |
| `patch_check`  | the check whose summary names the patch coverage, "96.84% of diff hit" |

### `[cabinet.agent]`

| key         | what it is                                                                     |
| ----------- | ------------------------------------------------------------------------------ |
| `model`     | the Claude model every agent call uses                                         |
| `effort`    | `low`, `medium`, `high`, `xhigh` or `max`                                      |
| `max_turns` | the turn limit per agent call; `0` is unbounded                                |
| `may_run`   | command prefixes an agent may run itself, on top of read-only git; see [Agents](agents.md) |

## The review skill

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
