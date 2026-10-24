"""One class per heal step, named for it.

A step is reached by returning its class. The carriers these rebuild are in
`pacts/healing.py`: the cast's steps take a `Run`, a branch's take a `Work`.
"""

from cabinet.pacts.healing import Run, Work


class MusterMine(Run):
    pass


class MusterThis(Run):
    pass


class Survey(Run):
    pass


class Chart(Run):
    pass


class CheckClean(Work):
    pass


class SyncBranch(Work):
    pass


class Tend(Work):
    pass


class MergeBase(Work):
    pass


class ResolveConflicts(Work):
    pass


class GateCheck(Work):
    pass


class FinishMerge(Work):
    pass


class PushWork(Work):
    pass


class QualityReview(Work):
    pass


class StandDown(Work):
    pass


class FinishPr(Work):
    pass


class SkipPr(Work):
    pass


class SetAside(Work):
    pass
