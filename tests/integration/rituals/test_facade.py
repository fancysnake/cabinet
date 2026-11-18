"""What vekna sweeps: one facade per ritual, with steps and services ready."""

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
    steps,
)

# The rituals each facade exports: its own, and for heal.mine the heal.pr it
# queues.
_FACADES = [
    pytest.param(heal_mine, {"heal.mine", "heal.pr"}, id="heal.mine"),
    pytest.param(heal_pr, {"heal.pr"}, id="heal.pr"),
    pytest.param(heal_main, {"heal.main"}, id="heal.main"),
    pytest.param(heal_this, {"heal.this"}, id="heal.this"),
    pytest.param(merge, {"merge"}, id="merge"),
    pytest.param(ci, {"ci"}, id="ci"),
    pytest.param(answer, {"answer"}, id="answer"),
    pytest.param(review, {"review"}, id="review"),
    pytest.param(guide, {"guide"}, id="guide"),
    pytest.param(identify, {"identify"}, id="identify"),
    pytest.param(labels, {"labels"}, id="labels"),
    pytest.param(labels_heal, {"labels.heal"}, id="labels.heal"),
    pytest.param(labels_identify, {"labels.identify"}, id="labels.identify"),
]


# The names `vekna cast` takes off a facade, which need not be Python names.
def _rituals(facade: ModuleType) -> set[str]:
    return {one.name for one in vars(facade).values() if isinstance(one, Ritual)}


class TestFacade:
    @staticmethod
    @pytest.mark.parametrize(("facade", "rituals"), _FACADES)
    def test_a_facade_exports_its_rituals(
        facade: ModuleType, rituals: set[str]
    ) -> None:
        assert _rituals(facade) == rituals

    # A step registers when its module is imported, and the package imports
    # every step module, whichever facade a project names.
    @staticmethod
    def test_the_package_imports_every_step_module() -> None:
        assert (steps.heal, steps.identify, steps.labels) == (
            heal_steps,
            identify_steps,
            labels_steps,
        )

    # heal.mine queues heal.pr casts, so a project loading only heal.mine
    # must still have heal.pr to run them.
    @staticmethod
    def test_heal_mine_brings_the_heal_pr_it_queues() -> None:
        assert heal_mine.heal_pr is heal_pr.heal_pr

    @staticmethod
    def test_importing_a_facade_wires_the_services() -> None:
        assert isinstance(services(), Services)
