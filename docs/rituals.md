# Rituals

Four rituals, one facade each under `cabinet.rituals`. Two of them sweep every
open pull request of yours; one works a single branch with you at the terminal;
one prepares the ground for the other three.

```bash
vekna cast refresh [--bound N] [--attended true]
vekna cast cover [--bound N] [--attended true]
vekna cast review [--bound N] [--batch N]
vekna cast labels
```

## refresh

*Transmutation.* The night's fast pass. Every open pull request of yours
that is not wearing the wait label is taken in turn, oldest-modified first:

1. Fetch and merge the base branch in. A conflict goes to an agent, which
   stages what it resolved; the ritual makes the commit.
2. Run the gate: lint, types, the fast suites, with no coverage measurement
   anywhere in it. Red means a repair attempt: the agent gets the task's
   output and edits, the ritual re-runs the task that broke, up to `--bound`
   times, and the whole gate once more when it comes back green. A branch the
   merge brought nothing to, and whose gate jobs CI is happy with, skips the
   gate: the server has run it over that tree already.
3. Push.
4. Post the quality review, one inline comment per action item anchored to
   the code it is about, unless the branch already wears the reviewed label.
   The label goes on once the review is posted; take it off after changing
   the branch meaningfully and the next run reviews it again.

A branch the gate would not go green on stands down rather than stopping: the
worktree is released and the branch is reviewed on its last good commit, then
reported blocked. Like *Purify Food and Drink*: what was there is still there,
only fit to use.

## cover

*Abjuration.* The night's slow pass, and it asks before it spends. It takes
a branch the same way `refresh` does, then reads what CI made of it: the check
board, including the patch coverage the coverage service's own check
carries. Where coverage or the suite is unhappy:

1. Run the project's `coverage` task.
2. Hand the agent what the branch left uncovered; it writes the tests, or
   repairs the suite where it is the suite that is broken.
3. Re-measure with `fast_coverage` between rounds, up to `--bound` times. The
   full measurement runs once more at the end, and that is the one that
   counts.
4. Push.

It posts no review: `refresh` runs first and that is where the review comes
from. Building the defences up.

## review

*Divination.* The morning after, and the opposite of the sweeps: nothing is
done without you saying so, and it is what commits the result.

A branch is a candidate when its pull request is open, yours, wearing the
reviewed label, not wearing the wait label, and carrying a review thread
nobody has settled. They are offered one after another, longest-waiting first,
except that the branch you are standing on goes first. Saying no to one moves
on to the next. For each branch you take:

1. The ritual fetches the open threads, `--batch` at a time, and an agent
   reads them against the code as it stands: one item per thread, with a
   priority and what it would do about it.
2. You answer the items one at a time, in your own words; saying nothing
   takes the reading's own proposal.
3. One agent fixes what you said to fix and writes a reply for every item.
   The ritual, the only thing that can reach the forge, opens the issues you
   said to file, posts the replies, and settles the threads.
4. Another round fetches what the forge still holds open, until nothing is.
5. The gate runs once, after the last round, repaired up to `--bound` times,
   and what came out is committed and pushed. No question in between: the
   answers you gave were the decision.

A gate that will not go green ends the cast rather than moving on, because the
repair work is sitting uncommitted in the worktree. Discovering what was
found, and settling it.

## labels

*Conjuration.* Makes every label the other rituals read and write, created
where missing and refreshed where present: the reviewed and wait labels and
each ritual's `started`/`done` checkpoints. Cast it once before the first
sweep, and again after changing `[cabinet.labels]`.

## Flags

| flag         | rituals             | what it does                                           |
| ------------ | ------------------- | ------------------------------------------------------ |
| `--bound N`  | all but `labels`    | how many times one step may be retried on one branch, 1 to 5, default 3 |
| `--attended true` | `refresh`, `cover` | somebody is at the terminal: ask before every repair attempt instead of letting the budget decide, and run agents in Claude's `auto` permission mode rather than `dontAsk` (see [Agents](agents.md)) |
| `--batch N`  | `review`            | how many open threads are read and answered in one round, default 7 |

`--batch` keeps a review within reach: a forty-thread review is six triages
you can hold in your head, and still one commit.

## Checkpoints

Every ritual but `labels` marks the branch it works. `v:refresh:started` goes on when
`refresh` begins and may have changed the branch; `v:refresh:done` replaces it
when the ritual ends clean. The two halves of a pair are never worn together,
so a label is a true claim about the branch at any moment. The prefix is
`labels.marker`; see [Configuration](configuration.md).

## Using only some of them

Each ritual has a facade of its own, so a project names the ones it wants. A
repository with no coverage task casts `refresh` and `review` and never sees
`cover`:

```toml
[rituals]
modules = ["cabinet.rituals.refresh", "cabinet.rituals.review"]
```

`modules = ["cabinet.rituals"]` loads all four.
