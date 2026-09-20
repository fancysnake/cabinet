"""Making the labels, on either forge, twice over."""

from pathlib import Path

import pytest
from vekna.lexicon import NoComponents, RitualError
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
]


class TestLabels:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_every_label_is_made_with_force(trial: Trial) -> None:
        trial.shell.replies(when="gh label create*", always=True)

        result = trial.cast(labels, NoComponents())

        assert result == Labelled(names=_NAMES)
        assert trial.steps == ["conjure"]
        assert len(trial.shell.commands) == len(_NAMES)
        assert trial.shell.commands[0] == (
            "gh label create pr::thermo --color 0e8a16"
            " --description 'A quality review was posted; remove to ask again'"
            " --force"
        )

    @staticmethod
    def test_on_gitlab_an_existing_label_is_updated(trial: Trial, here: Path) -> None:
        (here / ".vekna.toml").write_text('[cabinet]\nforge = "gitlab"\n')
        trial.shell.replies(when="glab api projects/:id/labels -X POST*", exit_code=1)
        trial.shell.replies(when="glab api projects/:id/labels -X POST*", always=True)
        trial.shell.replies(when="glab api projects/:id/labels/* -X PUT*")

        result = trial.cast(labels, NoComponents())

        assert result == Labelled(names=_NAMES)
        assert trial.shell.commands[0] == (
            "glab api projects/:id/labels -X POST -f name=pr::thermo"
            " -f color='#0e8a16'"
            " -f description='A quality review was posted; remove to ask again'"
        )
        assert trial.shell.commands[1] == (
            "glab api projects/:id/labels/pr%3A%3Athermo -X PUT -f color='#0e8a16'"
            " -f description='A quality review was posted; remove to ask again'"
        )
        assert len(trial.shell.commands) == len(_NAMES) + 1

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_forge_that_refuses_fails_the_cast(trial: Trial) -> None:
        trial.shell.replies(when="gh label create*", exit_code=1, stderr="403")

        with pytest.raises(RitualError, match="could not create the label pr::thermo"):
            trial.cast(labels, NoComponents())
