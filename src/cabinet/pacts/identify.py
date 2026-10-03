"""One class per identify step, named for it.

A step is reached by returning its class, as in `pacts/sweep.py`. The carrier
these rebuild stays in `pacts/issues.py`, and so do the payloads already named
for a step of their own: `Page`, `Pinning`.
"""

from cabinet.pacts.issues import Identifying


class Gather(Identifying):
    pass


class Leaf(Identifying):
    pass


class Tally(Identifying):
    pass
