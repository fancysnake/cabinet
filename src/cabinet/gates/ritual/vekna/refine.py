"""Refine the backlog: give every issue of yours a type and a size.

    vekna cast refine [--batch N]

An issue is a candidate when it is open, yours — opened by you or assigned to
you — and missing a type label, or missing a size label without being an
epic. Candidates go in pages of ``--batch``, lowest number first, and each page
is asked about before anything touches it: saying no moves on to the next page
rather than ending the cast.

One agent reads a page. It reads the ``issues`` skill once, on the first page,
and every page after continues the same session, so it keeps both the rules and
what it said about the pages before. It reaches the forge for nothing and edits
no files: what it hands back is a reading — a type, a size or the epic label,
the sub-issues an epic should be split into, and the links it found — and the
ritual is what puts that on the forge.

The issue bodies are somebody's words, so they go to the agent fenced as data,
the same as review threads.
"""

from vekna.folio.flow import decide
from vekna.lexicon import RitualError, Transition, done, emit_delta, goto, step

from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError, ForgeProtocol
from cabinet.pacts.issues import (
    Page,
    Pinning,
    Refined,
    RefinedItem,
    Refinement,
    Refining,
)
from cabinet.pacts.services import services

# One session for every page in the cast, so the skill is read once.
_THREAD = "refine"


# Ask the forge for your open issues and queue the unrefined ones.
@step
async def gather(refining: Refining) -> Transition:
    try:
        listed = await services().forge(refining.project).issues()
    except ForgeError as error:
        return goto(tally, refining.but(stopped=str(error)))
    return goto(
        leaf,
        refining.but(
            queue=services().backlog.unrefined(listed.issues),
            truncated=listed.truncated,
        ),
    )


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
    shown = services().report.page(page.issues)
    if not await decide(f"{shown}\nrefine these {len(page.issues)}?"):
        return goto(leaf, page.rowed("declined"))
    return goto(refine_page, page)


# The agent reads the page and says what each issue is.
@step
async def refine_page(page: Page) -> Transition:
    refining = page.refining
    project = refining.project
    prompt = services().prompts.refine(project, page.issues, briefed=refining.briefed)
    said = (
        await services()
        .agent(project)
        .ask_for(prompt, output=Refined, role="reader", key=_THREAD)
    )
    if isinstance(said, Fallen | Misread):
        return goto(tally, page.rowed("stopped").but(stopped=said.reason))
    # By the page's numbers, not the answer's: an issue it made up is not on
    # the page to be pinned, and one it skipped is named as missed by `pin`.
    wanted = {one.number for one in page.issues}
    kept = [item for item in said.items if item.number in wanted]
    return goto(pin, Pinning(page=page, items=kept))


# The labels and links one reading asks for, in the order the skill puts them
# on: the issue's own labels, then the parts it is split into — each opened,
# labelled and attached — then the open issues already under it, then what
# blocks it. Answers with the sub-issues opened, which only the forge knows.
async def _put(forge: ForgeProtocol, item: RefinedItem) -> list[int]:
    await forge.label_issue(item.number, add=item.wanted())
    opened: list[int] = []
    for part in item.parts:
        made = await forge.issue(part.title, part.body)
        await forge.label_issue(made.number, add=[part.kind, part.size])
        await forge.attach(item.number, made.number)
        opened.append(made.number)
    for child in item.children:
        await forge.attach(item.number, child)
    for blocker in item.blocked_by:
        await forge.blocks(item.number, blocker)
    return opened


# One page's rows, and what stopped the cast where something did. A forge that
# refuses mid-page stops it: what is already on is on, the issue in flight is
# named as half done, and so is everything after it that was never reached.
async def _pinned(pinning: Pinning) -> tuple[list[Refinement], str]:
    page = pinning.page
    forge = services().forge(page.refining.project)
    items = {item.number: item for item in pinning.items}
    rows: list[Refinement] = []
    for index, one in enumerate(page.issues):
        if (item := items.get(one.number)) is None:
            rows.append(Refinement(number=one.number, outcome="missed"))
            continue
        try:
            opened = await _put(forge, item)
        except ForgeError as error:
            left = page.issues[index:]
            rows += [
                Refinement(number=other.number, outcome="stopped") for other in left
            ]
            return rows, str(error)
        rows.append(
            Refinement(number=one.number, outcome="refined", item=item, opened=opened)
        )
    return rows, ""


# The forge writes, in one step of their own, apart from the agent's: the
# labels, the sub-issues and the links the reading asked for.
@step
async def pin(pinning: Pinning) -> Transition:
    rows, stopped = await _pinned(pinning)
    refining = pinning.page.refining.rowed(rows).but(briefed=True)
    if stopped:
        return goto(tally, refining.but(stopped=stopped))
    return goto(leaf, refining)


# Every ending comes here, so the report is owed however the cast ends.
@step
def tally(refining: Refining) -> Transition:
    emit_delta(services().report.refine(refining))
    if refining.stopped:
        raise RitualError(refining.stopped)
    return done(refining)
