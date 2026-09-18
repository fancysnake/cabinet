"""Review threads as the forge holds them, and what the agents make of them."""

from typing import Literal

from pydantic import BaseModel


class Comment(BaseModel):
    # Whatever the forge needs to reply under it: a REST id on GitHub, a note id
    # on GitLab. Opaque to everything but the adapter that made it.
    id: str
    author: str
    body: str


class Thread(BaseModel):
    # Whatever the forge needs to settle it: a graphql node id on GitHub, a
    # discussion id on GitLab. Carried through the triage so the round that
    # answers an item addresses the thread the item is about.
    id: str
    resolved: bool
    path: str = ""
    line: int | None = None
    comments: list[Comment] = []


Priority = Literal["p1", "p2", "p3", "p4"]
Action = Literal["fix", "reject", "file"]


class TriageItem(BaseModel):
    where: str
    # What the thread itself asked for, in one line. Without it the decision is
    # taken on the reading's verdict alone, with no sight of the comment
    # behind it.
    raised: str
    what: str
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
