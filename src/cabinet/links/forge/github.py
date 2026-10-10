"""GitHub through `gh`."""

from collections.abc import Sequence

from pydantic import (
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
)
from typing_extensions import override
from vekna.folio.shell import shell

from cabinet.links.forge.asking import asked, quoted
from cabinet.pacts.forge import ForgeError, ForgeProtocol
from cabinet.pacts.issues import Issue, Listing, Opened
from cabinet.pacts.project import LabelSpec
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Posted, Thread

# `labels` rides along so the wait label can be read without a call per pull
# request: the listing is the only place every open branch is in hand at once.
# `--limit` because gh's own default is thirty, and a pull request that falls
# off the end of the listing is one no ritual ever sees. A hundred, which is
# what the GitLab adapter pages at.
_LIST = (
    "gh pr list --author @me --state open --limit 100 "
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
# Both connections are paged by cursor, the comments nested in each thread by
# a query of their own: a page is never taken for the whole answer.
_THREADS = """\
query($owner: String!, $repo: String!, $number: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewThreads(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved path line
          comments(first: 100) {
            pageInfo { hasNextPage endCursor }
            nodes { databaseId author { login } body viewerDidAuthor } } } } } } }"""

_COMMENTS = """\
query($id: ID!, $after: String) {
  node(id: $id) { ... on PullRequestReviewThread {
    comments(first: 100, after: $after) {
      pageInfo { hasNextPage endCursor }
      nodes { databaseId author { login } body viewerDidAuthor } } } } }"""

_RESOLVE = """\
mutation($id: ID!) {
  resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }"""

_PASSED = "success"

# Where a listing of issues stops. Twice what the GitLab adapter pages at,
# because gh takes a limit rather than a page size and the endpoint behind it
# allows more — but a cap is a cap, so a listing that comes back this long is
# reported as truncated rather than taken for the whole backlog.
_ISSUE_PAGE = 200

# Asked twice, once per way an issue can be yours: gh takes one of `--author`
# and `--assignee` per listing and ANDs them when given both.
_ISSUES = (
    f"gh issue list {{who}} @me --state open --limit {_ISSUE_PAGE} "
    "--json number,title,url,body,labels"
)

# A relationship endpoint takes the issue's database id, which is not the
# number anything else here names an issue by.
_ID = "repos/{{owner}}/{{repo}}/issues/{number} --jq .id"
_SUB_ISSUES = "repos/{{owner}}/{{repo}}/issues/{epic}/sub_issues"
_BLOCKED_BY = "repos/{{owner}}/{{repo}}/issues/{number}/dependencies/blocked_by"


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
    mine: bool = Field(default=False, alias="viewerDidAuthor")


# Required wherever a connection is read: without it a full page and the
# whole answer look the same.
class _Page(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    more: bool = Field(alias="hasNextPage")
    cursor: str | None = Field(default=None, alias="endCursor")


class _Comments(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: _Page = Field(alias="pageInfo")
    nodes: list[_Comment] = []


class _Thread(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    resolved: bool = Field(alias="isResolved")
    path: str | None = None
    line: int | None = None
    comments: _Comments


class _ThreadNodes(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    page: _Page = Field(alias="pageInfo")
    nodes: list[_Thread] = []


# Required, with no default standing in for a path that is not there: gh
# exits 0 on a `pullRequest: null` answer, which carries no GraphQL error, and
# a default would read that as a pull request with nothing raised on it — so
# the review would post as though the threads had never been written. An
# answer this cannot find the threads in is an answer this cannot read.
class _Threads(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    threads: _ThreadNodes = Field(
        validation_alias=AliasPath("data", "repository", "pullRequest", "reviewThreads")
    )


# Required for the reason `_Threads` is: a `node: null` answer is not a thread
# with nothing more said on it.
class _MoreComments(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    comments: _Comments = Field(validation_alias=AliasPath("data", "node", "comments"))


class _Issue(BaseModel):
    number: int
    title: str
    url: str
    body: str = ""
    labels: list[_Label] = []


# The REST answer to opening one, which spells its URL the API's way.
class _Opened(BaseModel):
    number: int
    html_url: str


_PULLS: TypeAdapter[list[_Pull]] = TypeAdapter(list[_Pull])
_ISSUE_LIST: TypeAdapter[list[_Issue]] = TypeAdapter(list[_Issue])


# `gh` knows which repository this is, but graphql variables are not a REST
# path and nothing fills an `{owner}` in for them — so the slug is asked for
# once and split by the shell rather than by a second call.
def _graphql(query: str, *variables: str) -> str:
    extra = "".join(f" {part}" for part in variables)
    return (
        'slug="$(gh repo view --json nameWithOwner -q .nameWithOwner)" && '
        f"gh api graphql -f query={quoted(query)}"
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


# Asked once for a whole review rather than once per item: every anchored
# comment on one pull request is anchored to the same head. Empty where no
# item wants an anchor, and where gh would not say — an item then goes up
# plainly, which is the same bargain a refused anchor makes.
async def _head(number: int, findings: Sequence[Finding]) -> str:
    if all(finding.line is None for finding in findings):
        return ""
    try:
        head = await asked(
            f"gh pr view {number} --json headRefOid -q .headRefOid",
            "gh could not read the head commit",
        )
    except ForgeError:
        return ""
    return head.strip()


# The line has to be one this pull request's diff touches, or the API answers
# 422. When it does, and for an item about the change as a whole, the item
# goes on as a plain comment: losing the anchor is fine, losing the item is
# not. What comes back is what stopped it, or nothing.
async def _one(number: int, finding: Finding, *, head: str) -> str:
    if finding.line is not None and head:
        anchored = await shell(
            f"gh api repos/{{owner}}/{{repo}}/pulls/{number}/comments"
            f" -f commit_id={quoted(head)}"
            f" -f path={quoted(finding.path)} -F line={finding.line}"
            f" -f side=RIGHT -f body={quoted(finding.body)}",
            stream=False,
        )
        if anchored.exit_code == 0:
            return ""
    try:
        await asked(
            f"gh pr comment {number} --body {quoted(finding.body)}",
            f"could not comment on #{number}",
        )
    except ForgeError as error:
        return str(error)
    return ""


# One extra call per relationship, and there is no avoiding it: the listing
# carries numbers, the endpoints take ids, and nothing maps one to the other
# but asking.
async def _id(number: int) -> str:
    said = await asked(
        f"gh api {_ID.format(number=number)}", f"could not read the id of #{number}"
    )
    return said.strip()


# The numbers already on one end of a relationship.
async def _linked(path: str, complaint: str) -> set[int]:
    said = await asked(f"gh api {path} --paginate --jq '.[].number'", complaint)
    return {int(number) for number in said.split()}


# Both relationships are the other issue's id posted to an endpoint of this
# one. The API answers a link already there with a 422, so a refusal is
# checked against what is linked: a cast run again is not refused on every
# link it made the first time, and the listing is paid only on a refusal.
async def _link(path: str, field: str, other: int, complaint: str) -> None:
    held = await _id(other)
    try:
        await asked(f"gh api {path} -X POST -F {field}={held}", complaint)
    except ForgeError:
        if other in await _linked(path, complaint):
            return
        raise


# Where the next page starts; nothing on the first.
def _after(cursor: str | None) -> tuple[str, ...]:
    return () if cursor is None else (f"-f after={quoted(cursor)}",)


async def _thread_page(number: int, cursor: str | None) -> _ThreadNodes:
    answered = await asked(
        _graphql(_THREADS, *_after(cursor), f"-F number={number}"),
        "gh could not read the threads",
    )
    try:
        return _Threads.model_validate_json(answered).threads
    except ValidationError as error:
        msg = f"gh returned threads this could not read: {error}"
        raise ForgeError(msg) from error


async def _comment_page(thread: str, cursor: str | None) -> _Comments:
    answered = await asked(
        _graphql(_COMMENTS, f"-f id={quoted(thread)}", *_after(cursor)),
        f"gh could not read the comments on thread {thread}",
    )
    try:
        return _MoreComments.model_validate_json(answered).comments
    except ValidationError as error:
        msg = f"gh returned comments this could not read: {error}"
        raise ForgeError(msg) from error


# Every comment from the page in hand on, asking for the rest.
async def _comment_nodes(thread: str, held: _Comments) -> list[_Comment]:
    if not held.page.more:
        return held.nodes
    rest = await _comment_page(thread, held.page.cursor)
    return held.nodes + await _comment_nodes(thread, rest)


# Every thread from the page `cursor` starts on.
async def _threads_from(number: int, cursor: str | None) -> list[Thread]:
    page = await _thread_page(number, cursor)
    found = [await _thread(node) for node in page.nodes]
    if not page.page.more:
        return found
    return found + await _threads_from(number, page.page.cursor)


async def _thread(found: _Thread) -> Thread:
    nodes = await _comment_nodes(found.id, found.comments)
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
                mine=comment.mine,
            )
            for comment in nodes
        ],
    )


class GithubForge(ForgeProtocol):
    @override
    async def pulls(self) -> list[PullRequest]:
        listed = await asked(_LIST, "gh could not list your pull requests")
        try:
            return [_pull(found) for found in _PULLS.validate_json(listed)]
        except ValidationError as error:
            msg = f"gh returned something unreadable: {error}"
            raise ForgeError(msg) from error

    @override
    async def labels(self, number: int) -> list[str]:
        seen = await asked(
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
        flags = [f"--add-label {quoted(one)}" for one in add]
        flags += [f"--remove-label {quoted(one)}" for one in remove]
        if not flags:
            return
        await asked(
            f"gh pr edit {number} {' '.join(flags)}", f"could not label #{number}"
        )

    @override
    async def threads(self, number: int) -> list[Thread]:
        return await _threads_from(number, None)

    # The path without the number answers 404, and the reply goes under the
    # thread's first comment: that is the one the REST id names a thread by.
    @override
    async def reply(self, number: int, thread: Thread, body: str) -> None:
        if not thread.comments:
            msg = f"thread {thread.id} has no comment to reply under"
            raise ForgeError(msg)
        first = thread.comments[0].id
        await asked(
            f"gh api repos/{{owner}}/{{repo}}/pulls/{number}/comments/{first}/replies"
            f" -f body={quoted(body)}",
            f"could not reply on thread {thread.id}",
        )

    @override
    async def resolve(self, number: int, thread: Thread) -> None:
        await asked(
            _graphql(_RESOLVE, f"-f id={quoted(thread.id)}"),
            f"could not resolve thread {thread.id}",
        )

    @override
    async def board(self, branch: str) -> Board:
        path = _BOARD.format(branch=branch)
        answered = await asked(
            f"gh api {quoted(path)}", "gh could not read the check board"
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

    # One head commit for the whole review, and one pass down the items.
    @override
    async def comment(self, number: int, findings: Sequence[Finding]) -> Posted:
        head = await _head(number, findings)
        posted = 0
        for finding in findings:
            if stopped := await _one(number, finding, head=head):
                return Posted(count=posted, stopped=stopped)
            posted += 1
        return Posted(count=posted)

    # The API rather than `gh issue create`, which prints a URL and nothing
    # else: the number is what attaches the issue under its epic and names it
    # in the report, and reading it back out of the URL would be guessing.
    @override
    async def issue(self, title: str, body: str) -> Opened:
        made = await asked(
            "gh api repos/{owner}/{repo}/issues -X POST"
            f" -f title={quoted(title)} -f body={quoted(body)}",
            "could not open the issue",
        )
        try:
            opened = _Opened.model_validate_json(made)
        except ValidationError as error:
            msg = f"gh returned an issue this could not read: {error}"
            raise ForgeError(msg) from error
        return Opened(number=opened.number, url=opened.html_url)

    @override
    async def issues(self) -> Listing:
        found: dict[int, Issue] = {}
        truncated = False
        for who in ("--author", "--assignee"):
            listed = await asked(
                _ISSUES.format(who=who), "gh could not list your issues"
            )
            try:
                rows = _ISSUE_LIST.validate_json(listed)
            except ValidationError as error:
                msg = f"gh returned issues this could not read: {error}"
                raise ForgeError(msg) from error
            # A full listing may be a full backlog, and there is no total to
            # compare against: either way the rest of it is unaccounted for.
            truncated = truncated or len(rows) >= _ISSUE_PAGE
            # The first listing to name an issue keeps it: an issue you opened
            # and are assigned stays yours.
            found = {
                row.number: Issue(
                    number=row.number,
                    title=row.title,
                    url=row.url,
                    body=row.body,
                    labels=[label.name for label in row.labels],
                    mine=who == "--author",
                )
                for row in rows
            } | found
        return Listing(
            issues=[found[number] for number in sorted(found)], truncated=truncated
        )

    @override
    async def label_issue(
        self, number: int, *, add: Sequence[str] = (), remove: Sequence[str] = ()
    ) -> None:
        flags = [f"--add-label {quoted(one)}" for one in add]
        flags += [f"--remove-label {quoted(one)}" for one in remove]
        if not flags:
            return
        await asked(
            f"gh issue edit {number} {' '.join(flags)}", f"could not label #{number}"
        )

    @override
    async def attach(self, epic: int, child: int) -> None:
        await _link(
            _SUB_ISSUES.format(epic=epic),
            "sub_issue_id",
            child,
            f"could not attach #{child} under #{epic}",
        )

    @override
    async def blocks(self, number: int, blocker: int) -> None:
        await _link(
            _BLOCKED_BY.format(number=number),
            "issue_id",
            blocker,
            f"could not say #{number} is blocked by #{blocker}",
        )

    # `--force` updates a label that is already there instead of refusing it,
    # which is what makes the ritual safe to cast again.
    @override
    async def ensure_label(self, spec: LabelSpec) -> None:
        await asked(
            f"gh label create {quoted(spec.name)} --color {quoted(spec.color)}"
            f" --description {quoted(spec.description)} --force",
            f"could not create the label {spec.name}",
        )
