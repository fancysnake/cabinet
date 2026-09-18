"""What vekna sweeps: one facade per ritual, and the services already bound."""

from typing import TYPE_CHECKING

from vekna.lexicon._pacts import Step

from cabinet.gates.ritual.vekna import labels as labels_steps
from cabinet.gates.ritual.vekna import review as review_steps
from cabinet.gates.ritual.vekna import sweep
from cabinet.inits.services import Services
from cabinet.pacts.services import services
from cabinet.rituals import cover, labels, refresh, review

if TYPE_CHECKING:
    from types import ModuleType


# What vekna registers is every `Step` it finds in the module's namespace, so
# what a facade owes is every step of the module behind it. Read off that
# module rather than off the facade's own `__all__`, which cannot catch a step
# nobody imported.
def _steps(module: ModuleType) -> set[str]:
    return {name for name, found in vars(module).items() if isinstance(found, Step)}


# A step is named after its function and a ritual after itself, so the names
# vekna will register are exactly the names each facade exports.
class TestFacade:
    @staticmethod
    def test_refresh_exports_its_ritual_and_the_whole_sweep() -> None:
        exported = [getattr(refresh, name) for name in refresh.__all__]

        assert set(refresh.__all__) == _steps(sweep) | {"refresh"}
        assert {one.name for one in exported} == set(refresh.__all__)

    @staticmethod
    def test_cover_exports_its_ritual_and_the_whole_sweep() -> None:
        exported = [getattr(cover, name) for name in cover.__all__]

        assert set(cover.__all__) == _steps(sweep) | {"cover"}
        assert {one.name for one in exported} == set(cover.__all__)

    # The two facades name the same step objects, so a project loading both
    # registers each step once.
    @staticmethod
    def test_the_two_sweeps_share_their_steps() -> None:
        assert refresh.list_prs is cover.list_prs
        assert refresh.close_gap is cover.close_gap

    @staticmethod
    def test_review_exports_its_ritual_and_every_step() -> None:
        exported = [getattr(review, name) for name in review.__all__]

        assert set(review.__all__) == _steps(review_steps) | {"review"}
        assert {one.name for one in exported} == set(review.__all__)

    @staticmethod
    def test_importing_a_facade_wires_the_services() -> None:
        assert isinstance(services(), Services)

    @staticmethod
    def test_labels_exports_its_ritual_and_its_step() -> None:
        exported = [getattr(labels, name) for name in labels.__all__]

        assert set(labels.__all__) == _steps(labels_steps) | {"labels"}
        assert {one.name for one in exported} == set(labels.__all__)
