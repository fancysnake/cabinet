"""One class per heal step, named for it.

A step is reached by returning its class, as in `pacts/sweep.py`. The carrier
these rebuild is in `pacts/healing.py`.
"""

from cabinet.pacts.healing import Healing


class Muster(Healing):
    pass


class Survey(Healing):
    pass


class Chart(Healing):
    pass
