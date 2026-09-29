"""One class per refine step, named for it.

A step is reached by returning its class, as in `pacts/sweep.py`. The carrier
these rebuild stays in `pacts/issues.py`, and so do the payloads already named
for a step of their own: `Page`, `Pinning`.
"""

from cabinet.pacts.issues import Refining


class Gather(Refining):
    pass


class Leaf(Refining):
    pass


class Tally(Refining):
    pass
