"""A forge's rate limit waited out, and every other refusal left alone."""

import json

import pytest
from vekna.trial import Trial

from cabinet.links.forge.asking import asked
from cabinet.links.forge.github import GithubForge
from cabinet.links.forge.gitlab import GitlabForge
from cabinet.pacts.forge import ForgeError, ForgeLimitedError
from cabinet.pacts.project import LabelSpec
from cabinet.pacts.threads import Finding, Posted
from tests.conftest import drive

_CALL = "gh api user"
_LIMITED = "gh: API rate limit exceeded for user ID 1. (HTTP 403)"
_SECONDARY = "gh: You have exceeded a secondary rate limit. (HTTP 429)"
_GRAPHQL = "GraphQL: API rate limit already exceeded for user ID 1."
_ABUSE = "gh: You have triggered an abuse detection mechanism. (HTTP 403)"
_GITLAB = "glab: 429 Too Many Requests"
_PAUSES = (15, 30, 60, 120, 240, 480)
_ANCHORED = [Finding(path="src/thing.py", line=12, body="hm")]
_MR = "glab api projects/:id/merge_requests/7"
_DISCUSSIONS = "glab api projects/:id/merge_requests/7/discussions*"


def _limit_outlasts_every_pause(trial: Trial, when: str = _CALL) -> None:
    trial.shell.replies(when=when, always=True, exit_code=1, stderr=_LIMITED)
    trial.shell.replies(when="sleep *", always=True)


class TestAsked:
    @staticmethod
    @pytest.mark.parametrize("said", [_LIMITED, _SECONDARY, _GRAPHQL, _ABUSE, _GITLAB])
    def test_a_limit_is_waited_out(trial: Trial, said: str) -> None:
        trial.shell.replies(when=_CALL, exit_code=1, stderr=said)
        trial.shell.replies(when="sleep 15")
        trial.shell.replies(when=_CALL, stdout="me\n")

        assert drive(trial, lambda: asked(_CALL, "no")) == "me\n"
        assert trial.shell.commands == [_CALL, "sleep 15", _CALL]

    @staticmethod
    def test_each_pause_doubles_the_last_until_the_limit_is_declared(
        trial: Trial,
    ) -> None:
        _limit_outlasts_every_pause(trial)

        with pytest.raises(ForgeLimitedError, match="still rate limited after 15"):
            drive(trial, lambda: asked(_CALL, "no"))

        sleeps = [c for c in trial.shell.commands if c.startswith("sleep")]
        assert sleeps == [f"sleep {pause}" for pause in _PAUSES]
        assert trial.shell.commands.count(_CALL) == len(_PAUSES) + 1

    @staticmethod
    def test_a_limit_that_lifts_stops_the_pauses_short(trial: Trial) -> None:
        trial.shell.replies(when=_CALL, exit_code=1, stderr=_LIMITED)
        trial.shell.replies(when="sleep 15")
        trial.shell.replies(when=_CALL, exit_code=1, stderr=_LIMITED)
        trial.shell.replies(when="sleep 30")
        trial.shell.replies(when=_CALL)

        drive(trial, lambda: asked(_CALL, "no"))

        assert trial.shell.commands[-2:] == ["sleep 30", _CALL]

    @staticmethod
    def test_a_limit_that_lifts_on_the_last_attempt_is_no_failure(trial: Trial) -> None:
        for pause in _PAUSES:
            trial.shell.replies(when=_CALL, exit_code=1, stderr=_LIMITED)
            trial.shell.replies(when=f"sleep {pause}")
        trial.shell.replies(when=_CALL, stdout="me\n")

        assert drive(trial, lambda: asked(_CALL, "no")) == "me\n"

    @staticmethod
    def test_any_other_refusal_surfaces_at_once(trial: Trial) -> None:
        trial.shell.replies(when=_CALL, exit_code=1, stderr="HTTP 502")

        with pytest.raises(ForgeError, match="no: HTTP 502"):
            drive(trial, lambda: asked(_CALL, "no"))

        assert trial.shell.commands == [_CALL]

    @staticmethod
    def test_a_limit_a_failed_response_only_quotes_is_no_limit(trial: Trial) -> None:
        trial.shell.replies(
            when=_CALL, exit_code=1, stdout='{"title": "rate limit"}', stderr="HTTP 422"
        )

        with pytest.raises(ForgeError):
            drive(trial, lambda: asked(_CALL, "no"))

        assert trial.shell.commands == [_CALL]

    @staticmethod
    def test_a_warning_on_a_call_that_worked_is_no_limit(trial: Trial) -> None:
        trial.shell.replies(when=_CALL, stdout="me\n", stderr=_LIMITED)

        assert drive(trial, lambda: asked(_CALL, "no")) == "me\n"
        assert trial.shell.commands == [_CALL]

    @staticmethod
    def test_the_limit_outlives_what_catches_a_refusal() -> None:
        assert not issubclass(ForgeLimitedError, ForgeError)


class TestAnchors:
    @staticmethod
    def test_github_keeps_the_anchor_through_a_limit(trial: Trial) -> None:
        anchored = "gh api repos/{owner}/{repo}/pulls/7/comments*"
        trial.shell.replies(when="gh pr view 7*", stdout="abc123\n")
        trial.shell.replies(when=anchored, exit_code=1, stderr=_LIMITED)
        trial.shell.replies(when="sleep 15")
        trial.shell.replies(when=anchored)

        forge = GithubForge()

        assert drive(trial, lambda: forge.comment(7, _ANCHORED)) == Posted(count=1)
        assert not any(c.startswith("gh pr comment") for c in trial.shell.commands)

    @staticmethod
    def test_gitlab_keeps_the_anchor_through_a_limit(trial: Trial) -> None:
        refs = {"diff_refs": {"base_sha": "b", "head_sha": "h", "start_sha": "s"}}
        trial.shell.replies(when=_MR, stdout=json.dumps(refs))
        trial.shell.replies(when=_DISCUSSIONS, exit_code=1, stderr=_GITLAB)
        trial.shell.replies(when="sleep 15")
        trial.shell.replies(when=_DISCUSSIONS)

        forge = GitlabForge()

        assert drive(trial, lambda: forge.comment(7, _ANCHORED)) == Posted(count=1)
        assert not any(c.startswith("glab mr note") for c in trial.shell.commands)

    @staticmethod
    def test_a_limit_that_outlasts_the_anchor_is_not_waited_for_twice(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when="gh pr view 7*", stdout="abc123\n")
        _limit_outlasts_every_pause(
            trial, "gh api repos/{owner}/{repo}/pulls/7/comments*"
        )

        forge = GithubForge()

        with pytest.raises(ForgeLimitedError):
            drive(trial, lambda: forge.comment(7, _ANCHORED))

        assert not any(c.startswith("gh pr comment") for c in trial.shell.commands)


class TestGitlabLabel:
    @staticmethod
    def test_a_limited_create_is_tried_again_not_taken_for_a_duplicate(
        trial: Trial,
    ) -> None:
        create = "glab api projects/:id/labels -X POST*"
        trial.shell.replies(when=create, exit_code=1, stderr=_GITLAB)
        trial.shell.replies(when="sleep 15")
        trial.shell.replies(when=create)

        spec = LabelSpec(name="bug", color="d73a4a", description="broken")
        forge = GitlabForge()
        drive(trial, lambda: forge.ensure_label(spec))

        assert not any("-X PUT" in c for c in trial.shell.commands)
