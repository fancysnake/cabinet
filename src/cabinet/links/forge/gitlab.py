"""GitLab through `glab`, hosted or self-hosted alike.

Every call is `glab api` against the REST API with `:id` standing for the
project the worktree's remote names — so a self-hosted instance needs nothing
here, only `glab auth login --hostname`.
"""

from typing import TYPE_CHECKING, override
from urllib.parse import quote

from pydantic import BaseModel, TypeAdapter, ValidationError
from vekna.folio.shell import shell

from cabinet.links.forge.asking import asked, quoted
from cabinet.pacts.forge import ForgeError, ForgeProtocol
from cabinet.pacts.pulls import Board, Check, PullRequest
from cabinet.pacts.threads import Comment, Finding, Posted, Thread

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cabinet.pacts.project import LabelSpec

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
    web_url: str


_MERGE_REQUESTS: TypeAdapter[list[_MergeRequest]] = TypeAdapter(list[_MergeRequest])
_DISCUSSIONS: TypeAdapter[list[_Discussion]] = TypeAdapter(list[_Discussion])
_STATUSES: TypeAdapter[list[_Status]] = TypeAdapter(list[_Status])


def _api(path: str, *flags: str) -> str:
    extra = "".join(f" {flag}" for flag in flags)
    return f"glab api {quoted(path)}{extra}"


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


async def _refs(number: int) -> _DiffRefs:
    seen = await asked(
        _api(f"projects/:id/merge_requests/{number}"),
        "glab could not read the merge request",
    )
    try:
        return _Anchored.model_validate_json(seen).diff_refs
    except ValidationError as error:
        msg = f"glab returned a merge request this could not read: {error}"
        raise ForgeError(msg) from error


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
        listed = await asked(_api(_LIST), "glab could not list your merge requests")
        try:
            return [_pull(found) for found in _MERGE_REQUESTS.validate_json(listed)]
        except ValidationError as error:
            msg = f"glab returned something unreadable: {error}"
            raise ForgeError(msg) from error

    @override
    async def labels(self, number: int) -> list[str]:
        seen = await asked(
            _api(f"projects/:id/merge_requests/{number}"),
            "glab could not read the labels",
        )
        try:
            return _MergeRequest.model_validate_json(seen).labels
        except ValidationError as error:
            msg = f"glab returned labels this could not read: {error}"
            raise ForgeError(msg) from error

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
        answered = await asked(
            _api(f"projects/:id/merge_requests/{number}/discussions?per_page={_PAGE}"),
            "glab could not read the discussions",
        )
        try:
            found = _DISCUSSIONS.validate_json(answered)
        except ValidationError as error:
            msg = f"glab returned discussions this could not read: {error}"
            raise ForgeError(msg) from error
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
        answered = await asked(
            _api(f"projects/:id/repository/commits/{branch}/statuses?per_page={_PAGE}"),
            "glab could not read the commit statuses",
        )
        try:
            found = _STATUSES.validate_json(answered)
        except ValidationError as error:
            msg = f"glab returned statuses this could not read: {error}"
            raise ForgeError(msg) from error
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
    async def issue(self, title: str, body: str) -> str:
        made = await asked(
            _api(
                "projects/:id/issues",
                "-X POST",
                f"-f title={quoted(title)}",
                f"-f description={quoted(body)}",
            ),
            "could not open the issue",
        )
        try:
            return _Issue.model_validate_json(made).web_url
        except ValidationError as error:
            msg = f"glab returned an issue this could not read: {error}"
            raise ForgeError(msg) from error

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
