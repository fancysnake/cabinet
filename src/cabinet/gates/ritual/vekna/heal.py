"""Heal your pull requests: read what each one needs next.

    vekna cast heal.this --plan-only true
    vekna cast heal.mine --plan-only true

``heal.this`` takes the pull request of the branch at the cwd; ``heal.mine``
takes every open pull request of yours not wearing the wait label,
oldest-modified first.

Each one is surveyed once: whether it conflicts with its base, which of the
configured CI jobs are red, how many review threads are open, and which
labels it wears. That becomes its todo list, in the order a cast would work
it: merge, ci, answer, review, guide. Facts make a todo; the reviewed and qa
labels only take one away. The list is printed a line per pull request as it
is read.

Nothing is written: no checkout, no commit, no label. Where the forge has not
worked out whether a branch conflicts, git does, in memory, against the
remote's refs.
"""

from vekna.lexicon import Done, RitualError, emit_delta, step

from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import Chart, MusterMine, MusterThis, Survey
from cabinet.pacts.healing import Facts, Plan, Surveyed, Unsurveyed
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services


# Every open pull request of yours the forge lists, bar the parked ones.
@step
async def muster_mine(healing: MusterMine) -> Survey:
    project = healing.project
    pulls = await services().forge(project).pulls()
    return healing.queued(services().pulls.wanted(pulls, project)).to(Survey)


# The open pull request of yours for the branch at the cwd.
@step
async def muster_this(healing: MusterThis) -> Survey:
    project = healing.project
    pulls = await services().forge(project).pulls()
    here = await services().scm(project).here()
    if not (queue := services().pulls.at(pulls, here)):
        msg = f"no open pull request of yours has {here} as its branch"
        raise RitualError(msg)
    return healing.queued(queue).to(Survey)


# Read the next pull request's facts and say what it needs.
@step
async def survey(healing: Survey) -> Chart | Survey:
    if not healing.queue:
        return healing.to(Chart)
    row = await _surveyed(healing.project, healing.queue[0])
    emit_delta(services().report.surveyed(row))
    return healing.took(row).to(Survey)


@step
def chart(healing: Chart) -> Done[Plan]:
    return Done(Plan(surveyed=healing.surveyed))


# One pull request the forge or git would not answer about is a row saying
# so, not the end of the cast: the next one may answer fine.
async def _surveyed(project: Project, pull: PullRequest) -> Surveyed | Unsurveyed:
    forge = services().forge(project)
    try:
        board = await forge.board(pull.branch)
        threads = await forge.threads(pull.number)
        if (conflicted := pull.conflicted) is None:
            conflicted = await services().scm(project).conflicts(pull.base, pull.branch)
    except (ForgeError, ScmError) as error:
        return Unsurveyed(
            number=pull.number, branch=pull.branch, url=pull.url, note=str(error)
        )
    facts = Facts(pull=pull, board=board, threads=threads, conflicted=conflicted)
    return services().todos.surveyed(facts, project)
