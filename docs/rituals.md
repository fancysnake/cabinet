# Rituals

Thirteen rituals, one facade each under `cabinet.rituals`. Nine share one
graph: `heal.mine` sweeps every open pull request of yours, `heal.pr` takes
one by number in a worktree of its own, `heal.this` takes your branch's,
`heal.main` fixes a red base on a branch and opens a pull request, and
`merge`, `ci`, `answer`, `review` and `guide` each run a single task on your
branch. One identifies your open issues, and three make
the labels the others read and put on.

--8<-- "README.md:cast"

## heal.mine, heal.pr and heal.this

*Evocation.* Each pull request is read once and turned into a todo list, in
the order a cast works it:

| fact                                         | label that removes it | todo     |
| -------------------------------------------- | --------------------- | -------- |
| conflicts with its base                      | none                  | `merge`  |
| a red check whose job is in `ci.jobs`        | none                  | `ci`     |
| an open pull request                         | `labels.reviewed`     | `review` |
| unresolved review threads, whoever wrote them | none                 | `answer` |
| nothing else to do                           | `labels.qa`           | `guide`  |

Facts make todos; labels only remove them. A branch behind its base but
without a conflict needs no merge. Where the forge has not worked out whether
a branch conflicts, git does, in memory, against the remote's refs.

`heal.mine` surveys every open pull request of yours not wearing the wait
label, oldest-modified first. `heal.pr --number N` takes the open pull request
of yours with that number. `heal.this` takes the pull request for the branch
at the cwd, and reports that there is none when there is none. Each prints one
line per pull request as it reads it:

```text
#7 feature: merge, ci (checks), review, answer (3 threads)
#9 docs: guide
```

A forge call refused for a rate limit waits and tries again, doubling the
pause from 15 seconds; a limit that lasts past about 15 minutes fails the cast.
A pull request the forge would not answer about for any other reason gets a
line saying why, and the cast goes on. With `--plan-only true` that is all:
nothing is checked out, committed or labelled.

`heal.mine` works no branch itself. For each one with work it queues a
`heal.pr` on the vekna daemon and goes on to the next. Then it reports which
cast took which branch, and ends:

```text
heal — 2 queued

  #7 feature: cast c41
  #9 docs: cast c42
```

`heal.mine` does not wait for the casts it queued, so it holds no place on
the daemon while they run. Each `heal.pr` reports its own branch when it
ends, and fails where its branch was blocked.

