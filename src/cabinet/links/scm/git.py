"""What the rituals say to git, and what they make of the answer."""

import shlex

from typing_extensions import override
from vekna.folio.shell import ShellResult, shell

from cabinet.pacts.project import Project
from cabinet.pacts.scm import ScmError, ScmProtocol
from cabinet.pacts.tasks import Ran

# Porcelain because a step puts an `if` around it: empty output is a clean
# worktree.
_STATUS = "git status --porcelain"

# Where the worktree stands, which is not always the branch a step is working
# on.
_HERE = "git rev-parse --abbrev-ref HEAD"

_STASHED = "stashed"

# The agent was told not to commit the merge, but a step checks rather than
# trusts: MERGE_HEAD is gone when it committed anyway, and then there is no
# merge left to continue.
_CONTINUE_MERGE = (
    "if git rev-parse -q --verify MERGE_HEAD >/dev/null; then "
    "git add -A && git -c core.editor=true merge --continue; fi"
)

# pinentry draws on the terminal `GPG_TTY` names, and a command under a cast
# has no terminal on its stdin — so the controlling one is named for it where
# the shell that started the cast did not. Harmless without a key to unlock.
_GPG_TTY = 'GPG_TTY="${GPG_TTY:-$(tty </dev/tty 2>/dev/null)}"'

_HELPER = {
    "github": "gh auth setup-git",
    "gitlab": "git config --global credential.helper '!glab auth git-credential'",
}


# A near-copy of what the forge adapters share through
# `links/forge/asking.py`, and it stays a copy: `inside-links` holds the
# adapters apart, so nothing in `scm` may import from `forge`. What differs
# anyway is the error each raises and what each hands back.
def _quoted(value: str) -> str:
    return shlex.quote(value)


# Both streams, because a command that dies before it starts says so on
# stderr and nowhere else.
def _said(result: ShellResult) -> str:
    parts = (result.stdout.strip(), result.stderr.strip())
    return "\n".join(part for part in parts if part) or f"exit code {result.exit_code}"


def _ran(result: ShellResult) -> Ran:
    return Ran(stdout=result.stdout, stderr=result.stderr, exit_code=result.exit_code)


async def _asked(command: str, complaint: str, *, stream: bool = True) -> Ran:
    result = await shell(command, stream=stream)
    if result.exit_code:
        msg = f"{complaint}: {_said(result)}"
        raise ScmError(msg)
    return _ran(result)


# Naming the stash is only worth anything if the morning report says the name.
def stash_name(branch: str) -> str:
    return f"a pr sweep left {branch} unfinished"


class GitScm(ScmProtocol):
    def __init__(self, project: Project) -> None:
        self._remote = project.remote
        self._sign = project.sign_commits
        self._helper = _HELPER[project.forge]

    @override
    async def preflight(self) -> None:
        url = (
            await _asked(
                f"git remote get-url {_quoted(self._remote)}",
                f"no remote named {self._remote}",
                stream=False,
            )
        ).stdout.strip()
        if not url.startswith("https://"):
            msg = (
                f"remote {self._remote} is {url}, not https: a cast has no terminal"
                " for ssh to ask a passphrase on. Add an https remote with"
                f" `{self._helper}` behind it and name it in [cabinet] remote."
            )
            raise ScmError(msg)
        helper = await shell(
            f"git config --get-urlmatch credential.helper {_quoted(url)}", stream=False
        )
        if helper.exit_code or not helper.stdout.strip():
            msg = f"no credential helper for {url}: run `{self._helper}`"
            raise ScmError(msg)

    @override
    async def status(self) -> str:
        ran = await _asked(_STATUS, "git status failed", stream=False)
        return ran.stdout.strip()

    @override
    async def here(self) -> str:
        ran = await _asked(_HERE, "could not read the current branch", stream=False)
        return ran.stdout.strip()

    @override
    async def checkout(self, branch: str) -> None:
        await _asked(f"git checkout {_quoted(branch)}", f"could not take {branch}")

    @override
    async def sync_base(self, base: str) -> None:
        remote = _quoted(self._remote)
        await _asked(
            f"git fetch --prune {remote} && git checkout {_quoted(base)}"
            f" && git pull --ff-only {remote} {_quoted(base)}",
            f"could not update {base}",
        )

    # `merge --ff-only`, never `reset --hard`: a branch this ritual worked on
    # last night carries commits the remote has not seen, and they are the
    # whole point of the report. A branch that has genuinely diverged stops
    # here.
    @override
    async def catch_up(self, branch: str) -> None:
        await _asked(
            f"git merge --ff-only {_quoted(f'{self._remote}/{branch}')}",
            "could not catch up with the remote",
        )

    @override
    async def contains(self, base: str) -> bool:
        asked = await shell(
            f"git merge-base --is-ancestor {_quoted(base)} HEAD", stream=False
        )
        return asked.exit_code == 0

    @override
    async def merge(self, base: str) -> Ran:
        return _ran(await shell(f"git merge --no-edit {_quoted(base)}"))

    @override
    async def unmerged(self) -> list[str]:
        ran = await _asked(
            "git diff --name-only --diff-filter=U",
            "could not read the index",
            stream=False,
        )
        # By line, not by whitespace: `--name-only` leaves a space in a path
        # unquoted, and splitting on it hands the resolver two files that do
        # not exist instead of the one that does.
        return ran.stdout.splitlines()

    @override
    async def continue_merge(self) -> None:
        await _asked(_CONTINUE_MERGE, "could not finish the merge")

    # Idempotent: staging everything and finding nothing staged is a commit
    # rite that did nothing, not a failure.
    @override
    async def commit(self, message: str) -> None:
        unsigned = "" if self._sign else " -c commit.gpgsign=false"
        await _asked(
            "git add -A && (git diff --cached --quiet || "
            f"{_GPG_TTY} git{unsigned} commit -m {_quoted(message)})",
            "could not commit",
        )

    # The remote by name rather than the branch's upstream, which a branch a
    # ritual has just merged on may not have. It is the one `ahead` counts
    # against.
    @override
    async def push(self, branch: str) -> None:
        await _asked(
            f"git push {_quoted(self._remote)} {_quoted(branch)}",
            f"could not push {branch}",
        )

    # The dirty check is what makes the report's claim true: `git stash push`
    # on a clean tree exits 0 having saved nothing, so a note written off the
    # exit code alone would name a stash that is not there. Echoing our own
    # marker beats reading git's prose for the same answer.
    @override
    async def release(self, branch: str) -> str:
        name = stash_name(branch)
        ran = await _asked(
            "if git rev-parse -q --verify MERGE_HEAD >/dev/null; "
            "then git merge --abort; fi; "
            f'if [ -n "$({_STATUS})" ]; '
            f"then git stash push -u -m {_quoted(name)} >/dev/null "
            f"&& echo {_STASHED}; fi",
            "the worktree could not be released",
        )
        return name if ran.stdout.strip() == _STASHED else ""

    # HEAD is asked for by name first, because it is not always this branch: a
    # step reached from a failed checkout is still standing on the base, and
    # counting `<remote>/<branch>..HEAD` there measures the base against the
    # branch. A non-zero exit is "we could not tell".
    @override
    async def ahead(self, branch: str) -> int | None:
        span = _quoted(f"{self._remote}/{branch}..HEAD")
        counted = await shell(
            f'test {_quoted(branch)} = "$({_HERE})" && git rev-list --count {span}',
            stream=False,
        )
        if counted.exit_code:
            return None
        text = counted.stdout.strip()
        return int(text) if text.isdigit() else None
