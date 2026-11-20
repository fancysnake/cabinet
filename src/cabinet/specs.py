"""Business invariants: numbers only a rule reads."""

from cabinet.pacts.pulls import PULL_LIMIT

# How much of a gate's output is worth paying for, counted in characters rather
# than lines: what is being spent is tokens, and a line has no fixed price —
# twenty lines of ruff is a couple of hundred bytes, and twenty carrying a
# pytest assertion repr or a mypy note about a long generic type is orders of
# magnitude more. A task list stops at the first failure, and every tool in it
# puts its verdict last, so what fits at the end is the part that says what is
# wrong.
BUDGET = 4000

# What a report row can carry, counted in lines because this one is read by a
# person: a dozen is the tail every tool in these chains puts its tally in.
VERDICT_LINES = 12

# Columns a triage card wraps its own lines at. A mill cannot ask the terminal
# its width, and a terminal narrower than this wraps the card a second time.
CARD_WIDTH = 80

# A patch below this is a patch with a gap in it.
WHOLE = 100.0

# The engine's step budget for one heal cast. Running out of it raises past
# `chart` and loses the report, so `survey` takes a branch only where the worst
# it can spend still fits. Sized for the cast that spends most: `heal.mine` on
# the most pull requests a forge lists (`PULL_LIMIT`), a `summon` for each,
# and the muster, the `summon` that finds the queue empty, `attend` and
# `chart` around them. A cast that works a branch works one: eighty-two steps
# at worst at the default bound of three and the three default CI jobs, three
# rounds of `answer` among them, and four around it. The rest is room for a
# bigger bound and more jobs.
HEAL_STEPS = PULL_LIMIT + 4

# A problem this big goes to the escalated model on the first ask: files left
# conflicted by a merge, red checks on the branch's board, review threads open
# on the pull request. The threads sit above the default batch of seven, so
# one full round of `answer` is not a big one.
MANY_CONFLICTS = 5
MANY_RED = 3
MANY_THREADS = 10
