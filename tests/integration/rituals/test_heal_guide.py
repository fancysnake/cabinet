"""The guide task: the smoke test written, posted or edited in place, labelled."""

import shlex

from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import post_guide, tend
from cabinet.pacts.heal import Chart, PostGuide, SetAside, Tend
from cabinet.pacts.healing import Work
from cabinet.pacts.threads import GUIDE_MARK, Guide
from tests.integration.rituals.falling import falling

_COMMENTS = "gh api repos/{owner}/{repo}/issues/7/comments --paginate*"
_BODY = f"{GUIDE_MARK}\n\nclick it"
_POSTED = f"gh pr comment 7 --body {shlex.quote(_BODY)}"
_LABEL = "gh pr edit 7 --add-label v:guide:done"


class TestPostGuide:
    @staticmethod
    def test_the_guide_is_a_task(trial: Trial, work: Work) -> None:
        guiding = work.but(todos=["guide"])

        assert trial.walk(tend, guiding.to(Tend)) == work.to(PostGuide)

    @staticmethod
    def test_the_first_guide_is_posted_and_the_label_goes_on(
        trial: Trial, work: Work
    ) -> None:
        trial.coding.replies(Guide(body="click it"))
        trial.shell.replies(when=_COMMENTS)
        trial.shell.replies(when="gh pr comment 7*")
        trial.shell.replies(when=_LABEL)

        assert trial.walk(post_guide, work.to(PostGuide)) == work.to(Tend)
        assert "smoke-test/SKILL.md" in trial.coding.prompts[0]
        assert "origin/main...HEAD" in trial.coding.prompts[0]
        assert trial.shell.commands[-2:] == [_POSTED, _LABEL]
        assert "Edit" not in str(trial.coding.calls[0].focus_options)

    # The label was taken off to ask again: the comment that is up says the
    # new guide, and no second one appears beside it.
    @staticmethod
    def test_a_guide_already_up_is_edited_in_place(trial: Trial, work: Work) -> None:
        trial.coding.replies(Guide(body="click it"))
        trial.shell.replies(when=_COMMENTS, stdout="11\n")
        trial.shell.replies(when="gh api repos/{owner}/{repo}/issues/comments/11*")
        trial.shell.replies(when=_LABEL)

        assert trial.walk(post_guide, work.to(PostGuide)) == work.to(Tend)
        assert trial.shell.commands[-2].startswith(
            "gh api repos/{owner}/{repo}/issues/comments/11 -X PATCH"
        )
        assert "gh pr comment" not in " ".join(trial.shell.commands)

    @staticmethod
    def test_a_comment_the_forge_refuses_is_not_labelled(
        trial: Trial, work: Work
    ) -> None:
        trial.coding.replies(Guide(body="click it"))
        trial.shell.replies(when=_COMMENTS)
        trial.shell.replies(when="gh pr comment 7*", exit_code=1, stderr="403")

        assert trial.walk(post_guide, work.to(PostGuide)) == work.but(
            note="could not comment on #7: 403"
        ).to(SetAside)
        assert "--add-label" not in " ".join(trial.shell.commands)

    # The guide is up and the label is not, so the next cast writes another
    # and edits it over this one.
    @staticmethod
    def test_a_label_the_forge_refuses_sets_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.coding.replies(Guide(body="click it"))
        trial.shell.replies(when=_COMMENTS)
        trial.shell.replies(when="gh pr comment 7*")
        trial.shell.replies(when="gh pr edit 7*", exit_code=1, stderr="no such label")

        assert trial.walk(post_guide, work.to(PostGuide)) == work.but(
            note="could not label #7: no such label"
        ).to(SetAside)

    @staticmethod
    def test_an_empty_guide_sets_the_branch_aside(trial: Trial, work: Work) -> None:
        trial.coding.replies(Guide.model_construct(body=""))

        transition = trial.walk(post_guide, work.to(PostGuide))

        assert isinstance(transition, SetAside)
        assert "did not answer in the shape asked" in transition.note
        assert not trial.shell.commands

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()

        assert trial.walk(post_guide, work.to(PostGuide)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Chart)
