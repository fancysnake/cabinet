"""Pull requests as the forge lists them, and what CI says about them."""

from typing import Annotated, Self

from pydantic import BaseModel, Field

from cabinet.pacts.project import CiJob, Project

# A bound counts attempts at one step, so zero would mean a step that may never
# be tried at all; past five a repair loop has stopped being a repair loop.
Bound = Annotated[int, Field(ge=1, le=5)]

# Where a forge's listing of your open pull requests stops. Both forges cut the
# listing here, and the heal step budget is sized for this many, so raising it
# moves all of them together.
PULL_LIMIT = 1000


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

    # A branch `heal.main` works on before the forge has a pull request for it:
    # no number, URL or listing time yet.
    @classmethod
    def unopened(cls, branch: str, base: str, title: str) -> Self:
        return cls(
            number=0, title=title, url="", branch=branch, base=base, updated_at=""
        )

    @property
    def is_opened(self) -> bool:
        return self.number != 0

    def wears(self, label: str) -> bool:
        return label in self.labels


# Your open pull requests, and whether the forge listed them all: a listing
# that hit its cap hides the rest, and a hidden pull request looks exactly
# like one with nothing to do.
class PullListing(BaseModel):
    pulls: list[PullRequest] = []
    truncated: bool = False


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


# A check with the configured job it belongs to, resolved once where the
# board is read: `key` is the job's key in `[cabinet.ci.jobs]`, which every
# entry of a matrix job shares.
class Watched(BaseModel):
    check: Check
    key: str
    job: CiJob


class Board(BaseModel):
    checks: list[Check] = []

    # The checks whose job is configured: red anywhere else is not the
    # rituals' business. A covering job measures with the project's coverage
    # commands where it names none of its own.
    def watched(self, project: Project) -> list[Watched]:
        ci = project.ci
        watched: list[Watched] = []
        for check in self.checks:
            if (key := ci.key(check.name)) is None:
                continue
            job = ci.jobs[key]
            if job.covering:
                # Typed on the way in, as `model_copy` reads a bare literal as `Any`.
                update: dict[str, str] = {
                    "gate": job.gate or project.coverage,
                    "fast": job.fast or project.fast_coverage,
                }
                job = job.model_copy(update=update)
            watched.append(Watched(check=check, key=key, job=job))
        return watched
