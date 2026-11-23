"""The agent a heal step asks, and the session it asks in."""

from cabinet.pacts.agent import AgentProtocol, Fallen, Prompt
from cabinet.pacts.healing import Work
from cabinet.pacts.services import services


# The agent session `name` names on this branch. Built here and nowhere else:
# a step that opens a session and the loop that continues it must agree.
def session(work: Work, name: str) -> str:
    return f"{name}-{work.pr.number}"


# The agent for `work`, on the cast's project and attendance.
def agent_for(work: Work) -> AgentProtocol:
    return services().agent(work.run.project, attended=work.run.attended)


# A repair, in the session `key` names on this branch: every round of a loop
# continues the one before it, on the stronger model where `escalated`.
async def asked(
    work: Work, prompt: Prompt, *, key: str, escalated: bool
) -> Fallen | None:
    return await agent_for(work).ask(
        prompt, job="fix", key=session(work, key), escalated=escalated
    )
