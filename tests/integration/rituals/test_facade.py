"""What vekna sweeps: one facade per ritual, and the services already bound."""

from types import ModuleType

import pytest
from vekna.lexicon._pacts import Ritual, Step

from cabinet.gates.ritual.vekna import heal as heal_steps
from cabinet.gates.ritual.vekna import identify as identify_steps
from cabinet.gates.ritual.vekna import labels as labels_steps
from cabinet.inits.services import Services
from cabinet.pacts.services import services
from cabinet.rituals import (
    heal_mine,
    heal_this,
    identify,
    labels,
    labels_heal,
    labels_identify,
    merge,
    review,
)

# Every facade over the heal graph, and the ritual each one casts.
_HEALS = [
    pytest.param(heal_mine, "heal.mine", id="heal.mine"),
    pytest.param(heal_this, "heal.this", id="heal.this"),
    pytest.param(merge, "merge", id="merge"),
    pytest.param(review, "review", id="review"),
]


# A facade exports every step of the module behind it, so it names the whole
# graph it casts. Read off that module rather than off the facade's own
# `__all__`, which cannot catch a step nobody imported.
def _steps(module: ModuleType) -> set[str]:
    return {name for name, found in vars(module).items() if isinstance(found, Step)}


# The names vekna will register off a facade: each step's own, and the
# ritual's — which is what `vekna cast` takes, and need not be a Python name.
def _registered(facade: ModuleType) -> set[str]:
    exported = [getattr(facade, name) for name in facade.__all__]
    return {one.name for one in exported if isinstance(one, Step | Ritual)}


# A step is named after its function, so a facade's steps are exactly the
# names it exports beside its ritual.
class TestFacade:
    @staticmethod
    @pytest.mark.parametrize(("facade", "name"), _HEALS)
    def test_a_heal_facade_exports_its_ritual_and_every_step(
        facade: ModuleType, name: str
    ) -> None:
        ritual = facade.__name__.rsplit(".", 1)[-1]
        assert set(facade.__all__) == _steps(heal_steps) | {ritual}
        assert _registered(facade) == _steps(heal_steps) | {name}

    # One step object behind every one, so loading them registers each step
    # once: a second step taking the same payload class would refuse to load.
    @staticmethod
    def test_the_heal_rituals_share_their_steps() -> None:
        assert heal_this.tend is heal_mine.tend is merge.tend is review.tend

    @staticmethod
    def test_identify_exports_its_ritual_and_every_step() -> None:
        assert set(identify.__all__) == _steps(identify_steps) | {"identify"}
        assert _registered(identify) == set(identify.__all__)

    @staticmethod
    def test_importing_a_facade_wires_the_services() -> None:
        assert isinstance(services(), Services)

    @staticmethod
    def test_labels_exports_its_ritual_and_its_step() -> None:
        assert set(labels.__all__) == _steps(labels_steps) | {"labels"}
        assert _registered(labels) == {"labels", "conjure"}

    @staticmethod
    def test_labels_heal_exports_its_ritual_and_its_step() -> None:
        assert set(labels_heal.__all__) == _steps(labels_steps) | {"labels_heal"}
        assert _registered(labels_heal) == {"labels.heal", "conjure"}

    @staticmethod
    def test_labels_identify_exports_its_ritual_and_its_step() -> None:
        assert set(labels_identify.__all__) == _steps(labels_steps) | {
            "labels_identify"
        }
        assert _registered(labels_identify) == {"labels.identify", "conjure"}

    # One step object behind all three, so loading them registers `conjure` once.
    @staticmethod
    def test_the_label_rituals_share_their_step() -> None:
        assert labels.conjure is labels_heal.conjure is labels_identify.conjure
