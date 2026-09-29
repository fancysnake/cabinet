"""One class per review step, named for it.

A step is reached by returning its class, as in `pacts/sweep.py`. The carriers
these rebuild stay in `pacts/reviews.py`, and so do the payloads already named
for a step of their own: `Triage`, `Instructed`, `Answering`, `Landing`.
"""

from cabinet.pacts.reviews import Branch, Picking


class QueueUp(Picking):
    pass


class Pick(Picking):
    pass


class Recap(Picking):
    pass


class Look(Branch):
    pass


class Read(Branch):
    pass


class Land(Branch):
    pass


class Settle(Branch):
    pass
