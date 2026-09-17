"""GitHub through `gh`."""

import shlex
from typing import TYPE_CHECKING, override

from pydantic import (
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
)
from vekna.folio.shell import ShellResult, shell

from cabinet.pacts.forge import ForgeError, ForgeProtocol
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Thread

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cabinet.pacts.project import LabelSpec

# `labels` rides along so the wait label can be read without a call per pull
# request: the listing is the only place every open branch is in hand at once.
_LIST = (
    "gh pr list --author @me --state open "
    "--json number,title,headRefName,baseRefName,url,updatedAt,labels"
)

# The endpoint pages at thirty by default and a board can run to twenty-odd,
# so the default is two workflows away from silently dropping the check the
# answer turns on. The branch as the ref rather than a sha, so this asks about
# the head the branch has now. `filter=latest` is the endpoint's own default,
# so a re-run's earlier attempt is never the answer.
_BOARD = "repos/{{owner}}/{{repo}}/commits/{branch}/check-runs?per_page=100"

# GraphQL rather than `pulls/<number>/comments`, because the REST endpoint
# carries no resolution state: it answers a settled thread and a live one
# identically, and a cast that cannot tell them apart works twice. Both ids
# ride along: the reply endpoint takes `databaseId`, the mutation takes `id`.
_THREADS = """\
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) { nodes {
        id isResolved path line
        comments(first: 50) { nodes { databaseId author { login } body } } } } } } }"""

_RESOLVE = """\
mutation($id: ID!) {
  resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }"""

_PASSED = "success"


class _Label(BaseModel):
    name: str


class _Labels(BaseModel):
    labels: list[_Label]


