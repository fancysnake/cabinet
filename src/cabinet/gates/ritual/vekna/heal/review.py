"""The review task: the quality review posted as inline comments."""

from vekna.lexicon import step

from cabinet.gates.ritual.vekna.heal.agents import agent_for, session
from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.heal import Chart, QualityReview, SetAside, Tend
from cabinet.pacts.project import Project
from cabinet.pacts.services import services
from cabinet.pacts.threads import Finding, Findings


# Post the review and label the branch: the one task with no budget and no
# loop, because there is nothing here to retry against. An answer in the wrong
# shape sets the branch aside before anything is labelled. A well-formed answer
# with no items is indistinguishable from a review that missed what was there,
# so the label goes on, and an empty review is yours to notice and ask for
# again by taking the label off. What the branch already said stays in the
# note: a stash or a failed push is still news when the review fails too.
@step
async def quality_review(work: QualityReview) -> Tend | SetAside | Chart:
    project = work.run.project
    number = work.pr.number
    try:
        threads = await services().forge(project).threads(number)
    except ForgeError as error:
        return work.noting(str(error)).to(SetAside)
    prompt = services().prompts.review(
        project, base=work.base_ref, threads=threads, reason=work.reason
    )
    read = await agent_for(work).ask_for(
        prompt, output=Findings, job="review", key=session(work, "review")
    )
    if isinstance(read, Fallen):
        return work.abandoned(read.reason).to(Chart)
    if isinstance(read, Misread):
        return work.noting(read.reason).to(SetAside)
    findings = services().report.findings(project, read.items)
    if note := await _put_up(project, number, findings):
        return work.noting(note).to(SetAside)
    return work.to(Tend)


# Put every item up, label the branch, and say what did not happen. A posting
# that got partway still earns the label: what is up cannot be taken down, and
# an unlabelled branch is one the next cast reviews again, saying all of it a
# second time. Only a posting that got nowhere is left unlabelled — an empty
# review is labelled, for the reason above `quality_review`.
async def _put_up(project: Project, number: int, findings: list[Finding]) -> str:
    forge = services().forge(project)
    posted = await forge.comment(number, findings)
    if posted.count or not posted.stopped:
        try:
            await forge.label(number, add=[project.labels.reviewed])
        except ForgeError as error:
            return str(error)
    if not posted.stopped:
        return ""
    return f"{posted.count} of {len(findings)} review items went up: {posted.stopped}"
