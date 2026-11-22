"""The answer task: open review threads triaged, answered and settled.

Attended only: an unattended cast leaves the threads for you and says how many
wait. First whatever an earlier cast's forge failure left half-settled is
finished. Then the open threads go in batches of ``--batch``: an agent reads
them against the code into a triage, you answer each item in your own words
(saying nothing takes the reading's proposal), and another agent fixes what
you said to fix and drafts every reply, each put to you first where the
project sets ``approve_replies``. The ritual opens the issues you said to
file, posts the replies and settles the threads, and reads what is still
open for the next round, up to three. A thread somebody else opened is
settled by the reply and left for them to resolve. What the answers changed goes through
the gate and is committed. A round that finds nothing open puts the answered
label on; the next answer task takes it off before it starts. Attended, the
review threads are put to you, the one question a cast asks.
"""

from vekna.folio.flow import decide
from vekna.lexicon import emit_delta, step

from cabinet.gates.ritual.vekna.heal.agents import agent_for, session
from cabinet.gates.ritual.vekna.heal.repair import repaired
from cabinet.pacts.agent import UNTRUSTED_THREADS, Fallen, Misread
from cabinet.pacts.budgets import ROUNDS
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import (
    AnswerGate,
    AnswerThreads,
    ApproveReplies,
    AskTriage,
    Chart,
    LandAnswers,
    PostAnswers,
    ReadThreads,
    SetAside,
    SettleLeft,
    StandDown,
    Tend,
)
from cabinet.pacts.healing import Work
from cabinet.pacts.issues import Listing
from cabinet.pacts.project import CiJob, Project
from cabinet.pacts.scm import ScmError
from cabinet.pacts.services import services
from cabinet.pacts.threads import (
    Answer,
    Answered,
    Finding,
    Thread,
    Told,
    TriageNotes,
    filed_as,
    filed_for,
    settles,
    signed,
)


async def _unsettled(project: Project, number: int) -> list[Thread]:
    threads = await services().forge(project).threads(number)
    return [thread for thread in threads if thread.waits(project.bots)]


# The ritual's reply under a thread, then the thread settled: in that order,
# so a forge that fails between them leaves the mark `settle_left` reads. A
# thread somebody else opened is theirs to resolve, and the reply is all it
# gets. A plain item has no thread to reply under or resolve: a plain comment
# naming it is both, and `comment` reports a failure instead of raising it.
async def _settled(project: Project, number: int, thread: Thread, reply: str) -> None:
    forge = services().forge(project)
    if not thread.plain:
        await forge.reply(number, thread, signed(reply))
        if thread.closable(project.bots):
            await forge.resolve(number, thread)
        return
    naming = f"{reply}\n\nSettles {thread.id}\n\n{settles(thread.id)}"
    posted = await forge.comment(number, [Finding(path="", body=signed(naming))])
    if posted.stopped:
        raise ForgeError(posted.stopped)


def _filed(url: str) -> str:
    return f"Filed as {url}"


# Whether the ritual already named the issue under the thread. Its own line,
# so `issues/9` is not found inside `issues/91`.
def _named(thread: Thread, url: str) -> bool:
    return any(
        _filed(url) in one.body.splitlines() for one in thread.comments if one.mine
    )


# Settle what an earlier round left half done, and say how many threads that
# was. A thread the reply naming its issue already sits under has been
# answered once: what came after is read again, not answered twice.
async def _finished(
    project: Project, number: int, threads: list[Thread], listing: Listing
) -> int:
    forge = services().forge(project)
    answered = [thread for thread in threads if thread.answered]
    unanswered = [thread for thread in threads if not thread.answered]
    filed = [
        (thread, issue)
        for thread in unanswered
        if (issue := filed_as(listing.issues, thread.id)) is not None
        and not _named(thread, issue.url)
    ]
    closing = [thread for thread in answered if thread.closable(project.bots)]
    for thread in closing:
        await forge.resolve(number, thread)
    for thread, issue in filed:
        await _settled(project, number, thread, _filed(issue.url))
    return len(closing) + len(filed)


# Finish a round an earlier cast's forge failure cut short, before anything is
# read: a thread whose last word is the ritual's reply only wants settling,
# and one an open issue was filed for wants the reply naming it. A backlog the
# forge would not list whole may hide the issue filed for a thread, and
# reading that thread again would file it twice, so the task ends there. A
# branch still wearing the answered label from an earlier cast has threads
# open again, so the label comes off first.
@step
async def settle_left(work: SettleLeft) -> ReadThreads | Tend:
    project = work.run.project
    forge = services().forge(project)
    answered = project.labels.answered
    try:
        if work.pr.wears(answered):
            await forge.label(work.pr.number, remove=[answered])
        threads = await _unsettled(project, work.pr.number)
        # Only a thread with no reply yet can have an issue filed for it.
        unanswered = any(not thread.answered for thread in threads)
        listing = (
            services().backlog.merged(await forge.issues()) if unanswered else Listing()
        )
    except ForgeError as error:
        return work.noting(str(error)).to(Tend)
    if listing.truncated:
        note = (
            "the forge would not list every open issue, so an issue filed for"
            " an open thread may be missing from it"
        )
        return work.noting(note).to(Tend)
    try:
        done = await _finished(project, work.pr.number, threads, listing)
    except ForgeError as error:
        return work.noting(str(error)).to(Tend)
    if done:
        emit_delta(f"{work.pr.branch}: settled {done} threads an earlier cast left")
    return work.to(ReadThreads)


