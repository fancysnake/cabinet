"""Making the issue labels `identify` puts on."""

import pytest
from vekna.lexicon import NoComponents
from vekna.trial import Trial

from cabinet.pacts.project import Labelled
from cabinet.rituals.labels_identify import labels_identify

_NAMES = ["feature", "edit", "chore", "spike", "bug", "S", "M", "L", "epic"]


class TestLabelsIdentify:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_every_type_size_and_the_epic_label_is_made_with_force(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when="gh label create*", always=True)

        result = trial.cast(labels_identify, NoComponents())

        assert result == Labelled(names=_NAMES)
        assert trial.steps == ["conjure"]
        assert len(trial.shell.commands) == len(_NAMES)
        assert trial.shell.commands[-1] == (
            "gh label create epic --color 5319e7"
            " --description 'Too big for one PR: split into sub-issues, carries no"
            " size' --force"
        )
