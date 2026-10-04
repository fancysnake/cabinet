"""GitLab through `glab`, hosted or self-hosted alike.

Every call is `glab api` against the REST API with `:id` standing for the
project the worktree's remote names — so a self-hosted instance needs nothing
here, only `glab auth login --hostname`.
"""

from collections.abc import Sequence
from typing import TypeVar
from urllib.parse import quote

from pydantic import BaseModel, TypeAdapter, ValidationError
from typing_extensions import override
from vekna.folio.shell import shell

from cabinet.links.forge.asking import asked, quoted
from cabinet.pacts.forge import ForgeError, ForgeProtocol
from cabinet.pacts.issues import Issue, Listing, Opened
from cabinet.pacts.project import LabelSpec
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Posted, Thread

_PAGE = 100

_LIST = f"projects/:id/merge_requests?scope=created_by_me&state=opened&per_page={_PAGE}"

_PASSED = "success"
# Still on its way, as opposed to finished badly.
_PENDING = ("pending", "running", "created", "waiting_for_resource", "preparing")


class _Author(BaseModel):
    username: str = ""


class _MergeRequest(BaseModel):
    iid: int
    title: str
    web_url: str
    source_branch: str
    target_branch: str
    updated_at: str
    labels: list[str] = []


class _DiffRefs(BaseModel):
    base_sha: str
    head_sha: str
    start_sha: str


class _Anchored(BaseModel):
    diff_refs: _DiffRefs


class _Position(BaseModel):
    new_path: str = ""
    new_line: int | None = None


class _Note(BaseModel):
    id: int
    body: str = ""
    author: _Author = _Author()
    resolvable: bool = False
    resolved: bool = False
    position: _Position | None = None


class _Discussion(BaseModel):
    id: str
    notes: list[_Note] = []


class _Status(BaseModel):
    name: str
    status: str
    description: str | None = None


class _Issue(BaseModel):
    iid: int
    web_url: str


# `:id` stands for this project everywhere in a path, but a link's target
# project is a field rather than a path, and a field is not substituted.
class _Project(BaseModel):
    id: int


# One issue linked to another, and how, as seen from the issue asked about.
# The project too: an iid is only unique within one.
class _Linked(BaseModel):
    project_id: int
    iid: int
    link_type: str


_MERGE_REQUESTS: TypeAdapter[list[_MergeRequest]] = TypeAdapter(list[_MergeRequest])
_DISCUSSIONS: TypeAdapter[list[_Discussion]] = TypeAdapter(list[_Discussion])
_STATUSES: TypeAdapter[list[_Status]] = TypeAdapter(list[_Status])


class _Listed(BaseModel):
    iid: int
    title: str
    web_url: str
    # Null on an issue opened without one.
    description: str | None = None
    labels: list[str] = []


_LISTED: TypeAdapter[list[_Listed]] = TypeAdapter(list[_Listed])
_LINKED: TypeAdapter[list[_Linked]] = TypeAdapter(list[_Linked])
_MERGE_REQUEST: TypeAdapter[_MergeRequest] = TypeAdapter(_MergeRequest)
_ANCHORED: TypeAdapter[_Anchored] = TypeAdapter(_Anchored)
_ISSUE: TypeAdapter[_Issue] = TypeAdapter(_Issue)
_PROJECT: TypeAdapter[_Project] = TypeAdapter(_Project)

_T = TypeVar("_T")


def _api(path: str, *flags: str) -> str:
    extra = "".join(f" {flag}" for flag in flags)
    return f"glab api {quoted(path)}{extra}"


# What glab answered to `command`, read by `adapter`; `what` names it in the
# error when it cannot be read.
async def _read(
    adapter: TypeAdapter[_T], command: str, complaint: str, what: str
) -> _T:
    answered = await asked(command, complaint)
    try:
        return adapter.validate_json(answered)
    except ValidationError as error:
        msg = f"glab returned {what} this could not read: {error}"
        raise ForgeError(msg) from error


# The listing at `path`, which carries `per_page` already, from `page` on. The
# `x-next-page` and `Link` headers go unread so the answer stays a bare JSON
# body: a short page is the last one, and a full last page costs one more ask
# that comes back empty.
async def _pages(
    adapter: TypeAdapter[list[_T]], path: str, complaint: str, what: str, page: int = 1
) -> list[_T]:
    rows = await _read(adapter, _api(f"{path}&page={page}"), complaint, what)
    if len(rows) < _PAGE:
        return rows
    return rows + await _pages(adapter, path, complaint, what, page + 1)


def _pull(found: _MergeRequest) -> PullRequest:
    return PullRequest(
        number=found.iid,
        title=found.title,
        url=found.web_url,
        branch=found.source_branch,
        base=found.target_branch,
        updated_at=found.updated_at,
        labels=found.labels,
    )


