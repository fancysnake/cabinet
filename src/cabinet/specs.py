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

# The engine's step budget for one `review` cast. Running out of it raises past
# `recap` and loses the report, so `pick` keeps the cast under it by the worst
# case of every branch it takes, and the engine's own check never fires.
REVIEW_STEPS = 400

# The same for one `refresh` or `cover` cast, kept by `next_pr`. Big enough that
# the most GitHub lists, a hundred branches, each fits at the default bound
# of three: twenty steps a branch at worst, and a hundred and three around them.
# `REVIEW_STEPS` has no such sum behind it: a review branch's share stretches
# its rounds to whatever room is left, so there is no fixed worst case to size
# it by.
SWEEP_STEPS = 100 * 20 + 103
