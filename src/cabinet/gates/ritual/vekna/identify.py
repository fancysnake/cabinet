"""Identify the backlog: give every issue of yours a type and a size.

    vekna cast identify [--batch N]

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
from vekna.lexicon import Done, RitualError, emit_delta, step

from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError, ForgeProtocol
from cabinet.pacts.identify import Gather, Leaf, Tally
from cabinet.pacts.issues import (
    Identification,
    Identified,
    IdentifiedItem,
    Identifying,
    Page,
    Pinning,
)
from cabinet.pacts.services import services

# One session for every page in the cast, so the skill is read once.
_THREAD = "identify"


# Ask the forge for your open issues and queue the unidentified ones.
@step
async def gather(identifying: Gather) -> Tally | Leaf:
    try:
        listed = await services().forge(identifying.project).issues()
    except ForgeError as error:
        return identifying.but(stopped=str(error)).to(Tally)
    return identifying.but(
        queue=services().backlog.unidentified(listed.issues), truncated=listed.truncated
    ).to(Leaf)


# Take the next page, if you say so.
@step
async def leaf(identifying: Leaf) -> Tally | Leaf | Page:
    if not identifying.queue:
        return identifying.to(Tally)
    batch = identifying.batch
    page = Page(
        identifying=identifying.but(queue=identifying.queue[batch:]),
        issues=identifying.queue[:batch],
    )
    shown = services().report.page(page.issues)
    if not await decide(f"{shown}\nidentify these {len(page.issues)}?"):
        return page.rowed("declined").to(Leaf)
    return page


# The agent reads the page and says what each issue is.
@step
async def identify_page(page: Page) -> Tally | Pinning:
    identifying = page.identifying
    project = identifying.project
    prompt = services().prompts.identify(
        project, page.issues, briefed=identifying.briefed
    )
    said = (
        await services()
        .agent(project)
        .ask_for(prompt, output=Identified, role="reader", key=_THREAD)
    )
    if isinstance(said, Fallen | Misread):
        return page.rowed("stopped").but(stopped=said.reason).to(Tally)
    # By the page's numbers, not the answer's: an issue it made up is not on
    # the page to be pinned, and one it skipped is named as missed by `pin`.
    wanted = {one.number for one in page.issues}
    kept = [item for item in said.items if item.number in wanted]
    return Pinning(page=page, items=kept)


# The labels and links one reading asks for, in the order the skill puts them
# on: the issue's own labels, then the parts it is split into — each opened,
# labelled and attached — then the open issues already under it, then what
# blocks it. Each sub-issue goes into `opened` the moment the forge opens it,
# so one the forge fails on afterwards is still named rather than orphaned.
async def _put(forge: ForgeProtocol, item: IdentifiedItem, opened: list[int]) -> None:
    await forge.label_issue(item.number, add=item.wanted())
    for part in item.parts:
        made = await forge.issue(part.title, part.body)
        opened.append(made.number)
        await forge.label_issue(made.number, add=[part.kind, part.size])
        await forge.attach(item.number, made.number)
    for child in item.children:
        await forge.attach(item.number, child)
    for blocker in item.blocked_by:
        await forge.blocks(item.number, blocker)


# One page's rows, and what stopped the cast where something did. A forge that
# refuses mid-page stops it: what is already on is on, the issue in flight is
# named as half done, with the sub-issues it already opened, and so is
# everything after it that was never reached.
async def _pinned(pinning: Pinning) -> tuple[list[Identification], str]:
    page = pinning.page
    forge = services().forge(page.identifying.project)
    items = {item.number: item for item in pinning.items}
    rows: list[Identification] = []
    for index, one in enumerate(page.issues):
        if (item := items.get(one.number)) is None:
            rows.append(Identification(number=one.number, outcome="missed"))
            continue
        opened: list[int] = []
        try:
            await _put(forge, item, opened)
        except ForgeError as error:
            rows.append(
                Identification(number=one.number, outcome="stopped", opened=opened)
            )
            rows += [
                Identification(number=other.number, outcome="stopped")
                for other in page.issues[index + 1 :]
            ]
            return rows, str(error)
        rows.append(
            Identification(
                number=one.number, outcome="identified", item=item, opened=opened
            )
        )
    return rows, ""


# The forge writes, in one step of their own, apart from the agent's: the
# labels, the sub-issues and the links the reading asked for.
@step
async def pin(pinning: Pinning) -> Tally | Leaf:
    rows, stopped = await _pinned(pinning)
    identifying = pinning.page.identifying.rowed(rows).but(briefed=True)
    if stopped:
        return identifying.but(stopped=stopped).to(Tally)
    return identifying.to(Leaf)


# Every ending comes here, so the report is owed however the cast ends.
@step
def tally(identifying: Tally) -> Done[Identifying]:
    emit_delta(services().report.identify(identifying))
    if identifying.stopped:
        raise RitualError(identifying.stopped)
    return Done(identifying.to(Identifying))
