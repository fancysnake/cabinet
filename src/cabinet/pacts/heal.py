"""One class per heal step, named for it.

A step is reached by returning its class. The carriers these rebuild are in
`pacts/healing.py`: the cast's steps take a `Run`, a branch's take a `Work`.
The three in the middle of an `answer` round carry what the round has read
beside the `Work`, and hand the `Work` back on when the round is done.
"""

from pydantic import BaseModel

from cabinet.pacts.healing import Run, Work
from cabinet.pacts.threads import Answer, TriageItem


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


class RerunJobs(Work):
    pass


class PickJob(Work):
    pass


class MendJob(Work):
    pass


class JobGate(Work):
    pass


class CloseGap(Work):
    pass


class LandJob(Work):
    pass


class SettleLeft(Work):
    pass


class ReadThreads(Work):
    pass


# The triage, waiting for your answer to each item.
class AskTriage(BaseModel):
    work: Work
    items: list[TriageItem]


class AnswerThreads(BaseModel):
    work: Work
    # The whole thing the agent is sent, assembled where the triage and your
    # answers to it are both in hand.
    prompt: str
    # The threads the answers are owed under, so the step that posts them can
    # tell one the agent made up from one that was triaged.
    threads: list[str]


# What the agent answered, one entry per triaged thread, waiting to be posted
# by the step that can reach the forge.
class PostAnswers(BaseModel):
    work: Work
    items: list[Answer]
    threads: list[str]


class AnswerGate(Work):
    pass


class LandAnswers(Work):
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
