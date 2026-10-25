"""Pull requests as the forge lists them, and what CI says about them."""

from typing import Annotated

from pydantic import BaseModel, Field

from cabinet.pacts.project import Ci

# A bound counts attempts at one step, so zero would mean a step that may never
# be tried at all; past five a repair loop has stopped being a repair loop.
Bound = Annotated[int, Field(ge=1, le=5)]


# One pull request as the forge lists it, in the rituals' own words: which
# forge spelled the fields is the adapter's business.
class PullRequest(BaseModel):
    number: int
    title: str
    url: str
    branch: str
    base: str
    updated_at: str
    # As they stood at the listing. Read by the survey, once: a label a cast
    # puts on later is that cast's own business.
    labels: list[str] = []
    # Whether the branch conflicts with its base, as the forge last worked
    # out. None while the forge has not worked it out: git can, locally.
    conflicted: bool | None = None

    def wears(self, label: str) -> bool:
        return label in self.labels


# What CI says about one thing it ran. `passed` is None while a run is still
# going, which is why nothing reads it as anything but "not success yet".
# `title` is the one-line summary a job writes for itself: absent for most of
# the board, and for the patch check the coverage this branch achieved.
class Check(BaseModel):
    name: str
    passed: bool | None = None
    title: str = ""
    # The forge's id for the run, which a rerun and a log are asked by: the
    # job, for a check CI ran itself.
    id: int


class Board(BaseModel):
    checks: list[Check] = []
    # A page that stopped short of the whole board. What fell off the end could
    # be the check a reader turns on, and a page that does not say is not a
    # page saying yes.
    truncated: bool = False

    # The checks whose job is configured: red anywhere else is not the
    # rituals' business.
    def watched(self, ci: Ci) -> list[Check]:
        return [check for check in self.checks if ci.job(check.name) is not None]
