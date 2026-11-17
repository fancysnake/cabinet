"""What vekna sweeps: one facade per ritual, and the services already bound."""

from types import ModuleType

import pytest
from vekna.lexicon._pacts import Ritual

from cabinet.gates.ritual.vekna import heal as heal_steps
from cabinet.gates.ritual.vekna import identify as identify_steps
from cabinet.gates.ritual.vekna import labels as labels_steps
from cabinet.inits.services import Services
from cabinet.pacts.services import services
from cabinet.rituals import (
    answer,
    ci,
    guide,
    heal_main,
    heal_mine,
    heal_pr,
    heal_this,
    identify,
    labels,
    labels_heal,
    labels_identify,
    merge,
    review,
)

# Every facade, the step module behind it, and the rituals it exports: its
# own, and for heal.mine the heal.pr it queues.
_FACADES = [
    pytest.param(
        heal_mine,
        heal_steps,
        {"heal_mine": "heal.mine", "heal_pr": "heal.pr"},
        id="heal.mine",
    ),
    pytest.param(heal_pr, heal_steps, {"heal_pr": "heal.pr"}, id="heal.pr"),
    pytest.param(heal_main, heal_steps, {"heal_main": "heal.main"}, id="heal.main"),
    pytest.param(heal_this, heal_steps, {"heal_this": "heal.this"}, id="heal.this"),
    pytest.param(merge, heal_steps, {"merge": "merge"}, id="merge"),
    pytest.param(ci, heal_steps, {"ci": "ci"}, id="ci"),
    pytest.param(answer, heal_steps, {"answer": "answer"}, id="answer"),
    pytest.param(review, heal_steps, {"review": "review"}, id="review"),
    pytest.param(guide, heal_steps, {"guide": "guide"}, id="guide"),
    pytest.param(identify, identify_steps, {"identify": "identify"}, id="identify"),
    pytest.param(labels, labels_steps, {"labels": "labels"}, id="labels"),
    pytest.param(
        labels_heal, labels_steps, {"labels_heal": "labels.heal"}, id="labels.heal"
    ),
    pytest.param(
        labels_identify,
        labels_steps,
        {"labels_identify": "labels.identify"},
        id="labels.identify",
    ),
]


# The names `vekna cast` takes off a facade, which need not be Python names.
def _rituals(facade: ModuleType) -> set[str]:
    exported = [getattr(facade, name) for name in facade.__all__]
    return {one.name for one in exported if isinstance(one, Ritual)}


class TestFacade:
    # A step registers when its module is imported, so a facade that holds the
    # module as `steps` has registered the whole graph it casts.
    @staticmethod
    @pytest.mark.parametrize(("facade", "steps", "rituals"), _FACADES)
    def test_a_facade_exports_its_rituals_and_its_step_module(
        facade: ModuleType, steps: ModuleType, rituals: dict[str, str]
    ) -> None:
        assert set(facade.__all__) == rituals.keys() | {"steps"}
        assert facade.steps is steps
        assert _rituals(facade) == set(rituals.values())

    # heal.mine queues heal.pr casts, so a project loading only heal.mine
    # must still have heal.pr to run them.
    @staticmethod
    def test_heal_mine_brings_the_heal_pr_it_queues() -> None:
        assert heal_mine.heal_pr is heal_pr.heal_pr

    @staticmethod
    def test_importing_a_facade_wires_the_services() -> None:
        assert isinstance(services(), Services)
