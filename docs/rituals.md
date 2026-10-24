# Rituals

Nine rituals, one facade each under `cabinet.rituals`. Four work your pull
requests through one graph: `heal.mine` sweeps every open pull request of
yours, `heal.this` takes your branch's, and `merge` and `review` each run a
single task on your branch. One identifies your open issues, and three make
the labels the others read and put on.

--8<-- "README.md:cast"

## heal.mine and heal.this

*Evocation.* Each pull request is read once and turned into a todo list, in
the order a cast works it:

| fact                                         | label that removes it | todo     |
| -------------------------------------------- | --------------------- | -------- |
| conflicts with its base                      | none                  | `merge`  |
| a red check whose job is in `ci.jobs`        | none                  | `ci`     |
| unresolved review threads, whoever wrote them | none                 | `answer` |
| an open pull request                         | `labels.reviewed`     | `review` |
| nothing else to do                           | `labels.qa`           | `guide`  |

Facts make todos; labels only remove them. A branch behind its base but
without a conflict needs no merge. Where the forge has not worked out whether
a branch conflicts, git does, in memory, against the remote's refs.

`heal.mine` takes every open pull request of yours not wearing the wait label,
oldest-modified first. `heal.this` takes the pull request for the branch at
the cwd, and reports that there is none when there is none. Each prints one
line per pull request as it reads it:

```text
#7 feature: merge, ci (checks), answer (3 threads), review
#9 docs: guide
```

A pull request the forge would not answer about gets a line saying why, and
the cast goes on. With `--plan-only true` that is all: nothing is checked out,
committed or labelled.

Otherwise each branch with a task the cast works is taken: the worktree must
be clean, the base is brought up to date, and the branch is checked out and
fast-forwarded to the remote. The tasks then run in order, and each one hands
the branch back for the next:

- **merge**: the base merged in, conflicts resolved, the gate made green. See
  [merge](#merge).
- **review**: the quality review posted. See [review](#review).

`ci`, `answer` and `guide` are surveyed and reported; their tasks are still
to come. Whatever the cast committed is pushed before the review, so the
comments anchor to code the forge has, and before the branch is left. Nothing
waits for CI after a push.

A cast takes the next branch only while the worst that branch can spend still
fits its step budget. One that does not fit ends the cast without failing it,
and the report names the branches left for the next cast. The budget fits a
hundred branches at the default `--bound`.

## merge

*Transmutation.* `heal.this` with the merge task alone, the way *Mending*
joins what was split. Only a conflict makes a merge todo:

1. Merge the base in. A conflict goes to an agent, which stages what it
   resolved; the ritual makes the commit.
2. Run the gate. Red means a repair attempt: the agent gets the task's output
   and edits, the ritual re-runs the task that broke, up to `--bound` times,
   and the whole gate once more when it comes back green.
3. Commit the merge and the repairs, and push.

A branch the gate will not go green on stands down: the worktree is released,
the rest of its tasks are worked anyway, and the report calls it blocked.

## review

*Divination.* `heal.this` with the review task alone. It posts the quality
review as inline comments, one per action item and anchored to the code it is
about, then puts the reviewed label on. A pull request already wearing the
label has had its review: take the label off after changing the branch
meaningfully, and the next cast reviews it again. A branch whose gate stood
down is reviewed all the same, and the agent is told why it is not green.

## identify

*Divination.* The backlog, a page at a time, unasked. The candidates are your
open issues, opened by you or assigned to you, that lack a type label or lack
a size label without being an epic. They go in pages of `--batch`, lowest
number first:

1. The page is shown as it is taken up.
2. One agent reads the page: it reads the code each issue is about and says
   what the issue is — a type (`feature`, `edit`, `chore`, `bug`) and
   a size (`S`, `M`, `L`), or `epic` in place of a size with the sub-issues it
   should be split into, plus the open issues already part of it and the ones
   blocking it. An issue it could not size is left unsized, which the report
   tells apart from an epic.
3. The ritual puts that on the forge: the labels, then each sub-issue opened,
   labelled and attached under its epic, then the links. A write the forge
   refuses — a label it lacks, say — is named under its
   issue in the report, and the rest still go on, this issue's and the next
   ones'. A sub-issue opened but not attached is named there too. A page on
   which every write was refused stops the cast: that is a forge that is
   down or will not let you write, not one that disagrees with a write.
4. The next page continues the same agent session, so the skill it follows is
   read once per cast.

The agent follows the skill at `identify_skill` (see
[Configuration](configuration.md)): the `issues` skill from the
[plugins](plugins.md). It reaches the forge for nothing and edits no files, as
every other agent here — the writes are the ritual's, one step of their own.
The issue bodies reach it fenced as data, the same as review threads. The
report says what each issue came to, and says so when the forge would not list
your whole backlog: past the listing's cap an issue is never swept, and it
looks from here exactly like one nothing wanted doing to.

## labels

*Conjuration.* Makes every label cabinet uses, created where missing and
refreshed where present: what `labels.heal` and `labels.identify` each make, in
one cast. Cast it once to set a project up.

## labels.heal

*Conjuration.* Makes the three labels `heal` reads and puts on: the reviewed,
wait and qa labels. Each exists only to stop a ritual repeating something it
put on the pull request; a fact that goes away once fixed, such as a conflict
or a red check, needs no label. Cast it before the first `heal` when `labels`
was not, and again after changing `[cabinet.labels]`.

## labels.identify

*Conjuration.* Makes the labels `identify` puts on issues: the types, the
sizes and `epic`. Cast it before the first `identify` when `labels` was
not. The names are fixed, because the `issues` skill names them too.

## Flags

| flag         | rituals             | what it does                                           |
| ------------ | ------------------- | ------------------------------------------------------ |
| `--bound N`  | `heal.*`, `merge`   | how many times one step may be retried on one branch, 1 to 5, default 3 |
| `--attended true` | `heal.*`, `merge` | somebody is at the terminal: ask before every repair attempt instead of letting the budget decide, and run agents in Claude's `auto` permission mode rather than `dontAsk` (see [Agents](agents.md)) |
| `--plan-only true` | `heal.*`, `merge`, `review` | survey and print each pull request's todos; change nothing |
| `--batch N`  | `identify`          | how many issues go on one page, default 7               |

## Using only some of them

Each ritual has a facade of its own, so a project names the ones it wants. A
repository that only wants reviews casts `review` and never sees the rest:

```toml
[rituals]
modules = ["cabinet.rituals.review"]
```

`modules = ["cabinet.rituals"]` loads every ritual.
