"""One class per sweep step, named for it.

A step is reached by returning its class. `Closed` is `finish_pr`'s own, and
lives with what it closes.
"""

from cabinet.pacts.pulls import Run, Work


class ListPrs(Run):
    pass


class NextPr(Run):
    pass


# Not `Report`: that is what the step hands back.
class Reporting(Run):
    pass


class CheckClean(Work):
    pass


class SyncBranch(Work):
    pass


class MergeBase(Work):
    pass


class ResolveConflicts(Work):
    pass


class TakePass(Work):
    pass


class GateCheck(Work):
    pass


class FinishMerge(Work):
    pass


class CheckCi(Work):
    pass


class CloseGap(Work):
    pass


class PushWork(Work):
    pass


class QualityReview(Work):
    pass


class StandDown(Work):
    pass


class SkipPr(Work):
    pass


class SetAside(Work):
    pass