# Where a round finds nothing more to do. A branch the writer has worked on
# goes to the gate with whatever it changed, and a branch it never touched, or
# touched without changing a file, has nothing to land.
async def _landing(work: Work, note: str = "") -> Tend | AnswerGate | SetAside:
    work = work.noting(note)
    if not work.spent(answer_threads.name):
        return work.to(Tend)
    try:
        dirty = await services().scm(work.run.project).status()
    except ScmError as error:
        return work.noting(str(error)).to(SetAside)
    return work.to(AnswerGate) if dirty else work.to(Tend)


# The next batch of open threads, saying how many it leaves for later; none
# once the rounds are spent, without asking the forge. A forge with none open
# is the task done, and the branch wears the answered label for it. Beside the
# batch, how many threads are open in all.
async def _batch(work: Work) -> tuple[list[Thread], int]:
    if work.spent(read_threads.name) >= ROUNDS:
        return [], 0
    project = work.run.project
    if not (threads := await _unsettled(project, work.pr.number)):
        await services().forge(project).label(
            work.pr.number, add=[project.labels.answered]
        )
    batch = threads[: work.run.batch]
    if len(batch) < len(threads):
        emit_delta(
            f"{work.pr.branch}: {len(threads)} threads open,"
            f" reading {len(batch)} of them"
        )
    return batch, len(threads)


# Read the next batch of open threads into a triage. Read again after every
# round: an item is triaged against the code as it stands, and a thread the
# last round settled is no longer open.
@step
async def read_threads(
    work: ReadThreads,
) -> AskTriage | Tend | AnswerGate | SetAside | Chart:
    try:
        batch, unsettled = await _batch(work)
    except ForgeError as error:
        return await _landing(work, str(error))
    if not batch:
        return await _landing(work)
    read = await agent_for(work, UNTRUSTED_THREADS).ask_for(
        services().prompts.triage_read(work.pr.number, batch),
        output=TriageNotes,
        job="plan",
    )
    if isinstance(read, Fallen):
        return work.abandoned(read.reason).to(Chart)
    if isinstance(read, Misread):
        return await _landing(work, read.reason)
    # The reading is the agent's output: an item for a thread that was not
    # sent is made up, and is dropped.
    sent = {thread.id for thread in batch}
    # The forge said a thread was open, so an empty reading is the reading
    # disagreeing with the forge rather than a branch with nothing to do.
    if not (items := [item for item in read.items if item.thread in sent]):
        return await _landing(
            work, "the reading found nothing, but the forge says otherwise"
        )
    return AskTriage(
        work=work.charged(read_threads.name),
        items=items,
        threads=batch,
        unsettled=unsettled,
    )


# Put the triage on your terminal, a card at a time, and take your answer to
# each.
@step
async def ask_triage(triage: AskTriage) -> AnswerThreads:
    work = triage.work
    report = services().report
    told: list[Told] = []
    for item, card in report.cards(work.pr, triage.items, triage.threads):
        # Free text and not a choice: an item is answered by saying how the
        # thing is supposed to work, which no four options carry. An empty
        # answer agrees with the reading's own proposal.
        said = await decide(report.asked(card), free=True)
        told.append(
            Told(
                thread=item.thread,
                card=card,
                said=said or f"{item.action} it, as the reading says",
            )
        )
    prompt = services().prompts.triage_work(work.pr.number, told)
    triaged = {one.thread for one in told}
    threads = [thread for thread in triage.threads if thread.id in triaged]
    return AnswerThreads(
        work=work, prompt=prompt, threads=threads, unsettled=triage.unsettled
    )


# The agent edits code and drafts every reply; it reaches the forge for
# nothing, so what it hands back is posted by the step after this one. Straight
# in, with nothing asked: the triage was answered item by item a step ago. The
# gate's repairs continue the same session, so they meet an agent that
# remembers what it changed and why.
@step
async def answer_threads(
    instructed: AnswerThreads,
) -> PostAnswers | ApproveReplies | Tend | AnswerGate | SetAside | Chart:
    work = instructed.work.charged(answer_threads.name)
    came = await agent_for(work, UNTRUSTED_THREADS).ask_for(
        instructed.prompt,
        output=Answered,
        job="fix",
        key=session(work, answer_gate.name),
        escalated=services().sizes.escalates(threads=instructed.unsettled),
    )
    if isinstance(came, Fallen):
        return work.abandoned(came.reason).to(Chart)
    if isinstance(came, Misread):
        return await _landing(work, came.reason)
    if work.run.project.approve_replies:
        return ApproveReplies(work=work, drafts=came.items, threads=instructed.threads)
    return PostAnswers(work=work, items=came.items, threads=instructed.threads)


