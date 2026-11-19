"""The guide task: the smoke-test guide posted as a comment."""

from vekna.lexicon import step

from cabinet.gates.ritual.vekna.heal.agents import agent_for, session
from cabinet.pacts.agent import Fallen, Misread
from cabinet.pacts.forge import ForgeError
from cabinet.pacts.guide import GUIDE_MARK, Guide
from cabinet.pacts.heal import Chart, PostGuide, SetAside, Tend
from cabinet.pacts.services import services


# Post the smoke-test guide and label the branch: like the review, no budget
# and no loop. The comment goes up before the label, so a label the forge
# refuses leaves a guide the next cast edits rather than posts again.
@step
async def post_guide(work: PostGuide) -> Tend | SetAside | Chart:
    project = work.run.project
    number = work.pr.number
    read = await agent_for(work).ask_for(
        services().prompts.guide(project, base=work.base_ref),
        output=Guide,
        job="doc",
        key=session(work, "guide"),
    )
    if isinstance(read, Fallen):
        return work.abandoned(read.reason).to(Chart)
    if isinstance(read, Misread):
        return work.noting(read.reason).to(SetAside)
    forge = services().forge(project)
    try:
        await forge.note(number, read.body, marker=GUIDE_MARK)
        await forge.label(number, add=[project.labels.qa])
    except ForgeError as error:
        return work.noting(str(error)).to(SetAside)
    return work.to(Tend)
