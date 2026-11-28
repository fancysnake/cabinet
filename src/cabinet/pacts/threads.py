"""Review threads as the forge holds them, and what the agents make of them."""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel

from cabinet.pacts.issues import Issue


class Comment(BaseModel):
    # Whatever the forge needs to reply under it: a REST id on GitHub, a note id
    # on GitLab. Opaque to everything but the adapter that made it.
    id: str
    author: str
    body: str
    # Written by whoever the forge's client is logged in as.
    mine: bool = False
    # Written by an app, where the forge says so: GitHub does, GitLab does not.
    bot: bool = False


# Hidden in what `answer` posts, so the forge records how far a round got:
# a reply carrying it answered its thread, and an issue body naming a thread
# was filed for it.
ANSWERED = "<!-- cabinet:answered -->"


def signed(reply: str) -> str:
    return f"{reply}\n\n{ANSWERED}"


def filed_for(thread: str) -> str:
    return f"<!-- cabinet:thread {thread} -->"


# The open issue `answer` filed for a thread, where there is one. Only one
# you opened: an issue assigned to you carries whatever its author wrote.
def filed_as(issues: list[Issue], thread: str) -> Issue | None:
    mark = filed_for(thread)
    return next((one for one in issues if one.mine and mark in one.body), None)


class Thread(BaseModel):
    # Whatever the forge needs to settle it: a graphql node id on GitHub, a
    # discussion id on GitLab. Carried through the triage so the round that
    # answers an item addresses the thread the item is about.
    id: str
    resolved: bool
    path: str = ""
    line: int | None = None
    comments: list[Comment] = []
    # A plain comment standing as a thread: a review item the forge would not
    # anchor. The forge cannot resolve one, so `id` is the reference the reply
    # names it by, and that reply is what settles it.
    plain: bool = False

    # The last word, not any word: a reviewer answering the reply reopens
    # the conversation. And your word: anyone who can reply can write the
    # mark.
    @property
    def answered(self) -> bool:
        if not self.comments:
            return False
        last = self.comments[-1]
        return last.mine and ANSWERED in last.body

    # Who opened the thread: its first comment's author, empty where it has
    # none.
    @property
    def raised_by(self) -> str:
        return self.comments[0].author if self.comments else ""

    # Whether the ritual resolves it after replying: one you opened, or one
    # an app or one of `bots` did. A person resolves their own thread, having
    # read the reply.
    def closable(self, bots: Sequence[str]) -> bool:
        if not self.comments:
            return False
        first = self.comments[0]
        return first.mine or first.bot or first.author in bots

    # Whether `answer` still owes it anything. A thread the ritual leaves
    # open stops waiting once the ritual's reply is its last word.
    def waits(self, bots: Sequence[str]) -> bool:
        return not self.resolved and (self.closable(bots) or not self.answered)


# One plain comment on the pull request, outside every review thread.
class Remark(BaseModel):
    # What a reply names it by: its URL on both forges.
    ref: str
    author: str
    body: str
    mine: bool = False


# Hidden in every item the review posts, so a plain comment is known for one
# of its items, and in the reply that settles a plain item: a forge cannot
# resolve a plain comment, so that reply is the record.
ITEM = "<!-- cabinet:item -->"


def settles(ref: str) -> str:
    return f"<!-- cabinet:settles {ref} -->"


# The review items among the plain comments, as threads. Yours only, both the
# item and the reply settling it: anyone can type a mark. The mark ends in
# ` -->`, so one reference opening another (`…-12` and `…-123`) cannot match.
def remarked(remarks: Sequence[Remark]) -> list[Thread]:
    mine = [one for one in remarks if one.mine]
    return [
        Thread(
            id=one.ref,
            resolved=any(settles(one.ref) in other.body for other in mine),
            plain=True,
            comments=[Comment(id=one.ref, author=one.author, body=one.body, mine=True)],
        )
        for one in mine
        if ITEM in one.body
    ]


Priority = Literal["p1", "p2", "p3", "p4"]
Action = Literal["fix", "reject", "file"]
Grounds = Literal["tested", "read", "not checked"]
Size = Literal["small", "medium", "large"]
Risk = Literal["low", "medium", "high"]


class TriageItem(BaseModel):
    where: str
    # What the thread itself asked for, in one line. Without it the decision is
    # taken on the reading's verdict alone, with no sight of the comment
    # behind it.
    raised: str
    # What happens when nothing is done about the thread: the stake, which the
    # comment and the verdict both leave out.
    left: str
    # Why the reading would take its action.
    what: str
    # How the reading knows, and the run or the lines that show it: a verdict
    # nobody ran is worth less than one somebody did, and looks the same.
    grounds: Grounds
    # What was run, apart from `proof`: the card wraps prose at spaces and
    # cannot tell a command inside it. Empty when nothing was run.
    command: str
    proof: str
    # What the action costs.
    size: Size
    files: int
    risk: Risk
    # p4 is not a smaller p3: it is the thread that has no work in it at all —
    # already done, no longer true, or simply wrong — sorted out of the way so
    # the reading you go through is only the items worth a decision.
    priority: Priority
    # What the reading would do about it, which is what happens when you say
    # nothing: an item you agree with costs you a return key.
    action: Action
    thread: str


# What the reading agent returns, and no more: which branch this belongs to is
# the ritual's to know, not the agent's to repeat back.
class TriageNotes(BaseModel):
    items: list[TriageItem]


# One triaged thread as you went through it: the card you answered against and
# what you said.
class Told(BaseModel):
    thread: str
    card: str
    said: str


class IssueDraft(BaseModel):
    title: str
    body: str


# One answered thread: what to say under it, and the issue to open first where
# the answer was "file". The ritual posts, files and settles — the agent that
# wrote this could not, and that is the point.
class Answer(BaseModel):
    thread: str
    reply: str
    issue: IssueDraft | None = None


class Answered(BaseModel):
    items: list[Answer]


# One review action item, anchored to the code it is about. `line` is None for
# an item about the change as a whole.
class Finding(BaseModel):
    path: str
    line: int | None = None
    body: str


class Findings(BaseModel):
    items: list[Finding]


# What came of posting one review: how many items went up, and what stopped
# the posting where something did. A posting that got partway is a thing to
# act on rather than a thing to unwind — the comments are up, and nothing can
# take them down again.
class Posted(BaseModel):
    count: int
    stopped: str = ""
