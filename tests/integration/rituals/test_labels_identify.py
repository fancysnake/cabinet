"""Making the issue labels `identify` puts on."""

import pytest
from vekna.lexicon import NoComponents
from vekna.trial import Trial

from cabinet.pacts.project import Labelled
from cabinet.rituals.labels_identify import labels_identify

_NAMES = ["feature", "edit", "chore", "spike", "bug", "S", "M", "L", "epic", "shape"]


class TestLabelsIdentify:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_every_type_size_the_epic_and_the_shape_label_is_made_with_force(
        trial: Trial,
    ) -> None:
        trial.shell.replies(when="gh label create*", always=True)

        result = trial.cast(labels_identify, NoComponents())

        assert result == Labelled(names=_NAMES)
        assert trial.steps == ["conjure"]
        assert len(trial.shell.commands) == len(_NAMES)
        assert trial.shell.commands[-2:] == [
            (
                "gh label create epic --color 5319e7"
                " --description 'Too big for one PR: split into sub-issues, carries"
                " no size' --force"
            ),
            (
                "gh label create shape --color fbca04"
                " --description 'Changes the shape of the system: the user designs"
                " it first' --force"
            ),
        ]
