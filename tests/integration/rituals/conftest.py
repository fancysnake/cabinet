"""What every ritual test shares."""

import pytest
from vekna.trial import Trial


# A thread read also reads the pull request's plain comments, and none of
# these tests has any: the answers are empty, and `always` keeps them from
# being used up.
@pytest.fixture(autouse=True)
def _no_plain_comments(trial: Trial) -> None:
    trial.shell.replies(when="gh api user --jq .login", stdout="me\n", always=True)
    trial.shell.replies(
        when="gh api repos/{owner}/{repo}/issues/*/comments --paginate --jq *{ref:*",
        stdout="",
        always=True,
    )


# A survey fetches the remote before it asks git about a branch.
@pytest.fixture(autouse=True)
def _fetched(trial: Trial) -> None:
    trial.shell.replies(when="stamp=*git fetch origin*", always=True)


# A survey asks git whether the branch is behind its base. Here it is not.
@pytest.fixture
def fresh(trial: Trial) -> None:
    trial.shell.replies(
        when="git merge-base --is-ancestor origin/main origin/feature*", always=True
    )
