"""Business invariants: numbers only a rule reads."""

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

# A patch below this is a patch with a gap in it.
WHOLE = 100.0

# The engine's step budget for one heal cast. Running out of it raises past
# `chart` and loses the report, so `survey` takes a branch only where the worst
# it can spend still fits. Big enough that the most GitHub lists, a hundred
# branches, each fits at the default bound of three and the three default CI
# jobs: fifty-seven steps a branch at worst, and a hundred and three around
# them.
HEAL_STEPS = 100 * 57 + 103