The daemon runs each `heal.pr` in a pooled worktree as slots and trees free
up, so the checkout you cast from never moves. The daemon decides whether the
queued casts run one at a time or together; `vekna cast --queue heal.mine`
hands the whole cast to the daemon, which heals the branches side by side.
Typed at a terminal, `vekna cast heal.mine` stays for the casts it queued:
vekna prints each one's rows and prompts as they come, and the command exits
`1` where one of them failed. A queued cast with no terminal following it
asks in the `vekna` window, and on Discord where vekna 3.1.0 or later has a
`[discord]` table. Discord sends no empty reply, so answer `ok` there where a
terminal takes the return key. With no daemon running, `heal.mine` prints its
survey and fails: start one with `vekna`. If the daemon goes away after some
casts were queued, the report names those and `heal.mine` fails.
[Configuration](configuration.md#worktrees)
sizes the pool. Typed by hand, `heal.pr` runs where it was typed.

Otherwise each branch with a task the cast works is taken: the worktree must
be clean, the remote is fetched, and the branch is checked out and
fast-forwarded to it. The base is read as the remote has it and never checked
out, because a worktree cannot check out a branch another worktree stands on.
For the same reason a pull request branch that another worktree stands on is
blocked, and fails the cast: move that worktree off the branch and cast again.
The tasks then run in order, and each one hands
the branch back for the next:

- **merge**: the base merged in, conflicts resolved, the gate made green. See
  [merge](#merge).
- **ci**: the red CI jobs rerun, fixed or covered. See [ci](#ci).
- **review**: the quality review posted. See [review](#review).
- **answer**: the review threads triaged with you, fixed, replied to and
  settled. Attended casts only.
  See [answer](#answer).
- **guide**: the smoke test posted, once nothing else is left. See
  [guide](#guide).

Whatever the cast committed is pushed before the next task and before
the branch is left, so the review's comments anchor to code the forge has.
Nothing waits for CI after a push.

When a branch has no task left, the cast surveys it again and works what the
survey now finds: the comments the review posted are threads to answer, and a
branch with nothing else left gets its guide. A task the branch already had in
this cast is not worked a second time, so a check that is still red waits for
the next cast. The cast leaves the branch when a survey finds nothing new.

A cast takes a branch only where the worst that branch can spend fits its
step budget of 1,003 steps. The budget is sized for `heal.mine` surveying and
queuing the thousand pull requests GitHub lists. A branch spends at most 105
steps at the default `--bound` and three CI jobs, so a much larger `--bound`
still fits. A branch that does not fit ends the cast without failing it, and
the report names it as not reached. Cast again with a smaller `--bound`.

Every open pull request of yours is listed, up to a thousand: GitHub's search
returns no more, and GitLab's listing stops there to fit the step budget. A
listing that stops short says so in the report.

## heal.main

*Evocation.* Fixes a red base. It reads the checks on `base` whose job is in
`ci.jobs`, the same list the pull requests use, and prints what it found:

```text
main: ci (checks)
```

Where a job is red, it cuts the branch `main_fix_branch` names from the base
as the remote has it, and fixes each red job the way [ci](#ci) does, one
commit per job. It reruns nothing: a red job is fixed. Then it pushes the
branch and opens a pull request, which `heal.mine` tends from there. It never
pushes to the base and never merges.

A branch whose gate will not go green is opened all the same, and the pull
request says what stopped it. Where no fix was committed, no pull request is
opened.

One fix at a time: while an open pull request of yours sits on a branch of
the `main_fix_branch` shape, `heal.main` says so and ends. With
`--plan-only true` it prints the red jobs and cuts no branch.

A job that runs only on the base, never on a pull request, is fixed only if
it is in `ci.jobs`.

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
the rest of its tasks are worked anyway, and the report calls it blocked. A
cast that leaves a branch blocked fails, after the other branches are worked
and the report is printed.

## ci

*Abjuration.* `heal.this` with the ci task alone, the way *Lesser
Restoration* ends one condition at a time. A red check on a job listed in
`[cabinet.ci.jobs]` makes a ci todo, and so does a green `covering` check
whose summary names a gap. The task works the red checks one at a time:

1. **Rerun.** A job with `rerun = true` runs again if this head has run it
   only once. If anything was rerun, the task ends there: a fix pushed on top
   would start a new CI run and waste the rerun. The next cast reads the
   result.
2. **Fix with a gate.** An agent reads the end of the failed job's log and
   edits. Then the job's `gate` runs and is repaired the way the merge's gate
   is, with `fast` re-run between rounds, up to `--bound` times.
3. **Fix without a gate.** An agent reads the log and makes one attempt. The
   ritual commits it; the next CI run checks it.
4. **Cover.** A `covering` job runs the coverage measurement here, and the
   agent writes tests for the lines it names, with the fast measurement re-run
   between rounds.

Each job's fix is a commit of its own, and all of them go up in one push. A
job gets one check fixed per cast: when several of a matrix job's entries are
red, the first is fixed and the rest are named for the next cast. A job whose
gate will not go green stands the branch down, as a merge does, and the task
names the checks it did not reach. A fix that changes nothing is no fix:
the job stays red, and the report says it passes here while CI is still red.

In `heal.pr` and `heal.this`, a branch whose merge was committed leaves ci
for the next cast. The merge's push starts a new CI run, so the red checks the
survey read belong to the old head.

## answer

*Enchantment.* `heal.this` with the answer task alone, the way *Command* puts
one word to each listener. Every unresolved review thread makes an answer
todo, whoever wrote it, until the ritual has replied to it. The ritual
resolves a thread that you opened, that an app opened on GitHub, or that a
login in `bots` opened. A thread another person opened gets the reply and
stays open for them to resolve; it makes an answer todo again when they
write under the reply. Every item is yours to decide, so only an attended
cast works it. A cast run with `vekna cast --unattended` leaves the threads
alone and ends its report with what waits for you:

```text
waiting for you, cast without --unattended:
  #7 feature: 11 threads
```

Attended, the task goes round in batches of `--batch` open threads:

1. **Finish what was left.** A thread of yours whose last word is the ritual's
   own reply is resolved. A thread with an issue already filed for it gets the
   reply naming the issue. Both happen when the forge failed partway through
   an earlier cast.
2. **Read.** An agent reads the open threads against the code and returns a
   triage: one item per thread, with a priority (p1 to p4) and what it would
   do (fix, reject or file).
3. **Decide.** Each item is put to you as one card, the most urgent first.
   Press return or answer `ok` to take the reading's proposal, or answer in
   your own words.

    ```text
    #58 Add the export page — thread 1 of 3

    ── The thread ──────────────────────────────────────────────────────────────────
    Thread:   src/export.py:41, raised by alice
    Raised:   stop when the list of rows is empty
    If left:  an export with no rows crashes instead of saying so, and the page that
              asked for it shows an error with no reason

    ── The reading would FIX it ────────────────────────────────────────────────────
    Action:   fix — the loop reads the first row before it checks for one
    Grounds:  tested — ran the export with no rows and got IndexError
    Estimate: small, 1 file, low risk
    ```

    The second title names what a return key does. Grounds is `tested`,
    `read` or `not checked`: whether the reading ran something, only read the
    code, or did neither. The card wraps its rows at 80 columns.
4. **Answer.** Another agent fixes what you said to fix and drafts a reply for
   every item, written for the comment's author: it leaves out what you said
   at the triage and what the agent could not run or verify.
5. **Approve.** Only with `approve_replies = true`. Each drafted reply is put
   to you as it would be posted. Press return or answer `ok` to post it, or
   say what to change: the agent redrafts it and you are asked again, up to
   `--bound` times. The last asking says that no redraft is left. A reply you still do
   not take then is not posted, and its thread stays open.
6. **Post.** The ritual opens the issues you said to file, posts the replies
   and resolves the threads that are its to resolve.

Then the next batch is read, up to three rounds a cast; what is still open
after that waits for the next one. What the answers changed goes through the
gate, repaired as the merge's is, and is committed as one commit and pushed.
A gate that will not go green stands the branch down, as a merge does.

The review posts an item as a plain comment when the forge refuses its line,
as it does for a file the pull request does not change. A forge cannot resolve
a plain comment, so `answer` treats each such comment of yours as an open
thread. The ritual replies in a new plain comment that links to the item.
That reply settles the item: delete it to open the item again.

A round that finds no thread open puts the answered label on, so the pull
request tells you its review is answered. The next answer task takes it off
before it starts. The label is only for you to read: open threads decide
whether there is answering to do.

## review

*Divination.* `heal.this` with the review task alone. It posts the quality
review as inline comments, one per action item and anchored to the code it is
about, then puts the reviewed label on. A pull request already wearing the
label has had its review: take the label off after changing the branch
meaningfully, and the next cast reviews it again. A branch whose gate stood
down is reviewed all the same, and the agent is told why it is not green.
An attended `heal.*` cast then answers the comments it posted; `review` alone
posts them and stops.

## guide

*Divination.* `heal.this` with the guide task alone, the way *Guidance* lends
a hand to whoever checks the branch. A branch gets a guide only when the survey
finds nothing else to do and it is not wearing the qa label:

1. An agent follows the skill at `smoke_skill` and writes the manual smoke
   test for the branch: the shortest path that proves the change works where
   users meet it, and the features nearby it could have broken. It runs
   nothing.
2. The ritual posts the test as a plain comment on the pull request, never a
   review thread, so `answer` does not pick it up.
3. The ritual puts the qa label on.

To ask for a new guide, take the label off. The next cast edits the guide it
posted before rather than posting a second, and never touches a comment
someone else wrote. Nothing takes the label off for
you: merging the base in does not cost a branch its guide.

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

*Conjuration.* Makes the four labels `heal` reads and puts on: the reviewed,
wait, qa and answered labels. The reviewed and qa labels are the ritual's own:
each goes on once its task is done, so the next cast does not repeat it. The
answered label tells you the review threads are settled; see
[answer](#answer). A fact that goes away once
fixed, such as a conflict or a red check, needs no label. The wait label is
yours: put it on a pull request `heal.mine` should leave alone, such as a draft
or one waiting on somebody else, and take it off to hand it back. Cast
`labels.heal` before the first `heal` when `labels` was not, and again after
changing `[cabinet.labels]`.

## labels.identify

*Conjuration.* Makes the labels `identify` puts on issues: the types, the
sizes and `epic`. Cast it before the first `identify` when `labels` was
not. The names are fixed, because the `issues` skill names them too.

## Flags

| flag         | rituals             | what it does                                           |
| ------------ | ------------------- | ------------------------------------------------------ |
| `--bound N`  | `heal.*`, `merge`, `ci`, `answer` | how many times one step may be retried on one branch, 1 to 5, default 3 |
| `--number N` | `heal.pr` | the pull request to heal |
| `--plan-only true` | `heal.*`, `merge`, `ci`, `answer`, `review`, `guide` | survey and print each pull request's todos; change nothing |
| `--batch N`  | `identify`, `heal.*`, `answer` | how many issues go on one page, or open threads in one round of answers, default 7 |

A flag a repository always wants goes in `.vekna.toml` as one of vekna's
component defaults, keyed by the ritual's full name. A flag on the command
line still wins:

```toml
[defaults."cabinet:heal.mine"]
bound = 2
```

## Using only some of them

Each ritual has a facade of its own, so a project names the ones it wants. A
repository that only wants reviews casts `review` and never sees the rest:

```toml
[rituals]
modules = ["cabinet.rituals.review"]
```

`modules = ["cabinet.rituals"]` loads every ritual. `cabinet.rituals.heal_mine`
also loads `heal.pr`, the ritual it queues. `heal.main` has a facade of its
own, `cabinet.rituals.heal_main`.
