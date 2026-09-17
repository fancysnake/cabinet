"""What vekna sweeps: every step and ritual, and the services already bound."""

from cabinet.inits.services import Services
from cabinet.pacts.services import services
from cabinet.rituals import pr_review, pr_sweep


# A step is named after its function and a ritual after itself, so the names
# vekna will register are exactly the names the facade exports.
class TestFacade:
    @staticmethod
    def test_the_sweeps_export_their_rituals_and_every_step() -> None:
        exported = [getattr(pr_sweep, name) for name in pr_sweep.__all__]

        assert {one.name for one in exported} == set(pr_sweep.__all__)
        assert {"pr_refresh", "pr_cover"} <= set(pr_sweep.__all__)

    @staticmethod
    def test_the_review_exports_its_ritual_and_every_step() -> None:
        exported = [getattr(pr_review, name) for name in pr_review.__all__]

        assert {one.name for one in exported} == set(pr_review.__all__)
        assert "pr_review" in pr_review.__all__

    @staticmethod
    def test_importing_the_facade_wires_the_services() -> None:
        assert isinstance(services(), Services)
