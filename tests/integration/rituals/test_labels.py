"""Making every label, the pull request and the issue ones in one cast."""

import pytest
from vekna.lexicon import NoComponents
from vekna.trial import Trial

from cabinet.pacts.project import Labelled
from cabinet.rituals.labels import labels

_NAMES = [
    "pr::thermo",
    "pr::wait",
    "v:refresh:started",
    "v:refresh:done",
    "v:cover:started",
    "v:cover:done",
    "v:review:started",
    "v:review:done",
    "feature",
    "edit",
    "chore",
    "spike",
    "bug",
    "S",
    "M",
    "L",
    "epic",
]


class TestLabels:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_every_pr_and_issue_label_is_made_with_force(trial: Trial) -> None:
        trial.shell.replies(when="gh label create*", always=True)

        result = trial.cast(labels, NoComponents())

        assert result == Labelled(names=_NAMES)
        assert trial.steps == ["conjure"]
        assert len(trial.shell.commands) == len(_NAMES)
