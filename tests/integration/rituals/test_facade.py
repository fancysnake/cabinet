"""What vekna sweeps: one facade per ritual, and the services already bound."""

from types import ModuleType

from vekna.lexicon._pacts import Ritual, Step

from cabinet.gates.ritual.vekna import identify as identify_steps
from cabinet.gates.ritual.vekna import labels as labels_steps
from cabinet.gates.ritual.vekna import review as review_steps
from cabinet.gates.ritual.vekna import sweep
from cabinet.inits.services import Services
from cabinet.pacts.services import services
from cabinet.rituals import (
    cover,
    identify,
    labels,
    labels_identify,
    labels_pr,
    refresh,
    review,
)


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
    def test_refresh_exports_its_ritual_and_the_whole_sweep() -> None:
        assert set(refresh.__all__) == _steps(sweep) | {"refresh"}
        assert _registered(refresh) == set(refresh.__all__)

    @staticmethod
    def test_cover_exports_its_ritual_and_the_whole_sweep() -> None:
        assert set(cover.__all__) == _steps(sweep) | {"cover"}
        assert _registered(cover) == set(cover.__all__)

    # The two facades name the same step objects, decorated once: a second
    # step taking the same payload class would refuse to load.
    @staticmethod
    def test_the_two_sweeps_share_their_steps() -> None:
        assert refresh.list_prs is cover.list_prs
        assert refresh.close_gap is cover.close_gap

    @staticmethod
    def test_review_exports_its_ritual_and_every_step() -> None:
        assert set(review.__all__) == _steps(review_steps) | {"review"}
        assert _registered(review) == set(review.__all__)

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
    def test_labels_pr_exports_its_ritual_and_its_step() -> None:
        assert set(labels_pr.__all__) == _steps(labels_steps) | {"labels_pr"}
        assert _registered(labels_pr) == {"labels.pr", "conjure"}

    @staticmethod
    def test_labels_identify_exports_its_ritual_and_its_step() -> None:
        assert set(labels_identify.__all__) == _steps(labels_steps) | {
            "labels_identify"
        }
        assert _registered(labels_identify) == {"labels.identify", "conjure"}

    # One step object behind all three, so loading them registers `conjure` once.
    @staticmethod
    def test_the_label_rituals_share_their_step() -> None:
        assert labels.conjure is labels_pr.conjure is labels_identify.conjure
