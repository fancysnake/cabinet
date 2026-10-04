"""What every ritual test starts from: the services wired, a project in hand."""

import json
from pathlib import Path

import pytest

from cabinet.inits.services import Services
from cabinet.pacts.project import Labels, Project, State
from cabinet.pacts.pulls import PullRequest, Run, Work
from cabinet.pacts.reviews import Branch, Picking
from cabinet.pacts.services import bind

# The same rows the real forge would list, in gh's own spelling.
LIST = (
    "gh pr list --author @me --state open --limit 100 "
    "--json number,title,headRefName,baseRefName,url,updatedAt,labels"
)
STATUS = "git status --porcelain"
HERE = "git rev-parse --abbrev-ref HEAD"
GPG_TTY = 'GPG_TTY="${GPG_TTY:-$(tty </dev/tty 2>/dev/null)}"'
LABELS = "gh pr view 7 --json labels"
# The graphql call's jq holds brackets a glob would read as a character class,
# so the pattern names the two ends of the command and nothing in between.
THREADS = "slug=*gh api graphql*-F number=7"

# The one pull request most tests are about.
_NUMBER = 7

_LAST = {"hasNextPage": False}


def checkpoint(ritual: str, state: State) -> str:
    add, remove = Labels().pair(ritual, state)
    return f"gh pr edit 7 --add-label {add} --remove-label {remove}"


def board(name: str = "feature") -> str:
    path = f"repos/{{owner}}/{{repo}}/commits/{name}/check-runs?per_page=100"
    return f"gh api '{path}'"


def commit(message: str) -> str:
    return (
        "git add -A && (git diff --cached --quiet || "
        f"{GPG_TTY} git commit -m '{message}')"
    )


def row(number: int = _NUMBER, **extra: object) -> dict[str, object]:
    return {
        "number": number,
        "title": f"pr {number}",
        "headRefName": "feature" if number == _NUMBER else f"feature-{number}",
        "baseRefName": "main",
        "url": f"https://github.com/o/r/pull/{number}",
        "updatedAt": "2026-08-01T22:00:00Z",
        "labels": [],
        **extra,
    }


def listing(*rows: dict[str, object]) -> str:
    return json.dumps(list(rows))


# One page of a GraphQL connection, with a cursor to the next where there is one.
def page(nodes: list[dict[str, object]], cursor: str = "") -> dict[str, object]:
    info = {"hasNextPage": True, "endCursor": cursor} if cursor else _LAST
    return {"pageInfo": info, "nodes": nodes}


def comment(
    number: int, author: str = "reviewer", body: str = "hm"
) -> dict[str, object]:
    return {"databaseId": number, "author": {"login": author}, "body": body}


# A review thread, its `comments` one page of them.
def node(
    node_id: str,
    comments: dict[str, object],
    *,
    resolved: bool = False,
    path: str | None = None,
    line: int | None = None,
) -> dict[str, object]:
    return {
        "id": node_id,
        "isResolved": resolved,
        "path": path,
        "line": line,
        "comments": comments,
    }


# What `gh api graphql` answers for one page of a pull request's threads.
def threads_page(connection: dict[str, object]) -> str:
    return json.dumps(
        {"data": {"repository": {"pullRequest": {"reviewThreads": connection}}}}
    )


def _pull() -> PullRequest:
    return PullRequest(
        number=_NUMBER,
        title="pr 7",
        url="https://github.com/o/r/pull/7",
        branch="feature",
        base="main",
        updated_at="2026-08-01T22:00:00Z",
    )


@pytest.fixture(autouse=True)
def _wired() -> None:
    bind(Services())


@pytest.fixture
def project() -> Project:
    return Project()


@pytest.fixture
def pull() -> PullRequest:
    return _pull()


@pytest.fixture
def work() -> Work:
    return Work(run=Run(project=Project(), bound=3), pr=_pull())


@pytest.fixture
def branch() -> Branch:
    return Branch(picking=Picking(project=Project(), bound=2), name="feature", number=7)


# A whole cast reads its project from the cwd, the way a real one does.
@pytest.fixture
def here(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".vekna.toml").write_text('[rituals]\nmodules = ["cabinet.rituals"]\n')
    monkeypatch.chdir(tmp_path)
    return tmp_path
