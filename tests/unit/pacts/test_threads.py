"""Whether a thread carries the ritual's own answer."""

from cabinet.pacts.threads import ANSWERED, Comment, Thread


def _thread(*bodies: str) -> Thread:
    comments = [Comment(id=str(n), author="me", body=b) for n, b in enumerate(bodies)]
    return Thread(id="PRRT_1", resolved=False, comments=comments)


class TestAnswered:
    @staticmethod
    def test_the_last_word_carrying_the_mark_is_answered() -> None:
        assert _thread("guard", f"done\n\n{ANSWERED}").answered

    @staticmethod
    def test_a_word_after_the_answer_reopens_it() -> None:
        assert not _thread(ANSWERED, "no").answered

    @staticmethod
    def test_a_thread_without_comments_is_not_answered() -> None:
        assert not _thread().answered
