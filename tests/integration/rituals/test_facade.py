"""What vekna sweeps: one facade per ritual, and the services already bound."""

from cabinet.inits.services import Services
from cabinet.pacts.services import services
from cabinet.rituals import cover, refresh, review


# A step is named after its function and a ritual after itself, so the names
# vekna will register are exactly the names each facade exports.
class TestFacade:
    @staticmethod
    def test_refresh_exports_its_ritual_and_the_whole_sweep() -> None:
        exported = [getattr(refresh, name) for name in refresh.__all__]

        assert {one.name for one in exported} == set(refresh.__all__)
        assert "refresh" in refresh.__all__
        assert "cover" not in refresh.__all__

    @staticmethod
    def test_cover_exports_its_ritual_and_the_whole_sweep() -> None:
        exported = [getattr(cover, name) for name in cover.__all__]

        assert {one.name for one in exported} == set(cover.__all__)
        assert "cover" in cover.__all__
        assert "refresh" not in cover.__all__

    # The two facades name the same step objects, so a project loading both
    # registers each step once.
    @staticmethod
    def test_the_two_sweeps_share_their_steps() -> None:
        assert refresh.list_prs is cover.list_prs
        assert refresh.close_gap is cover.close_gap

    @staticmethod
    def test_review_exports_its_ritual_and_every_step() -> None:
        exported = [getattr(review, name) for name in review.__all__]

        assert {one.name for one in exported} == set(review.__all__)
        assert "review" in review.__all__

    @staticmethod
    def test_importing_a_facade_wires_the_services() -> None:
        assert isinstance(services(), Services)