def _check(found: _Status) -> Check:
    if found.status == _PASSED:
        passed = True
    elif found.status in _PENDING:
        passed = None
    else:
        passed = False
    return Check(name=found.name, passed=passed, title=found.description or "")


# A discussion is a review thread when its first note can be resolved; the
# rest are system notes and plain remarks, which nobody triages.
def _thread(found: _Discussion) -> Thread | None:
    if not found.notes or not found.notes[0].resolvable:
        return None
    first = found.notes[0]
    position = first.position or _Position()
    return Thread(
        id=found.id,
        resolved=first.resolved,
        path=position.new_path,
        line=position.new_line,
        comments=[
            Comment(id=str(note.id), author=note.author.username, body=note.body)
            for note in found.notes
        ],
    )


async def _project_id() -> int:
    project = await _read(
        _PROJECT, _api("projects/:id"), "glab could not read the project", "a project"
    )
    return project.id


# Both relationships are the one endpoint with a different `link_type`, and
# both want the target project spelled out even when it is this one. The API
# refuses a duplicate, so a refusal is checked against what is linked, and
# the listing is paid only on a refusal.
async def _link(number: int, other: int, kind: str, complaint: str) -> None:
    path = f"projects/:id/issues/{number}/links"
    project = await _project_id()
    try:
        await asked(
            _api(
                path,
                "-X POST",
                f"-F target_project_id={project}",
                f"-F target_issue_iid={other}",
                f"-f link_type={kind}",
            ),
            complaint,
        )
    except ForgeError:
        if await _linked(path, project, other, kind, complaint):
            return
        raise


# Whether issue `other` of `project` is linked as `kind` already.
async def _linked(
    path: str, project: int, other: int, kind: str, complaint: str
) -> bool:
    linked = await _read(_LINKED, _api(f"{path}?per_page={_PAGE}"), complaint, "links")
    return any(
        one.project_id == project and one.iid == other and one.link_type == kind
        for one in linked
    )


async def _refs(number: int) -> _DiffRefs:
    anchored = await _read(
        _ANCHORED,
        _api(f"projects/:id/merge_requests/{number}"),
        "glab could not read the merge request",
        "a merge request",
    )
    return anchored.diff_refs


# Read once for a whole review rather than once per item: every anchored
# discussion on one merge request carries the same refs. None where no item
# wants an anchor, and where glab would not say — an item then goes up as a
# plain note, which is the same bargain a refused anchor makes.
async def _anchor(number: int, findings: Sequence[Finding]) -> _DiffRefs | None:
    if all(finding.line is None for finding in findings):
        return None
    try:
        return await _refs(number)
    except ForgeError:
        return None


# A line outside the diff is refused — then the item goes on as a plain note,
# as it does for an item about the change as a whole. What comes back is what
# stopped it, or nothing.
async def _one(number: int, finding: Finding, *, refs: _DiffRefs | None) -> str:
    if finding.line is not None and refs is not None:
        anchored = await shell(
            _api(
                f"projects/:id/merge_requests/{number}/discussions",
                "-X POST",
                f"-f body={quoted(finding.body)}",
                "-f 'position[position_type]=text'",
                f"-f 'position[base_sha]={refs.base_sha}'",
                f"-f 'position[head_sha]={refs.head_sha}'",
                f"-f 'position[start_sha]={refs.start_sha}'",
                f"-f position[new_path]={quoted(finding.path)}",
                f"-f position[old_path]={quoted(finding.path)}",
                f"-F 'position[new_line]={finding.line}'",
            ),
            stream=False,
        )
        if anchored.exit_code == 0:
            return ""
    try:
        await asked(
            f"glab mr note {number} -m {quoted(finding.body)}",
            f"could not comment on !{number}",
        )
    except ForgeError as error:
        return str(error)
    return ""


