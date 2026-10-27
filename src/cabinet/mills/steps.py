"""How much of a cast's step budget each part of it spends."""

from typing_extensions import override

from cabinet.pacts.budgets import ROUNDS
from cabinet.pacts.healing import Run
from cabinet.pacts.services import StepsProtocol
from cabinet.specs import HEAL_STEPS

# The steps every branch walks at most once: `check_clean`, `sync_branch`,
# `merge_base`, `finish_merge` or `stand_down`, `rerun_jobs`, `quality_review`
# and `finish_pr`, two pushes (one after the merge, one after `ci`), and
# `tend` once before each of the six that follow it. `post_guide` is not
# among them: the survey asks for a guide only where nothing else is left.
_ONCE = 15


# A gate's loop: a whole run and a narrowed one for every repair the bound
# allows, then the last whole run.
def _gates(bound: int) -> int:
    return 2 * bound + 1


# `resolve_conflicts`: one per attempt, and the one that reads the index clean.
def _attempts(bound: int) -> int:
    return bound + 1


# `ci` per red job: `pick_job`, `mend_job`, a gate's loop, and `land_job` or
# `stand_down`. Then the `pick_job` that finds none left.
def _jobs(bound: int, jobs: int) -> int:
    return jobs * (3 + _gates(bound)) + 1


# `answer`: `settle_left` and the `tend` before it, then four steps a round for
# every round it may take, the `read_threads` that finds nothing more to do, a
# gate's loop, `land_answers` or `stand_down`, and the push with the `tend`
# before it.
def _answer(bound: int) -> int:
    return 2 + 4 * ROUNDS + 1 + _gates(bound) + 1 + 2


class Steps(StepsProtocol):
    # Every step that works no branch: the muster, a `survey` per branch and
    # the one that finds the queue empty, and `chart`.
    @override
    def opening(self, queue: int) -> int:
        return queue + 3

    # The worst one branch can spend, or `None` where the budget has no room
    # for it: the steps walked once, `resolve_conflicts`, the loop of
    # `gate_check`, every configured job red, and every round of `answer`.
    @override
    def heal_share(self, run: Run) -> int | None:
        jobs = len(run.project.ci.jobs)
        steps = (
            _ONCE
            + _attempts(run.bound)
            + _gates(run.bound)
            + _jobs(run.bound, jobs)
            + _answer(run.bound)
        )
        if run.reserved + steps > HEAL_STEPS:
            return None
        return steps