# One draft sent back to the session that wrote it, with what you want changed.
# A redraft in the wrong shape leaves the draft as it was, to be asked about
# again. The thread is the ritual's to know: a redraft cannot move the reply
# under another one.
async def _redrafted(work: Work, draft: Answer, said: str) -> Answer | Fallen:
    came = await agent_for(work, UNTRUSTED_THREADS).ask_for(
        services().prompts.redraft(draft, said),
        output=Answer,
        job="fix",
        key=session(work, answer_gate.name),
    )
    if isinstance(came, Fallen):
        return came
    if isinstance(came, Misread):
        emit_delta(came.reason)
        return draft
    return Answer(thread=draft.thread, reply=came.reply, issue=came.issue)


# Every drafted reply put to you before any is posted, where the project asks
# for it: return takes it, and anything else is what to change. What you
# changed is redrafted and comes back here, up to `--bound` times, because the
# worst a branch can spend has to be a number. Past that, a reply you still
# would not take is not posted: its thread stays open for the next round. An
# answer to a thread nobody triaged is passed on unasked, for `post_answers`
# to say and skip.
@step
async def approve_replies(
    drafted: ApproveReplies,
) -> PostAnswers | ApproveReplies | Chart:
    work = drafted.work
    report = services().report
    threads = {thread.id: thread for thread in drafted.threads}
    last = work.exhausted(approve_replies.name)
    taken = list(drafted.items)
    taken += [draft for draft in drafted.drafts if draft.thread not in threads]
    again: list[Answer] = []
    for draft in (draft for draft in drafted.drafts if draft.thread in threads):
        card = report.drafted(work.pr, threads[draft.thread], draft, last=last)
        if not (said := await decide(card, free=True)):
            taken.append(draft)
        elif last:
            emit_delta(
                f"no redrafts left at this --bound: thread {draft.thread} gets no"
                " reply and stays open"
            )
        else:
            redraft = await _redrafted(work, draft, said)
            if isinstance(redraft, Fallen):
                return work.abandoned(redraft.reason).to(Chart)
            again.append(redraft)
    if again:
        return ApproveReplies(
            work=work.charged(approve_replies.name),
            drafts=again,
            items=taken,
            threads=drafted.threads,
        )
    return PostAnswers(
        work=work.cleared(approve_replies.name), items=taken, threads=drafted.threads
    )


# An issue is opened before the reply that names it, and a thread is settled
# after the reply that answers it; both carry a mark `settle_left` reads back
# when the forge fails between them. A thread the agent invented is said and
# skipped; a thread it left unanswered stays open, and the next round reads it
# again. Answers with how many threads were settled.
async def _posted(answering: PostAnswers) -> int:
    work = answering.work
    number = work.pr.number
    project = work.run.project
    forge = services().forge(project)
    threads = {thread.id: thread for thread in answering.threads}
    settled = 0
    for item in answering.items:
        if item.thread not in threads:
            emit_delta(f"the agent answered a thread nobody triaged: {item.thread}")
            continue
        reply = item.reply
        if item.issue is not None:
            body = f"{item.issue.body}\n\n{filed_for(item.thread)}"
            opened = await forge.issue(item.issue.title, body)
            reply = f"{reply}\n\n{_filed(opened.url)}"
        await _settled(project, number, threads[item.thread], reply)
        settled += 1
    return settled


# The forge writes, in a step of their own, apart from the agent's. Round
# again rather than straight to the gate: what the forge still holds open is
# the next batch, and `read_threads` is what finds out there is none. A round
# that settled nothing would read the same batch back, so it lands with
# whatever the agent did change, and so does a forge that refused partway:
# the fixes are real whether or not every reply went up.
@step
async def post_answers(
    answering: PostAnswers,
) -> ReadThreads | Tend | AnswerGate | SetAside:
    work = answering.work
    try:
        settled = await _posted(answering)
    except ForgeError as error:
        return await _landing(work, str(error))
    if not settled:
        return await _landing(work)
    return work.to(ReadThreads)


# The gate over what the answers changed, repaired until it is green: the
# merge's loop, in the session the answers were written in.
@step
async def answer_gate(work: AnswerGate) -> AnswerGate | LandAnswers | StandDown | Chart:
    against = CiJob(gate=work.run.project.gate)
    return await repaired(work, against, name=answer_gate.name, then=LandAnswers)


@step
async def land_answers(work: LandAnswers) -> Tend | SetAside:
    try:
        await services().scm(work.run.project).commit("chore: act on the review triage")
    except ScmError as error:
        return work.noting(f"could not commit the answers: {error}").to(SetAside)
    return work.committed().to(Tend)