class GitlabForge(ForgeProtocol):
    @override
    async def pulls(self) -> list[PullRequest]:
        listed = await _read(
            _MERGE_REQUESTS,
            _api(_LIST),
            "glab could not list your merge requests",
            "merge requests",
        )
        return [_pull(found) for found in listed]

    @override
    async def labels(self, number: int) -> list[str]:
        seen = await _read(
            _MERGE_REQUEST,
            _api(f"projects/:id/merge_requests/{number}"),
            "glab could not read the labels",
            "labels",
        )
        return seen.labels

    @override
    async def label(
        self, number: int, *, add: Sequence[str] = (), remove: Sequence[str] = ()
    ) -> None:
        flags = [f"--label {quoted(one)}" for one in add]
        flags += [f"--unlabel {quoted(one)}" for one in remove]
        if not flags:
            return
        await asked(
            f"glab mr update {number} {' '.join(flags)}", f"could not label !{number}"
        )

    @override
    async def threads(self, number: int) -> list[Thread]:
        found = await _pages(
            _DISCUSSIONS,
            f"projects/:id/merge_requests/{number}/discussions?per_page={_PAGE}",
            "glab could not read the discussions",
            "discussions",
        )
        return [thread for one in found if (thread := _thread(one)) is not None]

    @override
    async def reply(self, number: int, thread: Thread, body: str) -> None:
        await asked(
            _api(
                f"projects/:id/merge_requests/{number}/discussions/{thread.id}/notes",
                "-X POST",
                f"-f body={quoted(body)}",
            ),
            f"could not reply on discussion {thread.id}",
        )

    @override
    async def resolve(self, number: int, thread: Thread) -> None:
        await asked(
            _api(
                f"projects/:id/merge_requests/{number}/discussions/{thread.id}",
                "-X PUT",
                "-F resolved=true",
            ),
            f"could not resolve discussion {thread.id}",
        )

    # Commit statuses rather than pipelines, because that is where an external
    # coverage service posts its patch summary — the same "N% of diff hit"
    # line the GitHub board carries. A full page may be a short page.
    @override
    async def board(self, branch: str) -> Board:
        found = await _read(
            _STATUSES,
            _api(f"projects/:id/repository/commits/{branch}/statuses?per_page={_PAGE}"),
            "glab could not read the commit statuses",
            "statuses",
        )
        return Board(
            checks=[_check(status) for status in found], truncated=len(found) >= _PAGE
        )

    # One read of the diff refs for the whole review, and one pass down the
    # items.
    @override
    async def comment(self, number: int, findings: Sequence[Finding]) -> Posted:
        refs = await _anchor(number, findings)
        posted = 0
        for finding in findings:
            if stopped := await _one(number, finding, refs=refs):
                return Posted(count=posted, stopped=stopped)
            posted += 1
        return Posted(count=posted)

    @override
    async def issue(self, title: str, body: str) -> Opened:
        opened = await _read(
            _ISSUE,
            _api(
                "projects/:id/issues",
                "-X POST",
                f"-f title={quoted(title)}",
                f"-f description={quoted(body)}",
            ),
            "could not open the issue",
            "an issue",
        )
        return Opened(number=opened.iid, url=opened.web_url)

    @override
    async def issues(self) -> Listing:
        found: dict[int, Issue] = {}
        truncated = False
        for scope in ("created_by_me", "assigned_to_me"):
            rows = await _read(
                _LISTED,
                _api(
                    f"projects/:id/issues?state=opened&scope={scope}&per_page={_PAGE}"
                ),
                "glab could not list your issues",
                "issues",
            )
            # A full page may be a short page, as it is for the board: what is
            # past it is not asked for, so the cast never sees it.
            truncated = truncated or len(rows) >= _PAGE
            found |= {
                row.iid: Issue(
                    number=row.iid,
                    title=row.title,
                    url=row.web_url,
                    body=row.description or "",
                    labels=row.labels,
                )
                for row in rows
            }
        return Listing(
            issues=[found[number] for number in sorted(found)], truncated=truncated
        )

    @override
    async def label_issue(
        self, number: int, *, add: Sequence[str] = (), remove: Sequence[str] = ()
    ) -> None:
        flags = [f"--label {quoted(one)}" for one in add]
        flags += [f"--unlabel {quoted(one)}" for one in remove]
        if not flags:
            return
        await asked(
            f"glab issue update {number} {' '.join(flags)}",
            f"could not label #{number}",
        )

    # `relates_to` and not a parent link: epics and child items are Premium,
    # and a relation is what every tier has.
    @override
    async def attach(self, epic: int, child: int) -> None:
        await _link(
            epic, child, "relates_to", f"could not attach #{child} under #{epic}"
        )

    @override
    async def blocks(self, number: int, blocker: int) -> None:
        await _link(
            number,
            blocker,
            "is_blocked_by",
            f"could not say #{number} is blocked by #{blocker}",
        )

    # Created, or updated where it is already there: the API refuses a
    # duplicate name, and a label that exists is not a failure of the ritual.
    @override
    async def ensure_label(self, spec: LabelSpec) -> None:
        colour = f"-f color={quoted(f'#{spec.color}')}"
        description = f"-f description={quoted(spec.description)}"
        made = await shell(
            _api(
                "projects/:id/labels",
                "-X POST",
                f"-f name={quoted(spec.name)}",
                colour,
                description,
            ),
            stream=False,
        )
        if made.exit_code == 0:
            return
        await asked(
            _api(
                f"projects/:id/labels/{quote(spec.name, safe='')}",
                "-X PUT",
                colour,
                description,
            ),
            f"could not create the label {spec.name}",
        )
