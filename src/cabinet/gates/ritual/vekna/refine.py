"""Refine the backlog: give every issue of yours a type and a size.

    vekna cast refine [--batch N]

An issue is a candidate when it is open, yours — opened by you or assigned to
you — and missing a type label, or missing a size label without being an
epic. Candidates go in pages of ``--batch``, lowest number first, and each page
is asked about before anything touches it: saying no moves on to the next page
rather than ending the cast.

One agent refines a page. It reads the ``issues`` skill once, on the first
page, and every page after continues the same session, so it keeps both the
rules and what it did to the pages before. Unlike every other agent here it
speaks to the forge: it labels the issues, opens and attaches sub-issues under
an epic, and links related issues, through the forge's CLI and nothing wider.
What it hands back is its own account of that, and it is read for the report
and for nothing else.

The issue bodies are somebody's words, so they go to the agent fenced as data,
the same as review threads.
"""

from vekna.folio.flow import decide
from vekna.lexicon import RitualError, Transition, done, emit_delta, goto, step

from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.issues import Page, Refined, Refinement, Refining
from cabinet.pacts.services import services

# One session for every page in the cast, so the skill is read once.
_THREAD = "refine"


# Ask the forge for your open issues and queue the unrefined ones.
@step
async def gather(refining: Refining) -> Transition:
    try:
        issues = await services().forge(refining.project).issues()
    except ForgeError as error:
        return goto(tally, refining.but(stopped=str(error)))
    return goto(leaf, refining.but(queue=services().backlog.unrefined(issues)))


# Take the next page, if you say so.
@step
async def leaf(refining: Refining) -> Transition:
    if not refining.queue:
        return goto(tally, refining)
    batch = refining.batch
    page = Page(
        refining=refining.but(queue=refining.queue[batch:]),
        issues=refining.queue[:batch],
    )
    shown = "\n".join(f"  #{one.number} {one.title}" for one in page.issues)
    if not await decide(f"{shown}\nrefine these {len(page.issues)}?"):
        return goto(leaf, page.rowed("declined"))
    return goto(refine_page, page)


# The agent refines the page on the forge and says what it did.
@step
async def refine_page(page: Page) -> Transition:
    refining = page.refining
    project = refining.project
    prompt = services().prompts.refine(project, page.issues, briefed=refining.briefed)
    said = (
        await services()
        .agent(project)
        .ask_for(prompt, output=Refined, role="refiner", key=_THREAD, attended=True)
    )
    if isinstance(said, Fallen | Misread):
        return goto(tally, page.rowed("stopped").but(stopped=said.reason))
    # By the page's numbers, not the answer's: an issue the agent skipped is
    # named as skipped, and one it made up is not on the page to be named.
    items = {item.number: item for item in said.items}
    rows = [
        (
            Refinement(number=one.number, outcome="refined", item=items[one.number])
            if one.number in items
            else Refinement(number=one.number, outcome="missed")
        )
        for one in page.issues
    ]
    return goto(leaf, refining.rowed(rows).but(briefed=True))


# Every ending comes here, so the report is owed however the cast ends.
@step
def tally(refining: Refining) -> Transition:
    emit_delta(services().report.refine(refining))
    if refining.stopped:
        raise RitualError(refining.stopped)
    return done(refining)
