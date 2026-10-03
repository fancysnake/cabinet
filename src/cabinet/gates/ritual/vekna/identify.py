"""Identify the backlog: give every issue of yours a type and a size.

    vekna cast identify [--batch N]

An issue is a candidate when it is open, yours — opened by you or assigned to
you — and missing a type label, or missing a size label without being an
epic. Candidates go in pages of ``--batch``, lowest number first, each shown
as it is taken up.

One agent reads a page. It reads the ``issues`` skill once, on the first page,
and every page after continues the same session, so it keeps both the rules and
what it said about the pages before. It reaches the forge for nothing and edits
no files: what it hands back is a reading — a type, a size or the epic label,
the sub-issues an epic should be split into, and the links it found — and the
ritual is what puts that on the forge. A write the forge refuses is named on
its issue's row, and the cast goes on.

The issue bodies are somebody's words, so they go to the agent fenced as data,
the same as review threads.
"""

from collections.abc import Awaitable

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


# Take the next page.
@step
def leaf(identifying: Leaf) -> Tally | Page:
    if not identifying.queue:
        return identifying.to(Tally)
    batch = identifying.batch
    page = Page(
        identifying=identifying.but(queue=identifying.queue[batch:]),
        issues=identifying.queue[:batch],
    )
    emit_delta(services().report.page(page.issues))
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


# One write; what the forge said, if it refused, goes in `refused`.
async def _tried(write: Awaitable[None], refused: list[str]) -> None:
    try:
        await write
    except ForgeError as error:
        refused.append(str(error))


# The labels and links one reading asks for, in the order the skill puts them
# on: the issue's own labels, then the parts it is split into — each opened,
# labelled and attached — then the open issues already under it, then what
# blocks it. No write waits on another but a part's label and attach on the
# part being opened, so a refused one is named and the rest still go on.
async def _put(forge: ForgeProtocol, item: IdentifiedItem) -> Identification:
    opened: list[int] = []
    refused: list[str] = []
    await _tried(forge.label_issue(item.number, add=item.wanted()), refused)
    for part in item.parts:
        try:
            made = await forge.issue(part.title, part.body)
        except ForgeError as error:
            refused.append(str(error))
            continue
        opened.append(made.number)
        await _tried(
            forge.label_issue(made.number, add=[part.kind, part.size]), refused
        )
        await _tried(forge.attach(item.number, made.number), refused)
    for child in item.children:
        await _tried(forge.attach(item.number, child), refused)
    for blocker in item.blocked_by:
        await _tried(forge.blocks(item.number, blocker), refused)
    return Identification(
        number=item.number,
        outcome="identified",
        item=item,
        opened=opened,
        refused=refused,
    )


# The forge writes, in one step of their own, apart from the agent's: the
# labels, the sub-issues and the links the reading asked for.
@step
async def pin(pinning: Pinning) -> Leaf:
    page = pinning.page
    forge = services().forge(page.identifying.project)
    items = {item.number: item for item in pinning.items}
    rows = [
        (
            Identification(number=one.number, outcome="missed")
            if (item := items.get(one.number)) is None
            else await _put(forge, item)
        )
        for one in page.issues
    ]
    return page.identifying.rowed(rows).but(briefed=True).to(Leaf)


# Every ending comes here, so the report is owed however the cast ends.
@step
def tally(identifying: Tally) -> Done[Identifying]:
    emit_delta(services().report.identify(identifying))
    if identifying.stopped:
        raise RitualError(identifying.stopped)
    return Done(identifying.to(Identifying))