# Aliased rather than renamed downstream: `gh --json` picks the spelling, and
# one mapping here beats camelCase running through every step.
# `populate_by_name` is not for any caller: without it mypy's pydantic plugin
# cannot name the aliased field in the generated `__init__` and falls back to
# `**kwargs: Any`, which this project refuses.
class _Pull(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    number: int
    title: str
    url: str
    branch: str = Field(alias="headRefName")
    base: str = Field(alias="baseRefName")
    updated_at: str = Field(alias="updatedAt")
    labels: list[_Label] = []


class _Check(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    # Null while a run is still going.
    conclusion: str | None = None
    title: str | None = Field(
        default=None, validation_alias=AliasPath("output", "title")
    )


# The endpoint wraps the board in one key, and it stays wrapped until it is
# parsed: unwrapping with `--jq` would move the reading into the command.
class _Board(BaseModel):
    total_count: int = 0
    check_runs: list[_Check] = []


class _Author(BaseModel):
    login: str = ""


class _Comment(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int = Field(alias="databaseId")
    author: _Author | None = None
    body: str = ""


class _Comments(BaseModel):
    nodes: list[_Comment] = []


class _Thread(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    resolved: bool = Field(alias="isResolved")
    path: str | None = None
    line: int | None = None
    comments: _Comments = _Comments()


class _ThreadNodes(BaseModel):
    nodes: list[_Thread] = []


class _Threads(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    threads: _ThreadNodes = Field(
        default=_ThreadNodes(),
        validation_alias=AliasPath(
            "data", "repository", "pullRequest", "reviewThreads"
        ),
    )


_PULLS: TypeAdapter[list[_Pull]] = TypeAdapter(list[_Pull])


def _quoted(value: str) -> str:
    return shlex.quote(value)


def _said(result: ShellResult) -> str:
    parts = (result.stdout.strip(), result.stderr.strip())
    return "\n".join(part for part in parts if part) or f"exit code {result.exit_code}"


async def _asked(command: str, complaint: str) -> str:
    result = await shell(command, stream=False)
    if result.exit_code:
        msg = f"{complaint}: {_said(result)}"
        raise ForgeError(msg)
    return result.stdout


# `gh` knows which repository this is, but graphql variables are not a REST
# path and nothing fills an `{owner}` in for them — so the slug is asked for
# once and split by the shell rather than by a second call.
def _graphql(query: str, *variables: str) -> str:
    extra = "".join(f" {part}" for part in variables)
    return (
        'slug="$(gh repo view --json nameWithOwner -q .nameWithOwner)" && '
        f"gh api graphql -f query={_quoted(query)}"
        f' -f owner="${{slug%/*}}" -f repo="${{slug#*/}}"{extra}'
    )


def _pull(found: _Pull) -> PullRequest:
    return PullRequest(
        number=found.number,
        title=found.title,
        url=found.url,
        branch=found.branch,
        base=found.base,
        updated_at=found.updated_at,
        labels=[label.name for label in found.labels],
    )


def _check(found: _Check) -> Check:
    passed = None if found.conclusion is None else found.conclusion == _PASSED
    return Check(name=found.name, passed=passed, title=found.title or "")


def _thread(found: _Thread) -> Thread:
    return Thread(
        id=found.id,
        resolved=found.resolved,
        path=found.path or "",
        line=found.line,
        comments=[
            Comment(
                id=str(comment.id),
                author=comment.author.login if comment.author else "",
                body=comment.body,
            )
            for comment in found.comments.nodes
        ],
    )


class GithubForge(ForgeProtocol):
    @override
    async def pulls(self) -> list[PullRequest]:
        listed = await _asked(_LIST, "gh could not list your pull requests")
        try:
            return [_pull(found) for found in _PULLS.validate_json(listed)]
        except ValidationError as error:
            msg = f"gh returned something unreadable: {error}"
            raise ForgeError(msg) from error

    @override
    async def labels(self, number: int) -> list[str]:
        seen = await _asked(
            f"gh pr view {number} --json labels", "gh could not read the labels"
        )
        try:
            return [label.name for label in _Labels.model_validate_json(seen).labels]
        except ValidationError as error:
            msg = f"gh returned labels this could not read: {error}"
            raise ForgeError(msg) from error

    # Idempotent on gh's side, so a branch that already carries a label costs
    # one call and no complaint.
    @override
    async def label(
        self, number: int, *, add: Sequence[str] = (), remove: Sequence[str] = ()
    ) -> None:
        flags = [f"--add-label {_quoted(one)}" for one in add]
        flags += [f"--remove-label {_quoted(one)}" for one in remove]
        if not flags:
            return
        await _asked(
            f"gh pr edit {number} {' '.join(flags)}", f"could not label #{number}"
        )

    @override
    async def threads(self, number: int) -> list[Thread]:
        answered = await _asked(
            _graphql(_THREADS, f"-F number={number}"), "gh could not read the threads"
        )
        try:
            found = _Threads.model_validate_json(answered)
        except ValidationError as error:
            msg = f"gh returned threads this could not read: {error}"
            raise ForgeError(msg) from error
        return [_thread(node) for node in found.threads.nodes]

    # The path without the number answers 404, and the reply goes under the
    # thread's first comment: that is the one the REST id names a thread by.
    @override
    async def reply(self, number: int, thread: Thread, body: str) -> None:
        if not thread.comments:
            msg = f"thread {thread.id} has no comment to reply under"
            raise ForgeError(msg)
        first = thread.comments[0].id
        await _asked(
            f"gh api repos/{{owner}}/{{repo}}/pulls/{number}/comments/{first}/replies"
            f" -f body={_quoted(body)}",
            f"could not reply on thread {thread.id}",
        )

    @override
    async def resolve(self, number: int, thread: Thread) -> None:
        await _asked(
            _graphql(_RESOLVE, f"-f id={_quoted(thread.id)}"),
            f"could not resolve thread {thread.id}",
        )

    @override
    async def board(self, branch: str) -> Board:
        path = _BOARD.format(branch=branch)
        answered = await _asked(
            f"gh api {_quoted(path)}", "gh could not read the check board"
        )
        try:
            found = _Board.model_validate_json(answered)
        except ValidationError as error:
            msg = f"gh returned a board this could not read: {error}"
            raise ForgeError(msg) from error
        return Board(
            checks=[_check(check) for check in found.check_runs],
            truncated=len(found.check_runs) < found.total_count,
        )

    # The line has to be one this pull request's diff touches, or the API
    # answers 422. When it does, and for an item about the change as a whole,
    # the item goes on as a plain comment: losing the anchor is fine, losing
    # the item is not.
    @override
    async def comment(self, number: int, finding: Finding) -> None:
        if finding.line is not None:
            head = await _asked(
                f"gh pr view {number} --json headRefOid -q .headRefOid",
                "gh could not read the head commit",
            )
            anchored = await shell(
                f"gh api repos/{{owner}}/{{repo}}/pulls/{number}/comments"
                f" -f commit_id={_quoted(head.strip())}"
                f" -f path={_quoted(finding.path)} -F line={finding.line}"
                f" -f side=RIGHT -f body={_quoted(finding.body)}",
                stream=False,
            )
            if anchored.exit_code == 0:
                return
        await _asked(
            f"gh pr comment {number} --body {_quoted(finding.body)}",
            f"could not comment on #{number}",
        )

    @override
    async def issue(self, title: str, body: str) -> str:
        made = await _asked(
            f"gh issue create --title {_quoted(title)} --body {_quoted(body)}",
            "could not open the issue",
        )
        return made.strip()

    # `--force` updates a label that is already there instead of refusing it,
    # which is what makes the ritual safe to cast again.
    @override
    async def ensure_label(self, spec: LabelSpec) -> None:
        await _asked(
            f"gh label create {_quoted(spec.name)} --color {_quoted(spec.color)}"
            f" --description {_quoted(spec.description)} --force",
            f"could not create the label {spec.name}",
        )
