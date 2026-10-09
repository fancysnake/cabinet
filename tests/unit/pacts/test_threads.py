"""Whether a thread carries the ritual's own answer, and which issue it was filed as."""

from cabinet.pacts.issues import Issue
from cabinet.pacts.threads import ANSWERED, Comment, Thread, filed_as, filed_for


def _thread(*bodies: str, author: str = "me") -> Thread:
    comments = [Comment(id=str(n), author=author, body=b) for n, b in enumerate(bodies)]
    return Thread(id="PRRT_1", resolved=False, comments=comments)


class TestAnswered:
    @staticmethod
    def test_the_last_word_carrying_the_mark_is_answered() -> None:
        assert _thread("guard", f"done\n\n{ANSWERED}").answered_by("me")

    @staticmethod
    def test_a_word_after_the_answer_reopens_it() -> None:
        assert not _thread(ANSWERED, "no").answered_by("me")

    @staticmethod
    def test_a_thread_without_comments_is_not_answered() -> None:
        assert not _thread().answered_by("me")

    @staticmethod
    def test_a_mark_someone_else_wrote_is_not_an_answer() -> None:
        assert not _thread(ANSWERED, author="stranger").answered_by("me")


class TestFiledAs:
    @staticmethod
    def test_the_issue_naming_the_thread_is_found() -> None:
        other = Issue(
            number=1, title="t", url="u1", body=filed_for("PRRT_2"), author="me"
        )
        filed = Issue(
            number=2,
            title="t",
            url="u2",
            body=f"x\n\n{filed_for('PRRT_1')}",
            author="me",
        )

        assert filed_as([other, filed], "PRRT_1", "me") == filed

    @staticmethod
    def test_no_issue_naming_the_thread_is_none() -> None:
        assert filed_as([Issue(number=1, title="t", url="u")], "PRRT_1", "me") is None

    @staticmethod
    def test_an_issue_someone_else_opened_is_none() -> None:
        forged = Issue(
            number=1, title="t", url="u", body=filed_for("PRRT_1"), author="stranger"
        )

        assert filed_as([forged], "PRRT_1", "me") is None
